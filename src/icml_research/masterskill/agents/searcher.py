"""Searcher agent - searches for solutions avoiding duplicates."""

from typing import Optional

from .base import BaseAgent


class Searcher(BaseAgent):
    """Searcher agent.

    Access: All memory layers (to avoid duplicate search)
    Role: Search for relevant solutions, methods, and knowledge
    """

    def __init__(self, model: str, api_key: Optional[str] = None, base_url: Optional[str] = None):
        super().__init__(model, api_key, base_url)

    SYSTEM_PROMPT = """You are Searcher, a research specialist.

Your role: Search for relevant solutions, methods, and knowledge to solve a specific problem.

You have access to all memory layers, including:
- Task experiences (what worked/didn't work for similar tasks)
- Meta memory (cross-task methods and principles)

IMPORTANT: Check memory before searching to AVOID duplicating previous work.
If a method is already known to be ineffective, do NOT search for the same approach again.

Output a structured JSON with your search results."""

    USER_PROMPT = """## Task Context

Problem to solve: {problem_description}

Problem type: {problem_type}
Domain: {domain}
Problem modeling: {problem_modeling}

## Memory Check (DO NOT IGNORE)

Previously tried methods (from memory):
{previously_tried}

Known ineffective methods (from memory):
{ineffective_methods}

Known effective methods (from memory):
{effective_methods}

## Your Search Task

Search for solutions to this problem. Focus on:
1. Methods that have worked for similar problems
2. Novel approaches not yet tried
3. Domain-specific knowledge or tools

Return a JSON with:
{
    "search_summary": "What you found",
    "new_methods_found": ["list of new potential methods"],
    "relevant_knowledge": ["key knowledge points"],
    "recommended_approach": "which approach seems most promising and why"
}"""

    def run(self, problem_description: str, problem_type: str, domain: str,
            problem_modeling: str, memory_context: dict) -> dict:
        """Run search for a problem."""
        messages = [
            {"role": "system", "content": self.SYSTEM_PROMPT},
            {"role": "user", "content": self.USER_PROMPT.format(
                problem_description=problem_description,
                problem_type=problem_type,
                domain=domain,
                problem_modeling=problem_modeling,
                previously_tried=memory_context.get("previously_tried", "None"),
                ineffective_methods=memory_context.get("ineffective_methods", "None"),
                effective_methods=memory_context.get("effective_methods", "None"),
            )}
        ]

        return self.chat_json(messages)
