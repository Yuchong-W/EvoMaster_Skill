"""Benchmark Runner - orchestrates the full benchmark workflow."""

import re
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from ..core.types import (
    Config, TaskContext, SkillBundle,
    TaskStatus, TaskAttempt, ResearchOutput,
    ProblemType, EffectiveMethod, IneffectiveMethod,
    BenchmarkRunEvent, BenchmarkRunRecord,
)
from ..judge.feedback import JudgerFeedback
from ..memory import ShallowMemory, TaskExperienceMemory, MetaMemoryStore, BenchmarkResultStore
from ..memory_manager import MemoryManager
from ..agents import Searcher, Analyzer, Critic, Reflector
from ..skill import SkillRepository, SkillCreator
from ..judge import Judger
from ..proposer import QuickProposer
from ..task_analyzer import TaskAnalyzer
from .docker_executor import DockerExecutor


class BenchmarkRunner:
    """Main orchestrator for the benchmark-driven skill discovery system.

    Workflow per task:
    1. Model attempts task -> fails
    2. Analyzer analyzes weakness
    3. Try existing skills (试探性复用)
    4. If no skill works -> Research builds Skill + Judger (parallel)
    5. Skill -> Judger evaluation
    6. If Judger fails -> QuickProposer small fix (max 3 iterations)
    7. If Judger passes -> Real test
    8. If real test passes -> Memory update -> next task
    9. If real test fails -> Research modifies Judger
    10. If skill stuck at Judger -> QuickProposer (max 3 iterations)
    11. If same Judger triggers 2x Research with no judger pass -> reflect
    12. After 4 real test failures -> abandon task
    """

    def __init__(self, config: Config):
        self.config = config

        # Initialize memory
        data_dir = config.data_root or str(Path(config.skillsbench_root) / "data")
        self.shallow_memory = ShallowMemory(f"{data_dir}/shallow")
        self.task_memory = TaskExperienceMemory(f"{data_dir}/task_experience")
        self.meta_memory = MetaMemoryStore(f"{data_dir}/meta")
        self.result_store = BenchmarkResultStore(f"{data_dir}/benchmark_runs")

        # Memory manager with permission control
        self.memory = MemoryManager(data_dir)

        # Task analyzer for extracting domain/modeling
        self.task_analyzer = TaskAnalyzer()

        # Initialize agents from agent_config
        from ..agent_config import get_agent_params
        searcher_cfg = get_agent_params("searcher")
        analyzer_cfg = get_agent_params("analyzer")
        critic_cfg = get_agent_params("critic")
        skill_creator_cfg = get_agent_params("skill_creator")
        quick_proposer_cfg = get_agent_params("quick_proposer")
        judger_cfg = get_agent_params("judger")
        reflector_cfg = get_agent_params("reflector")

        self.searcher = Searcher(searcher_cfg["model"])
        self.analyzer = Analyzer(analyzer_cfg["model"])
        self.critic = Critic(critic_cfg["model"])
        self.skill_creator = SkillCreator(skill_creator_cfg["model"])
        self.judger = Judger(judger_cfg["model"])
        self.quick_proposer = QuickProposer(quick_proposer_cfg["model"])
        self.reflector = Reflector(reflector_cfg["model"])

        # Skill repository (SkillsBench format)
        self.skill_repo = SkillRepository(config.skillsbench_root)

        # Docker executor for skill and real test
        self.docker = DockerExecutor(config.skillsbench_root)

    def run_benchmark(self, task_ids: Optional[list[str]] = None) -> dict:
        """Run the full benchmark."""
        # Get task list
        if task_ids is None:
            task_ids = self._list_unsolved_tasks()

        results = {
            "total": len(task_ids),
            "solved": [],
            "abandoned": [],
            "solved_count": 0,
            "abandoned_count": 0,
        }

        for task_id in task_ids:
            status = self.run_task(task_id)
            if status == TaskStatus.SOLVED:
                results["solved"].append(task_id)
                results["solved_count"] += 1
            else:
                results["abandoned"].append(task_id)
                results["abandoned_count"] += 1

        return results

    def run_task(self, task_id: str) -> TaskStatus:
        """Run a single task through the feedback loop."""
        started_at = datetime.now(timezone.utc).isoformat()
        started_monotonic = time.monotonic()
        run_record = BenchmarkRunRecord(
            run_id=uuid.uuid4().hex[:12],
            task_id=task_id,
            status=TaskStatus.UNSOLVED,
            started_at=started_at,
        )
        skill_ids_tried: set[str] = set()
        real_test_failures = 0
        status = TaskStatus.ABANDONED
        context: Optional[TaskContext] = None

        try:
            context = self._load_task_context(task_id)
            if not context:
                run_record.failure_class = "missing_task_context"
                return TaskStatus.ABANDONED

            run_record.problem_type = context.problem_type.value if context.problem_type else ""
            run_record.domain = context.domain
            run_record.problem_modeling = context.problem_modeling

            attempt_result = self._model_attempt(context)
            self._append_run_event(
                run_record,
                stage="base_attempt",
                passed=attempt_result.get("success", False),
                model=attempt_result.get("model", ""),
                score=attempt_result.get("score", 0.0),
                duration_seconds=attempt_result.get("duration_seconds", 0.0),
                failure_class=attempt_result.get("failure_class", ""),
                routing_reason=attempt_result.get("routing_reason", ""),
                input_tokens=attempt_result.get("input_tokens", 0),
                cached_input_tokens=attempt_result.get("cached_input_tokens", 0),
                output_tokens=attempt_result.get("output_tokens", 0),
                notes=attempt_result.get("error", ""),
            )
            if attempt_result.get("success"):
                if not self.config.stop_after_base_attempt:
                    self._on_base_model_solved(task_id, context, attempt_result)
                    self._maybe_optimize_after_success(
                        context=context,
                        baseline_result=attempt_result,
                        baseline_skill=None,
                        run_record=run_record,
                    )
                status = TaskStatus.SOLVED
                run_record.final_score = 1.0
                run_record.final_model = attempt_result.get("model", "")
                return status

            if self.config.stop_after_base_attempt:
                run_record.failure_class = attempt_result.get("failure_class", "")
                run_record.final_model = attempt_result.get("model", "")
                run_record.final_score = attempt_result.get("score", 0.0)
                return TaskStatus.ABANDONED

            failure_analysis = self.analyzer.run(
                task_id=task_id,
                problem_type=context.problem_type.value if context.problem_type else "unknown",
                attempt_result=str(attempt_result.get("error", "model failed")),
                trace_history=self.shallow_memory.get_trace(task_id),
                judger_feedback=None,
            )

            problem_type = failure_analysis.get("problem_type_refinement", "tool_bottleneck")
            try:
                context.problem_type = ProblemType(problem_type) if problem_type else ProblemType.TOOL
            except ValueError:
                context.problem_type = context.problem_type or ProblemType.TOOL
            run_record.problem_type = context.problem_type.value

            judger_research_triggers = 0
            current_skill: Optional[SkillBundle] = None
            current_judger_criteria: Optional[dict] = None
            judger_feedback_history: list[dict] = []
            skill_summary_history: list[str] = []

            existing_skills = self._find_reusable_skills(context)
            if existing_skills:
                for skill in existing_skills:
                    skill_ids_tried.add(skill.skill_id)
                    result = self._try_skill(context, skill)
                    real_result = result.get("real_test_result")
                    self._record_attempt(
                        context=context,
                        skill=skill,
                        judger_feedback=result.get("feedback"),
                        real_test_passed=real_result.get("passed") if real_result else None,
                        quick_proposer_iterations=0,
                        research_triggered=False,
                        note=real_result.get("details", "") if real_result else "",
                        duration_seconds=real_result.get("duration_seconds", 0.0) if real_result else 0.0,
                        input_tokens=real_result.get("input_tokens", 0) if real_result else 0,
                        cached_input_tokens=real_result.get("cached_input_tokens", 0) if real_result else 0,
                        output_tokens=real_result.get("output_tokens", 0) if real_result else 0,
                    )
                    if real_result:
                        self._append_real_test_event(run_record, skill.skill_id, real_result)
                    if result.get("passed"):
                        self._on_task_solved(task_id, context, skill)
                        self._maybe_optimize_after_success(
                            context=context,
                            baseline_result=real_result or {},
                            baseline_skill=skill,
                            run_record=run_record,
                        )
                        status = TaskStatus.SOLVED
                        run_record.final_score = 1.0
                        run_record.final_model = real_result.get("model", "") if real_result else ""
                        return status

            research_output = self._research_new_skill(context)
            if not research_output.skill:
                run_record.failure_class = "research_failed"
                return TaskStatus.ABANDONED

            current_skill = research_output.skill
            skill_ids_tried.add(current_skill.skill_id)

            while real_test_failures < self.config.max_real_test_failures:
                judger_result = self._evaluate_with_judger(context, current_skill, current_judger_criteria)

                if judger_result.passed:
                    judger_research_triggers = 0
                    real_result = self._run_real_test(context, current_skill)
                    self._record_attempt(
                        context=context,
                        skill=current_skill,
                        judger_feedback=judger_result,
                        real_test_passed=real_result.get("passed"),
                        quick_proposer_iterations=0,
                        research_triggered=True,
                        note=real_result.get("details", ""),
                        duration_seconds=real_result.get("duration_seconds", 0.0),
                        input_tokens=real_result.get("input_tokens", 0),
                        cached_input_tokens=real_result.get("cached_input_tokens", 0),
                        output_tokens=real_result.get("output_tokens", 0),
                    )
                    self._append_real_test_event(run_record, current_skill.skill_id, real_result)

                    if real_result.get("passed"):
                        self._on_task_solved(task_id, context, current_skill)
                        self._maybe_optimize_after_success(
                            context=context,
                            baseline_result=real_result,
                            baseline_skill=current_skill,
                            run_record=run_record,
                        )
                        status = TaskStatus.SOLVED
                        run_record.final_score = real_result.get("score", 0.0)
                        run_record.final_model = real_result.get("model", "")
                        return status

                    real_test_failures += 1

                    if real_test_failures >= self.config.max_real_test_failures:
                        self._on_task_abandoned(task_id, context)
                        run_record.failure_class = real_result.get("failure_class", "")
                        return TaskStatus.ABANDONED

                    failure_record = {
                        "type": "real_test_failed_after_judger_pass",
                        "skill_id": current_skill.skill_id,
                        "reason": str(real_result.get("details", "")),
                    }
                    current_judger_criteria = self.judger.build_judger_criteria(
                        task_id, context.instruction_md[:200],
                        context.instruction_md,
                        [failure_record]
                    )
                    continue

                quick_proposer_iterations = 0
                if self._should_use_quick_proposer(judger_result):
                    while quick_proposer_iterations < self.config.max_quick_proposer_iterations:
                        judger_feedback_history.append(judger_result.to_dict())
                        skill_summary_history.append(
                            f"Skill: {current_skill.name}, iterations: {quick_proposer_iterations}"
                        )

                        current_skill = self.quick_proposer.propose_fix(
                            current_skill,
                            judger_result,
                            self.shallow_memory.get_trace(task_id)
                        )
                        skill_ids_tried.add(current_skill.skill_id)
                        quick_proposer_iterations += 1
                        judger_result = self._evaluate_with_judger(context, current_skill, current_judger_criteria)

                        if judger_result.passed:
                            judger_feedback_history.append(judger_result.to_dict())
                            break

                self._record_attempt(
                    context=context,
                    skill=current_skill,
                    judger_feedback=judger_result,
                    real_test_passed=None,
                    quick_proposer_iterations=quick_proposer_iterations,
                    research_triggered=True,
                    duration_seconds=0.0,
                    input_tokens=0,
                    cached_input_tokens=0,
                    output_tokens=0,
                )

                if not judger_result.passed:
                    judger_research_triggers += 1

                    if judger_research_triggers >= self.config.max_research_triggers_same_judger:
                        reflection_result = self._reflect_on_judger(
                            context=context,
                            judger_criteria=current_judger_criteria,
                            skill_summaries=skill_summary_history,
                            feedbacks=judger_feedback_history,
                            trigger_count=judger_research_triggers,
                        )
                        if reflection_result.get("diagnosis") == "judger_too_strict":
                            current_judger_criteria = self.judger.build_judger_criteria(
                                task_id, context.instruction_md[:200],
                                context.instruction_md,
                                []
                            )
                        judger_research_triggers = 0

                    research_output = self._research_new_skill(context)
                    if research_output.skill:
                        current_skill = research_output.skill
                        skill_ids_tried.add(current_skill.skill_id)

            if context:
                self._on_task_abandoned(task_id, context)
            return TaskStatus.ABANDONED
        except Exception as exc:
            run_record.failure_class = self._classify_unhandled_exception(exc)
            if context:
                self._on_task_abandoned(task_id, context)
            self._append_run_event(
                run_record,
                stage="runner_exception",
                passed=False,
                failure_class=run_record.failure_class,
                notes=str(exc),
            )
            return TaskStatus.ABANDONED
        finally:
            run_record.status = status
            run_record.real_test_failures = real_test_failures
            run_record.skills_tried = sorted(skill_ids_tried)
            run_record.finished_at = datetime.now(timezone.utc).isoformat()
            run_record.duration_seconds = time.monotonic() - started_monotonic
            if not run_record.final_model and run_record.events:
                for event in reversed(run_record.events):
                    if event.model:
                        run_record.final_model = event.model
                        break
            if not run_record.failure_class:
                run_record.failure_class = self._infer_failure_class(run_record)
            self.result_store.save(run_record)

    def _model_attempt(self, context: TaskContext) -> dict:
        """Run model on task without skill (initial attempt)."""
        # Run the task without any skill to see if model can solve it
        timeout_seconds = self._initial_attempt_timeout_seconds(context)
        result = self.docker.run_task(
            task_id=context.task_id,
            instruction=context.instruction_md,
            output_path=context.output_path,
            timeout=timeout_seconds,
            include_task_local_skills=self.config.base_attempt_include_task_skills,
        )

        return {
            "success": result.get("passed", False),
            "error": result.get("error", ""),
            "output": result.get("output", ""),
            "model": result.get("model", ""),
            "score": result.get("score", 0.0),
            "duration_seconds": result.get("duration_seconds", 0.0),
            "routing_reason": result.get("routing_reason", ""),
            "failure_class": result.get("failure_class", ""),
            "input_tokens": result.get("input_tokens", 0),
            "cached_input_tokens": result.get("cached_input_tokens", 0),
            "output_tokens": result.get("output_tokens", 0),
        }

    def _initial_attempt_timeout_seconds(self, context: TaskContext) -> int:
        """Choose a practical base-attempt timeout from config plus task metadata.

        Hard tasks can legitimately need longer uninterrupted execution time than the
        generic exploratory default. When task metadata already provides an agent
        timeout budget, prefer that budget within the system-wide real-test ceiling.
        """
        timeout_seconds = int(self.config.initial_attempt_timeout_seconds)
        task_toml = context.task_toml or {}

        agent_timeout = task_toml.get("agent", {}).get("timeout_sec")
        if agent_timeout is not None:
            try:
                timeout_seconds = max(timeout_seconds, int(float(agent_timeout)))
            except (TypeError, ValueError):
                pass

        difficulty = str(task_toml.get("metadata", {}).get("difficulty", "")).lower()
        if difficulty == "hard":
            timeout_seconds = max(timeout_seconds, 420)

        return min(timeout_seconds, int(self.config.real_test_timeout_seconds))

    def _load_task_context(self, task_id: str) -> Optional[TaskContext]:
        """Load task context from SkillsBench and analyze it."""
        task_dir = Path(self.config.skillsbench_root) / "tasks" / task_id
        if not task_dir.exists():
            return None

        instruction_md = (task_dir / "instruction.md").read_text()

        # Load task.toml
        task_toml = {}
        toml_path = task_dir / "task.toml"
        if toml_path.exists():
            try:
                import tomllib
                task_toml = tomllib.loads(toml_path.read_text())
            except Exception:
                pass

        tests_dir = str(task_dir / "tests")
        environment_dir = str(task_dir / "environment")

        # Analyze task to extract problem_type, domain, modeling
        analysis = self.task_analyzer.analyze(task_id, instruction_md, task_toml)

        return TaskContext(
            task_id=task_id,
            instruction_md=instruction_md,
            task_toml=task_toml,
            tests_dir=tests_dir,
            environment_dir=environment_dir,
            bundled_skills_summary=self._summarize_bundled_task_skills(task_id),
            output_path=self._infer_primary_output_path(instruction_md),
            execution_log_path="/tmp/execution.log",
            problem_type=analysis["problem_type"],
            domain=analysis["domain"],
            problem_modeling=analysis["problem_modeling"],
        )

    def _list_unsolved_tasks(self) -> list[str]:
        """List tasks that are not yet solved."""
        solved = set(self.task_memory.get_all_solved())
        tasks_dir = Path(self.config.skillsbench_root) / "tasks"
        all_tasks = [d.name for d in tasks_dir.iterdir() if d.is_dir()]
        return [t for t in all_tasks if t not in solved]

    def _find_reusable_skills(self, context: TaskContext) -> list[SkillBundle]:
        """Find potentially reusable skills from meta memory.

        Reuse condition: problem_type + domain + modeling all match or highly overlap.
        This is called when a new task fails and we want to try existing skills first.
        """
        skills: list[SkillBundle] = []
        seen: set[str] = set()

        for skill_id in self._ordered_task_skill_ids(context):
            skill = self.skill_repo.load_skill(context.task_id, skill_id)
            if not skill or skill.skill_id in seen:
                continue
            skills.append(skill)
            seen.add(skill.skill_id)

        if not context.problem_type:
            return skills

        transferable = self.meta_memory.get_transferable_skills(
            problem_type=context.problem_type,
            domain=context.domain or "general",
            modeling=context.problem_modeling or "direct_solution",
            min_transferability="medium",
        )

        for method in transferable:
            skill = self.shallow_memory.get_skill(method.method_id)
            if not skill or skill.skill_id in seen:
                continue
            skills.append(skill)
            seen.add(skill.skill_id)

        return skills

    def _ordered_task_skill_ids(self, context: TaskContext) -> list[str]:
        """Order task-local bundled skills, prioritizing task metadata requirements."""
        available = self.skill_repo.list_task_skills(context.task_id)
        if not available:
            return []

        metadata = context.task_toml.get("metadata", {}) if context.task_toml else {}
        required = [
            str(skill_id).strip()
            for skill_id in metadata.get("required_skills", [])
            if str(skill_id).strip()
        ]
        if not required:
            return available

        normalized_available = {self._normalize_skill_name(skill_id): skill_id for skill_id in available}
        prioritized: list[str] = []
        seen: set[str] = set()

        for required_skill in required:
            normalized = self._normalize_skill_name(required_skill)
            matched = normalized_available.get(normalized)
            if matched and matched not in seen:
                prioritized.append(matched)
                seen.add(matched)

        for skill_id in available:
            if skill_id not in seen:
                prioritized.append(skill_id)
                seen.add(skill_id)

        return prioritized

    def _normalize_skill_name(self, value: str) -> str:
        """Normalize skill identifiers for matching task metadata to directories."""
        return "".join(ch for ch in value.lower() if ch.isalnum())

    def _infer_primary_output_path(self, instruction_md: str) -> str:
        """Infer the main output artifact path from the task instruction."""
        absolute_paths = re.findall(
            r"(/(?:root|app|output|results|workspace|work|tmp|home)[^\s'\"`()<>]+)",
            instruction_md,
        )
        preferred_absolute = [
            path for path in absolute_paths
            if self._looks_like_output_artifact(path)
        ]
        if preferred_absolute:
            return preferred_absolute[0]

        lowered = instruction_md.lower()
        bare_matches = re.finditer(
            r"(?:write .*? to|save(?: your result| the result| result| answers)?(?: to| as)|output .*? in)\s+[`'\"]?([a-z0-9_./-]+\.(?:xlsx|csv|json|txt|md|ass|rttm|mp4))",
            lowered,
        )
        for match in bare_matches:
            candidate = match.group(1).strip()
            if self._looks_like_output_artifact(candidate):
                return candidate

        return ""

    def _looks_like_output_artifact(self, path: str) -> bool:
        """Heuristic to distinguish result artifacts from task inputs."""
        lowered = path.lower()
        output_markers = (
            "output", "answer", "result", "report", "annotation", "taxonomy",
            "subtitle", "diarization", "recovered", "detection",
        )
        input_markers = (
            "input", "background", "question", "problem.json", "data/",
            "domain", "problem", "paper.pdf", "source",
        )
        if any(marker in lowered for marker in input_markers):
            return False
        if any(marker in lowered for marker in output_markers):
            return True
        return lowered.endswith((".xlsx", ".csv", ".json", ".txt", ".md", ".ass", ".rttm", ".mp4"))

    def _try_skill(self, context: TaskContext, skill: SkillBundle) -> dict:
        """Try an existing skill on a task.

        Returns:
            {"passed": bool, "feedback": JudgerFeedback, "is_new": False}
        """
        # Execute skill with Judger evaluation
        judger_result = self._evaluate_with_judger(context, skill)

        if judger_result.passed:
            # Try real test
            real_result = self._run_real_test(context, skill)
            return {
                "passed": real_result.get("passed", False),
                "feedback": judger_result,
                "real_test_result": real_result,
                "is_new": False,
            }

        return {
            "passed": False,
            "feedback": judger_result,
            "is_new": False,
        }

    def _research_new_skill(self, context: TaskContext) -> ResearchOutput:
        """Research team creates new skill."""
        # Analyzer analyzes the problem
        analysis = self.analyzer.run(
            task_id=context.task_id,
            problem_type=context.problem_type.value if context.problem_type else "unknown",
            attempt_result="Initial research",
            trace_history=self.shallow_memory.get_trace(context.task_id),
        )

        # Query memory for context
        previously_tried = self._get_previously_tried_methods(context)
        ineffective_methods = self._get_ineffective_methods(context)
        effective_methods = self._get_effective_method_objects(context)
        effective_methods_summary = self._format_effective_methods(effective_methods)

        memory_context = {
            "previously_tried": previously_tried,
            "ineffective_methods": ineffective_methods,
            "effective_methods": effective_methods_summary,
            "bundled_task_skills": context.bundled_skills_summary or "No bundled task skills found.",
        }

        suggested_directions = analysis.get("suggested_directions", [])
        if isinstance(suggested_directions, str):
            problem_description = suggested_directions
        elif suggested_directions:
            problem_description = suggested_directions[0]
        else:
            problem_description = context.instruction_md

        # Searcher searches
        search_result = self.searcher.run(
            problem_description=problem_description,
            problem_type=context.problem_type.value if context.problem_type else "tool",
            domain=context.domain or "general",
            problem_modeling=context.problem_modeling or "direct_solution",
            memory_context=memory_context,
        )

        # Create skill
        skill = self.skill_creator.create_skill(
            task_id=context.task_id,
            problem_type=context.problem_type.value if context.problem_type else "tool",
            domain=context.domain or "general",
            problem_modeling=context.problem_modeling or "direct_solution",
            research_output=ResearchOutput(
                analysis=analysis.get("root_cause", ""),
                search_summary=self._summarize_search_result(search_result),
            ),
            effective_methods=effective_methods,
            bundled_task_skills=context.bundled_skills_summary,
        )

        # Critic reviews
        critic_result = self.critic.run(
            old_submission={},
            new_submission={"type": "skill", "content": skill.to_skill_md()},
        )

        if not critic_result.get("approved"):
            # Not approved - return empty
            return ResearchOutput(critic_feedback=critic_result.get("rejection_reason", ""))

        return ResearchOutput(
            skill=skill,
            analysis=analysis.get("root_cause", ""),
            search_summary=self._summarize_search_result(search_result),
            new_method=True,
            critic_approved=True,
        )

    def _summarize_search_result(self, search_result: dict) -> str:
        """Keep the most actionable parts of Searcher output for SkillCreator."""
        parts: list[str] = []
        search_summary = str(search_result.get("search_summary", "")).strip()
        if search_summary:
            parts.append(search_summary)
        recommended = str(search_result.get("recommended_approach", "")).strip()
        if recommended:
            parts.append(f"Recommended approach: {recommended}")
        relevant_knowledge = search_result.get("relevant_knowledge") or []
        if relevant_knowledge:
            trimmed = [str(item).strip() for item in relevant_knowledge if str(item).strip()]
            if trimmed:
                parts.append("Relevant knowledge:\n" + "\n".join(f"- {item}" for item in trimmed[:5]))
        return "\n\n".join(parts)

    def _get_previously_tried_methods(self, context: TaskContext) -> str:
        """Get methods previously tried for this task."""
        trace = self.shallow_memory.get_trace(context.task_id)
        if not trace:
            return "No previous attempts"
        tried = []
        for attempt in trace:
            tried.append(f"- {attempt.skill_id}: judger_passed={attempt.judger_passed}, real_test_passed={attempt.real_test_passed}")
        return "Previously tried methods:\n" + "\n".join(tried)

    def _get_ineffective_methods(self, context: TaskContext) -> str:
        """Get known ineffective methods from meta memory."""
        if not context.problem_type:
            return "No ineffective methods recorded"
        # Get all ineffective methods for this problem type
        meta = self.meta_memory.get(context.problem_type, context.domain or "general", context.problem_modeling or "direct_solution")
        if not meta or not meta.ineffective_methods:
            return "No ineffective methods recorded"
        result = "Known ineffective methods:\n"
        for method in meta.ineffective_methods:
            result += f"- {method.method_id}: {method.description} (failed on: {method.failed_tasks})\n"
        return result

    def _get_effective_methods(self, context: TaskContext) -> str:
        """Get transferable effective methods from meta memory as a summary."""
        return self._format_effective_methods(self._get_effective_method_objects(context))

    def _get_effective_method_objects(self, context: TaskContext) -> list[EffectiveMethod]:
        """Get transferable effective methods as typed objects."""
        if not context.problem_type:
            return []
        return self.meta_memory.get_transferable_skills(
            problem_type=context.problem_type,
            domain=context.domain or "general",
            modeling=context.problem_modeling or "direct_solution",
            min_transferability="low",  # Include low transferability for reference
        )

    def _format_effective_methods(self, methods: list[EffectiveMethod]) -> str:
        """Format effective methods for prompting."""
        if not methods:
            return "No effective methods recorded"
        result = "Known effective methods:\n"
        for method in methods:
            result += f"- {method.method_id}: {method.description} (transferability: {method.transferability})\n"
        return result

    def _summarize_bundled_task_skills(self, task_id: str) -> str:
        """Summarize skills already bundled with a task."""
        task_toml = {}
        toml_path = Path(self.config.skillsbench_root) / "tasks" / task_id / "task.toml"
        if toml_path.exists():
            try:
                import tomllib
                task_toml = tomllib.loads(toml_path.read_text())
            except Exception:
                task_toml = {}

        metadata = task_toml.get("metadata", {})
        required = [
            str(skill_id).strip()
            for skill_id in metadata.get("required_skills", [])
            if str(skill_id).strip()
        ]
        required_normalized = {self._normalize_skill_name(skill_id) for skill_id in required}
        skill_ids = self._ordered_task_skill_ids(
            TaskContext(
                task_id=task_id,
                instruction_md="",
                task_toml=task_toml,
                tests_dir="",
                environment_dir="",
            )
        )
        if not skill_ids:
            return "No bundled task skills found."

        summaries = []
        if required:
            summaries.append(
                "Task metadata marks these bundled skills as required or preferred: "
                + ", ".join(required)
            )
        for skill_id in skill_ids[:8]:
            skill = self.skill_repo.load_skill(task_id, skill_id)
            if skill is None:
                summaries.append(f"- {skill_id}: summary unavailable")
                continue
            parts = []
            if self._normalize_skill_name(skill_id) in required_normalized:
                parts.append("priority=required")
            if skill.description:
                parts.append(f"description={skill.description.strip().replace(chr(10), ' ')[:180]}")
            if skill.trigger_condition:
                parts.append(f"trigger={skill.trigger_condition.strip().replace(chr(10), ' ')[:180]}")
            if skill.usage:
                parts.append(f"usage={skill.usage.strip().replace(chr(10), ' ')[:180]}")
            if skill.scripts:
                file_list = ", ".join(sorted(skill.scripts)[:4])
                parts.append(f"files={file_list}")
            summaries.append(f"- {skill_id}: " + " | ".join(parts))

        return "Bundled task skills:\n" + "\n".join(summaries)

    def _record_attempt(
        self,
        context: TaskContext,
        skill: SkillBundle,
        judger_feedback: Optional[JudgerFeedback],
        real_test_passed: Optional[bool],
        quick_proposer_iterations: int,
        research_triggered: bool,
        note: str = "",
        duration_seconds: float = 0.0,
        input_tokens: int = 0,
        cached_input_tokens: int = 0,
        output_tokens: int = 0,
    ) -> None:
        """Persist attempt history even when the task is not solved yet."""
        blocking_issues: list[str] = []
        success_factors: list[str] = []
        judger_passed: Optional[bool] = None

        if judger_feedback is not None:
            judger_passed = judger_feedback.passed
            blocking_issues.extend(
                self._truncate_note(f"{issue.type}: {issue.description}", limit=180)
                for issue in judger_feedback.blocking_issues[:5]
            )
            success_factors.extend(
                self._truncate_note(signal, limit=180)
                for signal in judger_feedback.positive_signals[:5]
            )

        if note and real_test_passed is False:
            blocking_issues.append(self._truncate_note(f"real_test: {note}", limit=180))

        attempt = TaskAttempt(
            skill_id=skill.skill_id,
            quick_proposer_iterations=quick_proposer_iterations,
            research_triggered=research_triggered,
            judger_passed=judger_passed,
            real_test_passed=real_test_passed,
            duration_seconds=duration_seconds,
            input_tokens=input_tokens,
            cached_input_tokens=cached_input_tokens,
            output_tokens=output_tokens,
            blocking_issues=blocking_issues,
            success_factors=success_factors,
        )
        self.task_memory.ensure_task(
            task_id=context.task_id,
            problem_type=context.problem_type or ProblemType.TOOL,
            domain=context.domain,
            problem_modeling=context.problem_modeling,
        )
        self.task_memory.add_attempt(context.task_id, attempt)
        self.shallow_memory.add_trace(context.task_id, attempt)

    def _should_use_quick_proposer(self, judger_feedback: JudgerFeedback) -> bool:
        """Reserve QuickProposer for wording-sensitive failures, not execution failures."""
        if judger_feedback.recommendation == "abandon":
            return False

        operational_issue_types = {
            "constraint_violation",
            "missing_output",
            "wrong_format",
            "wrong_answer",
            "execution_error",
            "tool_error",
            "runtime_error",
            "timeout",
            "file_not_found",
            "module_not_found",
            "dependency_missing",
        }
        operational_markers = (
            "missing output",
            "wrong format",
            "wrong answer",
            "timed out",
            "timeout",
            "file not found",
            "module not found",
            "dependency",
            "runtime error",
            "execution failed",
            "constraint",
        )

        for issue in judger_feedback.blocking_issues:
            issue_type = (issue.type or "").strip().lower()
            description = issue.description.lower()
            suggestion = issue.suggestion.lower()
            if issue_type in operational_issue_types:
                return False
            combined = f"{description}\n{suggestion}"
            if any(marker in combined for marker in operational_markers):
                return False
        return True

    def _evaluate_with_judger(self, context: TaskContext, skill: SkillBundle,
                               criteria: Optional[dict] = None) -> JudgerFeedback:
        """Evaluate skill with Judger.

        Args:
            criteria: Optional stricter criteria from build_judger_criteria.
        """
        # Execute skill to get result (placeholder)
        execution_result = self._execute_skill(skill, context)

        return self.judger.evaluate(
            task_id=context.task_id,
            problem_description=context.instruction_md[:200],
            instruction=context.instruction_md,
            skill_description=skill.description,
            execution_result=execution_result,
            criteria=criteria,
        )

    def _execute_skill(self, skill: SkillBundle, context: TaskContext) -> str:
        """Execute skill in Docker and return terminal output."""
        result = self.docker.execute_skill(
            task_id=context.task_id,
            skill=skill,
            instruction=context.instruction_md,
            output_path=context.output_path,
            timeout=self.config.skill_execution_timeout_seconds,
        )

        if result["success"]:
            return result["execution_log"]
        else:
            return f"Error: {result['error']}\n{result['execution_log']}"

    def _run_real_test(self, context: TaskContext, skill: SkillBundle) -> dict:
        """Run real test using SkillsBench official test script."""
        # First save skill to the task's skills directory
        self.skill_repo.save_skill(context.task_id, skill)

        # Run official test
        result = self.docker.run_real_test(
            task_id=context.task_id,
            instruction=context.instruction_md,
            skill=skill,
            timeout=self.config.real_test_timeout_seconds,
        )

        return {
            "passed": result["passed"],
            "score": result["score"],
            "details": result["details"],
            "exit_code": result.get("exit_code", -1),
            "model": result.get("model", ""),
            "reasoning_effort": result.get("reasoning_effort", ""),
            "execution_duration_seconds": result.get("execution_duration_seconds", 0.0),
            "test_duration_seconds": result.get("test_duration_seconds", 0.0),
            "duration_seconds": result.get("duration_seconds", 0.0),
            "difficulty": result.get("difficulty", ""),
            "routing_reason": result.get("routing_reason", ""),
            "failure_class": result.get("failure_class", ""),
            "input_tokens": result.get("input_tokens", 0),
            "cached_input_tokens": result.get("cached_input_tokens", 0),
            "output_tokens": result.get("output_tokens", 0),
        }

    def _reflect_on_judger(
        self,
        context: TaskContext,
        judger_criteria: Optional[dict],
        skill_summaries: list[str],
        feedbacks: list[dict],
        trigger_count: int,
    ) -> dict:
        """Reflect on Judger when stuck.

        Called when same Judger has triggered Research 2x without any judger pass
        reaching real test. Analyzes whether Judger is too strict.
        """
        # Use Reflector agent to analyze
        result = self.reflector.run(
            task_id=context.task_id,
            judger_criteria=judger_criteria or {},
            skill_summaries=skill_summaries,
            feedbacks=feedbacks[-5:] if feedbacks else [],  # Last 5 feedbacks
            trigger_count=trigger_count,
        )

        # Record reflection in meta memory if it suggests adjustment
        if result.get("diagnosis") == "judger_too_strict":
            self.meta_memory.add_success_factor(
                problem_type=context.problem_type or ProblemType.TOOL,
                domain=context.domain or "general",
                modeling=context.problem_modeling or "direct_solution",
                factor=f"Judger反思: {result.get('reasoning', '')} - 调整: {result.get('adjustments', [])}",
            )

        return result

    def _on_task_solved(self, task_id: str, context: TaskContext, skill: SkillBundle) -> None:
        """Handle successful task resolution."""
        # Analyze why this skill worked
        why_worked = self._analyze_success(context, skill)

        # Update task memory
        self.task_memory.ensure_task(
            task_id=task_id,
            problem_type=context.problem_type or ProblemType.TOOL,
            domain=context.domain,
            problem_modeling=context.problem_modeling,
        )
        self.task_memory.update_final_status(
            task_id=task_id,
            status=TaskStatus.SOLVED,
            what_worked=skill.description,
            why_worked=why_worked,
            effective_skill_id=skill.skill_id,
        )

        # Determine transferability based on problem type
        transferability = self._estimate_transferability(context, skill)

        # Update meta memory
        effective_method = EffectiveMethod(
            method_id=skill.skill_id,
            description=skill.description,
            origin_task=task_id,
            transferability=transferability,
            conditions=f"problem_type={context.problem_type.value if context.problem_type else 'unknown'}, domain={context.domain}, modeling={context.problem_modeling}",
        )
        self.meta_memory.add_effective_method(
            problem_type=context.problem_type or ProblemType.TOOL,
            domain=context.domain or "general",
            modeling=context.problem_modeling or "direct_solution",
            method=effective_method,
        )

        # Save skill to repo
        self.skill_repo.save_skill(task_id, skill)
        self.shallow_memory.add_skill(skill)

        # Update shallow memory
        attempt = TaskAttempt(
            skill_id=skill.skill_id,
            quick_proposer_iterations=0,
            research_triggered=True,
            judger_passed=True,
            real_test_passed=True,
        )
        self.shallow_memory.add_trace(task_id, attempt)

    def _on_base_model_solved(self, task_id: str, context: TaskContext, attempt_result: dict) -> None:
        """Handle tasks solved without any external skill."""
        self.task_memory.ensure_task(
            task_id=task_id,
            problem_type=context.problem_type or ProblemType.TOOL,
            domain=context.domain,
            problem_modeling=context.problem_modeling,
        )
        model = attempt_result.get("model", "")
        routing_reason = attempt_result.get("routing_reason", "")
        what_worked = "Solved without external skill"
        if model:
            what_worked += f" using {model}"
        why_worked = self._truncate_note(
            "; ".join(
                part for part in [
                    "base model solved the task directly",
                    f"problem_type={context.problem_type.value if context.problem_type else 'unknown'}",
                    f"domain={context.domain}" if context.domain else "",
                    f"problem_modeling={context.problem_modeling}" if context.problem_modeling else "",
                    f"routing={routing_reason}" if routing_reason else "",
                ]
                if part
            ),
            limit=400,
        )
        self.task_memory.update_final_status(
            task_id=task_id,
            status=TaskStatus.SOLVED,
            what_worked=what_worked,
            why_worked=why_worked,
            effective_skill_id="",
        )
        self.shallow_memory.add_trace(
            task_id,
            TaskAttempt(
                skill_id="__base_model__",
                quick_proposer_iterations=0,
                research_triggered=False,
                judger_passed=True,
                real_test_passed=True,
                duration_seconds=attempt_result.get("duration_seconds", 0.0),
                input_tokens=attempt_result.get("input_tokens", 0),
                cached_input_tokens=attempt_result.get("cached_input_tokens", 0),
                output_tokens=attempt_result.get("output_tokens", 0),
                success_factors=[why_worked],
            ),
        )

    def _maybe_optimize_after_success(
        self,
        context: TaskContext,
        baseline_result: dict,
        baseline_skill: Optional[SkillBundle],
        run_record: BenchmarkRunRecord,
    ) -> None:
        """Optionally evolve a lower-cost skill after correctness is already proven."""
        rounds = max(0, int(self.config.post_solve_optimization_rounds))
        if rounds <= 0:
            return

        current_skill = baseline_skill or self._select_post_solve_candidate_skill(context)
        baseline_source = "skill_pass" if baseline_skill is not None else "base_model_pass"
        current_result = baseline_result
        optimization_feedback: list[str] = []
        if current_skill is None:
            return

        for round_index in range(1, rounds + 1):
            optimized_skill = self.skill_creator.optimize_skill(
                task_id=context.task_id,
                problem_type=context.problem_type.value if context.problem_type else "tool",
                domain=context.domain or "general",
                problem_modeling=context.problem_modeling or "direct_solution",
                current_skill=current_skill,
                success_summary=self._build_success_summary(current_result),
                bundled_task_skills=context.bundled_skills_summary,
                duration_seconds=float(current_result.get("duration_seconds", 0.0) or 0.0),
                input_tokens=int(current_result.get("input_tokens", 0) or 0),
                cached_input_tokens=int(current_result.get("cached_input_tokens", 0) or 0),
                output_tokens=int(current_result.get("output_tokens", 0) or 0),
                baseline_source=baseline_source,
                instruction_excerpt=self._truncate_note(context.instruction_md, limit=1600),
                failure_feedback=self._format_optimization_feedback(
                    baseline_source=baseline_source,
                    feedback_items=optimization_feedback,
                ),
                skill_id=f"{current_skill.skill_id}-opt{round_index}",
            )

            critic_result = self.critic.run(
                old_submission={"type": "skill", "content": current_skill.to_skill_md()},
                new_submission={"type": "skill", "content": optimized_skill.to_skill_md()},
            )
            if not critic_result.get("approved"):
                optimization_feedback.append(
                    self._summarize_optimization_feedback(
                        round_index=round_index,
                        skill=optimized_skill,
                        critic_note=critic_result.get("rejection_reason", critic_result.get("reason", "")),
                    )
                )
                self._append_run_event(
                    run_record,
                    stage=f"post_solve_optimize_round_{round_index}",
                    passed=False,
                    skill_id=optimized_skill.skill_id,
                    notes=critic_result.get("rejection_reason", critic_result.get("reason", "")),
                )
                continue

            self.shallow_memory.add_skill(optimized_skill)
            trial = self._try_skill(context, optimized_skill)
            real_result = trial.get("real_test_result") or {}
            if real_result:
                self._append_real_test_event(run_record, optimized_skill.skill_id, real_result)

            self._record_attempt(
                context=context,
                skill=optimized_skill,
                judger_feedback=trial.get("feedback"),
                real_test_passed=real_result.get("passed") if real_result else None,
                quick_proposer_iterations=0,
                research_triggered=False,
                note=real_result.get("details", "") if real_result else "",
                duration_seconds=real_result.get("duration_seconds", 0.0) if real_result else 0.0,
                input_tokens=real_result.get("input_tokens", 0) if real_result else 0,
                cached_input_tokens=real_result.get("cached_input_tokens", 0) if real_result else 0,
                output_tokens=real_result.get("output_tokens", 0) if real_result else 0,
            )

            improved, comparison_summary = self._compare_optimization_results(
                baseline_result=current_result,
                candidate_result=real_result,
                baseline_skill=current_skill,
                candidate_skill=optimized_skill,
            )
            self._append_run_event(
                run_record,
                stage=f"post_solve_optimize_round_{round_index}",
                passed=improved,
                model=real_result.get("model", ""),
                score=real_result.get("score", 0.0),
                duration_seconds=real_result.get("duration_seconds", 0.0),
                failure_class=real_result.get("failure_class", ""),
                skill_id=optimized_skill.skill_id,
                routing_reason=real_result.get("routing_reason", ""),
                input_tokens=real_result.get("input_tokens", 0),
                cached_input_tokens=real_result.get("cached_input_tokens", 0),
                output_tokens=real_result.get("output_tokens", 0),
                notes=comparison_summary,
            )

            if not improved:
                optimization_feedback.append(
                    self._summarize_optimization_feedback(
                        round_index=round_index,
                        skill=optimized_skill,
                        judger_feedback=trial.get("feedback"),
                        real_result=real_result,
                        comparison_summary=comparison_summary,
                    )
                )
                continue

            self._register_optimized_skill_success(
                context=context,
                skill=optimized_skill,
                comparison_summary=comparison_summary,
                update_task_memory=baseline_skill is not None,
            )
            current_skill = optimized_skill
            current_result = real_result
            baseline_source = "skill_pass"

    def _select_post_solve_candidate_skill(self, context: TaskContext) -> Optional[SkillBundle]:
        """Choose a bundled skill to optimize after a base-model solve."""
        for skill_id in self._ordered_task_skill_ids(context):
            skill = self.skill_repo.load_skill(context.task_id, skill_id)
            if skill is not None:
                return skill
        return None

    def _build_success_summary(self, result: dict) -> str:
        """Create a compact success summary for post-solve optimization prompts."""
        parts = []
        details = str(result.get("details", "") or "").strip()
        if details:
            parts.append(self._truncate_note(details, limit=1200))

        duration_seconds = float(result.get("duration_seconds", 0.0) or 0.0)
        input_tokens = int(result.get("input_tokens", 0) or 0)
        cached_input_tokens = int(result.get("cached_input_tokens", 0) or 0)
        output_tokens = int(result.get("output_tokens", 0) or 0)
        if duration_seconds or input_tokens or output_tokens:
            parts.append(
                "Performance:"
                f" duration_seconds={duration_seconds:.2f},"
                f" input_tokens={input_tokens},"
                f" cached_input_tokens={cached_input_tokens},"
                f" output_tokens={output_tokens}"
            )

        return "\n\n".join(parts) if parts else "Successful execution with no additional summary."

    def _format_optimization_feedback(
        self,
        baseline_source: str,
        feedback_items: list[str],
    ) -> str:
        """Format the latest optimization-loop feedback for the next candidate."""
        intro = (
            "Baseline passed with an external skill."
            if baseline_source == "skill_pass"
            else "Baseline passed without an external skill; distill the successful behavior into a reusable skill."
        )
        if not feedback_items:
            return intro
        joined = "\n\n".join(feedback_items[-3:])
        return f"{intro}\n\nRecent optimization failures or regressions:\n{joined}"

    def _summarize_optimization_feedback(
        self,
        round_index: int,
        skill: SkillBundle,
        critic_note: str = "",
        judger_feedback: Optional[JudgerFeedback] = None,
        real_result: Optional[dict] = None,
        comparison_summary: str = "",
    ) -> str:
        """Compress candidate failure feedback for the next optimization round."""
        parts = [f"Round {round_index} candidate: {skill.skill_id}"]
        if critic_note:
            parts.append(f"critic: {self._truncate_note(critic_note, limit=240)}")
        if judger_feedback is not None:
            for issue in judger_feedback.blocking_issues[:3]:
                parts.append(
                    self._truncate_note(
                        f"judger {issue.type}: {issue.description}",
                        limit=240,
                    )
                )
        if real_result:
            failure_class = str(real_result.get("failure_class", "") or "").strip()
            details = str(real_result.get("details", "") or "").strip()
            if failure_class:
                parts.append(f"real_test failure_class={failure_class}")
            if details:
                parts.append(
                    self._truncate_note(
                        f"real_test details: {details}",
                        limit=280,
                    )
                )
        if comparison_summary:
            parts.append(self._truncate_note(f"comparison: {comparison_summary}", limit=220))
        return "\n".join(parts)

    def _compare_optimization_results(
        self,
        baseline_result: dict,
        candidate_result: dict,
        baseline_skill: SkillBundle,
        candidate_skill: SkillBundle,
    ) -> tuple[bool, str]:
        """Decide whether a post-solve optimized skill is materially better."""
        if not candidate_result.get("passed"):
            return False, "candidate failed official real test"

        improvements: list[str] = []
        regressions: list[str] = []
        notes: list[str] = []
        cost_improved = False

        baseline_duration = float(baseline_result.get("duration_seconds", 0.0) or 0.0)
        candidate_duration = float(candidate_result.get("duration_seconds", 0.0) or 0.0)
        if baseline_duration > 0 and candidate_duration > 0:
            if candidate_duration <= baseline_duration * 0.9:
                improvements.append(
                    f"duration {baseline_duration:.2f}s -> {candidate_duration:.2f}s"
                )
                cost_improved = True
            elif candidate_duration > baseline_duration * 1.15:
                regressions.append(
                    f"duration regressed {baseline_duration:.2f}s -> {candidate_duration:.2f}s"
                )

        baseline_tokens = self._total_tokens(baseline_result)
        candidate_tokens = self._total_tokens(candidate_result)
        if baseline_tokens > 0 and candidate_tokens > 0:
            if candidate_tokens <= int(baseline_tokens * 0.9):
                improvements.append(f"tokens {baseline_tokens} -> {candidate_tokens}")
                cost_improved = True
            elif candidate_tokens > int(baseline_tokens * 1.15):
                regressions.append(f"tokens regressed {baseline_tokens} -> {candidate_tokens}")

        baseline_skill_size = len(baseline_skill.to_skill_md())
        candidate_skill_size = len(candidate_skill.to_skill_md())
        if candidate_skill_size <= int(baseline_skill_size * 0.75):
            improvements.append(f"skill_md_size {baseline_skill_size} -> {candidate_skill_size}")
        elif candidate_skill_size > int(baseline_skill_size * 1.15):
            size_note = f"skill_md_size regressed {baseline_skill_size} -> {candidate_skill_size}"
            # Prompt size matters, but it should not outweigh large real runtime/token wins
            # that are already measured on the official task execution path.
            if cost_improved:
                notes.append(size_note)
            else:
                regressions.append(size_note)

        if regressions:
            details = regressions + improvements + notes
            return False, "; ".join(details) if details else "candidate regressed"
        if improvements:
            return True, "; ".join(improvements + notes)
        return False, "candidate passed but showed no material runtime/token/size improvement"

    def _register_optimized_skill_success(
        self,
        context: TaskContext,
        skill: SkillBundle,
        comparison_summary: str,
        update_task_memory: bool,
    ) -> None:
        """Persist an optimized skill that improved over an already passing baseline."""
        self.skill_repo.save_skill(context.task_id, skill)
        self.shallow_memory.add_skill(skill)

        effective_method = EffectiveMethod(
            method_id=skill.skill_id,
            description=self._truncate_note(
                f"{skill.description} Optimized after successful solve. {comparison_summary}",
                limit=300,
            ),
            origin_task=context.task_id,
            transferability=self._estimate_transferability(context, skill),
            conditions=f"post_solve_optimization on task={context.task_id}",
        )
        self.meta_memory.add_effective_method(
            problem_type=context.problem_type or ProblemType.TOOL,
            domain=context.domain or "general",
            modeling=context.problem_modeling or "direct_solution",
            method=effective_method,
        )
        self.meta_memory.add_success_factor(
            problem_type=context.problem_type or ProblemType.TOOL,
            domain=context.domain or "general",
            modeling=context.problem_modeling or "direct_solution",
            factor=self._truncate_note(
                f"post_solve_optimization: {comparison_summary}",
                limit=240,
            ),
        )

        if update_task_memory:
            self.task_memory.update_final_status(
                task_id=context.task_id,
                status=TaskStatus.SOLVED,
                what_worked=skill.description,
                why_worked=self._truncate_note(comparison_summary, limit=400),
                effective_skill_id=skill.skill_id,
            )

    def _total_tokens(self, result: dict) -> int:
        """Return a simple token proxy for optimization comparisons."""
        return int(result.get("input_tokens", 0) or 0) + int(result.get("output_tokens", 0) or 0)

    def _append_run_event(
        self,
        run_record: BenchmarkRunRecord,
        stage: str,
        passed: bool,
        model: str = "",
        score: float = 0.0,
        duration_seconds: float = 0.0,
        failure_class: str = "",
        skill_id: str = "",
        routing_reason: str = "",
        input_tokens: int = 0,
        cached_input_tokens: int = 0,
        output_tokens: int = 0,
        notes: str = "",
    ) -> None:
        """Attach a compact event record to the task run."""
        run_record.events.append(
            BenchmarkRunEvent(
                stage=stage,
                passed=passed,
                model=model,
                score=score,
                duration_seconds=duration_seconds,
                failure_class=failure_class,
                skill_id=skill_id,
                routing_reason=routing_reason,
                input_tokens=input_tokens,
                cached_input_tokens=cached_input_tokens,
                output_tokens=output_tokens,
                notes=self._truncate_note(notes),
            )
        )

    def _append_real_test_event(
        self,
        run_record: BenchmarkRunRecord,
        skill_id: str,
        real_result: dict,
    ) -> None:
        """Record a real-test outcome for later analysis."""
        self._append_run_event(
            run_record,
            stage="real_test",
            passed=real_result.get("passed", False),
            model=real_result.get("model", ""),
            score=real_result.get("score", 0.0),
            duration_seconds=real_result.get("duration_seconds", 0.0),
            failure_class=real_result.get("failure_class", ""),
            skill_id=skill_id,
            routing_reason=real_result.get("routing_reason", ""),
            input_tokens=real_result.get("input_tokens", 0),
            cached_input_tokens=real_result.get("cached_input_tokens", 0),
            output_tokens=real_result.get("output_tokens", 0),
            notes=real_result.get("details", ""),
        )

    def _truncate_note(self, text: str, limit: int = 600) -> str:
        """Keep persisted notes compact."""
        if not text:
            return ""
        normalized = " ".join(str(text).split())
        if len(normalized) <= limit:
            return normalized
        return normalized[: limit - 3] + "..."

    def _infer_failure_class(self, run_record: BenchmarkRunRecord) -> str:
        """Infer a final failure class from persisted events."""
        if run_record.status == TaskStatus.SOLVED:
            return ""
        for event in reversed(run_record.events):
            if event.failure_class:
                return event.failure_class
        return "abandoned_without_classification"

    def _classify_unhandled_exception(self, exc: Exception) -> str:
        """Map unexpected task-run exceptions into compact failure classes."""
        lowered = str(exc).lower()
        if "protocolerror" in lowered or "incompleteread" in lowered or "connection broken" in lowered:
            return "docker_transport_error"
        if "permission denied" in lowered:
            return "permission_error"
        return exc.__class__.__name__.lower()

    def _on_task_abandoned(self, task_id: str, context: TaskContext) -> None:
        """Handle task abandonment."""
        self.task_memory.ensure_task(
            task_id=task_id,
            problem_type=context.problem_type or ProblemType.TOOL,
            domain=context.domain,
            problem_modeling=context.problem_modeling,
        )
        self.task_memory.update_final_status(
            task_id=task_id,
            status=TaskStatus.ABANDONED,
        )

        # Record ineffective method with context info for future avoidance
        ineffective_method = IneffectiveMethod(
            method_id="unknown",
            description=f"problem_type={context.problem_type.value if context.problem_type else 'unknown'}, domain={context.domain}, modeling={context.problem_modeling}",
            failed_tasks=[task_id],
            failure_reason="Could not solve within limits",
        )
        self.meta_memory.add_ineffective_method(
            problem_type=context.problem_type or ProblemType.TOOL,
            domain=context.domain or "general",
            modeling=context.problem_modeling or "direct_solution",
            method=ineffective_method,
        )

    def _analyze_success(self, context: TaskContext, skill: SkillBundle) -> str:
        """Analyze why a skill worked for this task."""
        # Build analysis based on task and skill characteristics
        factors = []

        # Problem type factor
        if context.problem_type:
            factors.append(f"problem_type={context.problem_type.value}")

        # Domain factor
        if context.domain:
            factors.append(f"domain={context.domain}")

        # Modeling factor
        if context.problem_modeling:
            factors.append(f"problem_modeling={context.problem_modeling}")

        # Skill characteristics
        if skill.trigger_condition:
            factors.append(f"trigger={skill.trigger_condition[:50]}")

        return "; ".join(factors) if factors else "Skill succeeded on task"

    def _estimate_transferability(self, context: TaskContext, skill: SkillBundle) -> str:
        """Estimate how transferable this skill/method is to similar tasks."""
        # Higher transferability if:
        # 1. Problem type is KNOWLEDGE (methods are more general)
        # 2. Domain is broader/more common
        # 3. Modeling is more generic

        if context.problem_type == ProblemType.KNOWLEDGE:
            return "high"

        # Tool bottleneck methods tend to be more specific
        if context.domain in ("code_generation", "tool_use", "reasoning_about_tools"):
            return "medium"

        # Very specific modeling suggests lower transferability
        if context.problem_modeling and any(x in context.problem_modeling.lower() for x in ["specific", "narrow", "exact"]):
            return "low"

        return "medium"
