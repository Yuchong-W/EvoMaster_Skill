"""Configuration management."""

import os
from pathlib import Path

from .types import Config
from ..agent_config import AGENT_CONFIG


def _get_model(name: str, override: str) -> str:
    """Get model name: use override if not 'from_agent_config', else from config."""
    if override and override != "from_agent_config":
        return override
    return AGENT_CONFIG.get(name, {}).get("model", "gpt-4o")


def load_config(
    skillsbench_root: str = "/home/yuchong/skillsbench",
    data_root: str = "",
    **kwargs
) -> Config:
    """Load configuration from environment and parameters."""
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
