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

### System Optimization Pass

Focused follow-up based on `technical_design.md` next steps:

- replaced keyword-only execution routing with an explicit `TaskRouter`
- made the router read `task.toml` difficulty, category, and tags before falling back to task-shape signals
- fixed a latent routing bug where `DockerExecutor` still referenced nonexistent `skill.content`
- made executor results return model, reasoning effort, resolved difficulty, routing reason, duration, and failure class
- added `BenchmarkResultStore` to persist compact run telemetry under `benchmark_runs/`
- made `BenchmarkRunner` write structured run records with task status, models used, durations, scores, skill IDs, and failure classes
- hardened `problem_type` refinement so invalid analyzer output no longer crashes the runner

Smoke validation:

- `py_compile` passed for both `MasterSkill/` and `src/icml_research/masterskill/`
- task router smoke output:
  - `citation-check` -> `hard`, `gpt-5.4`
  - `weighted-gdp-calc` -> `medium`, `gpt-5.3-codex`
  - `civ6-adjacency-optimizer` -> `hard`, `gpt-5.4`
- benchmark result persistence smoke test wrote a valid latest snapshot under `/tmp/masterskill-result-smoke/latest/demo.json`

### Runtime Validation And Follow-Up Fixes

Real benchmark validation:

- reran `citation-check` with `data_root=/tmp/masterskill-opt-validate`
- task finished `solved`
- persisted run record showed:
  - `final_model = gpt-5.4`
  - `final_score = 1.0`
  - `duration_seconds ~= 574.4`
  - routing reason: `task.toml difficulty=medium; category=research; hard tags present`

Follow-up issue discovered from that run:

- when a task was solved directly by the base model, `BenchmarkRunner.run_task()` returned early before writing `task_experience`
- this meant solved tasks could be rediscovered as unsolved in later benchmark runs

Fix:

- added `_on_base_model_solved()` to persist:
  - `task_experience.final_status = solved`
  - `what_worked = Solved without external skill using <model>`
  - shallow trace entry with `skill_id = __base_model__`

Validation:

- runner smoke test under `/tmp/masterskill-base-success-smoke` confirmed:
  - `task_experience` now records solved status for base-model success
  - shallow trace records `__base_model__`
  - `benchmark_runs/latest/<task>.json` remains consistent with solved status and final model

Docker supervision note:

- a later `citation-check` rerun showed the container entering test phase and spending significant tail time in `pip3 install --break-system-packages uv`
- this confirms the runtime chain remains live, but test dependency bootstrap can dominate tail latency even after model execution completes

### Runtime Cost Reduction And Real Skill-Evolution Validation

Additional runtime optimizations:

- added Docker environment image caching keyed by a content hash of `task/environment`
- added compatibility reuse for older unlabeled `masterskill:<task>` images so existing local cache is not discarded
- added task-scoped verifier runtime image prewarming from `tests/test.sh` bootstrap commands
- split execution budgets into:
  - `initial_attempt_timeout_seconds`
  - `skill_execution_timeout_seconds`
  - `real_test_timeout_seconds`
- reduced internal Codex-agent reasoning pressure:
  - `gpt-5.2`, `gpt-5.3`, `gpt-5.4` internal agents now use lighter Codex reasoning than the original `xhigh` path
  - internal Codex calls now use bounded per-model timeouts and a lower-effort retry on timeout
- fixed unnecessary `uv` installation in `_run_tests()` so it only happens when `test.sh` actually uses `uvx`
- added executor and agent debug logging behind `MASTERSKILL_DEBUG=1`

Real chain validation on `civ6-adjacency-optimizer`:

- confirmed runtime now reports `legacy image cache hit`, so pre-existing local task images are reused immediately
- confirmed fail-fast base attempt path:
  - base `codex exec` timed out under the shortened initial budget
  - runner continued into post-failure analysis instead of stalling
- confirmed real skill-evolution loop now executes:
  - `Analyzer`
  - `Searcher`
  - `SkillCreator`
  - `Critic`
  - `DockerExecutor.execute_skill()`
  - `Judger`
  - `QuickProposer`

Concrete blockers found and fixed from real `civ6` evolution runs:

- `Analyzer.USER_PROMPT` had unescaped JSON braces and crashed on `.format(...)`
- same prompt-format bug also existed in `Searcher.USER_PROMPT` and `Critic.USER_PROMPT`
- `QuickProposer` failed under host Codex + ChatGPT login because `gpt-5.1` is unsupported in that route
- fixed Codex fallback compatibility by mapping `gpt-5.1 -> gpt-5.2` for CLI-backed internal agents

Current status after these fixes:

- MasterSkill is no longer limited to base-model passes
- the system can now enter and progress through the real research / skill creation / critique / execution / judging loop on a hard task
- remaining work is about improving task solve rate and iteration quality, not about basic chain breakage

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
