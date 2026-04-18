#!/usr/bin/env bash

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

MODE="${1:-}"

if [[ -z "$MODE" ]]; then
  cat <<'EOF'
Usage:
  scripts/run_phase1_skillsbench.sh current-calibration
  scripts/run_phase1_skillsbench.sh baseline-calibration
  scripts/run_phase1_skillsbench.sh current-sweep
  scripts/run_phase1_skillsbench.sh baseline-sweep
  scripts/run_phase1_skillsbench.sh current-task <task_id>
  scripts/run_phase1_skillsbench.sh baseline-task <task_id>
EOF
  exit 1
fi

LOG_DIR="$ROOT/MasterSkill/logs"
mkdir -p "$LOG_DIR"
RUN_TS="$(date +%Y%m%d_%H%M%S)"
LOG_FILE="$LOG_DIR/phase1_${MODE}_${RUN_TS}.log"
BRANCH="$(git branch --show-current)"
COMMIT_SHA="$(git rev-parse HEAD)"
TASK_ROOT="$ROOT/MasterSkill/case"

CURRENT_ROOT="$ROOT/MasterSkill/masterskill_data_phase1_current"
BASELINE_ROOT="$ROOT/MasterSkill/masterskill_data_phase1_pre_evolution"
CALIBRATION_CURRENT_ROOT="$ROOT/MasterSkill/masterskill_data_phase1_calibration_current"
CALIBRATION_BASELINE_ROOT="$ROOT/MasterSkill/masterskill_data_phase1_calibration_pre_evolution"

CALIBRATION_TASKS=(
  enterprise-information-search
  pddl-tpp-planning
  react-performance-debugging
  taxonomy-tree-merge
  financial-modeling-qa
)

SINGLE_TASK="${2:-}"

run_cmd() {
  echo "[phase1] mode=$MODE" | tee -a "$LOG_FILE"
  echo "[phase1] log=$LOG_FILE" | tee -a "$LOG_FILE"
  echo "[phase1] branch=$BRANCH" | tee -a "$LOG_FILE"
  echo "[phase1] commit=$COMMIT_SHA" | tee -a "$LOG_FILE"
  echo "[phase1] task_root=$TASK_ROOT" | tee -a "$LOG_FILE"
  echo "[phase1] data_root=$DATA_ROOT" | tee -a "$LOG_FILE"
  echo "[phase1] docker=$(docker version --format '{{.Server.Version}}' 2>/dev/null || echo unavailable)" | tee -a "$LOG_FILE"
  echo "[phase1] command: $*" | tee -a "$LOG_FILE"
  "$@" 2>&1 | tee -a "$LOG_FILE"
}

write_manifest() {
  mkdir -p "$DATA_ROOT"
  cat > "$DATA_ROOT/phase1_manifest.json" <<EOF
{
  "mode": "$MODE",
  "timestamp": "$RUN_TS",
  "branch": "$BRANCH",
  "commit_sha": "$COMMIT_SHA",
  "task_root": "$TASK_ROOT",
  "data_root": "$DATA_ROOT"
}
EOF
}

case "$MODE" in
  current-calibration)
    DATA_ROOT="$CALIBRATION_CURRENT_ROOT"
    write_manifest
    run_cmd python3 run_local.py \
      --tasks "${CALIBRATION_TASKS[@]}" \
      --data-root "$DATA_ROOT" \
      --post-solve-optimization-rounds 1 \
      --max-research-cycles 3
    ;;
  baseline-calibration)
    DATA_ROOT="$CALIBRATION_BASELINE_ROOT"
    write_manifest
    run_cmd python3 run_local.py \
      --tasks "${CALIBRATION_TASKS[@]}" \
      --pre-evolution-baseline \
      --data-root "$DATA_ROOT"
    ;;
  current-sweep)
    DATA_ROOT="$CURRENT_ROOT"
    write_manifest
    run_cmd python3 run_local.py \
      --benchmark-all \
      --data-root "$DATA_ROOT" \
      --post-solve-optimization-rounds 1 \
      --max-research-cycles 3
    ;;
  baseline-sweep)
    DATA_ROOT="$BASELINE_ROOT"
    write_manifest
    run_cmd python3 run_local.py \
      --benchmark-all \
      --pre-evolution-baseline \
      --data-root "$DATA_ROOT"
    ;;
  current-task)
    if [[ -z "$SINGLE_TASK" ]]; then
      echo "missing task id for current-task mode" >&2
      exit 1
    fi
    DATA_ROOT="$CALIBRATION_CURRENT_ROOT"
    write_manifest
    run_cmd python3 run_local.py \
      --task "$SINGLE_TASK" \
      --data-root "$DATA_ROOT" \
      --post-solve-optimization-rounds 1 \
      --max-research-cycles 3
    ;;
  baseline-task)
    if [[ -z "$SINGLE_TASK" ]]; then
      echo "missing task id for baseline-task mode" >&2
      exit 1
    fi
    DATA_ROOT="$CALIBRATION_BASELINE_ROOT"
    write_manifest
    run_cmd python3 run_local.py \
      --task "$SINGLE_TASK" \
      --pre-evolution-baseline \
      --data-root "$DATA_ROOT"
    ;;
  *)
    echo "unknown mode: $MODE" >&2
    exit 1
    ;;
esac
