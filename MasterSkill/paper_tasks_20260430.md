# Paper Tasks for 2026-04-30

## Purpose

This is the active task sheet for `2026-04-30`.

`2026-04-29` closed the experimental coverage gap:

- `phase1_pre_evolution`: `15 / 15`
- `phase1_current`: `15 / 15`

Today should therefore move from run completion to paper-material production and
evidence hygiene.

## Hard Goals For Today

1. freeze the paper-facing claim boundary from the new full-suite comparison
2. convert the frozen comparison into paper-ready tables and task groupings
3. start a real paper outline rather than only planning notes
4. identify and resolve evidence-hygiene issues that would undermine the paper if left unaddressed

## Non-Goals For Today

- do not launch new broad benchmark sweeps
- do not add major runtime features
- do not widen the task set beyond the frozen `15 / 15` suite

## Starting Point

Frozen compare at start of day:

- baseline solved: `3 / 15`
- current solved: `5 / 15`
- solve gains: `taxonomy-tree-merge`, `xlsx-recover-data`
- solve losses: `0`

Best current paper framing:

- coverage gain on the frozen suite
- case-study evidence of chain value
- limited support for broad efficiency/stability claims

## Key Risk To Resolve Today

The main evidence-hygiene risk for `2026-04-30` was model inconsistency across
paper-facing `latest` snapshots.

Observed issue at start of day:

- some `baseline/current` latest snapshots still showed a legacy final model
- the new experiment policy requires `gpt-5.2`

Required response:

- rerun the mismatched solved tasks under `gpt-5.2`
- overwrite the paper-facing `latest` snapshots in place if reruns succeed

## Model-Consistency Decision

Decision for `2026-04-30`:

- use `strict model consistency`
- rerun all `baseline/current` latest snapshots that still report the legacy
  final model
- use the rerun-updated `latest` roots as the paper-facing evidence once the
  reruns complete successfully

Current rerun set:

- baseline:
  - `enterprise-information-search`
  - `financial-modeling-qa`
  - `pddl-tpp-planning`
- current:
  - `enterprise-information-search`
  - `financial-modeling-qa`
  - `pddl-tpp-planning`
  - `seismic-phase-picking`

Execution status:

- current-side rerun set: completed
- baseline-side rerun set: completed
- all solved `baseline/current latest` snapshots are now `gpt-5.2`

## Deliverables For Today

### A. Paper-Ready Evidence Assets

- one main result table draft
- one task attribution table draft
- one case-study source map
- one first paper outline

### B. Evidence-Hygiene Execution

- execute the strict `gpt-5.2` rerun set
- replace the affected latest snapshots in-place if reruns succeed
- record any rerun failures explicitly instead of silently keeping
  pre-normalization entries

## Priority Order

1. model-consistency execution
2. main result table draft
3. taxonomy case-study extraction
4. enterprise / financial supporting-case extraction
5. first paper outline

## Concrete Tasks

### Task 1: Freeze The Claim Boundary

Write down the exact paper claim that the current frozen compare supports:

- coverage gain from `3 / 15` to `5 / 15`
- no solve losses
- no broad runtime win claim

### Task 2: Build Main Table Draft

Produce a markdown table with:

- task id
- baseline status
- current status
- baseline duration
- current duration
- solve-gain / common-solved / unchanged-failure label
- provisional attribution bucket

### Task 3: Build Attribution Draft

For the main tasks of interest:

- `taxonomy-tree-merge`
- `xlsx-recover-data`
- `enterprise-information-search`
- `financial-modeling-qa`
- `pddl-tpp-planning`

assign one provisional attribution label:

- `coverage gain`
- `post-pass optimization`
- `bundled-skill leverage`
- `mixed / unclear`

### Task 4: Start Paper Outline

Create the first real outline with:

- introduction claim
- method sections
- evaluation section
- main table
- taxonomy case-study figure
- limitations section

### Task 5: Complete Or Advance The `gpt-5.2` Rerun Set

Use a dedicated rerun helper and work through the mismatched tasks in this order:

1. current solved tasks
2. current non-solved task with an explicit legacy model field
3. baseline solved tasks

If all reruns do not finish today, end the day with:

- the helper script on disk
- logs for the tasks already completed
- an exact list of remaining reruns

Current remaining rerun:

- none

## Success Condition

`2026-04-30` is successful if, by end of day:

- the paper argument is narrower but explicit
- the main table and outline exist on disk
- the model-consistency rerun set is completed

## End-of-Day Status

`2026-04-30` close-out:

- strict `gpt-5.2` consistency reruns completed for all solved paper-facing
  baseline/current tasks
- refreshed frozen compare now shows:
  - baseline solved: `3 / 15`
  - current solved: `6 / 15`
  - solve gains: `seismic-phase-picking`, `taxonomy-tree-merge`,
    `xlsx-recover-data`
  - solve losses: `0`
- paper-facing docs no longer depend on a model-transition disclosure path
