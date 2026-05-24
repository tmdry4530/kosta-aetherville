# RunPod SSH Deployment Guide for Codex

## Objective

Set up the cloud backend on the user's rented RunPod instance by SSH. Do not ask for credentials inside chat; read them from `infra/runpod/.env.runpod` or environment variables.

## Required local setup

1. Copy env file:

```bash
cp infra/runpod/.env.runpod.example infra/runpod/.env.runpod
```

2. Fill:

```bash
RUNPOD_HOST=
RUNPOD_SSH_PORT=
RUNPOD_USER=root
RUNPOD_SSH_KEY=/absolute/path/to/private_key
RUNPOD_REMOTE_DIR=/workspace/aetherville
```

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
- Docker daemon availability
- exposed service ports if URLs are provided

## Deployment modes

### Mode A — Docker Compose

Use when remote `docker info` succeeds.

```bash
bash infra/runpod/deploy_over_ssh.sh
```

Remote command should eventually run:

```bash
cd "$RUNPOD_REMOTE_DIR"
docker compose -f docker-compose.yml -f docker-compose.cloud.yml up -d --build
```

### Mode B — direct process fallback

### Direct-process scripts now provided

For the current RunPod pod, Docker is unavailable. Use the direct-process scripts
below after the repository is synced:

```bash
# Starts orchestrator :8080, vision :8001, and mock vLLM-compatible fallback :8000.
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

The real vLLM upgrade path is intentionally opt-in to avoid accidental model
downloads/GPU spend:

```bash
export AETHERVILLE_VLLM_MODE=real
export MODEL_NAME="<approved-model>"
bash infra/runpod/start_direct_processes.sh
```


Use when Docker daemon is unavailable.

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
uv run uvicorn aetherville_server.vision:app --host 0.0.0.0 --port 8001
uv run uvicorn aetherville_server.main:app --host 0.0.0.0 --port 8080
```

The current implementation uses repo-managed pid files under `AETHERVILLE_RUN_DIR` instead of deleting or altering system services.

For M0, Docker unavailability is not by itself a hard blocker if SSH and GPU
checks pass. Record it as the deployment-mode decision, use direct processes for
the next cloud-services goal, and avoid blind Docker retries.

## Health checks

Inside RunPod:

```bash
curl -fsS http://127.0.0.1:8080/api/v1/health
curl -fsS http://127.0.0.1:8001/health
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
