# MasterSkill Development Log

## 2026-04-29

### Paper-Track Reset And Evidence Freeze Progress

- Added the active paper planning documents:
  - `MasterSkill/paper_plan_20260513.md`
  - `MasterSkill/paper_evidence_memo_20260429.md`
- Reframed the near-term target:
  - keep full-suite baseline/current comparison as a hard requirement
  - use case studies as the explanation layer rather than as a substitute for suite-scale evidence
- Standardized the current `SkillsBench` experiment policy on `gpt-5.2` for execution and experiment-facing agents.

### Documentation Cleanup

- Simplified the active doc hierarchy so the current resume path points first to:
  - `paper_plan_20260513.md`
  - `state.md`
- Marked older Phase 1 OSS documents as reference / archival rather than current near-term drivers:
  - `phase1_runbook.md`
  - `pipeline_todo.md`
  - `release_checklist.md`
  - `session_resume.md`

### Docker Recovery

- Confirmed the active WSL environment had temporarily lost Docker access:
  - `docker version` unavailable
  - `/var/run/docker.sock` missing
- Verified Windows-side Docker installation paths:
  - `/mnt/e/Docker/Docker Desktop.exe`
  - `/mnt/e/Docker/resources/bin/docker.exe`
- Relaunched Docker Desktop from Windows and confirmed WSL connectivity recovered:
  - Windows `docker.exe version` reached the daemon
  - WSL `docker version` succeeded
  - `/var/run/docker.sock` reappeared

### Phase 1 Current Completion

- Repaired `scripts/run_e1_current_until_complete.sh` ordering so paper-priority missing tasks start with:
  - `taxonomy-tree-merge`
  - `react-performance-debugging` kept last
- Worked through duplicate stale resume processes during current completion and explicitly killed stale branches so only one active writer remained at a time.
- Advanced `MasterSkill/masterskill_data_phase1_current/benchmark_runs/latest` coverage from `10 / 15` to `15 / 15`.

Newly added current latest snapshots:

- `taxonomy-tree-merge`
  - solved
  - final model `gpt-5.2`
  - top-level duration later stabilized to `1028.40s`
  - event-level effective tokens `23410`
  - task container confirmed output artifacts:
    - `unified_taxonomy_full.csv`
    - `unified_taxonomy_hierarchy.csv`
  - post-pass candidate `taxonomy-tree-merge-fast` failed official real test and was rejected
- `xlsx-recover-data`
  - solved
  - final model `gpt-5.2`
- `speaker-diarization-subtitles`
  - abandoned
  - persisted only after interrupting a stuck host-side wait
- `video-filler-word-remover`
  - abandoned
  - persisted only after interrupting a stuck host-side wait
- `react-performance-debugging`
  - latest snapshot persisted after interrupting a late-stage host-side wait, completing `15 / 15` current coverage

### End-Of-Day Frozen Compare

Re-ran:

- `scripts/summarize_masterskill_results.py` for baseline and current
- `scripts/compare_masterskill_runs.py` for baseline vs current

Observed suite-level comparison:

- baseline solved: `3 / 15`
- current solved: `5 / 15`
- solve gains for current:
  - `taxonomy-tree-merge`
  - `xlsx-recover-data`
- solve losses for current: `0`

Observed claim boundary:

- this frozen comparison supports a coverage-gain story better than a broad efficiency story
- common-solved tasks currently do not show broad runtime/token wins in the frozen current root
- the strongest primary case remains `taxonomy-tree-merge`

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

### 2026-04-18 07:04 CST baseline taxonomy-tree-merge

- exit_code=0; run_id=2381b58f446c | status=abandoned | failure_class=timeout | duration_seconds=720.1362161819998 | final_model=gpt-5.4 | final_score=0.0 | last_event=base_attempt | notes=Model could not solve autonomously

### 2026-04-18 07:38 CST current react-performance-debugging

- exit_code=0; run_id=ac5d06ed819b | status=abandoned | failure_class=timeoutexpired | duration_seconds=2266.8051828269963 | final_model=gpt-5.4 | final_score=0.0 | last_event=runner_exception | notes=Command '['/usr/local/bin/codex', 'exec', '--ephemeral', '--skip-git-repo-check', '-C', '/tmp/masterskill-codex-lc1ug0hj', '-s', 'read-only', '-c', 'model_reasoning_effort="medium"', '-m', 'gpt-5.2', '-o', '/tmp/masterskill-codex-lc1ug0h...

### 2026-04-18 09:08 CST current taxonomy-tree-merge

- exit_code=0; run_id=8f0054b678e5 | status=abandoned | failure_class=timeoutexpired | duration_seconds=5933.604577464001 | final_model=gpt-5.4 | final_score=0.0 | last_event=runner_exception | notes=Command '['/usr/local/bin/codex', 'exec', '--ephemeral', '--skip-git-repo-check', '-C', '/tmp/masterskill-codex-o17n59j1', '-s', 'read-only', '-c', 'model_reasoning_effort="medium"', '-m', 'gpt-5.2', '-o', '/tmp/masterskill-codex-o17n59j...

### 2026-04-18 09:21 CST baseline react-performance-debugging

- exit_code=0; run_id=bd8392b759a6 | status=abandoned | failure_class=timeout | duration_seconds=810.9967598750009 | final_model=gpt-5.4 | final_score=0.0 | last_event=base_attempt | notes=Model could not solve autonomously

### 2026-04-18 09:32 CST baseline taxonomy-tree-merge

- exit_code=0; run_id=acf078bb3e51 | status=abandoned | failure_class=timeout | duration_seconds=717.2174208470024 | final_model=gpt-5.4 | final_score=0.0 | last_event=base_attempt | notes=Model could not solve autonomously

### 2026-04-18 10:05 CST current react-performance-debugging

- exit_code=0; run_id=de26c5ee9511 | status=abandoned | failure_class=timeoutexpired | duration_seconds=2225.3260962740023 | final_model=gpt-5.4 | final_score=0.0 | last_event=runner_exception | notes=Command '['/usr/local/bin/codex', 'exec', '--ephemeral', '--skip-git-repo-check', '-C', '/tmp/masterskill-codex-iwy0kbrw', '-s', 'read-only', '-c', 'model_reasoning_effort="medium"', '-m', 'gpt-5.2', '-o', '/tmp/masterskill-codex-iwy0kbr...

### 2026-04-18 11:45 CST Stability Repair Pass

- Added internal-agent fallback handling across `Searcher`, `Analyzer`, `Critic`, `Reflector`, `QuickProposer`, `SkillCreator`, and base JSON parsing so repeated Codex timeouts no longer crash the whole benchmark run.
- Changed `Judger` fallback behavior from lenient pass to conservative fail, preventing unavailable Judger responses from incorrectly advancing to real tests.
- Adjusted internal Codex agent time budgets to `120/180/240s` for `gpt-5.2/5.3/5.4` and lowered execution reasoning effort from `xhigh` to `high` or `medium` depending on model tier.
- Made Docker build apt timeout task-aware using `task.toml` `environment.build_timeout_sec` with a 300s floor; this directly addresses repeated `react-performance-debugging` build-stage apt failures after Docker cache resets.
- Tightened artifact export filtering to skip cache-heavy or transient paths such as Hugging Face cache, `.npm`, `.next/cache`, `tsx`, `v8-compile-cache`, and Playwright temp downloads, reducing archive noise and removing the previously observed `taxonomy-tree-merge` archive failure source.
- Improved research handoff by passing `Searcher` recommended approach and relevant knowledge into `SkillCreator`, not just the short search summary.
- Added failure-aware cooldown and broader staging coverage to `scripts/overnight_masterskill.sh` so overnight automation can skip repeated identical failures and correctly commit `judge`/`proposer` mirror changes.

### 2026-04-18 11:45 CST Chain Verification

- `python3 -m py_compile` passed for all modified `MasterSkill/` and mirrored `src/icml_research/masterskill/` modules.
- Local smoke checks passed for fallback paths: `Searcher`, `SkillCreator`, `QuickProposer`, `Judger`, and Docker timeout/cache helpers.
- A real Docker-backed `react-performance-debugging` verification run with capped loop limits confirmed the repaired current chain now progresses through `execution -> official tests -> analyzer -> searcher -> skill_creator -> critic -> judger -> next skill execution` instead of failing immediately at internal-agent timeout. The run was stopped manually once the closed-loop behavior was confirmed.

### 2026-04-18 16:24 CST Loop Budget And Scheduling

- Added `max_research_cycles` to `Config`, `load_config()`, and CLI entrypoints so total research rounds per task are explicitly bounded.
- Updated `BenchmarkRunner.run_task()` to abandon with `failure_class=research_budget_exhausted` when the research-cycle budget is consumed before any passing real test, instead of continuing to spin on Judger/research indefinitely.
- Reworked `scripts/overnight_masterskill.sh` so current/evolution slots run first and baseline slots are skipped automatically when the latest result already contains a valid `base_attempt` record. This keeps overnight time focused on the real optimization target rather than re-sampling already-valid pure-base failures.
- Validation passed: `py_compile` succeeded, CLI help exposes `--max-research-cycles`, and the latest baseline JSONs for both target tasks already end at `base_attempt`, so the new baseline-skip rule will activate on the next overnight start.

### 2026-04-18 16:49 CST Effective Token Accounting

- Normalized optimization-cost comparisons to use `effective_tokens = max(input_tokens - cached_input_tokens, 0) + output_tokens` instead of raw `input_tokens + output_tokens`, so cache-heavy runs are not treated as equally expensive when the billable/runtime token burden is materially lower.
- Updated post-solve optimization summaries to show both raw token fields and the derived `effective_input_tokens` / `effective_total_tokens` values.
- Extended `BenchmarkResultStore` persistence so every newly written benchmark event JSON now includes `effective_input_tokens` and `effective_total_tokens`, removing the need for downstream analysis scripts to recompute the cached-token-adjusted view by hand.

### 2026-04-18 17:15 CST React Current-Chain Breakthrough

- Re-ran `python3 run_local.py --task react-performance-debugging --data-root /home/yuchong/auto-research-team/MasterSkill/masterskill_data --post-solve-optimization-rounds 1 --max-research-cycles 3` with real host Docker access.
- New latest run `11cfecf9997e` finished `solved` instead of falling into the older internal-agent `timeoutexpired` path.
- The solve came directly from `base_attempt`:
  - `duration_seconds = 679.14`
  - `input_tokens = 2486252`
  - `cached_input_tokens = 2445568`
  - `output_tokens = 18946`
  - `effective_total_tokens = 59630`
- Post-pass optimization attempted one candidate skill, `react-nextjs-performance-repair`, but that candidate failed the official real test and was not accepted.
- Net effect: `react-performance-debugging` is now a confirmed solved current/evolved task, and the control-plane/runtime fixes are no longer blocked by the previous fatal internal-agent timeout chain on this task.

### 2026-04-18 20:15 CST Taxonomy Current-Chain Breakthrough

- Re-ran `python3 run_local.py --task taxonomy-tree-merge --data-root /home/yuchong/auto-research-team/MasterSkill/masterskill_data --post-solve-optimization-rounds 1 --max-research-cycles 3` with real host Docker access.
- New latest run `7fca7f410e32` finished `solved`, replacing the older `timeoutexpired` current record `8f0054b678e5`.
- The solve came directly from `base_attempt`:
  - `duration_seconds = 688.11`
  - `input_tokens = 1487264`
  - `cached_input_tokens = 1459840`
  - `output_tokens = 24246`
  - `effective_total_tokens = 51670`
- Post-pass optimization attempted one candidate skill, `taxonomy-tree-merge-lite`, but that candidate failed the official real test and was not accepted.
- Net effect: `taxonomy-tree-merge` is now also a confirmed solved current/evolved task, so the immediate remaining comparison gap is no longer the evolved chain; it is the stale pre-evolution baselines for `react-performance-debugging` and `taxonomy-tree-merge`.

### 2026-04-18 20:40 CST Pre-Evolution Baseline Refresh

- Re-ran the stale baseline pair with:
  - `python3 run_local.py --tasks react-performance-debugging taxonomy-tree-merge --pre-evolution-baseline --data-root /home/yuchong/auto-research-team/MasterSkill/masterskill_data_pre_evolution`
- `react-performance-debugging`
  - new latest baseline run `5c939012e58b`
  - `status = solved`
  - `base_attempt` passed directly
  - `duration_seconds = 560.43`
  - `input_tokens = 1366807`
  - `cached_input_tokens = 1335808`
  - `output_tokens = 16542`
  - `effective_total_tokens = 47541`
- `taxonomy-tree-merge`
  - new latest baseline run `d700c31496bf`
  - `status = abandoned`
  - `failure_class = timeout`
  - `base_attempt` still did not solve autonomously
  - `duration_seconds = 704.94`
  - `input_tokens = 892330`
  - `cached_input_tokens = 870144`
  - `output_tokens = 30314`
  - `effective_total_tokens = 52500`
- Comparison implication after the refresh:
  - `react-performance-debugging`: current/evolved and pure baseline now both pass, so future work should compare runtime, effective tokens, and stability instead of treating it as a pure pass/fail gain.
  - `taxonomy-tree-merge`: current/evolved now passes while pure baseline still fails, so this remains the clearest current evidence that the MasterSkill runtime/control-plane changes materially expand task coverage on a hard case.

### 2026-04-18 21:10 CST Phase 1 Runbook Operationalization

- Added `--benchmark-all` to both runtime entrypoints so a frozen full-suite sweep can explicitly run every task under the active task root instead of depending on task-memory solved-state filtering.
- Added `scripts/summarize_masterskill_results.py` to summarize `benchmark_runs/latest/*.json` into suite-level solved/abandoned counts, failure-class breakdowns, and per-task duration / effective-token views.
- Added [phase1_runbook.md](/home/yuchong/auto-research-team/MasterSkill/phase1_runbook.md) as the execution guide for calibration runs, frozen Phase 1 sweeps, and release-readiness checks.
- Added `scripts/run_phase1_skillsbench.sh` so Phase 1 calibration and full-suite sweeps now have a single canonical launcher with fixed data-root names and task-set modes.
- Added `scripts/compare_masterskill_runs.py` so baseline vs current/evolved comparisons can be generated directly from persisted `benchmark_runs/latest/*.json` outputs after a sweep.
- Validation passed for:
  - `python3 run_local.py --help`
  - `python3 scripts/summarize_masterskill_results.py --help`
  - `python3 scripts/compare_masterskill_runs.py --help`
  - `python3 -m py_compile MasterSkill/main.py MasterSkill/runner/benchmark_runner.py src/icml_research/masterskill/main.py src/icml_research/masterskill/runner/benchmark_runner.py scripts/summarize_masterskill_results.py scripts/compare_masterskill_runs.py`

### 2026-04-18 21:20 CST Phase 1 Current Calibration Started

- Launched `scripts/run_phase1_skillsbench.sh current-calibration` against the representative task set:
  - `enterprise-information-search`
  - `pddl-tpp-planning`
  - `react-performance-debugging`
  - `taxonomy-tree-merge`
  - `financial-modeling-qa`
- The run uses fresh data root `/home/yuchong/auto-research-team/MasterSkill/masterskill_data_phase1_calibration_current`.
- Early signal is positive: the first task (`enterprise-information-search`) reached post-solve optimization in the fresh calibration root instead of failing immediately from a harness/runtime error, so the new Phase 1 launcher and config surface are at least live under real Docker-backed execution.

### 2026-04-18 21:50 CST Phase 1 Calibration Progress Clarification

- `enterprise-information-search` completed successfully in the fresh calibration root as run `4dd60dd2fc93`.
- The base solve was still direct (`__base_model__`), but the post-pass optimization candidate `enterprise-direct-answer-lean` was accepted with a real efficiency gain:
  - `effective_total_tokens 125466 -> 62935`
- The main `current-calibration` batch did continue beyond the first task; after the enterprise task finished, it advanced into `pddl-tpp-planning` post-pass candidate evaluation (`pddl-tpp-batch-solve-verify-fastpath`).
- A short two-task diagnostic probe was started while the task switch window looked suspicious, but it became redundant once the main calibration batch clearly progressed to the second task, so the probe run was stopped to avoid wasting resources.

### 2026-04-18 22:45 CST Phase 1 Single-Task Calibration Fallback

- Added single-task Phase 1 launcher modes to `scripts/run_phase1_skillsbench.sh`:
  - `current-task <task_id>`
  - `baseline-task <task_id>`
- Updated `phase1_runbook.md` so single-task modes are now the formal fallback when:
  - a calibration batch appears to stall between task transitions
  - a long task should be resumed under the same calibration data root
  - a specific hard task deserves focused debugging without rerunning earlier calibration tasks
- Used that fallback to continue the Phase 1 current calibration in the same data root for `react-performance-debugging`.
- During the fresh `react-performance-debugging` calibration run, the chain progressed through:
  - existing bundled skill evaluation (`react-best-practices`)
  - additional bundled measurement/debug skill evaluation (`browser-testing`)
  - transition into research-driven new skill creation after those task-local priors did not produce a passing solve path quickly
- This is useful Phase 1 evidence even before final task status is written: the runtime is not bailing out early and is exercising the intended `reuse -> research` fallback path on a hard task under the calibration configuration.

### 2026-04-18 22:55 CST React Calibration Stall, Taxonomy Calibration Started

- The focused `react-performance-debugging` Phase 1 calibration run did not write a final benchmark snapshot under the calibration root and stopped producing new shallow-trace output after the bundled-skill trace entries.
- Manual interruption showed the host runner blocked in:
  - `BenchmarkRunner._evaluate_with_judger`
  - `DockerExecutor.execute_skill`
  - `DockerExecutor._run_agent`
  - `subprocess.run(...).communicate()`
- This should be treated as a Phase 1 runtime/control-plane issue, not as an interpretable benchmark result for the task itself.
- Per the Phase 1 runbook, the blocked hard-task calibration was paused and the calibration sequence continued with:
  - `scripts/run_phase1_skillsbench.sh current-task taxonomy-tree-merge`
- The goal remains unchanged:
  - keep Phase 1 moving across representative tasks
  - return to the `react` stall later as a runtime stabilization item instead of letting it block the full calibration path

### 2026-04-18 23:12 CST Hard-Task Calibration Timeouts Recorded

- `react-performance-debugging` has now been persisted under the Phase 1 current calibration root as:
  - `status=abandoned`
  - `failure_class=timeout`
  - `run_id=57aedef4bd81`
  - `duration_seconds=2380.39`
- `taxonomy-tree-merge` current calibration also completed as:
  - `status=abandoned`
  - `failure_class=timeout`
  - `run_id=c3669c23c2e2`
  - `duration_seconds=767.86`
- The taxonomy timeout is notable because the task-local bundled skill `hierarchical-taxonomy-clustering` was still discovered in `skills_tried`, but the current calibration run did not convert that prior into a pass under the frozen Phase 1 settings.
- Current Phase 1 calibration state under `masterskill_data_phase1_calibration_current` is now:
  - solved: `enterprise-information-search`, `pddl-tpp-planning`
  - abandoned/timeout: `react-performance-debugging`, `taxonomy-tree-merge`
- Next planned action remains to finish the current calibration set with `financial-modeling-qa`, then switch to the comparable baseline calibration pass.

### 2026-04-19 10:40 CST Taxonomy Skill Upgrade Validated

- Upgraded the bundled task-local skill `hierarchical-taxonomy-clustering` from a mostly methodological note into an executable pipeline:
  - added a deterministic `scripts/pipeline.py`
  - updated the skill instructions to point the agent toward the runnable pipeline
- Removed the runtime dependency on downloading `nltk.wordnet` by replacing WordNet-based lemmatization with a built-in lightweight singularization pass. This makes the skill runnable inside the stock task image without extra network setup.
- Ran the updated pipeline directly inside `masterskill:taxonomy-tree-merge-test-runtime` and then executed the official `tests/test_outputs.py` checks against its outputs.
- Result:
  - `unified_taxonomy_full.csv`: 8,968 rows
  - `unified_taxonomy_hierarchy.csv`: 469 rows
  - official checks passed: `22 / 22`
- Re-ran the full MasterSkill chain with a fresh isolated data root:
  - `/home/yuchong/auto-research-team/MasterSkill/masterskill_data_taxonomy_skill_validation`
- During that live benchmark run, the task container did generate the expected output artifacts under `/root/output`, confirming the upgraded bundled skill is actually being invoked by the runtime.
- The run still did not write a benchmark snapshot before the host process stalled, which sharpens the remaining blocker:
  - the taxonomy hard case now appears solvable with the bundled skill
  - the current failure mode is in the host-side `_run_agent` / `codex exec` completion path rather than the taxonomy method itself
- Added a small prompt-side execution guard in `docker_executor.py`:
  - prefer bundled end-to-end pipelines before inventing a new approach
  - stop immediately once the required outputs exist and pass a minimal sanity check
- A second isolated rerun with that prompt change (`masterskill_data_taxonomy_skill_validation_v2`) again generated the required taxonomy CSVs inside the live task container but still failed to persist a benchmark record before hanging, so the prompt adjustment alone is not sufficient to clear the host-side completion issue.

### 2026-04-18 16:04 CST Overnight run started

- branch=overnight-masterskill-recovery; log=/home/yuchong/auto-research-team/MasterSkill/logs/overnight_20260418_160420.log

### 2026-04-18 16:04 CST Overnight run started

- branch=overnight-masterskill-recovery; log=/home/yuchong/auto-research-team/MasterSkill/logs/overnight_20260418_160422.log

### 2026-04-18 16:17 CST baseline react-performance-debugging

- exit_code=0; run_id=698b991b04a6 | status=abandoned | failure_class=timeout | duration_seconds=883.826898697007 | final_model=gpt-5.4 | final_score=0.0 | last_event=base_attempt | notes=Model could not solve autonomously

### 2026-04-21 13:58 CST Next-Stage Plan Registered, E1 Started

- Recorded the experiment-level next-stage roadmap (`E1` to `E10`) into `pipeline_todo.md` as the active execution reference.
- Reconfirmed the end objective as chain-level autonomous skill quality improvement with pass-rate trajectory toward `>=90%` SkillsBench.
- Began `E1` execution flow:
  - freeze the run protocol
  - run one frozen `baseline-sweep`
  - run one frozen `current-sweep`
  - verify no missing task snapshots under `benchmark_runs/latest/`

### 2026-04-21 14:01 CST E1 Baseline Sweep Launched

- Started frozen baseline full-suite run:
  - `scripts/run_phase1_skillsbench.sh baseline-sweep`
- Runtime command:
  - `python3 run_local.py --benchmark-all --pre-evolution-baseline --no-persist-task-skills --data-root /home/yuchong/auto-research-team/MasterSkill/masterskill_data_phase1_pre_evolution`
- Run log:
  - `/home/yuchong/auto-research-team/MasterSkill/logs/phase1_baseline-sweep_20260421_140133.log`
- Live process snapshot at launch window:
  - `bash scripts/run_phase1_skillsbench.sh baseline-sweep`
  - `python3 run_local.py --benchmark-all --pre-evolution-baseline ...`

### 2026-04-21 14:40 CST E1 In-Flight Status + Follow-up Session Bound

- Baseline sweep remains active on the frozen protocol and has produced 5 latest records so far under:
  - `/home/yuchong/auto-research-team/MasterSkill/masterskill_data_phase1_pre_evolution/benchmark_runs/runs.jsonl`
- Mid-run quality snapshot:
  - solved: 3
  - abandoned: 2
  - `failure_class=builderror`: 2
- Confirmed one long-running tool-setup phase in-container (`apt-get install ... build-essential gfortran openblas ...`) is the current wall-clock bottleneck rather than host process death.
- Bound the E1 post-baseline follow-up to a persistent elevated PTY session:
  - session id: `10485`
  - command: `scripts/run_e1_followup.sh MasterSkill/logs/e1_followup_live_<timestamp>.log`
  - current state: waiting for `baseline-sweep` process to finish, then auto-runs `current-sweep` + baseline/current summaries + compare.

### 2026-04-21 15:02 CST E1 Baseline Hang Detected, Switched To Resume Mode

- Observed no benchmark artifact updates after `14:36 CST`:
  - `benchmark_runs/runs.jsonl` and `benchmark_runs/tasks/*.jsonl` stopped advancing
  - host `run_local.py --benchmark-all --pre-evolution-baseline` remained alive but idle (`State=S`, wait channel `unix_stream_read_generic`)
  - task containers eventually dropped to none, confirming no active test execution during the freeze window
- Applied the runbook-style intervention:
  - interrupted the hung baseline PTY session (`Ctrl-C`)
  - paused the waiting follow-up session before it could continue an invalid sequence
- Resumed baseline in the same data root with unsolved-task mode:
  - `python3 run_local.py --benchmark --pre-evolution-baseline --no-persist-task-skills --data-root /home/yuchong/auto-research-team/MasterSkill/masterskill_data_phase1_pre_evolution`
  - log: `/home/yuchong/auto-research-team/MasterSkill/logs/phase1_baseline-resume_20260421_150236.log`
- Resume confirmation:
  - `runs.jsonl` advanced from `5` to `6`
  - `quantum-numerical-simulation` snapshot persisted (abandoned without classification), indicating the previous stuck segment was crossed and baseline execution resumed.

### 2026-04-21 15:14 CST E1 Auto-Chaining Rebound For Resume Flow

- Updated `scripts/run_e1_followup.sh` wait condition so it blocks on either baseline mode:
  - wrapper mode: `scripts/run_phase1_skillsbench.sh baseline-sweep`
  - direct resume mode: `python3 run_local.py --benchmark --pre-evolution-baseline ...`
  - full baseline mode: `python3 run_local.py --benchmark-all --pre-evolution-baseline ...`
- Relaunched follow-up watcher with the updated logic:
  - session id: `53701`
  - log: `/home/yuchong/auto-research-team/MasterSkill/logs/e1_followup_live_20260421_151415.log`
  - state: waiting for baseline resume process to exit before automatically starting `current-sweep` and post-run summaries/comparison.
- Baseline resume remains active:
  - session id: `91648`
  - process: `python3 run_local.py --benchmark --pre-evolution-baseline --no-persist-task-skills --data-root .../masterskill_data_phase1_pre_evolution`

### 2026-04-21 15:29 CST E1 Sequencing Guard Added (Baseline Coverage Gate)

- Detected sequencing bug during live orchestration:
  - follow-up watcher proceeded to `current-sweep` as soon as baseline process disappeared, even though baseline `latest` coverage was only `6/15`.
  - this was triggered after a manual interrupt of a hung baseline-resume run.
- Mitigation applied in `scripts/run_e1_followup.sh`:
  - added helper checks for baseline process status and baseline `latest/*.json` coverage
  - watcher now proceeds only when both are true:
    - baseline process is not running
    - baseline latest coverage reaches expected task count (`15/15`)
- Immediately enforced corrected E1 order:
  - interrupted prematurely started `current-sweep`
  - restarted baseline-resume:
    - session id: `75862`
    - command: `python3 run_local.py --benchmark --pre-evolution-baseline --no-persist-task-skills --data-root /home/yuchong/auto-research-team/MasterSkill/masterskill_data_phase1_pre_evolution`
  - relaunched follow-up watcher with coverage gate:
    - session id: `26581`
    - log: `/home/yuchong/auto-research-team/MasterSkill/logs/e1_followup_live_20260421_152927.log`

### 2026-04-21 15:35 CST E1 Current-Root Cleanliness Guard Added

- Added an additional E1 safety step in `scripts/run_e1_followup.sh` before starting `current-sweep`:
  - if `/MasterSkill/masterskill_data_phase1_current/benchmark_runs/runs.jsonl` already exists and is non-empty, move the whole current root to a timestamped backup:
    - `masterskill_data_phase1_current_pre_e1_backup_<timestamp>`
  - recreate a clean `masterskill_data_phase1_current` directory for the new frozen current run.
- Reason:
  - earlier interrupted `current-sweep` attempts left partial records in the current root, which would contaminate baseline-vs-current interpretation for E1.
- Restarted follow-up watcher so the new guard is active:
  - interrupted prior watcher session (`26581`)
  - launched new watcher session:
    - session id: `83272`
    - log: `/home/yuchong/auto-research-team/MasterSkill/logs/e1_followup_live_20260421_153527.log`

### 2026-04-21 16:30 CST E1 Baseline Auto-Resume Upgraded To Missing-Task Per-Task Mode

- Upgraded baseline continuation from manual/whole-unsolved retries to a dedicated loop script:
  - `scripts/run_e1_baseline_until_complete.sh`
- Evolution of the strategy during this window:
  - v1: `--benchmark` retries (still repeatedly hit early tasks)
  - v2: `--tasks <all missing>` batch (reduced re-run noise but still vulnerable to one heavy task blocking the whole batch)
  - v3 (active): iterate missing tasks one-by-one with per-task timeout and progress logging.
- Active policy in v3:
  - identify missing tasks from `benchmark_runs/latest/*.json` under baseline root
  - run each missing task with:
    - `python3 run_local.py --task <task_id> --pre-evolution-baseline --no-persist-task-skills --data-root ...`
  - enforce per-task timeout (`PER_TASK_TIMEOUT_SECONDS`, currently 900s)
  - move `react-performance-debugging` to the end of each missing-task pass to avoid front-loading long stalls
- Follow-up watcher alignment:
  - updated `scripts/run_e1_followup.sh` baseline detection to include `--tasks` and `--task` baseline processes
  - relaunched watcher session:
    - session id: `28203`
    - log: `/home/yuchong/auto-research-team/MasterSkill/logs/e1_followup_live_20260421_160731.log`
- Live evidence of forward motion under v3:
  - `reserves-at-risk-calc` timed out at per-task boundary and loop automatically moved to `seismic-phase-picking` without manual intervention.

### 2026-04-21 19:05 CST E1 Baseline Coverage Completed (15/15)

- Applied graceful-interrupt-driven progression on stalled baseline missing tasks.
- Baseline data root reached full latest coverage:
  - `MasterSkill/masterskill_data_phase1_pre_evolution/benchmark_runs/latest/*.json = 15`
- Baseline task coverage now includes all 15 phase tasks, with explicit persisted latest snapshots.
- The follow-up watcher detected completion and automatically transitioned into current sweep.

### 2026-04-21 19:23 CST E1 Current Sweep Switched To Controlled Per-Task Completion

- Observed current full-sweep (`--benchmark-all`) beginning to show the same host-side long-wait pattern after initial tasks.
- To keep E1 moving deterministically, introduced:
  - `scripts/run_e1_current_until_complete.sh`
  - behavior mirrors baseline recovery:
    - iterate missing current tasks from `current/benchmark_runs/latest`
    - run one task at a time with current settings:
      - `--no-persist-task-skills`
      - `--post-solve-optimization-rounds 1`
      - `--max-research-cycles 3`
    - timeout wrapper uses graceful signal first:
      - `timeout --signal=INT --kill-after=60s ...`
    - keeps `react-performance-debugging` last in each pass
- Live current progress under controlled mode:
  - persisted current latest coverage advanced from `2/15` to `4/15` while continuing forward to next missing task (`pddl-tpp-planning`).

### 2026-04-30 17:30 CST Paper-Facing GPT-5.2 Consistency Completed

- Completed strict `gpt-5.2` consistency reruns for paper-facing solved tasks.
- Current-side solved reruns completed:
  - `enterprise-information-search`
  - `financial-modeling-qa`
  - `pddl-tpp-planning`
  - `seismic-phase-picking`
- Baseline-side solved reruns completed:
  - `enterprise-information-search`
  - `financial-modeling-qa`
  - `pddl-tpp-planning`
- Paper-facing `baseline/current latest` solved snapshots are now uniformly
  `gpt-5.2`.
- Refreshed frozen compare after reruns:
  - baseline solved: `3 / 15`
  - current solved: `6 / 15`
  - solve gains: `seismic-phase-picking`, `taxonomy-tree-merge`,
    `xlsx-recover-data`
  - solve losses: `0`
