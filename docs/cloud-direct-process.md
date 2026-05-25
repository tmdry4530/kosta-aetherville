# Cloud Direct-Process Runtime

This document records the non-Docker runtime path required by the current RunPod
pod.

## Services

| Service | Port | Direct command |
|---|---:|---|
| Orchestrator | 8080 | `uv run uvicorn aetherville_server.main:app --host 0.0.0.0 --port 8080` |
| Vision | 18001 verified / 8001 architecture target | `uv run uvicorn aetherville_server.vision:app --host 0.0.0.0 --port "${AETHERVILLE_VISION_PORT:-18001}"` |
| vLLM fallback | 8000 | `uv run uvicorn aetherville_server.vllm_fallback:app --host 0.0.0.0 --port 8000` |
| real vLLM | 8000 | `uv run python -m vllm.entrypoints.openai.api_server --model "$MODEL_NAME" --host 0.0.0.0 --port 8000` |
| Redis | 6379 | `redis-server` when available; otherwise orchestrator memory fallback |

## Health checks

```bash
bash infra/runpod/health_check_direct.sh
```

Equivalent raw checks:

```bash
curl -fsS http://127.0.0.1:8080/api/v1/health
curl -fsS "http://127.0.0.1:${AETHERVILLE_VISION_PORT:-18001}/health"
curl -fsS http://127.0.0.1:8000/v1/models
```

## Real vLLM 4090 path

The default remains the mock OpenAI-compatible fallback. When the operator has
approved 4090 GPU usage, real vLLM can be bootstrapped into the uv environment
and served from the same OpenAI-compatible port:

```bash
export AETHERVILLE_VLLM_MODE=real
export AETHERVILLE_BOOTSTRAP_VLLM=1
export AETHERVILLE_VLLM_INSTALL_PACKAGE="vllm==0.10.2"
export AETHERVILLE_VLLM_COMPAT_PACKAGE="transformers==4.55.4"
export AETHERVILLE_MODEL_CACHE_DIR=/workspace/aetherville-model-cache
export MODEL_NAME=Qwen/Qwen2.5-14B-Instruct-AWQ
export VLLM_EXTRA_ARGS="--gpu-memory-utilization 0.88 --max-model-len 4096"
bash infra/runpod/deploy_over_ssh.sh --mode direct
```

`health_check_direct.sh` accepts any OpenAI-compatible `/v1/models` list when
`AETHERVILLE_VLLM_MODE=real`. Keep model cache under `/workspace` so a process
restart does not force a fresh model download.

## Port override policy

If a RunPod template process already owns one of the default ports, do not kill
that process blindly. Use the direct-process port overrides for smoke testing and
record the exposure blocker:

```bash
export AETHERVILLE_VISION_PORT=18001
bash infra/runpod/start_direct_processes.sh
VISION_URL=http://127.0.0.1:18001 bash infra/runpod/health_check_direct.sh
```

The current verified pod uses `AETHERVILLE_VISION_PORT=18001` because a template
process owns `:8001`. The final public demo should still expose the
architecture-contract ports or document a port-mapping/proxy change explicitly.
