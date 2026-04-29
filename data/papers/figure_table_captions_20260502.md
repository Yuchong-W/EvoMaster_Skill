# Figure And Table Captions Draft

Date: 2026-05-02

## Figure 1. MasterSkill System Loop

Suggested caption:

`MasterSkill` wraps benchmark execution in a control loop that attempts a base
solve, analyzes task behavior, reuses or derives candidate external skills,
validates them with official-task evaluation, and optionally performs a limited
post-solve optimization pass. Candidate paths are preserved only if they
survive that evaluation step.

## Figure 2. Taxonomy Tree Merge Case Timeline

Suggested caption:

`taxonomy-tree-merge` is the clearest end-to-end case in the paper. The frozen
baseline remains unsolved, while the frozen current pipeline solves the task
under `gpt-5.2` by leveraging a bundled prior that survives official-task
validation. A regressive candidate, `taxonomy-tree-merge-fast`, is later
rejected after failing the official real test.

## Figure 3. Selected Task Attribution Overview

Suggested caption:

Selected tasks separate into two qualitatively different groups: solve-gain
cases such as `taxonomy-tree-merge`, `xlsx-recover-data`, and
`seismic-phase-picking`, and common-solved optimization cases such as
`financial-modeling-qa`, `enterprise-information-search`, and
`pddl-tpp-planning`. This distinction explains why the paper makes a suite-level
coverage claim rather than a uniform efficiency claim.

## Table 1. Frozen Suite Comparison

Suggested caption:

Frozen paper-facing comparison between the pre-evolution baseline and the
current `MasterSkill` pipeline on a `15`-task `SkillsBench` slice. The current
pipeline improves solve coverage from `3 / 15` to `6 / 15` with no solve losses.
The strongest suite-level conclusion is coverage gain; runtime evidence among
common-solved tasks is mixed.

## Table 2. Selected Task Attribution

Suggested caption:

Selected task-level attribution summary for the main paper cases. The table
distinguishes solve-gain evidence from optimization-only evidence and marks
where the strongest support comes from suite-level outcome differences versus
trace-level accepted or rejected candidate behavior.

## Table 3. Taxonomy Case Trace Summary

Suggested caption:

Trace-level summary for the primary `taxonomy-tree-merge` case. The table
records baseline failure, current solved status, validated artifact pathway, and
rejected post-solve candidate, showing that the system preserves official-task
discipline while filtering regressions.
