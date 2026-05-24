# Goal 02 — Cloud Services Direct Process Runtime

Compatibility note: this file keeps the historical filename
`02-cloud-services-docker-compose.md` so existing goal links continue to work.
Docker Compose artifacts are future portability/deployment documentation only;
they are not part of current RunPod execution acceptance.

## Objective

Implement the current RunPod cloud services as a direct-process runtime for
vLLM or its OpenAI-compatible fallback, vision, orchestrator, Redis or memory
fallback, and the simulation engine.

The RunPod pod itself is the execution environment. Docker is not required for
the current execution path.

Do not attempt Docker daemon setup, Docker Compose execution,
Docker-in-Docker, or blind Docker retries.

## Scope

- Allowed: `infra/runpod/**`, `server/**` service entrypoints,
  `packages/**` runtime packages, `.env.example`, docs.
- Allowed as portability documentation only: `docker-compose*.yml`,
  `infra/docker/**`, optional `infra/caddy/**`.

## Acceptance criteria

- vLLM has a direct-process script or documented command path. A deterministic
  OpenAI-compatible fallback is acceptable until real model startup is approved.
- FastAPI orchestrator runs via `uvicorn` or an equivalent direct process.
- Vision service runs via `uvicorn` or an equivalent direct process; a
  deterministic stub is acceptable when real YOLO startup is not approved.
- Simulation engine is importable and runnable as a Python package/module.
- Process management is available through shell scripts, tmux, nohup, or
  supervisor-compatible commands.
- Health checks and smoke tests cover vLLM/fallback, vision, orchestrator, and
  Redis/memory fallback without requiring Docker.
- RunPod deployment script can sync the repo and start the direct-process mode.
- Docker Compose artifacts, if present, are clearly marked future portability
  documentation and are not current acceptance gates.

## Verification commands

```bash
bash -n infra/runpod/verify_runpod.sh \
  infra/runpod/deploy_over_ssh.sh \
  infra/runpod/bootstrap_runpod.sh \
  infra/runpod/start_direct_processes.sh \
  infra/runpod/stop_direct_processes.sh \
  infra/runpod/health_check_direct.sh

uv run python -m compileall -q server/src packages/shared-schemas/src/python
uv run pytest server packages
bash infra/runpod/deploy_over_ssh.sh --dry-run --mode direct
# If RunPod direct services are intentionally running:
AETHERVILLE_VISION_PORT=18001 AETHERVILLE_REDIS_MODE=memory \
  bash infra/runpod/health_check_direct.sh
```

Do not run Docker commands for current RunPod acceptance.

## Completion report

Report:

- changed files
- commands run and results
- blockers
- RunPod status if touched
- next goal
