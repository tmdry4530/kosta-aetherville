#!/usr/bin/env bash
set -euo pipefail

ORCHESTRATOR_URL="${ORCHESTRATOR_URL:-http://127.0.0.1:${AETHERVILLE_ORCHESTRATOR_PORT:-8080}}"
VISION_URL="${VISION_URL:-http://127.0.0.1:${AETHERVILLE_VISION_PORT:-8001}}"
VLLM_URL="${VLLM_URL:-http://127.0.0.1:${AETHERVILLE_VLLM_PORT:-8000}/v1}"
REDIS_PORT="${AETHERVILLE_REDIS_PORT:-6379}"
REDIS_MODE="${AETHERVILLE_REDIS_MODE:-auto}"
HEALTH_RETRIES="${AETHERVILLE_HEALTH_RETRIES:-1}"
HEALTH_SLEEP="${AETHERVILLE_HEALTH_SLEEP:-0.5}"

check_http() {
  local name="$1"
  local url="$2"
  local expected="${3:-}"
  local attempt
  local body
  echo "== $name =="
  for attempt in $(seq 1 "$HEALTH_RETRIES"); do
    if body=$(curl -fsS --max-time 5 "$url"); then
      if [[ -z "$expected" || "$body" == *"$expected"* ]]; then
        printf '%s\n' "$body"
        return 0
      fi
      echo "unexpected $name health payload; expected marker '$expected'" >&2
      printf '%s\n' "$body" >&2
    fi
    if [[ "$attempt" != "$HEALTH_RETRIES" ]]; then
      sleep "$HEALTH_SLEEP"
    fi
  done
  echo "health check failed for $name after $HEALTH_RETRIES attempts" >&2
  return 1
}

check_http orchestrator "$ORCHESTRATOR_URL/api/v1/health" '"service":"orchestrator"'
check_http vision "$VISION_URL/health" '"service":"vision"'
check_http vllm "$VLLM_URL/models" 'aetherville-mock-llm'

echo "== redis =="
if [[ "$REDIS_MODE" == "memory" ]]; then
  echo "redis: memory fallback selected"
elif command -v redis-cli >/dev/null 2>&1 && redis-cli -h 127.0.0.1 -p "$REDIS_PORT" ping >/tmp/aetherville_redis_ping 2>/tmp/aetherville_redis_ping.err; then
  cat /tmp/aetherville_redis_ping
else
  echo "redis: unavailable; acceptable only when orchestrator is configured for in-memory fallback"
fi

echo "direct-process health check complete"
