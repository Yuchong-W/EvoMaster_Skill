---
name: pddl-tpp-plan-emitter
description: Use for `pddl-tpp-planning` tasks that must write complete plan artifacts to `plan_output`. Prevent truncated manual plans by saving both the `.txt` and `.pkl` from the same Unified Planning plan object and verifying they exactly match a fresh `pyperplan` solve.
---

# PDDL TPP Plan Emitter

Use this skill for `case/tasks/pddl-tpp-planning` or similar TPP tasks where `problem.json` specifies `plan_output` files.

## Why this skill exists

- `instruction.md` requires a syntactically correct, valid plan with one action primitive per line written to each requested output path.
- `environment/solve.py` and `skills/pddl-skills/save_plan.skill` define the canonical write path: iterate `plan.actions`, write `str(action)` to `<task>.txt`, and pickle the same plan object to `<task>.pkl`.
- `tests/test_outputs.py` and `environment/validate.py` re-solve each problem with `OneshotPlanner(name="pyperplan")` and expect the pickled plan actions to exactly equal the solver result. They also reject blank or malformed text lines.
- The shallow trace regression was a partial `task02.txt` plus verifier mismatch. This skill is here to prevent that exact failure mode.

## Required workflow

1. Read the full `problem.json` first and process every listed task. Do not stop after the first solved plan.
2. Load each domain/problem with `PDDLReader` or the local `load-problem` skill.
3. Generate the plan with `OneshotPlanner(name="pyperplan")` or the local `generate-plan` skill.
4. Save artifacts from the planner's plan object itself, not from manually retyped output:
   - `<plan_output>`: one `str(action)` per line, no numbering, comments, or summary text
   - `<plan_output with .pkl suffix>`: `pickle.dump(plan, f)` of the same plan object
5. Never hand-edit only the `.txt` file after saving. If the text file changes, rewrite the `.pkl` from the same plan object too.
6. Treat any copied or displayed plan as suspect until you read it back from disk. Truncation usually happens during narration, not during `save-plan`.
7. Run both local checks before finishing:
   - `python3 <this-skill-dir>/scripts/strict_plan_lint.py <plan_output>`
   - `python3 <this-skill-dir>/scripts/check_tpp_outputs.py <problem.json>`
8. If either check fails, regenerate or re-save from the plan object. Do not patch individual lines by hand.

## Failure patterns to avoid

- Returning or writing only the first part of a plan, including a cut-off final line.
- Producing a visible plan in the response but forgetting the required on-disk artifacts.
- Writing `task01.txt` but forgetting `task02.txt` or later entries in `problem.json`.
- Using a format different from Unified Planning's `str(action)` serialization.
- Creating a `.txt` file that no longer matches the paired `.pkl`.

## Scripts

- `scripts/strict_plan_lint.py`: fast format check for one saved plan file.
- `scripts/check_tpp_outputs.py`: task-level verifier for existence, text completeness, `.txt`/`.pkl` consistency, and exact match with a fresh `pyperplan` solve.
