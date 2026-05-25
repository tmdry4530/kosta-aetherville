#!/usr/bin/env bash
set -euo pipefail

DRY_RUN=0
while [[ $# -gt 0 ]]; do
  case "$1" in
    --dry-run)
      DRY_RUN=1
      shift
      ;;
    *)
      echo "Unknown argument: $1" >&2
      exit 2
      ;;
  esac
done

ROOT_DIR="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$ROOT_DIR"

RUN_DIR="${AETHERVILLE_RUN_DIR:-/tmp/aetherville}"
LOG_DIR="$RUN_DIR/logs"
PID_DIR="$RUN_DIR/pids"
HOST="${AETHERVILLE_SERVICE_HOST:-0.0.0.0}"
ORCHESTRATOR_PORT="${AETHERVILLE_ORCHESTRATOR_PORT:-8080}"
VISION_PORT="${AETHERVILLE_VISION_PORT:-18001}"
VLLM_PORT="${AETHERVILLE_VLLM_PORT:-8000}"
REDIS_PORT="${AETHERVILLE_REDIS_PORT:-6379}"
VLLM_MODE="${AETHERVILLE_VLLM_MODE:-mock}"
REDIS_MODE="${AETHERVILLE_REDIS_MODE:-auto}"
MODEL_NAME="${MODEL_NAME:-Qwen/Qwen2.5-14B-Instruct-AWQ}"
MODEL_CACHE_DIR="${AETHERVILLE_MODEL_CACHE_DIR:-/workspace/aetherville-model-cache}"
VLLM_INSTALL_PACKAGE="${AETHERVILLE_VLLM_INSTALL_PACKAGE:-vllm==0.10.2}"
VLLM_COMPAT_PACKAGE="${AETHERVILLE_VLLM_COMPAT_PACKAGE:-transformers==4.55.4}"
LLM_MODE="${AETHERVILLE_LLM_MODE:-cache}"
RESTART_PROCESSES="${AETHERVILLE_RESTART_PROCESSES:-0}"

redacted_cmd() {
  printf '%s' "$*" | sed -E 's/(HF_TOKEN=)[^ ]+/\1<redacted>/g; s/(AETHERVILLE_JWT_SECRET=)[^ ]+/\1<redacted>/g'
}

run_or_print() {
  if [[ "$DRY_RUN" == "1" ]]; then
    echo "DRY-RUN: $(redacted_cmd "$@")"
  else
    "$@"
  fi
}

ensure_uv() {
  if command -v uv >/dev/null 2>&1; then
    return 0
  fi
  if [[ "${AETHERVILLE_BOOTSTRAP_UV:-0}" == "1" ]]; then
    run_or_print python -m pip install --user uv
    export PATH="$HOME/.local/bin:$PATH"
  fi
  if ! command -v uv >/dev/null 2>&1 && [[ "$DRY_RUN" != "1" ]]; then
    echo "Blocker: uv is not installed. Set AETHERVILLE_BOOTSTRAP_UV=1 to install uv into the user environment, or install uv before starting services." >&2
    exit 20
  fi
}

start_process() {
  local name="$1"
  local command="$2"
  local pid_file="$PID_DIR/$name.pid"
  local log_file="$LOG_DIR/$name.log"

  if [[ -f "$pid_file" ]] && kill -0 "$(cat "$pid_file")" >/dev/null 2>&1; then
    if [[ "$RESTART_PROCESSES" == "1" ]]; then
      echo "restarting $name pid=$(cat "$pid_file")"
      kill "$(cat "$pid_file")" >/dev/null 2>&1 || true
      sleep 0.5
    else
      echo "$name already running with pid $(cat "$pid_file")"
      return 0
    fi
  fi

  if [[ "$DRY_RUN" == "1" ]]; then
    echo "DRY-RUN: start $name -> $(redacted_cmd "$command")"
    return 0
  fi

  mkdir -p "$LOG_DIR" "$PID_DIR"
  nohup bash -lc "$command" >"$log_file" 2>&1 &
  echo "$!" >"$pid_file"
  echo "started $name pid=$(cat "$pid_file") log=$log_file"
}

stop_process_if_running() {
  local name="$1"
  local pid_file="$PID_DIR/$name.pid"
  if [[ -f "$pid_file" ]] && kill -0 "$(cat "$pid_file")" >/dev/null 2>&1; then
    echo "stopping $name pid=$(cat "$pid_file")"
    if [[ "$DRY_RUN" == "1" ]]; then
      echo "DRY-RUN: stop $name"
      return 0
    fi
    kill "$(cat "$pid_file")" >/dev/null 2>&1 || true
    sleep 0.5
  fi
}

echo "== Aetherville direct-process start =="
echo "workspace=$ROOT_DIR"
echo "run_dir=$RUN_DIR"
echo "vllm_mode=$VLLM_MODE redis_mode=$REDIS_MODE"

run_or_print mkdir -p "$LOG_DIR" "$PID_DIR"
ensure_uv
if [[ "${AETHERVILLE_SKIP_UV_SYNC:-0}" == "1" ]]; then
  echo "Skipping uv sync because AETHERVILLE_SKIP_UV_SYNC=1"
else
  run_or_print uv sync --no-dev
fi

ensure_real_vllm() {
  if [[ "$VLLM_MODE" != "real" ]]; then
    return 0
  fi
  run_or_print mkdir -p "$MODEL_CACHE_DIR"
  export HF_HOME="${HF_HOME:-$MODEL_CACHE_DIR/hf}"
  export HUGGINGFACE_HUB_CACHE="${HUGGINGFACE_HUB_CACHE:-$HF_HOME/hub}"
  if [[ "$DRY_RUN" == "1" ]]; then
    echo "DRY-RUN: verify or install real vLLM package '$VLLM_INSTALL_PACKAGE'"
    return 0
  fi
  if [[ "${AETHERVILLE_FORCE_VLLM_INSTALL:-0}" != "1" ]] \
    && uv run python -c "import vllm" >/dev/null 2>&1; then
    echo "real vLLM package already available"
    return 0
  fi
  if [[ "${AETHERVILLE_BOOTSTRAP_VLLM:-0}" != "1" ]]; then
    echo "Blocker: AETHERVILLE_VLLM_MODE=real requires vLLM, but it is not installed." >&2
    echo "Set AETHERVILLE_BOOTSTRAP_VLLM=1 to install '$VLLM_INSTALL_PACKAGE' into the uv environment." >&2
    exit 21
  fi
  echo "Installing real vLLM runtime package into uv environment: $VLLM_INSTALL_PACKAGE"
  run_or_print uv pip install "$VLLM_INSTALL_PACKAGE"
  if [[ -n "$VLLM_COMPAT_PACKAGE" ]]; then
    echo "Installing real vLLM compatibility package: $VLLM_COMPAT_PACKAGE"
    run_or_print uv pip install "$VLLM_COMPAT_PACKAGE"
  fi
}

ensure_real_vllm

if [[ "$REDIS_MODE" == "memory" ]]; then
  echo "redis mode: in-memory fallback selected; redis-server will not be started."
elif command -v redis-server >/dev/null 2>&1; then
  start_process redis "redis-server --port '$REDIS_PORT' --bind 0.0.0.0 --protected-mode no"
else
  echo "redis-server not found; using orchestrator in-memory fallback for this demo slice."
  echo "Set AETHERVILLE_REDIS_MODE=memory to make this explicit."
fi

start_process vision "uv run uvicorn aetherville_server.vision:app --host '$HOST' --port '$VISION_PORT'"

if [[ "$VLLM_MODE" == "real" ]]; then
  stop_process_if_running vllm-fallback
  start_process vllm "env -u VLLM_EXTRA_ARGS HF_HOME='${HF_HOME:-$MODEL_CACHE_DIR/hf}' HUGGINGFACE_HUB_CACHE='${HUGGINGFACE_HUB_CACHE:-$MODEL_CACHE_DIR/hf/hub}' uv run python -m vllm.entrypoints.openai.api_server --model '$MODEL_NAME' --host '$HOST' --port '$VLLM_PORT' ${VLLM_EXTRA_ARGS:-}"
else
  stop_process_if_running vllm
  start_process vllm-fallback "uv run uvicorn aetherville_server.vllm_fallback:app --host '$HOST' --port '$VLLM_PORT'"
fi

start_process orchestrator "AETHERVILLE_PROBE_DEPENDENCIES=1 AETHERVILLE_REDIS_MODE='$REDIS_MODE' AETHERVILLE_LLM_MODE='$LLM_MODE' AETHERVILLE_LLM_MODEL='$MODEL_NAME' AETHERVILLE_VISION_URL='http://127.0.0.1:$VISION_PORT' AETHERVILLE_VLLM_URL='http://127.0.0.1:$VLLM_PORT/v1' uv run uvicorn aetherville_server.main:app --host '$HOST' --port '$ORCHESTRATOR_PORT'"

echo "Direct-process start complete. Run: bash infra/runpod/health_check_direct.sh"
