"""Benchmark Runner - orchestrates the full benchmark workflow."""

import uuid
from pathlib import Path
from typing import Optional
import subprocess

from ..core.types import (
    Config, TaskContext, SkillBundle, JudgerFeedback,
    TaskStatus, TaskAttempt, ResearchOutput,
    ProblemType, EffectiveMethod, IneffectiveMethod,
)
from ..memory import ShallowMemory, TaskExperienceMemory, MetaMemoryStore
from ..memory_manager import MemoryManager, AgentRole
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
    11. If same Judger triggers 3x Research with no real test -> reflect
    12. After 4 real test failures -> abandon task
    """

    def __init__(self, config: Config):
        self.config = config

        # Initialize memory
        data_dir = config.data_root or str(Path(config.skillsbench_root) / "data")
        self.shallow_memory = ShallowMemory(f"{data_dir}/shallow")
        self.task_memory = TaskExperienceMemory(f"{data_dir}/task_experience")
        self.meta_memory = MetaMemoryStore(f"{data_dir}/meta")

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
        # Load task context
        context = self._load_task_context(task_id)
        if not context:
            return TaskStatus.ABANDONED

        # Step 1: Model attempts task -> fails
        attempt_result = self._model_attempt(context)
        if attempt_result.get("success"):
            return TaskStatus.SOLVED

        # Analyze failure
        failure_analysis = self.analyzer.run(
            task_id=task_id,
            problem_type=context.problem_type or "unknown",
            attempt_result=str(attempt_result.get("error", "model failed")),
            trace_history=self.shallow_memory.get_trace(task_id),
            judger_feedback=None,
        )

        # Determine problem type
        problem_type = failure_analysis.get("problem_type_refinement", "tool_bottleneck")
        context.problem_type = ProblemType(problem_type) if problem_type else ProblemType.TOOL

        # Initialize counters
        real_test_failures = 0
        judger_research_triggers = 0
        current_skill: Optional[SkillBundle] = None
        current_judger_criteria: Optional[dict] = None

        # Track history for reflection
        judger_feedback_history: list[dict] = []
        skill_summary_history: list[str] = []

        # Step 2: Try existing skills (试探性复用)
        existing_skills = self._find_reusable_skills(context)
        if existing_skills:
            # Try each existing skill
            for skill in existing_skills:
                result = self._try_skill(context, skill)
                if result.get("passed"):
                    self._on_task_solved(task_id, context, skill)
                    return TaskStatus.SOLVED

        # Step 3: Need new skill - Research builds Skill + Judger (parallel)
        research_output = self._research_new_skill(context)
        if not research_output.skill:
            # Research failed
            return TaskStatus.ABANDONED

        current_skill = research_output.skill

        # Step 4: Quick Proposer / Judger loop
        while real_test_failures < self.config.max_real_test_failures:
            # Test current skill with Judger
            judger_result = self._evaluate_with_judger(context, current_skill)

            if judger_result.pass:
                # Judger passed -> real test
                real_result = self._run_real_test(context, current_skill)

                if real_result.get("passed"):
                    # Success!
                    self._on_task_solved(task_id, context, current_skill)
                    return TaskStatus.SOLVED
                else:
                    # Real test failed
                    real_test_failures += 1
                    judger_research_triggers = 0  # Reset for new Judger

                    if real_test_failures >= self.config.max_real_test_failures:
                        # Max failures reached
                        self._on_task_abandoned(task_id, context)
                        return TaskStatus.ABANDONED

                    # Need stricter Judger
                    current_judger_criteria = self.judger.build_judger_criteria(
                        task_id, context.instruction_md[:200],
                        context.instruction_md,
                        []
                    )
                    # Continue loop to try again with stricter criteria
            else:
                # Judger failed -> Quick Proposer
                quick_proposer_iterations = 0
                judger_failures = 0

                while quick_proposer_iterations < self.config.max_quick_proposer_iterations:
                    # Track feedback
                    judger_feedback_history.append(judger_result.to_dict())
                    skill_summary_history.append(
                        f"Skill: {current_skill.name}, iterations: {quick_proposer_iterations}"
                    )

                    # Quick Proposer fix
                    current_skill = self.quick_proposer.propose_fix(
                        current_skill,
                        judger_result,
                        self.shallow_memory.get_trace(task_id)
                    )
                    quick_proposer_iterations += 1

                    # Re-evaluate with Judger
                    judger_result = self._evaluate_with_judger(context, current_skill)

                    if judger_result.pass:
                        # Break to real test
                        judger_feedback_history.append(judger_result.to_dict())
                        break
                    else:
                        judger_failures += 1

                # Check if stuck at Judger
                if not judger_result.pass:
                    # Quick proposer exhausted -> Research
                    judger_research_triggers += 1

                    if judger_research_triggers >= self.config.max_research_triggers_same_judger:
                        # Need to reflect on Judger
                        reflection_result = self._reflect_on_judger(
                            context=context,
                            judger_criteria=current_judger_criteria,
                            skill_summaries=skill_summary_history,
                            feedbacks=judger_feedback_history,
                            trigger_count=judger_research_triggers,
                        )
                        # If reflection suggests Judger is wrong, adjust criteria
                        if reflection_result.get("diagnosis") == "judger_too_strict":
                            # Rebuild criteria with looser standards
                            current_judger_criteria = self.judger.build_judger_criteria(
                                task_id, context.instruction_md[:200],
                                context.instruction_md,
                                judger_feedback_history[-3:] if judger_feedback_history else []
                            )
                        judger_research_triggers = 0

                    # Research new approach
                    research_output = self._research_new_skill(context)
                    if research_output.skill:
                        current_skill = research_output.skill
                        judger_research_triggers = 0  # Reset

        return TaskStatus.ABANDONED

    def _model_attempt(self, context: TaskContext) -> dict:
        """Run model on task without skill (initial attempt)."""
        # Run the task without any skill to see if model can solve it
        result = self.docker.run_task(
            task_id=context.task_id,
            instruction=context.instruction_md,
            output_path=context.output_path,
        )

        return {
            "success": result.get("passed", False),
            "error": result.get("error", ""),
            "output": result.get("output", ""),
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
            output_path="/root/output.json",
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

        if judger_result.pass:
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
            problem_type=context.problem_type or "unknown",
            attempt_result="Initial research",
            trace_history=self.shallow_memory.get_trace(context.task_id),
        )

        # Get memory context for Searcher
        memory_context = {
            "previously_tried": "TODO: query task memory",
            "ineffective_methods": "TODO: query meta memory",
            "effective_methods": "TODO: query meta memory",
        }

        # Searcher searches
        search_result = self.searcher.run(
            problem_description=analysis.get("suggested_directions", [context.instruction_md])[0],
            problem_type=context.problem_type.value if context.problem_type else "tool",
            domain="TODO: extract from task",
            problem_modeling="TODO: extract from task",
            memory_context=memory_context,
        )

        # Create skill
        skill = self.skill_creator.create_skill(
            task_id=context.task_id,
            problem_type=context.problem_type.value if context.problem_type else "tool",
            domain="TODO",
            problem_modeling="TODO",
            research_output=ResearchOutput(
                analysis=analysis.get("root_cause", ""),
                search_summary=search_result.get("search_summary", ""),
            ),
            effective_methods=[],
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

    def _evaluate_with_judger(self, context: TaskContext, skill: SkillBundle) -> JudgerFeedback:
        """Evaluate skill with Judger."""
        # Execute skill to get result (placeholder)
        execution_result = self._execute_skill(skill, context)

        return self.judger.evaluate(
            task_id=context.task_id,
            problem_description=context.instruction_md[:200],
            instruction=context.instruction_md,
            skill_description=skill.description,
            execution_result=execution_result,
        )

    def _execute_skill(self, skill: SkillBundle, context: TaskContext) -> str:
        """Execute skill in Docker and return terminal output."""
        result = self.docker.execute_skill(
            task_id=context.task_id,
            skill=skill,
            instruction=context.instruction_md,
            output_path=context.output_path,
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
            output_path=context.output_path,
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

        Called when same Judger has triggered Research 3x without any skill
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
        # Update task memory
        self.task_memory.update_final_status(
            task_id=task_id,
            status=TaskStatus.SOLVED,
            what_worked=skill.description,
            why_worked="TODO: analyze",
            effective_skill_id=skill.skill_id,
        )

        # Update meta memory
        effective_method = EffectiveMethod(
            method_id=skill.skill_id,
            description=skill.description,
            origin_task=task_id,
            transferability="medium",
            conditions="TODO",
        )
        self.meta_memory.add_effective_method(
            problem_type=context.problem_type or ProblemType.TOOL,
            domain="TODO",
            modeling="TODO",
            method=effective_method,
        )

        # Save skill to repo
        self.skill_repo.save_skill(task_id, skill)

        # Update shallow memory
        attempt = TaskAttempt(
            skill_id=skill.skill_id,
            quick_proposer_iterations=0,
            research_triggered=True,
            judger_passed=True,
            real_test_passed=True,
        )
        self.shallow_memory.add_trace(task_id, attempt)

    def _on_task_abandoned(self, task_id: str, context: TaskContext) -> None:
        """Handle task abandonment."""
        self.task_memory.update_final_status(
            task_id=task_id,
            status=TaskStatus.ABANDONED,
        )

        # Record ineffective method
        ineffective_method = IneffectiveMethod(
            method_id="unknown",
            description="Multiple attempts failed",
            failed_tasks=[task_id],
            failure_reason="Could not solve within limits",
        )
        self.meta_memory.add_ineffective_method(
            problem_type=context.problem_type or ProblemType.TOOL,
            domain="TODO",
            modeling="TODO",
            method=ineffective_method,
        )
