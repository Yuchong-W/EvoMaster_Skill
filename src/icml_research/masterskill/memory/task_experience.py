"""Task experience memory: per-task experience records."""

import json
from pathlib import Path
from typing import Optional
from dataclasses import asdict

from ..core.types import TaskExperience, TaskStatus, ProblemType, TaskAttempt


class TaskExperienceMemory:
    """Middle memory layer: per-task experience.

    Stores what worked for each task and why.
    Max 2 entries per task.
    """

    def __init__(self, data_dir: str, max_entries: int = 2):
        self.data_dir = Path(data_dir)
        self.experience_file = self.data_dir / "task_experiences.json"
        self.max_entries = max_entries
        self._ensure_file()

    def _ensure_file(self) -> None:
        self.data_dir.mkdir(parents=True, exist_ok=True)
        if not self.experience_file.exists():
            self.experience_file.write_text("{}")

    def _load(self) -> dict[str, dict]:
        return json.loads(self.experience_file.read_text())

    def _save(self, data: dict[str, dict]) -> None:
        self.experience_file.write_text(json.dumps(data, indent=2))

    def _deserialize_attempt(self, attempt: dict | TaskAttempt) -> TaskAttempt:
        if isinstance(attempt, TaskAttempt):
            return attempt
        return TaskAttempt(**attempt)

    def _deserialize_experience(self, raw: dict | TaskExperience) -> TaskExperience:
        if isinstance(raw, TaskExperience):
            return raw
        return TaskExperience(
            task_id=raw["task_id"],
            problem_type=ProblemType(raw.get("problem_type", ProblemType.KNOWLEDGE)),
            domain=raw.get("domain", ""),
            problem_modeling=raw.get("problem_modeling", ""),
            attempts=[self._deserialize_attempt(a) for a in raw.get("attempts", [])],
            final_status=TaskStatus(raw.get("final_status", TaskStatus.UNSOLVED)),
            what_worked=raw.get("what_worked", ""),
            why_worked_analysis=raw.get("why_worked_analysis", ""),
            effective_skill_id=raw.get("effective_skill_id"),
        )

    def ensure_task(
        self,
        task_id: str,
        problem_type: ProblemType,
        domain: str = "",
        problem_modeling: str = "",
    ) -> TaskExperience:
        """Ensure a task record exists so final status updates are persisted."""
        data = self._load()
        if task_id in data:
            exp = self._deserialize_experience(data[task_id])
            changed = False
            if not exp.domain and domain:
                exp.domain = domain
                changed = True
            if not exp.problem_modeling and problem_modeling:
                exp.problem_modeling = problem_modeling
                changed = True
            if changed:
                data[task_id] = asdict(exp)
                self._save(data)
            return exp

        exp = TaskExperience(
            task_id=task_id,
            problem_type=problem_type,
            domain=domain,
            problem_modeling=problem_modeling,
        )
        data[task_id] = asdict(exp)
        self._save(data)
        return exp

    def get(self, task_id: str) -> Optional[TaskExperience]:
        """Get experience for a task."""
        data = self._load()
        if task_id not in data:
            return None
        return self._deserialize_experience(data[task_id])

    def add(self, task_id: str, experience: TaskExperience) -> None:
        """Add or update experience for a task.

        If already at max entries, replaces oldest INEFFECTIVE entry
        or oldest entry if all are effective.
        """
        data = self._load()

        if task_id in data:
            existing = self._deserialize_experience(data[task_id])
            if len(existing.attempts) >= self.max_entries:
                # Find entry to replace
                # Prefer replacing INEFFECTIVE attempts
                for i, attempt in enumerate(existing.attempts):
                    if attempt.real_test_passed is False:
                        existing.attempts[i] = experience.attempts[0] if experience.attempts else attempt
                        data[task_id] = asdict(existing)
                        self._save(data)
                        return
                # All effective, replace oldest
                existing.attempts[0] = experience.attempts[0] if experience.attempts else existing.attempts[0]
                data[task_id] = asdict(existing)
                self._save(data)
                return

        data[task_id] = asdict(experience)
        self._save(data)

    def update_final_status(self, task_id: str, status: TaskStatus,
                           what_worked: str = "", why_worked: str = "",
                           effective_skill_id: str = "") -> None:
        """Update final status and analysis for a task."""
        data = self._load()
        if task_id not in data:
            exp = TaskExperience(task_id=task_id, problem_type=ProblemType.KNOWLEDGE)
        else:
            exp = self._deserialize_experience(data[task_id])
        exp.final_status = status
        if what_worked:
            exp.what_worked = what_worked
        if why_worked:
            exp.why_worked_analysis = why_worked
        if effective_skill_id:
            exp.effective_skill_id = effective_skill_id

        data[task_id] = asdict(exp)
        self._save(data)

    def add_attempt(self, task_id: str, attempt: TaskAttempt) -> None:
        """Add an attempt to existing experience."""
        data = self._load()
        if task_id not in data:
            # Create new experience with this attempt
            exp = TaskExperience(task_id=task_id, problem_type=ProblemType.KNOWLEDGE)
            exp.attempts.append(attempt)
            data[task_id] = asdict(exp)
        else:
            exp = self._deserialize_experience(data[task_id])
            exp.attempts.append(attempt)
            data[task_id] = asdict(exp)
        self._save(data)

    def get_all_solved(self) -> list[str]:
        """Get all solved task IDs."""
        data = self._load()
        return [
            task_id for task_id, exp in data.items()
            if self._deserialize_experience(exp).final_status == TaskStatus.SOLVED
        ]

    def get_all_abandoned(self) -> list[str]:
        """Get all abandoned task IDs."""
        data = self._load()
        return [
            task_id for task_id, exp in data.items()
            if self._deserialize_experience(exp).final_status == TaskStatus.ABANDONED
        ]
