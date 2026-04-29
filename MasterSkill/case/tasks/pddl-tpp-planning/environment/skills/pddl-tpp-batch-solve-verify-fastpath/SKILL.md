# PDDL TPP Batch Solve And Verify Fastpath

Solves `pddl-tpp-planning` batches by running the packaged TPP batch solver on `/app/problem.json`, then immediately validating emitted `.txt` plans and sibling `.pkl` artifacts with the bundled checker. Minimizes search and narration by treating the packaged solver and verifier as the default path.

## When to Use

Use when the task is `pddl-tpp-planning` or equivalent, `/app/problem.json` is a JSON array of entries with `domain`, `problem`, and `plan_output`, and the packaged batch solver/checker are available.

## How to Use

1. Read `/app/problem.json` once and treat it as the source of truth for every `domain`, `problem`, and `plan_output` path. Do not inspect large PDDL files unless the solver or checker fails.
2. Run the packaged solver directly:
`python3 /root/.codex/skills/pddl-tpp-pyperplan-batch/solve_tpp_batch.py /app/problem.json`
3. Immediately run the bundled verifier:
`python3 /root/.codex/skills/pddl-tpp-plan-emitter/scripts/check_tpp_outputs.py /app/problem.json`
4. If both commands pass, stop exploring and finalize artifacts. Do not manually rewrite plan lines, re-plan by hand, or narrate file contents.
5. If a command fails, fix only the blocking issue and rerun the same command. Keep the workflow on the solver -> verifier path.
6. Finalization checklist before exit:
- For each entry in `/app/problem.json`, confirm `plan_output` exists.
- Reopen each `plan_output` text file and sanity-check that it is non-empty, line-oriented, and each non-blank line looks like a single PDDL action such as `name(...)`.
- Confirm the sibling sidecar artifact from the same solve exists: replace the `.txt` suffix in `plan_output` with `.pkl` and verify that file is present.
- Ensure no output file is truncated or missing; if any artifact is absent, rerun solver/checker rather than hand-editing.
- There is no separate answer JSON for this task; the required deliverables are every listed `plan_output` text file plus its sibling `.pkl`.

