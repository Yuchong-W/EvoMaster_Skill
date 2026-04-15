"""Task-aware execution routing."""

from pathlib import Path

from ..core.types import ExecutionPlan, SkillBundle, TaskDifficulty


class TaskRouter:
    """Builds an explicit execution plan from task metadata and task content."""

    HARD_TAGS = {
        "optimization", "constraint-satisfaction", "simulation", "citation",
        "bibtex", "verification", "compiler", "quantum", "docking", "video",
        "planning", "forecasting",
    }
    MEDIUM_TAGS = {
        "excel", "spreadsheet", "csv", "json", "analysis", "report",
        "data", "office", "statistics", "extraction", "transformation",
    }

    def __init__(self, skillsbench_root: str):
        self.skillsbench_root = Path(skillsbench_root)
        self._task_toml_cache: dict[str, dict] = {}

    def build_plan(
        self,
        task_id: str,
        instruction: str,
        output_path: str = "",
        skill: SkillBundle | None = None,
    ) -> ExecutionPlan:
        """Return a concrete difficulty and model choice for a task run."""
        task_toml = self._load_task_toml(task_id)
        metadata = task_toml.get("metadata", {})
        category = str(metadata.get("category", "")).lower()
        tags = [str(tag).lower() for tag in metadata.get("tags", [])]
        metadata_difficulty = str(metadata.get("difficulty", "")).lower()

        reasons: list[str] = []
        difficulty = self._difficulty_from_metadata(metadata_difficulty, reasons)
        difficulty = self._difficulty_from_task_shape(
            difficulty=difficulty,
            category=category,
            tags=tags,
            instruction=instruction,
            output_path=output_path,
            skill=skill,
            reasons=reasons,
        )
        return ExecutionPlan(
            task_id=task_id,
            difficulty=difficulty,
            preferred_model=self._model_for_difficulty(difficulty, instruction, skill),
            category=category,
            tags=tags,
            reasons=reasons,
        )

    def _load_task_toml(self, task_id: str) -> dict:
        if task_id in self._task_toml_cache:
            return self._task_toml_cache[task_id]

        task_toml = {}
        toml_path = self.skillsbench_root / "tasks" / task_id / "task.toml"
        if toml_path.exists():
            try:
                import tomllib
                task_toml = tomllib.loads(toml_path.read_text())
            except Exception:
                task_toml = {}
        self._task_toml_cache[task_id] = task_toml
        return task_toml

    def _difficulty_from_metadata(self, metadata_difficulty: str, reasons: list[str]) -> TaskDifficulty:
        mapping = {
            "easy": TaskDifficulty.LIGHT,
            "light": TaskDifficulty.LIGHT,
            "medium": TaskDifficulty.MEDIUM,
            "hard": TaskDifficulty.HARD,
        }
        if metadata_difficulty in mapping:
            reasons.append(f"task.toml difficulty={metadata_difficulty}")
            return mapping[metadata_difficulty]
        reasons.append("task.toml missing explicit difficulty")
        return TaskDifficulty.LIGHT

    def _difficulty_from_task_shape(
        self,
        difficulty: TaskDifficulty,
        category: str,
        tags: list[str],
        instruction: str,
        output_path: str,
        skill: SkillBundle | None,
        reasons: list[str],
    ) -> TaskDifficulty:
        if category in {"research", "games", "scientific-analysis"}:
            difficulty = self._max_difficulty(difficulty, TaskDifficulty.HARD)
            reasons.append(f"category={category}")

        if any(tag in self.HARD_TAGS for tag in tags):
            difficulty = self._max_difficulty(difficulty, TaskDifficulty.HARD)
            reasons.append("hard tags present")
        elif any(tag in self.MEDIUM_TAGS for tag in tags):
            difficulty = self._max_difficulty(difficulty, TaskDifficulty.MEDIUM)
            reasons.append("medium tags present")

        if len(instruction) > 3000:
            difficulty = self._max_difficulty(difficulty, TaskDifficulty.HARD)
            reasons.append("long instruction")
        elif len(instruction) > 1400:
            difficulty = self._max_difficulty(difficulty, TaskDifficulty.MEDIUM)
            reasons.append("moderate instruction length")

        if output_path.endswith((".xlsx", ".csv")):
            difficulty = self._max_difficulty(difficulty, TaskDifficulty.MEDIUM)
            reasons.append(f"structured artifact output={output_path}")

        skill_size = len(skill.to_skill_md()) if skill is not None else 0
        if skill_size > 2500 or (skill is not None and skill.scripts):
            difficulty = self._max_difficulty(difficulty, TaskDifficulty.MEDIUM)
            reasons.append("skill payload is non-trivial")

        return difficulty

    def _model_for_difficulty(
        self,
        difficulty: TaskDifficulty,
        instruction: str,
        skill: SkillBundle | None,
    ) -> str:
        if difficulty == TaskDifficulty.HARD:
            return "gpt-5.4"
        if difficulty == TaskDifficulty.MEDIUM:
            return "gpt-5.3-codex"
        if len(instruction) > 700 or (skill is not None and len(skill.to_skill_md()) > 1200):
            return "gpt-5.2"
        return "gpt-5.1"

    def _max_difficulty(self, left: TaskDifficulty, right: TaskDifficulty) -> TaskDifficulty:
        order = {
            TaskDifficulty.LIGHT: 1,
            TaskDifficulty.MEDIUM: 2,
            TaskDifficulty.HARD: 3,
        }
        return left if order[left] >= order[right] else right
