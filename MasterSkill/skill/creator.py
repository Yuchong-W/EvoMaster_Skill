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

CRITICAL QUALITY BAR:
- Prefer operational, end-to-end solving skills over diagnostic-only helpers
- If bundled task skills already exist, prefer adapting or composing them
- Avoid creating scripts that only inspect inputs, print metadata, or restate the task
- The skill should materially increase the chance of solving the task, not just improve observability

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

Bundled task skills already available in the environment:
{bundled_task_skills}

## Your Task

Create a skill bundle that addresses the problem.

The bundle should help solve the task end-to-end.
Reject weak patterns such as:
- input verifiers with no solve path
- scripts that only echo file stats / hashes / metadata
- generic reminders without executable task steps

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

    OPTIMIZE_SYSTEM_PROMPT = """You are SkillCreator, a skill optimization specialist.

Your role: refine an already viable skill so the model can solve the task with
lower search cost, fewer wasted steps, and less prompt bloat while preserving correctness.

Sometimes the baseline solve came from the base model without any external skill.
In that case, do not blindly compress the old task-local skill. Distill the winning
behavior into a compact operational workflow and use the old skill only as reference.

Optimization priorities:
1. Reduce unnecessary context and exploratory work
2. Make the solve path more direct and operational
3. Preserve any details that are required for correctness
4. Prefer concise, high-signal instructions over broad background

Do NOT:
- Remove constraints the verifier actually depends on
- Replace a working operational path with vague advice
- Add scripts that only inspect inputs or restate the task
- Trust example output snippets over the actual verifier contract when they conflict

Output MUST be valid JSON."""

    OPTIMIZE_USER_PROMPT = """## Task Context

Task: {task_id}
Problem type: {problem_type}
Domain: {domain}
Problem modeling: {problem_modeling}

## Baseline Source

{baseline_source}

## Baseline Performance

Duration seconds: {duration_seconds}
Input tokens: {input_tokens}
Cached input tokens: {cached_input_tokens}
Output tokens: {output_tokens}

## Task Instruction

{instruction_excerpt}

## Working Execution Summary

{success_summary}

## Current Skill

{current_skill}

## Bundled Task Skills

{bundled_task_skills}

## Feedback From Previous Optimization Attempts

{failure_feedback}

## Your Task

Produce an optimized skill that aims to reduce runtime and token usage without
losing correctness. Keep only the minimum context and instructions needed for a
reliable solve path.

Important:
- Preserve explicit verifier contracts such as required output paths, JSON schema,
  list-vs-scalar rules, and token logging requirements.
- When instruction examples and verifier behavior conflict, follow the verifier contract.
- Include a finalization checklist for output artifacts: write every required file,
  reopen it, parse or sanity-check it, and ensure nothing is truncated or missing.
- Keep execution narration minimal. For small required text artifacts such as JSON
  answer files, end by printing the final validated artifact so downstream checks
  can verify the exact output without relying on earlier narration.
- If the task has multiple output files or paired sidecar artifacts, explicitly state
  how to produce and verify each of them before exiting.
- If previous feedback mentions timeout, missing output, or wrong format, address
  those issues directly in the workflow.
- If the task requires token logging but exact usage is not exposed inside the task
  runtime, compute a deterministic numeric estimate from the actual processed
  question/answer/evidence text with a task-local helper and write the numeric
  values directly. Never use identical placeholder constants or describe the
  values as guesses/placeholders in the final transcript.
- If baseline_source says the task passed without an external skill, create a distilled
  reusable solve path instead of assuming the current skill already works.

Return a JSON with:
{{
    "skill_id": "optimized skill id",
    "name": "optimized skill name",
    "description": "what the optimized skill does",
    "trigger_condition": "when to use it",
    "usage": "concise, direct solve workflow",
    "scripts": {{
        "optional_script.py": "script content"
    }},
    "optimization_notes": [
        "what was removed or tightened to reduce cost"
    ]
}}"""

    def create_skill(self, task_id: str, problem_type: str, domain: str,
                    problem_modeling: str, research_output: ResearchOutput,
                    effective_methods: list, bundled_task_skills: str = "",
                    skill_id: Optional[str] = None) -> SkillBundle:
        """Create a skill bundle."""
        skill_id = skill_id or str(uuid.uuid4())[:8]
        fallback = self._fallback_skill_payload(
            task_id=task_id,
            skill_id=skill_id,
            problem_type=problem_type,
            domain=domain,
            problem_modeling=problem_modeling,
            research_output=research_output,
            bundled_task_skills=bundled_task_skills,
            effective_methods=effective_methods,
        )

        messages = [
            {"role": "system", "content": self.SYSTEM_PROMPT},
            {"role": "user", "content": self.USER_PROMPT.format(
                task_id=task_id,
                problem_type=problem_type,
                domain=domain,
                problem_modeling=problem_modeling,
                research_output=self._format_research(research_output),
                effective_methods=self._format_methods(effective_methods),
                bundled_task_skills=bundled_task_skills or "No bundled task skills found.",
            )}
        ]

        result = self.chat_json(messages, temperature=0.7, fallback=fallback)

        return SkillBundle(
            skill_id=result.get("skill_id", skill_id),
            name=result.get("name", "Unnamed Skill"),
            description=result.get("description", ""),
            trigger_condition=result.get("trigger_condition", ""),
            usage=result.get("usage", ""),
            scripts=result.get("scripts", {}),
        )

    def optimize_skill(
        self,
        task_id: str,
        problem_type: str,
        domain: str,
        problem_modeling: str,
        current_skill: SkillBundle,
        success_summary: str,
        bundled_task_skills: str = "",
        duration_seconds: float = 0.0,
        input_tokens: int = 0,
        cached_input_tokens: int = 0,
        output_tokens: int = 0,
        baseline_source: str = "skill_pass",
        instruction_excerpt: str = "",
        failure_feedback: str = "",
        skill_id: Optional[str] = None,
    ) -> SkillBundle:
        """Create a lower-cost variant of a skill after a successful run."""
        optimized_skill_id = skill_id or f"{current_skill.skill_id}-optimized"
        fallback = self._fallback_optimized_skill_payload(
            optimized_skill_id=optimized_skill_id,
            current_skill=current_skill,
            bundled_task_skills=bundled_task_skills,
            baseline_source=baseline_source,
            failure_feedback=failure_feedback,
        )
        messages = [
            {"role": "system", "content": self.OPTIMIZE_SYSTEM_PROMPT},
            {"role": "user", "content": self.OPTIMIZE_USER_PROMPT.format(
                task_id=task_id,
                problem_type=problem_type,
                domain=domain,
                problem_modeling=problem_modeling,
                duration_seconds=f"{duration_seconds:.2f}",
                input_tokens=input_tokens,
                cached_input_tokens=cached_input_tokens,
                output_tokens=output_tokens,
                baseline_source=baseline_source,
                instruction_excerpt=instruction_excerpt or "No instruction excerpt available.",
                success_summary=success_summary or "No execution summary available.",
                current_skill=current_skill.to_skill_md(),
                bundled_task_skills=bundled_task_skills or "No bundled task skills found.",
                failure_feedback=failure_feedback or "No prior optimization feedback.",
            )},
        ]

        result = self.chat_json(messages, temperature=0.4, fallback=fallback)

        return SkillBundle(
            skill_id=result.get("skill_id", optimized_skill_id),
            name=result.get("name", f"{current_skill.name} Optimized"),
            description=result.get("description", current_skill.description),
            trigger_condition=result.get("trigger_condition", current_skill.trigger_condition),
            usage=result.get("usage", current_skill.usage),
            scripts=result.get("scripts", current_skill.scripts),
            metadata={
                "optimization_notes": result.get("optimization_notes", []),
                "baseline_source": baseline_source,
            },
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

    def _fallback_skill_payload(
        self,
        task_id: str,
        skill_id: str,
        problem_type: str,
        domain: str,
        problem_modeling: str,
        research_output: ResearchOutput,
        bundled_task_skills: str,
        effective_methods: list,
    ) -> dict:
        """Synthesize a minimal operational skill when the LLM path is unavailable."""
        research_hints = " ".join(
            part.strip()
            for part in [research_output.analysis, research_output.search_summary]
            if part and part.strip()
        )
        usage_steps = [
            "1. Read the task instruction and verifier contract first. Extract every required output path, filename, schema, and sidecar artifact before editing anything.",
            "2. Reuse bundled task skills and task-local tools first; only add the smallest missing step needed to complete the task end-to-end.",
            "3. Build the solution toward final verifier-visible artifacts, not toward diagnostics or metadata-only scripts.",
            "4. Re-open every required artifact after writing it and validate format, completeness, and consistency before exiting.",
        ]
        bundled_hint = self._truncate_text(
            bundled_task_skills or "No bundled task skills found.",
            limit=220,
        )
        if bundled_hint and bundled_hint != "No bundled task skills found.":
            usage_steps.append(f"5. Start from bundled support already in the environment: {bundled_hint}")
        if research_hints:
            usage_steps.append(f"6. Prioritize this fix direction: {self._truncate_text(research_hints, limit=260)}")
        if effective_methods:
            usage_steps.append(
                "7. Borrow only verified useful parts of prior effective methods, and do not repeat methods already known to fail on this task."
            )

        return {
            "skill_id": skill_id,
            "name": f"{task_id.replace('-', ' ').title()} Operational Solver",
            "description": (
                "Fallback operational skill that composes bundled task skills, targets the "
                "verifier contract directly, and validates final artifacts before exit."
            ),
            "trigger_condition": (
                f"Use for {task_id} when solving {problem_type or 'tool'} tasks in "
                f"{domain or 'general'} domains with {problem_modeling or 'direct_solution'} modeling."
            ),
            "usage": "\n".join(usage_steps),
            "scripts": {},
        }

    def _fallback_optimized_skill_payload(
        self,
        optimized_skill_id: str,
        current_skill: SkillBundle,
        bundled_task_skills: str,
        baseline_source: str,
        failure_feedback: str,
    ) -> dict:
        """Produce a conservative lower-cost optimization fallback."""
        usage_steps = [
            "1. Follow the shortest known working path; do not reopen broad search if the current method is already viable.",
            "2. Read only the instruction fragments needed to determine required outputs, schema, and verifier constraints.",
            "3. Reuse existing bundled skills or helper scripts instead of re-deriving the same steps from scratch.",
            "4. Write every required artifact, reopen it, sanity-check the final contents, and keep execution narration minimal.",
        ]
        if baseline_source == "base_model_pass":
            usage_steps.append(
                "5. Distill the successful base-model behavior into a compact workflow instead of expanding the old task-local skill."
            )
        if failure_feedback:
            usage_steps.append(
                f"6. Explicitly avoid prior optimization regressions: {self._truncate_text(failure_feedback, limit=260)}"
            )
        bundled_hint = self._truncate_text(bundled_task_skills or "", limit=220)
        if bundled_hint:
            usage_steps.append(f"7. Keep bundled support in play only where it shortens the solve path: {bundled_hint}")

        return {
            "skill_id": optimized_skill_id,
            "name": f"{current_skill.name} Optimized",
            "description": current_skill.description or "Lower-cost fallback variant of the current operational skill.",
            "trigger_condition": current_skill.trigger_condition,
            "usage": "\n".join(usage_steps),
            "scripts": current_skill.scripts,
            "optimization_notes": [
                "Used a fallback optimization path to preserve a stable operational workflow.",
                "Removed broad exploratory work in favor of a tighter verifier-first checklist.",
            ],
        }

    def _truncate_text(self, text: str, limit: int = 240) -> str:
        """Keep fallback prompt-derived text compact."""
        normalized = " ".join((text or "").split())
        if len(normalized) <= limit:
            return normalized
        return normalized[: limit - 3] + "..."
