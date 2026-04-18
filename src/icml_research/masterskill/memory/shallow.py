"""Shallow memory: Skill repository and trace."""

import json
from pathlib import Path
from typing import Optional
from dataclasses import asdict

from ..core.types import SkillBundle, SkillStatus, TaskAttempt


class ShallowMemory:
    """Shallow memory layer: skill repository + trace.

    - Skills are stored as files in SKILL.md format (SkillsBench compatible)
    - Trace records attempt history for debugging
    """

    def __init__(self, data_dir: str):
        self.data_dir = Path(data_dir)
        self.skills_dir = self.data_dir / "skills"
        self.trace_dir = self.data_dir / "trace"
        self.skills_dir.mkdir(parents=True, exist_ok=True)
        self.trace_dir.mkdir(parents=True, exist_ok=True)

    # === Skill Repository Operations ===

    def add_skill(self, skill: SkillBundle) -> None:
        """Add a skill to the repository."""
        skill_dir = self.skills_dir / skill.skill_id
        skill_dir.mkdir(parents=True, exist_ok=True)

        # Write SKILL.md
        skill_md_path = skill_dir / "SKILL.md"
        skill_md_path.write_text(skill.to_skill_md())

        # Write metadata
        meta_path = skill_dir / "metadata.json"
        meta = {
            "skill_id": skill.skill_id,
            "name": skill.name,
            "status": skill.status.value,
            "description": skill.description,
            "trigger_condition": skill.trigger_condition,
            "usage": skill.usage,
        }
        meta_path.write_text(json.dumps(meta, indent=2))

        # Write support files.
        scripts_dir = skill_dir / "scripts"
        for relative_path, content in skill.scripts.items():
            file_path = scripts_dir / relative_path
            file_path.parent.mkdir(parents=True, exist_ok=True)
            file_path.write_text(content)

    def get_skill(self, skill_id: str) -> Optional[SkillBundle]:
        """Retrieve a skill by ID."""
        skill_dir = self.skills_dir / skill_id
        if not skill_dir.exists():
            return None

        meta_path = skill_dir / "metadata.json"
        if not meta_path.exists():
            return None

        meta = json.loads(meta_path.read_text())

        # Load scripts
        scripts_dir = skill_dir / "scripts"
        scripts = {}
        if scripts_dir.exists():
            for file_path in scripts_dir.rglob("*"):
                if file_path.is_file():
                    scripts[str(file_path.relative_to(scripts_dir))] = file_path.read_text()

        return SkillBundle(
            skill_id=meta["skill_id"],
            name=meta["name"],
            description=meta["description"],
            trigger_condition=meta["trigger_condition"],
            usage=meta.get("usage", ""),
            scripts=scripts,
            status=SkillStatus(meta.get("status", "draft")),
        )

    def list_skills(self) -> list[str]:
        """List all skill IDs in the repository."""
        if not self.skills_dir.exists():
            return []
        return [d.name for d in self.skills_dir.iterdir() if d.is_dir()]

    def update_skill_status(self, skill_id: str, status: SkillStatus) -> None:
        """Update skill status."""
        skill_dir = self.skills_dir / skill_id
        meta_path = skill_dir / "metadata.json"
        if meta_path.exists():
            meta = json.loads(meta_path.read_text())
            meta["status"] = status.value
            meta_path.write_text(json.dumps(meta, indent=2))

    def delete_skill(self, skill_id: str) -> None:
        """Delete a skill."""
        import shutil
        skill_dir = self.skills_dir / skill_id
        if skill_dir.exists():
            shutil.rmtree(skill_dir)

    # === Trace Operations ===

    def add_trace(self, task_id: str, attempt: TaskAttempt) -> None:
        """Add an attempt record to trace."""
        trace_file = self.trace_dir / f"{task_id}.jsonl"
        with open(trace_file, "a") as f:
            f.write(json.dumps(asdict(attempt)) + "\n")

    def get_trace(self, task_id: str) -> list[TaskAttempt]:
        """Get all attempts for a task."""
        trace_file = self.trace_dir / f"{task_id}.jsonl"
        if not trace_file.exists():
            return []

        attempts = []
        for line in trace_file.read_text().strip().split("\n"):
            if line:
                data = json.loads(line)
                attempts.append(TaskAttempt(**data))
        return attempts

    def get_latest_trace(self, task_id: str) -> Optional[TaskAttempt]:
        """Get the most recent attempt for a task."""
        attempts = self.get_trace(task_id)
        return attempts[-1] if attempts else None

    def clear_trace(self, task_id: str) -> None:
        """Clear trace for a task (after task completion)."""
        trace_file = self.trace_dir / f"{task_id}.jsonl"
        if trace_file.exists():
            trace_file.unlink()
