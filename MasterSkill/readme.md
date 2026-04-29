# MasterSkill

`MasterSkill` is the active runtime and experimentation area of this repository.

It is a benchmark-driven skill discovery system aimed at `SkillsBench` tasks:

- try a fixed base model in the real task environment
- analyze failures and reuse existing skills when possible
- research or synthesize new skills when reuse is insufficient
- validate only against official task tests
- keep optimized skills only when they improve correctness, runtime, or token cost

## Repository Role

This directory is the direct local execution path used for:

- benchmark runs
- Docker-backed task execution
- memory and benchmark result persistence
- post-solve optimization
- experiment logging and recovery

The parallel package mirror remains under `src/icml_research/masterskill/`, but
that namespace is retained only for compatibility with the repo's earlier layout.

## Docs

Active docs:

- Paper plan for `2026-05-13`: `MasterSkill/paper_plan_20260513.md`
- Project state and active doc map: `MasterSkill/state.md`
- Technical design: `MasterSkill/technical_design.md`
- Development log: `MasterSkill/development_log.md`

Reference / archival docs:

- Phase 1 OSS runbook: `MasterSkill/phase1_runbook.md`
- Phase 1 tactical todo: `MasterSkill/pipeline_todo.md`
- Phase 1 release checklist: `MasterSkill/release_checklist.md`
- Earlier session recovery notes: `MasterSkill/session_resume.md`
- Historical task classification context: `MasterSkill/skillsbench_task_classification.md`
