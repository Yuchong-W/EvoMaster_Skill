#!/usr/bin/env bash
set -euo pipefail

SEED="${PYTHONHASHSEED:-1}"
PROFILE="${HOME:-/root}/.bash_profile"

mkdir -p "$(dirname "$PROFILE")"
if [ -f "$PROFILE" ]; then
  grep -v '^export PYTHONHASHSEED=' "$PROFILE" > "${PROFILE}.masterskill.tmp" || true
  mv "${PROFILE}.masterskill.tmp" "$PROFILE"
fi
printf 'export PYTHONHASHSEED=%s\n' "$SEED" >> "$PROFILE"

export PYTHONHASHSEED="$SEED"
exec python3 /root/.skills/pddl-tpp-planning-direct/scripts/solve_tpp_batch.py
