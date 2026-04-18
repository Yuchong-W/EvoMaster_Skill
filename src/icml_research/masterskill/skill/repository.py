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
        skill_path = self.get_skill_path(task_id, skill.skill_id)
        skill_path.mkdir(parents=True, exist_ok=True)

        # Write SKILL.md
        (skill_path / "SKILL.md").write_text(skill.to_skill_md())

        # Write support files if any.
        if skill.scripts:
            for relative_path, script_content in skill.scripts.items():
                file_path = skill_path / relative_path
                file_path.parent.mkdir(parents=True, exist_ok=True)
                file_path.write_text(script_content)

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
            description=self._extract_description(content),
            trigger_condition=self._extract_section(content, "When to Use"),
            usage=self._extract_section(content, "How to Use"),
            scripts=self._load_support_files(skill_path),
            status=SkillStatus.ACTIVE,
        )

        return skill

    def _load_support_files(self, skill_path: Path) -> dict[str, str]:
        """Load executable/support files that should accompany the skill."""
        files: dict[str, str] = {}

        scripts_dir = skill_path / "scripts"
        if scripts_dir.exists():
            for file_path in sorted(p for p in scripts_dir.rglob("*") if p.is_file()):
                files[str(file_path.relative_to(skill_path))] = file_path.read_text()

        for file_path in sorted(skill_path.iterdir()):
            if not file_path.is_file():
                continue
            if file_path.name == "SKILL.md":
                continue
            lowered = file_path.name.lower()
            if lowered.startswith("license") or lowered.startswith("readme"):
                continue
            files.setdefault(file_path.name, file_path.read_text())

        return files

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

    def _extract_description(self, content: str) -> str:
        """Extract the free-form description before the first section."""
        lines = content.split("\n")
        body = []
        started = False
        for line in lines[1:]:
            if line.startswith("## "):
                break
            if not started and not line.strip():
                continue
            started = True
            body.append(line)
        return "\n".join(body).strip()

    def list_task_skills(self, task_id: str) -> list[str]:
        """List all skills for a task."""
        skills_path = self.skillsbench_root / "tasks" / task_id / "environment" / "skills"
        if not skills_path.exists():
            return []
        skill_dirs = [d for d in skills_path.iterdir() if d.is_dir()]
        skill_dirs.sort(key=lambda path: self._skill_sort_key(path))
        return [d.name for d in skill_dirs]

    def _skill_sort_key(self, skill_path: Path) -> tuple[float, str]:
        skill_md = skill_path / "SKILL.md"
        timestamp = skill_md.stat().st_mtime if skill_md.exists() else skill_path.stat().st_mtime
        return (timestamp, skill_path.name)
