"""Critic agent - evaluates if changes are meaningful."""

from typing import Optional

from .base import BaseAgent


class Critic(BaseAgent):
    """Critic agent.

    Access: Only new vs old skill (for comparison)
    Role: Prevent "grinding" - ensure changes are meaningful improvements
    """

    def __init__(self, model: str, api_key: Optional[str] = None, base_url: Optional[str] = None):
        super().__init__(model, api_key, base_url)

    SYSTEM_PROMPT = """You are Critic, a quality control specialist.

Your role: Evaluate if a NEW submission is meaningfully DIFFERENT from the OLD one.

IMPORTANT: You only see the old and new skill/Judger. Focus on whether there is
a SUBSTANTIVE difference, not just superficial changes.

Acceptance criteria (ANY ONE qualifies as meaningful):
1. New method introduced
2. Clearer formulation/description
3. Code implemented
4. Key data meanings clarified
5. Engineering details specified (units, etc.)
6. Detailed API usage specified

Reject if:
- Just rephrasing the same idea
- No concrete changes
- "Grinding" (minor tweaks without substance)

Be strict but fair. Better to reject trivial changes than accept non-improvements."""

    USER_PROMPT = """## Comparison: Old vs New

### OLD Submission
{old_submission}

### NEW Submission
{new_submission}

## Your Evaluation

Determine if the NEW submission is meaningfully different from OLD.

Return a JSON with:
{{
    "approved": true/false,
    "reason": "why it was approved or rejected",
    "substantive_changes": ["list of actual new contributions"],
    "rejection_reason": "if rejected, why (e.g., 'mere rephrasing')"
}}"""

    def run(self, old_submission: dict, new_submission: dict) -> dict:
        """Evaluate if change is meaningful."""
        messages = [
            {"role": "system", "content": self.SYSTEM_PROMPT},
            {"role": "user", "content": self.USER_PROMPT.format(
                old_submission=self._format_submission(old_submission),
                new_submission=self._format_submission(new_submission),
            )}
        ]

        return self.chat_json(messages)

    def _format_submission(self, submission: dict) -> str:
        """Format a submission for comparison."""
        if not submission:
            return "Empty submission"
        return f"Type: {submission.get('type', 'unknown')}\n" \
               f"Content:\n{submission.get('content', '')}"
