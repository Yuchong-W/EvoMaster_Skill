"""MasterSkill - Benchmark-Driven Skill Discovery System.

Usage:
    python -m icml_research.masterskill.main --task <task_id>
    python -m icml_research.masterskill.main --benchmark
"""

import argparse
import sys
from pathlib import Path

from .core.config import load_config
from .core.types import default_skillsbench_root
from .runner import BenchmarkRunner


def main():
    default_root = default_skillsbench_root()
    parser = argparse.ArgumentParser(description="MasterSkill - Benchmark-Driven Skill Discovery")
    parser.add_argument("--task", type=str, help="Run a single task")
    parser.add_argument("--benchmark", action="store_true", help="Run full benchmark")
    parser.add_argument("--tasks", nargs="+", type=str, help="Run specific tasks")
    parser.add_argument("--skillsbench-root", type=str, default=default_root)
    parser.add_argument("--data-root", type=str, default="")
    parser.add_argument("--max-real-test-failures", type=int, default=4)
    parser.add_argument("--max-quick-proposer", type=int, default=3)
    parser.add_argument("--max-research-trigger", type=int, default=2)
    parser.add_argument("--post-solve-optimization-rounds", type=int, default=0)
    parser.add_argument(
        "--pre-evolution-baseline",
        action="store_true",
        help="Measure pure base-attempt pass rate with no bundled task-local skills exposed and stop before any reuse/research/evolution steps.",
    )

    args = parser.parse_args()

    if not args.task and not args.benchmark and not args.tasks:
        parser.print_help()
        sys.exit(1)

    data_root = args.data_root
    if args.pre_evolution_baseline and not data_root:
        data_root = str(Path(default_root).parent / "masterskill_data_pre_evolution")

    # Load config
    config = load_config(
        skillsbench_root=args.skillsbench_root,
        data_root=data_root,
        max_real_test_failures=args.max_real_test_failures,
        max_quick_proposer_iterations=args.max_quick_proposer,
        max_research_triggers_same_judger=args.max_research_trigger,
        post_solve_optimization_rounds=0 if args.pre_evolution_baseline else args.post_solve_optimization_rounds,
        base_attempt_include_task_skills=not args.pre_evolution_baseline,
        stop_after_base_attempt=args.pre_evolution_baseline,
    )

    # Initialize runner
    runner = BenchmarkRunner(config)

    if args.task:
        # Run single task
        print(f"Running task: {args.task}")
        status = runner.run_task(args.task)
        print(f"Task {args.task} finished with status: {status.value}")

    elif args.tasks:
        # Run specific tasks
        print(f"Running {len(args.tasks)} tasks")
        results = {"solved": [], "abandoned": [], "solved_count": 0, "abandoned_count": 0}
        for task_id in args.tasks:
            status = runner.run_task(task_id)
            if status.value == "solved":
                results["solved"].append(task_id)
                results["solved_count"] += 1
            else:
                results["abandoned"].append(task_id)
                results["abandoned_count"] += 1

        print(f"\nResults: {results['solved_count']} solved, {results['abandoned_count']} abandoned")

    elif args.benchmark:
        # Run full benchmark
        print("Running full benchmark...")
        results = runner.run_benchmark()
        print(f"\nBenchmark complete:")
        print(f"  Total: {results['total']}")
        print(f"  Solved: {results['solved_count']}")
        print(f"  Abandoned: {results['abandoned_count']}")
        print(f"  Solve rate: {results['solved_count']/results['total']*100:.1f}%")
        print(f"\nSolved tasks: {results['solved']}")
        print(f"Abandoned tasks: {results['abandoned']}")


if __name__ == "__main__":
    main()
