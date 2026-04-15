"""Quick Proposer - surface-level fixes without changing core method."""

from typing import Optional

from ..agents.base import BaseAgent
from ..core.types import SkillBundle
from ..judge.feedback import JudgerFeedback


class QuickProposer(BaseAgent):
    """Quick Proposer agent.

    Scope: Surface-level fixes only (wording, details)
    Constraint: Cannot modify core method
    Memory access: History only (shallow trace)
    Cannot see: Cognitive layer (prevents shortcuts)

    This agent makes small improvements to a skill based on Judger feedback,
    WITHOUT changing the core approach.
    """

    def __init__(self, model: str, api_key: Optional[str] = None, base_url: Optional[str] = None):
        super().__init__(model, api_key, base_url)

    SYSTEM_PROMPT = """You are QuickProposer, a skill refinement specialist.

Your role: Make SMALL, SURFACE-LEVEL improvements to a skill description.

IMPORTANT CONSTRAINTS:
- Do NOT change the core method or approach
- Do NOT add new functionality
- Focus ONLY on clarity, wording, and presentation
- Changes should be quick and incremental

You can improve:
- Clarity of instructions
- Wording and phrasing
- Adding examples or clarifications
- Better organization of content
- More precise trigger conditions

You should NOT do:
- Change the fundamental approach
- Add new tools or methods
- Rewrite the core logic
- Make architectural changes"""

    USER_PROMPT = """## Task

Task: {task_id}
Current Skill:
{current_skill}

## Judger Feedback (Blocking Issues)
{blocking_issues}

## Judger Feedback (Non-Blocking Concerns)
{non_blocking_concerns}

## Trace History (Recent Modifications)
{trace_history}

## Your Task

Make SMALL improvements to the skill description based on the feedback.
DO NOT change the core method. Focus on clarity and presentation.

Return a JSON with the improved skill:
{{
    "skill_id": "{skill_id}",  // Keep the same ID
    "name": "Improved skill name",
    "description": "Improved description (keep core meaning)",
    "trigger_condition": "Improved trigger condition",
    "usage": "Improved usage instructions",
    "changes_made": ["list of specific changes made"]
}}

IMPORTANT: Only change wording and presentation. Keep the core method intact."""

    def propose_fix(self, skill: SkillBundle, judger_feedback: JudgerFeedback,
                   trace_history: list) -> SkillBundle:
        """Propose small fixes based on Judger feedback."""
        messages = [
            {"role": "system", "content": self.SYSTEM_PROMPT},
            {"role": "user", "content": self.USER_PROMPT.format(
                task_id=skill.skill_id,
                current_skill=skill.to_skill_md()[:2000],
                blocking_issues=self._format_blocking(judger_feedback.blocking_issues),
                non_blocking_concerns=self._format_concerns(judger_feedback.non_blocking_concerns),
                trace_history=self._format_trace(trace_history),
                skill_id=skill.skill_id,
            )}
        ]

        result = self.chat_json(messages, temperature=0.5)

        return SkillBundle(
            skill_id=skill.skill_id,  # Keep same ID
            name=result.get("name", skill.name),
            description=result.get("description", skill.description),
            trigger_condition=result.get("trigger_condition", skill.trigger_condition),
            usage=result.get("usage", skill.usage),
            scripts=skill.scripts,  # Don't change scripts
            metadata={"changes_made": result.get("changes_made", [])},
        )

    def _format_blocking(self, issues: list) -> str:
        if not issues:
            return "No blocking issues"
        return "\n".join([
            f"- [{i.type}] {i.description}\n  Suggestion: {i.suggestion}"
            for i in issues
        ])

    def _format_concerns(self, concerns: list) -> str:
        if not concerns:
            return "No non-blocking concerns"
        return "\n".join([
            f"- [{c.type}] {c.description}\n  Suggestion: {c.suggestion}"
            for c in concerns
        ])

    def _format_trace(self, trace: list) -> str:
        if not trace:
            return "No modification history"
        formatted = []
        for attempt in trace[-3:]:
            if hasattr(attempt, "skill_id"):
                formatted.append(
                    f"- skill={attempt.skill_id}, "
                    f"judger_passed={attempt.judger_passed}, "
                    f"real_test_passed={attempt.real_test_passed}"
                )
            else:
                formatted.append(
                    f"- skill={attempt.get('skill_id', 'unknown')}, "
                    f"judger_passed={attempt.get('judger_passed')}, "
                    f"real_test_passed={attempt.get('real_test_passed')}"
                )
        return "\n".join(formatted)
