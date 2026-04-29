#!/usr/bin/env bash

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

LOG_FILE="${1:-$ROOT/MasterSkill/logs/e1_followup_$(date +%Y%m%d_%H%M%S).log}"
mkdir -p "$(dirname "$LOG_FILE")"

log() {
  echo "[$(date '+%Y-%m-%d %H:%M:%S %Z')] $*" | tee -a "$LOG_FILE"
}

baseline_is_running() {
  pgrep -af "scripts/run_phase1_skillsbench.sh baseline-sweep" >/dev/null \
    || pgrep -af "python3 run_local.py --benchmark-all --pre-evolution-baseline --no-persist-task-skills --data-root $ROOT/MasterSkill/masterskill_data_phase1_pre_evolution" >/dev/null \
    || pgrep -af "python3 run_local.py --benchmark --pre-evolution-baseline --no-persist-task-skills --data-root $ROOT/MasterSkill/masterskill_data_phase1_pre_evolution" >/dev/null \
    || pgrep -af "python3 run_local.py --tasks .* --pre-evolution-baseline --no-persist-task-skills --data-root $ROOT/MasterSkill/masterskill_data_phase1_pre_evolution" >/dev/null \
    || pgrep -af "python3 run_local.py --task .* --pre-evolution-baseline --no-persist-task-skills --data-root $ROOT/MasterSkill/masterskill_data_phase1_pre_evolution" >/dev/null
}

baseline_latest_count() {
  find "$ROOT/MasterSkill/masterskill_data_phase1_pre_evolution/benchmark_runs/latest" -maxdepth 1 -name '*.json' 2>/dev/null | wc -l
}

baseline_expected_tasks() {
  find "$ROOT/MasterSkill/case/tasks" -mindepth 1 -maxdepth 1 -type d 2>/dev/null | wc -l
}

wait_for_baseline() {
  local expected latest
  expected="$(baseline_expected_tasks)"
  log "waiting for baseline completion (process exit + latest coverage ${expected}/${expected})..."
  while true; do
    latest="$(baseline_latest_count)"
    if baseline_is_running; then
      sleep 30
      continue
    fi
    if [[ "$latest" -ge "$expected" ]]; then
      break
    fi
    log "baseline process not running but coverage is ${latest}/${expected}; waiting for resume"
    sleep 30
  done
  log "baseline complete with latest coverage ${latest}/${expected}; proceeding"
}

prepare_current_root() {
  local current_root backup_ts backup_root
  current_root="$ROOT/MasterSkill/masterskill_data_phase1_current"
  if [[ -s "$current_root/benchmark_runs/runs.jsonl" ]]; then
    backup_ts="$(date +%Y%m%d_%H%M%S)"
    backup_root="${current_root}_pre_e1_backup_${backup_ts}"
    mv "$current_root" "$backup_root"
    log "backed up existing current data root to $backup_root"
  fi
  mkdir -p "$current_root"
}

main() {
  log "E1 follow-up start"
  wait_for_baseline

  prepare_current_root
  log "starting current-sweep"
  scripts/run_phase1_skillsbench.sh current-sweep 2>&1 | tee -a "$LOG_FILE"

  log "summarizing baseline sweep"
  python3 scripts/summarize_masterskill_results.py \
    --data-root "$ROOT/MasterSkill/masterskill_data_phase1_pre_evolution" \
    --show-tasks 2>&1 | tee -a "$LOG_FILE"

  log "summarizing current sweep"
  python3 scripts/summarize_masterskill_results.py \
    --data-root "$ROOT/MasterSkill/masterskill_data_phase1_current" \
    --show-tasks 2>&1 | tee -a "$LOG_FILE"

  log "comparing baseline vs current"
  python3 scripts/compare_masterskill_runs.py \
    --left-root "$ROOT/MasterSkill/masterskill_data_phase1_pre_evolution" \
    --right-root "$ROOT/MasterSkill/masterskill_data_phase1_current" \
    --left-label baseline \
    --right-label current \
    --show-tasks 2>&1 | tee -a "$LOG_FILE"

  log "E1 follow-up completed"
}

main "$@"
