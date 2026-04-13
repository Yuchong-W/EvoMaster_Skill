"""Judger feedback format."""

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class BlockingIssue:
    """A blocking issue that prevents passing."""
    type: str  # e.g., "constraint_violation", "missing_output", "wrong_format"
    description: str
    severity: str = "fatal"  # fatal | warning | info
    suggestion: str = ""


@dataclass
class NonBlockingConcern:
    """A non-blocking concern (improvement suggestion)."""
    type: str  # e.g., "edge_case", "robustness", "clarity"
    description: str
    severity: str = "warning"  # warning | info
    suggestion: str = ""


@dataclass
class JudgerFeedback:
    """Feedback from Judger evaluation.

    Evaluates skill execution result, not the skill itself.
    Cost is similar to real test, but provides richer diagnostic feedback.
    """
    pass: bool
    score: float = 0.0
    blocking_issues: list[BlockingIssue] = field(default_factory=list)
    non_blocking_concerns: list[NonBlockingConcern] = field(default_factory=list)
    positive_signals: list[str] = field(default_factory=list)
    confidence: float = 0.0
    recommendation: str = "unknown"  # proceed_to_real_test | keep_improving | abandon

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "pass": self.pass,
            "score": self.score,
            "blocking_issues": [
                {
                    "type": i.type,
                    "description": i.description,
                    "severity": i.severity,
                    "suggestion": i.suggestion,
                }
                for i in self.blocking_issues
            ],
            "non_blocking_concerns": [
                {
                    "type": c.type,
                    "description": c.description,
                    "severity": c.severity,
                    "suggestion": c.suggestion,
                }
                for c in self.non_blocking_concerns
            ],
            "positive_signals": self.positive_signals,
            "confidence": self.confidence,
            "recommendation": self.recommendation,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "JudgerFeedback":
        """Create from dictionary."""
        blocking_issues = [
            BlockingIssue(**i) for i in data.get("blocking_issues", [])
        ]
        non_blocking_concerns = [
            NonBlockingConcern(**c) for c in data.get("non_blocking_concerns", [])
        ]

        return cls(
            pass=data.get("pass", False),
            score=data.get("score", 0.0),
            blocking_issues=blocking_issues,
            non_blocking_concerns=non_blocking_concerns,
            positive_signals=data.get("positive_signals", []),
            confidence=data.get("confidence", 0.0),
            recommendation=data.get("recommendation", "unknown"),
        )

    @classmethod
    def from_llm_response(cls, response: str) -> "JudgerFeedback":
        """Parse JudgerFeedback from LLM response text.

        This is a fallback when JSON parsing fails.
        """
        # Try to extract pass/fail
        pass_indicators = ["pass", "passed", "success", "通过"]
        fail_indicators = ["fail", "failed", "block", "阻塞"]

        response_lower = response.lower()
        passed = any(ind in response_lower for ind in pass_indicators)
        failed = any(ind in response_lower for ind in fail_indicators)

        return cls(
            pass=passed and not failed,
            score=0.5 if passed else 0.0,
            recommendation="proceed_to_real_test" if passed else "keep_improving",
        )
