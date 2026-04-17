# PDDL TPP Batch Fastpath

Solve `pddl-tpp-planning` batches with the packaged pyperplan runner, then validate emitted `.txt` plans and sibling `.pkl` artifacts with the bundled checkers. Default path is solve -> verify -> stop.

## When to Use

Use when the task is `pddl-tpp-planning` or an equivalent batch TPP task with `/app/problem.json` listing `domain`, `problem`, and `plan_output` for each entry, and the packaged batch solver is available.

## How to Use

1. Read `/app/problem.json` once and treat it as the source of truth. It is a JSON array; use each `domain`, `problem`, and `plan_output` path exactly as listed.
2. Do not open domain/problem files up front. Let the packaged solver consume them directly. Only inspect a specific failing entry if the solver or verifier errors.
3. Run the batch solver:
`python3 /root/.codex/skills/pddl-tpp-pyperplan-batch/solve_tpp_batch.py /app/problem.json`
4. Run the artifact/output verifier immediately after solving:
`python3 /root/.codex/skills/pddl-tpp-plan-emitter/scripts/check_tpp_outputs.py /app/problem.json`
5. Run strict plan lint on the emitted text plans:
`python3 /root/.codex/skills/pddl-tpp-plan-emitter/scripts/strict_plan_lint.py /app/problem.json`
6. Finalization checklist before exit:
- Every `plan_output` file exists at the exact path from `problem.json`.
- Every sibling `.pkl` produced from the same returned plan object exists.
- `check_tpp_outputs.py` passes for the full batch.
- `strict_plan_lint.py` passes for the full batch.
- If you manually inspect any plan file, reopen it from disk and confirm it is non-empty, one action per line, and not truncated.
7. If any command fails, fix only the blocking issue, rerun that command, then rerun the downstream verifier/lint. Do not manually rewrite full plans unless the packaged path is broken.
8. Keep narration minimal. The output artifacts are the plan files themselves; once solver and both checks pass, stop.

