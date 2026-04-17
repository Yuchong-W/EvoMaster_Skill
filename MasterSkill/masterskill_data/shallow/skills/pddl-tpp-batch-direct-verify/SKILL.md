# PDDL TPP Batch Direct Verify

Distilled low-overhead workflow for pddl-tpp-planning: run the packaged batch solver on problem.json, verify emitted plans immediately, confirm both text and sidecar artifacts, and stop.

## When to Use

Use for pddl-tpp-planning or equivalent batch TPP tasks where problem.json is a JSON array of entries with domain, problem, and plan_output fields, and the packaged pyperplan batch solver is available.

## How to Use

1. Read `/app/problem.json` once and treat it as the source of truth. Iterate entries exactly as listed; use each `domain`, `problem`, and `plan_output` value verbatim.
2. Do not open large PDDL files up front. First run the packaged solver:
`python3 /root/.codex/skills/pddl-tpp-pyperplan-batch/solve_tpp_batch.py /app/problem.json`
3. Immediately run the bundled checker:
`python3 /root/.codex/skills/pddl-tpp-plan-emitter/scripts/check_tpp_outputs.py /app/problem.json`
4. Finalization checklist before exit:
- Every `plan_output` path from `/app/problem.json` exists.
- The sibling `.pkl` for each `plan_output` also exists; emit the `.txt` and `.pkl` from the same returned plan object, never separately.
- Reopen each `plan_output` file once and sanity-check that it is readable, not truncated, and formatted as one action per line.
- Reopen each sibling `.pkl` once and confirm it is present and non-empty.
- If the checker accepts an empty plan, keep it; do not invent actions manually.
5. If anything fails, inspect only the failing entry and blocking error, fix that path, then rerun the same solver command and checker. Avoid broad exploration, manual plan rewriting, or extra narration.
6. Stop as soon as solver + checker + artifact sanity checks all pass.

