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
DEADLINE_EPOCH="${MASTERSKILL_DEADLINE_EPOCH:-$(( $(date +%s) + 35500 ))}"

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
    scripts/monitor_overnight_masterskill.sh \
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
    MasterSkill/proposer \
    MasterSkill/runner \
    MasterSkill/skill \
    MasterSkill/evolved_skills \
    MasterSkill/masterskill_data \
    MasterSkill/masterskill_data_pre_evolution \
    src/icml_research/masterskill/main.py \
    src/icml_research/masterskill/agents \
    src/icml_research/masterskill/core \
    src/icml_research/masterskill/judge \
    src/icml_research/masterskill/memory \
    src/icml_research/masterskill/proposer \
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

json_field() {
  local json_path="$1"
  local field_name="$2"
  python3 - "$json_path" "$field_name" <<'PY'
import json
import pathlib
import sys

path = pathlib.Path(sys.argv[1])
field_name = sys.argv[2]
if not path.exists():
    print("")
    raise SystemExit(0)

try:
    data = json.loads(path.read_text())
except Exception:
    print("")
    raise SystemExit(0)

value = data.get(field_name, "")
if value is None:
    value = ""
print(str(value))
PY
}

latest_event_stage() {
  local json_path="$1"
  python3 - "$json_path" <<'PY'
import json
import pathlib
import sys

path = pathlib.Path(sys.argv[1])
if not path.exists():
    print("")
    raise SystemExit(0)

try:
    data = json.loads(path.read_text())
except Exception:
    print("")
    raise SystemExit(0)

events = data.get("events") or []
event = events[-1] if events else {}
print(str(event.get("stage", "") or ""))
PY
}

should_skip_baseline_slot() {
  local label="$1"
  local json_path="$2"

  if [[ "$label" != baseline* ]]; then
    return 1
  fi

  if [ "${MASTERSKILL_INCLUDE_BASELINES:-0}" = "1" ]; then
    return 1
  fi

  local last_stage
  last_stage="$(latest_event_stage "$json_path")"
  [ "$last_stage" = "base_attempt" ]
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
  RUN_STATUS="$(json_field "$json_path" "status")"
  RUN_FAILURE_CLASS="$(json_field "$json_path" "failure_class")"
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
  "current react-performance-debugging"
  "current taxonomy-tree-merge"
  "baseline react-performance-debugging"
  "baseline taxonomy-tree-merge"
)

declare -a COMMANDS=(
  "python3 run_local.py --task react-performance-debugging --data-root $CURRENT_DATA --post-solve-optimization-rounds 1 --max-research-cycles 3"
  "python3 run_local.py --task taxonomy-tree-merge --data-root $CURRENT_DATA --post-solve-optimization-rounds 1 --max-research-cycles 3"
  "python3 run_local.py --task react-performance-debugging --pre-evolution-baseline --data-root $BASELINE_DATA"
  "python3 run_local.py --task taxonomy-tree-merge --pre-evolution-baseline --data-root $BASELINE_DATA"
)

declare -a JSONS=(
  "$CURRENT_DATA/benchmark_runs/latest/react-performance-debugging.json"
  "$CURRENT_DATA/benchmark_runs/latest/taxonomy-tree-merge.json"
  "$BASELINE_DATA/benchmark_runs/latest/react-performance-debugging.json"
  "$BASELINE_DATA/benchmark_runs/latest/taxonomy-tree-merge.json"
)

BACKOFF_REPEAT_THRESHOLD="${MASTERSKILL_BACKOFF_REPEAT_THRESHOLD:-2}"
BACKOFF_COOLDOWN_SLOTS="${MASTERSKILL_BACKOFF_COOLDOWN_SLOTS:-2}"
RUN_STATUS=""
RUN_FAILURE_CLASS=""
declare -a LAST_RESULT_KEYS=()
declare -a REPEAT_COUNTS=()
declare -a COOLDOWN_UNTIL=()

record_slot_result() {
  local slot="$1"
  local label="$2"
  local slot_index="$3"
  local result_key=""

  if [ -n "$RUN_FAILURE_CLASS" ]; then
    result_key="failure:$RUN_FAILURE_CLASS"
  elif [ -n "$RUN_STATUS" ]; then
    result_key="status:$RUN_STATUS"
  else
    result_key="status:unknown"
  fi

  local last_key="${LAST_RESULT_KEYS[$slot]:-}"
  local repeat_count=1
  if [ "$result_key" = "$last_key" ]; then
    repeat_count=$(( ${REPEAT_COUNTS[$slot]:-0} + 1 ))
  fi

  LAST_RESULT_KEYS[$slot]="$result_key"
  REPEAT_COUNTS[$slot]="$repeat_count"

  if [[ "$result_key" == failure:* ]] && [ "$repeat_count" -ge "$BACKOFF_REPEAT_THRESHOLD" ]; then
    COOLDOWN_UNTIL[$slot]=$(( slot_index + BACKOFF_COOLDOWN_SLOTS + 1 ))
    log "backoff: $label repeated_result=$result_key count=$repeat_count cooldown_slots=$BACKOFF_COOLDOWN_SLOTS"
    append_resume "$label -> cooldown scheduled after repeated $result_key (count=$repeat_count, skip_until_slot=${COOLDOWN_UNTIL[$slot]})"
    append_devlog "$label cooldown" "repeated_result=$result_key; count=$repeat_count; skip_until_slot=${COOLDOWN_UNTIL[$slot]}"
    REPEAT_COUNTS[$slot]=0
  fi
}

index=0
while within_deadline; do
  slot=$(( index % ${#LABELS[@]} ))
  if should_skip_baseline_slot "${LABELS[$slot]}" "${JSONS[$slot]}"; then
    log "skipping: ${LABELS[$slot]} because a valid base_attempt record already exists"
    append_resume "${LABELS[$slot]} -> skipped because latest record already contains a valid base_attempt result"
    index=$(( index + 1 ))
    continue
  fi
  if [ "${COOLDOWN_UNTIL[$slot]:-0}" -gt "$index" ]; then
    log "skipping: ${LABELS[$slot]} due to cooldown until slot ${COOLDOWN_UNTIL[$slot]}"
    append_resume "${LABELS[$slot]} -> skipped due to repeated failure cooldown (current_slot=$index, resume_at=${COOLDOWN_UNTIL[$slot]})"
    index=$(( index + 1 ))
    continue
  fi
  run_and_record "${LABELS[$slot]}" "${COMMANDS[$slot]}" "${JSONS[$slot]}"
  record_slot_result "$slot" "${LABELS[$slot]}" "$index"
  index=$(( index + 1 ))
done

append_resume "Overnight run finished; total_slots=$index; branch=\`$BRANCH\`"
append_devlog "Overnight run finished" "total_slots=$index; branch=$BRANCH"
maybe_commit_push "Finish overnight MasterSkill recovery run"
log "overnight runner finished after $index slots"
