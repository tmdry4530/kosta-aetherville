#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$ROOT_DIR"
RUN_DIR="${AETHERVILLE_RUN_DIR:-/tmp/aetherville}"
PID_DIR="$RUN_DIR/pids"

if [[ ! -d "$PID_DIR" ]]; then
  echo "No pid dir at $PID_DIR"
  exit 0
fi

for pid_file in "$PID_DIR"/*.pid; do
  [[ -e "$pid_file" ]] || continue
  name="$(basename "$pid_file" .pid)"
  pid="$(cat "$pid_file")"
  if kill -0 "$pid" >/dev/null 2>&1; then
    echo "stopping $name pid=$pid"
    children="$(pgrep -P "$pid" 2>/dev/null || true)"
    if [[ -n "$children" ]]; then
      kill $children || true
    fi
    kill "$pid" || true
  else
    echo "$name pid=$pid is not running"
  fi
  rm -f "$pid_file"
done
