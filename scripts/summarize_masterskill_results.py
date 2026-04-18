#!/usr/bin/env python3
"""Summarize persisted MasterSkill benchmark latest snapshots."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Summarize MasterSkill benchmark results from benchmark_runs/latest/*.json"
    )
    parser.add_argument(
        "--data-root",
        required=True,
        help="MasterSkill data root containing benchmark_runs/latest/",
    )
    parser.add_argument(
        "--show-tasks",
        action="store_true",
        help="Print a per-task table after the aggregate summary.",
    )
    return parser.parse_args()


def load_records(latest_dir: Path) -> list[dict]:
    records: list[dict] = []
    for path in sorted(latest_dir.glob("*.json")):
        try:
            data = json.loads(path.read_text())
        except Exception:
            continue
        data["_path"] = str(path)
        records.append(data)
    return records


def effective_total_tokens(record: dict) -> int:
    events = record.get("events") or []
    best = 0
    for event in events:
        value = event.get("effective_total_tokens")
        if isinstance(value, int):
            best = max(best, value)
            continue
        input_tokens = int(event.get("input_tokens", 0) or 0)
        cached_input_tokens = int(event.get("cached_input_tokens", 0) or 0)
        output_tokens = int(event.get("output_tokens", 0) or 0)
        best = max(best, max(input_tokens - cached_input_tokens, 0) + output_tokens)
    return best


def summarize(records: list[dict], data_root: str) -> str:
    total = len(records)
    status_counts = Counter(str(r.get("status", "") or "unknown") for r in records)
    failure_counts = Counter(
        str(r.get("failure_class", "") or "none") for r in records if str(r.get("status", "")) != "solved"
    )

    solved = [r for r in records if r.get("status") == "solved"]
    abandoned = [r for r in records if r.get("status") != "solved"]

    solved_durations = [float(r.get("duration_seconds", 0.0) or 0.0) for r in solved]
    solved_effective_tokens = [effective_total_tokens(r) for r in solved]

    lines = [
        f"data_root: {data_root}",
        f"latest_records: {total}",
        f"solved: {status_counts.get('solved', 0)}",
        f"abandoned: {status_counts.get('abandoned', 0)}",
    ]

    if total:
        solve_rate = status_counts.get("solved", 0) / total * 100.0
        lines.append(f"solve_rate: {solve_rate:.1f}%")

    if solved_durations:
        avg_duration = sum(solved_durations) / len(solved_durations)
        median_duration = sorted(solved_durations)[len(solved_durations) // 2]
        lines.append(f"solved_avg_duration_sec: {avg_duration:.2f}")
        lines.append(f"solved_median_duration_sec: {median_duration:.2f}")

    if solved_effective_tokens:
        avg_tokens = sum(solved_effective_tokens) / len(solved_effective_tokens)
        median_tokens = sorted(solved_effective_tokens)[len(solved_effective_tokens) // 2]
        lines.append(f"solved_avg_effective_total_tokens: {avg_tokens:.0f}")
        lines.append(f"solved_median_effective_total_tokens: {median_tokens}")

    if failure_counts:
        lines.append("failure_classes:")
        for failure_class, count in failure_counts.most_common():
            lines.append(f"  {failure_class}: {count}")

    return "\n".join(lines)


def task_table(records: list[dict]) -> str:
    header = "task_id\tstatus\tfailure_class\tduration_sec\teffective_total_tokens\tfinal_model"
    lines = [header]
    for record in sorted(records, key=lambda r: r.get("task_id", "")):
        lines.append(
            "\t".join(
                [
                    str(record.get("task_id", "")),
                    str(record.get("status", "")),
                    str(record.get("failure_class", "")),
                    f"{float(record.get('duration_seconds', 0.0) or 0.0):.2f}",
                    str(effective_total_tokens(record)),
                    str(record.get("final_model", "")),
                ]
            )
        )
    return "\n".join(lines)


if __name__ == "__main__":
    args = parse_args()
    latest_dir = Path(args.data_root) / "benchmark_runs" / "latest"
    if not latest_dir.exists():
        raise SystemExit(f"missing latest directory: {latest_dir}")

    records = load_records(latest_dir)
    print(summarize(records, args.data_root))
    if args.show_tasks and records:
        print()
        print(task_table(records))
