#!/usr/bin/env python3
"""Compare two MasterSkill benchmark result roots via latest snapshots."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Compare two MasterSkill data roots using benchmark_runs/latest/*.json"
    )
    parser.add_argument("--left-root", required=True, help="First data root, e.g. baseline")
    parser.add_argument("--right-root", required=True, help="Second data root, e.g. current/evolved")
    parser.add_argument("--left-label", default="left", help="Display label for the first root")
    parser.add_argument("--right-label", default="right", help="Display label for the second root")
    parser.add_argument("--show-tasks", action="store_true", help="Print a per-task comparison table.")
    return parser.parse_args()


def load_latest(data_root: str) -> dict[str, dict]:
    latest_dir = Path(data_root) / "benchmark_runs" / "latest"
    records: dict[str, dict] = {}
    if not latest_dir.exists():
        return records
    for path in sorted(latest_dir.glob("*.json")):
        try:
            data = json.loads(path.read_text())
        except Exception:
            continue
        task_id = str(data.get("task_id", "") or path.stem)
        records[task_id] = data
    return records


def effective_total_tokens(record: dict) -> int:
    best = 0
    for event in record.get("events") or []:
        value = event.get("effective_total_tokens")
        if isinstance(value, int):
            best = max(best, value)
            continue
        input_tokens = int(event.get("input_tokens", 0) or 0)
        cached_input_tokens = int(event.get("cached_input_tokens", 0) or 0)
        output_tokens = int(event.get("output_tokens", 0) or 0)
        best = max(best, max(input_tokens - cached_input_tokens, 0) + output_tokens)
    return best


def summarize_pair(left: dict, right: dict, left_label: str, right_label: str) -> tuple[list[str], list[str]]:
    task_ids = sorted(set(left) | set(right))

    left_solved = 0
    right_solved = 0
    solve_gains: list[str] = []
    solve_losses: list[str] = []
    runtime_win = 0
    token_win = 0
    common_solved = 0

    per_task_rows: list[str] = []
    for task_id in task_ids:
        left_record = left.get(task_id, {})
        right_record = right.get(task_id, {})
        left_status = str(left_record.get("status", "missing"))
        right_status = str(right_record.get("status", "missing"))
        if left_status == "solved":
            left_solved += 1
        if right_status == "solved":
            right_solved += 1
        if left_status != "solved" and right_status == "solved":
            solve_gains.append(task_id)
        if left_status == "solved" and right_status != "solved":
            solve_losses.append(task_id)

        left_duration = float(left_record.get("duration_seconds", 0.0) or 0.0)
        right_duration = float(right_record.get("duration_seconds", 0.0) or 0.0)
        left_tokens = effective_total_tokens(left_record)
        right_tokens = effective_total_tokens(right_record)

        if left_status == "solved" and right_status == "solved":
            common_solved += 1
            if right_duration < left_duration:
                runtime_win += 1
            if right_tokens < left_tokens:
                token_win += 1

        per_task_rows.append(
            "\t".join(
                [
                    task_id,
                    left_status,
                    right_status,
                    f"{left_duration:.2f}",
                    f"{right_duration:.2f}",
                    str(left_tokens),
                    str(right_tokens),
                    str(left_record.get("failure_class", "")),
                    str(right_record.get("failure_class", "")),
                ]
            )
        )

    summary = [
        f"tasks_compared: {len(task_ids)}",
        f"{left_label}_solved: {left_solved}",
        f"{right_label}_solved: {right_solved}",
        f"solve_gains_for_{right_label}: {len(solve_gains)}",
        f"solve_losses_for_{right_label}: {len(solve_losses)}",
        f"common_solved: {common_solved}",
        f"{right_label}_faster_on_common_solved: {runtime_win}",
        f"{right_label}_lower_effective_tokens_on_common_solved: {token_win}",
    ]

    if solve_gains:
        summary.append(f"{right_label}_solve_gains: {', '.join(solve_gains)}")
    if solve_losses:
        summary.append(f"{right_label}_solve_losses: {', '.join(solve_losses)}")

    return summary, per_task_rows


if __name__ == "__main__":
    args = parse_args()
    left = load_latest(args.left_root)
    right = load_latest(args.right_root)
    summary, rows = summarize_pair(left, right, args.left_label, args.right_label)
    print("\n".join(summary))
    if args.show_tasks:
        print()
        print(
            "task_id\t"
            f"{args.left_label}_status\t{args.right_label}_status\t"
            f"{args.left_label}_duration_sec\t{args.right_label}_duration_sec\t"
            f"{args.left_label}_effective_tokens\t{args.right_label}_effective_tokens\t"
            f"{args.left_label}_failure_class\t{args.right_label}_failure_class"
        )
        print("\n".join(rows))
