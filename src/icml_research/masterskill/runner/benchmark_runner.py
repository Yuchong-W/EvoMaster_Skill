"""Benchmark Runner - orchestrates the full benchmark workflow."""

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
                notes=attempt_result.get("error", ""),
            )
            if attempt_result.get("success"):
                self._on_base_model_solved(task_id, context, attempt_result)
                status = TaskStatus.SOLVED
                run_record.final_score = 1.0
                run_record.final_model = attempt_result.get("model", "")
                return status

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
                    if real_result:
                        self._append_real_test_event(run_record, skill.skill_id, real_result)
                    if result.get("passed"):
                        self._on_task_solved(task_id, context, skill)
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
                    self._append_real_test_event(run_record, current_skill.skill_id, real_result)

                    if real_result.get("passed"):
                        self._on_task_solved(task_id, context, current_skill)
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
        result = self.docker.run_task(
            task_id=context.task_id,
            instruction=context.instruction_md,
            output_path=context.output_path,
            timeout=self.config.initial_attempt_timeout_seconds,
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
        }

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
            output_path="",
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
        if not context.problem_type:
            return []

        # Query meta memory for transferable skills
        transferable = self.meta_memory.get_transferable_skills(
            problem_type=context.problem_type,
            domain=context.domain or "general",
            modeling=context.problem_modeling or "direct_solution",
            min_transferability="medium",
        )

        skills = []
        for method in transferable:
            # Load the actual skill from shallow memory
            skill = self.shallow_memory.get_skill(method.method_id)
            if skill:
                skills.append(skill)

        return skills

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
                search_summary=search_result.get("search_summary", ""),
            ),
            effective_methods=effective_methods,
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
            search_summary=search_result.get("search_summary", ""),
            new_method=True,
            critic_approved=True,
        )

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
                success_factors=[why_worked],
            ),
        )

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
