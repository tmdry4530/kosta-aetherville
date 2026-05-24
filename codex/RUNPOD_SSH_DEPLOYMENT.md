# RunPod SSH Deployment Guide for Codex

## Objective

Set up the cloud backend on the user's rented RunPod instance by SSH. Do not ask for credentials inside chat; read them from `infra/runpod/.env.runpod` or environment variables.

## Required local setup

1. Copy env file:

```bash
cp infra/runpod/.env.runpod.example infra/runpod/.env.runpod
```

2. Fill the required SSH variables listed in
   `infra/runpod/.env.runpod.example` using only the local ignored
   `.env.runpod` file or process environment. Do not copy actual values into
   tracked docs, chat, logs, or commits.

3. Ensure `.env.runpod` is ignored.

The repository keeps this local file out of source control with
`infra/runpod/.gitignore`. Do not copy secrets into tracked docs, command
examples, or completion reports.

## First diagnostics

Codex should run:

```bash
bash infra/runpod/verify_runpod.sh
```

This checks:

- SSH connection
- GPU via `nvidia-smi`
- workspace path
- Python
- Node/pnpm if available
- currently running service process names without command-line arguments
- no-Docker direct-process policy
- exposed service ports if URLs are provided

## Deployment modes

### Current mode — direct process runtime

For the current RunPod pod, Docker is unavailable and is not required. The pod
itself is the execution environment. Do not attempt Docker daemon setup,
Docker Compose execution, Docker-in-Docker, or blind Docker retries. Use the
direct-process scripts below after the repository is synced:

```bash
# Starts orchestrator :8080, vision, and mock vLLM-compatible fallback :8000.
# Redis uses memory fallback unless redis-server is installed.
export AETHERVILLE_VLLM_MODE=mock
export AETHERVILLE_REDIS_MODE=memory
bash infra/runpod/start_direct_processes.sh
bash infra/runpod/health_check_direct.sh
```

If `uv` is missing on the pod and a user-level install is acceptable:

```bash
export AETHERVILLE_BOOTSTRAP_UV=1
bash infra/runpod/start_direct_processes.sh
```

Stop only the processes created by this repo's pid files:

```bash
bash infra/runpod/stop_direct_processes.sh
```

Deploy script modes:

```bash
bash infra/runpod/deploy_over_ssh.sh --dry-run --mode direct
bash infra/runpod/deploy_over_ssh.sh --mode sync-only
bash infra/runpod/deploy_over_ssh.sh --mode direct
```

### Future portability — Docker Compose artifacts

Docker Compose files may remain in the repository as portability/deployment
documentation for a different Docker-capable target. They are not an active
execution dependency for the verified RunPod pod, and current Codex automation
must not run Docker or Docker Compose.

The real vLLM upgrade path is intentionally opt-in to avoid accidental model
downloads/GPU spend:

```bash
export AETHERVILLE_VLLM_MODE=real
export MODEL_NAME="<approved-model>"
bash infra/runpod/start_direct_processes.sh
```


Codex must create or document process supervisors for:

- Redis availability or in-memory fallback for M0
- vLLM direct process
- Vision FastAPI process
- Orchestrator FastAPI/Socket.IO process

Implemented process pattern:

```bash
# Real vLLM, opt-in only after model access/cost approval
uv run python -m vllm.entrypoints.openai.api_server \
  --model "$MODEL_NAME" \
  --host 0.0.0.0 \
  --port 8000

# Default mock/fallback services used for safe smoke tests
uv run uvicorn aetherville_server.vllm_fallback:app --host 0.0.0.0 --port 8000
uv run uvicorn aetherville_server.vision:app --host 0.0.0.0 --port "${AETHERVILLE_VISION_PORT:-18001}"
uv run uvicorn aetherville_server.main:app --host 0.0.0.0 --port 8080
```

The current implementation uses repo-managed pid files under `AETHERVILLE_RUN_DIR` instead of deleting or altering system services.

For M0 and later cloud milestones, Docker unavailability is not a hard blocker
when SSH and GPU checks pass. Record direct-process runtime as the deployment
decision and avoid Docker daemon setup, Docker Compose execution,
Docker-in-Docker, or blind Docker retries.

## Health checks

Inside RunPod:

```bash
curl -fsS http://127.0.0.1:8080/api/v1/health
curl -fsS "http://127.0.0.1:${AETHERVILLE_VISION_PORT:-18001}/health"
curl -fsS http://127.0.0.1:8000/v1/models
```

From local machine, use RunPod exposed URLs/ports:

```bash
curl -fsS "$RUNPOD_PUBLIC_ORCHESTRATOR_URL/api/v1/health"
```

## Security

- Do not print tokens.
- Use SSH keys only through `RUNPOD_SSH_KEY`.
- Do not use `StrictHostKeyChecking=no` unless the user explicitly accepts that trade-off.
- Never run recursive deletion on remote workspace unless user explicitly approves.

## Completion criteria

- SSH works.
- GPU visible.
- Deployment mode selected and documented.
- At least orchestrator health works remotely or blocker is documented.
- Next RunPod command is clear.
