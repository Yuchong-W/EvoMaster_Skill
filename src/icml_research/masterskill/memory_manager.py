"""Memory Manager - unified interface for memory access with permissions.

Each agent has different access levels:
- Searcher: all layers (read), write to all layers
- Analyzer: shallow trace only (read), write to trace
- Critic: new vs old skill comparison only (read), no write
- QuickProposer: shallow trace only (read), no write
- SkillCreator: all layers (read), write to all layers
- Reflector: all layers (read), write to meta
"""

from enum import Enum
from typing import Optional
from dataclasses import dataclass

from .memory.shallow import ShallowMemory
from .memory.task_experience import TaskExperienceMemory
from .memory.meta_memory import MetaMemoryStore
from .core.types import (
    ProblemType, TaskExperience, MetaMemory,
    EffectiveMethod, IneffectiveMethod, TaskStatus,
)


class AgentRole(str, Enum):
    """Agent roles with different memory permissions."""
    SEARCHER = "searcher"
    ANALYZER = "analyzer"
    CRITIC = "critic"
    QUICK_PROPOSER = "quick_proposer"
    SKILL_CREATOR = "skill_creator"
    REFLECTOR = "reflector"
    RUNNER = "runner"  # System orchestrator


@dataclass
class MemoryPermission:
    """Memory access permissions for an agent."""
    read_shallow: bool = False
    write_shallow: bool = False
    read_task_experience: bool = False
    write_task_experience: bool = False
    read_meta: bool = False
    write_meta: bool = False


# Permission table
AGENT_PERMISSIONS = {
    AgentRole.SEARCHER: MemoryPermission(
        read_shallow=True, write_shallow=True,
        read_task_experience=True, write_task_experience=True,
        read_meta=True, write_meta=True,
    ),
    AgentRole.ANALYZER: MemoryPermission(
        read_shallow=True, write_shallow=False,
        read_task_experience=False, write_task_experience=False,
        read_meta=False, write_meta=False,
    ),
    AgentRole.CRITIC: MemoryPermission(
        read_shallow=False, write_shallow=False,
        read_task_experience=False, write_task_experience=False,
        read_meta=False, write_meta=False,
        # Special: Critic only compares new vs old submissions
    ),
    AgentRole.QUICK_PROPOSER: MemoryPermission(
        read_shallow=True, write_shallow=False,
        read_task_experience=False, write_task_experience=False,
        read_meta=False, write_meta=False,
    ),
    AgentRole.SKILL_CREATOR: MemoryPermission(
        read_shallow=True, write_shallow=True,
        read_task_experience=True, write_task_experience=True,
        read_meta=True, write_meta=True,
    ),
    AgentRole.REFLECTOR: MemoryPermission(
        read_shallow=True, write_shallow=False,
        read_task_experience=True, write_task_experience=True,
        read_meta=True, write_meta=True,
    ),
    AgentRole.RUNNER: MemoryPermission(
        read_shallow=True, write_shallow=True,
        read_task_experience=True, write_task_experience=True,
        read_meta=True, write_meta=True,
    ),
}


class MemoryManager:
    """Unified memory interface with permission control.

    All memory access goes through this manager to enforce permissions.
    """

    def __init__(self, data_dir: str):
        self.shallow = ShallowMemory(f"{data_dir}/shallow")
        self.task_experience = TaskExperienceMemory(f"{data_dir}/task_experience")
        self.meta = MetaMemoryStore(f"{data_dir}/meta")

    def check_permission(self, role: AgentRole, permission: str) -> bool:
        """Check if a role has a specific permission."""
        perms = AGENT_PERMISSIONS.get(role, MemoryPermission())
        return getattr(perms, permission, False)

    # === Shallow Memory (Trace + Skill Repo) ===

    def get_trace(self, role: AgentRole, task_id: str) -> list:
        """Get trace for a task. Requires read_shallow permission."""
        if not self.check_permission(role, "read_shallow"):
            raise PermissionError(f"{role.value} cannot read shallow memory")
        return self.shallow.get_trace(task_id)

    def add_trace(self, role: AgentRole, task_id: str, attempt: dict) -> None:
        """Add trace entry. Requires write_shallow permission."""
        if not self.check_permission(role, "write_shallow"):
            raise PermissionError(f"{role.value} cannot write shallow memory")
        from .core.types import TaskAttempt
        self.shallow.add_trace(task_id, TaskAttempt(**attempt))

    def list_skills(self, role: AgentRole) -> list[str]:
        """List all skills. Requires read_shallow permission."""
        if not self.check_permission(role, "read_shallow"):
            raise PermissionError(f"{role.value} cannot read skill repository")
        return self.shallow.list_skills()

    def get_skill(self, role: AgentRole, skill_id: str):
        """Get a skill by ID. Requires read_shallow permission."""
        if not self.check_permission(role, "read_shallow"):
            raise PermissionError(f"{role.value} cannot read skill repository")
        return self.shallow.get_skill(skill_id)

    def save_skill(self, role: AgentRole, skill) -> None:
        """Save a skill. Requires write_shallow permission."""
        if not self.check_permission(role, "write_shallow"):
            raise PermissionError(f"{role.value} cannot write skill repository")
        self.shallow.add_skill(skill)

    # === Task Experience Memory ===

    def get_task_experience(self, role: AgentRole, task_id: str) -> Optional[TaskExperience]:
        """Get experience for a task. Requires read_task_experience permission."""
        if not self.check_permission(role, "read_task_experience"):
            raise PermissionError(f"{role.value} cannot read task experience")
        return self.task_experience.get(task_id)

    def add_task_attempt(self, role: AgentRole, task_id: str, attempt: dict) -> None:
        """Add attempt to task experience. Requires write_task_experience permission."""
        if not self.check_permission(role, "write_task_experience"):
            raise PermissionError(f"{role.value} cannot write task experience")
        from .core.types import TaskAttempt
        self.task_experience.add_attempt(task_id, TaskAttempt(**attempt))

    def update_task_status(
        self, role: AgentRole, task_id: str, status: TaskStatus,
        what_worked: str = "", why_worked: str = "", effective_skill_id: str = ""
    ) -> None:
        """Update task final status. Requires write_task_experience permission."""
        if not self.check_permission(role, "write_task_experience"):
            raise PermissionError(f"{role.value} cannot write task experience")
        self.task_experience.update_final_status(
            task_id, status, what_worked, why_worked, effective_skill_id
        )

    def get_solved_tasks(self, role: AgentRole) -> list[str]:
        """Get all solved task IDs. Requires read_task_experience permission."""
        if not self.check_permission(role, "read_task_experience"):
            raise PermissionError(f"{role.value} cannot read task experience")
        return self.task_experience.get_all_solved()

    # === Meta Memory ===

    def get_meta_memory(
        self, role: AgentRole,
        problem_type: ProblemType, domain: str, modeling: str
    ) -> Optional[MetaMemory]:
        """Get meta memory for a problem profile. Requires read_meta permission."""
        if not self.check_permission(role, "read_meta"):
            raise PermissionError(f"{role.value} cannot read meta memory")
        return self.meta.get(problem_type, domain, modeling)

    def get_transferable_skills(
        self, role: AgentRole,
        problem_type: ProblemType, domain: str, modeling: str,
        min_transferability: str = "medium"
    ) -> list[EffectiveMethod]:
        """Get transferable skills for reuse. Requires read_meta permission."""
        if not self.check_permission(role, "read_meta"):
            raise PermissionError(f"{role.value} cannot read meta memory")
        return self.meta.get_transferable_skills(problem_type, domain, modeling, min_transferability)

    def add_effective_method(
        self, role: AgentRole,
        problem_type: ProblemType, domain: str, modeling: str,
        method: EffectiveMethod
    ) -> None:
        """Add effective method to meta memory. Requires write_meta permission."""
        if not self.check_permission(role, "write_meta"):
            raise PermissionError(f"{role.value} cannot write meta memory")
        self.meta.add_effective_method(problem_type, domain, modeling, method)

    def add_ineffective_method(
        self, role: AgentRole,
        problem_type: ProblemType, domain: str, modeling: str,
        method: IneffectiveMethod
    ) -> None:
        """Add ineffective method to meta memory. Requires write_meta permission."""
        if not self.check_permission(role, "write_meta"):
            raise PermissionError(f"{role.value} cannot write meta memory")
        self.meta.add_ineffective_method(problem_type, domain, modeling, method)

    def add_success_factor(
        self, role: AgentRole,
        problem_type: ProblemType, domain: str, modeling: str,
        factor: str
    ) -> None:
        """Add success factor. Requires write_meta permission."""
        if not self.check_permission(role, "write_meta"):
            raise PermissionError(f"{role.value} cannot write meta memory")
        self.meta.add_success_factor(problem_type, domain, modeling, factor)

    def is_method_ineffective(self, role: AgentRole, method_id: str) -> bool:
        """Check if method is known ineffective. Requires read_meta permission."""
        if not self.check_permission(role, "read_meta"):
            raise PermissionError(f"{role.value} cannot read meta memory")
        return self.meta.is_method_ineffective(method_id)

    # === Utility ===

    def get_memory_context_for_searcher(
        self, task_id: str, problem_type: ProblemType, domain: str, modeling: str
    ) -> dict:
        """Get a combined memory context for Searcher agent.

        This is a helper to get all relevant memory in one call.
        """
        context = {
            "task_experience": None,
            "trace": self.shallow.get_trace(task_id),
            "solved_similar": [],
            "effective_methods": [],
            "ineffective_methods": [],
            "skills": self.shallow.list_skills()[:10],  # Limit for prompt size
        }

        # Get task experience
        exp = self.task_experience.get(task_id)
        if exp:
            context["task_experience"] = {
                "problem_type": exp.problem_type.value,
                "domain": exp.domain,
                "problem_modeling": exp.problem_modeling,
                "attempts": len(exp.attempts),
                "final_status": exp.final_status.value,
            }

        # Get similar solved tasks from meta
        meta = self.meta.get(problem_type, domain, modeling)
        if meta:
            context["effective_methods"] = [
                {"id": m.method_id, "description": m.description, "transferability": m.transferability}
                for m in meta.effective_methods
            ]
            context["ineffective_methods"] = [
                {"id": m.method_id, "description": m.description, "reason": m.failure_reason}
                for m in meta.ineffective_methods
            ]

        return context
