#!/usr/bin/env bash

set -u

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

LOG_DIR="$ROOT/MasterSkill/logs"
mkdir -p "$LOG_DIR"
RUN_TS="$(date +%Y%m%d_%H%M%S)"
RUN_LOG="$LOG_DIR/overnight_${RUN_TS}.log"
STATUS_FILE="$LOG_DIR/overnight_latest_run.txt"
BRANCH="$(git branch --show-current)"
DEADLINE_EPOCH="$(( $(date +%s) + 35500 ))"

export PYTHONUNBUFFERED=1

log() {
  printf '[%s] %s\n' "$(date -Iseconds)" "$*" | tee -a "$RUN_LOG"
}

append_devlog() {
  local heading="$1"
  local body="$2"
  {
    printf '\n### %s\n\n' "$(date '+%Y-%m-%d %H:%M %Z') ${heading}"
    printf -- '- %s\n' "$body"
  } >> "$ROOT/MasterSkill/development_log.md"
}

append_resume() {
  local line="$1"
  printf '\n- [%s] %s\n' "$(date '+%Y-%m-%d %H:%M %Z')" "$line" >> "$ROOT/MasterSkill/session_resume.md"
}

stage_known_paths() {
  git add -- \
    .gitignore \
    run_local.py \
    scripts/overnight_masterskill.sh \
    MasterSkill/run_local.py \
    MasterSkill/session_resume.md \
    MasterSkill/development_log.md \
    MasterSkill/state.md \
    MasterSkill/technical_design.md \
    MasterSkill/skillsbench_task_classification.md \
    MasterSkill/main.py \
    MasterSkill/agents \
    MasterSkill/core \
    MasterSkill/judge \
    MasterSkill/memory \
    MasterSkill/runner \
    MasterSkill/skill \
    MasterSkill/evolved_skills \
    MasterSkill/masterskill_data \
    MasterSkill/masterskill_data_pre_evolution \
    src/icml_research/masterskill/main.py \
    src/icml_research/masterskill/agents \
    src/icml_research/masterskill/core \
    src/icml_research/masterskill/memory \
    src/icml_research/masterskill/runner \
    src/icml_research/masterskill/skill
}

maybe_commit_push() {
  local message="$1"
  stage_known_paths >> "$RUN_LOG" 2>&1 || true
  if git diff --cached --quiet; then
    log "no staged changes for commit: $message"
    return 0
  fi

  log "committing: $message"
  if git commit -m "$message" >> "$RUN_LOG" 2>&1; then
    log "pushing branch $BRANCH"
    git push origin "$BRANCH" >> "$RUN_LOG" 2>&1
  else
    log "commit failed: $message"
  fi
}

summarize_json() {
  local json_path="$1"
  python3 - "$json_path" <<'PY'
import json
import pathlib
import sys

path = pathlib.Path(sys.argv[1])
if not path.exists():
    print("result file missing")
    raise SystemExit(0)

data = json.loads(path.read_text())
parts = [
    f"run_id={data.get('run_id', '')}",
    f"status={data.get('status', '')}",
    f"failure_class={data.get('failure_class', '')}",
    f"duration_seconds={data.get('duration_seconds', '')}",
    f"final_model={data.get('final_model', '')}",
    f"final_score={data.get('final_score', '')}",
]
events = data.get("events") or []
if events:
    event = events[-1]
    notes = (event.get("notes") or "").replace("\n", " ").strip()
    if len(notes) > 240:
        notes = notes[:237] + "..."
    parts.append(f"last_event={event.get('stage', '')}")
    if notes:
        parts.append(f"notes={notes}")
print(" | ".join(parts))
PY
}

run_and_record() {
  local label="$1"
  local command="$2"
  local json_path="$3"

  log "starting: $label"
  log "command: $command"
  printf '%s\n' "$label" > "$STATUS_FILE"
  bash -lc "$command" >> "$RUN_LOG" 2>&1
  local exit_code=$?
  local summary
  summary="$(summarize_json "$json_path")"
  log "finished: $label exit_code=$exit_code"
  log "summary: $summary"
  append_resume "$label -> exit_code=$exit_code; $summary"
  append_devlog "$label" "exit_code=$exit_code; $summary"
  maybe_commit_push "Checkpoint overnight: $label"
}

within_deadline() {
  [ "$(date +%s)" -lt "$DEADLINE_EPOCH" ]
}

append_resume "Overnight run started on branch \`$BRANCH\`; log file: \`$RUN_LOG\`"
append_devlog "Overnight run started" "branch=$BRANCH; log=$RUN_LOG"
maybe_commit_push "Start overnight MasterSkill recovery run"

BASELINE_DATA="$ROOT/MasterSkill/masterskill_data_pre_evolution"
CURRENT_DATA="$ROOT/MasterSkill/masterskill_data"

declare -a LABELS=(
  "baseline react-performance-debugging"
  "baseline taxonomy-tree-merge"
  "current react-performance-debugging"
  "current taxonomy-tree-merge"
)

declare -a COMMANDS=(
  "python3 run_local.py --task react-performance-debugging --pre-evolution-baseline --data-root $BASELINE_DATA"
  "python3 run_local.py --task taxonomy-tree-merge --pre-evolution-baseline --data-root $BASELINE_DATA"
  "python3 run_local.py --task react-performance-debugging --data-root $CURRENT_DATA --post-solve-optimization-rounds 1"
  "python3 run_local.py --task taxonomy-tree-merge --data-root $CURRENT_DATA --post-solve-optimization-rounds 1"
)

declare -a JSONS=(
  "$BASELINE_DATA/benchmark_runs/latest/react-performance-debugging.json"
  "$BASELINE_DATA/benchmark_runs/latest/taxonomy-tree-merge.json"
  "$CURRENT_DATA/benchmark_runs/latest/react-performance-debugging.json"
  "$CURRENT_DATA/benchmark_runs/latest/taxonomy-tree-merge.json"
)

index=0
while within_deadline; do
  slot=$(( index % ${#LABELS[@]} ))
  run_and_record "${LABELS[$slot]}" "${COMMANDS[$slot]}" "${JSONS[$slot]}"
  index=$(( index + 1 ))
done

append_resume "Overnight run finished; total_slots=$index; branch=\`$BRANCH\`"
append_devlog "Overnight run finished" "total_slots=$index; branch=$BRANCH"
maybe_commit_push "Finish overnight MasterSkill recovery run"
log "overnight runner finished after $index slots"
