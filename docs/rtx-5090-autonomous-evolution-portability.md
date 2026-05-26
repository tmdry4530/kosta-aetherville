# RTX 5090 Portability — Autonomous City Evolution Goals 13–17

This note describes how to move the current Aetherville autonomous-city branch to a future 5090 machine without relying on Docker.

## Restore source

```bash
git clone <repo-url> kosta-aetherville
cd kosta-aetherville
# or unpack the local backup tarball created under .omx/backups/
```

Final verified backup:

```text
.omx/backups/aetherville-goals13-17-autonomous-city-20260526-101816.tar.gz
sha256: a628885b3b6729114069a6d8c5040584147f5aa100d57abf9e02a79fc03cbe1c
```

The final backup for this goal excludes `.git/`, `.omx/`, `.env*`, `infra/runpod/.env.runpod`, dependency folders, caches, and dogfood output. Recreate credentials from the secure source only.

## Install dependencies

```bash
uv sync
pnpm install
```

## Start direct-process services

For a local 5090 smoke without real model downloads:

```bash
AETHERVILLE_REDIS_MODE=memory \
AETHERVILLE_STT_MODE=stub \
AETHERVILLE_CITY_AI_MODE=rules \
AETHERVILLE_VLLM_MODE=mock \
AETHERVILLE_RUN_DIR=/tmp/aetherville-5090 \
uv run uvicorn aetherville_server.main:app --host 127.0.0.1 --port 18080
```

For real vLLM/YOLO/STT, enable the existing opt-in env vars only after model/cache paths and tokens are configured outside the repo. Do not commit env files.

## Verify autonomous-city features

```bash
uv run pytest packages/shared-schemas/tests server/sim -q
uv run ruff check server packages scripts
uv run mypy server packages
pnpm lint
pnpm typecheck
pnpm test
python3 scripts/replanner_resilience_smoke.py --orchestrator-url http://127.0.0.1:18080 --wait-seconds 60
python3 scripts/learning_evolution_smoke.py --orchestrator-url http://127.0.0.1:18080 --repeat 2
python3 scripts/autonomous_city_dogfood_smoke.py --orchestrator-url http://127.0.0.1:18080 --wait-seconds 12
```

## Start browser

```bash
NEXT_PUBLIC_ORCHESTRATOR_URL=http://127.0.0.1:18080 \
NEXT_PUBLIC_SOCKET_URL=http://127.0.0.1:18080 \
NEXT_PUBLIC_SOCKET_TRANSPORTS=polling \
pnpm --filter @aetherville/client exec next dev -H 0.0.0.0 -p 3000
```

Then open `http://127.0.0.1:3000/` and `http://127.0.0.1:3000/replay`.

## What can be claimed

- Entity brains explain current goals/reasons for citizens, taxi/vehicles, drones, and traffic lights.
- Bounded replanner detects/reports/replans synthetic blocker classes and keeps demo flow moving.
- Learning/evolution persists JSON-backed experience and policy-bias signals.
- UI exposes TaskGraph, entity intent, replan feed, causal chain, RunPod proof, and truthful learning status.

Do **not** claim model-weight self-training unless a separate training job and checkpoint promotion path is implemented and verified.
