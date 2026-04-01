#!/usr/bin/env python3
"""
DRskill Pipeline: Deep Research → Skill Generation for SkillsBench tasks.

Usage:
    python3 dr_skill_pipeline.py <task_dir> [options]
    python3 dr_skill_pipeline.py --batch <tasks_root> [options]

Environment variables:
    OPENAI_API_KEY   - API key for both Perplexity and Claude
    OPENAI_BASE_URL  - Base URL for OpenAI-compatible API
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import sys
import time
import traceback
from datetime import datetime
from pathlib import Path
from typing import Any
from urllib import error, request

# ── Models ──────────────────────────────────────────────────────────────────
DR_MODEL = "perplexity-deep-research-ssvip"
SKILL_MODEL = "claude-opus-4-6"

# ── Timeouts ────────────────────────────────────────────────────────────────
DR_TIMEOUT = 600
SKILL_TIMEOUT = 300
MAX_RETRIES = 3
RETRY_DELAY = 30

# ── SkillsBench blacklist (prevent DR from accessing benchmark sources) ────
DR_BLOCKED_DOMAINS = [
    "-skillsbench.ai",
    "-www.skillsbench.ai",
]
DR_BLOCKED_URLS = [
    "https://github.com/benchflow-ai/skillsbench",
    "https://arxiv.org/abs/2602.12670",
    "https://www.skillsbench.ai/",
    "https://huggingface.co/papers/2602.12670",
    "https://news.ycombinator.com/item?id=47040430",
]

# ── Dockerfile COPY lines for skills ───────────────────────────────────────
SKILL_COPY_LINES = """\
# Copy skills to all agent paths
COPY skills /root/.claude/skills
COPY skills /root/.codex/skills
COPY skills /root/.opencode/skill
COPY skills /root/.goose/skills
COPY skills /root/.factory/skills
COPY skills /root/.agents/skills
COPY skills /root/.gemini/skills
"""


# ═══════════════════════════════════════════════════════════════════════════
#  API helpers
# ═══════════════════════════════════════════════════════════════════════════

def _normalize_base_url(base_url: str) -> str:
    base = base_url.rstrip("/")
    return base if base.endswith("/v1") else f"{base}/v1"


def _api_call(
    api_key: str,
    base_url: str,
    endpoint: str,
    payload: dict[str, Any],
    timeout: int,
) -> dict[str, Any]:
    url = f"{_normalize_base_url(base_url)}/{endpoint}"
    data = json.dumps(payload).encode("utf-8")
    req = request.Request(
        url, data=data, method="POST",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
    )
    try:
        with request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read().decode("utf-8")
    except error.HTTPError as e:
        body = e.read().decode("utf-8", errors="ignore")
        raise RuntimeError(f"API HTTP {e.code}: {body[:500]}") from e
    except error.URLError as e:
        raise RuntimeError(f"API network error: {e}") from e
    return json.loads(raw)


def _extract_text(resp: dict[str, Any]) -> str:
    """Extract text from various API response formats."""
    # Responses API format
    ot = resp.get("output_text")
    if isinstance(ot, str) and ot.strip():
        return ot.strip()
    # Responses API with output array
    output = resp.get("output")
    if isinstance(output, list):
        parts = []
        for item in output:
            if not isinstance(item, dict):
                continue
            content = item.get("content")
            if not isinstance(content, list):
                continue
            for c in content:
                if isinstance(c, dict):
                    t = c.get("text")
                    if isinstance(t, str) and t.strip():
                        parts.append(t.strip())
        if parts:
            return "\n\n".join(parts)
    # Chat completions format
    try:
        msg = resp["choices"][0]["message"]["content"]
        if isinstance(msg, str):
            return msg.strip()
        if isinstance(msg, list):
            return "\n".join(
                it.get("text", "") for it in msg
                if isinstance(it, dict) and it.get("type") == "text"
            ).strip()
    except (KeyError, IndexError, TypeError):
        pass
    raise RuntimeError(f"Cannot extract text from response: {str(resp)[:300]}")


def call_with_retry(fn, *args, retries: int = MAX_RETRIES, delay: int = RETRY_DELAY, **kwargs):
    """Call fn with retries on failure."""
    for attempt in range(1, retries + 1):
        try:
            return fn(*args, **kwargs)
        except Exception as e:
            if attempt == retries:
                raise
            print(f"  [RETRY {attempt}/{retries}] {e}", file=sys.stderr)
            time.sleep(delay)


# ═══════════════════════════════════════════════════════════════════════════
#  Task context collection
# ═══════════════════════════════════════════════════════════════════════════

def collect_task_context(task_dir: Path) -> dict[str, str]:
    """Collect all relevant task files, excluding skills/ and solution/."""
    ctx: dict[str, str] = {}

    # instruction.md
    instr = task_dir / "instruction.md"
    if instr.exists():
        ctx["instruction.md"] = instr.read_text(encoding="utf-8")

    # task.toml
    toml = task_dir / "task.toml"
    if toml.exists():
        ctx["task.toml"] = toml.read_text(encoding="utf-8")

    # Dockerfile
    dockerfile = task_dir / "environment" / "Dockerfile"
    if dockerfile.exists():
        ctx["Dockerfile"] = dockerfile.read_text(encoding="utf-8")

    # test_outputs.py
    test_file = task_dir / "tests" / "test_outputs.py"
    if test_file.exists():
        ctx["test_outputs.py"] = test_file.read_text(encoding="utf-8")

    # Environment file listing (excluding skills/)
    env_dir = task_dir / "environment"
    if env_dir.exists():
        file_list = []
        for p in sorted(env_dir.rglob("*")):
            rel = p.relative_to(env_dir)
            # Skip skills directory
            if str(rel).startswith("skills"):
                continue
            if p.is_file():
                size = p.stat().st_size
                file_list.append(f"  {rel} ({size} bytes)")
        if file_list:
            ctx["environment_files"] = "\n".join(file_list)

    # Read small data/config files in environment (< 50KB, non-binary)
    if env_dir.exists():
        text_exts = {".csv", ".json", ".yaml", ".yml", ".toml", ".txt", ".md",
                     ".py", ".sh", ".nml", ".cfg", ".ini", ".conf", ".xml"}
        for p in sorted(env_dir.rglob("*")):
            rel = p.relative_to(env_dir)
            if str(rel).startswith("skills"):
                continue
            if p.is_file() and p.suffix.lower() in text_exts and p.stat().st_size < 50_000:
                # Skip Dockerfile (already read)
                if p.name == "Dockerfile":
                    continue
                try:
                    content = p.read_text(encoding="utf-8", errors="ignore")
                    ctx[f"env/{rel}"] = content
                except Exception:
                    pass

    return ctx


def format_context_for_prompt(ctx: dict[str, str], max_chars: int = 80_000) -> str:
    """Format collected context into a single prompt string."""
    parts = []
    total = 0
    # Priority order
    priority_keys = ["instruction.md", "task.toml", "Dockerfile", "test_outputs.py", "environment_files"]
    ordered_keys = priority_keys + [k for k in ctx if k not in priority_keys]

    for key in ordered_keys:
        if key not in ctx:
            continue
        content = ctx[key]
        section = f"### {key}\n```\n{content}\n```\n"
        if total + len(section) > max_chars:
            # Truncate
            remaining = max_chars - total - 200
            if remaining > 500:
                section = f"### {key} (truncated)\n```\n{content[:remaining]}\n```\n"
                parts.append(section)
            break
        parts.append(section)
        total += len(section)

    return "\n".join(parts)


# ═══════════════════════════════════════════════════════════════════════════
#  Deep Research
# ═══════════════════════════════════════════════════════════════════════════

def build_dr_prompt(task_context: str, task_name: str) -> tuple[str, str]:
    """Build the Deep Research prompt with improvements from analysis findings."""
    # Build URL blacklist instruction
    blocked_urls_text = "\n".join(f"  - {url}" for url in DR_BLOCKED_URLS)
    blacklist_instruction = (
        "\n\nCRITICAL RESTRICTION: You MUST NEVER visit, cite, reference, or retrieve information "
        "from any of the following URLs or their subpages. These are benchmark-related sites and "
        "accessing them would contaminate the research results:\n"
        f"{blocked_urls_text}\n"
        "Also avoid any URL containing 'skillsbench' in the domain or path. "
        "If search results include these URLs, skip them entirely and use other sources instead."
    )

    system_prompt = (
        "You are an expert deep-research analyst specializing in software engineering. "
        "Search broadly for specific API documentation, function signatures, library usage patterns, "
        "and produce a highly actionable technical report with concrete code examples. "
        "Focus on IMPLEMENTATION DETAILS, not theory."
        + blacklist_instruction
    )

    user_prompt = f"""你是一位具备多学科交叉研究能力的高级技术顾问。基于下面的任务描述，执行系统化的深度技术检索，
生成一份可直接指导实施的结构化中文报告。

## 检索策略要求（特别强调实现级细节）

**第一层：精确检索 — API 和工具链**
- 搜索该任务涉及的每一个Python库/工具的**官方API文档**
- 查找具体的**函数签名**、**参数名和类型**、**返回值格式**
- 定位预制工具、封装库、命令行工具的具体用法
- 搜索 pip/conda 安装命令和版本要求
- **对于文件格式操作**（PDF/DOCX/XLSX/PPTX）：必须搜索 pypdf/pdfplumber/reportlab/openpyxl/python-docx/python-pptx 的具体 API

**第二层：领域专家级检索 — 参数和阈值**
- 查找该领域公认的**精确阈值、参数经验值**
- 搜索 DataFrame/数据结构的**精确列名**和字段格式
- 检索 config 字典/配置文件的**必填键**和默认值
- 搜索输出格式规范（JSON schema、CSV列头、文件命名）

**第三层：反模式和常见错误**
- 搜索该技术方案的 **"不要做什么"**（anti-patterns, common mistakes）
- 查找 "Never use X" 或 "Avoid Y" 类型的最佳实践警告
- 搜索坐标系、单位、编码等常见混淆点
- 检索版本兼容性问题和已知 breaking changes

**第四层：代码示例**
- 搜索完整的、可运行的代码示例
- 优先查找 GitHub 上的实际项目用法
- 收集 Stack Overflow 上高票答案中的代码片段

## 报告结构要求

### 1. 任务分析
- 用一句话概括任务本质
- 分解为 2-5 个子问题
- 列出每个子问题涉及的**具体库/工具**

### 2. 核心技术方案（必须包含代码）
每条方案必须包含：
- 具体的库名称及推荐版本
- **完整的函数调用示例**（包含参数名和推荐值）
- 输入/输出数据格式规范
- 关键注意事项

### 3. API 速查表
以代码块形式列出所有关键 API：
```python
# 库名.模块
function_name(param1: type = default, param2: type = default) -> return_type
```

### 4. 参数校准表
| 参数名 | 推荐值 | 来源 | 注意事项 |

### 5. 反模式清单
列出所有已知的 "不要做什么"，格式：
- ❌ 不要: [具体做法]
- ✅ 应该: [正确做法]
- 原因: [为什么]

### 6. 完整实施代码框架
提供一个可以直接使用的代码骨架

---
任务名称：{task_name}

任务上下文：

{task_context}
"""
    return system_prompt, user_prompt


def call_deep_research(api_key: str, base_url: str, task_context: str, task_name: str) -> str:
    """Call Perplexity Deep Research API."""
    system_prompt, user_prompt = build_dr_prompt(task_context, task_name)
    payload = {
        "model": DR_MODEL,
        "temperature": 0.2,
        "search_domain_filter": DR_BLOCKED_DOMAINS,
        "input": [
            {"role": "system", "content": [{"type": "input_text", "text": system_prompt}]},
            {"role": "user", "content": [{"type": "input_text", "text": user_prompt}]},
        ],
    }

    def _call():
        resp = _api_call(api_key, base_url, "responses", payload, DR_TIMEOUT)
        return _extract_text(resp)

    return call_with_retry(_call)


# ═══════════════════════════════════════════════════════════════════════════
#  Skill Generation
# ═══════════════════════════════════════════════════════════════════════════

SKILL_GEN_SYSTEM = """\
You are an expert skill designer for AI agent benchmarks. You create high-quality \
SKILL.md files that help AI agents complete specialized tasks.

## SKILL.md Format

Every skill has:
1. YAML frontmatter with `name` and `description` fields (description is the PRIMARY \
trigger - include ALL "when to use" information here)
2. Markdown body with actionable instructions, code examples, and parameters

## Design Principles
- Concise: Only add knowledge Claude doesn't already have
- Specific: Include exact API calls, parameter values, data formats
- Actionable: Provide runnable code examples, not theory
- Progressive disclosure: SKILL.md body < 500 lines; use references/ for details

## Output Format
Return ONLY valid JSON (no markdown fencing, no extra text) with this structure:
{
  "skills": [
    {
      "name": "skill-name-in-kebab-case",
      "skill_md": "---\\nname: skill-name\\ndescription: ...\\n---\\n\\n# Title\\n...",
      "scripts": {
        "script_name.py": "#!/usr/bin/env python3\\n..."
      }
    }
  ]
}

The "scripts" field is optional - only include when deterministic code is needed.
"""


def build_skill_gen_prompt(task_context: str, dr_report: str, task_name: str) -> str:
    """Build the prompt for Claude to generate skills."""
    return f"""Based on the following task description and deep research report, design 1-5 skills \
that would help an AI agent complete this task effectively.

## Task: {task_name}

## Task Context
{task_context}

## Deep Research Report
{dr_report[:60000]}

## Requirements

1. Generate 1-5 skills, each covering a distinct capability domain
2. Each skill MUST include:
   - Specific function/API calls with exact parameter names and types
   - Recommended parameter values with justification
   - Input/output data format specifications
   - Code examples that can be directly used
   - Common pitfalls and anti-patterns to avoid
3. The `description` in frontmatter must clearly state WHEN to use the skill
4. For file format tasks (PDF/DOCX/XLSX/PPTX), include format-specific API skills
5. For tasks with specific tools/scripts, document the exact CLI usage
6. Keep each SKILL.md body under 400 lines
7. Do NOT include README, CHANGELOG, or other auxiliary files

Output ONLY the JSON object. No markdown code fences."""


def call_skill_generation(
    api_key: str, base_url: str, task_context: str, dr_report: str, task_name: str
) -> list[dict[str, Any]]:
    """Call Claude to generate skills."""
    user_prompt = build_skill_gen_prompt(task_context, dr_report, task_name)
    payload = {
        "model": SKILL_MODEL,
        "messages": [
            {"role": "system", "content": SKILL_GEN_SYSTEM},
            {"role": "user", "content": user_prompt},
        ],
        "temperature": 0.3,
    }

    def _call():
        resp = _api_call(api_key, base_url, "chat/completions", payload, SKILL_TIMEOUT)
        text = _extract_text(resp)
        # Try to extract JSON from the response
        return _parse_skills_json(text)

    return call_with_retry(_call)


def _parse_skills_json(text: str) -> list[dict[str, Any]]:
    """Parse skills JSON from Claude's response, handling various formats."""
    # Try direct parse
    try:
        data = json.loads(text)
        if isinstance(data, dict) and "skills" in data:
            return data["skills"]
        if isinstance(data, list):
            return data
    except json.JSONDecodeError:
        pass

    # Try extracting JSON from markdown code blocks
    patterns = [
        r'```json\s*\n(.*?)\n```',
        r'```\s*\n(.*?)\n```',
        r'(\{[\s\S]*"skills"[\s\S]*\})',
    ]
    for pat in patterns:
        match = re.search(pat, text, re.DOTALL)
        if match:
            try:
                data = json.loads(match.group(1))
                if isinstance(data, dict) and "skills" in data:
                    return data["skills"]
                if isinstance(data, list):
                    return data
            except json.JSONDecodeError:
                continue

    raise RuntimeError(f"Failed to parse skills JSON from response:\n{text[:1000]}")


# ═══════════════════════════════════════════════════════════════════════════
#  Skill writing
# ═══════════════════════════════════════════════════════════════════════════

def write_skills(task_dir: Path, skills: list[dict[str, Any]]) -> list[str]:
    """Write generated skills to the task's environment/skills/ directory."""
    skills_dir = task_dir / "environment" / "skills"
    skills_dir.mkdir(parents=True, exist_ok=True)

    written = []
    for skill in skills:
        name = skill.get("name", "").strip()
        if not name:
            continue

        # Sanitize name
        name = re.sub(r'[^a-zA-Z0-9_-]', '-', name).strip('-')
        if not name:
            continue

        skill_dir = skills_dir / name
        skill_dir.mkdir(parents=True, exist_ok=True)

        # Write SKILL.md
        skill_md = skill.get("skill_md", "")
        if skill_md:
            (skill_dir / "SKILL.md").write_text(skill_md, encoding="utf-8")

        # Write scripts if any
        scripts = skill.get("scripts", {})
        if scripts:
            scripts_dir = skill_dir / "scripts"
            scripts_dir.mkdir(exist_ok=True)
            for fname, content in scripts.items():
                (scripts_dir / fname).write_text(content, encoding="utf-8")

        written.append(name)

    return written


# ═══════════════════════════════════════════════════════════════════════════
#  Dockerfile patching
# ═══════════════════════════════════════════════════════════════════════════

def patch_dockerfile(task_dir: Path) -> bool:
    """Add COPY skills lines to Dockerfile if not already present."""
    dockerfile = task_dir / "environment" / "Dockerfile"
    if not dockerfile.exists():
        return False

    content = dockerfile.read_text(encoding="utf-8")

    # Check if already has COPY skills
    if "COPY skills /root/.claude/skills" in content:
        return False

    # Find the best insertion point - after the last COPY or RUN line
    lines = content.rstrip().split("\n")
    content_with_skills = content.rstrip() + "\n\n" + SKILL_COPY_LINES
    dockerfile.write_text(content_with_skills, encoding="utf-8")
    return True


# ═══════════════════════════════════════════════════════════════════════════
#  Pipeline for a single task
# ═══════════════════════════════════════════════════════════════════════════

def process_task(task_dir: Path, api_key: str, base_url: str, save_report: bool = True) -> bool:
    """Run the full pipeline for a single task."""
    task_name = task_dir.name
    print(f"\n{'='*60}")
    print(f"  Processing: {task_name}")
    print(f"{'='*60}")

    # 1. Collect context
    print(f"  [1/4] Collecting task context...")
    ctx = collect_task_context(task_dir)
    if "instruction.md" not in ctx:
        print(f"  ERROR: No instruction.md found in {task_dir}", file=sys.stderr)
        return False
    context_text = format_context_for_prompt(ctx)
    print(f"         Context: {len(context_text)} chars from {len(ctx)} files")

    # 2. Deep Research
    print(f"  [2/4] Calling Deep Research ({DR_MODEL})...")
    t0 = time.time()
    try:
        dr_report = call_deep_research(api_key, base_url, context_text, task_name)
    except Exception as e:
        print(f"  ERROR in Deep Research: {e}", file=sys.stderr)
        traceback.print_exc()
        return False
    dt = time.time() - t0
    print(f"         Report: {len(dr_report)} chars in {dt:.0f}s")

    # Save report for reference
    if save_report:
        report_dir = task_dir / "environment" / "dr_report"
        report_dir.mkdir(exist_ok=True)
        (report_dir / f"{task_name}_report.md").write_text(
            f"# Deep Research Report: {task_name}\n"
            f"- Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
            f"- Model: {DR_MODEL}\n\n---\n\n{dr_report}\n",
            encoding="utf-8",
        )

    # 3. Generate skills
    print(f"  [3/4] Generating skills ({SKILL_MODEL})...")
    t0 = time.time()
    try:
        skills = call_skill_generation(api_key, base_url, context_text, dr_report, task_name)
    except Exception as e:
        print(f"  ERROR in skill generation: {e}", file=sys.stderr)
        traceback.print_exc()
        return False
    dt = time.time() - t0
    print(f"         Generated {len(skills)} skills in {dt:.0f}s")

    # 4. Write skills
    print(f"  [4/4] Writing skills...")
    # Clear existing skills first
    skills_dir = task_dir / "environment" / "skills"
    if skills_dir.exists():
        for child in skills_dir.iterdir():
            if child.is_dir():
                shutil.rmtree(child)
            else:
                child.unlink()

    written = write_skills(task_dir, skills)
    print(f"         Written: {', '.join(written) if written else '(none)'}")

    # 5. Patch Dockerfile
    patched = patch_dockerfile(task_dir)
    if patched:
        print(f"         Dockerfile patched with COPY skills")

    print(f"  DONE: {task_name} ({len(written)} skills)")
    return True


# ═══════════════════════════════════════════════════════════════════════════
#  Batch processing
# ═══════════════════════════════════════════════════════════════════════════

def copy_tasks_no_skills(src: Path, dst: Path) -> int:
    """Copy tasks-no-skills to tasks_to_test, clearing existing skills content."""
    if dst.exists():
        print(f"  Removing existing {dst}...")
        shutil.rmtree(dst)

    print(f"  Copying {src} → {dst}...")
    shutil.copytree(src, dst)

    # Clear skills content in all tasks
    count = 0
    for task_dir in sorted(dst.iterdir()):
        if not task_dir.is_dir():
            continue
        skills_dir = task_dir / "environment" / "skills"
        if skills_dir.exists():
            for child in skills_dir.iterdir():
                if child.is_dir():
                    shutil.rmtree(child)
                else:
                    child.unlink()
        count += 1

    return count


def batch_process(tasks_root: Path, api_key: str, base_url: str, resume_from: str | None = None) -> None:
    """Process all tasks in a directory."""
    task_dirs = sorted(
        d for d in tasks_root.iterdir()
        if d.is_dir() and (d / "instruction.md").exists()
    )

    if resume_from:
        # Skip tasks until we find the resume point
        idx = next((i for i, d in enumerate(task_dirs) if d.name == resume_from), 0)
        task_dirs = task_dirs[idx:]
        print(f"Resuming from task: {resume_from} ({len(task_dirs)} remaining)")

    total = len(task_dirs)
    success = 0
    failed = []

    print(f"\nBatch processing {total} tasks")
    print(f"  Deep Research model: {DR_MODEL}")
    print(f"  Skill gen model: {SKILL_MODEL}")
    print(f"  API base URL: {base_url}")

    for i, task_dir in enumerate(task_dirs, 1):
        print(f"\n[{i}/{total}] ", end="")
        try:
            ok = process_task(task_dir, api_key, base_url)
            if ok:
                success += 1
            else:
                failed.append(task_dir.name)
        except Exception as e:
            print(f"  FATAL ERROR: {e}", file=sys.stderr)
            traceback.print_exc()
            failed.append(task_dir.name)

        # Rate limiting between tasks
        if i < total:
            time.sleep(5)

    print(f"\n{'='*60}")
    print(f"  BATCH COMPLETE: {success}/{total} succeeded")
    if failed:
        print(f"  Failed: {', '.join(failed)}")
    print(f"{'='*60}")


# ═══════════════════════════════════════════════════════════════════════════
#  CLI
# ═══════════════════════════════════════════════════════════════════════════

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="DRskill: Deep Research → Skill Generator")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("task_dir", nargs="?", type=Path, help="Single task directory to process")
    group.add_argument("--batch", type=Path, help="Process all tasks in directory")
    group.add_argument(
        "--init",
        type=Path,
        metavar="SRC",
        help="Copy tasks-no-skills to tasks_to_test and clear skills",
    )

    parser.add_argument("--output-dir", type=Path, help="Output to a different task directory")
    parser.add_argument("--resume-from", type=str, help="Resume batch from this task name")
    parser.add_argument("--base-url", default=os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1"))
    parser.add_argument("--no-report", action="store_true", help="Don't save deep research report")
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key and not args.init:
        print("Error: OPENAI_API_KEY not set", file=sys.stderr)
        return 1

    if args.init:
        # Just copy and prepare
        dst = args.init.parent / "tasks_to_test"
        count = copy_tasks_no_skills(args.init, dst)
        print(f"  Initialized {count} tasks in {dst}")
        return 0

    if args.batch:
        batch_process(args.batch, api_key, args.base_url, args.resume_from)
        return 0

    # Single task
    task_dir = args.task_dir
    if args.output_dir:
        # Copy task to output dir first
        dst = args.output_dir / task_dir.name
        if not dst.exists():
            shutil.copytree(task_dir, dst)
        task_dir = dst

    ok = process_task(task_dir, api_key, args.base_url, save_report=not args.no_report)
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
