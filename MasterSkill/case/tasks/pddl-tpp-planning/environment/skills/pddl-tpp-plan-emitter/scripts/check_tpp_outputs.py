import json
import pickle
import sys
from pathlib import Path

from unified_planning.io import PDDLReader
from unified_planning.shortcuts import OneshotPlanner


def lint_plan(plan_file: Path) -> None:
    lines = [line.strip() for line in plan_file.read_text(encoding="utf-8").splitlines()]
    if not lines:
        raise ValueError(f"empty plan file: {plan_file}")
    for index, line in enumerate(lines, start=1):
        if not line:
            raise ValueError(f"empty line at {index} in {plan_file}")
        if line.count("(") != 1 or line.count(")") != 1:
            raise ValueError(f"malformed action at {index} in {plan_file}: {line}")


def validate_entry(entry: dict) -> None:
    plan_output = Path(entry["plan_output"])
    pkl_output = plan_output.with_suffix(".pkl")

    if not plan_output.exists():
        raise FileNotFoundError(f"missing text output: {plan_output}")
    if not pkl_output.exists():
        raise FileNotFoundError(f"missing pickle output: {pkl_output}")

    lint_plan(plan_output)

    reader = PDDLReader()
    problem = reader.parse_problem(entry["domain"], entry["problem"])
    with OneshotPlanner(name="pyperplan") as planner:
        result = planner.solve(problem)

    if result.plan is None:
        raise RuntimeError(f"pyperplan found no plan for {entry['id']}")

    with pkl_output.open("rb") as handle:
        pred_plan = pickle.load(handle)

    expected = [str(action) for action in result.plan.actions]
    predicted = [str(action) for action in pred_plan.actions]
    text_lines = [line.strip() for line in plan_output.read_text(encoding="utf-8").splitlines()]

    if predicted != expected:
        raise ValueError(f"pickled plan mismatch for {entry['id']}")
    if text_lines != predicted:
        raise ValueError(f"text and pickle mismatch for {entry['id']}")


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: check_tpp_outputs.py <problem.json>")
        return 2

    problem_file = Path(sys.argv[1])
    tasks = json.loads(problem_file.read_text(encoding="utf-8"))
    for entry in tasks:
        validate_entry(entry)

    print("tpp outputs OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
