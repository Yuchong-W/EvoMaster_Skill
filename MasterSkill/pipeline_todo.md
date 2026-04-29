# Pipeline Todo

> Status note on 2026-04-29:
> this file is retained as tactical reference for runtime and full-suite work.
> The active near-term plan for the paper milestone is
> `MasterSkill/paper_plan_20260513.md`.

Updated: 2026-04-19

## Purpose

This file is the operational todo list for the current priority:

- build `MasterSkill` into a strong end-to-end optimization pipeline
- let the system itself collect feedback, research external knowledge, generate candidate skills, and refine them
- avoid manual skill editing during debugging
- once the pipeline is stable, launch full-suite runs in monitor-only mode

This file is more tactical than [roadmap.md](/home/yuchong/auto-research-team/MasterSkill/roadmap.md).
Use it as the current execution checklist.

## Working Principle

The rule for the current stage is:

- manually fix the chain
- do not manually optimize task skills during experiments
- allow the system to optimize its own candidate skills
- treat task-bundled skills as priors or references, not as files to hand-edit mid-run

In other words:

- human intervention belongs in runtime, orchestration, evaluation, and guardrails
- skill iteration should come from the system loop itself

## End State

The pipeline is ready for frozen full-suite testing when all of the following are true:

- it can run against a clean `SkillsBench` task root
- hard-task runs no longer get dominated by avoidable harness failures
- the system can iterate on candidate skills without mutating bundled task-local skills
- long runs are stopped by explicit chain guardrails rather than silent hangs
- benchmark results are persisted with interpretable failure classes
- full-suite execution can be monitored without human in-loop skill editing

## Priority Order

1. make clean-task execution reliable
2. stop silent hangs and fake progress
3. preserve autonomous skill iteration while preventing manual or bundled-skill interference
4. validate on clean hard tasks
5. freeze config
6. run full suite in monitor-only mode
7. analyze pass-rate and attribution outcomes

## Workstream A: Clean Task Root Compatibility

### Goal

The runner should work against either:

- a full `SkillsBench` repo root
- a direct `tasks/` directory

### Done

- added path-resolution helpers so the runner no longer assumes `skillsbench_root/tasks/...` unconditionally

### Remaining Todo

- verify the same compatibility in all code paths that read:
  - `task.toml`
  - `instruction.md`
  - `tests/`
  - `environment/`
  - `environment/skills/`
- add a regression check that runs one task with:
  - `--skillsbench-root <repo_root>`
  - `--skillsbench-root <repo_root>/tasks`
- make sure summary scripts and launcher docs describe both supported forms clearly

## Workstream B: Stall Detection And Early Stop

### Goal

The chain should not sit inside `codex exec` for many minutes without observable work.

### Done

- added a workspace activity log
- added a stall timeout that kills `codex exec` when there is no observable progress

### Remaining Todo

- classify stall failures distinctly from generic timeouts in summaries and logs
- calibrate the stall timeout so it does not kill legitimate long-running work such as:
  - embeddings
  - frontend build/test cycles
  - large file processing
- define acceptable activity signals:
  - `task_shell`
  - `task_put`
  - `task_get`
  - `last-message.txt`
  - derived helper file creation
  - output artifact creation
- confirm that a task with legitimate slow progress is not misclassified as stalled
- add one explicit development-log entry whenever stall guard fires on a clean hard task

## Workstream C: Bundled Skill Immutability, Candidate Skill Freedom

### Goal

Preserve the intended research loop:

- bundled task-local skills are read-only references
- system-generated candidate skills may still be iterated on
- humans do not hand-edit skills during the experiment

### Done

- bundled task-local skill trees in the host workspace are copied as read-only
- prompt now says bundled task-local skills are references, not files to edit in place
- `task_put` blocks copying bundled task-local skill files back into the container

### Remaining Todo

- verify the chain can still:
  - generate a new candidate skill
  - revise a generated candidate skill
  - validate the revised candidate against official tests
- explicitly distinguish in logs between:
  - bundled task skill
  - generated candidate skill
  - derived helper script
- ensure candidate-skill iteration does not silently fall back to modifying files under bundled `./skills`
- add a simple failure message when the agent attempts to mutate a bundled skill so the reason is obvious in traces

## Workstream D: Hard-Task Debugging Protocol

### Goal

Use clean hard tasks to debug the pipeline, not to hand-solve tasks.

### Hard Tasks To Keep Using

- `taxonomy-tree-merge`
- `react-performance-debugging`

Additional hard tasks can be added later once the current two stop exposing new chain bugs.

### Protocol

For each hard task:

1. use the clean clone under `/tmp/skillsbench-clean`
2. run with a fresh dedicated `data_root`
3. do not edit task files
4. only inspect:
   - benchmark JSON
   - shallow traces
   - activity log
   - container output directory
   - host process state
5. if the run is clearly misbehaving, stop it and fix the chain rather than the skill

### Remaining Todo

- define explicit stop conditions for hard-task monitoring:
  - no workspace activity for `N` seconds
  - repeated container idleness with no output artifacts
  - repeated attempts to modify bundled skills
  - repeated no-op retries of the same command family
- keep one compact per-task debugging template in the development log:
  - task id
  - clean root path
  - data root
  - observed activity
  - stop reason
  - chain issue inferred

## Workstream E: Execution Fidelity And Outcome Capture

### Goal

If the system makes real progress, the run should end in an analyzable persisted result.

### Current Risk

Some runs generate artifacts or partial work but still fail to write a clean benchmark result.

### Remaining Todo

- verify that output-artifact existence is checked before declaring the run dead
- ensure benchmark records are written for these cases:
  - clean timeout
  - stall guard
  - container execution failure
  - official test failure
  - successful solve path
- ensure `runs.jsonl`, `latest/*.json`, and task traces stay consistent with each other
- distinguish these failure classes clearly:
  - `missing_task_context`
  - `stall`
  - `timeout`
  - `runner_exception`
  - `official_test_failed`
  - `candidate_regression`

## Workstream F: Autonomous Skill Optimization Validation

### Goal

Prove that the system loop, not human manual editing, is what improves skills.

### What Must Be True Before Full Suite

- at least one task shows the system creating a candidate skill from feedback/research
- at least one task shows the system revising or selecting a better candidate without human skill edits
- the logs make that causal chain visible

### Remaining Todo

- identify one medium or hard task where current autonomous iteration is already closest to working
- run it under clean conditions and capture:
  - initial failure
  - research step
  - candidate skill creation
  - candidate evaluation
  - follow-up revision or rejection
- write a short causal summary in `development_log.md` for each successful autonomous iteration case

## Workstream G: Monitor-Only Full-Suite Readiness

### Goal

Reach a point where full-suite execution can run with:

- frozen config
- no manual skill intervention
- operator acts only as monitor / stop-the-bleeding / post-run analyst

### Required Before Launch

- clean task root selected
- exact data roots chosen
- runtime commit frozen
- stall guard calibrated
- bundled-skill immutability enforced
- candidate-skill iteration confirmed still alive
- result persistence verified on calibration tasks

### Full-Suite Monitor Responsibilities

During the frozen suite, the operator may:

- watch progress
- record anomalies
- stop obviously broken runs
- restart only under documented policy

The operator may not:

- edit task skills
- patch a task mid-sweep
- rewrite candidate skills by hand
- quietly change runtime logic while still calling the run “frozen”

## Immediate Todo

### Next 1

- let the current clean hard-task runs confirm that bundled skills remain unmodified and candidate/derived helpers are still allowed

### Next 2

- add explicit `stall` failure classification instead of collapsing into generic `timeout`

### Next 3

- verify one clean hard task can complete with either:
  - real solve progression
  - clean, fast, interpretable failure

### Next 4

- verify one clean non-hard task still allows autonomous candidate-skill optimization under the new guardrails

### Next 5

- once these checks pass, freeze the Phase 1 runtime config for the first monitor-only full-suite sweep

## Next-Stage Experimental Roadmap (2026-04-21)

Target:

- move from calibration-only evidence to frozen full-suite evidence
- optimize the chain so autonomous skill generation/selection drives benchmark gains
- use pass-rate trajectory checkpoints toward `>=90%` on SkillsBench

Experiment sequence:

1. `E1` reproducible frozen baseline/current pair:
   - run one `baseline-sweep` and one `current-sweep` with frozen settings
   - verify no missing tasks in `latest/*.json`
2. `E2` reproducibility check:
   - rerun frozen `current-sweep` twice
   - solve-rate drift must be within `<=3pp`
3. `E3` hard-task stability:
   - hard-task subset with stall-timeout grid (`300/450/600s`)
   - reduce `stall+timeout` failure share by at least `30%`
4. `E4` persistence integrity:
   - validate `latest`, `runs.jsonl`, task streams consistency under interruptions
5. `E5` immutability-vs-iteration validation:
   - bundled skills remain read-only
   - candidate skills can still be revised and validated
6. `E6` candidate acceptance A/B:
   - compare acceptance rules and keep lowest-regression policy with non-decreasing pass rate
7. `E7` skill artifact quality gate:
   - reject malformed generated scripts before execution
8. `E8` transfer validation:
   - verify at least three skills with cross-task net benefit
9. `E9` full-suite climb:
   - daily frozen current runs, close top failure buckets first
10. `E10` 90% gate:
   - three consecutive frozen sweeps, average `>=90%`, no single run below `88%`

Execution policy:

- every experiment must persist manifest + summaries + comparison outputs
- runtime changes are allowed only between frozen experiments, never during a frozen sweep

## Definition Of Done For This File

This todo list is no longer “active” when:

- clean hard-task runs mostly fail or succeed for task reasons, not chain reasons
- bundled task-local skills remain untouched during runs
- autonomous candidate-skill iteration is preserved
- frozen full-suite execution can begin with monitor-only human involvement
