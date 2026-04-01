#!/usr/bin/env python3
"""Compare task reports against task skills and generate a methodology summary."""

from __future__ import annotations

import argparse
import json
import os
import re
import statistics
import sys
import time
from collections import Counter
from pathlib import Path
from typing import Any
from urllib import error, request

TEXT_FILE_EXTS = {".md", ".markdown", ".txt", ".yaml", ".yml", ".json"}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Compare *_report.md files with corresponding task skills and output "
            "per-task analyses plus a final methodology markdown summary."
        )
    )
    parser.add_argument(
        "--report-dir",
        type=Path,
        default=Path("DeepResearch/Opus-4-6/Report"),
        help="Directory containing *_report.md files.",
    )
    parser.add_argument(
        "--tasks-root",
        type=Path,
        default=Path("skillsbench/tasks"),
        help="Root directory of tasks.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("DeepResearch/Opus-4-6/ReportSkillCompare"),
        help="Output directory for per-task analyses and summary.",
    )
    parser.add_argument(
        "--model",
        default="claude-sonnet-4-6-cc",
        help="Model name for analysis.",
    )
    parser.add_argument(
        "--base-url",
        default=os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1"),
        help="OpenAI-compatible API base URL.",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=600,
        help="HTTP timeout (seconds).",
    )
    parser.add_argument(
        "--max-report-chars",
        type=int,
        default=120000,
        help="Max report characters passed to the model.",
    )
    parser.add_argument(
        "--max-skill-chars",
        type=int,
        default=90000,
        help="Max combined skill characters passed to the model.",
    )
    parser.add_argument(
        "--retries",
        type=int,
        default=2,
        help="Retry count for model call failures.",
    )
    parser.add_argument(
        "--sleep",
        type=float,
        default=0.5,
        help="Sleep seconds between tasks to reduce burst rate.",
    )
    return parser.parse_args()


def normalize_base_url(base_url: str) -> str:
    base = base_url.rstrip("/")
    return base if base.endswith("/v1") else f"{base}/v1"


def http_post_json(
    url: str, api_key: str, payload: dict[str, Any], timeout: int
) -> dict[str, Any]:
    data = json.dumps(payload).encode("utf-8")
    req = request.Request(
        url,
        data=data,
        method="POST",
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
        raise RuntimeError(f"API HTTP error {e.code}: {body}") from e
    except error.URLError as e:
        raise RuntimeError(f"API network error: {e}") from e

    try:
        return json.loads(raw)
    except json.JSONDecodeError as e:
        raise RuntimeError(f"Invalid JSON response: {raw[:500]}") from e


def call_model(
    api_key: str,
    base_url: str,
    model: str,
    system_prompt: str,
    user_prompt: str,
    timeout: int,
) -> str:
    url = f"{normalize_base_url(base_url)}/chat/completions"
    payload = {
        "model": model,
        "temperature": 0.1,
        "max_tokens": 3500,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
    }
    response = http_post_json(url=url, api_key=api_key, payload=payload, timeout=timeout)
    try:
        content = response["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError) as e:
        raise RuntimeError("Unexpected chat response format.") from e
    if not isinstance(content, str):
        raise RuntimeError("Model content is not a string.")
    return content.strip()


def normalize_name(name: str) -> str:
    return re.sub(r"[^a-z0-9]", "", name.lower())


def extract_task_from_report(report_path: Path) -> str:
    name = report_path.name
    if not name.endswith("_report.md"):
        return report_path.stem
    return name[: -len("_report.md")]


def resolve_task_dir(task_name: str, tasks_root: Path) -> tuple[Path | None, str]:
    direct = tasks_root / task_name
    if (direct / "environment" / "skills").is_dir():
        return direct, "direct"

    candidates = []
    for d in tasks_root.iterdir():
        if d.is_dir() and (d / "environment" / "skills").is_dir():
            candidates.append(d)

    name_norm = normalize_name(task_name)
    for d in candidates:
        if normalize_name(d.name) == name_norm:
            return d, "normalized_exact"

    prefix = [d for d in candidates if normalize_name(d.name).startswith(name_norm)]
    if len(prefix) == 1:
        return prefix[0], "normalized_prefix"

    contains = [d for d in candidates if name_norm in normalize_name(d.name)]
    if len(contains) == 1:
        return contains[0], "normalized_contains"

    return None, "unresolved"


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="ignore")


def collect_skill_text(skill_root: Path, max_chars: int) -> tuple[str, list[Path]]:
    files: list[Path] = []
    skill_md_files = sorted(skill_root.rglob("SKILL.md"))
    files.extend(skill_md_files)
    extra_md = sorted(
        p
        for p in skill_root.rglob("*")
        if p.is_file()
        and p.suffix.lower() in TEXT_FILE_EXTS
        and p.name != "SKILL.md"
    )
    files.extend(extra_md)

    seen: set[Path] = set()
    blocks: list[str] = []
    kept_files: list[Path] = []
    total = 0
    for path in files:
        if path in seen:
            continue
        seen.add(path)
        try:
            txt = read_text(path).strip()
        except Exception:
            continue
        if not txt:
            continue
        block = f"\n\n### FILE: {path}\n\n{txt}"
        if total + len(block) > max_chars:
            remain = max_chars - total
            if remain > 600:
                blocks.append(block[:remain] + "\n\n[TRUNCATED]")
                kept_files.append(path)
            break
        blocks.append(block)
        kept_files.append(path)
        total += len(block)
    return "".join(blocks).strip(), kept_files


def extract_json_object(text: str) -> dict[str, Any]:
    stripped = text.strip()
    if stripped.startswith("{") and stripped.endswith("}"):
        return json.loads(stripped)

    match = re.search(r"\{.*\}", stripped, flags=re.S)
    if not match:
        raise ValueError("No JSON object found in model output.")
    return json.loads(match.group(0))


def analyze_one_task(
    api_key: str,
    args: argparse.Namespace,
    report_file: Path,
    task_dir: Path,
) -> tuple[dict[str, Any], str]:
    report_task = extract_task_from_report(report_file)
    report_text = read_text(report_file)[: args.max_report_chars]
    skill_root = task_dir / "environment" / "skills"
    skill_text, used_skill_files = collect_skill_text(skill_root, args.max_skill_chars)
    if not skill_text:
        raise RuntimeError(f"No readable skill text under {skill_root}")

    system_prompt = (
        "你是严格的技术审稿员。请只基于输入内容判断，不要编造。"
        "重点评估知识覆盖、知识冲突、以及有效知识占比。"
        "输出必须是合法 JSON。"
    )
    user_prompt = f"""
请比较“任务报告”和“任务技能文档（skills）”，并判断报告是否覆盖了完成 skills 所需的知识。

评估标准（优先级从高到低）：
1) 报告是否包含 skills 落地需要的关键知识：算法/方法、阈值参数、工具命令、验证手段、故障排查、边界条件。
2) 是否存在知识冲突/矛盾：报告给出的做法与 skill 的要求相反或不兼容。
3) 有效知识占比：报告内容中真正支持 skill 落地的比例（0~1）。

请输出一个 JSON 对象，字段必须严格如下：
{{
  "task": "{report_task}",
  "task_dir": "{task_dir}",
  "coverage_score": 0,
  "useful_knowledge_ratio": 0.0,
  "conflict_exists": false,
  "conflict_severity": "none",
  "present_key_knowledge": ["..."],
  "missing_key_knowledge": ["..."],
  "conflicting_points": [
    {{"report_point":"...", "skill_point":"...", "why_conflict":"..."}}
  ],
  "effective_knowledge_points": ["..."],
  "redundant_or_unreliable_points": ["..."],
  "overall_judgement": "...",
  "evidence_quality_note": "说明你判断依据在输入中是否充分"
}}

说明：
- coverage_score 范围 0~100，表示“覆盖了 skill 所需知识”的完整度。
- useful_knowledge_ratio 范围 0~1，表示报告内容中“有效支撑 skill 实施”的占比。
- conflict_severity 只允许: none/minor/major。
- 如果没有冲突，conflicting_points 返回空数组。
- missing/present 列表请写“具体知识项”，而非抽象词。

下面是输入：

## Report ({report_file})
{report_text}

## Skill Docs (from {skill_root})
{skill_text}
"""

    last_err: Exception | None = None
    for i in range(args.retries + 1):
        try:
            raw = call_model(
                api_key=api_key,
                base_url=args.base_url,
                model=args.model,
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                timeout=args.timeout,
            )
            data = extract_json_object(raw)
            data["_used_skill_files"] = [str(p) for p in used_skill_files]
            data["_report_file"] = str(report_file)
            return data, raw
        except Exception as e:  # noqa: BLE001
            last_err = e
            if i < args.retries:
                time.sleep(1.5)
                continue
    raise RuntimeError(f"Failed on {report_file}: {last_err}")


def bucket_score(score: float) -> str:
    if score >= 80:
        return "high(>=80)"
    if score >= 60:
        return "mid(60-79)"
    return "low(<60)"


def category_from_missing(item: str) -> str:
    s = item.lower()
    rules = [
        ("参数与阈值", ["阈值", "参数", "超时", "学习率", "窗口", "精度", "temperature"]),
        ("工具与命令", ["命令", "cli", "uv", "docker", "bash", "script", "workflow"]),
        ("验证与评测", ["验证", "测试", "benchmark", "评估", "指标", "回归"]),
        ("边界与鲁棒性", ["边界", "异常", "极端", "鲁棒", "容错", "故障"]),
        ("兼容与版本", ["版本", "兼容", "依赖", "api", "协议"]),
        ("数据与前处理", ["数据", "清洗", "格式", "schema", "编码", "缺失值"]),
        ("算法与方法", ["算法", "方法", "模型", "策略", "推断", "优化"]),
    ]
    for cat, kws in rules:
        if any(k in s for k in kws):
            return cat
    return "其他"


def render_task_markdown(item: dict[str, Any]) -> str:
    task = str(item.get("task", "unknown"))
    coverage = item.get("coverage_score", "N/A")
    ratio = item.get("useful_knowledge_ratio", "N/A")
    conflict_exists = item.get("conflict_exists", False)
    conflict_sev = item.get("conflict_severity", "none")

    present = item.get("present_key_knowledge", []) or []
    missing = item.get("missing_key_knowledge", []) or []
    conflicts = item.get("conflicting_points", []) or []
    effective = item.get("effective_knowledge_points", []) or []
    redundant = item.get("redundant_or_unreliable_points", []) or []

    lines = [
        f"# {task} 对比分析",
        "",
        f"- coverage_score: **{coverage}**",
        f"- useful_knowledge_ratio: **{ratio}**",
        f"- conflict_exists: **{conflict_exists}**",
        f"- conflict_severity: **{conflict_sev}**",
        "",
        "## 关键结论",
        str(item.get("overall_judgement", "")),
        "",
        "## 已覆盖的关键知识",
    ]
    lines.extend(f"- {x}" for x in present[:12])
    lines.extend(["", "## 缺失的关键知识"])
    lines.extend(f"- {x}" for x in missing[:12])
    lines.extend(["", "## 冲突点"])
    if conflicts:
        for c in conflicts[:8]:
            if isinstance(c, dict):
                rp = c.get("report_point", "")
                sp = c.get("skill_point", "")
                why = c.get("why_conflict", "")
                lines.append(f"- report: {rp} | skill: {sp} | reason: {why}")
            else:
                lines.append(f"- {c}")
    else:
        lines.append("- 无")
    lines.extend(["", "## 有效知识点"])
    lines.extend(f"- {x}" for x in effective[:12])
    lines.extend(["", "## 冗余或不可靠知识点"])
    lines.extend(f"- {x}" for x in redundant[:12])
    lines.extend(["", "## 证据质量", str(item.get("evidence_quality_note", "")), ""])
    return "\n".join(lines)


def render_summary_markdown(
    all_items: list[dict[str, Any]],
    output_dir: Path,
    model_name: str,
) -> str:
    cov_scores: list[float] = []
    useful_ratios: list[float] = []
    conflict_tasks: list[str] = []
    score_buckets: Counter[str] = Counter()
    missing_counter: Counter[str] = Counter()
    missing_category_counter: Counter[str] = Counter()

    for item in all_items:
        task = str(item.get("task", "unknown"))
        score = item.get("coverage_score")
        ratio = item.get("useful_knowledge_ratio")
        if isinstance(score, (int, float)):
            cov_scores.append(float(score))
            score_buckets[bucket_score(float(score))] += 1
        if isinstance(ratio, (int, float)):
            useful_ratios.append(float(ratio))
        if item.get("conflict_exists") is True:
            conflict_tasks.append(task)

        missing = item.get("missing_key_knowledge", []) or []
        for m in missing:
            if not isinstance(m, str):
                continue
            m2 = m.strip()
            if not m2:
                continue
            missing_counter[m2] += 1
            missing_category_counter[category_from_missing(m2)] += 1

    avg_cov = statistics.mean(cov_scores) if cov_scores else 0.0
    med_cov = statistics.median(cov_scores) if cov_scores else 0.0
    avg_ratio = statistics.mean(useful_ratios) if useful_ratios else 0.0

    top_missing = missing_counter.most_common(12)
    top_categories = missing_category_counter.most_common(8)

    lines = [
        "# Report vs Skill 方法论总结",
        "",
        f"- 分析模型: `{model_name}`",
        f"- 任务总数: **{len(all_items)}**",
        f"- 平均覆盖度: **{avg_cov:.2f}/100**",
        f"- 覆盖度中位数: **{med_cov:.2f}/100**",
        f"- 平均有效知识占比: **{avg_ratio:.2f}**",
        f"- 存在冲突的任务数: **{len(conflict_tasks)}**",
        "",
        "## 覆盖度分层",
        f"- high(>=80): {score_buckets.get('high(>=80)', 0)}",
        f"- mid(60-79): {score_buckets.get('mid(60-79)', 0)}",
        f"- low(<60): {score_buckets.get('low(<60)', 0)}",
        "",
        "## 主要缺失知识类型（硬编码归类）",
    ]
    lines.extend(f"- {cat}: {count}" for cat, count in top_categories)
    lines.extend(["", "## 高频缺失知识项"])
    lines.extend(f"- {k}  (出现 {v} 次)" for k, v in top_missing)
    lines.extend(["", "## 冲突任务列表"])
    if conflict_tasks:
        lines.extend(f"- {t}" for t in conflict_tasks)
    else:
        lines.append("- 未检测到显著冲突任务")

    lines.extend(
        [
            "",
            "## 方法论建议",
            "1. 先抽取 skill 所需知识清单，再写报告。清单最少包含：方法/算法、关键参数阈值、工具命令、验证方案、故障排查、边界条件。",
            "2. 报告中每个核心结论都要绑定到 skill 可执行项，避免只有背景知识而缺少落地步骤。",
            "3. 对参数类知识采用“三档值”写法（默认/保守/激进）并标注适用条件，减少与 skill 的实施偏差。",
            "4. 单独增加“冲突检查”段，逐项核对 skill 的版本约束、依赖约束、命令约束，避免知识矛盾。",
            "5. 把验证与回归标准前置，报告需给出可复现的验收信号（命令、指标、阈值、失败判据）。",
            "6. 对低覆盖任务优先补齐高频缺失类型，通常是参数阈值、验证方法和工具命令细节。",
            "",
            "## 逐任务结果索引",
        ]
    )
    for item in all_items:
        task = str(item.get("task", "unknown"))
        score = item.get("coverage_score", "N/A")
        ratio = item.get("useful_knowledge_ratio", "N/A")
        conflict = item.get("conflict_exists", False)
        per_task_md = output_dir / "per_task" / f"{task}_comparison.md"
        lines.append(
            f"- {task}: coverage={score}, ratio={ratio}, conflict={conflict}, file=`{per_task_md}`"
        )
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    args = parse_args()
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("Error: OPENAI_API_KEY is not set.", file=sys.stderr)
        return 1

    report_dir = args.report_dir
    if not report_dir.is_dir():
        print(f"Error: report dir not found: {report_dir}", file=sys.stderr)
        return 1
    if not args.tasks_root.is_dir():
        print(f"Error: tasks root not found: {args.tasks_root}", file=sys.stderr)
        return 1

    output_dir = args.output_dir
    per_task_dir = output_dir / "per_task"
    raw_dir = output_dir / "raw_json"
    output_dir.mkdir(parents=True, exist_ok=True)
    per_task_dir.mkdir(parents=True, exist_ok=True)
    raw_dir.mkdir(parents=True, exist_ok=True)

    reports = sorted(report_dir.glob("*_report.md"))
    if not reports:
        print(f"Error: no report files in {report_dir}", file=sys.stderr)
        return 1

    all_items: list[dict[str, Any]] = []
    unresolved: list[str] = []
    failed: list[str] = []

    for idx, report_file in enumerate(reports, start=1):
        report_task = extract_task_from_report(report_file)
        task_dir, how = resolve_task_dir(report_task, args.tasks_root)
        if task_dir is None:
            unresolved.append(report_task)
            print(f"[{idx}/{len(reports)}] UNRESOLVED {report_task}")
            continue
        print(f"[{idx}/{len(reports)}] ANALYZE {report_task} -> {task_dir.name} ({how})")

        try:
            item, raw_text = analyze_one_task(
                api_key=api_key,
                args=args,
                report_file=report_file,
                task_dir=task_dir,
            )
            if not item.get("task"):
                item["task"] = report_task
            item["_resolved_task_dir"] = str(task_dir)
            item["_resolve_mode"] = how

            all_items.append(item)
            task_name = str(item.get("task", report_task))
            (raw_dir / f"{task_name}.json").write_text(
                json.dumps(item, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
            (per_task_dir / f"{task_name}_comparison.md").write_text(
                render_task_markdown(item),
                encoding="utf-8",
            )
            (per_task_dir / f"{task_name}_raw_response.txt").write_text(
                raw_text + "\n",
                encoding="utf-8",
            )
        except Exception as e:  # noqa: BLE001
            failed.append(f"{report_task}: {e}")
            print(f"[{idx}/{len(reports)}] FAIL {report_task}: {e}")
        time.sleep(args.sleep)

    summary = render_summary_markdown(all_items, output_dir=output_dir, model_name=args.model)
    if unresolved:
        summary += "\n## 未解析任务\n" + "\n".join(f"- {x}" for x in unresolved) + "\n"
    if failed:
        summary += "\n## 分析失败任务\n" + "\n".join(f"- {x}" for x in failed) + "\n"

    summary_path = output_dir / "report_vs_skill_methodology_summary.md"
    summary_path.write_text(summary, encoding="utf-8")

    print(
        "DONE "
        f"total_reports={len(reports)} analyzed={len(all_items)} "
        f"unresolved={len(unresolved)} failed={len(failed)} summary={summary_path}"
    )
    return 0 if not failed else 2


if __name__ == "__main__":
    raise SystemExit(main())
