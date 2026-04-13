"""Skill Creator - creates skills from research output."""

import uuid
from typing import Optional

from ..agents.base import BaseAgent
from ..core.types import SkillBundle, ResearchOutput


class SkillCreator(BaseAgent):
    """Skill Creator agent.

    Access: All memory layers
    Role: Create skill bundle from research output and analysis
    """

    def __init__(self, model: str, api_key: Optional[str] = None, base_url: Optional[str] = None):
        super().__init__(model, api_key, base_url)

    SYSTEM_PROMPT = """You are SkillCreator, a skill engineering specialist.

Your role: Create a SKILL.md bundle that helps a model solve a specific task.

A good skill includes:
1. CLEAR description of what the skill does
2. PRECISE trigger conditions (when to use this skill)
3. ACTIONABLE usage instructions (how to use it)
4. Optional: supporting scripts or tools

The skill should be in English, use formal language, and be specific about
what the model should do.

Output MUST be valid JSON."""

    USER_PROMPT = """## Task Context

Task: {task_id}
Problem type: {problem_type}
Domain: {domain}
Problem modeling: {problem_modeling}

## Research Output

{research_output}

## Available Memory

Previously effective methods:
{effective_methods}

## Your Task

Create a skill bundle that addresses the problem.

Return a JSON with:
{{
    "skill_id": "auto-generated-id-or-use-provided",
    "name": "Clear skill name",
    "description": "What this skill does (1-2 sentences)",
    "trigger_condition": "When should this skill be used? (specific situations)",
    "usage": "Step-by-step instructions on how to use this skill",
    "scripts": {{  # Optional
        "script_name.py": "script content"
    }}
}}"""

    def create_skill(self, task_id: str, problem_type: str, domain: str,
                    problem_modeling: str, research_output: ResearchOutput,
                    effective_methods: list, skill_id: Optional[str] = None) -> SkillBundle:
        """Create a skill bundle."""
        skill_id = skill_id or str(uuid.uuid4())[:8]

        messages = [
            {"role": "system", "content": self.SYSTEM_PROMPT},
            {"role": "user", "content": self.USER_PROMPT.format(
                task_id=task_id,
                problem_type=problem_type,
                domain=domain,
                problem_modeling=problem_modeling,
                research_output=self._format_research(research_output),
                effective_methods=self._format_methods(effective_methods),
            )}
        ]

        result = self.chat_json(messages, temperature=0.7)

        return SkillBundle(
            skill_id=result.get("skill_id", skill_id),
            name=result.get("name", "Unnamed Skill"),
            description=result.get("description", ""),
            trigger_condition=result.get("trigger_condition", ""),
            usage=result.get("usage", ""),
            scripts=result.get("scripts", {}),
        )

    def _format_research(self, output: ResearchOutput) -> str:
        """Format research output for prompt."""
        parts = []
        if output.analysis:
            parts.append(f"Analysis:\n{output.analysis}")
        if output.search_summary:
            parts.append(f"Search Summary:\n{output.search_summary}")
        if output.skill:
            parts.append(f"Existing Skill:\n{output.skill.description}")
        return "\n\n".join(parts) if parts else "No research output available."

    def _format_methods(self, methods: list) -> str:
        """Format effective methods for prompt."""
        if not methods:
            return "No previously effective methods found."
        return "\n".join([
            f"- {m.description} (transferability: {m.transferability})"
            for m in methods[:5]  # Limit to 5
        ])
