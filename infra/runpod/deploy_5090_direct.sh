#!/usr/bin/env bash
set -euo pipefail

PROFILE="safe-smoke"
SKIP_VERIFY=0
DRY_RUN=0

usage() {
  cat <<'USAGE'
Usage: bash infra/runpod/deploy_5090_direct.sh [--profile safe-smoke|real-demo] [--skip-verify] [--dry-run]

Profiles:
  safe-smoke  Fast 5090 bring-up with mock vLLM/vision/STT. No model download.
  real-demo   Real vLLM + real YOLO + vLLM-backed God Mode/City AI.
              Requires AETHERVILLE_APPROVE_REAL_AI=1 to avoid accidental GPU spend.

Before running:
  1. Fill infra/runpod/.env.runpod for the NEW 5090 pod only.
  2. Do not print or commit .env.runpod.
  3. Do not run Docker; this uses direct-process runtime only.
USAGE
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --profile)
      PROFILE="${2:?--profile requires safe-smoke|real-demo}"
      shift 2
      ;;
    --profile=*)
      PROFILE="${1#--profile=}"
      shift
      ;;
    --skip-verify)
      SKIP_VERIFY=1
      shift
      ;;
    --dry-run)
      DRY_RUN=1
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "Unknown argument: $1" >&2
      usage >&2
      exit 2
      ;;
  esac
done

case "$PROFILE" in
  safe-smoke|real-demo) ;;
  *)
    echo "Invalid profile: $PROFILE" >&2
    usage >&2
    exit 2
    ;;
esac

cd "$(dirname "$0")/../.."

if [[ "$SKIP_VERIFY" != "1" ]]; then
  echo "== 5090 SSH/GPU verification =="
  bash infra/runpod/verify_runpod.sh
fi

export AETHERVILLE_BOOTSTRAP_UV="${AETHERVILLE_BOOTSTRAP_UV:-1}"
export AETHERVILLE_REDIS_MODE="${AETHERVILLE_REDIS_MODE:-memory}"
export AETHERVILLE_RESTART_PROCESSES="${AETHERVILLE_RESTART_PROCESSES:-1}"
export AETHERVILLE_HEALTH_RETRIES="${AETHERVILLE_HEALTH_RETRIES:-60}"
export AETHERVILLE_HEALTH_SLEEP="${AETHERVILLE_HEALTH_SLEEP:-2}"
export AETHERVILLE_VISION_PORT="${AETHERVILLE_VISION_PORT:-18001}"
export AETHERVILLE_ORCHESTRATOR_PORT="${AETHERVILLE_ORCHESTRATOR_PORT:-8080}"
export AETHERVILLE_VLLM_PORT="${AETHERVILLE_VLLM_PORT:-8000}"
export AETHERVILLE_MODEL_CACHE_DIR="${AETHERVILLE_MODEL_CACHE_DIR:-/workspace/aetherville-model-cache}"

if [[ "$PROFILE" == "safe-smoke" ]]; then
  echo "== Deploy profile: safe-smoke =="
  echo "No real model download will be requested."
  export AETHERVILLE_VLLM_MODE="mock"
  export AETHERVILLE_LLM_MODE="cache"
  export AETHERVILLE_VISION_MODE="mock"
  export AETHERVILLE_GOD_MODE_LLM="rules"
  export AETHERVILLE_CITY_AI_MODE="disabled"
  export AETHERVILLE_STT_MODE="stub"
  export AETHERVILLE_BOOTSTRAP_VLLM="0"
  export AETHERVILLE_BOOTSTRAP_YOLO="0"
  export AETHERVILLE_BOOTSTRAP_STT="0"
else
  echo "== Deploy profile: real-demo =="
  if [[ "${AETHERVILLE_APPROVE_REAL_AI:-0}" != "1" ]]; then
    cat >&2 <<'ERR'
Blocker: real-demo can download models and spend GPU time.
Set AETHERVILLE_APPROVE_REAL_AI=1 only when the new 5090 pod is funded and ready.
ERR
    exit 31
  fi
  export AETHERVILLE_VLLM_MODE="real"
  export AETHERVILLE_LLM_MODE="vllm"
  export AETHERVILLE_VISION_MODE="real"
  export AETHERVILLE_GOD_MODE_LLM="vllm"
  export AETHERVILLE_CITY_AI_MODE="vllm"
  export AETHERVILLE_CITY_AI_INTERVAL_TICKS="${AETHERVILLE_CITY_AI_INTERVAL_TICKS:-90}"
  export AETHERVILLE_CITY_AI_LLM_TIMEOUT_SEC="${AETHERVILLE_CITY_AI_LLM_TIMEOUT_SEC:-10}"
  export AETHERVILLE_STT_MODE="${AETHERVILLE_STT_MODE:-stub}"
  export AETHERVILLE_BOOTSTRAP_VLLM="${AETHERVILLE_BOOTSTRAP_VLLM:-1}"
  export AETHERVILLE_BOOTSTRAP_YOLO="${AETHERVILLE_BOOTSTRAP_YOLO:-1}"
  export AETHERVILLE_BOOTSTRAP_STT="${AETHERVILLE_BOOTSTRAP_STT:-0}"
  export MODEL_NAME="${MODEL_NAME:-Qwen/Qwen2.5-14B-Instruct-AWQ}"
  export VLLM_GPU_MEMORY_UTILIZATION="${VLLM_GPU_MEMORY_UTILIZATION:-0.90}"
  export VLLM_MAX_MODEL_LEN="${VLLM_MAX_MODEL_LEN:-8192}"
  export VLLM_EXTRA_ARGS="${VLLM_EXTRA_ARGS:---gpu-memory-utilization $VLLM_GPU_MEMORY_UTILIZATION --max-model-len $VLLM_MAX_MODEL_LEN}"
fi

DEPLOY_ARGS=(--mode direct)
if [[ "$DRY_RUN" == "1" ]]; then
  DEPLOY_ARGS=(--dry-run --mode direct)
fi

bash infra/runpod/deploy_over_ssh.sh "${DEPLOY_ARGS[@]}"
