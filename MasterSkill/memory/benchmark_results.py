"""Persistence for benchmark task-run results."""

import json
from dataclasses import asdict
from enum import Enum
from pathlib import Path

from ..core.types import BenchmarkRunRecord


class BenchmarkResultStore:
    """Stores compact task-run records for later analysis."""

    def __init__(self, data_dir: str):
        self.data_dir = Path(data_dir)
        self.latest_dir = self.data_dir / "latest"
        self.tasks_dir = self.data_dir / "tasks"
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.latest_dir.mkdir(parents=True, exist_ok=True)
        self.tasks_dir.mkdir(parents=True, exist_ok=True)
        self.all_runs_path = self.data_dir / "runs.jsonl"

    def save(self, record: BenchmarkRunRecord) -> None:
        """Append a run record and refresh the latest snapshot for that task."""
        payload = self._to_jsonable(record)
        with self.all_runs_path.open("a") as handle:
            handle.write(json.dumps(payload) + "\n")

        task_runs_path = self.tasks_dir / f"{record.task_id}.jsonl"
        with task_runs_path.open("a") as handle:
            handle.write(json.dumps(payload) + "\n")

        latest_path = self.latest_dir / f"{record.task_id}.json"
        latest_path.write_text(json.dumps(payload, indent=2))

    def save_latest(self, record: BenchmarkRunRecord) -> None:
        """Refresh only the latest snapshot for checkpointing in long runs."""
        payload = self._to_jsonable(record)
        latest_path = self.latest_dir / f"{record.task_id}.json"
        latest_path.write_text(json.dumps(payload, indent=2))

    def _to_jsonable(self, record: BenchmarkRunRecord) -> dict:
        """Convert dataclasses and enums into JSON-safe primitives."""
        payload = self._normalize(asdict(record))
        for event in payload.get("events", []):
            input_tokens = self._as_int(event.get("input_tokens", 0))
            cached_input_tokens = self._as_int(event.get("cached_input_tokens", 0))
            output_tokens = self._as_int(event.get("output_tokens", 0))
            effective_input_tokens = max(input_tokens - cached_input_tokens, 0)
            event["effective_input_tokens"] = effective_input_tokens
            event["effective_total_tokens"] = effective_input_tokens + output_tokens
        return payload

    def _normalize(self, value):
        if isinstance(value, Enum):
            return value.value
        if isinstance(value, dict):
            return {k: self._normalize(v) for k, v in value.items()}
        if isinstance(value, list):
            return [self._normalize(v) for v in value]
        return value

    def _as_int(self, value) -> int:
        try:
            return int(value or 0)
        except (TypeError, ValueError):
            return 0
