#!/usr/bin/env bash

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

DATA_ROOT="$ROOT/MasterSkill/masterskill_data_phase1_pre_evolution"
TASK_ROOT="$ROOT/MasterSkill/case/tasks"
PER_TASK_TIMEOUT_SECONDS="${PER_TASK_TIMEOUT_SECONDS:-1500}"
SLEEP_SECONDS="${SLEEP_SECONDS:-10}"

latest_count() {
  find "$DATA_ROOT/benchmark_runs/latest" -maxdepth 1 -name '*.json' 2>/dev/null | wc -l
}

expected_count() {
  find "$TASK_ROOT" -mindepth 1 -maxdepth 1 -type d 2>/dev/null | wc -l
}

list_missing_tasks() {
  local task_id
  for dir in "$TASK_ROOT"/*; do
    [[ -d "$dir" ]] || continue
    task_id="$(basename "$dir")"
    if [[ ! -f "$DATA_ROOT/benchmark_runs/latest/${task_id}.json" ]]; then
      echo "$task_id"
    fi
  done
}

log() {
  echo "[$(date '+%Y-%m-%d %H:%M:%S %Z')] $*"
}

main() {
  local expected current attempt rc task
  local -a missing ordered tail
  expected="$(expected_count)"
  attempt=0
  log "baseline auto-resume start: target coverage ${expected}/${expected}"
  while true; do
    current="$(latest_count)"
    if [[ "$current" -ge "$expected" ]]; then
      log "baseline coverage reached ${current}/${expected}; stop"
      break
    fi

    attempt=$((attempt + 1))
    mapfile -t missing < <(list_missing_tasks)
    ordered=()
    tail=()
    for task in "${missing[@]}"; do
      if [[ "$task" == "react-performance-debugging" ]]; then
        tail+=("$task")
      else
        ordered+=("$task")
      fi
    done
    missing=("${ordered[@]}" "${tail[@]}")
    if [[ "${#missing[@]}" -eq 0 ]]; then
      log "attempt ${attempt}: no missing tasks found; stop"
      break
    fi
    log "attempt ${attempt}: coverage ${current}/${expected}, missing tasks: ${missing[*]}"

    for task in "${missing[@]}"; do
      if [[ -f "$DATA_ROOT/benchmark_runs/latest/${task}.json" ]]; then
        continue
      fi
      log "attempt ${attempt}: run task ${task}"
      set +e
      timeout --signal=INT --kill-after=60s "${PER_TASK_TIMEOUT_SECONDS}s" \
        python3 run_local.py \
          --task "$task" \
          --pre-evolution-baseline \
          --no-persist-task-skills \
          --data-root "$DATA_ROOT"
      rc=$?
      set -e
      if [[ "$rc" -eq 0 ]]; then
        log "task ${task} exited cleanly"
      elif [[ "$rc" -eq 124 ]]; then
        log "task ${task} timed out"
      else
        log "task ${task} exited rc=${rc}"
      fi
      current="$(latest_count)"
      log "coverage after ${task}: ${current}/${expected}"
      if [[ "$current" -ge "$expected" ]]; then
        break
      fi
    done
    sleep "$SLEEP_SECONDS"
  done
}

main "$@"
