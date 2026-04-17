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
