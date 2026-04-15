# MasterSkill Technical Design

## Scope

This document records the current technical routes for `MasterSkill`, including accepted architecture, rejected alternatives, package layout, model routing, execution strategy, and known limits.

## System Goal

`MasterSkill` is a benchmark-driven skill discovery system for `SkillsBench`.

The target loop is:

1. Run the base model on a benchmark task without a skill.
2. If the task fails, analyze the task and the failed trace.
3. Reuse an existing skill if a transferable one already exists.
4. Otherwise generate or refine a new skill through research and critique.
5. Re-run the task with the skill in a real execution environment.
6. Judge the result from execution artifacts and tests, not from the skill text alone.
7. Store task experience and meta-memory for future reuse.

## Code Layout

Two code layouts are maintained in parallel:

- Legacy runtime entry: `MasterSkill/`
- Package-style layout: `src/icml_research/masterskill/`

Current policy:

- `MasterSkill/` remains the direct execution path used for local debugging.
- `src/icml_research/masterskill/` is kept in sync as the installable package target.
- `pyproject.toml` and `scripts/run_research.py` provide the package-oriented entry path for the broader repo.

This dual-layout route was chosen because the repo already had working imports based on `MasterSkill/`, while packaging work had already started under `src/`.

## Accepted Architecture

### 1. Agent Layer

Internal agents are split by role:

- `Searcher`: gathers candidate solution ideas
- `Analyzer`: identifies the task bottleneck
- `Critic`: filters weak or grinding-style proposals
- `SkillCreator`: produces a skill bundle
- `QuickProposer`: proposes cheap wording or tactical fixes
- `Judger`: evaluates actual execution results
- `Reflector`: reasons about repeated judge failures and trigger thresholds

### 2. Memory Layer

Three memory surfaces are used:

- `ShallowMemory`: per-task attempts and recent skill usage
- `TaskExperienceMemory`: durable task-level outcomes and status
- `MetaMemoryStore`: reusable effective and ineffective methods grouped by `problem_type::domain::modeling`

Current implementation requirement:

- memory persistence must round-trip enums and nested dataclasses
- task records must exist before updates
- solved skills must be written back to the shallow repository

### 3. Runner Layer

`BenchmarkRunner` owns the benchmark loop:

- raw attempt
- task analysis
- skill reuse lookup
- research / skill creation
- real test
- judge / quick proposer / reflector loop

The current runner depends on `DockerExecutor` for any real task execution.

## Model Routing

### Internal Agent Routing

The internal planning and evaluation agents are now routed through GPT-5 family models:

- `quick_proposer` -> `gpt-5.1`
- `searcher` / `analyzer` / `critic` -> `gpt-5.2`
- `judge` / `reflector` -> `gpt-5.3-codex`
- `skill_creator` -> `gpt-5.4`

Reasoning policy:

- `gpt-5.1` uses `high`
- `gpt-5.2`, `gpt-5.3-codex`, `gpt-5.4` use `xhigh`

This policy exists because `gpt-5.1` rejects `xhigh`.

### Execution Model Routing

The execution agent is set to `auto`.

`DockerExecutor` chooses the execution model by task difficulty:

- hard optimization / simulation / citation verification / long tasks -> `gpt-5.4`
- medium structured tasks -> `gpt-5.3-codex`
- lighter tasks -> `gpt-5.2` or `gpt-5.1`

Current keyword-based routing lives in `runner/docker_executor.py`.

## Execution Architecture

### Accepted Route: Host-Side Codex Controls Docker

Current production route:

1. Build the task image.
2. Start the task container in keepalive mode.
3. Copy instruction, skill, and tests into the container.
4. Create a temporary host workspace with helper scripts:
   - `task_shell`
   - `task_put`
   - `task_get`
5. Run host-side `codex exec --ephemeral` using the currently logged-in ChatGPT account.
6. Let Codex operate on the running container through `docker exec` and `docker cp`.
7. Run official tests inside the container.
8. Return execution log, artifacts, and test output to the runner.

Why this route was accepted:

- it reuses the local `~/.codex/auth.json` ChatGPT login without requiring an API key
- it avoids container-side access problems to `chatgpt.com`
- it keeps the benchmark environment isolated inside Docker
- it still allows the model to inspect and mutate files inside the task container

### Rejected Route A: In-Container Claude CLI

Old route:

- mount host Claude CLI into the container
- load Anthropic auth from env or `~/.claude/settings.json`
- execute the task directly in the container

Why it was rejected:

- the repo needed to move away from the existing GLM / Claude proxy path
- the user explicitly requested switching to the current ChatGPT login
- model routing and auth behavior were harder to reason about in the existing proxy setup

### Rejected Route B: In-Container Codex CLI

Attempted route:

- mount host `codex` CLI, host `node`, and host auth into the container
- run `codex exec` directly inside the task container

Why it was rejected:

- host `node` required shared libraries and builtin resources inside the container
- even after runtime fixes, the container could not reliably connect to `chatgpt.com`
- writable session state under `~/.codex` was still required
- the approach was more fragile than host-side control

## Environment Assumptions

Current required host-side components:

- Docker engine reachable from WSL/Linux
- Python `docker` package
- Python `openai` package
- `codex` CLI installed on host
- current ChatGPT login stored in `~/.codex/auth.json`

Current required task-side baseline:

- Docker task image must support `bash`
- tests are expected under `/tests`
- execution artifacts must be writable in task-defined output paths

## Test Strategy

Current verification strategy is layered:

1. import and CLI sanity checks
2. `py_compile` / `compileall`
3. targeted memory and config smoke tests
4. direct Docker task execution
5. official task tests through `run_task()`

Representative benchmark targets used during bring-up:

- `civ6-adjacency-optimizer`
- `weighted-gdp-calc`
- `flood-risk-analysis`
- `citation-check`

## Known Limits

- Some SkillsBench tasks have task-side inconsistencies between `solution/solve.sh` and the official tests.
- Large task images with `libreoffice` or heavy pip installs have long first-run setup time.
- The execution model still depends on prompt quality and benchmark difficulty; a clean environment does not imply a task pass.
- `DockerExecutor` currently uses heuristic model routing; this should eventually be replaced with explicit task metadata or a learned router.

## Next Design Work

- Replace keyword-based execution routing with a small explicit difficulty classifier.
- Cache or prebuild heavy SkillsBench images to reduce repeated environment setup.
- Move host-Codex helper scripts into a reusable module instead of generating them ad hoc.
- Add benchmark-result persistence so each task run stores model, duration, score, and failure class.
- Collapse duplicated legacy/package trees once package entrypoints become the default.
