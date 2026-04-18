"""Reflector agent - meta-reasoning about Judger strictness."""

from typing import Optional

from .base import BaseAgent


class Reflector(BaseAgent):
    """Reflector agent.

    Role: When same Judger triggers Research 3x without real test,
          reflect on whether Judger is too strict and suggest adjustments.

    Access: All memory layers (read), meta memory (write)
    """

    SYSTEM_PROMPT = """You are Reflector, a meta-reasoning specialist.

Your role: Analyze WHY a Judger keeps blocking skills and determine if the
Judger criteria are too strict or have blind spots.

You are invoked when:
- Same Judger triggered Research 3+ times
- No skill has made it to real test yet
- This suggests either:
  1. The skills are genuinely not good enough (research problem)
  2. The Judger is too strict / has wrong criteria (evaluation problem)

You need to diagnose which case it is and suggest adjustments.

Be honest and analytical. The goal is not to make Judger pass everything,
but to have accurate evaluation criteria."""

    USER_PROMPT = """## Situation

Task: {task_id}
Judger has been triggered {count} times without any skill reaching real test.

## Historical Context

Judger criteria:
{judger_criteria}

## What was tried

Previous skills that failed Judger:
{skill_summaries}

## Recent Judger feedbacks (blocking issues)
{feedbacks}

## Your Analysis

Analyze:
1. Are the blocking issues consistently about the same thing?
2. Is the Judger requiring something that the task doesn't actually need?
3. Are the skills genuinely not meeting requirements?
4. Is there a pattern suggesting Judger is too strict?

Return a JSON with:
{{
    "diagnosis": "judger_too_strict | skills_not_good | unclear",
    "reasoning": "Why you think this",
    "adjustments": [
        "Specific changes to Judger criteria",
        "Or: what Research should focus on instead"
    ],
    "confidence": 0.0-1.0
}}"""

    def run(self, task_id: str, judger_criteria: dict,
            skill_summaries: list, feedbacks: list, trigger_count: int) -> dict:
        """Run reflection on Judger strictness."""
        fallback = {
            "diagnosis": "unclear",
            "reasoning": (
                "Fallback reflection: keep Judger stable and continue pushing for a more "
                "operational end-to-end solve path before relaxing evaluation."
            ),
            "adjustments": [
                "Keep the current Judger criteria unchanged for now.",
                "Focus research on producing validated output artifacts and explicit verifier-contract checks.",
            ],
            "confidence": 0.2,
        }
        messages = [
            {"role": "system", "content": self.SYSTEM_PROMPT},
            {"role": "user", "content": self.USER_PROMPT.format(
                task_id=task_id,
                count=trigger_count,
                judger_criteria=self._format_criteria(judger_criteria),
                skill_summaries=self._format_skills(skill_summaries),
                feedbacks=self._format_feedbacks(feedbacks),
            )}
        ]

        return self.chat_json(messages, temperature=0.7, fallback=fallback)

    def _format_criteria(self, criteria: dict) -> str:
        if not criteria:
            return "No specific criteria defined"
        parts = [f"- {k}: {v}" for k, v in criteria.items() if k != "additional_checks"]
        if "additional_checks" in criteria:
            for check in criteria["additional_checks"]:
                parts.append(f"- additional_check: {check}")
        return "\n".join(parts) if parts else "No specific criteria"

    def _format_skills(self, summaries: list) -> str:
        if not summaries:
            return "No skills attempted"
        return "\n".join([f"- {s}" for s in summaries[:5]])

    def _format_feedbacks(self, feedbacks: list) -> str:
        if not feedbacks:
            return "No feedback available"
        return "\n".join([
            f"- Blocking: {f.get('blocking_issues', [])}, Pass: {f.get('pass')}"
            for f in feedbacks[-3:]
        ])
