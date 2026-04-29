# MasterSkill Paper Plan for 2026-05-13

Updated: 2026-04-29

## Purpose

This is the active execution plan for the `2026-05-13` paper-targeted `arXiv` version.

It supersedes the previous near-term planning assumption that the next milestone
should be a full Phase 1 OSS release with broad full-suite evidence.

The new target is narrower:

- produce a credible paper draft by `2026-05-13`
- support a limited set of claims with a small but convincing evidence package
- avoid overclaiming full-suite generality that the current repo state does not yet support

## Paper Target

By `2026-05-13`, the repo should support an `arXiv` paper that argues:

1. `MasterSkill` is a benchmark-driven external-skill optimization pipeline, not just a static skill library.
2. The pipeline can execute a meaningful end-to-end chain in real task environments:
   - base attempt
   - analysis / research
   - candidate skill reuse or creation
   - official-test validation
   - post-pass optimization or rejection
3. On a full `SkillsBench` evaluation, the optimized pipeline yields meaningful, analyzable outcomes relative to baseline.
4. At least one convincing case study explains where the gain comes from and what part of the pipeline is actually valuable.

This paper does **not** need to claim:

- dominant superiority on all `SkillsBench` tasks
- broad transfer across many domains
- seedless skill construction as a fully established result

## Claim Discipline

The paper should separate evidence into these buckets:

- `harness recovery`
- `bundled-skill leverage`
- `autonomous candidate-skill refinement`
- `post-pass optimization / distillation`
- `mixed or unclear`

Any result that cannot be attributed cleanly should remain in `mixed` and should
not carry a strong innovation claim.

## Evidence Strategy

Use a `full-suite + case-study` structure.

### Full-Suite Evaluation Is A Hard Requirement

The paper is not allowed to rely only on a handful of cherry-picked tasks.

Before `2026-05-13`, we need:

- one baseline `SkillsBench` sweep
- one optimized / current `SkillsBench` sweep
- one aggregate comparison
- one per-task comparison
- one failure-breakdown summary

The paper-level claim should be anchored in that full-suite comparison.

### Case Studies Are The Explanation Layer

The full-suite results alone are not enough.

We still need `1` or `2` task-level case studies that explain:

- what the chain did
- where the gain came from
- whether the gain was due to:
  - harness recovery
  - bundled-skill leverage
  - autonomous refinement
  - accepted post-pass optimization

Case studies are therefore required, but they are not substitutes for the
full-suite table.

### Primary Case Study

Preferred primary case:

- `taxonomy-tree-merge`

Reason:

- it is currently the clearest solved-vs-failed comparison candidate
- pre-evolution evidence shows a pure-base failure
- current evidence shows a solved run in the evolved chain

Required evidence before the paper:

- one clean writeup of the baseline failure path
- one clean writeup of the successful current path
- explicit discussion of what portion is likely due to:
  - bundled-skill leverage
  - runtime stabilization
  - pipeline routing / validation / optimization behavior
- confirmation that the case is not being misrepresented as autonomous skill creation if the main gain is actually skill leverage

### Secondary Case Candidates

Priority order:

1. `enterprise-information-search`
2. `financial-modeling-qa`
3. `pddl-tpp-planning`

Current interpretation:

- `enterprise-information-search`:
  - strong autonomous post-pass optimization story
  - accepted passing skills:
    - `enterprise-direct-evidence-answer`
    - `enterprise-direct-answer-minimal`
  - useful for showing refinement and compression, even if current Phase 1 timing snapshots are noisy
- `financial-modeling-qa`:
  - stable solved task
  - accepted compact task-local skill:
    - `financial-modeling-pairwise-match-delta`
  - likely the cleanest efficiency-supporting task in current data roots
- `pddl-tpp-planning`:
  - accepted post-pass skill:
    - `pddl-tpp-batch-fastpath`
  - useful for a second optimization example if the evidence package is cleaner than `financial-modeling-qa`

### Tasks To Avoid As Standalone Evidence

- `react-performance-debugging`
  - useful as a side observation
  - not ideal as a main result because the current story is more about runtime / stability and candidate rejection than about a clean headline gain
- incomplete `phase1_current` full-suite summaries
  - not suitable as final paper evidence until completed

## Current Evidence Snapshot

### Strongest Current Signals

- `taxonomy-tree-merge`
  - `masterskill_data_pre_evolution/latest`: abandoned, `failure_class=timeout`
  - `masterskill_data/latest`: solved
  - best current use: primary case study for coverage expansion
- `enterprise-information-search`
  - multiple accepted passing skills are already documented
  - best current use: autonomous post-pass optimization case
- `financial-modeling-qa`
  - both baseline and current solve
  - current Phase 1 snapshot is slightly faster than baseline
  - best current use: compact accepted optimization / distillation example
- `pddl-tpp-planning`
  - accepted post-pass optimized skill exists
  - best current use: fallback supporting optimization case if evidence ends up cleaner than `financial-modeling-qa`

### Important Constraints

- `phase1_current` is incomplete (`10` latest records vs `15` in `phase1_pre_evolution`)
- the frozen `current-sweep` was interrupted by a host-side hang / `KeyboardInterrupt`
- `data/papers/` is still empty, so writing must begin immediately instead of waiting for experimental closure
- the worktree is still active and not yet effectively frozen

## Scope Freeze

From now until `2026-05-13`, default policy is:

- all SkillsBench experiments use `gpt-5.2`
- full-suite baseline/current comparison is mandatory
- do not expand to many new tasks beyond what is needed for the suite and case-study explanation
- do not introduce major new system features unless they unblock paper-critical evidence
- prefer a completed, defensible full-suite package plus a small number of well-attributed cases over many partial side experiments

## Deliverables By 2026-05-13

- one complete `arXiv` draft
- one full-suite baseline result set
- one full-suite optimized/current result set
- one aggregate comparison table
- one per-task comparison appendix table
- one failure-breakdown table
- one system figure
- one main results table
- one case-study figure or timeline
- one attribution table for selected tasks
- one limitations section that explicitly states the evidence boundary

## Schedule

### 2026-04-29 to 2026-04-30

- freeze the paper target and evidence strategy
- confirm the full-suite requirement and the case-study role
- select the final case-study task set
- reduce document sprawl and point active docs to this plan
- record evidence gaps for each candidate task
- convert the frozen compare into a paper-ready table and outline

### 2026-05-01 to 2026-05-03

- complete the missing full-suite paper-critical runs
- patch only paper-critical runtime blockers
- collect baseline/current comparison outputs and selected case evidence

### 2026-05-04

- freeze experiment protocol for the paper
- lock main tables and figure requirements

### 2026-05-05 to 2026-05-08

- write the full draft:
  - introduction
  - method
  - setup
  - main results
  - case study
  - limitations

### 2026-05-09 to 2026-05-10

- revise for claim discipline and clarity
- tighten attribution wording
- replace weak claims with narrower but defensible ones

### 2026-05-11

- final evidence audit
- verify that all tables and claims map to stored artifacts

### 2026-05-12

- final polish
- appendix and reproducibility notes

### 2026-05-13

- publish `arXiv` v1

## Today's Tasks

1. Create this plan and make it the active top-level planning reference.
2. Simplify the documentation hierarchy so current intent is obvious.
3. Reframe the milestone so full-suite baseline/current comparison is the hard requirement.
4. Lock the case-study candidate task set.
5. Record the current full-suite and task-level evidence gaps.
6. Choose the first experiment / analysis action for `2026-04-29`.

## Case-Study Candidate Set as of 2026-04-29

### Primary Case

- `taxonomy-tree-merge`

Current evidence:

- pure pre-evolution baseline failed with timeout in
  `masterskill_data_pre_evolution/benchmark_runs/latest/taxonomy-tree-merge.json`
- evolved chain solved in
  `masterskill_data/benchmark_runs/latest/taxonomy-tree-merge.json`

Current gap:

- the paper still needs a concise causal explanation of why the evolved chain solved
- the current writeup must separate bundled-skill leverage from pipeline-level innovation
- the result needs a clean case-study narrative, not just JSON references

### Secondary Case A

- `enterprise-information-search`

Current evidence:

- accepted optimized skills are already documented
- strong refinement story exists in `development_log.md` and `state.md`

Current gap:

- current frozen Phase 1 snapshot is slower than baseline, so this should not be sold as a simple runtime win
- this task needs to be framed as refinement / accepted-skill evidence, not as a broad efficiency headline
- we still need a compact extraction of the successful chain for paper use

### Secondary Case B

- `financial-modeling-qa`

Current evidence:

- both baseline and current Phase 1 snapshots solve
- current Phase 1 snapshot is modestly faster than baseline
- accepted compact skill exists

Current gap:

- verify whether this is the cleanest second supporting task relative to `pddl-tpp-planning`
- extract exact accepted-skill narrative from logs and traces

### Secondary Case B Alternate

- `pddl-tpp-planning`

Current evidence:

- accepted optimized skill exists
- historical docs report meaningful runtime improvement

Current gap:

- current frozen Phase 1 snapshot is slower than baseline
- we need to confirm whether the stronger paper story comes from historical accepted optimization evidence or from a fresh rerun

## Full-Suite Requirement As of 2026-04-29

The paper cannot ship on `2026-05-13` without:

- completed baseline latest coverage
- completed current latest coverage
- baseline-vs-current comparison outputs that reflect the same task set

Current state:

- baseline Phase 1 root has `15` latest records
- current Phase 1 root has only `10` latest records
- therefore the current immediate blocker is not paper prose but finishing a trustworthy current comparison set

## First Execution Task for 2026-04-29

Create a compact paper-evidence memo that decides:

- what exact full-suite artifacts are still missing
- whether `financial-modeling-qa` or `pddl-tpp-planning` is the better second case-study task
- what exact claim each selected case supports
- what missing artifact or rerun is still required per selected case

That memo should be completed before any new broad experiment is launched.
