# Session Resume

Updated: 2026-04-17

## Supplemental Note From Current Recovery Pass

- repo root now has `run_local.py`, so `python3 run_local.py ...` works from `/home/yuchong/auto-research-team`
- the old Docker credential-store blocker (`docker-credential-desktop.exe not installed or not available in PATH`) is no longer the active failure mode when the run is executed with real host Docker access
- `taxonomy-tree-merge` cold builds after the Docker reset were being killed by the executor's rewritten build-stage `apt-get` timeout (`180s`)
- this session raised the build-stage `apt-get` timeout to `300s` in both:
  - `MasterSkill/runner/docker_executor.py`
  - `src/icml_research/masterskill/runner/docker_executor.py`
- validation rerun confirmed the cold build now moves past the original `apt-get` timeout and reaches later package-install steps (observed at `pip install sentence-transformers==2.5.1`)
- no new completed taxonomy baseline was kept as `latest` from that validation pass because the long rerun was interrupted after the environment check; `latest/taxonomy-tree-merge.json` was restored to the last fully completed `builderror` record

## What Is Already Done

- Added a pure pre-evolution baseline mode:
  - `--pre-evolution-baseline`
  - base attempt does **not** see bundled task-local skills
  - run stops immediately after base attempt
  - default baseline data root is `masterskill_data_pre_evolution/`
- Synced the baseline-mode changes into both:
  - `MasterSkill/`
  - `../src/icml_research/masterskill/`
- Fixed two comparison-chain issues:
  - `base_attempt` was previously exposed to bundled task-local skills
  - post-pass comparison now allows large real runtime/token wins to outweigh moderate `skill_md_size` regressions
- Fixed two execution-chain issues discovered during baseline measurement:
  - tasks with `tests/test.sh` but no `tests/test_outputs.py` should not be labeled `missing_test_file`
  - Docker build transport failures such as `IncompleteRead` / `ProtocolError` are now retryable
- Added runner-side exception classification so a single task failure no longer crashes the whole `--tasks` batch.

## Current Verified Results

### Evolved / current chain

- `enterprise-information-search`
  - latest evolved result: solved
  - post-pass passing skills:
    - `enterprise-direct-evidence-answer`
    - `enterprise-direct-answer-minimal`
  - accepted gain:
    - `duration 406.82s -> 343.18s`
    - `tokens 1394607 -> 1033712`

- `pddl-tpp-planning`
  - latest evolved result: solved
  - accepted post-pass skill:
    - `pddl-tpp-batch-fastpath`
  - accepted gain:
    - `duration 148.58s -> 131.10s`

### Pre-evolution baseline

Stored under:

- `/home/yuchong/auto-research-team/MasterSkill/masterskill_data_pre_evolution/`

Already measured:

- `enterprise-information-search`
  - pure base solved
  - `duration_seconds ~= 327.11`
  - `input_tokens = 1122933`
  - `output_tokens = 13062`
  - file:
    - `/home/yuchong/auto-research-team/MasterSkill/masterskill_data_pre_evolution/benchmark_runs/latest/enterprise-information-search.json`

- `pddl-tpp-planning`
  - pure base solved
  - `duration_seconds ~= 198.97`
  - `input_tokens = 294178`
  - `output_tokens = 7006`
  - file:
    - `/home/yuchong/auto-research-team/MasterSkill/masterskill_data_pre_evolution/benchmark_runs/latest/pddl-tpp-planning.json`

Stale pre-evolution records that must be rerun after Docker recovers:

- `react-performance-debugging`
  - current baseline record is stale
  - reason: it was recorded before the `test.sh`-only fix
  - current stale file:
    - `/home/yuchong/auto-research-team/MasterSkill/masterskill_data_pre_evolution/benchmark_runs/latest/react-performance-debugging.json`

- `taxonomy-tree-merge`
  - current baseline record is stale
  - reason: the batch run hit a Docker transport/build failure before the new retry handling
  - current stale file:
    - `/home/yuchong/auto-research-team/MasterSkill/masterskill_data_pre_evolution/benchmark_runs/latest/taxonomy-tree-merge.json`

## Current Blocker

The remaining baseline reruns are blocked by Docker daemon instability, not by repo logic.

Observed symptoms:

- Docker API `/version` returned `500`
- WSL-side `docker` sometimes returned `Input/output error`
- one baseline batch was interrupted by Docker build transport failure

## First Steps After Restart

1. Restore Docker.

Recommended order:

- first try restarting Docker Desktop without shutting down WSL
- verify with:

```bash
docker version
docker ps
```

If that still fails, only then use the heavier recovery path outside this session:

- quit Docker Desktop
- `wsl --shutdown`
- relaunch Docker Desktop

2. Rerun the two stale baseline tasks:

```bash
python3 run_local.py \
  --tasks react-performance-debugging taxonomy-tree-merge \
  --pre-evolution-baseline \
  --data-root /home/yuchong/auto-research-team/MasterSkill/masterskill_data_pre_evolution
```

3. Read the completed baseline files:

```bash
find masterskill_data_pre_evolution/benchmark_runs/latest -maxdepth 1 -name '*.json' | sort
```

4. Then compare pre-evolution vs evolved results for:

- `enterprise-information-search`
- `pddl-tpp-planning`
- `react-performance-debugging` once baseline and evolved runs exist
- `taxonomy-tree-merge` once baseline and evolved runs exist

## Comparison Rule Going Forward

- For tasks where pure base already passes:
  - compare runtime, tokens, and stability
  - do **not** use pass-rate alone as the main metric

- For tasks where pure base fails:
  - compare pass/fail first
  - then compare runtime/tokens for passing variants

## Relevant Files To Reopen First

- `/home/yuchong/auto-research-team/MasterSkill/session_resume.md`
- `/home/yuchong/auto-research-team/MasterSkill/state.md`
- `/home/yuchong/auto-research-team/MasterSkill/development_log.md`
- `/home/yuchong/auto-research-team/MasterSkill/masterskill_data_pre_evolution/benchmark_runs/latest/enterprise-information-search.json`
- `/home/yuchong/auto-research-team/MasterSkill/masterskill_data_pre_evolution/benchmark_runs/latest/pddl-tpp-planning.json`
- `/home/yuchong/auto-research-team/MasterSkill/masterskill_data/benchmark_runs/latest/enterprise-information-search.json`
- `/home/yuchong/auto-research-team/MasterSkill/masterskill_data/benchmark_runs/latest/pddl-tpp-planning.json`

- [2026-04-17 23:46 CST] Overnight run started on branch `overnight-masterskill-recovery`; log file: `/home/yuchong/auto-research-team/MasterSkill/logs/overnight_20260417_234600.log`

- [2026-04-17 23:46 CST] Overnight run started on branch `overnight-masterskill-recovery`; log file: `/home/yuchong/auto-research-team/MasterSkill/logs/overnight_20260417_234632.log`

- [2026-04-18 00:04 CST] baseline react-performance-debugging -> exit_code=0; run_id=d7c1a7b52e6a | status=abandoned | failure_class=builderror | duration_seconds=1147.1781633839992 | final_model= | final_score=0.0 | last_event=runner_exception | notes=The command '/bin/sh -c timeout 300s apt-get -o Acquire::Retries=5 -o Acquire::http::Timeout=30 -o Acquire::https::Timeout=30 -o Acquire::ForceIPv4=true update && timeout 300s apt-get -o Acquire::Retries=5 -o Acquire::http::Timeout=30 -o...

- [2026-04-18 01:27 CST] baseline taxonomy-tree-merge -> exit_code=0; run_id=f754362d87e6 | status=abandoned | failure_class=timeout | duration_seconds=5440.698454790001 | final_model=gpt-5.4 | final_score=0.0 | last_event=base_attempt | notes=Model could not solve autonomously

- [2026-04-18 01:44 CST] current react-performance-debugging -> exit_code=0; run_id=581cb3df0d17 | status=abandoned | failure_class=builderror | duration_seconds=1112.9304100709996 | final_model= | final_score=0.0 | last_event=runner_exception | notes=The command '/bin/sh -c timeout 300s apt-get -o Acquire::Retries=5 -o Acquire::http::Timeout=30 -o Acquire::https::Timeout=30 -o Acquire::ForceIPv4=true update && timeout 300s apt-get -o Acquire::Retries=5 -o Acquire::http::Timeout=30 -o...

- [2026-04-18 02:45 CST] current taxonomy-tree-merge -> exit_code=0; run_id=7fa774e8b2a5 | status=abandoned | failure_class=timeoutexpired | duration_seconds=4043.5363252589996 | final_model=gpt-5.4 | final_score=0.0 | last_event=runner_exception | notes=Command '['/usr/local/bin/codex', 'exec', '--ephemeral', '--skip-git-repo-check', '-C', '/tmp/masterskill-codex-b8vz59bm', '-s', 'read-only', '-c', 'model_reasoning_effort="medium"', '-m', 'gpt-5.2', '-o', '/tmp/masterskill-codex-b8vz59b...

- [2026-04-18 03:01 CST] baseline react-performance-debugging -> exit_code=0; run_id=d1c9e54d35ff | status=abandoned | failure_class=builderror | duration_seconds=1036.4254961099978 | final_model= | final_score=0.0 | last_event=runner_exception | notes=The command '/bin/sh -c timeout 300s apt-get -o Acquire::Retries=5 -o Acquire::http::Timeout=30 -o Acquire::https::Timeout=30 -o Acquire::ForceIPv4=true update && timeout 300s apt-get -o Acquire::Retries=5 -o Acquire::http::Timeout=30 -o...

- [2026-04-18 03:12 CST] baseline taxonomy-tree-merge -> exit_code=0; run_id=15afc7399aef | status=abandoned | failure_class=timeout | duration_seconds=712.4763632379982 | final_model=gpt-5.4 | final_score=0.0 | last_event=base_attempt | notes=Model could not solve autonomously

- [2026-04-18 03:28 CST] current react-performance-debugging -> exit_code=0; run_id=32ef05a0e68b | status=abandoned | failure_class=builderror | duration_seconds=1039.8171880549999 | final_model= | final_score=0.0 | last_event=runner_exception | notes=The command '/bin/sh -c timeout 300s apt-get -o Acquire::Retries=5 -o Acquire::http::Timeout=30 -o Acquire::https::Timeout=30 -o Acquire::ForceIPv4=true update && timeout 300s apt-get -o Acquire::Retries=5 -o Acquire::http::Timeout=30 -o...

- [2026-04-18 05:36 CST] current taxonomy-tree-merge -> exit_code=0; run_id=0d35a0516807 | status=abandoned | failure_class=timeoutexpired | duration_seconds=8480.788630378 | final_model=gpt-5.4 | final_score=0.0 | last_event=runner_exception | notes=Command '['/usr/local/bin/codex', 'exec', '--ephemeral', '--skip-git-repo-check', '-C', '/tmp/masterskill-codex-04c5y3km', '-s', 'read-only', '-c', 'model_reasoning_effort="medium"', '-m', 'gpt-5.2', '-o', '/tmp/masterskill-codex-04c5y3k...

- [2026-04-18 05:52 CST] baseline react-performance-debugging -> exit_code=0; run_id=90d0a1315afa | status=abandoned | failure_class=builderror | duration_seconds=1036.691220189001 | final_model= | final_score=0.0 | last_event=runner_exception | notes=The command '/bin/sh -c timeout 300s apt-get -o Acquire::Retries=5 -o Acquire::http::Timeout=30 -o Acquire::https::Timeout=30 -o Acquire::ForceIPv4=true update && timeout 300s apt-get -o Acquire::Retries=5 -o Acquire::http::Timeout=30 -o...

- [2026-04-18 06:03 CST] baseline taxonomy-tree-merge -> exit_code=0; run_id=b6d17e15ea59 | status=abandoned | failure_class=timeout | duration_seconds=714.0765244359973 | final_model=gpt-5.4 | final_score=0.0 | last_event=base_attempt | notes=Model could not solve autonomously

- [2026-04-18 06:19 CST] current react-performance-debugging -> exit_code=0; run_id=8937b3fc9cfa | status=abandoned | failure_class=builderror | duration_seconds=1030.2050966940042 | final_model= | final_score=0.0 | last_event=runner_exception | notes=The command '/bin/sh -c timeout 300s apt-get -o Acquire::Retries=5 -o Acquire::http::Timeout=30 -o Acquire::https::Timeout=30 -o Acquire::ForceIPv4=true update && timeout 300s apt-get -o Acquire::Retries=5 -o Acquire::http::Timeout=30 -o...

- [2026-04-18 06:28 CST] current taxonomy-tree-merge -> exit_code=0; run_id=0d41770db6a4 | status=abandoned | failure_class=apierror | duration_seconds=599.8123059920035 | final_model= | final_score=0.0 | last_event=runner_exception | notes=500 Server Error for http+docker://localhost/v1.54/containers/b65ca3f09d4eb1bc542a1d9e6c6e22a19fea865da8d03f5efb1496ed3fc642e2/archive?path=%2Froot%2F.cache%2Fhuggingface%2Fhub%2Fmodels--sentence-transformers--all-MiniLM-L6-v2%2Fsnapshot...

- [2026-04-18 06:53 CST] baseline react-performance-debugging -> exit_code=0; run_id=2c3bfe0bef93 | status=abandoned | failure_class=timeout | duration_seconds=1638.8500706439954 | final_model=gpt-5.4 | final_score=0.0 | last_event=base_attempt | notes=Model could not solve autonomously

- [2026-04-18 07:04 CST] baseline taxonomy-tree-merge -> exit_code=0; run_id=2381b58f446c | status=abandoned | failure_class=timeout | duration_seconds=720.1362161819998 | final_model=gpt-5.4 | final_score=0.0 | last_event=base_attempt | notes=Model could not solve autonomously

- [2026-04-18 07:38 CST] current react-performance-debugging -> exit_code=0; run_id=ac5d06ed819b | status=abandoned | failure_class=timeoutexpired | duration_seconds=2266.8051828269963 | final_model=gpt-5.4 | final_score=0.0 | last_event=runner_exception | notes=Command '['/usr/local/bin/codex', 'exec', '--ephemeral', '--skip-git-repo-check', '-C', '/tmp/masterskill-codex-lc1ug0hj', '-s', 'read-only', '-c', 'model_reasoning_effort="medium"', '-m', 'gpt-5.2', '-o', '/tmp/masterskill-codex-lc1ug0h...

- [2026-04-18 09:08 CST] current taxonomy-tree-merge -> exit_code=0; run_id=8f0054b678e5 | status=abandoned | failure_class=timeoutexpired | duration_seconds=5933.604577464001 | final_model=gpt-5.4 | final_score=0.0 | last_event=runner_exception | notes=Command '['/usr/local/bin/codex', 'exec', '--ephemeral', '--skip-git-repo-check', '-C', '/tmp/masterskill-codex-o17n59j1', '-s', 'read-only', '-c', 'model_reasoning_effort="medium"', '-m', 'gpt-5.2', '-o', '/tmp/masterskill-codex-o17n59j...

- [2026-04-18 09:21 CST] baseline react-performance-debugging -> exit_code=0; run_id=bd8392b759a6 | status=abandoned | failure_class=timeout | duration_seconds=810.9967598750009 | final_model=gpt-5.4 | final_score=0.0 | last_event=base_attempt | notes=Model could not solve autonomously

- [2026-04-18 09:32 CST] baseline taxonomy-tree-merge -> exit_code=0; run_id=acf078bb3e51 | status=abandoned | failure_class=timeout | duration_seconds=717.2174208470024 | final_model=gpt-5.4 | final_score=0.0 | last_event=base_attempt | notes=Model could not solve autonomously

- [2026-04-18 10:05 CST] current react-performance-debugging -> exit_code=0; run_id=de26c5ee9511 | status=abandoned | failure_class=timeoutexpired | duration_seconds=2225.3260962740023 | final_model=gpt-5.4 | final_score=0.0 | last_event=runner_exception | notes=Command '['/usr/local/bin/codex', 'exec', '--ephemeral', '--skip-git-repo-check', '-C', '/tmp/masterskill-codex-iwy0kbrw', '-s', 'read-only', '-c', 'model_reasoning_effort="medium"', '-m', 'gpt-5.2', '-o', '/tmp/masterskill-codex-iwy0kbr...

- [2026-04-18 11:45 CST] Repaired the main stability bottlenecks in both `MasterSkill/` and `src/icml_research/masterskill/`: internal agents now degrade via JSON fallbacks instead of turning second Codex timeouts into fatal `runner_exception`; `Judger` now fails conservatively when unavailable; `QuickProposer` keeps the current skill unchanged on fallback; `SkillCreator` can synthesize/optimize minimal operational skills on fallback.

- [2026-04-18 11:45 CST] Docker/runtime fixes landed: build-stage apt timeout now respects `task.toml` `environment.build_timeout_sec` with a 300s floor, execution reasoning effort is reduced from `xhigh` to `high`/`medium` by model tier, and artifact export now excludes cache-heavy paths such as `/root/.cache`, `/root/.npm`, `/.next/cache/`, `tsx`, `v8-compile-cache`, and Playwright download temp files.

- [2026-04-18 11:45 CST] Evolution-loop optimization landed in `scripts/overnight_masterskill.sh`: the runner now stages `proposer`/`judge` mirror paths correctly and applies failure-aware cooldown for repeated identical failure classes instead of blind 4-slot rotation.

- [2026-04-18 11:45 CST] Verification status: `py_compile` and local fallback smoke tests passed. A real Docker-backed `react-performance-debugging` chain check with capped loop limits reached `execution -> official test.sh -> analyzer -> searcher -> skill_creator -> critic -> judger -> next skill execution` without reproducing the previous fatal internal-agent timeout path. The verification run was stopped manually after the closed loop was confirmed.

- [2026-04-18 16:24 CST] Next-step control-plane patch landed: added `max_research_cycles` to cap total research loops per task, so `run_task()` no longer depends only on `real_test_failures` and cannot spin indefinitely when Judger keeps blocking without ever reaching real test.

- [2026-04-18 16:24 CST] Night runner policy was tightened to focus on current/evolution work: slot order is now `current react -> current taxonomy -> baseline react -> baseline taxonomy`, and baseline slots are skipped by default when the latest JSON already ends at `base_attempt` (set `MASTERSKILL_INCLUDE_BASELINES=1` to force baseline reruns).

- [2026-04-18 16:04 CST] Overnight run started on branch `overnight-masterskill-recovery`; log file: `/home/yuchong/auto-research-team/MasterSkill/logs/overnight_20260418_160420.log`

- [2026-04-18 16:04 CST] Overnight run started on branch `overnight-masterskill-recovery`; log file: `/home/yuchong/auto-research-team/MasterSkill/logs/overnight_20260418_160422.log`

- [2026-04-18 16:17 CST] baseline react-performance-debugging -> exit_code=0; run_id=698b991b04a6 | status=abandoned | failure_class=timeout | duration_seconds=883.826898697007 | final_model=gpt-5.4 | final_score=0.0 | last_event=base_attempt | notes=Model could not solve autonomously
