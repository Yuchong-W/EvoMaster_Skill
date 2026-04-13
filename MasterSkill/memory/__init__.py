"""Memory system for MasterSkill.

Three-layer architecture:
- Shallow (Trace): Skill repository + attempt history
- Middle (Task Experience): Per-task experience records
- Deep (Meta Memory): Cross-task meta-knowledge and methods
"""

from .shallow import ShallowMemory
from .task_experience import TaskExperienceMemory
from .meta_memory import MetaMemoryStore

__all__ = ["ShallowMemory", "TaskExperienceMemory", "MetaMemoryStore"]
