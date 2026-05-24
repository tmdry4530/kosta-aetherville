# PROGRESS.md

## Current objective

- Active master goal: complete; post-audit continuation uses direct-process runtime only for cloud milestones.
- Current phase state: **Phase 99 Final Audit complete** as of 2026-05-24T21:57:21+09:00.
- Current follow-up: patch goal/status documents so verified RunPod execution strategy is explicitly direct-process runtime, not Docker-first.

## Phase 00 — RunPod SSH Bootstrap

- Status: complete.
- RunPod SSH connectivity: passed.
- GPU visibility: passed; pod reports NVIDIA GeForce RTX 4090.
- Docker daemon: unavailable; do not blind retry Docker.
- Deployment mode: direct-process runtime.
- Runtime inventory from prior verification: Python 3.11.10 present; node, pnpm, uv, and redis-server missing on pod.
- Remote workspace: absent during dry-run; actual deploy script is responsible for creating it.
- No vLLM/model download/GPU workload has been started.

## Phase 01 — Foundation Monorepo

- Status: complete.
- Added root pnpm workspace, root uv workspace, `.env.example`, and root `.gitignore` for generated artifacts/secrets.
- Added `packages/shared-schemas` as the Pydantic source-of-truth package:
  - envelope types: `state_update`, `state_diff`, `event`, `command`, `ack`, `error`
  - world state/entity models for citizens, vehicles, drones, traffic lights, forecast points, YOLO detections
  - God Mode/select entity/sim control command models
  - REST health response models
  - valid fixture tests and invalid-envelope rejection test
- Added generated TypeScript contract surface at `packages/shared-schemas/src/typescript/index.ts` plus generator script.
- Added FastAPI + Socket.IO orchestrator skeleton under `server/`:
  - `/api/v1/health`
  - `/health`
  - Socket.IO connect ack skeleton using shared envelope schema
- Added Next.js App Router client under `client/`:
  - R3F placeholder city scene
  - endpoint configuration from `NEXT_PUBLIC_ORCHESTRATOR_URL` / `NEXT_PUBLIC_SOCKET_URL`
  - Zustand connection store and coordinate conversion stub
  - basic Node test runner wiring

## Verification evidence — Phase 01

- pass: `python3 packages/shared-schemas/scripts/generate_typescript.py`
- pass: `uv sync`
- pass: `uv run python -m compileall -q packages/shared-schemas/src/python server/src`
- pass: `uv run pytest` — 7 tests passed
- pass: `uv run ruff check server packages`
- pass: `uv run mypy server packages`
- pass: local orchestrator smoke via `uv run uvicorn aetherville_server.main:app --host 127.0.0.1 --port 18080` and `curl -fsS http://127.0.0.1:18080/api/v1/health`
- pass: `pnpm install`
- pass: `pnpm lint`
- pass: `pnpm typecheck`
- pass: `pnpm test` — 1 Node test passed
- pass: `pnpm build` — Next.js static page build completed

## Warnings / residual risks

- `pnpm install` reported ignored build scripts for `unrs-resolver`; lint/typecheck/test/build still passed.
- The vision/vLLM/Redis dependency statuses in orchestrator health are placeholders for Phase 02 and later.
- Socket.IO currently emits only a connect ack; tick/state broadcast lands in later schema/simulation phases.
- RunPod was not touched during Phase 01; previous verified state remains authoritative.

## Files changed in Phase 01

- `.env.example`
- `.gitignore`
- `package.json`
- `pnpm-lock.yaml`
- `pnpm-workspace.yaml`
- `pyproject.toml`
- `uv.lock`
- `packages/shared-schemas/package.json`
- `packages/shared-schemas/pyproject.toml`
- `packages/shared-schemas/scripts/generate_typescript.py`
- `packages/shared-schemas/src/python/aetherville_schemas/__init__.py`
- `packages/shared-schemas/src/python/aetherville_schemas/models.py`
- `packages/shared-schemas/src/python/aetherville_schemas/py.typed`
- `packages/shared-schemas/src/typescript/index.ts`
- `packages/shared-schemas/tests/fixtures/state_update.json`
- `packages/shared-schemas/tests/test_models.py`
- `packages/shared-schemas/tests/test_typescript_output.py`
- `server/pyproject.toml`
- `server/src/aetherville_server/__init__.py`
- `server/src/aetherville_server/main.py`
- `server/tests/test_health.py`
- `client/package.json`
- `client/next-env.d.ts`
- `client/next.config.mjs`
- `client/tsconfig.json`
- `client/.eslintrc.json`
- `client/src/app/globals.css`
- `client/src/app/layout.tsx`
- `client/src/app/page.tsx`
- `client/src/components/CityPlaceholder.tsx`
- `client/src/lib/config.ts`
- `client/src/lib/coords.ts`
- `client/src/store/connection.ts`
- `client/tests/config.test.mjs`
- `TASKS.json`
- `PROGRESS.md`
- `SESSION_HANDOFF.md`
- `DECISIONS.md`


## Phase 02 — Cloud Services Direct Process Runtime

- Status: complete as of 2026-05-24T20:16:05+09:00.
- Goal 02 is treated as **Cloud Services Direct Process Runtime** while retaining filename compatibility with `.codex/goals/02-cloud-services-docker-compose.md`.
- Current acceptance does not require Docker execution.
- Docker/Compose artifacts are retained only for future Docker-capable portability documentation:
  - `docker-compose.yml`
  - `docker-compose.cloud.yml`
  - `infra/docker/server.Dockerfile`
  - optional `infra/caddy/Caddyfile`
- Added direct-process service scripts:
  - `infra/runpod/start_direct_processes.sh`
  - `infra/runpod/health_check_direct.sh`
  - `infra/runpod/stop_direct_processes.sh`
- Extended `infra/runpod/deploy_over_ssh.sh` with `--mode bootstrap|sync-only|direct|compose` and tar-over-SSH fallback when remote `rsync` is missing.
- Added service entrypoints:
  - `aetherville_server.vision:app` with `/health` and mock `/detect`
  - `aetherville_server.vllm_fallback:app` with `/health`, `/v1/models`, and `/v1/chat/completions`
- Updated orchestrator health to probe direct-process vision/vLLM dependencies when `AETHERVILLE_PROBE_DEPENDENCIES=1`.

## Verification evidence — Phase 02

- pass: `bash -n infra/runpod/verify_runpod.sh infra/runpod/deploy_over_ssh.sh infra/runpod/bootstrap_runpod.sh infra/runpod/start_direct_processes.sh infra/runpod/stop_direct_processes.sh infra/runpod/health_check_direct.sh`
- pass: `uv run python -m compileall -q server/src packages/shared-schemas/src/python`
- pass: `uv run pytest` — 11 tests passed
- pass: `uv run ruff check server packages`
- pass: `uv run mypy server packages`
- not current acceptance: Docker Compose config validation is portability-only and must not be required for the verified RunPod path.
- pass: local direct-process smoke with mock vLLM, vision, orchestrator, Redis memory fallback
- pass: `bash infra/runpod/verify_runpod.sh` after deployment; SSH/GPU still pass and Docker remains unavailable
- pass: `bash infra/runpod/deploy_over_ssh.sh --dry-run --mode direct`; remote `rsync` missing, tar-over-SSH fallback selected
- pass: actual RunPod direct deploy/start with `AETHERVILLE_BOOTSTRAP_UV=1 AETHERVILLE_VLLM_MODE=mock AETHERVILLE_REDIS_MODE=memory AETHERVILLE_VISION_PORT=18001 bash infra/runpod/deploy_over_ssh.sh --mode direct`
- pass: remote direct health check with `AETHERVILLE_VISION_PORT=18001 AETHERVILLE_REDIS_MODE=memory bash infra/runpod/health_check_direct.sh`
- pass: `pnpm lint`, `pnpm typecheck`, `pnpm test` after Phase 02 changes

## RunPod state — Phase 02

- Remote workspace exists and has the repo synced through tar-over-SSH fallback because remote `rsync` is unavailable.
- User-level `uv` was installed on the pod through `python -m pip install --user uv`; no Docker install or system cleanup was attempted.
- The RunPod pod itself is the execution environment; Docker is not required for the current service path.
- Running direct-process services:
  - orchestrator: `:8080`
  - vLLM OpenAI-compatible mock fallback: `:8000`
  - vision mock service: `:18001`
- Port `:8001` is currently occupied by a template `nginx` process on the pod, so the vision service uses internal fallback port `18001` for smoke tests. This is a residual port-exposure risk for the final architecture contract and must be resolved or explicitly proxied before public demo.
- Redis binary is missing; `AETHERVILLE_REDIS_MODE=memory` is the active fallback.
- No real vLLM model download, training job, or GPU inference workload was started; `nvidia-smi` shows no compute process.

## Phase 02 warnings / residual risks

- RunPod public URL envs are not configured, so only in-pod/local SSH health checks were verified.
- Real vLLM remains opt-in and requires model access/disk/cost confirmation.
- Vision default architecture port `8001` is blocked by pod nginx; direct-process runtime uses `18001` until port mapping/proxy is resolved.
- Remote `rsync` is missing; tar-over-SSH sync does not delete stale remote files.


## Phase 03 — Shared Schemas, REST, WebSocket

- Status: complete as of 2026-05-24T20:29:22+09:00.
- Expanded Pydantic contracts and regenerated TypeScript output:
  - `EventPayload`, `AckPayload`, `ErrorPayload`
  - `SimStatusResponse`
  - `GodCommandResponse`
  - `Envelope<TPayload = unknown>` for generated client payload typing
- Added fixtures/tests for `state_update`, `event`, `command`, `ack`, and `error` envelopes.
- Added orchestrator REST endpoints using shared response/request models:
  - `GET /api/v1/health`
  - `GET /api/v1/sim/status`
  - `POST /api/v1/god/command`
- Added Socket.IO contract behavior:
  - connect emits `aetherville:ack`
  - connect emits `aetherville:state_update`
  - command envelope emits `aetherville:event`
- Added client WebSocket bridge under `client/src/ws/` and a client connection status bridge that consumes generated shared types.

## Verification evidence — Phase 03

- pass: `python3 packages/shared-schemas/scripts/generate_typescript.py`
- pass: `uv run pytest packages server` — 19 tests passed
- pass: `uv run ruff check server packages`
- pass: `uv run mypy server packages`
- pass: `pnpm test` — 2 Node tests passed
- pass: `pnpm typecheck`
- pass: `pnpm lint`
- pass: `pnpm build`
- pass: RunPod read-only verification before redeploy; SSH/GPU still pass, Docker unavailable
- pass: RunPod direct redeploy/restart with mock vLLM, Redis memory fallback, and vision `18001`
- pass: RunPod REST smoke for `/api/v1/sim/status` and `/api/v1/god/command`
- pass: RunPod Socket.IO polling smoke received `aetherville:state_update`

## RunPod state — Phase 03

- Services were restarted with the Phase 03 code.
- Current in-pod direct health remains green for orchestrator, vLLM fallback, vision on `18001`, and Redis memory fallback.
- No real vLLM model download, training, or GPU inference workload was started.
- `:8001` remains occupied by template nginx; vision continues on `:18001` until proxy/port mapping is resolved.


## Phase 04 — Simulation Engine Minimal Slice

- Status: complete as of 2026-05-24T20:39:15+09:00.
- Replaced the static demo state helper with `aetherville_server.sim.SimulationEngine`.
- Added deterministic world tick state with:
  - time/weather/temperature
  - citizens
  - vehicles
  - drones
  - traffic lights
  - traffic forecast
  - event timeline
- Added REST simulation endpoints:
  - `GET /api/v1/sim/status`
  - `GET /api/v1/sim/state`
  - `POST /api/v1/sim/start`
  - `POST /api/v1/sim/stop`
  - `POST /api/v1/sim/reset`
  - `GET /api/v1/timeline`
- Added configurable async broadcast loop via `AETHERVILLE_TICK_RATE_HZ`.
- Socket.IO now broadcasts `aetherville:state_update` while the simulation is running.

## Verification evidence — Phase 04

- pass: `python3 packages/shared-schemas/scripts/generate_typescript.py`
- pass: `uv run pytest packages server` — 24 tests passed
- pass: `uv run ruff check server packages`
- pass: `uv run mypy server packages`
- pass: `pnpm test` — 2 Node tests passed
- pass: `pnpm typecheck`
- pass: `pnpm lint`
- pass: RunPod read-only verification before redeploy; SSH/GPU still pass, Docker unavailable
- pass: RunPod direct redeploy/restart with mock vLLM, Redis memory fallback, and vision `18001`
- pass: RunPod simulation Socket.IO polling smoke received 10 sequential state_update ticks `[1..10]`

## RunPod state — Phase 04

- Services were restarted with the Phase 04 simulation engine code.
- `GET /api/v1/health` reports simulation status `ok` and the deterministic tick rate.
- Current direct-process services remain orchestrator `:8080`, vLLM fallback `:8000`, vision `:18001`, Redis memory fallback.
- No real vLLM model download, training, or GPU inference workload was started.
- `:8001` remains occupied by template nginx; vision continues on `:18001` until proxy/port mapping is resolved.

## Next recommended goal

- `.codex/goals/05-client-city-scene.md`

## Phase 05 — Client City Scene

- Status: complete as of 2026-05-24T20:50:11+09:00.
- Upgraded the browser shell from a static placeholder into a live/mock-compatible city cockpit:
  - R3F scene renders roads, buildings, citizens, vehicles, drones, and traffic lights from `WorldStatePayload`.
  - Connection status, tick, and weather are visible in the scene and fixed connection card.
  - Side panels now exist for memory stream, vehicle camera, traffic forecast chart, and God Mode macro placeholders.
  - `/replay` route exists and drives deterministic fallback state without requiring RunPod connectivity.
- Kept client state contract aligned with generated shared schemas; no schema source change was required.

## Verification evidence — Phase 05

- pass: `pnpm typecheck`
- pass: `pnpm lint`
- pass: `pnpm test` — 2 Node tests passed
- pass: `pnpm --filter @aetherville/client build` — `/` and `/replay` static routes built successfully

## RunPod state — Phase 05

- RunPod was not touched during Phase 05 client-only work.
- Existing known state remains: direct-process runtime only, Docker daemon unavailable, orchestrator `:8080`, vLLM fallback `:8000`, vision `:18001`, Redis memory fallback.
- No real vLLM model download, training, or GPU inference workload was started.

## Next recommended goal

- `.codex/goals/06-citizen-agents.md`

## Phase 06 — Citizen Agents Minimal Slice

- Status: complete as of 2026-05-24T21:00:54+09:00.
- Added deterministic citizen agent interfaces:
  - 20 `CitizenPersona` fixtures generated from a seed.
  - Cached daily `PlanNode` tree per citizen.
  - In-memory `MemoryRecord` stream with retrieval scores based on importance plus query overlap.
  - Dialogue and reflection response models with `aetherville:event` envelopes.
- Added event-driven/cached LLM facade:
  - `CachedLLMPlanner.daily_plan()` and `reflect()` cache by event key.
  - No LLM path is called from the simulation tick loop.
- Integrated citizen agents into the simulation snapshot and REST API:
  - `GET /api/v1/citizens`
  - `GET /api/v1/citizens/{id}`
  - `GET /api/v1/citizens/{id}/memories?query=`
  - `POST /api/v1/citizens/{id}/dialogue`
  - `POST /api/v1/citizens/{id}/reflect`
- Client memory panel now lives under `client/src/ui/MemoryPanel.tsx` and uses generated `MemoryRecord` types.
- Updated API contract docs and ADR-008 for cached/event-driven LLM behavior.

## Verification evidence — Phase 06

- pass: `python3 packages/shared-schemas/scripts/generate_typescript.py`
- pass: `uv run pytest server/agents server/llm packages` — 16 tests passed
- pass: `uv run ruff check server packages`
- pass: `uv run mypy server packages`
- pass: `uv run pytest packages server` — 32 tests passed
- pass: `pnpm test` — 2 Node tests passed
- pass: `pnpm typecheck`
- pass: `pnpm lint`
- pass: `pnpm --filter @aetherville/client build` — `/` and `/replay` static routes built successfully

## RunPod state — Phase 06

- RunPod was not touched during Phase 06 code work.
- Existing known state remains: direct-process runtime only, Docker daemon unavailable, orchestrator `:8080`, vLLM fallback `:8000`, vision `:18001`, Redis memory fallback.
- No real vLLM model download, training, or GPU inference workload was started.

## Next recommended goal

- `.codex/goals/07-vehicles-vision.md`

## Phase 07 — Vehicles and Vision

- Status: complete as of 2026-05-24T21:13:21+09:00.
- Added vehicle/vision contracts to shared schemas and regenerated TypeScript:
  - `VisionDetectRequest`
  - `VisionDetectResponse`
  - `VehicleCameraFrame`
  - `TripState`
- Added deterministic vehicle control:
  - A* grid pathfinding.
  - `VehicleController` follows a demo path and loops the route.
  - `TripManager` assigns a demo trip to `v01`.
  - Vehicle speed slows for mock pedestrian or red-light detections.
  - Simulation timeline can emit `collision_avoided` demo events.
- Updated vision service `/detect` to return schema-valid deterministic mock detections through shared models.
- Added orchestrator camera endpoint: `GET /api/v1/vehicles/{vehicle_id}/camera`.
- Added `client/src/ui/VehicleCamPanel.tsx` with detection box overlays.
- Added `docs/vision-yolo-upgrade.md` documenting the real YOLO upgrade path and GPU cost gates.

## Verification evidence — Phase 07

- pass: `python3 packages/shared-schemas/scripts/generate_typescript.py`
- pass: `uv run pytest server/vehicles server/vision packages` — 18 tests passed
- pass: `uv run ruff check server packages`
- pass: `uv run mypy server packages`
- pass: `uv run pytest packages server` — 40 tests passed
- pass: `pnpm test` — 2 Node tests passed
- pass: `pnpm typecheck`
- pass: `pnpm lint`
- pass: `pnpm --filter @aetherville/client build` — `/` and `/replay` static routes built successfully
- pass: `bash infra/runpod/verify_runpod.sh` before redeploy; SSH/GPU still pass, Docker unavailable, no GPU compute process
- pass: RunPod direct-process sync and repo-managed process restart with mock vLLM, Redis memory fallback, and vision `18001`
- pass: RunPod direct health check for orchestrator, vision, vLLM fallback, and Redis memory fallback
- pass: RunPod Phase 07 smoke: `/api/v1/sim/state` vehicle detections, `/api/v1/vehicles/v01/camera`, and vision `/detect` returned schema-compatible detections

## RunPod state — Phase 07

- RunPod was synced and repo-managed direct processes were restarted after the code update.
- Current direct-process services:
  - orchestrator `:8080`
  - vLLM fallback `:8000`
  - vision `:18001`
  - Redis memory fallback
- Docker daemon remains unavailable; no Docker retry was attempted beyond the required read-only verification.
- No real YOLO weights, model downloads, training jobs, or GPU inference workloads were started; `nvidia-smi` showed no compute processes before deploy.
- `:8001` remains occupied by template nginx, so vision continues on internal fallback port `18001` until proxy/port mapping is resolved.

## Next recommended goal

- `.codex/goals/08-traffic-ai.md`

## Phase 08 — Traffic AI

- Status: complete as of 2026-05-24T21:27:19+09:00.
- Added `aetherville_server.traffic_ai` module:
  - `FixedCycleController` baseline for north/south and east/west lights.
  - `TrafficSignalEnv` reset/step abstraction for PPO-compatible tests.
  - `TrafficPolicyWrapper` that loads a JSON checkpoint if present and falls back to baseline pressure control.
  - `LstmForecastWrapper` deterministic fallback forecast facade.
  - `traffic_ai.metrics.compare_policies()` comparison metrics script path.
- Integrated traffic AI into simulation snapshots:
  - traffic lights now include `tl_ns` and `tl_ew`.
  - forecast payload includes 5/10/15 minute `TrafficForecastPoint` values.
- Added `client/src/ui/TrafficChartPanel.tsx` and wired the side panel to the generated forecast payload.
- Added `docs/traffic-ai.md` for PPO/LSTM upgrade path and cost gates.

## Verification evidence — Phase 08

- pass: `uv run pytest server/traffic_ai server/sim packages` — 18 tests passed
- pass: `uv run ruff check server packages`
- pass: `uv run mypy server packages`
- pass: `uv run pytest packages server` — 46 tests passed
- pass: `pnpm test` — 2 Node tests passed
- pass: `pnpm typecheck`
- pass: `pnpm lint`
- pass: `pnpm --filter @aetherville/client build` — `/` and `/replay` static routes built successfully
- pass: `bash infra/runpod/verify_runpod.sh` before redeploy; SSH/GPU still pass, Docker unavailable, no GPU compute process
- pass: RunPod sync-only deploy, repo-managed direct-process restart, and direct health check
- pass: RunPod Phase 08 smoke: `/api/v1/sim/state` returned `tl_ns`, `tl_ew`, and forecast minutes `5,10,15`

## RunPod state — Phase 08

- RunPod was synced and repo-managed direct processes were restarted after the code update.
- Current direct-process services:
  - orchestrator `:8080`
  - vLLM fallback `:8000`
  - vision `:18001`
  - Redis memory fallback
- Docker daemon remains unavailable; no Docker retry was attempted beyond the required read-only verification.
- No PPO training, LSTM training, real model download, or GPU inference workload was started; `nvidia-smi` showed no compute processes before deploy.
- `:8001` remains occupied by template nginx, so vision continues on internal fallback port `18001` until proxy/port mapping is resolved.

## Next recommended goal

- `.codex/goals/09-god-mode.md`

## Phase 09 — God Mode

- Status: complete as of 2026-05-24T21:41:03+09:00.
- Added deterministic `GodCommandDispatcher` with categories:
  - environment
  - event
  - person
  - infrastructure
  - relationship
- Expanded world and God Mode contracts:
  - `WorldClock.active_event`
  - `WorldClock.infrastructure_status`
  - `GodCommandResponse.category`
  - multi-event `events` / `envelopes`
  - event kinds for injected events, person, infrastructure, and relationship changes
- Simulation effects now include:
  - weather changes for environment commands
  - visible active event/infrastructure status
  - memory injection for person and relationship commands
- Orchestrator broadcasts all resulting event envelopes and then a fresh state update.
- Added optional voice placeholder `VoiceCommandStub`; no STT model is started.
- Added `client/src/ui/GodModeMicPanel.tsx` with text input, macro buttons, disabled voice placeholder, and result status.
- Added `docs/god-mode.md` and updated API/WS contract docs.

## Verification evidence — Phase 09

- pass: `python3 packages/shared-schemas/scripts/generate_typescript.py`
- pass: `uv run pytest server/voice server/orchestrator server/sim packages` — 19 tests passed
- pass: `uv run ruff check server packages`
- pass: `uv run mypy server packages`
- pass: `uv run pytest packages server` — 52 tests passed
- pass: `pnpm test` — 2 Node tests passed
- pass: `pnpm typecheck`
- pass: `pnpm lint`
- pass: `pnpm --filter @aetherville/client build` — `/` and `/replay` static routes built successfully
- pass: `bash infra/runpod/verify_runpod.sh` before redeploy; SSH/GPU still pass, Docker unavailable, no GPU compute process
- pass: RunPod sync-only deploy, repo-managed direct-process restart, and direct health check
- pass: RunPod Phase 09 smoke: relationship God command returned two `memory_added` events plus `relationship_changed`, and world `active_event` updated

## RunPod state — Phase 09

- RunPod was synced and repo-managed direct processes were restarted after the code update.
- Current direct-process services:
  - orchestrator `:8080`
  - vLLM fallback `:8000`
  - vision `:18001`
  - Redis memory fallback
- Docker daemon remains unavailable; no Docker retry was attempted beyond the required read-only verification.
- No STT model download, faster-whisper startup, real model download, or GPU inference workload was started; `nvidia-smi` showed no compute processes before deploy.
- `:8001` remains occupied by template nginx, so vision continues on internal fallback port `18001` until proxy/port mapping is resolved.

## Next recommended goal

- `.codex/goals/10-polish-demo.md`

## Phase 10 — Polish and Demo

- Status: complete as of 2026-05-24T21:49:41+09:00.
- Added demo readiness artifacts:
  - `docs/metrics-report.md`
  - `docs/demo-readiness-checklist.md`
  - `docs/architecture-diagram.md`
  - `scripts/demo_smoke.py`
- Updated README with current demo commands and live/replay routes.
- Added `pnpm test:e2e` workspace script and client e2e static fallback test.
- Replay fallback is verified to use `ReplayDriver` and no `ConnectionBridge`, so it remains available when RunPod/network fails.
- Updated `codex/CHECKLISTS.md` with a 15-minute demo dry-run checklist.

## Verification evidence — Phase 10

- pass: `uv run pytest` — 29 tests passed
- pass: `uv run ruff check server packages scripts`
- pass: `uv run mypy server packages`
- pass: `pnpm lint`
- pass: `pnpm typecheck`
- pass: `pnpm test` — 3 Node tests passed
- pass: `pnpm test:e2e` — 1 replay fallback e2e test passed
- pass: `pnpm --filter @aetherville/client build` — `/` and `/replay` static routes built successfully
- pass: `scripts/demo_smoke.py --dry-run`

## RunPod state — Phase 10

- RunPod was not touched during Phase 10 because changes were docs/scripts/client test metadata only.
- Existing known state remains from Phase 09: direct-process runtime only, Docker daemon unavailable, orchestrator `:8080`, vLLM fallback `:8000`, vision `:18001`, Redis memory fallback.
- No real model download, training, STT, YOLO, PPO/LSTM, or GPU inference workload was started.

## Next recommended goal

- `.codex/goals/99-final-audit.md`

## Phase 99 — Final Audit

- Status: complete as of 2026-05-24T21:57:21+09:00.
- Audited master final criteria against current repo and runtime evidence.
- `TASKS.json` now includes and marks the final audit task `M7-001` as done.
- Final local verification evidence:
  - pass: `git status --short` ran; repository has untracked project files because this workspace is not yet committed, but no secret env/key files were printed or added to tracked output.
  - pass: `uv run pytest` — 29 tests passed
  - pass: `uv run pytest packages server` — 52 tests passed
  - pass: `uv run ruff check server packages scripts`
  - pass: `uv run mypy server packages`
  - pass: `pnpm lint`
  - pass: `pnpm typecheck`
  - pass: `pnpm test` — 3 Node tests passed
  - pass: `pnpm test:e2e` — 1 replay fallback test passed
  - pass: `pnpm --filter @aetherville/client build` — `/` and `/replay` static routes built successfully
- Final RunPod verification evidence:
  - pass: `bash infra/runpod/verify_runpod.sh`; SSH/GPU passed, Docker unavailable, no GPU compute process
  - pass: direct-process health check for orchestrator, vision, vLLM fallback, Redis memory fallback
  - pass: final in-pod integration smoke for world state, vehicle camera, vision detect, God Mode weather command, and Socket.IO polling `aetherville:state_update`
- Retry/failure note:
  - first Socket.IO smoke attempted `python-socketio` AsyncClient and failed because remote `aiohttp` is not installed.
  - final Socket.IO smoke was retried with stdlib Engine.IO polling and passed without adding dependencies.

## Final residual risks

- Docker daemon is unavailable on the current RunPod; direct-process runtime is the verified cloud runtime.
- Vision target port `:8001` remains occupied by template nginx; verified vision service runs on `:18001` internally.
- Public RunPod REST/WSS URLs are not configured in tracked files; final smokes used in-pod SSH execution.
- Real vLLM, YOLO, PPO/LSTM, and STT workloads are deferred behind explicit model/cost approval.
- Remote `rsync` is unavailable; deployment uses tar-over-SSH fallback without delete semantics.
- pass: final client start smoke — `pnpm --filter @aetherville/client exec next start -p 3100`, then `curl /` and `curl /replay` returned Aetherville/replay content; local server was stopped after smoke.

## Post-audit runtime strategy patch — 2026-05-24

- Status: complete.
- Updated master and Goal 02 documents to make **direct-process runtime** the active cloud strategy.
- Explicitly removed Docker execution from current cloud acceptance criteria.
- Docker Compose artifacts remain future portability/deployment documentation only.
- ADR-009 records why Docker is optional packaging rather than an execution dependency on the verified RunPod pod.
- No Docker command was run for this patch.

## Phase 99 re-audit after direct-process hardening — 2026-05-24T22:39:21+09:00

- Status: complete.
- Next incomplete/invalidated phase selected: **Phase 99 Final Audit**, because the post-audit direct-process strategy patch changed runtime goal/docs after the previous final audit.
- Hardened RunPod automation so current scripts enforce the direct-process policy:
  - `infra/runpod/verify_runpod.sh` records Docker as unavailable/skipped by policy and does not invoke Docker commands.
  - `infra/runpod/bootstrap_runpod.sh` prints direct-process commands only.
  - `infra/runpod/deploy_over_ssh.sh --mode compose` now fails fast as unsupported for the current RunPod execution path.
- Updated related docs/checklists to remove Docker-first or Docker-execution guidance for the verified RunPod pod.

## Verification evidence — Phase 99 re-audit

- pass: `git status --short` ran and showed only tracked direct-process hardening/docs/status edits.
- pass: `bash -n infra/runpod/verify_runpod.sh infra/runpod/deploy_over_ssh.sh infra/runpod/bootstrap_runpod.sh infra/runpod/start_direct_processes.sh infra/runpod/stop_direct_processes.sh infra/runpod/health_check_direct.sh`
- pass: `python3 -m json.tool TASKS.json`
- pass: markdown fenced-code/local-link check for changed goal/docs/status files.
- pass: `uv run pytest` — 29 tests.
- pass: `uv run pytest packages server` — 52 tests.
- pass: `uv run ruff check server packages scripts`.
- pass: `uv run mypy server packages`.
- pass: `pnpm lint`.
- pass: `pnpm typecheck`.
- pass: `pnpm test` — 3 Node tests.
- pass: `pnpm test:e2e` — 1 replay fallback test.
- pass: `pnpm --filter @aetherville/client build`.
- pass: local client start smoke for `/` and `/replay` on port `3100`.
- pass: `bash infra/runpod/verify_runpod.sh`; SSH/GPU passed, RTX 4090 visible, no GPU compute process, Docker commands skipped by policy.
- pass: `bash infra/runpod/deploy_over_ssh.sh --dry-run --mode direct`; tar-over-SSH fallback selected because remote `rsync` is unavailable.
- pass: `AETHERVILLE_BOOTSTRAP_UV=1 AETHERVILLE_VLLM_MODE=mock AETHERVILLE_REDIS_MODE=memory AETHERVILLE_VISION_PORT=18001 bash infra/runpod/deploy_over_ssh.sh --mode direct`; direct-process health passed.
- pass: final in-pod integration smoke for orchestrator health, world state, vehicle camera, vision `/detect`, God command, and Socket.IO polling `aetherville:state_update`.
- retry note: the first remote smoke used an invalid God command payload and returned HTTP 422; it was corrected to the shared `GodCommand` schema and passed.

## RunPod state — Phase 99 re-audit

- The RunPod pod itself remains the execution environment.
- Direct-process services are healthy: orchestrator `:8080`, vLLM fallback `:8000`, vision `:18001`, Redis memory fallback.
- Docker daemon setup, Docker Compose execution, Docker-in-Docker, and blind Docker retries were not attempted.
- GPU remains visible as NVIDIA GeForce RTX 4090 with no compute process during verification.

## Final residual risks after re-audit

- Public RunPod REST/WSS URLs are not configured in tracked files; final cloud smokes used in-pod SSH execution.
- Vision target port `:8001` remains occupied by template nginx on the current pod; verified direct-process vision uses `:18001`.
- Real vLLM, YOLO, PPO/LSTM, and STT workloads remain opt-in upgrade paths behind explicit model/cost approval.
- Remote `rsync` is unavailable; deployment uses tar-over-SSH fallback without delete semantics.

## Final demo freeze pass — 2026-05-24T23:03:56+09:00

- Status: complete as of 2026-05-24T23:11:38+09:00; commit pending.
- Master implementation phases were not reopened; this pass prepares the already-complete direct-process demo for live local-browser-to-RunPod operation.
- Added `docs/live-demo-runbook.md` with two supported connection modes:
  - Mode A: public RunPod endpoint.
  - Mode B: local SSH tunnel fallback.
- Added `docs/demo-script-15min.md` for the presentation sequence.
- Added a final freeze checklist to `docs/demo-readiness-checklist.md`.
- Updated RunPod demo docs and env examples so verified vision service port `18001` is used for the current pod.
- Updated direct-process script defaults so omitted `AETHERVILLE_VISION_PORT` uses the verified `18001` runtime path.
- Docker daemon setup, Docker Compose execution, Docker-in-Docker, and blind Docker retries remain out of scope and were not performed.

## Verification evidence — final demo freeze

- pass: `python3 -m json.tool TASKS.json`
- pass: `bash -n infra/runpod/*.sh`
- pass: `git diff --check`
- pass: `pnpm typecheck`
- pass: `pnpm --filter @aetherville/client build`
- pass: SSH tunnel direct-process smoke with `python3 scripts/demo_smoke.py --orchestrator-url http://127.0.0.1:18080`; health `ok`, 20 citizens, 1 vehicle, forecast offsets `[5, 10, 15]`.
