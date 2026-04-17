from __future__ import annotations

import json
import pickle
from pathlib import Path

from unified_planning import shortcuts as up_shortcuts
from unified_planning.engines import SequentialPlanValidator
from unified_planning.io import PDDLReader
from unified_planning.shortcuts import OneshotPlanner


def app_root() -> Path:
    candidates = [Path("/app"), Path.cwd()]
    for candidate in candidates:
        if (candidate / "problem.json").exists():
            return candidate
    raise FileNotFoundError("Could not locate problem.json under /app or the current directory.")


def solve_one(root: Path, spec: dict) -> None:
    domain_path = root / spec["domain"]
    problem_path = root / spec["problem"]
    output_path = root / spec["plan_output"]
    output_path.parent.mkdir(parents=True, exist_ok=True)

    reader = PDDLReader()
    problem = reader.parse_problem(str(domain_path), str(problem_path))

    with OneshotPlanner(name="pyperplan") as planner:
        result = planner.solve(problem)
    plan = result.plan
    if plan is None:
        raise RuntimeError(f"No plan found for {spec['id']}")

    validator = SequentialPlanValidator()
    validation = validator.validate(problem, plan)
    if validation.status.name != "VALID":
        raise RuntimeError(f"Plan for {spec['id']} is invalid: {validation}")

    with output_path.open("w") as handle:
        for action in plan.actions:
            handle.write(f"{action}\n")

    with output_path.with_suffix(".pkl").open("wb") as handle:
        pickle.dump(plan, handle)


def main() -> None:
    up_shortcuts.get_environment().credits_stream = None
    root = app_root()
    specs = json.loads((root / "problem.json").read_text())
    for spec in specs:
        solve_one(root, spec)


if __name__ == "__main__":
    main()
