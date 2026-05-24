# Cloud Direct-Process Runtime

This document records the non-Docker runtime path required by the current RunPod
pod.

## Services

| Service | Port | Direct command |
|---|---:|---|
| Orchestrator | 8080 | `uv run uvicorn aetherville_server.main:app --host 0.0.0.0 --port 8080` |
| Vision | 8001 | `uv run uvicorn aetherville_server.vision:app --host 0.0.0.0 --port 8001` |
| vLLM fallback | 8000 | `uv run uvicorn aetherville_server.vllm_fallback:app --host 0.0.0.0 --port 8000` |
| Redis | 6379 | `redis-server` when available; otherwise orchestrator memory fallback |

## Health checks

```bash
bash infra/runpod/health_check_direct.sh
```

Equivalent raw checks:

```bash
curl -fsS http://127.0.0.1:8080/api/v1/health
curl -fsS http://127.0.0.1:8001/health
curl -fsS http://127.0.0.1:8000/v1/models
```

## Real vLLM upgrade path

The default is the mock OpenAI-compatible fallback to avoid accidental model
downloads and GPU spend. Real vLLM is opt-in:

```bash
export AETHERVILLE_VLLM_MODE=real
export MODEL_NAME="<approved-model>"
bash infra/runpod/start_direct_processes.sh
```

Do not set real mode until model access, disk space, and expected GPU cost are
confirmed.

## Port override policy

If a RunPod template process already owns one of the default ports, do not kill
that process blindly. Use the direct-process port overrides for smoke testing and
record the exposure blocker:

```bash
export AETHERVILLE_VISION_PORT=18001
bash infra/runpod/start_direct_processes.sh
VISION_URL=http://127.0.0.1:18001 bash infra/runpod/health_check_direct.sh
```

The final public demo should still expose the architecture-contract ports or
document a port-mapping/proxy change explicitly.
