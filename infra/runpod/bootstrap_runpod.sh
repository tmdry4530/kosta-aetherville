#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/../.."

echo "== Aetherville RunPod bootstrap =="
echo "workspace=$(pwd)"

echo "== GPU =="
if command -v nvidia-smi >/dev/null 2>&1; then
  nvidia-smi || true
else
  echo "nvidia-smi not found; GPU runtime may be unavailable."
fi

echo "== Required tools =="
python --version || true
node --version || true
pnpm --version || true
uv --version || true
redis-server --version || true

echo "== Service processes =="
ps -eo pid=,comm= | awk '$2 ~ /^(python|uvicorn|vllm|redis-server|caddy)$/ {print}' || true

echo "== Direct-process runtime policy =="
echo "Docker daemon setup, Docker Compose execution, and Docker-in-Docker are not part of the current RunPod path."
echo "Use direct-process runtime commands:"
cat <<'EOF'
Direct-process commands:
  # Optional when uv is missing and user-level install is acceptable:
  export AETHERVILLE_BOOTSTRAP_UV=1

  # Start mock/fallback services without model download:
  export AETHERVILLE_VLLM_MODE=mock
  export AETHERVILLE_REDIS_MODE=memory
  bash infra/runpod/start_direct_processes.sh
  bash infra/runpod/health_check_direct.sh

  # Stop only processes created by this repo's pid files:
  bash infra/runpod/stop_direct_processes.sh

  # Real vLLM upgrade path after model access is approved:
  export AETHERVILLE_VLLM_MODE=real
  export MODEL_NAME="<approved-model>"
  bash infra/runpod/start_direct_processes.sh
EOF

echo "Bootstrap check complete."
