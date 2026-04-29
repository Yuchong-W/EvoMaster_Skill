"""Configuration management."""

import os
from pathlib import Path

from .types import Config, default_skillsbench_root
from ..agent_config import AGENT_CONFIG


def _get_model(name: str, override: str) -> str:
    """Get model name: use override if not 'from_agent_config', else from config."""
    if override and override != "from_agent_config":
        return override
    return AGENT_CONFIG.get(name, {}).get("model", "gpt-5.2")


def load_config(
    skillsbench_root: str = "",
    data_root: str = "",
    **kwargs
) -> Config:
    """Load configuration from environment and parameters."""
    skillsbench_root = skillsbench_root or default_skillsbench_root()

    # Get API key from environment
    api_key = os.environ.get("OPENAI_API_KEY", "")
    base_url = os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1")

    # Extract model overrides from kwargs
    model_overrides = {
        k.replace("model_", ""): v
        for k, v in kwargs.items()
        if k.startswith("model_") and v
    }

    return Config(
        skillsbench_root=skillsbench_root,
        data_root=data_root or str(Path(skillsbench_root).parent / "masterskill_data"),
        max_real_test_failures=kwargs.get("max_real_test_failures", Config.max_real_test_failures),
        max_quick_proposer_iterations=kwargs.get(
            "max_quick_proposer_iterations",
            Config.max_quick_proposer_iterations,
        ),
        max_research_triggers_same_judger=kwargs.get(
            "max_research_triggers_same_judger",
            Config.max_research_triggers_same_judger,
        ),
        max_research_cycles=kwargs.get(
            "max_research_cycles",
            Config.max_research_cycles,
        ),
        initial_attempt_timeout_seconds=kwargs.get(
            "initial_attempt_timeout_seconds",
            Config.initial_attempt_timeout_seconds,
        ),
        skill_execution_timeout_seconds=kwargs.get(
            "skill_execution_timeout_seconds",
            Config.skill_execution_timeout_seconds,
        ),
        real_test_timeout_seconds=kwargs.get(
            "real_test_timeout_seconds",
            Config.real_test_timeout_seconds,
        ),
        post_solve_optimization_rounds=kwargs.get(
            "post_solve_optimization_rounds",
            Config.post_solve_optimization_rounds,
        ),
        base_attempt_include_task_skills=kwargs.get(
            "base_attempt_include_task_skills",
            Config.base_attempt_include_task_skills,
        ),
        stop_after_base_attempt=kwargs.get(
            "stop_after_base_attempt",
            Config.stop_after_base_attempt,
        ),
        persist_task_skills=kwargs.get(
            "persist_task_skills",
            Config.persist_task_skills,
        ),
        openai_api_key=api_key,
        openai_base_url=base_url,
        model_searcher=_get_model("searcher", model_overrides.get("searcher", "")),
        model_analyzer=_get_model("analyzer", model_overrides.get("analyzer", "")),
        model_critic=_get_model("critic", model_overrides.get("critic", "")),
        model_skill_creator=_get_model("skill_creator", model_overrides.get("skill_creator", "")),
        model_quick_proposer=_get_model("quick_proposer", model_overrides.get("quick_proposer", "")),
        model_judger=_get_model("judger", model_overrides.get("judger", "")),
        model_reflector=_get_model("reflector", model_overrides.get("reflector", "")),
    )
