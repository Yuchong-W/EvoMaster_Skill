---
name: pddl-tpp-direct-batch-runner
description: Minimal solve path for pddl-tpp-planning. Run the packaged batch solver first, then run the bundled verifier, and stop once both pass.
---

# PDDL TPP Direct Batch Runner

Use this skill when `problem.json` lists one or more TPP tasks with `plan_output` targets and the goal is to produce verifier-compatible `.txt` and `.pkl` artifacts with minimal reasoning overhead.

## When to Use

- The task is `pddl-tpp-planning` or a near-identical batch PDDL planning task.
- A packaged batch solver script is already available in the task-local skills.
- You want the shortest operational path: solve, save, verify, stop.

## How to Use

1. Read `/app/problem.json` once to confirm the task exists and outputs are expected.
2. Run the packaged batch solver directly:

```bash
python3 /root/.codex/skills/pddl-tpp-pyperplan-batch/solve_tpp_batch.py /app/problem.json
```

3. Immediately run the task-level checker:

```bash
python3 /root/.codex/skills/pddl-tpp-plan-emitter/scripts/check_tpp_outputs.py /app/problem.json
```

4. If both commands pass, stop. Do not manually rewrite plan lines, reopen large files for narration, or perform extra exploratory inspection.
5. If a command fails, fix only the blocking issue and rerun the same command. Keep the solve path short.

## Failure Patterns To Avoid

- Reading the full domain/problem files into the response before trying the packaged solver.
- Hand-writing plans instead of using the returned `pyperplan` plan object.
- Regenerating correct artifacts and then spending the remaining budget narrating or re-inspecting them.
