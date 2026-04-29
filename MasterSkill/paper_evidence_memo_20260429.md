# Paper Evidence Memo

Date: 2026-04-29

## Purpose

This memo converts the `2026-05-13` paper target into a concrete evidence and
execution checklist for today.

It answers four questions:

1. what full-suite artifacts are still missing
2. which case-study tasks are currently strongest
3. which supporting task is the better second case candidate
4. what to run next today

## Full-Suite Status

### Baseline Root

Path:

- `MasterSkill/masterskill_data_phase1_pre_evolution/benchmark_runs/latest`

Coverage:

- `15 / 15` tasks present

### Current Root

Path:

- `MasterSkill/masterskill_data_phase1_current/benchmark_runs/latest`

Coverage:

- `10 / 15` tasks present

Missing tasks:

- `react-performance-debugging`
- `speaker-diarization-subtitles`
- `taxonomy-tree-merge`
- `video-filler-word-remover`
- `xlsx-recover-data`

## Immediate Full-Suite Blocker

The paper cannot rely on the current Phase 1 comparison yet because the task
set is incomplete on the current side.

The immediate blocker is therefore:

- complete `phase1_current` latest coverage to `15 / 15`

This is more urgent than polishing per-task narratives.

## Current Comparison Read

### Already Comparable Solved Tasks

- `enterprise-information-search`
  - baseline solved
  - current solved
  - current snapshot is slower than baseline
  - best paper use: accepted post-pass refinement example, not simple efficiency claim
- `financial-modeling-qa`
  - baseline solved
  - current solved
  - current snapshot is slightly faster than baseline
  - best paper use: compact accepted optimization example
- `pddl-tpp-planning`
  - baseline solved
  - current solved
  - current snapshot is slower than baseline
  - best paper use: accepted optimization example only if logs show a cleaner chain than `financial-modeling-qa`

### Strongest Coverage-Style Signal In Legacy Roots

- `taxonomy-tree-merge`
  - legacy baseline: failed
  - legacy current: solved
  - best paper use: primary case study for “the optimized chain can unlock a hard task that pure base does not solve”

## Case-Study Decision

### Primary Case Study

- `taxonomy-tree-merge`

Reason:

- strongest solved-vs-failed contrast available in existing repo evidence
- directly useful for explaining why chain-level optimization matters
- also forces us to confront attribution honestly instead of hiding behind aggregate tables

### Secondary Case Study

- `enterprise-information-search`

Reason:

- strongest current evidence for accepted post-pass optimization and refinement
- already has two accepted passing skills documented:
  - `enterprise-direct-evidence-answer`
  - `enterprise-direct-answer-minimal`
- useful for showing that the system can improve an already-working solve path instead of only chasing first-pass solves

### Better Third Candidate: `financial-modeling-qa` over `pddl-tpp-planning`

Current decision:

- prefer `financial-modeling-qa` as the next supporting task

Reason:

- current Phase 1 snapshot is at least directionally better than baseline on runtime
- accepted compact skill exists
- easier to defend as a modest efficiency/supporting case

Why not choose `pddl-tpp-planning` first:

- historical docs describe a good optimization story
- but the current frozen Phase 1 snapshot is slower than baseline
- that creates a paper-writing burden unless we rerun or explain the mismatch clearly

## Required Evidence Gaps

### `taxonomy-tree-merge`

Need:

- one completed `phase1_current` snapshot under the same comparison root
- one concise narrative of:
  - baseline failure
  - current success
  - what part of the gain is likely bundled-skill leverage vs orchestration improvement

Useful existing evidence already available:

- legacy pure baseline failed by timeout in:
  - `MasterSkill/masterskill_data_pre_evolution/benchmark_runs/latest/taxonomy-tree-merge.json`
- legacy current solved in:
  - `MasterSkill/masterskill_data/benchmark_runs/latest/taxonomy-tree-merge.json`
- the bundled skill was upgraded into an executable pipeline:
  - `hierarchical-taxonomy-clustering/scripts/pipeline.py`
- direct task-image validation already recorded:
  - `unified_taxonomy_full.csv`: `8,968` rows
  - `unified_taxonomy_hierarchy.csv`: `469` rows
  - official checks passed: `22 / 22`
- development-log interpretation already points to the key causal split:
  - the task became method-feasible
  - later failures shifted toward host-side completion / persistence rather than task impossibility

### `enterprise-information-search`

Need:

- one concise chain summary from logs / traces
- one small table or timeline showing:
  - base state
  - accepted candidate
  - optimized accepted candidate

### `financial-modeling-qa`

Need:

- one concise accepted-skill summary
- one confirmation that the result is clean enough to keep as the third evidence point

## Today’s Run Priority

Order missing current tasks by paper value first:

1. `taxonomy-tree-merge`
2. `react-performance-debugging`
3. `xlsx-recover-data`
4. `video-filler-word-remover`
5. `speaker-diarization-subtitles`

Reasoning:

- `taxonomy-tree-merge` is the highest-value paper case
- `react-performance-debugging` is not the main claim, but it is useful for the explanation layer and was intentionally delayed by the recovery script
- the remaining three matter primarily because full-suite completeness is required

## Today’s Execution Decision

Start the current completion flow rather than waiting for more analysis.

Use:

- `scripts/run_e1_current_until_complete.sh`

Success condition for today:

- the missing-task completion flow is running cleanly
- we have log evidence showing which missing task is being processed first
- if the run stalls again, capture the exact failure mode instead of leaving the current root partially unexplained

## 2026-04-29 Execution Outcome

### What Was Completed Today

- created the paper plan and made it the active near-term planning document
- simplified the documentation hierarchy so current intent is obvious
- confirmed the missing current tasks in the Phase 1 comparison root:
  - `react-performance-debugging`
  - `speaker-diarization-subtitles`
  - `taxonomy-tree-merge`
  - `video-filler-word-remover`
  - `xlsx-recover-data`
- updated `scripts/run_e1_current_until_complete.sh` so paper-critical task
  ordering starts with:
  - `taxonomy-tree-merge`
  - `react-performance-debugging` last

### Blocker Found

The current full-suite completion run is blocked by missing Docker connectivity in
the active WSL environment.

Observed facts:

- `docker version` is not available in this distro
- `/var/run/docker.sock` does not exist
- `run_local.py` fails during `docker.from_env()` before task execution begins

Observed error classes:

- sandboxed run: `PermissionError: Operation not permitted`
- escalated host run: `FileNotFoundError: No such file or directory`

Interpretation:

- the immediate blocker is not the task logic
- the immediate blocker is missing Docker Desktop / WSL integration for this distro

### Immediate Next Step

Before any more paper-critical reruns:

1. restore Docker access in this WSL environment
2. rerun `scripts/run_e1_current_until_complete.sh`
3. verify that `taxonomy-tree-merge` actually enters real task execution rather
   than failing in executor initialization

### Docker Recovery Completed

Later on `2026-04-29`, Docker access was restored.

Verified:

- Windows Docker Desktop launched successfully from:
  - `/mnt/e/Docker/Docker Desktop.exe`
- Windows-side daemon became available via:
  - `/mnt/e/Docker/resources/bin/docker.exe version`
- WSL integration became available again:
  - `docker version` works inside WSL
  - `/var/run/docker.sock` exists again

### Current Run State After Recovery

- restarted `scripts/run_e1_current_until_complete.sh`
- confirmed the paper-priority first task remains:
  - `taxonomy-tree-merge`
- confirmed `run_local.py --task taxonomy-tree-merge` is now alive under the
  restored Docker environment
- confirmed runtime containers were created for the taxonomy task, so the run is
  now past executor initialization and into real execution

### New Current Results Added On 2026-04-29

- `taxonomy-tree-merge`
  - added to:
    - `MasterSkill/masterskill_data_phase1_current/benchmark_runs/latest/taxonomy-tree-merge.json`
  - status: `solved`
  - final model: `gpt-5.2`
  - top-level duration: `1028.40s`
  - event-level base-solve duration: `338.07s`
  - event-level effective tokens: `23410`
  - task container confirmed output artifacts:
    - `unified_taxonomy_full.csv`
    - `unified_taxonomy_hierarchy.csv`
  - post-pass candidate rejection is now also persisted:
    - `taxonomy-tree-merge-fast`
    - `candidate failed official real test`
- `xlsx-recover-data`
  - added to:
    - `MasterSkill/masterskill_data_phase1_current/benchmark_runs/latest/xlsx-recover-data.json`
  - status: `solved`
  - final model: `gpt-5.2`
  - top-level duration: `872.94s`
  - event-level duration: `385.54s`
  - event-level effective tokens: `24253`

Coverage impact:

- `phase1_current` advanced from `10 / 15` to `12 / 15`
- remaining missing current tasks are now:
  - `speaker-diarization-subtitles`
  - `video-filler-word-remover`
  - `react-performance-debugging`

### Data-Quality Note

The earlier temporary `duration_seconds = 0.0` issue for
`taxonomy-tree-merge.json` later self-corrected when the record was updated
again. This suggests the run-record persistence path may update in multiple
stages during or after post-pass processing.

## End-Of-Day Result Snapshot

### Full-Suite Coverage

By end of day on `2026-04-29`:

- `phase1_pre_evolution` coverage: `15 / 15`
- `phase1_current` coverage: `15 / 15`

This completes the immediate paper-critical requirement that both comparison
roots contain the same task set.

### Aggregate Comparison

Current summary:

- baseline solved: `3 / 15`
- current solved: `5 / 15`
- solve gains for current: `2`
- solve losses for current: `0`
- current solve gains:
  - `taxonomy-tree-merge`
  - `xlsx-recover-data`

### Common-Solved Tasks

Tasks solved in both baseline and current:

- `enterprise-information-search`
- `financial-modeling-qa`
- `pddl-tpp-planning`

Observed direction:

- `financial-modeling-qa` is the only common-solved task currently faster in the
  frozen current root
- `enterprise-information-search` and `pddl-tpp-planning` are slower in the
  current frozen root than in the pure baseline root
- therefore the current paper story should not be framed as a broad runtime win

### Current Claim Boundary

The strongest defensible full-suite claim at end of day is:

- the optimized/current pipeline expands solve coverage on the frozen `SkillsBench`
  task set from `3` to `5` solved tasks
- the cleanest solve-gain evidence is:
  - `taxonomy-tree-merge`
  - `xlsx-recover-data`

The strongest defensible case-study claim remains:

- `taxonomy-tree-merge` is the best primary case because it combines:
  - baseline failure
  - current success
  - direct task-artifact confirmation
  - post-pass candidate rejection evidence

### Important Caution

The current frozen suite still has many `abandoned_without_classification`
outcomes. That weakens any broad reliability claim and means the paper should
stay narrow:

- highlight coverage gains and concrete chain behavior
- avoid claiming broad efficiency or stability improvement across the suite
