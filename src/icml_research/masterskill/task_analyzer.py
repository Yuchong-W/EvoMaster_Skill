"""Task analyzer - extracts domain, modeling, and problem type from task."""

from pathlib import Path
import json

from .core.types import ProblemType, TaskContext


class TaskAnalyzer:
    """Extracts structured information from a task.

    This is used to:
    1. Determine problem_type (knowledge_bottleneck vs tool_bottleneck)
    2. Extract domain (e.g., "math", "code", "reasoning")
    3. Extract problem_modeling (e.g., "multi-step deduction", "API orchestration")

    This runs once at task initialization to populate the task context.
    """

    # Domain keywords mapping
    DOMAIN_KEYWORDS = {
        "mathematical_reasoning": ["math", "calculate", "equation", "algebra", "geometry", "calculus"],
        "code_generation": ["code", "programming", "implement", "function", "algorithm"],
        "logical_deduction": ["logic", "deduction", "reasoning", "infer", "puzzle"],
        "data_analysis": ["data", "statistics", "analyze", "plot", "regression"],
        "web_knowledge": ["search", "web", "information", "fact", "knowledge"],
        "domain_specific": ["medical", "legal", "financial", "scientific", "engineering"],
        "natural_language": ["text", "nlp", "language", "summarize", "translate"],
        "planning_scheduling": ["plan", "schedule", "optimize", "route", "constraint"],
    }

    # Problem modeling patterns
    MODELING_PATTERNS = {
        "multi_step_deduction": ["step", "chain", "sequence", "reasoning", "derive"],
        "search_retrieval": ["search", "find", "lookup", "retrieve", "query"],
        "transformation": ["convert", "transform", "parse", "encode", "decode"],
        "optimization": ["minimize", "maximize", "optimize", "best", "optimal"],
        "verification": ["verify", "check", "validate", "test", "proof"],
        "generation": ["generate", "create", "produce", "synthesize"],
        "classification": ["classify", "categorize", "label", "predict"],
        "extraction": ["extract", "parse", "identify", "find"],
    }

    # Problem type indicators
    KNOWLEDGE_INDICATORS = [
        "specific knowledge", "domain expertise", "专业术语",
        "公式", "theorem", "definition", "原理",
        "requires understanding of", "needs specialized",
    ]

    TOOL_INDICATORS = [
        "API", "tool", "command", "script", "execute",
        "run", "call", "function", "method",
        "如何使用", "how to use", "usage of",
    ]

    def analyze(self, task_id: str, instruction_md: str, task_toml: dict = None) -> dict:
        """Analyze a task and extract structured information.

        Returns:
            {
                "problem_type": ProblemType,
                "domain": str,
                "problem_modeling": str,
                "category": str,  # from task.toml metadata
                "tags": list[str],  # from task.toml metadata
                "analysis_reasoning": str,
            }
        """
        instruction_lower = instruction_md.lower()

        # Extract from task.toml if available
        category = ""
        tags = []
        if task_toml and "metadata" in task_toml:
            category = task_toml["metadata"].get("category", "")
            tags = task_toml["metadata"].get("tags", [])

        # Determine problem type
        problem_type = self._determine_problem_type(instruction_lower, tags)

        # Determine domain
        domain = self._determine_domain(instruction_lower, category, tags)

        # Determine problem modeling
        modeling = self._determine_modeling(instruction_lower)

        reasoning = self._build_reasoning(problem_type, domain, modeling, category, tags)

        return {
            "problem_type": problem_type,
            "domain": domain,
            "problem_modeling": modeling,
            "category": category,
            "tags": tags,
            "analysis_reasoning": reasoning,
        }

    def _determine_problem_type(self, text: str, tags: list) -> ProblemType:
        """Determine if the bottleneck is knowledge or tool usage."""
        knowledge_score = 0
        tool_score = 0

        # Check tags
        tool_tags = ["api", "tool", "script", "command", "bash"]
        knowledge_tags = ["reasoning", "logic", "math", "theorem"]

        for tag in tags:
            tag_lower = tag.lower()
            if tag_lower in tool_tags:
                tool_score += 2
            if tag_lower in knowledge_tags:
                knowledge_score += 1

        # Check text content
        for indicator in self.KNOWLEDGE_INDICATORS:
            if indicator in text:
                knowledge_score += 1

        for indicator in self.TOOL_INDICATORS:
            if indicator in text:
                tool_score += 1

        # Special cases
        if "API" in text or "api" in text:
            tool_score += 2
        if "calculate" in text or "compute" in text:
            knowledge_score += 1
        if "execute" in text or "run command" in text:
            tool_score += 2

        return ProblemType.TOOL if tool_score > knowledge_score else ProblemType.KNOWLEDGE

    def _determine_domain(self, text: str, category: str, tags: list) -> str:
        """Determine the domain of the task."""
        # First try category from task.toml
        if category:
            return category.lower()

        # Then check tags
        for domain, keywords in self.DOMAIN_KEYWORDS.items():
            for tag in tags:
                if tag.lower() in keywords:
                    return domain

        # Then analyze text
        scores = {}
        for domain, keywords in self.DOMAIN_KEYWORDS.items():
            score = sum(1 for kw in keywords if kw in text)
            scores[domain] = score

        if scores and max(scores.values()) > 0:
            return max(scores, key=scores.get)

        return "general"

    def _determine_modeling(self, text: str) -> str:
        """Determine the problem modeling approach."""
        scores = {}

        for modeling, keywords in self.MODELING_PATTERNS.items():
            score = sum(1 for kw in keywords if kw in text)
            scores[modeling] = score

        # Special detection for multi-step
        if "step" in text and ("reasoning" in text or "deduction" in text):
            return "multi_step_deduction"

        if scores and max(scores.values()) > 0:
            return max(scores, key=scores.get)

        return "direct_solution"

    def _build_reasoning(self, problem_type: ProblemType, domain: str,
                         modeling: str, category: str, tags: list) -> str:
        """Build a human-readable reasoning string."""
        parts = [
            f"Problem type: {problem_type.value} (bottleneck is {'tool usage' if problem_type == ProblemType.TOOL else 'domain knowledge'})",
            f"Domain: {domain}",
            f"Modeling: {modeling}",
        ]
        if category:
            parts.append(f"Category: {category}")
        if tags:
            parts.append(f"Tags: {', '.join(tags)}")
        return "\n".join(parts)


def load_task_toml(task_dir: Path) -> dict:
    """Load and parse task.toml."""
    toml_path = task_dir / "task.toml"
    if not toml_path.exists():
        return {}

    try:
        import tomllib
        return tomllib.loads(toml_path.read_text())
    except Exception:
        # Fallback: simple parsing
        return {}
