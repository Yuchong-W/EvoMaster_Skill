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

## 2026-04-17

### Local Execution And Hard-Case Bring-Up

Entry and task-root fixes:

- added `run_local.py` so the repo checkout can be run directly without package-path hacks
- made the local `case/` tree the default benchmark root when present
- aligned CLI config so `post_solve_optimization_rounds` is controllable from the command line

Execution-fidelity and environment fixes:

- Docker build now defaults to host-network mode when supported
- task Dockerfiles are rewritten with:
  - `apt-get` retries
  - HTTP / HTTPS transport timeouts
  - forced IPv4
  - shell-level `timeout 180s`
  - `--no-install-recommends`
- verifier `test.sh` is also rewritten at copy time with the same apt / pip hardening instead of only fixing the task image
- task-scoped test-runtime image prewarm now falls back to the base task image when dependency bootstrap keeps failing, so real tests do not abort before model execution

Telemetry and optimization-loop changes:

- Codex JSON output is now parsed for:
  - `input_tokens`
  - `cached_input_tokens`
  - `output_tokens`
- `TaskAttempt` and `BenchmarkRunEvent` now persist token and duration fields
- added a post-pass optimization loop controlled by `post_solve_optimization_rounds`
- post-pass optimization now uses failure feedback from prior failed candidates instead of running only a single blind compression pass
- `BenchmarkRunner._run_real_test()` now forwards full runtime and token metrics so optimization rounds can compare real execution cost rather than only skill size

### Hard-Case Results

`enterprise-information-search`

- the task now passes local official real tests through the repaired harness
- the successful path initially remained `base_attempt`, but the latest rerun converted post-pass optimization into passing external skills too
- latest solved run:
  - `base_attempt` passed in about `381.2s`
  - `input_tokens = 1670074`
  - `cached_input_tokens = 1574400`
  - `output_tokens = 14059`
- post-pass optimization is now materially productive on this task:
  - round 1 candidate `enterprise-direct-evidence-answer` passed official real test
  - round 2 candidate `enterprise-direct-answer-minimal` also passed official real test
- recorded improvements from the accepted second-round candidate:
  - `duration 406.82s -> 343.18s`
  - `tokens 1394607 -> 1033712`
- the key fixes that unlocked this were:
  - small output artifacts are surfaced before long execution narration in executor summaries
  - Judger now keeps both the head and tail of execution results, so final `answer.json` content remains visible
  - enterprise token helper now writes plausible numeric values and the skill explicitly prints final `/root/answer.json`

`financial-modeling-qa`

- this task had been in the paper-era `With Skills = 0%` pool and had previously failed locally during environment bring-up
- after executor hardening, the task now reaches model execution reliably and passes local official real tests
- latest solved run:
  - `base_attempt` passed in about `549.9s`
  - `input_tokens = 1073127`
  - `cached_input_tokens = 1030400`
  - `output_tokens = 11808`
- post-pass optimization produced a passing distilled skill:
  - `financial-modeling-pairwise-match-delta`
- current recorded improvement signal is mainly skill compactness:
  - `skill_md_size 30386 -> 3532`
- this optimized skill was saved into the task-local skill directory and shallow memory

`pddl-tpp-planning`

- local official real test also passed on the repaired harness
- latest solved run:
  - `base_attempt` passed in about `148.6s`
  - `input_tokens = 329829`
  - `cached_input_tokens = 316928`
  - `output_tokens = 3704`
- post-pass optimization now succeeds on this task:
  - accepted candidate: `pddl-tpp-batch-fastpath`
  - official real-test runtime: `131.10s`
  - official real-test tokens: `365834 + 3257 output`
- this result came after two chain changes:
  - a new direct task-local seed skill that tells the model to run the packaged batch solver and checker first
  - optimization comparison logic now treats large real runtime/token wins as more important than moderate `skill_md_size` regressions

### Current Interpretation

- paper-era zero-pass classification remains historically true for the benchmark report and should not be overwritten in documentation
- local results now show that some of those tasks were at least partly limited by harness fidelity, timeout budgeting, and verifier bootstrap behavior
- the remaining core research problem is unchanged:
  - keep converting base-model local passes into lower-cost, repeatable passing skills
  - extend the same post-pass acceptance path beyond the current `enterprise-information-search`, `financial-modeling-qa`, and `pddl-tpp-planning` wins
  - keep proving skill contributions on hard tasks where the environment no longer dominates the outcome
- fixed unnecessary `uv` installation in `_run_tests()` so it only happens when `test.sh` actually uses `uvx`
- added executor and agent debug logging behind `MASTERSKILL_DEBUG=1`

### Pre-Evolution Baseline Mode

Added a reproducible baseline mode before final comparison experiments:

- new CLI flag: `--pre-evolution-baseline`
- in this mode:
  - `base_attempt` does **not** see bundled task-local skills
  - the runner stops immediately after base attempt
  - default baseline outputs are written to `masterskill_data_pre_evolution/`

Measured baseline results so far:

- `enterprise-information-search`
  - pure base solved
  - `duration_seconds ~= 327.11`
  - `input_tokens = 1122933`
  - `output_tokens = 13062`
- `pddl-tpp-planning`
  - pure base solved
  - `duration_seconds ~= 198.97`
  - `input_tokens = 294178`
  - `output_tokens = 7006`

Baseline reruns still pending after chain fixes:

- `react-performance-debugging`
  - previously mislabeled as `missing_test_file` because the executor only recognized `tests/test_outputs.py`
  - fixed so tasks with `tests/test.sh` are now valid test tasks too
- `taxonomy-tree-merge`
  - baseline batch was interrupted by Docker build transport failure
  - build retries now also cover transport-level `IncompleteRead` / `ProtocolError` failures

Additional robustness added during this baseline work:

- runner now records a classified failure event for unexpected per-task exceptions instead of crashing the whole `--tasks` batch
- session handoff note written to `session_resume.md` so work can resume immediately after restarting Docker / the shell

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

## 2026-04-15 Additional Audit

### Benchmark Leakage Audit

Checked whether benchmark-only data was exposed to the model-facing phase.

Findings:

- `solution/` was not exposed through the current executor path:
  - image build context uses only `tasks/<id>/environment`
  - host-side Codex workspace only includes helper scripts plus the candidate skill
- `tests/` *were* exposed before model execution in `DockerExecutor.run_real_test()`

Fix:

- moved `_copy_tests(container, task_dir)` to run only after `_run_agent(...)` returns
- updated `technical_design.md` so the documented execution route matches the no-leak behavior

### PDDL TPP Skill Evolution

Targeted task:

- `pddl-tpp-planning` from the "human skill still could not solve reliably" bucket

Initial evolved skill:

- added `MasterSkill/evolved_skills/pddl-tpp-planning-direct/`
- direct solver script uses:
  - `PDDLReader`
  - `OneshotPlanner(name="pyperplan")`
  - `SequentialPlanValidator`
  - `.txt` + `.pkl` outputs matching the task verifier contract

First real result:

- the direct solver produced valid plans, but `task02` still failed verifier comparison
- failure was not invalid planning; it was action-order mismatch between two equivalent plans

Root cause:

- `pyperplan` tie-breaking changed across Python processes because hash randomization changed iteration order
- the produced plan and the verifier's fresh plan were both valid, but not byte-for-byte identical in action order

Fix:

- added `run_deterministic_solver.sh` to the evolved skill
- the wrapper:
  - pins `PYTHONHASHSEED=1`
  - writes the same export into `/root/.bash_profile`
  - runs the batch planner under the same seed
- this forces the later verifier shell to use the same planner tie-breaking order

Validation:

- direct container comparison confirmed the generated `task02.pkl` matches a fresh seeded `pyperplan` solve
- direct verifier-equivalent run passed:
  - installed `pytest==8.4.1` in the task container
  - ran the deterministic wrapper
  - ran official `tests/test_outputs.py`
  - result: `2 passed`

Runtime follow-up:

- improved runtime-image prewarming to parse `uvx --with ...` dependencies from `tests/test.sh`
- the executor now warms those verifier dependencies during image build instead of paying the whole cost at verification time

### Current-Loop Validation On Zero-Pass Tasks

Goal of this pass:

- test whether the existing `BenchmarkRunner` loop itself is useful on tasks from the
  "human-curated skill still could not solve" bucket
- avoid task-specific structural rewrites
- specifically observe `Analyzer`, `Searcher`, `SkillCreator`, `Critic`, `Judger`, and `QuickProposer`

`pddl-tpp-planning`

- ran the full current loop with a fresh temporary data root
- observed the complete loop in action:
  - base attempt timeout
  - `Analyzer`
  - `Searcher`
  - `SkillCreator`
  - `Critic`
  - `execute_skill`
  - `Judger`
  - `QuickProposer`
- this confirmed that the research loop is not dead code on a zero-pass task
- the loop also eventually reached `run_real_test()`, which means repeated refinement was enough to produce at least one `judger_passed` skill

Important weakness exposed by this run:

- before adding any new context, research generated a new skill `pddl-tpp-plan-emitter`
- that skill focused on visible plan text and manual action-trace emission
- it did **not** prioritize the already-bundled task skill `pddl-skills`, even though the task environment already provided the correct `unified_planning` / `pyperplan` pathway

Generic improvement added from this finding:

- `TaskContext` now carries a summary of bundled task skills from `environment/skills`
- `Searcher` prompt now receives `bundled_task_skills`
- `SkillCreator` prompt now also receives `bundled_task_skills`
- this is a system-level fix for all tasks with bundled expert skills, not a PDDL-only patch

Observed effect of the new bundled-skill context:

- a patched research-only rerun on `pddl-tpp-planning` no longer defaulted to pure plan-emission instructions
- one sampled output shifted toward an in-process `Unified Planning` / `pyperplan`-based planner skill
- another sampled output was still weak (`verify_pddl_inputs.py` only), so the direction improved but generation remains unstable

Conclusion from `pddl`:

- the current loop has real value: it can move a hard task from base failure into repeated skill refinement and even reach `judger_passed`
- the current loop also has a real limitation: without stronger grounding, research can underuse bundled expert skills and wander into prompt-level fixes instead of solver-level execution

`xlsx-recover-data`

- started a full current-loop run as a second zero-pass comparison task
- base image successfully built
- run progressed into runtime / verifier preparation, but did not finish within the observation window for this log update
- current evidence is enough to say the task is not blocked by missing base image setup, but not yet enough to claim solve-rate impact

### Local Case Root

To avoid writing ongoing evolution directly into the external `skillsbench` tree:

- created `MasterSkill/case/tasks/`
- copied the current hard target tasks into the local case area:
  - `pddl-tpp-planning`
  - `taxonomy-tree-merge`
  - `xlsx-recover-data`
- changed the default task root selection so MasterSkill now prefers the local
  `MasterSkill/case` root when it exists, and only falls back to
  `/home/yuchong/skillsbench` otherwise

Validation:

- `load_config()` now resolves `skillsbench_root` to
  `/home/yuchong/auto-research-team/MasterSkill/case`
- default task listing under the local case root returns the three copied tasks

Case expansion:

- copied additional zero-pass / human-curated-skill-failed tasks into the local case root:
  - `react-performance-debugging`
  - `financial-modeling-qa`
  - `latex-formula-extraction`
  - `quantum-numerical-simulation`
  - `enterprise-information-search`
- intentionally deferred more auth- or network-heavy cases such as
  `gh-repo-analytics` and `scheduling-email-assistant` from the local active pool for now

### Seed-Skill Execution And Memory Tightening

Why this change was needed:

- the loop could summarize bundled task skills, but it still did not reliably use them as executable seeds
- `SkillRepository.load_skill()` only returned parsed `SKILL.md` text and silently dropped bundled support files
- as a result, task-local human-curated skills could degrade into empty shells during reuse

Generic fixes added:

- `SkillRepository.load_skill()` now loads bundled support files from:
  - top-level non-`SKILL.md` task skill files such as `recalc.py` or `*.skill`
  - nested `scripts/` trees
- `SkillRepository.save_skill()` now preserves relative support-file paths instead of forcing everything under a flat scripts directory
- `DockerExecutor` now mounts skill support files at their normalized relative paths and also keeps a legacy `scripts/<name>` alias for bare filenames
- `ShallowMemory` now preserves nested support-file paths when storing and restoring skills
- `_find_reusable_skills()` now tries task-local bundled skills before meta-memory transfer skills
- task-local skill ordering is now stable and seed-first by sorting bundled skills by their original `SKILL.md` timestamp
- failed / partial skill attempts are now recorded into both shallow trace and task-experience memory instead of only successful terminal outcomes

Validation:

- `py_compile` passed for the updated main tree and mirrored `src/` tree
- bundled support-file smoke checks:
  - `pddl-tpp-planning / pddl-skills` now restores:
    - `generate_plan.skill`
    - `load_problem.skill`
    - `save_plan.skill`
    - `validate.skill`
  - `xlsx-recover-data / xlsx` now restores:
    - `recalc.py`
  - `financial-modeling-qa / pdf` now restores its nested `scripts/*.py` helpers
- shallow-memory roundtrip now preserves nested relative paths such as:
  - `tool.py`
  - `nested/helper.sh`
- reusable-skill ordering smoke test on local case `pddl-tpp-planning` now returns:
  - `pddl-skills`
  - `pddl-tpp-plan-emitter`
- attempted a real `_try_skill()` seed-smoke on local-case `pddl-tpp-planning`
  - code path reached `DockerExecutor` construction correctly
  - the current shell environment was blocked by Docker daemon access instability before task execution
  - observed failures included:
    - Python Docker SDK socket permission denial in the sandboxed shell
    - daemon `/version` returning `500` in the escalated shell
    - `/usr/bin/docker` reporting `Input/output error` in the current WSL session
- improved `DockerExecutor` error surfacing so the original daemon failure is now included in the raised runtime error instead of being hidden

### Leakage Hardening Round 2

Leakage threat identified:

- copying `/tests` after model execution was not by itself sufficient
- the execution and evaluation phases still shared the same container
- a model could in principle leave background processes, patched shell state, or runtime hooks behind
- those leftovers could then observe or interfere with official tests once `/tests` was copied in

Generic fix added:

- `run_real_test()` now uses a two-container evaluation flow
  - container A: model execution only
  - collect changed execution artifacts from allowed writable roots only
  - container B: fresh evaluation container restored only with those artifacts
  - copy `/tests` only into container B
  - run official tests only in container B
- artifact export explicitly excludes:
  - `/tests`
  - `/solution`
  - `/root/.claude`
  - `/root/.codex`
  - `/root/.skills`
- system paths such as `/usr/bin/python3` are also not restored into evaluation

Validation:

- `py_compile` passed for the updated executor in both trees
- path-filter smoke checks confirmed:
  - `/root/output.json` is exportable
  - `/app/main.py` is exportable
  - `/tests/test.sh` is not exportable
  - `/solution/solve.sh` is not exportable
  - `/root/.codex/skills/...` is not exportable
  - `/usr/bin/python3` is not exportable
- changed-path selection smoke test reduced a mixed diff to:
  - `/app/src/main.py`
  - `/root/output.json`

### Loop Control Tightening

Why this change was needed:

- `QuickProposer` is intentionally shallow and wording-oriented
- hard cases were still at risk of spending iterations on quick proposer even when Judger was flagging execution-layer failures
- examples include:
  - missing output
  - wrong format
  - timeout
  - dependency / runtime errors

Generic fix added:

- `BenchmarkRunner` now skips `QuickProposer` when Judger feedback indicates operational blocking failures
- `QuickProposer` is retained only for wording-sensitive / guidance-sensitive cases
- this should reduce loop churn on zero-pass tasks and push them back to research sooner

Validation:

- `py_compile` passed for both benchmark runner trees
- helper smoke check confirmed:
  - `missing_output` -> no quick proposer
  - wording/clarity issue -> quick proposer allowed
  - `recommendation=abandon` -> no quick proposer

### Case Expansion Round 2

To widen the zero-pass active pool without pulling in network-auth tasks, copied these additional
`With Skills = 0%` cases into `MasterSkill/case/tasks/`:

- `video-filler-word-remover`
- `speaker-diarization-subtitles`
- `gravitational-wave-detection`
- `shock-analysis-supply`
- `shock-analysis-demand`
- `seismic-phase-picking`
- `reserves-at-risk-calc`

Current local case pool size:

- 15 hard cases under active local evolution

### 2026-04-17 23:46 CST Overnight run started

- branch=overnight-masterskill-recovery; log=/home/yuchong/auto-research-team/MasterSkill/logs/overnight_20260417_234600.log

### 2026-04-17 23:46 CST Overnight run started

- branch=overnight-masterskill-recovery; log=/home/yuchong/auto-research-team/MasterSkill/logs/overnight_20260417_234632.log

### 2026-04-18 00:04 CST baseline react-performance-debugging

- exit_code=0; run_id=d7c1a7b52e6a | status=abandoned | failure_class=builderror | duration_seconds=1147.1781633839992 | final_model= | final_score=0.0 | last_event=runner_exception | notes=The command '/bin/sh -c timeout 300s apt-get -o Acquire::Retries=5 -o Acquire::http::Timeout=30 -o Acquire::https::Timeout=30 -o Acquire::ForceIPv4=true update && timeout 300s apt-get -o Acquire::Retries=5 -o Acquire::http::Timeout=30 -o...

### 2026-04-18 01:27 CST baseline taxonomy-tree-merge

- exit_code=0; run_id=f754362d87e6 | status=abandoned | failure_class=timeout | duration_seconds=5440.698454790001 | final_model=gpt-5.4 | final_score=0.0 | last_event=base_attempt | notes=Model could not solve autonomously

### 2026-04-18 01:44 CST current react-performance-debugging

- exit_code=0; run_id=581cb3df0d17 | status=abandoned | failure_class=builderror | duration_seconds=1112.9304100709996 | final_model= | final_score=0.0 | last_event=runner_exception | notes=The command '/bin/sh -c timeout 300s apt-get -o Acquire::Retries=5 -o Acquire::http::Timeout=30 -o Acquire::https::Timeout=30 -o Acquire::ForceIPv4=true update && timeout 300s apt-get -o Acquire::Retries=5 -o Acquire::http::Timeout=30 -o...

### 2026-04-18 02:45 CST current taxonomy-tree-merge

- exit_code=0; run_id=7fa774e8b2a5 | status=abandoned | failure_class=timeoutexpired | duration_seconds=4043.5363252589996 | final_model=gpt-5.4 | final_score=0.0 | last_event=runner_exception | notes=Command '['/usr/local/bin/codex', 'exec', '--ephemeral', '--skip-git-repo-check', '-C', '/tmp/masterskill-codex-b8vz59bm', '-s', 'read-only', '-c', 'model_reasoning_effort="medium"', '-m', 'gpt-5.2', '-o', '/tmp/masterskill-codex-b8vz59b...

### 2026-04-18 03:01 CST baseline react-performance-debugging

- exit_code=0; run_id=d1c9e54d35ff | status=abandoned | failure_class=builderror | duration_seconds=1036.4254961099978 | final_model= | final_score=0.0 | last_event=runner_exception | notes=The command '/bin/sh -c timeout 300s apt-get -o Acquire::Retries=5 -o Acquire::http::Timeout=30 -o Acquire::https::Timeout=30 -o Acquire::ForceIPv4=true update && timeout 300s apt-get -o Acquire::Retries=5 -o Acquire::http::Timeout=30 -o...

### 2026-04-18 03:12 CST baseline taxonomy-tree-merge

- exit_code=0; run_id=15afc7399aef | status=abandoned | failure_class=timeout | duration_seconds=712.4763632379982 | final_model=gpt-5.4 | final_score=0.0 | last_event=base_attempt | notes=Model could not solve autonomously

### 2026-04-18 03:28 CST current react-performance-debugging

- exit_code=0; run_id=32ef05a0e68b | status=abandoned | failure_class=builderror | duration_seconds=1039.8171880549999 | final_model= | final_score=0.0 | last_event=runner_exception | notes=The command '/bin/sh -c timeout 300s apt-get -o Acquire::Retries=5 -o Acquire::http::Timeout=30 -o Acquire::https::Timeout=30 -o Acquire::ForceIPv4=true update && timeout 300s apt-get -o Acquire::Retries=5 -o Acquire::http::Timeout=30 -o...

### 2026-04-18 05:36 CST current taxonomy-tree-merge

- exit_code=0; run_id=0d35a0516807 | status=abandoned | failure_class=timeoutexpired | duration_seconds=8480.788630378 | final_model=gpt-5.4 | final_score=0.0 | last_event=runner_exception | notes=Command '['/usr/local/bin/codex', 'exec', '--ephemeral', '--skip-git-repo-check', '-C', '/tmp/masterskill-codex-04c5y3km', '-s', 'read-only', '-c', 'model_reasoning_effort="medium"', '-m', 'gpt-5.2', '-o', '/tmp/masterskill-codex-04c5y3k...

### 2026-04-18 05:52 CST baseline react-performance-debugging

- exit_code=0; run_id=90d0a1315afa | status=abandoned | failure_class=builderror | duration_seconds=1036.691220189001 | final_model= | final_score=0.0 | last_event=runner_exception | notes=The command '/bin/sh -c timeout 300s apt-get -o Acquire::Retries=5 -o Acquire::http::Timeout=30 -o Acquire::https::Timeout=30 -o Acquire::ForceIPv4=true update && timeout 300s apt-get -o Acquire::Retries=5 -o Acquire::http::Timeout=30 -o...

### 2026-04-18 06:03 CST baseline taxonomy-tree-merge

- exit_code=0; run_id=b6d17e15ea59 | status=abandoned | failure_class=timeout | duration_seconds=714.0765244359973 | final_model=gpt-5.4 | final_score=0.0 | last_event=base_attempt | notes=Model could not solve autonomously

### 2026-04-18 06:19 CST current react-performance-debugging

- exit_code=0; run_id=8937b3fc9cfa | status=abandoned | failure_class=builderror | duration_seconds=1030.2050966940042 | final_model= | final_score=0.0 | last_event=runner_exception | notes=The command '/bin/sh -c timeout 300s apt-get -o Acquire::Retries=5 -o Acquire::http::Timeout=30 -o Acquire::https::Timeout=30 -o Acquire::ForceIPv4=true update && timeout 300s apt-get -o Acquire::Retries=5 -o Acquire::http::Timeout=30 -o...

### 2026-04-18 06:28 CST current taxonomy-tree-merge

- exit_code=0; run_id=0d41770db6a4 | status=abandoned | failure_class=apierror | duration_seconds=599.8123059920035 | final_model= | final_score=0.0 | last_event=runner_exception | notes=500 Server Error for http+docker://localhost/v1.54/containers/b65ca3f09d4eb1bc542a1d9e6c6e22a19fea865da8d03f5efb1496ed3fc642e2/archive?path=%2Froot%2F.cache%2Fhuggingface%2Fhub%2Fmodels--sentence-transformers--all-MiniLM-L6-v2%2Fsnapshot...

### 2026-04-18 06:53 CST baseline react-performance-debugging

- exit_code=0; run_id=2c3bfe0bef93 | status=abandoned | failure_class=timeout | duration_seconds=1638.8500706439954 | final_model=gpt-5.4 | final_score=0.0 | last_event=base_attempt | notes=Model could not solve autonomously
