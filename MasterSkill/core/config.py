"""Configuration management."""

import os
from pathlib import Path

from .types import Config


def load_config(
    skillsbench_root: str = "/home/yuchong/skillsbench",
    data_root: str = "",
    **kwargs
) -> Config:
    """Load configuration from environment and parameters."""
    # Get API key from environment
    api_key = os.environ.get("OPENAI_API_KEY", "")
    base_url = os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1")

    return Config(
        skillsbench_root=skillsbench_root,
        data_root=data_root or str(Path(skillsbench_root).parent / "masterskill_data"),
        openai_api_key=api_key,
        openai_base_url=base_url,
        **{k: v for k, v in kwargs.items() if v is not None}
    )
