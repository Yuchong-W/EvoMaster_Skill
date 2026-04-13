"""Judger - evaluates skill execution results."""

import json
from typing import Optional

from ..agents.base import BaseAgent
from .feedback import JudgerFeedback, BlockingIssue, NonBlockingConcern


class Judger(BaseAgent):
    """Judger agent.

    Evaluates skill execution result, NOT the skill itself.
    Cost ≈ Real test, but returns richer diagnostic feedback.

    Design principles:
    - Asymmetric error tolerance:
      - False negative (correct blocked): acceptable (wastes one real test)
      - False positive (wrong passed): must avoid (wastes skill attempts)
    - Prefer "pass if no fatal blocking issues"
    """

    def __init__(self, model: str, api_key: Optional[str] = None, base_url: Optional[str] = None):
        super().__init__(model, api_key, base_url)

    SYSTEM_PROMPT = """You are Judger, an evaluation specialist.

Your role: Evaluate if a skill execution RESULT meets the task requirements.

IMPORTANT:
- You evaluate the EXECUTION RESULT, not the skill description itself
- You should be LENIENT - prefer to pass results that might be correct
- Only block if there are CLEAR, FATAL errors
- Non-blocking concerns should be noted but NOT prevent passing

Evaluation criteria:
1. Does the output exist?
2. Does it meet basic format requirements?
3. Are there any constraint violations?
4. Are there obvious factual errors?
5. Is the approach fundamentally wrong?

You should rarely block. A result should only fail if it's clearly wrong."""

    USER_PROMPT = """## Task

Task: {task_id}
Problem: {problem_description}

## Task Instruction
{instruction}

## Skill Description
{skill_description}

## Execution Result (from skill execution)
{execution_result}

## Test/Verifier (if available)
{test_info}

## Your Evaluation

Evaluate if this result should pass. Consider:
1. Does it meet the task requirements?
2. Are there FATAL blocking issues?
3. Are there non-blocking concerns?

Return a JSON:
{{
    "pass": true/false,
    "score": 0.0-1.0,
    "blocking_issues": [
        {{
            "type": "constraint_violation|missing_output|wrong_format|...",
            "description": "What specifically is wrong",
            "severity": "fatal",  // fatal blocks, warning/info notes only
            "suggestion": "How to fix it"
        }}
    ],
    "non_blocking_concerns": [
        {{
            "type": "edge_case|robustness|clarity|...",
            "description": "Potential improvement",
            "severity": "warning",
            "suggestion": "How to improve"
        }}
    ],
    "positive_signals": ["What is working well"],
    "confidence": 0.0-1.0,
    "recommendation": "proceed_to_real_test|keep_improving|abandon"
}}

BE LENIENT. Only block on FATAL issues. Prefer passing questionable results
to avoid blocking correct ones."""

    def evaluate(self, task_id: str, problem_description: str,
                 instruction: str, skill_description: str,
                 execution_result: str, test_info: Optional[str] = None) -> JudgerFeedback:
        """Evaluate a skill execution result."""
        messages = [
            {"role": "system", "content": self.SYSTEM_PROMPT},
            {"role": "user", "content": self.USER_PROMPT.format(
                task_id=task_id,
                problem_description=problem_description,
                instruction=instruction[:2000],  # Limit length
                skill_description=skill_description[:1000],
                execution_result=execution_result[:3000],
                test_info=test_info or "No test info available.",
            )}
        ]

        try:
            result = self.chat_json(messages, temperature=0.3)
            return JudgerFeedback.from_dict(result)
        except (json.JSONDecodeError, KeyError) as e:
            # Fallback: try to parse from text
            content = self.chat(messages, temperature=0.3)
            # Try to extract JSON
            if "```json" in content:
                start = content.find("```json") + 7
                end = content.find("```", start)
                result = json.loads(content[start:end])
                return JudgerFeedback.from_dict(result)
            # Fallback to lenient pass
            return JudgerFeedback(
                pass=True,
                score=0.5,
                recommendation="proceed_to_real_test",
                confidence=0.3,
            )

    def build_judger_criteria(self, task_id: str, problem_description: str,
                               instruction: str, historical_failures: list[dict]) -> dict:
        """Build stricter Judger criteria based on real test failures.

        Called when real test repeatedly fails but Judger passes.
        This adds stricter criteria to prevent false positives.
        """
        criteria = {
            "task_id": task_id,
            "problem_description": problem_description,
            "instruction": instruction,
            "additional_checks": [],
        }

        # Analyze historical failures
        for failure in historical_failures[-3:]:  # Last 3 failures
            if failure.get("type") == "real_test_failed_after_judger_pass":
                # Add specific check based on failure reason
                reason = failure.get("reason", "")
                if "format" in reason.lower():
                    criteria["additional_checks"].append({
                        "check": "strict_format_validation",
                        "reason": "Previous failures due to format issues",
                    })
                elif "constraint" in reason.lower():
                    criteria["additional_checks"].append({
                        "check": "strict_constraint_check",
                        "reason": "Previous failures due to constraint violations",
                    })

        return criteria
