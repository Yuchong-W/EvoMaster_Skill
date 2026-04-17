# MasterSkill Technical Design

## Non-Negotiable Priorities

1. The only success criterion is passing the real official task tests in the real execution environment.
   Improvements that only look better in prompts, logs, or Judger output do not count unless they increase real pass rate.
2. The primary object being optimized is the `skill`.
   Runner, routing, judging, and memory changes are only justified when they help the system discover, reuse, refine, or execute better skills that pass real tests.

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
8. If the task already passes, optionally continue with post-pass optimization to distill a lower-cost skill without losing correctness.

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
- `BenchmarkResultStore`: compact per-run telemetry for later benchmark analysis

Current implementation requirement:

- memory persistence must round-trip enums and nested dataclasses
- task records must exist before updates
- solved skills must be written back to the shallow repository
- each benchmark run must persist task status, model choice, duration, score, and failure class

### 3. Runner Layer

`BenchmarkRunner` owns the benchmark loop:

- raw attempt
- task analysis
- skill reuse lookup
- research / skill creation
- real test
- judge / quick proposer / reflector loop
- optional post-pass optimization loop after a solved result

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
- `gpt-5.2`, `gpt-5.3-codex`, `gpt-5.4` use bounded Codex reasoning tuned for runtime cost

Codex CLI compatibility notes:

- ChatGPT-account Codex execution does not support `gpt-5.1`
- internal Codex-backed calls therefore map `gpt-5.1 -> gpt-5.2`
- internal agents use shorter bounded timeouts plus a lower-effort retry on timeout to keep research iterations moving

### Execution Model Routing

The execution agent is set to `auto`.

`DockerExecutor` now delegates execution routing to `runner/task_router.py`, which builds an explicit `ExecutionPlan` from task metadata plus task shape.

Routing inputs:

- `task.toml` difficulty
- `task.toml` category
- `task.toml` tags
- instruction length
- output artifact type
- skill payload size

`TaskRouter` chooses the execution model by resolved task difficulty:

- hard optimization / simulation / citation verification / long tasks -> `gpt-5.4`
- medium structured tasks -> `gpt-5.3-codex`
- lighter tasks -> `gpt-5.2` or `gpt-5.1`

Each execution result now also carries:

- chosen model
- reasoning effort
- routing reason
- resolved difficulty
- execution duration
- failure class

## Execution Architecture

### Accepted Route: Host-Side Codex Controls Docker

Current production route:

1. Build the task image.
2. Start the task container in keepalive mode.
3. Copy only the instruction and skill into the container for the model-facing phase.
4. Create a temporary host workspace with helper scripts:
   - `task_shell`
   - `task_put`
   - `task_get`
5. Run host-side `codex exec --ephemeral` using the currently logged-in ChatGPT account.
6. Let Codex operate on the running container through `docker exec` and `docker cp`.
7. Copy official tests into the container only after the model finishes, then run verification.
8. Return execution log, artifacts, and test output to the runner.

Runtime-cost controls layered onto this route:

- environment image cache keyed by `task/environment` content hash
- compatibility reuse of older unlabeled local `masterskill:<task>` images
- task-scoped verifier runtime images for prewarming common `test.sh` dependencies
- staged time budgets for:
  - base model attempt
  - skill execution
  - official real test
- debug logging behind `MASTERSKILL_DEBUG=1` for both executor and internal agents

Research-context controls layered onto this route:

- task-bundled skills from `environment/skills` are summarized into `TaskContext`
- `Searcher` and `SkillCreator` both receive bundled-skill summaries
- this biases research toward reusing task-local expert tooling before inventing a disconnected skill from scratch
- task-local bundled skills are also loaded as executable seed candidates before cross-task transfer skills
- bundled seed ordering is stabilized by original skill timestamp so curated task skills are tried before newly generated local variants

Task-root controls layered onto this route:

- when `MasterSkill/case` exists, it becomes the default task root
- this keeps active task evolution in a repo-local case area instead of mutating the external
  `/home/yuchong/skillsbench` tree by default

Leakage controls layered onto this route:

- task execution and official evaluation no longer share the same container
- after model execution, only changed task artifacts from allowed writable roots are exported
- official tests run in a fresh container restored only with those artifacts
- `/tests`, `/solution`, Codex/Claude skill directories, and system paths are not restored into evaluation
- host-side Codex still operates only inside an ephemeral helper workspace rather than the task root itself

Loop-efficiency controls layered onto this route:

- `QuickProposer` is now bypassed for clearly operational Judger failures
- execution-layer failures such as missing outputs, wrong formats, timeouts, and dependency/runtime errors go straight back toward research instead of consuming wording-only refinement budget

Post-pass optimization controls layered onto this route:

- `post_solve_optimization_rounds` allows continuing to optimize after a task is already solved
- optimization candidates are generated by `SkillCreator.optimize_skill()`
- when the baseline solve came from the base model instead of a skill, optimization prompts explicitly frame the task as distillation of the successful behavior rather than compression of a previously failing bundled skill
- failed optimization attempts feed their Judger and real-test failure summaries into the next optimization round
- only materially improved candidates are persisted back to the task-local skill repository
- large real runtime/token wins are allowed to outweigh moderate `skill_md_size` regressions, because official execution cost is the primary optimization target

Judger-visibility controls layered onto this route:

- executor summaries now put `[Output Artifacts]` before long execution narration for skill-guided runs
- `Judger` now receives a compacted execution result that preserves both the beginning and the end of the transcript
- this keeps final validated artifacts such as `/root/answer.json` visible even when the agent produced a long reasoning trace

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

Additional verifier-runtime assumptions:

- verifier bootstrap may be flaky on Ubuntu mirrors and must be treated as a best-effort prewarm, not a hard prerequisite for running the test
- if task-scoped verifier prewarm keeps failing, the executor must still continue with the base task image and run the official verifier there

## Test Strategy

Current verification strategy is layered:

1. import and CLI sanity checks
2. `py_compile` / `compileall`
3. targeted memory and config smoke tests
4. direct Docker task execution
5. official task tests through `run_task()`
6. fail-fast hard-task validation to confirm the system reaches the research / skill loop instead of stalling in the base attempt

Result artifacts from task runs are persisted under:

- `<data_root>/benchmark_runs/runs.jsonl`
- `<data_root>/benchmark_runs/tasks/<task_id>.jsonl`
- `<data_root>/benchmark_runs/latest/<task_id>.json`

Optimization and trace artifacts are also persisted under:

- `<data_root>/shallow/trace/<task_id>.jsonl`
- `<data_root>/shallow/skills/<skill_id>/`

## Current Limits

- post-pass optimization is now looped and feedback-aware, but it still depends on the quality of the distilled skill prompt and currently has not yet converted `enterprise-information-search` into a passing optimized skill
- the newest runtime/token forwarding fix landed after the first successful `financial-modeling-qa` optimization run, so that specific run records skill-size improvement more clearly than runtime/token improvement
- paper-era `With Skills = 0%` classifications should still be treated as historical benchmark observations, not overwritten by local harness improvements

Representative benchmark targets used during bring-up:

- `civ6-adjacency-optimizer`
- `weighted-gdp-calc`
- `flood-risk-analysis`
- `citation-check`

Representative runtime validation milestones:

- `citation-check`: confirmed real benchmark pass with persisted run record
- `civ6-adjacency-optimizer`: confirmed real research loop progression through `Analyzer -> Searcher -> SkillCreator -> Critic -> execute_skill -> Judger -> QuickProposer`

## Known Limits

- Some SkillsBench tasks have task-side inconsistencies between `solution/solve.sh` and the official tests.
- Large task images with `libreoffice` or heavy pip installs have long first-run setup time.
- The execution model still depends on prompt quality and benchmark difficulty; a clean environment does not imply a task pass.
- The current execution router is metadata-driven and explicit, but still rule-based rather than learned.
- Some verifier scripts still encode task-specific dependency setup patterns that are not yet lifted into reusable runtime prewarm rules.
- Research-loop quality is now gated more by skill quality and agent prompting than by basic chain breakage.
- `SkillBundle` still represents support files as text-only relative paths; binary assets are not yet first-class in the evolution format.
- Some bundled task skills ship reference material outside `scripts/`; the current loader intentionally filters out `LICENSE` / `README`-style files and keeps executable/support files only.
- Docker / WSL daemon availability is still an external operational dependency; when that layer is unstable, the benchmark loop cannot be fully exercised even if the code path is ready.

## Next Design Work

- Cache or prebuild heavy SkillsBench images to reduce repeated environment setup.
- Move host-Codex helper scripts into a reusable module instead of generating them ad hoc.
- Extend benchmark result persistence with aggregate reports and pass-rate deltas over time.
- Collapse duplicated legacy/package trees once package entrypoints become the default.
- Replace the rule-based execution router with either benchmark-supplied routing metadata or a learned router once enough run history exists.
- Improve the QuickProposer / research loop so hard tasks spend less time on wording-only revisions when execution artifacts show missing-output or timeout failures.
- Promote failed-attempt persistence into richer loop control so repeated Judger / QuickProposer churn can trigger earlier strategy shifts without waiting for a final abandon state.
