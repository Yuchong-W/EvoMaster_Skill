#!/usr/bin/env bash

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

MODE="${1:-all}"

LOG_DIR="$ROOT/MasterSkill/logs"
mkdir -p "$LOG_DIR"
RUN_TS="$(date +%Y%m%d_%H%M%S)"
LOG_FILE="$LOG_DIR/phase1_gpt52_consistency_${MODE}_${RUN_TS}.log"

CURRENT_ROOT="$ROOT/MasterSkill/masterskill_data_phase1_current"
BASELINE_ROOT="$ROOT/MasterSkill/masterskill_data_phase1_pre_evolution"

CURRENT_TASKS=(
  enterprise-information-search
  financial-modeling-qa
  pddl-tpp-planning
  seismic-phase-picking
)

BASELINE_TASKS=(
  enterprise-information-search
  financial-modeling-qa
  pddl-tpp-planning
)

log() {
  echo "[$(date '+%Y-%m-%d %H:%M:%S %Z')] $*" | tee -a "$LOG_FILE"
}

run_current_task() {
  local task="$1"
  log "current rerun start: $task"
  python3 run_local.py \
    --task "$task" \
    --data-root "$CURRENT_ROOT" \
    --no-persist-task-skills \
    --post-solve-optimization-rounds 1 \
    --max-research-cycles 3 2>&1 | tee -a "$LOG_FILE"
  log "current rerun done: $task"
}

run_baseline_task() {
  local task="$1"
  log "baseline rerun start: $task"
  python3 run_local.py \
    --task "$task" \
    --pre-evolution-baseline \
    --no-persist-task-skills \
    --data-root "$BASELINE_ROOT" 2>&1 | tee -a "$LOG_FILE"
  log "baseline rerun done: $task"
}

run_current() {
  local task
  for task in "${CURRENT_TASKS[@]}"; do
    run_current_task "$task"
  done
}

run_baseline() {
  local task
  for task in "${BASELINE_TASKS[@]}"; do
    run_baseline_task "$task"
  done
}

case "$MODE" in
  current)
    run_current
    ;;
  baseline)
    run_baseline
    ;;
  all)
    run_current
    run_baseline
    ;;
  *)
    echo "unknown mode: $MODE" >&2
    exit 1
    ;;
esac
