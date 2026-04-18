"""Analyzer agent - analyzes problems to identify root causes."""

from typing import Optional

from .base import BaseAgent


class Analyzer(BaseAgent):
    """Analyzer agent.

    Access: Shallow trace only (to prevent hasty attribution)
    Role: Analyze why a skill failed or why Judger is blocking
    """

    def __init__(self, model: str, api_key: Optional[str] = None, base_url: Optional[str] = None):
        super().__init__(model, api_key, base_url)

    SYSTEM_PROMPT = """You are Analyzer, a problem analysis specialist.

Your role: Analyze WHY something failed and identify the ROOT CAUSE.

IMPORTANT: You only have access to shallow trace (recent attempts).
Do NOT jump to conclusions based on limited data. Focus on:
1. What specifically failed
2. Why it failed (root cause, not symptoms)
3. What would need to change to succeed

Be precise and analytical. Avoid vague attributions."""

    USER_PROMPT = """## Situation

Task: {task_id}
Problem type: {problem_type}

## Failure Context

Model attempt result: {attempt_result}

## Trace History (Recent Attempts)

{trace_history}

## Judger Feedback (if available)

{judger_feedback}

## Your Analysis Task

Analyze why this is failing. Focus on:
1. What is the SPECIFIC blocking issue?
2. What is the ROOT CAUSE (not just the symptom)?
3. What would need to change to pass Judger?
4. Is this a stubborn issue (failed multiple times) or a new failure?

Return a JSON with:
{{
    "root_cause": "precise description of why it's failing",
    "blocking_issues": ["specific issues blocking success"],
    "suggested_directions": ["potential ways to fix this"],
    "is_stubborn": true/false (if failed 2+ times),
    "problem_type_refinement": "refined problem type if needed"
}}"""

    def run(self, task_id: str, problem_type: str, attempt_result: str,
            trace_history: list, judger_feedback: Optional[dict] = None) -> dict:
        """Run analysis for a problem."""
        normalized_problem_type = problem_type if problem_type in {"knowledge_bottleneck", "tool_bottleneck"} else "tool_bottleneck"
        attempt_excerpt = str(attempt_result or "").strip()[:220] or "Latest attempt failed without a detailed error."
        fallback = {
            "root_cause": (
                "Fallback analysis: treat the latest failure as an operational bottleneck until "
                "a more specific analyzer signal is available."
            ),
            "blocking_issues": [attempt_excerpt],
            "suggested_directions": [
                "Target the concrete verifier contract and required output artifacts first.",
                "Reuse bundled task skills and task-local tools before inventing new tooling.",
                "Avoid repeating methods that already failed in recent trace history.",
            ],
            "is_stubborn": len(trace_history or []) >= 2,
            "problem_type_refinement": normalized_problem_type,
        }
        messages = [
            {"role": "system", "content": self.SYSTEM_PROMPT},
            {"role": "user", "content": self.USER_PROMPT.format(
                task_id=task_id,
                problem_type=problem_type,
                attempt_result=attempt_result,
                trace_history=self._format_trace(trace_history),
                judger_feedback=self._format_judger(judger_feedback),
            )}
        ]

        return self.chat_json(messages, fallback=fallback)

    def _format_trace(self, trace: list) -> str:
        if not trace:
            return "No trace history available."
        formatted = []
        for index, attempt in enumerate(trace[-5:], start=1):
            if hasattr(attempt, "skill_id"):
                formatted.append(
                    f"- Attempt {index}: skill={attempt.skill_id}, "
                    f"qp_iterations={attempt.quick_proposer_iterations}, "
                    f"research={attempt.research_triggered}, "
                    f"judger_passed={attempt.judger_passed}, "
                    f"real_test_passed={attempt.real_test_passed}"
                )
            else:
                formatted.append(
                    f"- Attempt {index}: skill={attempt.get('skill_id', 'N/A')}, "
                    f"qp_iterations={attempt.get('quick_proposer_iterations', 0)}, "
                    f"research={attempt.get('research_triggered', False)}, "
                    f"judger_passed={attempt.get('judger_passed')}, "
                    f"real_test_passed={attempt.get('real_test_passed')}"
                )
        return "\n".join(formatted)

    def _format_judger(self, feedback: Optional[dict]) -> str:
        if not feedback:
            return "No Judger feedback available."
        return f"Pass: {feedback.get('pass')}\n" \
               f"Score: {feedback.get('score', 0)}\n" \
               f"Blocking issues: {feedback.get('blocking_issues', [])}\n" \
               f"Concerns: {feedback.get('non_blocking_concerns', [])}"
