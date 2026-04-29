# Release Checklist

> Status note on 2026-04-29:
> this checklist remains relevant for a later OSS release, but it is not the
> gating checklist for the `2026-05-13` paper milestone. See
> `MasterSkill/paper_plan_20260513.md`.

Updated: 2026-04-19

## Purpose

This checklist defines the minimum bar for releasing `MasterSkill` as a high-quality open-source project with strong evidence and clear upgrade potential toward a top-tier paper.

Use this file as the release gate.

## Release Standard

The release should not happen merely because:

- the repo looks cleaner
- a few tasks pass
- the docs read well

The release should happen only when all three are true:

1. the end-to-end optimization pipeline is operational
2. full-suite evidence shows meaningful progress
3. external users can install, run, and understand the system

## A. Must-Have Pipeline Checks

- [ ] The runner works against a clean `SkillsBench` task root.
- [ ] The runner works when `--skillsbench-root` points to a repo root.
- [ ] The runner works when `--skillsbench-root` points directly to a `tasks/` directory.
- [ ] Clean hard-task runs no longer fail immediately due to task-context/path bugs.
- [ ] Silent `codex exec` hangs are guarded by explicit stall detection.
- [ ] Stall failures are written as analyzable benchmark outcomes instead of disappearing mid-run.
- [ ] Bundled task-local skills are treated as read-only references during runs.
- [ ] The system can still iterate on generated candidate skills after bundled skills are locked down.
- [ ] Task runs persist interpretable failure classes.
- [ ] `latest/*.json`, `runs.jsonl`, task traces, and memory artifacts stay consistent with each other.
- [ ] Official-test execution remains isolated from solve-time execution.
- [ ] Output artifacts are captured and reflected in the stored run result when relevant.

## B. Must-Have Hard-Task Checks

- [ ] At least one clean hard task shows real solve progression rather than immediate harness failure.
- [ ] At least one clean hard task either solves or fails in a clear, interpretable way.
- [ ] Hard-task debugging is being done without manual editing of task skills.
- [ ] Hard-task stop conditions are explicit and documented.
- [ ] There is evidence that hard-task bottlenecks are increasingly about task difficulty rather than broken orchestration.

## C. Must-Have Autonomous Skill-Optimization Checks

- [ ] At least one task shows the system creating a candidate skill from the feedback/research loop.
- [ ] At least one task shows the system revising or selecting a better candidate skill without human skill editing.
- [ ] The logs make the causal chain visible:
  - initial failure
  - research / analysis
  - candidate generation
  - candidate validation
  - follow-up refinement or rejection
- [ ] The runtime distinguishes bundled task skills from generated candidate skills in traces or logs.
- [ ] The runtime can reject regressive candidates cleanly.
- [ ] Candidate-skill optimization remains alive after bundled-skill immutability guardrails are added.

## D. Must-Have Full-Suite Experiment Checks

- [ ] A frozen full-suite `current/evolved` `SkillsBench` sweep has been run.
- [ ] A comparable frozen full-suite baseline sweep has been run.
- [ ] Both sweeps use documented, versioned, and frozen runtime settings.
- [ ] Both sweeps use clean or clearly versioned task roots and data roots.
- [ ] The full-suite runs were executed in monitor-only mode:
  - no mid-run manual skill editing
  - no silent runtime logic changes
- [ ] Aggregate summaries exist for both sweeps.
- [ ] Per-task summaries exist for both sweeps.
- [ ] A baseline-vs-current comparison report exists.
- [ ] Failure-class breakdown exists.
- [ ] Attribution table exists for the main success cases.

## E. Must-Have Evidence Thresholds

- [ ] The full-suite results show meaningful hard-task coverage expansion.
- [ ] The full-suite results show meaningful improvement on medium/easy tasks in at least one of:
  - runtime
  - `effective_total_tokens`
  - stability
- [ ] Harness-induced failures are materially reduced relative to earlier runs or baseline behavior.
- [ ] At least one important success case is clearly attributable to autonomous pipeline behavior rather than manual task-skill editing.
- [ ] The release claim can be stated narrowly and defended by the available evidence.

## F. Must-Have Documentation Checks

- [ ] Top-level README explains what `MasterSkill` is in one page.
- [ ] README includes a quickstart that a new user can actually follow.
- [ ] `MasterSkill/readme.md` matches the current runtime and directory layout.
- [ ] `roadmap.md` reflects the current two-stage strategy:
  - publishable OSS first
  - paper-grade system claim after that
- [ ] `phase1_runbook.md` reflects the current frozen-run protocol.
- [ ] `pipeline_todo.md` reflects the current pipeline-debugging protocol.
- [ ] Result directories and benchmark artifacts are documented clearly.
- [ ] Known limitations are documented clearly.
- [ ] Reproducibility instructions are documented clearly.

## G. Must-Have Repository Hygiene Checks

- [ ] Failed transient candidate skills are not cluttering the repo.
- [ ] Unnecessary generated artifacts are ignored or cleaned up.
- [ ] The repo does not depend on hidden local state to reproduce the reported results.
- [ ] The default branch is in a state that another user can clone and understand.
- [ ] Pushed benchmark evidence matches the documented commands and commit state.

## H. Nice-to-Have Before Release

- [ ] One small repeated run confirms the main outcome is not a one-off fluke.
- [ ] There is at least one concise case-study document for a hard task.
- [ ] There is at least one concise case-study document for an autonomous candidate-skill improvement case.
- [ ] There is a compact benchmark result table suitable for README or release notes.
- [ ] There is a compact “how to inspect failures” guide for contributors.

## I. Nice-to-Have For High-Star Potential

- [ ] The project has a clear one-sentence positioning statement.
- [ ] The README includes an opinionated example that feels impressive on first read.
- [ ] The evaluation story is easy to understand without reading internal logs.
- [ ] The repo surfaces a strong “why this matters” narrative for:
  - hard tasks
  - skill refinement
  - benchmark-driven iteration
- [ ] The release notes explain what is genuinely new relative to naive baseline execution.

## J. Nice-to-Have For Paper Trajectory

- [ ] The release evidence already separates:
  - harness recovery
  - bundled-skill leverage
  - autonomous candidate-skill refinement
  - mixed outcomes
- [ ] There is a shortlist of clean tasks for future seedless experiments.
- [ ] There is a shortlist of transferable candidate-skill cases worth deeper analysis.
- [ ] The release does not overclaim beyond what the data supports.

## Immediate Release Blockers To Track

- [ ] Clean hard-task runs still need to converge to either credible solves or clean, interpretable failures.
- [ ] Autonomous candidate-skill optimization still needs at least one explicit success case under the new guardrails.
- [ ] The frozen full-suite `current/evolved` sweep still needs to be run.
- [ ] The frozen full-suite baseline sweep still needs to be run.
- [ ] Full-suite evidence still needs to show meaningful progress before release.

## Release Decision Rule

Do not release just because the checklist is “mostly green”.

Release when:

- all must-have sections are satisfied
- no blocker remains in the “Immediate Release Blockers” section
- the full-suite evidence supports a narrow but strong OSS claim

If any of those fail, keep iterating on the pipeline rather than forcing a release.
