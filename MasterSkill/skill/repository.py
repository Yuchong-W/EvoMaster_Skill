"""Skill repository for managing skill lifecycle."""

from pathlib import Path
from typing import Optional
import re

from ..core.types import SkillBundle, SkillStatus


class SkillRepository:
    """Repository for managing skill bundles in SkillsBench format.

    Skills are stored in the SkillsBench directory structure:
    <task_id>/environment/skills/<skill_id>/SKILL.md
    """

    TRIGGER_SECTION_CANDIDATES = (
        "When to Use",
        "When to Apply",
        "Use When",
        "When Applicable",
    )
    USAGE_SECTION_CANDIDATES = (
        "How to Use",
        "Usage",
        "Workflow",
        "Methodology",
        "Quick Start",
        "Example Workflow",
        "4-Step Pipeline",
        "Suggested Command",
    )
    BINARY_EXTENSIONS = {
        ".pyc",
        ".pyo",
        ".so",
        ".dll",
        ".dylib",
        ".exe",
        ".bin",
        ".o",
        ".a",
        ".class",
    }

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
        frontmatter, body = self._split_frontmatter(content)

        skill = SkillBundle(
            skill_id=skill_id,
            name=self._extract_name(body, frontmatter, skill_id),
            description=self._extract_description(body, frontmatter),
            trigger_condition=self._extract_first_section(body, self.TRIGGER_SECTION_CANDIDATES),
            usage=self._extract_usage(body),
            scripts=self._load_support_files(skill_path),
            metadata=frontmatter,
            status=SkillStatus.ACTIVE,
        )

        return skill

    def _load_support_files(self, skill_path: Path) -> dict[str, str]:
        """Load executable/support files that should accompany the skill."""
        files: dict[str, str] = {}

        scripts_dir = skill_path / "scripts"
        if scripts_dir.exists():
            for file_path in sorted(p for p in scripts_dir.rglob("*") if p.is_file()):
                if self._should_skip_support_file(file_path):
                    continue
                files[str(file_path.relative_to(skill_path))] = file_path.read_text()

        for file_path in sorted(skill_path.iterdir()):
            if not file_path.is_file():
                continue
            if file_path.name == "SKILL.md":
                continue
            lowered = file_path.name.lower()
            if lowered.startswith("license") or lowered.startswith("readme"):
                continue
            if self._should_skip_support_file(file_path):
                continue
            files.setdefault(file_path.name, file_path.read_text())

        return files

    def _should_skip_support_file(self, file_path: Path) -> bool:
        """Ignore cache and binary artifacts that should not be bundled into skills."""
        if "__pycache__" in file_path.parts:
            return True
        if file_path.suffix.lower() in self.BINARY_EXTENSIONS:
            return True
        return False

    def _split_frontmatter(self, content: str) -> tuple[dict[str, str], str]:
        """Split optional YAML-style frontmatter from markdown body."""
        if not content.startswith("---\n"):
            return {}, content

        closing = content.find("\n---\n", 4)
        if closing == -1:
            return {}, content

        frontmatter_text = content[4:closing]
        body = content[closing + 5:]
        return self._parse_frontmatter(frontmatter_text), body

    def _parse_frontmatter(self, text: str) -> dict[str, str]:
        """Parse simple scalar key/value pairs from YAML-style frontmatter."""
        parsed: dict[str, str] = {}
        current_key = ""
        current_lines: list[str] = []

        def flush_current() -> None:
            nonlocal current_key, current_lines
            if current_key:
                parsed[current_key] = "\n".join(current_lines).strip().strip("\"'")
            current_key = ""
            current_lines = []

        for raw_line in text.splitlines():
            line = raw_line.rstrip()
            if not line.strip():
                continue
            if line.startswith((" ", "\t")):
                if current_key:
                    current_lines.append(line.strip())
                continue
            if ":" not in line:
                continue
            flush_current()
            key, value = line.split(":", 1)
            current_key = key.strip()
            current_lines = [value.strip()]

        flush_current()
        return parsed

    def _extract_name(self, body: str, frontmatter: dict[str, str], skill_id: str) -> str:
        """Extract skill name from frontmatter or first heading."""
        frontmatter_name = frontmatter.get("name", "").strip()
        if frontmatter_name:
            return frontmatter_name

        for line in body.strip().splitlines():
            if line.startswith("# "):
                return line[2:].strip()

        fallback = skill_id.replace("-", " ").replace("_", " ").strip()
        return fallback or "Unnamed Skill"

    def _extract_first_section(self, content: str, candidates: tuple[str, ...]) -> str:
        """Extract the first matching markdown section from a set of aliases."""
        for section in candidates:
            extracted = self._extract_section(content, section)
            if extracted:
                return extracted
        return ""

    def _extract_section(self, content: str, section: str) -> str:
        """Extract a markdown section by title, tolerating heading depth."""
        lines = content.splitlines()
        in_section = False
        result_lines = []
        section_heading = section.strip().lower()

        for line in lines:
            stripped = line.strip()
            if stripped.startswith("#"):
                heading = stripped.lstrip("#").strip().lower()
                if heading == section_heading:
                    in_section = True
                    continue
                if in_section:
                    break
            if in_section:
                result_lines.append(line)

        return "\n".join(result_lines).strip()

    def _extract_description(self, body: str, frontmatter: dict[str, str]) -> str:
        """Extract a compact description for prompting and summaries."""
        frontmatter_description = frontmatter.get("description", "").strip().strip("\"'")
        if frontmatter_description:
            return frontmatter_description

        lines = body.splitlines()
        description_lines: list[str] = []
        started = False
        for line in lines:
            stripped = line.strip()
            if stripped.startswith("#"):
                if started:
                    break
                started = True
                continue
            if stripped.startswith("##"):
                break
            if not stripped and not description_lines:
                continue
            if stripped:
                started = True
            if started:
                description_lines.append(line)

        description = "\n".join(description_lines).strip()
        if description:
            return description

        paragraphs = [chunk.strip() for chunk in re.split(r"\n\s*\n", body) if chunk.strip()]
        for paragraph in paragraphs:
            if not paragraph.startswith("#"):
                return paragraph
        return ""

    def _extract_usage(self, body: str) -> str:
        """Extract a practical usage section with resilient fallbacks."""
        usage = self._extract_first_section(body, self.USAGE_SECTION_CANDIDATES)
        if usage:
            return usage

        fallback_sections = (
            "Quick Reference",
            "Important Requirements",
            "Requirements for Outputs",
            "Rule Categories by Priority",
        )
        for section in fallback_sections:
            extracted = self._extract_section(body, section)
            if extracted:
                return extracted

        paragraphs = [chunk.strip() for chunk in re.split(r"\n\s*\n", body) if chunk.strip()]
        useful: list[str] = []
        for paragraph in paragraphs:
            if paragraph.startswith("#"):
                continue
            useful.append(paragraph)
            if len(useful) >= 2:
                break
        return "\n\n".join(useful)

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
