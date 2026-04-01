#!/usr/bin/env python3
"""Generate a research report from a task markdown via OpenAI-compatible API."""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Any
from urllib import error, request

DEFAULT_MODEL = "claude-opus-4-6"
DEFAULT_TIMEOUT = 600
DEFAULT_API_MODE = "chat"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Read a markdown task file, call a research model, and write "
            "<task_name>_report.md"
        )
    )
    parser.add_argument(
        "task_file",
        type=Path,
        help="Path to the markdown task file.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path.cwd(),
        help="Output directory for report files (default: current directory).",
    )
    parser.add_argument(
        "--model",
        default=DEFAULT_MODEL,
        help=f"Model name to call (default: {DEFAULT_MODEL}).",
    )
    parser.add_argument(
        "--base-url",
        default=os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1"),
        help=(
            "OpenAI-compatible API base URL (default: OPENAI_BASE_URL env or "
            "https://api.openai.com/v1)."
        ),
    )
    parser.add_argument(
        "--temperature",
        type=float,
        default=0.2,
        help="Sampling temperature (default: 0.2).",
    )
    parser.add_argument(
        "--max-tokens",
        type=int,
        default=4000,
        help="Max completion tokens for chat API (default: 4000).",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=DEFAULT_TIMEOUT,
        help=f"HTTP timeout in seconds (default: {DEFAULT_TIMEOUT}).",
    )
    parser.add_argument(
        "--api-mode",
        choices=["chat", "responses"],
        default=DEFAULT_API_MODE,
        help=f"API mode to use (default: {DEFAULT_API_MODE}).",
    )
    parser.add_argument(
        "--report-task-name",
        default=None,
        help="Override filename prefix. Output will be <report_task_name>_report.md.",
    )
    return parser.parse_args()


def slugify_task_name(name: str) -> str:
    cleaned = re.sub(r"\s+", "_", name.strip())
    cleaned = re.sub(r"[^\w\-]", "_", cleaned)
    cleaned = re.sub(r"_+", "_", cleaned).strip("_")
    return cleaned or "task"


def resolve_report_task_name(task_file: Path, report_task_name: str | None) -> str:
    if report_task_name:
        return slugify_task_name(report_task_name)
    if task_file.stem.lower() in {"instruction", "intruction"}:
        return slugify_task_name(task_file.parent.name)
    return slugify_task_name(task_file.stem)


def normalize_base_url(base_url: str) -> str:
    base = base_url.rstrip("/")
    return base if base.endswith("/v1") else f"{base}/v1"


def read_task(task_file: Path) -> str:
    if not task_file.exists():
        raise FileNotFoundError(f"Task file not found: {task_file}")
    if task_file.suffix.lower() not in {".md", ".markdown"}:
        raise ValueError("Task file must be markdown (.md/.markdown).")
    content = task_file.read_text(encoding="utf-8").strip()
    if not content:
        raise ValueError("Task file is empty.")
    return content


def build_prompts(task_text: str) -> tuple[str, str]:
    system_prompt = (
        "你是一位资深技术研究员。请围绕用户任务执行网络检索并综合分析，"
        "输出结构化、可执行、带来源的中文 markdown 报告。"
    )
    user_prompt = (
        "你是一位具备多学科交叉研究能力的高级技术顾问。基于下面的任务描述，执行系统化的深度技术检索，"
        "并生成一份可直接指导实施的结构化中文报告。\n\n"
        "## 检索策略要求\n\n"
        "**第一层：精确检索**\n"
        "- 搜索该任务涉及的核心算法、协议、标准文档（RFC、IEEE、ISO 等）\n"
        "- 查找官方文档中的 API 签名、函数参数、返回值规范\n"
        "- 定位权威教材或综述论文中对该问题的标准解法\n\n"
        "**第二层：领域专家级检索**\n"
        "- 查找该领域公认的阈值、参数经验值和校准基准（如信号处理中的 SNR 阈值、"
        "ML 中的学习率范围、网络协议中的超时参数等）\n"
        "- 检索 benchmark 数据集上的 baseline 性能指标，作为结果校验参考\n"
        "- 搜索领域专家的 best practice、production-ready 配置和调优指南\n\n"
        "**第三层：边界条件与故障模式检索**\n"
        "- 搜索该技术方案在极端输入、大规模数据、高并发等边界条件下的已知问题\n"
        "- 查找相关的 CVE、已知 bug、兼容性问题、平台差异\n"
        "- 检索社区中该方案的常见失败模式和 debug 经验（Stack Overflow、GitHub Issues）\n\n"
        "## 报告结构要求\n\n"
        "### 1. 标题\n"
        "用一句话概括任务的技术本质。\n\n"
        "### 2. 任务重述与问题分解\n"
        "- 用你自己的话重述任务目标\n"
        "- 将任务分解为 2-5 个可独立解决的子问题\n"
        "- 标注每个子问题的技术领域归属（如：信号处理、图论、系统编程等）\n\n"
        "### 3. 核心技术方案（3-8 条）\n"
        "每条方案必须包含：\n"
        "- 具体的算法/工具/库名称及版本\n"
        "- 关键参数的推荐值及其来源依据（论文、文档、实验）\n"
        "- 时间复杂度与空间复杂度\n"
        "- 适用条件与不适用场景\n\n"
        "### 4. 领域特定阈值与参数校准表\n"
        "以表格形式列出：\n"
        "| 参数名 | 推荐值/范围 | 来源 | 适用条件 | 超出范围的后果 |\n"
        "对每个关键参数给出：默认值、保守值、激进值三档。\n\n"
        "### 5. 边界条件与鲁棒性分析\n"
        "- 输入为空、极大、极小、含异常值时的预期行为\n"
        "- 浮点精度、整数溢出、编码问题等技术陷阱\n"
        "- 并发安全、内存限制、超时风险\n"
        "- 跨平台/跨版本兼容性问题\n\n"
        "### 6. 关键证据与来源\n"
        "- 每条关键结论标注证据强度：[强] 来自官方文档/权威论文，[中] 来自社区共识/经验，[弱] 来自个别案例\n"
        "- 给出可访问的链接\n"
        "- 明确区分：已验证的事实 vs 合理推断 vs 未经验证的假设\n\n"
        "### 7. 实施路径与验证方案\n"
        "- 给出推荐的实施顺序（先做什么、后做什么）\n"
        "- 每个步骤的验证方法（如何确认该步骤正确完成）\n"
        "- 预期的中间产物和最终产物\n\n"
        "### 8. 风险矩阵\n"
        "| 风险项 | 概率 | 影响 | 缓解措施 |\n"
        "重点关注：数据质量风险、依赖库版本风险、性能瓶颈风险。\n\n"
        "### 9. 备选方案与降级策略\n"
        "- 如果首选方案失败，退而求其次的方案是什么\n"
        "- 最小可行方案（MVP）：用最简单的方式先跑通\n\n"
        "---\n"
        "任务描述如下：\n\n"
        f"{task_text}"
    )
    return system_prompt, user_prompt


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


def call_chat_completions(
    api_key: str,
    base_url: str,
    model: str,
    system_prompt: str,
    user_prompt: str,
    temperature: float,
    max_tokens: int,
    timeout: int,
) -> dict[str, Any]:
    url = f"{normalize_base_url(base_url)}/chat/completions"
    payload = {
        "model": model,
        "temperature": temperature,
        "max_tokens": max_tokens,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
    }
    return http_post_json(url=url, api_key=api_key, payload=payload, timeout=timeout)


def call_responses_api(
    api_key: str,
    base_url: str,
    model: str,
    system_prompt: str,
    user_prompt: str,
    temperature: float,
    timeout: int,
) -> dict[str, Any]:
    url = f"{normalize_base_url(base_url)}/responses"
    payload = {
        "model": model,
        "temperature": temperature,
        "input": [
            {
                "role": "system",
                "content": [{"type": "input_text", "text": system_prompt}],
            },
            {
                "role": "user",
                "content": [{"type": "input_text", "text": user_prompt}],
            },
        ],
    }
    return http_post_json(url=url, api_key=api_key, payload=payload, timeout=timeout)


def extract_text(response_json: dict[str, Any]) -> str:
    output_text = response_json.get("output_text")
    if isinstance(output_text, str) and output_text.strip():
        return output_text.strip()

    output = response_json.get("output")
    if isinstance(output, list):
        parts: list[str] = []
        for item in output:
            if not isinstance(item, dict):
                continue
            content = item.get("content")
            if not isinstance(content, list):
                continue
            for chunk in content:
                if isinstance(chunk, dict):
                    text = chunk.get("text")
                    if isinstance(text, str) and text.strip():
                        parts.append(text.strip())
        if parts:
            return "\n\n".join(parts).strip()

    try:
        message = response_json["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError) as e:
        raise RuntimeError(
            "Unexpected response structure; cannot find model text content."
        ) from e

    if isinstance(message, str):
        text = message.strip()
    elif isinstance(message, list):
        parts = []
        for item in message:
            if isinstance(item, dict) and item.get("type") == "text":
                maybe_text = item.get("text")
                if isinstance(maybe_text, str) and maybe_text.strip():
                    parts.append(maybe_text.strip())
        text = "\n\n".join(parts).strip()
    else:
        raise RuntimeError("Unsupported message content type in response.")

    if not text:
        raise RuntimeError("Model returned empty content.")
    return text


def write_report(
    output_dir: Path,
    task_file: Path,
    report_text: str,
    model: str,
    report_task_name: str | None,
) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    task_name = resolve_report_task_name(task_file, report_task_name)
    output_path = output_dir / f"{task_name}_report.md"

    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    header = (
        f"# {task_name} Report\n\n"
        f"- 生成时间: {now}\n"
        f"- 模型: `{model}`\n"
        f"- 任务文件: `{task_file}`\n\n"
        "---\n\n"
    )
    output_path.write_text(header + report_text + "\n", encoding="utf-8")
    return output_path


def main() -> int:
    args = parse_args()
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("Error: OPENAI_API_KEY is not set.", file=sys.stderr)
        return 1

    try:
        task_text = read_task(args.task_file)
        system_prompt, user_prompt = build_prompts(task_text)
        if args.api_mode == "responses":
            response_json = call_responses_api(
                api_key=api_key,
                base_url=args.base_url,
                model=args.model,
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                temperature=args.temperature,
                timeout=args.timeout,
            )
        else:
            response_json = call_chat_completions(
                api_key=api_key,
                base_url=args.base_url,
                model=args.model,
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                temperature=args.temperature,
                max_tokens=args.max_tokens,
                timeout=args.timeout,
            )
        report_text = extract_text(response_json)
        output_path = write_report(
            output_dir=args.output_dir,
            task_file=args.task_file,
            report_text=report_text,
            model=args.model,
            report_task_name=args.report_task_name,
        )
    except Exception as exc:  # noqa: BLE001
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    print(f"Report generated: {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
