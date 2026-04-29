# PDDL TPP Batch Solve Verify Minimal

Solves `pddl-tpp-planning` batches by treating `/app/problem.json` as the sole input manifest, running the packaged batch solver once, then immediately validating every emitted `.txt` plan and paired `.pkl` sidecar artifact.

## When to Use

Use when the task is `pddl-tpp-planning` or equivalent and `/app/problem.json` is a JSON array whose entries provide `domain`, `problem`, and `plan_output` paths.

## How to Use

1. Read `/app/problem.json` once and use each entry exactly as listed. Do not explore domain/problem files up front.
2. Run the packaged batch solver directly:
`python3 /root/.codex/skills/pddl-tpp-pyperplan-batch/solve_tpp_batch.py /app/problem.json`
3. Immediately run the bundled verifier:
`python3 /root/.codex/skills/pddl-tpp-plan-emitter/scripts/check_tpp_outputs.py /app/problem.json`
4. Finalization checklist before stopping:
- Every `plan_output` path from `/app/problem.json` exists.
- The sibling `.pkl` for each `plan_output` exists.
- Reopen each emitted `.txt` plan and confirm it is non-empty, line-oriented, and not truncated.
- Let the checker be the source of truth for syntax/completeness across both `.txt` and `.pkl` artifacts.
5. Do not manually rewrite plans after solver output; that can desynchronize the `.txt` and `.pkl` artifacts.
6. If solve or verify fails, inspect only the failing entry, fix the blocking issue, then rerun the same solver command followed by the same checker command.

