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
      - False positive (wrong passed): MUST avoid - wastes real test resources
      - False negative (correct blocked): Acceptable in borderline cases - wastes one iteration
    - Be strict within reasonable bounds; blocking is appropriate when there are real concerns
    - Non-blocking concerns should be noted but NOT prevent passing
    """

    def __init__(self, model: str, api_key: Optional[str] = None, base_url: Optional[str] = None):
        super().__init__(model, api_key, base_url)

    SYSTEM_PROMPT = """You are Judger, an evaluation specialist.

Your role: Evaluate if a skill execution RESULT meets the task requirements.

IMPORTANT:
- You evaluate the EXECUTION RESULT, not the skill description itself
- You should be STRICT but fair - block results that have real problems
- Only pass results that are LIKELY CORRECT; borderline cases should be blocked
- Non-blocking concerns should be noted but NOT prevent passing

Evaluation criteria (in order of importance):
1. Are there CONSTRAINT VIOLATIONS? (must block)
2. Are there FORMAT/MISSING OUTPUT issues? (must block if critical)
3. Is the approach FUNDAMENTALLY WRONG? (must block)
4. Are there factual errors? (block if key facts are wrong)
5. Are there non-blocking concerns? (note but allow)

Blocking guidelines:
- HIGH CONFIDENCE wrong → block
- MEDIUM CONFIDENCE wrong → block
- LOW CONFIDENCE correct → lean toward pass
- Edge cases → consider severity and impact"""

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

Evaluate if this result should pass. Be STRICT:
1. Does it meet ALL critical constraints?
2. Are there any fatal blocking issues?
3. Are there non-blocking concerns to note?

Return a JSON:
{{
    "pass": true/false,
    "score": 0.0-1.0,
    "blocking_issues": [
        {{
            "type": "constraint_violation|missing_output|wrong_format|wrong_answer|...",
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

IMPORTANT: Be strict but fair. Block results with real problems. Pass only if
you're reasonably confident the result is correct. When in doubt, lean toward
blocking rather than letting a potentially wrong result waste a real test."""

    def evaluate(self, task_id: str, problem_description: str,
                 instruction: str, skill_description: str,
                 execution_result: str, test_info: Optional[str] = None,
                 criteria: Optional[dict] = None) -> JudgerFeedback:
        """Evaluate a skill execution result.

        Args:
            criteria: Optional dict with additional_checks from build_judger_criteria.
                     If provided, these strict checks will be applied.
        """
        # Build user prompt with criteria if provided
        criteria_section = ""
        if criteria and criteria.get("additional_checks"):
            checks = criteria["additional_checks"]
            criteria_section = "\n\n## STRICT ADDITIONAL CHECKS (Must Verify)\n"
            for check in checks:
                criteria_section += f"- **{check['check']}**: {check['reason']}\n"
            criteria_section += "\nThese are known failure patterns. Be extra strict."

        messages = [
            {"role": "system", "content": self.SYSTEM_PROMPT},
            {"role": "user", "content": self.USER_PROMPT.format(
                task_id=task_id,
                problem_description=problem_description,
                instruction=instruction[:2000],  # Limit length
                skill_description=skill_description[:1000],
                execution_result=self._compact_execution_result(execution_result),
                test_info=test_info or "No test info available.",
            ) + criteria_section}
        ]

        try:
            result = self.chat_json(messages, temperature=0.3)
            return JudgerFeedback.from_dict(result)
        except (json.JSONDecodeError, KeyError, TypeError, ValueError) as exc:
            try:
                content = self.chat(messages, temperature=0.3)
                result = json.loads(self._extract_json_content(content))
                return JudgerFeedback.from_dict(result)
            except Exception as inner_exc:
                return self._fallback_feedback(
                    f"Judger response could not be parsed: {exc}; secondary parse failed: {inner_exc}"
                )
        except Exception as exc:
            return self._fallback_feedback(str(exc))

    def _compact_execution_result(self, execution_result: str, limit: int = 4200) -> str:
        """Keep both the opening actions and final artifacts visible to the Judger."""
        if len(execution_result) <= limit:
            return execution_result

        head = execution_result[: limit // 2].rstrip()
        tail = execution_result[-(limit // 2):].lstrip()
        return f"{head}\n\n...[snip]...\n\n{tail}"

    def _fallback_feedback(self, reason: str) -> JudgerFeedback:
        """Return a conservative fail when Judger itself is unavailable."""
        clipped_reason = " ".join(reason.split())
        if len(clipped_reason) > 240:
            clipped_reason = clipped_reason[:237] + "..."
        return JudgerFeedback(
            passed=False,
            score=0.0,
            blocking_issues=[
                BlockingIssue(
                    type="judger_unavailable",
                    description=f"Judger fallback triggered: {clipped_reason}",
                    suggestion="Keep improving the operational solve path and rerun evaluation.",
                )
            ],
            non_blocking_concerns=[],
            positive_signals=[],
            confidence=0.2,
            recommendation="keep_improving",
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
