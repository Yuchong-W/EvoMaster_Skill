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

- Technical design: `MasterSkill/technical_design.md`
- Project state: `MasterSkill/state.md`
- Session resume: `MasterSkill/session_resume.md`
- Development log: `MasterSkill/development_log.md`
- SkillsBench task classification: `MasterSkill/skillsbench_task_classification.md`
