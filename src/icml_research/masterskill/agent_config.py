"""Agent configuration for MasterSkill.

All agent models should be configured here for easy modification.

Usage:
    from agent_config import AGENT_CONFIG, get_agent_config
    config = get_agent_config()
"""

AGENT_CONFIG = {
    # All SkillsBench experiments are currently standardized on gpt-5.2.
    # Research Team Agents
    "searcher": {
        "model": "gpt-5.2",
        "temperature": 0.7,
        "max_tokens": 4096,
        "description": "Research specialist - searches for solutions",
    },
    "analyzer": {
        "model": "gpt-5.2",
        "temperature": 0.3,
        "max_tokens": 2048,
        "description": "Problem analysis - identifies root causes",
    },
    "critic": {
        "model": "gpt-5.2",
        "temperature": 0.5,
        "max_tokens": 2048,
        "description": "Quality control - prevents grinding",
    },
    "skill_creator": {
        "model": "gpt-5.2",
        "temperature": 0.7,
        "max_tokens": 4096,
        "description": "Skill engineering - creates skill bundles",
    },
    "quick_proposer": {
        "model": "gpt-5.2",
        "temperature": 0.5,
        "max_tokens": 2048,
        "description": "Surface fixes - wording and details only",
    },
    "judge": {
        "model": "gpt-5.2",
        "temperature": 0.3,
        "max_tokens": 4096,
        "description": "Evaluation - assesses skill execution results",
    },
    "reflector": {
        "model": "gpt-5.2",
        "temperature": 0.7,
        "max_tokens": 4096,
        "description": "Meta-reasoning - reflects on Judger strictness",
    },

    # Execution Agent (Codex CLI using the current ChatGPT login)
    "execution": {
        "model": "gpt-5.2",
        "cli_path": "/usr/local/bin/codex",
        "description": "Executes tasks from the host via Codex, controlling the Docker task container",
        "timeout": 600,
    },
}


def get_agent_config():
    """Get full agent configuration."""
    return AGENT_CONFIG


def get_agent_model(agent_name: str) -> str:
    """Get model for a specific agent."""
    if agent_name == "judger":
        agent_name = "judge"
    return AGENT_CONFIG.get(agent_name, {}).get("model", "gpt-5.2")


def get_agent_params(agent_name: str) -> dict:
    """Get all parameters for a specific agent."""
    if agent_name == "judger":
        agent_name = "judge"
    return AGENT_CONFIG.get(agent_name, {})
