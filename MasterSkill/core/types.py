"""Core type definitions for MasterSkill."""

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class ProblemType(str, Enum):
    """Problem bottleneck types."""
    KNOWLEDGE = "knowledge_bottleneck"  # Specialized domain knowledge
    TOOL = "tool_bottleneck"          # Tool usage complexity


class TaskStatus(str, Enum):
    """Task resolution status."""
    UNSOLVED = "unsolved"
    SOLVED = "solved"
    ABANDONED = "abandoned"


class TaskDifficulty(str, Enum):
    """Execution difficulty used for model routing."""
    LIGHT = "light"
    MEDIUM = "medium"
    HARD = "hard"


class SkillStatus(str, Enum):
    """Skill lifecycle status."""
    DRAFT = "draft"
    ACTIVE = "active"
    EFFECTIVE = "effective"
    INEFFECTIVE = "ineffective"
    ARCHIVED = "archived"


class AttemptResult(str, Enum):
    """Single attempt result."""
    SUCCESS = "success"
    FAIL_QUICK_PROPOSER = "fail_quick_proposer"
    FAIL_JUDGER = "fail_judger"
    FAIL_REAL_TEST = "fail_real_test"


@dataclass
class TaskAttempt:
    """Record of a single skill attempt."""
    skill_id: str
    quick_proposer_iterations: int = 0
    research_triggered: bool = False
    judger_passed: Optional[bool] = None
    real_test_passed: Optional[bool] = None
    blocking_issues: list = field(default_factory=list)
    success_factors: list = field(default_factory=list)


@dataclass
class SkillBundle:
    """A skill with its description and resources."""
    skill_id: str
    name: str
    description: str
    trigger_condition: str  # When to use this skill
    usage: str            # How to use
    scripts: dict[str, str] = field(default_factory=dict)  # path -> content
    metadata: dict = field(default_factory=dict)
    status: SkillStatus = SkillStatus.DRAFT

    def to_skill_md(self) -> str:
        """Convert to SKILL.md format for SkillsBench."""
        result = f"# {self.name}\n\n"
        result += f"{self.description}\n\n"
        result += f"## When to Use\n\n{self.trigger_condition}\n\n"
        result += f"## How to Use\n\n{self.usage}\n\n"

        if self.scripts:
            result += "## Scripts\n\n"
            for path, content in self.scripts.items():
                result += f"### {path}\n\n```\n{content}\n```\n\n"

        return result


@dataclass
class TaskExperience:
    """Per-task experience record."""
    task_id: str
    problem_type: ProblemType
    domain: str = ""
    problem_modeling: str = ""
    attempts: list[TaskAttempt] = field(default_factory=list)
    final_status: TaskStatus = TaskStatus.UNSOLVED
    what_worked: str = ""
    why_worked_analysis: str = ""
    effective_skill_id: Optional[str] = None


@dataclass
class EffectiveMethod:
    """Record of an effective method."""
    method_id: str
    description: str
    origin_task: str
    transferability: str = "medium"  # high | medium | low
    conditions: str = ""
    hyperparameters: dict = field(default_factory=dict)


@dataclass
class IneffectiveMethod:
    """Record of an ineffective method."""
    method_id: str
    description: str
    failed_tasks: list[str] = field(default_factory=list)
    failure_reason: str = ""


@dataclass
class MetaMemory:
    """Deep meta-memory for cross-task knowledge."""
    problem_type: ProblemType
    domain: str
    problem_modeling: str
    effective_methods: list[EffectiveMethod] = field(default_factory=list)
    ineffective_methods: list[IneffectiveMethod] = field(default_factory=list)
    success_factors: list[str] = field(default_factory=list)


@dataclass
class TaskContext:
    """Context for a task being processed."""
    task_id: str
    instruction_md: str
    task_toml: dict
    tests_dir: str
    environment_dir: str
    model_attempt_result: Optional[str] = None
    failure_reason: Optional[str] = None
    problem_type: Optional[ProblemType] = None
    domain: str = ""          # e.g., "mathematical_reasoning", "code_generation"
    problem_modeling: str = ""  # e.g., "multi_step_deduction", "search_retrieval"
    # Fixed paths for skill execution
    output_path: str = ""
    execution_log_path: str = "/tmp/execution.log"


@dataclass
class ExecutionPlan:
    """Execution routing decision for a task run."""
    task_id: str
    difficulty: TaskDifficulty
    preferred_model: str
    category: str = ""
    tags: list[str] = field(default_factory=list)
    reasons: list[str] = field(default_factory=list)


@dataclass
class BenchmarkRunEvent:
    """A compact record for one significant task-run event."""
    stage: str
    passed: bool
    model: str = ""
    score: float = 0.0
    duration_seconds: float = 0.0
    failure_class: str = ""
    skill_id: str = ""
    routing_reason: str = ""
    notes: str = ""


@dataclass
class BenchmarkRunRecord:
    """Persisted result for one full task run."""
    run_id: str
    task_id: str
    status: TaskStatus
    started_at: str
    finished_at: str = ""
    duration_seconds: float = 0.0
    problem_type: str = ""
    domain: str = ""
    problem_modeling: str = ""
    final_score: float = 0.0
    final_model: str = ""
    failure_class: str = ""
    real_test_failures: int = 0
    skills_tried: list[str] = field(default_factory=list)
    events: list[BenchmarkRunEvent] = field(default_factory=list)


@dataclass
class ResearchOutput:
    """Output from Research Team."""
    skill: Optional[SkillBundle] = None
    judger: Optional[dict] = None  # Judger evaluation criteria
    analysis: str = ""
    search_summary: str = ""
    new_method: bool = False
    critic_approved: bool = False
    critic_feedback: str = ""


@dataclass
class Config:
    """System configuration.

    Models are loaded from agent_config.py - see model_xxx fields below.
    """
    # Paths
    skillsbench_root: str = "/home/yuchong/skillsbench"
    data_root: str = ""

    # Limits
    max_real_test_failures: int = 4
    max_quick_proposer_iterations: int = 3
    max_research_triggers_same_judger: int = 2
    max_task_experience_entries: int = 2
    initial_attempt_timeout_seconds: int = 240
    skill_execution_timeout_seconds: int = 420
    real_test_timeout_seconds: int = 900

    # Models per agent type (loaded from agent_config)
    # Override individual agents via kwargs if needed
    model_searcher: str = "from_agent_config"
    model_analyzer: str = "from_agent_config"
    model_critic: str = "from_agent_config"
    model_skill_creator: str = "from_agent_config"
    model_quick_proposer: str = "from_agent_config"
    model_judger: str = "from_agent_config"
    model_reflector: str = "from_agent_config"

    # API
    openai_api_key: str = ""
    openai_base_url: str = "https://api.openai.com/v1"
