#!/usr/bin/env bash

set -u

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

LOG_DIR="$ROOT/MasterSkill/logs"
mkdir -p "$LOG_DIR"
MONITOR_TS="$(date +%Y%m%d_%H%M%S)"
MONITOR_LOG="$LOG_DIR/overnight_monitor_${MONITOR_TS}.log"
MONITOR_STATUS_FILE="$LOG_DIR/overnight_monitor_latest.txt"
RUNNER_STATUS_FILE="$LOG_DIR/overnight_latest_run.txt"
RUNNER_LAUNCH_LOG="$LOG_DIR/overnight_supervisor_launcher.out"
POLL_SECONDS="${MASTERSKILL_MONITOR_POLL_SECONDS:-180}"
STALL_WARN_SECONDS="${MASTERSKILL_MONITOR_STALL_WARN_SECONDS:-1800}"
DEADLINE_EPOCH="${MASTERSKILL_DEADLINE_EPOCH:-$(( $(date +%s) + 35500 ))}"

log() {
  printf '[%s] %s\n' "$(date -Iseconds)" "$*" | tee -a "$MONITOR_LOG"
}

runner_pid() {
  pgrep -fo "bash scripts/overnight_masterskill.sh" || true
}

runner_slot() {
  if [ -f "$RUNNER_STATUS_FILE" ]; then
    cat "$RUNNER_STATUS_FILE"
  else
    printf 'unknown'
  fi
}

latest_runner_log() {
  ls -1t "$LOG_DIR"/overnight_*.log 2>/dev/null | grep -v 'overnight_monitor_' | head -n 1
}

start_runner() {
  local pid
  log "runner missing; starting replacement runner"
  MASTERSKILL_DEADLINE_EPOCH="$DEADLINE_EPOCH" \
    bash scripts/overnight_masterskill.sh >> "$RUNNER_LAUNCH_LOG" 2>&1 &
  pid=$!
  sleep 2
  log "replacement runner launched pid=$pid"
}

last_warned_log=""

log "monitor started deadline_epoch=$DEADLINE_EPOCH poll_seconds=$POLL_SECONDS stall_warn_seconds=$STALL_WARN_SECONDS"

while [ "$(date +%s)" -lt "$DEADLINE_EPOCH" ]; do
  pid="$(runner_pid)"
  slot="$(runner_slot)"
  latest_log="$(latest_runner_log)"

  if [ -n "$pid" ]; then
    etime="$(ps -p "$pid" -o etime= 2>/dev/null | xargs || true)"
    status_line="runner alive pid=$pid etime=${etime:-unknown} slot=$slot"
    if [ -n "$latest_log" ] && [ -f "$latest_log" ]; then
      log_mtime="$(stat -c %Y "$latest_log")"
      log_age="$(( $(date +%s) - log_mtime ))"
      status_line="$status_line log=$(basename "$latest_log") log_age_seconds=$log_age"
      if [ "$log_age" -ge "$STALL_WARN_SECONDS" ] && [ "$latest_log" != "$last_warned_log" ]; then
        log "warning: runner log has been quiet for ${log_age}s while pid=$pid slot=$slot"
        last_warned_log="$latest_log"
      fi
    fi
    printf '%s\n' "$status_line" > "$MONITOR_STATUS_FILE"
    log "$status_line"
  else
    log "runner not found; last_known_slot=$slot"
    start_runner
  fi

  sleep "$POLL_SECONDS"
done

log "monitor finished because deadline was reached"
