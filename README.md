# EvoMaster_Skill

This repository is currently centered on `MasterSkill`: a benchmark-driven skill
discovery and evaluation system for `SkillsBench`.

The active goal is not ICML paper analysis. The repo now focuses on:

- running a fixed base model plus external skills against real benchmark tasks
- evolving task-local or transferable skills that improve pass rate, runtime, or token cost
- validating improvements with official task tests in real Docker-backed environments
- tracking pre-evolution baselines versus current/evolved chains

## Current Layout

- `MasterSkill/`
  Main local runtime, benchmark loop, memory stores, docs, and result snapshots.
- `MasterSkill/case/`
  Local case root for tasks under active evolution. This is the default task root
  when present, so ongoing task-local skill writes happen here instead of in an
  external SkillsBench checkout.
- `src/icml_research/masterskill/`
  Installable package mirror kept in sync with the local runtime.
  The `icml_research` namespace is legacy packaging baggage, not the current
  project focus.
- `scripts/`
  Operational helpers such as overnight runners and monitors.
- `DeepResearch/` and `DRskill/`
  Earlier supporting experiments that informed the current direction but are no
  longer the primary repo entrypoint.

## Key Docs

- Roadmap: `MasterSkill/roadmap.md`
- Phase 1 runbook: `MasterSkill/phase1_runbook.md`
- Technical design: `MasterSkill/technical_design.md`
- Project state: `MasterSkill/state.md`
- Session resume / recovery notes: `MasterSkill/session_resume.md`
- Development log: `MasterSkill/development_log.md`
- SkillsBench task classification context: `MasterSkill/skillsbench_task_classification.md`
