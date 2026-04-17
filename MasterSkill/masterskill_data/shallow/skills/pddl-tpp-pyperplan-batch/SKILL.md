# PDDL TPP Pyperplan Batch Emitter

Solve each TPP entry in `problem.json` with `pyperplan` and emit verifier-compatible `plan_output` text plus sibling `.pkl` from the same returned plan object.

## When to Use

Use when a task provides PDDL `domain` and `problem` files plus a required `plan_output`, especially for `pddl-tpp-planning` style batches.

## How to Use

1. Read `problem.json` and iterate every entry exactly as listed; use `entry["domain"]`, `entry["problem"]`, and `entry["plan_output"]` verbatim.
2. For each entry, load the problem with `PDDLReader` and solve it with `OneshotPlanner(name="pyperplan")`.
3. Do not hand-write, reorder, or trim the plan. Use the solver's returned plan directly so it matches the verifier's expected action sequence.
4. Write `plan_output` as UTF-8 text with one `str(action)` per line. Also write `plan_output` with the `.pkl` suffix by pickling the same plan object.
5. Finalization checklist: reopen the `.txt`, confirm it is non-empty, confirm every line is a single parenthesized action, confirm reopened text lines exactly equal `[str(a) for a in plan.actions]`, reopen the `.pkl`, confirm its action strings exactly match the text file, and confirm every task in `problem.json` produced both artifacts.
6. If any task has `result.plan is None` or any artifact check fails, stop and fix that task instead of leaving partial outputs.

## Scripts

### solve_tpp_batch.py

```
import json
import pickle
import sys
from pathlib import Path

from unified_planning.io import PDDLReader
from unified_planning.shortcuts import OneshotPlanner


def solve_entry(entry: dict) -> None:
    out_path = Path(entry["plan_output"])
    out_path.parent.mkdir(parents=True, exist_ok=True)

    reader = PDDLReader()
    problem = reader.parse_problem(entry["domain"], entry["problem"])
    with OneshotPlanner(name="pyperplan") as planner:
        result = planner.solve(problem)

    if result.plan is None:
        raise RuntimeError(f"no plan for {entry['id']}")

    actions = [str(action) for action in result.plan.actions]
    if not actions:
        raise RuntimeError(f"empty plan for {entry['id']}")

    out_path.write_text("\n".join(actions) + "\n", encoding="utf-8")
    pkl_path = out_path.with_suffix(".pkl")
    with pkl_path.open("wb") as handle:
        pickle.dump(result.plan, handle)

    text_lines = [line.strip() for line in out_path.read_text(encoding="utf-8").splitlines()]
    if text_lines != actions:
        raise ValueError(f"text mismatch for {entry['id']}")
    if any((not line) or line.count("(") != 1 or line.count(")") != 1 for line in text_lines):
        raise ValueError(f"malformed text plan for {entry['id']}")

    with pkl_path.open("rb") as handle:
        loaded_plan = pickle.load(handle)
    if [str(action) for action in loaded_plan.actions] != actions:
        raise ValueError(f"pickle mismatch for {entry['id']}")


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: solve_tpp_batch.py <problem.json>")
        return 2

    tasks = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    for entry in tasks:
        solve_entry(entry)

    print("tpp outputs OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

```

