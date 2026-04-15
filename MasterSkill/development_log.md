# MasterSkill Development Log

## 2026-04-14

### Repository Review

- Read `MasterSkill/readme.md`, `MasterSkill/state.md`, and the runner / memory / skill code.
- Confirmed the project is an automated skill-discovery loop for `SkillsBench`, not just a static skill repo.
- Identified that the repo was between prototype cleanup and package migration.

### Structural Bug Fixes

Fixed import and runtime blockers across the legacy tree and mirrored them into `src/icml_research/masterskill/`.

Key fixes:

- repaired broken imports in `core/__init__.py`, `skill/__init__.py`, and `agents/reflector.py`
- fixed `QuickProposer` / `Analyzer` handling of trace entries
- fixed `SkillRepository.save_skill()` using undefined state
- fixed CLI config propagation in `core/config.py`
- fixed runner logic around research triggers, method summaries, and shallow-memory writeback
- fixed memory serialization / deserialization for enums and nested dataclasses
- removed abstract-method instantiation blocker in `agents/base.py`
- aligned `judger` / `judge` config aliasing

### Initial Environment Bring-Up

Installed host dependencies:

- `openai`
- `docker`

Docker setup work:

- verified Docker Desktop status from WSL
- started Docker Desktop explicitly from Windows
- confirmed Docker SDK connectivity from Python

### Claude / GLM Path Investigation

Observed initial execution path:

- host CLI: Claude Code
- remote/proxy model path resolved to `glm-5`

Findings:

- local Claude settings existed under `~/.claude/settings.json`
- host environment also had `ANTHROPIC_API_KEY`
- direct host-side Claude invocation could work after removing the conflicting API-key path

### Docker Executor Repairs

Large executor rework:

- corrected build context to `task/environment`
- kept containers alive with an explicit sleep loop
- copied task tests into `/tests`
- executed real tests in the same container as the model run
- fixed bad assumptions around `CompletedProcess`, output decoding, and result fields
- added `uvx` bootstrap fallback for task tests that assumed `uvx` existed

### Task Bring-Up Results

`civ6-adjacency-optimizer`

- official oracle solution could run in the image and write `/output/scenario_3.json`
- benchmark tests exposed a task-side inconsistency: oracle output shape did not fully satisfy the strict format tests
- direct model execution still failed to produce the required output file within the allowed time

`weighted-gdp-calc`

- image build completed successfully
- official test path exposed that the task test script required `uvx` but the image did not provide it
- this led to the executor-side `uvx` bootstrap fix

`flood-risk-analysis`

- environment execution progressed into real task work
- task setup was slowed down by additional package installation during runtime

## 2026-04-15

### Switch To ChatGPT Login / GPT-5 Family

User requirement:

- stop using the old Claude/GLM route
- use the current logged-in ChatGPT account
- use GPT-5.1 to GPT-5.4 depending on task difficulty

Validation results on host:

- `codex` CLI exists
- `~/.codex/auth.json` uses `auth_mode = chatgpt`
- verified host-side access to:
  - `gpt-5.1`
  - `gpt-5.2`
  - `gpt-5.3-codex`
  - `gpt-5.4`

Important compatibility note:

- `gpt-5.1` does not support reasoning effort `xhigh`

### Internal Agent Migration

Changed internal model assignments:

- `quick_proposer` -> `gpt-5.1`
- `searcher` / `analyzer` / `critic` -> `gpt-5.2`
- `judge` / `reflector` -> `gpt-5.3-codex`
- `skill_creator` -> `gpt-5.4`

Changed `BaseAgent` behavior:

- if `OPENAI_API_KEY` exists, keep using the OpenAI SDK path
- otherwise fall back to host-side `codex exec` using the ChatGPT login

Smoke test:

- instantiated `BaseAgent('gpt-5.1')`
- verified it answered successfully through the Codex login path

### Execution Architecture Migration

Attempt 1: in-container Codex

- mounted host `codex`, `node`, and auth into a container
- resolved several runtime issues:
  - missing `libnode.so`
  - missing `/usr/share/nodejs`
  - read-only session state
- final blocker remained container-side connectivity to `chatgpt.com`

Decision:

- abandoned in-container Codex as the primary route

Attempt 2: host-side Codex controlling Docker

Implemented current route:

- start task container in keepalive mode
- generate host helper scripts:
  - `task_shell`
  - `task_put`
  - `task_get`
- run `codex exec --ephemeral` on the host
- let Codex mutate the container through Docker helpers

Smoke test:

- verified host-side Codex could create a file inside a temporary Docker container

### Robustness Fixes

- added clean timeout handling for host-side `codex exec`
- ensured timeouts return a normal failed task result instead of crashing `run_task()`
- cleaned timeout log formatting for byte output
- improved execution prompt to prefer `python3` and base Unix tools in minimal task images
- promoted bibliography / citation tasks to `gpt-5.4`

### Benchmark Test Records

`civ6-adjacency-optimizer`

- host-side Codex path ran successfully through `run_task()`
- the execution log showed `OpenAI Codex` and `model: gpt-5.4`
- result still failed because the model timed out before producing a valid benchmark output

`citation-check`

Run 1:

- task ran through the new execution path
- used `gpt-5.3-codex`
- failed test because the model spent time on weak environment assumptions and partial extraction attempts

Run 2:

- reran after prompt and routing improvements
- used `gpt-5.4`
- passed the official benchmark test

Result:

- first confirmed real SkillsBench pass through the new ChatGPT-account execution architecture

## Current Environment Snapshot

- host OS path in use: `/home/yuchong`
- Docker engine reachable from WSL/Linux
- host `codex` CLI available at `/usr/local/bin/codex`
- logged-in account source: `~/.codex/auth.json`
- repo branch during this work: `master`
- remote target: `origin https://github.com/Yuchong-W/EvoMaster_Skill.git`

## Current Submission Contents

This submission includes:

- MasterSkill bug fixes
- GPT-5 model routing updates
- host-side Codex execution architecture
- package-layout mirror under `src/icml_research/masterskill`
- root `pyproject.toml`
- `scripts/run_research.py`
- this development log
- `technical_design.md`
