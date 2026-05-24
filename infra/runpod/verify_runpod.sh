#!/usr/bin/env bash
set -euo pipefail

ENV_FILE="infra/runpod/.env.runpod"
if [[ -f "$ENV_FILE" ]]; then
  set -a
  # shellcheck disable=SC1090
  source "$ENV_FILE"
  set +a
fi

: "${RUNPOD_HOST:?RUNPOD_HOST is required}"
: "${RUNPOD_SSH_PORT:=22}"
: "${RUNPOD_USER:=root}"
: "${RUNPOD_SSH_KEY:?RUNPOD_SSH_KEY is required}"
: "${RUNPOD_REMOTE_DIR:=/workspace/aetherville}"

SSH_OPTS=(-i "$RUNPOD_SSH_KEY" -p "$RUNPOD_SSH_PORT" -o BatchMode=yes -o ConnectTimeout=15 -o IdentitiesOnly=yes -o StrictHostKeyChecking=accept-new)
TARGET="$RUNPOD_USER@$RUNPOD_HOST"
REDACTED_TARGET="$RUNPOD_USER@<runpod-host>:<port>"

redact_output() {
  local line
  while IFS= read -r line; do
    line="${line//$RUNPOD_HOST/<runpod-host>}"
    line="${line//$RUNPOD_SSH_KEY/<ssh-key>}"
    printf '%s\n' "$line"
  done
}

ssh_run() {
  local output
  local status
  local restore_errexit=0
  case $- in
    *e*) restore_errexit=1 ;;
  esac
  set +e
  output=$(ssh "${SSH_OPTS[@]}" "$TARGET" "$@" 2>&1)
  status=$?
  if [[ "$restore_errexit" == "1" ]]; then
    set -e
  fi
  printf '%s\n' "$output" | redact_output
  return "$status"
}

echo "== Local SSH key check =="
if [[ ! -r "$RUNPOD_SSH_KEY" ]]; then
  echo "Blocker: RUNPOD_SSH_KEY is not readable locally."
  exit 9
fi
if ssh-keygen -y -f "$RUNPOD_SSH_KEY" >/tmp/aetherville_runpod_pubkey.verify 2>/dev/null; then
  ssh-keygen -lf /tmp/aetherville_runpod_pubkey.verify | awk '{print "configured-key:", $2, $4}'
else
  echo "Blocker: RUNPOD_SSH_KEY could not be parsed as a private key."
  exit 9
fi

echo "== RunPod SSH connectivity =="
if ! ssh_run 'echo host=$(hostname); echo user=$(whoami); pwd'; then
  echo "Blocker: SSH connectivity/authentication failed. Verify RunPod pod is running, the SSH port/user are correct, and the public key for RUNPOD_SSH_KEY is attached to the pod."
  exit 10
fi

echo "== GPU check =="
if ! ssh_run 'if command -v nvidia-smi >/dev/null 2>&1; then nvidia-smi; else echo "nvidia-smi not found"; exit 2; fi'; then
  echo "Blocker: GPU visibility check failed. Verify the pod was launched with a GPU image/runtime and that nvidia-smi works inside the pod."
  exit 11
fi

echo "== Runtime check =="
ssh_run 'set -e; python --version || true; node --version || true; pnpm --version || true; uv --version || true; redis-server --version || true'

echo "== Service process check =="
ssh_run 'ps -eo pid=,comm= | awk '"'"'$2 ~ /^(python|uvicorn|vllm|redis-server|caddy|docker)$/ {print}'"'"' || true'

echo "== Docker check =="
if ssh_run 'command -v docker >/dev/null 2>&1 && docker info >/dev/null 2>&1'; then
  echo "Docker daemon: available"
else
  echo "Docker daemon: unavailable. Use direct-process fallback or a RunPod template with Docker support."
fi

echo "== Remote workspace check =="
ssh_run "if test -d '$RUNPOD_REMOTE_DIR'; then echo 'remote workspace exists'; else echo 'remote workspace missing; deploy script will create it'; fi"

echo "== Optional public URL checks =="
if [[ -n "${RUNPOD_PUBLIC_ORCHESTRATOR_URL:-}" ]]; then
  curl -fsS --max-time 5 "$RUNPOD_PUBLIC_ORCHESTRATOR_URL/api/v1/health" || echo "orchestrator public health not reachable yet"
fi
if [[ -n "${RUNPOD_PUBLIC_VISION_URL:-}" ]]; then
  curl -fsS --max-time 5 "$RUNPOD_PUBLIC_VISION_URL/health" || echo "vision public health not reachable yet"
fi
if [[ -n "${RUNPOD_PUBLIC_VLLM_URL:-}" ]]; then
  curl -fsS --max-time 5 "$RUNPOD_PUBLIC_VLLM_URL/models" || echo "vLLM public models endpoint not reachable yet"
fi

echo "RunPod verification completed for $REDACTED_TARGET."
