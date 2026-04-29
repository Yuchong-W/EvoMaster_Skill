# Phase 1 Runbook

> Status note on 2026-04-29:
> this file is now a reference runbook for the broader Phase 1 OSS milestone.
> It is no longer the primary near-term driver for the `2026-05-13` paper
> target. See `MasterSkill/paper_plan_20260513.md`.

Updated: 2026-04-18

## Purpose

This document operationalizes [roadmap.md](/home/yuchong/auto-research-team/MasterSkill/roadmap.md) for the Phase 1 OSS milestone.

Use it as the default execution guide for:

- calibration runs before freezing configuration
- frozen full-suite `SkillsBench` sweeps
- result summarization
- release-readiness checks

If this file and ad hoc shell notes disagree, this file wins.

## Phase 1 Objective

Reach a publishable OSS milestone where:

- `hard` tasks can be solved at real official-test fidelity, even if the solves are expensive
- `medium` and `easy` tasks become cheaper, faster, and more stable
- at least one full `SkillsBench` sweep has been run with a frozen configuration
- results are persisted, summarized, and understandable to external users

## Canonical References

- High-level plan: [roadmap.md](/home/yuchong/auto-research-team/MasterSkill/roadmap.md)
- Current pipeline todo: [pipeline_todo.md](/home/yuchong/auto-research-team/MasterSkill/pipeline_todo.md)
- Release gate: [release_checklist.md](/home/yuchong/auto-research-team/MasterSkill/release_checklist.md)
- Technical routes: [technical_design.md](/home/yuchong/auto-research-team/MasterSkill/technical_design.md)
- Current project state: [state.md](/home/yuchong/auto-research-team/MasterSkill/state.md)
- Recovery / handoff context: [session_resume.md](/home/yuchong/auto-research-team/MasterSkill/session_resume.md)
- Ongoing experiment log: [development_log.md](/home/yuchong/auto-research-team/MasterSkill/development_log.md)

## Ground Rules

1. Official task tests in the real environment are the only success criterion.
2. Calibration runs and frozen evaluation runs must not be mixed.
3. During a frozen suite run, do not change the runtime logic.
4. Always preserve benchmark artifacts and JSON summaries under the chosen data root.
5. Treat attribution carefully:
   - harness recovery
   - bundled-skill leverage
   - research-derived accepted skill
   - mixed / unclear

## Recommended Phase 1 Config

This is the current candidate configuration for Phase 1 full-suite runs.

Preferred launcher:

```bash
scripts/run_phase1_skillsbench.sh <mode>
```

Supported modes:

- `current-calibration`
- `baseline-calibration`
- `current-sweep`
- `baseline-sweep`
- `current-task <task_id>`
- `baseline-task <task_id>`

Each launcher mode now writes a small `phase1_manifest.json` into the target `data_root`
containing the mode, timestamp, branch, commit SHA, task root, and data root.

The single-task modes are the preferred fallback when:

- a calibration batch looks stuck between task transitions
- one long task needs to be resumed without rerunning earlier calibration tasks
- a specific hard task deserves focused debugging under the same calibration data root

### Current / Evolved Sweep

```bash
scripts/run_phase1_skillsbench.sh current-sweep
```

Notes:

- `--benchmark-all` is required for frozen suite runs so the sweep does not depend on task-memory solved-state filtering.
- use a dedicated fresh `data_root` for the frozen sweep
- this sweep allows bundled task-local skills during `base_attempt`
- this sweep allows one post-pass optimization round

### Pure Pre-Evolution Baseline Sweep

```bash
scripts/run_phase1_skillsbench.sh baseline-sweep
```

Notes:

- this disables bundled task-local skills during `base_attempt`
- this stops after `base_attempt`
- this is the cleanest suite-level baseline for pass/fail and runtime comparison

## Calibration Before Freezing

Before any frozen suite run, use a small but representative task set to validate that the chain is stable enough.

The calibration set should cover:

- at least one hard task with current evidence of coverage expansion
- at least one task where baseline also passes and runtime/tokens matter more than pass/fail
- at least one task that previously failed due to harness/runtime issues

Calibration goals:

- no obvious fatal harness failures
- result persistence works
- failure classes are interpretable
- post-pass does not spin uselessly
- token accounting is present in newly written events

Current calibration task set:

- `enterprise-information-search`
- `pddl-tpp-planning`
- `react-performance-debugging`
- `taxonomy-tree-merge`
- `financial-modeling-qa`

## What To Freeze Before A Full Sweep

Freeze these items before launching the full suite:

- task root
- data root names
- runtime branch / commit SHA
- `max_research_cycles`
- `post_solve_optimization_rounds`
- whether bundled task-local skills are exposed in `base_attempt`
- any shell-level environment variables that affect runner behavior

Record the frozen settings in `development_log.md` before or at sweep start.
Also retain the generated `phase1_manifest.json` under the frozen data root.

## Execution Checklist

Before launching a frozen suite:

- verify `docker version`
- verify `docker ps`
- verify the target `data_root` is either fresh or intentionally chosen
- verify current branch / commit SHA
- verify `run_local.py --help` includes the expected flags
- verify no stale operational assumption in docs conflicts with the intended run

## During The Sweep

Monitor:

- benchmark JSONs under `benchmark_runs/latest/`
- `benchmark_runs/runs.jsonl`
- `task_experience/task_experiences.json`
- `shallow/trace/*.jsonl`
- Docker health

If a run dies due to a clear harness fault:

- stop calling that a benchmark result
- fix the harness during calibration mode
- restart the frozen sweep from a clean or clearly versioned data root

## After The Sweep

Summarize the suite immediately.

### Aggregate Summary

```bash
python3 scripts/summarize_masterskill_results.py \
  --data-root /home/yuchong/auto-research-team/MasterSkill/masterskill_data_phase1_current
```

### Per-Task Summary

```bash
python3 scripts/summarize_masterskill_results.py \
  --data-root /home/yuchong/auto-research-team/MasterSkill/masterskill_data_phase1_current \
  --show-tasks
```

Run the same commands for the baseline data root as well.

### Baseline vs Current Comparison

```bash
python3 scripts/compare_masterskill_runs.py \
  --left-root /home/yuchong/auto-research-team/MasterSkill/masterskill_data_phase1_pre_evolution \
  --right-root /home/yuchong/auto-research-team/MasterSkill/masterskill_data_phase1_current \
  --left-label baseline \
  --right-label current \
  --show-tasks
```

## Required Phase 1 Analysis Outputs

At minimum, prepare:

- current/evolved suite summary
- pure baseline suite summary
- pass/fail delta between the two
- duration delta for tasks that pass in both
- effective-token delta for tasks that pass in both
- failure-class breakdown
- a short attribution table for the most important successful tasks

## Release Gate For Phase 1

Do not declare the OSS milestone complete until all of the following are true:

- at least one frozen full-suite current/evolved sweep exists
- at least one comparable baseline sweep exists
- the results are summarized in a human-readable form
- hard-task successes are backed by official-test pass records
- medium/easy-task gains include runtime, token, or stability evidence
- docs explain how to run and interpret the system
- transient failed skill candidates are not cluttering the repo

## Immediate Next Actions

1. complete one short calibration pass after the new `--benchmark-all` and Phase 1 launcher additions
2. freeze the Phase 1 config
3. launch the first full-suite current/evolved sweep
4. launch the corresponding baseline sweep
5. summarize both with `scripts/summarize_masterskill_results.py`
6. compare them with `scripts/compare_masterskill_runs.py`
