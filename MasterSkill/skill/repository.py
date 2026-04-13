"""Skill repository for managing skill lifecycle."""

from pathlib import Path
from typing import Optional

from ..core.types import SkillBundle, SkillStatus


class SkillRepository:
    """Repository for managing skill bundles in SkillsBench format.

    Skills are stored in the SkillsBench directory structure:
    <task_id>/environment/skills/<skill_id>/SKILL.md
    """

    def __init__(self, skillsbench_root: str):
        self.skillsbench_root = Path(skillsbench_root)

    def get_skill_path(self, task_id: str, skill_id: str) -> Path:
        """Get path to a skill directory."""
        return self.skillsbench_root / "tasks" / task_id / "environment" / "skills" / skill_id

    def skill_exists(self, task_id: str, skill_id: str) -> bool:
        """Check if a skill already exists for a task."""
        skill_path = self.get_skill_path(task_id, skill_id)
        return (skill_path / "SKILL.md").exists()

    def save_skill(self, task_id: str, skill: SkillBundle) -> None:
        """Save a skill to the SkillsBench directory structure."""
        skill_path = self.get_skill_path(task_id, skill_id)
        skill_path.mkdir(parents=True, exist_ok=True)

        # Write SKILL.md
        (skill_path / "SKILL.md").write_text(skill.to_skill_md())

        # Write scripts if any
        if skill.scripts:
            scripts_dir = skill_path / "scripts"
            scripts_dir.mkdir(exist_ok=True)
            for script_name, script_content in skill.scripts.items():
                (scripts_dir / script_name).write_text(script_content)

    def load_skill(self, task_id: str, skill_id: str) -> Optional[SkillBundle]:
        """Load a skill from the SkillsBench directory."""
        skill_path = self.get_skill_path(task_id, skill_id)
        skill_md = skill_path / "SKILL.md"
        if not skill_md.exists():
            return None

        content = skill_md.read_text()

        # Parse basic structure from SKILL.md
        # This is a simplified parser - in production might want more robust parsing
        skill = SkillBundle(
            skill_id=skill_id,
            name=self._extract_name(content),
            description=self._extract_section(content, "When to Use"),
            trigger_condition=self._extract_section(content, "When to Use"),
            usage=self._extract_section(content, "How to Use"),
            status=SkillStatus.ACTIVE,
        )

        return skill

    def _extract_name(self, content: str) -> str:
        """Extract skill name from markdown."""
        lines = content.strip().split("\n")
        if lines and lines[0].startswith("# "):
            return lines[0][2:].strip()
        return "Unnamed Skill"

    def _extract_section(self, content: str, section: str) -> str:
        """Extract a section from markdown."""
        lines = content.split("\n")
        in_section = False
        result_lines = []

        for line in lines:
            if line.strip() == f"## {section}":
                in_section = True
                continue
            if in_section and line.startswith("## "):
                break
            if in_section:
                result_lines.append(line)

        return "\n".join(result_lines).strip()

    def list_task_skills(self, task_id: str) -> list[str]:
        """List all skills for a task."""
        skills_path = self.skillsbench_root / "tasks" / task_id / "environment" / "skills"
        if not skills_path.exists():
            return []
        return [d.name for d in skills_path.iterdir() if d.is_dir()]
