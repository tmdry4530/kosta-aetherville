# project/TEST_PLAN.md — Aetherville Verification Contract

## Release gate levels

### Gate A — M0 Foundation

Required:

- Repo installs with `uv sync` and `pnpm install`.
- Shared schema package builds.
- Orchestrator `/api/v1/health` returns all service statuses.
- WebSocket client receives at least 10 sequential ticks.
- RunPod SSH check passes or blocker is documented.
- `project/TASKS.json`, `project/PROGRESS.md`, `project/SESSION_HANDOFF.md` updated.

### Gate B — Playable local/cloud slice

Required:

- RunPod vLLM endpoint passes Korean prompt smoke test or documented fallback is active.
- Vision service returns mock or real detections with schema-compliant payload.
- Browser renders city scene and displays connection status.
- God Mode text command changes world weather via REST and WebSocket update.

### Gate C — Course/demo quality

Required:

- Citizen memory stream visible.
- Vehicle camera panel displays YOLO/mock boxes.
- Traffic chart panel displays actual + forecast/mock data.
- Demo script can run 15 minutes with fallback replay.
- Evaluation metrics report generated.

## Required verification commands

Python:

```bash
uv run ruff check server packages scripts
uv run mypy server packages
uv run pytest
```

TypeScript:

```bash
pnpm lint
pnpm typecheck
pnpm test
```

Docker/RunPod:

```bash
bash infra/runpod/verify_runpod.sh
bash infra/runpod/deploy_over_ssh.sh --dry-run
ssh "$RUNPOD_USER@$RUNPOD_HOST" -p "$RUNPOD_SSH_PORT" "nvidia-smi"
```

Health:

```bash
curl -fsS "$ORCHESTRATOR_URL/api/v1/health"
curl -fsS "$VISION_URL/health"
curl -fsS "$VLLM_URL/models"
```

## Test matrix

| Area | Test type | Examples |
|---|---|---|
| Shared schemas | unit/contract | envelope parse, state_update parse, command parse |
| Orchestrator | unit/integration | tick scheduler, broadcaster, command handler |
| Sim engine | unit | time/weather/event, A* path, AABB collision |
| Citizens | unit/integration | memory retrieval score, plan tree, reflection trigger |
| Vehicles | unit/sim | path following, braking on pedestrian/red light detection |
| Vision | service/contract | base64 frame input, detection output, health |
| Traffic AI | unit/training smoke | env step/reset, PPO wrapper load, LSTM predictor output |
| Client | component/e2e | socket connect, panels, city scene render, God Mode text |
| RunPod | smoke | ssh, gpu, service ports, model cache |

## Never mark complete when

- A service starts only locally but not on RunPod for a cloud backend goal.
- A test was skipped without reason.
- Schema changed in Python but TypeScript output was not regenerated.
- Docker path fails and no direct-process fallback or blocker report exists.
- RunPod credentials are exposed in a log, commit, or report.
