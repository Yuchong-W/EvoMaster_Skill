"""Path helpers for resolving SkillsBench layouts."""

from pathlib import Path


def resolve_tasks_root(skillsbench_root: str | Path) -> Path:
    """Accept either a SkillsBench repo root or a direct tasks/ directory."""
    root = Path(skillsbench_root)
    if root.name == "tasks" and root.is_dir():
        return root
    tasks_dir = root / "tasks"
    return tasks_dir if tasks_dir.is_dir() else root


def resolve_task_dir(skillsbench_root: str | Path, task_id: str) -> Path:
    """Return the task directory regardless of which root form was provided."""
    return resolve_tasks_root(skillsbench_root) / task_id
