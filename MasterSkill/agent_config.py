"""Agent configuration for MasterSkill.

All agent models should be configured here for easy modification.

Usage:
    from agent_config import AGENT_CONFIG, get_agent_config
    config = get_agent_config()
"""

AGENT_CONFIG = {
    # Research Team Agents
    "searcher": {
        "model": "gpt-4o",
        "temperature": 0.7,
        "max_tokens": 4096,
        "description": "Research specialist - searches for solutions",
    },
    "analyzer": {
        "model": "gpt-4o",
        "temperature": 0.3,
        "max_tokens": 2048,
        "description": "Problem analysis - identifies root causes",
    },
    "critic": {
        "model": "gpt-4o",
        "temperature": 0.5,
        "max_tokens": 2048,
        "description": "Quality control - prevents grinding",
    },
    "skill_creator": {
        "model": "claude-sonnet-4-6",
        "temperature": 0.7,
        "max_tokens": 4096,
        "description": "Skill engineering - creates skill bundles",
    },
    "quick_proposer": {
        "model": "gpt-4o-mini",
        "temperature": 0.5,
        "max_tokens": 2048,
        "description": "Surface fixes - wording and details only",
    },
    "judge": {
        "model": "gpt-4o",
        "temperature": 0.3,
        "max_tokens": 4096,
        "description": "Evaluation - assesses skill execution results",
    },
    "reflector": {
        "model": "gpt-4o",
        "temperature": 0.7,
        "max_tokens": 4096,
        "description": "Meta-reasoning - reflects on Judger strictness",
    },

    # Execution Agent (Claude Code CLI for running tasks)
    "execution": {
        "model": "claude-sonnet-4-6",
        "cli_path": "/home/yuchong/.local/bin/claude",
        "description": "Executes tasks in Docker using Claude Code CLI",
        "timeout": 600,
    },
}


def get_agent_config():
    """Get full agent configuration."""
    return AGENT_CONFIG


def get_agent_model(agent_name: str) -> str:
    """Get model for a specific agent."""
    return AGENT_CONFIG.get(agent_name, {}).get("model", "gpt-4o")


def get_agent_params(agent_name: str) -> dict:
    """Get all parameters for a specific agent."""
    return AGENT_CONFIG.get(agent_name, {})
