# project/PROGRESS.md

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
- `project/TASKS.json`
- `project/PROGRESS.md`
- `project/SESSION_HANDOFF.md`
- `project/DECISIONS.md`


## Phase 02 — Cloud Services Direct Process Runtime

- Status: complete as of 2026-05-24T20:16:05+09:00.
- Goal 02 is treated as **Cloud Services Direct Process Runtime** while retaining filename compatibility with `.codex/goals/02-cloud-services-docker-compose.md`.
- Current acceptance does not require Docker execution.
- Docker/Compose artifacts are retained only for future Docker-capable portability documentation:
  - `infra/docker/docker-compose.yml`
  - `infra/docker/docker-compose.cloud.yml`
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
- `project/TASKS.json` now includes and marks the final audit task `M7-001` as done.
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
- pass: `python3 -m json.tool project/TASKS.json`
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

- pass: `python3 -m json.tool project/TASKS.json`
- pass: `bash -n infra/runpod/*.sh`
- pass: `git diff --check`
- pass: `pnpm typecheck`
- pass: `pnpm --filter @aetherville/client build`
- pass: SSH tunnel direct-process smoke with `python3 scripts/demo_smoke.py --orchestrator-url http://127.0.0.1:18080`; health `ok`, 20 citizens, 1 vehicle, forecast offsets `[5, 10, 15]`.


## Final demo operational risk acceptance — 2026-05-24T23:51:11+09:00

- Status: accepted by user.
- Accepted for the final live demo:
  - Public RunPod REST/WSS URLs are not tracked; use ignored local env values or SSH tunnel Mode B.
  - Vision canonical `8001` is blocked on the current pod; verified demo port is `18001`.
  - Real vLLM, YOLO, PPO/LSTM, and STT remain opt-in and will not start without a separate explicit model/runtime command.
  - Remote `rsync` is unavailable; tar-over-SSH sync fallback is accepted.
- No RunPod change, model download, training job, Docker command, or code implementation change was performed for this acceptance record.

## gstack + dogfood playable demo audit — 2026-05-25T00:36:00+09:00

- Status: report-only QA complete.
- Used gstack `qa-only` rubric/report format and dogfood `agent-browser` browser session against the live local client connected to RunPod tunnel endpoints.
- Positive evidence: home `/` and replay `/replay` loaded, orchestrator health/status passed, vision `18001/health` passed, Socket.IO polling handshake passed, `scripts/demo_smoke.py --orchestrator-url http://127.0.0.1:18080` passed.
- Key finding: connected God Mode command submission is blocked by CORS preflight and a client/server payload mismatch; treat live connected God Mode as a demo blocker until fixed, or present it as offline/replay fallback only.
- Additional findings: replay route is not discoverable from the live UI, WebSocket upgrade warning appears while polling works, and mobile viewport is crowded.
- Report: `docs/gstack-dogfood-audit.md`; raw local QA artifacts: `.gstack/qa-reports/aetherville-20260525-002316/` and `dogfood-output/aetherville-20260525-002316/`.
- Docker was not used; no `.env.runpod`, SSH key path, token, or secret material was printed.

## gstack/dogfood risk resolution — 2026-05-25T01:24:00+09:00

- Status: complete for the approved deterministic/direct-process demo path.
- Resolved God Mode live command blocker by adding FastAPI CORS for local demo origins and verifying the client sends the shared `GodCommand` payload.
- Resolved replay discoverability by adding a visible `Replay fallback 열기` link on `/` and a return link on `/replay`.
- Resolved Socket.IO console noise by making polling the default browser transport via `NEXT_PUBLIC_SOCKET_TRANSPORTS=polling`; WSS remains opt-in by env.
- Resolved mobile overlay/crowding by moving the connection card into normal mobile flow and reducing hero scale.
- Hardened RunPod direct deploy so `.gstack/` and `dogfood-output/` are not synced and repo-managed processes restart after sync.
- Redeployed RunPod direct-process services with Docker still excluded; orchestrator, vision `18001`, and vLLM fallback health passed.
- Browser verification on local client port `3100` showed replay/God Mode links, `transport: polling`, successful God Mode result, and empty console/errors after submit.

## gstack tooling follow-up — 2026-05-25T02:22:00+09:00

- Status: complete; the former non-demo gstack browser tooling note is now repaired locally.
- Registered installed gstack `1.31.0.0` for Codex as namespaced `gstack-*` skills under the user Codex skills directory.
- Added user-level command shims so `bun` resolves to the non-snap user install and `browse` resolves to the gstack browse binary instead of the system `xdg-open` alias.
- Verification passed: `command -v bun`, `bun --version`, `command -v browse`, `browse --help`, and `browse status`.
- This was a local tooling repair only: no Docker, no RunPod runtime change, and no secrets printed.

## Local client endpoint documentation fix — 2026-05-25T02:30:00+09:00

- Status: complete; documented that `NEXT_PUBLIC_*` values are build-time values for production bundles.
- Demo runbook continues to prefer `pnpm dev` with explicit endpoint envs for Mode A/Mode B.
- Checklist now requires matching build-time envs when an operator chooses `next build && next start`.
- This closes the endpoint drift risk observed when a production build made without demo envs displayed default localhost service URLs.

## Actor visual distinction polish — 2026-05-25T02:52:00+09:00

- Status: complete locally; 3D city scene now separates actor classes by shape and color, not just position.
- Citizens render as two-part people with pink heads, teal bodies, and floor halos.
- Vehicles render as yellow taxi-like cars with blue cabs, black wheels, and roof lights.
- Traffic lights render as pole-mounted three-color signal heads instead of single dots.
- Drones render as bright octahedrons with purple propeller arms.
- Buildings were muted so they no longer compete with live actors, and a scene legend explains every category.

## Waypoint movement polish — 2026-05-25T03:21:00+09:00

- Status: complete and deployed to the direct-process RunPod runtime.
- Replaced circular citizen motion with deterministic sidewalk/crosswalk waypoint routes.
- Updated client replay/fallback motion so citizens, taxi, and drone also follow straight route segments instead of circular sine/cosine loops.
- Added regression coverage proving the first citizen advances along a corridor segment with stable lane position, not an orbit.
- Verified RunPod tunnel state after redeploy: simulation running, tick advancing, and sampled citizens moving between route waypoints.

## Top-bottom layout polish — 2026-05-25T03:47:00+09:00

- Status: complete locally; main page no longer uses the previous left/right split.
- `.shell` now stacks the hero/instructions on top and the live city scene plus panels underneath.
- Hero typography was tightened for a top banner layout, endpoint cards are compact, and the city canvas expands full-width below.
- Runtime services were not changed; this is a local client layout update only.

## Tagged 4x4 city + larger live stage polish — 2026-05-25T06:05:46+09:00

- Status: complete and deployed to the verified direct-process RunPod runtime.
- Expanded the demo world contract to show a 4x4 street grid with 16 building blocks, 7 default citizens, 3 vehicles, and 4 visible traffic lights.
- Added shared `display_tags` for citizens, vehicles, and traffic lights, then rendered those tags as billboard labels in the R3F city scene.
- God Mode scenario support verified:
  - `민지랑 민수가 만난다` tags `c01`/`c02` as meeting participants and updates `talking_to` state.
  - `민지가 택시를 불러줘` tags taxi `v01` with `택시 호출` and emits a `trip_requested` event.
- Increased demo city prominence by compacting the top hero banner and giving the city panel a larger responsive stage (`clamp(560px, 78vh, 880px)`).
- Visual browser smoke: `/tmp/aetherville-live-grid-tags-connected.png`; live Socket.IO polling reached `connected`, city tick advanced, and tags were visible. Visual verdict persisted at `.omx/state/visual-grid-tags/ralph-progress.json` with score `94`.
- RunPod direct-process redeploy passed using tar-over-SSH fallback; `uv` bootstrap was enabled because the pod lacked `uv` on PATH. Simulation was started after deploy.
- Verified via local tunnel: orchestrator health, sim status `7/3/4`, vision `18001`, meeting command, taxi command, and world-state tag extraction.
- Docker daemon setup, Docker Compose, Docker-in-Docker, and blind Docker retries were not used.

## God Mode visible event feedback polish — 2026-05-25T07:29:15+09:00

- Status: complete and deployed to the verified direct-process RunPod runtime.
- Audit input: `Video Project 8.mp4` showed that the prior God Mode shortcuts could read as a short looping city clip because rain, taxi, and traffic commands did not create strong enough visual/behavioral consequences.
- Rain command improvement:
  - God Mode rain now locks weather for a demo window instead of being overwritten by the automatic weather toggle.
  - Client renders a visible animated rain sheet and `RAIN ACTIVE · 비 내리는 중` badge.
- Taxi command improvement:
  - `민지가 택시를 불러줘` now dispatches taxi `v01` toward the passenger pickup point instead of only retagging a looping route.
  - Taxi tags progress through movement/pickup/passenger phases such as `민지에게 이동`, `픽업 대기`, and `민지 탑승`.
- Traffic surge improvement:
  - `차량 정체` now activates a congestion window, slows vehicle route progress, adds `정체/저속` vehicle tags, raises forecast congestion, and displays a red `TRAFFIC SURGE · 차량 저속/정체` overlay.
- Visual evidence: `/tmp/aetherville-event-feedback-final.png`; browser smoke confirmed `rainOverlay`, `trafficOverlay`, `trafficPanel`, and `taxiTag` all true while Socket.IO polling was connected.
- RunPod direct-process redeploy passed using tar-over-SSH fallback and `AETHERVILLE_BOOTSTRAP_UV=1`; Docker was not used.

## Mini-GTA live city motion polish — 2026-05-25T08:44:38+09:00

- Status: complete and deployed to the verified direct-process RunPod runtime.
- Audit input: `Video Project 8.mp4` and live browser checks showed the demo could still read as a short loop when God Mode events were subtle.
- Client scene polish:
  - Added a smooth R3F game camera that follows taxi/meeting/traffic focal points instead of a fixed static view.
  - Added street lights, lane dashes, neon building windows, compact mini-map HUD, and denser traffic-jam queue vehicles.
  - Replaced static citizen capsules with animated pedestrian rigs including bob, arm swing, and leg swing.
  - Added wheel-spinning vehicles with headlights/brake lights, taxi/congestion pulse rings, and rotating drone rotors.
  - Added in-scene 3D rain streaks on top of the existing rain overlay/badge.
- God Mode behavior fix:
  - `교통량 증가시켜` now classifies as infrastructure and triggers the same `traffic_jam` congestion path as explicit 정체/혼잡 commands.
- Layout polish: the top hero now uses a compact two-column banner on wide viewports so the city appears sooner and larger in the first screen.
- Runtime evidence after direct-process redeploy: weather `rain`, active event `traffic congestion`, infrastructure `traffic congestion active`, taxi tags include `택시 호출/민지에게 이동`, v02 tags include `정체/저속`, and forecast indices were `[1.0, 1.0, 1.0]`.
- Browser evidence: `/tmp/aetherville-mini-gta-envbuild.png`; local production client showed `connected`, rain/traffic/taxi evidence true, canvas present, and 4 side panels present.
- Docker daemon setup, Docker Compose, Docker-in-Docker, and blind Docker retries were not used.

## Persistent demo AI learning loop — 2026-05-25T11:47:49+09:00

- Status: complete locally; direct-process RunPod redeploy pending verification in this turn.
- Added a shared `LearningSnapshot` / `LearningStatusResponse` contract and included `learning` in every `WorldStatePayload`.
- Added `LearningStore`, a JSON-backed deterministic online adaptation layer that persists God Mode, 시민 기억, 택시, 날씨, and 교통 events without starting real GPU training.
- Simulation feedback now reflects learned state in traffic queue pressure, vehicle learned-speed factor, traffic light tags, policy version, and forecast/panel state.
- Added `/api/v1/learning/status` and health dependency evidence for the learning loop.
- Client now has an `AI 학습 루프` panel showing experience count, epoch, policy version, traffic bias, taxi success rate, and latest insight.
- Truthfulness note: this is persistent demo adaptation, not real vLLM/YOLO/PPO/LSTM/STT self-training. Keeping the server running improves the persisted adaptation state only as events are observed or commanded.
- Docker daemon setup, Docker Compose, Docker-in-Docker, and blind Docker retries remain excluded.

## Persistent demo AI learning loop deployment — 2026-05-25T12:06:00+09:00

- Status: complete and deployed to the verified direct-process RunPod runtime.
- RunPod verify passed: SSH/GPU visible, NVIDIA GeForce RTX 4090 idle for compute, Docker commands skipped by policy.
- Direct-process redeploy passed using tar-over-SSH fallback, `AETHERVILLE_BOOTSTRAP_UV=1`, mock vLLM, memory Redis, and vision port `18001`.
- Runtime smoke passed through local tunnel: `/api/v1/health` reported `learning:ok`, `/api/v1/learning/status` returned `deterministic_online_adaptation`, and vision `/health` returned ok.
- God Mode learning smoke passed: traffic, taxi, and rain commands raised experience count to 6, policy version to `adaptive-demo-v2`, traffic bias to `0.12`, taxi success rate to `0.59`, weather to `rain`, taxi tags to `택시 호출/민지에게 이동`, traffic light tags to `학습제어/v2`, and forecast indices to `[1.0, 1.0, 1.0]`.
- Local production client was rebuilt with tunnel `NEXT_PUBLIC_*` values, restarted on port `3000`, and the rendered HTML contains `AI 학습 루프`.
- Docker daemon setup, Docker Compose, Docker-in-Docker, and blind Docker retries were not used.

## Real 4090 vLLM activation — 2026-05-25T13:02:41+09:00

- Status: complete for first real GPU workload; broader “extreme” completion remains active.
- Pushed prior completed work to `origin/master` at commit `ea506b1`.
- Added direct-process support for real vLLM bootstrap with CUDA-12.8-compatible pins: `vllm==0.10.2` and `transformers==4.55.4`.
- Added process-mode switching so real vLLM stops the mock vLLM fallback before binding `:8000`, and mock mode stops real vLLM when reverting.
- Added model-cache guidance and sync exclusions for large local video artifacts.
- Started real vLLM on the RTX 4090 with `Qwen/Qwen2.5-14B-Instruct-AWQ`, `--gpu-memory-utilization 0.88`, and `--max-model-len 4096`.
- Verified `/v1/models` returns `Qwen/Qwen2.5-14B-Instruct-AWQ` and `/v1/chat/completions` generated a Korean citizen line.
- Added `OpenAICompatiblePlanner` and connected citizen reflection to real vLLM when `AETHERVILLE_LLM_MODE=vllm`.
- Verified orchestrator health reports `vllm:ok` and `POST /api/v1/citizens/c01/reflect` returns a real model-generated Korean reflection.
- GPU evidence after smoke: about 22.5 GiB VRAM used by the real vLLM workload.
- Docker daemon setup, Docker Compose, and Docker-in-Docker were not used.

## Real 4090 YOLO vision activation — 2026-05-25T13:14:53+09:00

- Status: complete for first real vision inference path; broader “extreme” completion remains active.
- Added optional real YOLO mode to the vision service behind `AETHERVILLE_VISION_MODE=real` while preserving deterministic mock fallback.
- Added RunPod direct-process support for `AETHERVILLE_BOOTSTRAP_YOLO=1`, `AETHERVILLE_YOLO_INSTALL_PACKAGE`, `AETHERVILLE_YOLO_MODEL`, and `AETHERVILLE_YOLO_DEVICE`.
- Installed `ultralytics 8.4.53` on the RunPod uv environment and started vision with `yolo11n.pt` on device `0` while real vLLM remained active.
- Verified vision `/health` reports `yolo:ok` and `/detect` returns `mode=real` with YOLO detections on the synthetic road frame.
- GPU evidence after real YOLO smoke with real vLLM still loaded: about 23.1 GiB VRAM used.
- Detection filter now defaults to traffic-relevant COCO labels so non-demo classes from synthetic shapes are suppressed.
- Docker daemon setup, Docker Compose, and Docker-in-Docker were not used.

## Real YOLO vehicle camera panel integration — 2026-05-25T13:22:50+09:00

- Status: complete locally; RunPod direct-process redeploy/smoke follows in this turn.
- Added `VehicleCameraFrame.mode` to distinguish mock camera boxes from real RunPod YOLO detections.
- Orchestrator `/api/v1/vehicles/{id}/camera` now calls vision `/detect` when `AETHERVILLE_CAMERA_VISION_MODE=real`, without putting YOLO inference in the 10 Hz simulation tick loop.
- Direct-process startup passes the vision mode into orchestrator camera enrichment so `AETHERVILLE_VISION_MODE=real` activates the camera endpoint path.
- Browser `VehicleCamPanel` now polls the camera endpoint and displays `REAL YOLO · RunPod 4090` when real detections are returned; state-embedded mock detections remain the fallback.
- Updated demo/metrics/YOLO docs to remove the stale “browser camera still mock-only” gap.
- Docker daemon setup, Docker Compose, Docker-in-Docker, and blind Docker retries were not used.

## Real YOLO vehicle camera panel deployment — 2026-05-25T13:35:02+09:00

- Status: complete and deployed to the verified direct-process RunPod runtime.
- Sync used tar-over-SSH fallback; Docker daemon setup, Docker Compose, Docker-in-Docker, and blind Docker retries were not used.
- Restart strategy preserved existing real vLLM and real YOLO processes, then restarted only the orchestrator so the new camera enrichment code loaded.
- RunPod health passed: orchestrator `ok`, vision `yolo:ok`, vLLM model list returned `Qwen/Qwen2.5-14B-Instruct-AWQ`, Redis memory fallback active.
- Local tunnel smoke passed: `/api/v1/vehicles/v01/camera` returned `mode: real`, dimensions `640x384`, and a traffic-light detection from the real vision service.
- God Mode smoke passed after restart: simulation started, `교통량 증가시켜` set traffic congestion, `민지가 택시를 불러줘` moved taxi tags into dispatch/pickup phases, and `도시에 비를 내려줘` set weather to rain.
- Local Next dev server was restarted on port `3000` with tunnel `NEXT_PUBLIC_*` values; `/` and `/replay` HTTP smokes passed after compilation.

## Real 4090 traffic policy checkpoint — 2026-05-25T13:50:33+09:00

- Status: complete and deployed to the verified direct-process RunPod runtime.
- Added `TrafficAiSnapshot` to the shared world-state contract and regenerated TypeScript contracts.
- Added a RunPod-safe traffic policy trainer: `python -m aetherville_server.traffic_ai.train_gpu_policy`.
- Trained a checkpoint on the RTX 4090 with PyTorch CUDA: 320 episodes, horizon 80.
- Training output reported `trained_on_gpu: true`, `training_backend: torch_cuda`, selection `trained_linear_policy`, and loss `0.208008`.
- Measured traffic policy result: average queue `32.913` vs fixed-cycle `48.138`, a `31.628%` reduction in the deterministic traffic environment.
- Orchestrator was restarted with `AETHERVILLE_TRAFFIC_POLICY_CHECKPOINT` pointing to the RunPod model cache checkpoint.
- Runtime smoke via local tunnel confirmed `traffic_ai.mode=checkpoint`, `trained_on_gpu=true`, `training_backend=torch_cuda`, and traffic-light tags include `AI정책:checkpoint`.
- Browser traffic panel now displays a `GPU POLICY` badge and queue-cut percentage from shared state.
- Docker daemon setup, Docker Compose, Docker-in-Docker, and blind Docker retries were not used.

## Local client traffic policy panel restart — 2026-05-25T13:58:30+09:00

- Status: complete locally.
- Restarted the local Next dev server on port `3000` with tunnel `NEXT_PUBLIC_*` values.
- HTTP smoke passed for `/` and `/replay` after Next compiled the updated traffic panel.

## Real 4090 LSTM traffic forecast checkpoint — 2026-05-25T14:09:29+09:00

- Status: complete and deployed to the verified direct-process RunPod runtime.
- Added `TrafficForecastAiSnapshot` to the shared world-state contract and regenerated TypeScript contracts.
- Added `aetherville_server.traffic_ai.train_lstm_forecast`, a short PyTorch LSTM trainer that exports JSON weights for torch-free orchestrator inference.
- Trained the LSTM forecast checkpoint on the RTX 4090 with PyTorch CUDA: 960 samples, 180 epochs, sequence length 12, hidden size 10.
- Training output reported `trained_on_gpu: true`, `training_backend: torch_cuda`, `MAPE: 11.84`, and `training_loss: 2.911555`.
- Orchestrator was restarted with both `AETHERVILLE_TRAFFIC_POLICY_CHECKPOINT` and `AETHERVILLE_TRAFFIC_FORECAST_CHECKPOINT` pointing to RunPod model-cache checkpoints.
- Runtime smoke via local tunnel confirmed `traffic_forecast_ai.mode=lstm_checkpoint`, `trained_on_gpu=true`, `training_backend=torch_cuda`, and forecast points were emitted from the LSTM checkpoint path.
- Browser traffic panel now displays an `LSTM FORECAST` badge and MAPE from shared state.
- Docker daemon setup, Docker Compose, Docker-in-Docker, and blind Docker retries were not used.

## Local client LSTM panel restart — 2026-05-25T14:18:40+09:00

- Status: complete locally.
- After the LSTM panel/schema update, the old Next dev cache produced a transient missing chunk error.
- Cleared `client/.next`, restarted Next dev on port `3000` with tunnel `NEXT_PUBLIC_*` values, and re-smoked `/` plus `/replay` successfully.

## Real 4090 vLLM God Mode interpretation — 2026-05-25T14:27:17+09:00

- Status: complete locally; direct-process RunPod redeploy/smoke follows in this turn.
- Added a constrained OpenAI-compatible vLLM interpreter for God Mode text commands behind `AETHERVILLE_GOD_MODE_LLM=vllm`.
- Safety model: vLLM does not execute arbitrary effects. It only selects one action from the fixed demo vocabulary (`rain`, `traffic_jam`, `taxi_call`, `meeting`, etc.), then the existing deterministic dispatcher applies the effect. Timeout, invalid JSON, disabled env, or model failure falls back to the rules path.
- `GodCommandResponse` now exposes `ai_mode`, `ai_confidence`, and `ai_reason`; generated TypeScript was refreshed and the browser God Mode panel shows `vLLM NN%` or `rules fallback` after command execution.
- Direct-process startup now passes `AETHERVILLE_GOD_MODE_LLM` into the orchestrator. Docker daemon setup, Docker Compose, Docker-in-Docker, and blind Docker retries were not used.

## Real 4090 vLLM God Mode deployment — 2026-05-25T14:42:00+09:00

- Status: complete and deployed to the verified direct-process RunPod runtime.
- RunPod verify passed: SSH/GPU visible, NVIDIA GeForce RTX 4090 active with real vLLM memory resident; Docker commands remained skipped by policy.
- Sync used tar-over-SSH fallback; existing real vLLM and real YOLO processes were preserved, then only the orchestrator was stopped and restarted with `AETHERVILLE_GOD_MODE_LLM=vllm`.
- Direct health passed when run with `AETHERVILLE_VLLM_MODE=real`: orchestrator `ok`, vision `yolo:ok`, vLLM `/v1/models` returned `Qwen/Qwen2.5-14B-Instruct-AWQ`, Redis memory fallback active. The default mock-mode health invocation correctly failed against real vLLM and was rerun with the real-mode env.
- Local tunnel God Mode smoke passed: `출근길을 혼잡하게 만들어줘` returned `ai_mode=vllm`, `ai_confidence=1.0`, event action `traffic_jam`, and world state showed `traffic_ai=checkpoint/torch_cuda`, `traffic_forecast_ai=lstm_checkpoint/torch_cuda`, and congestion tags on vehicles.
- Local Next production server was rebuilt with tunnel `NEXT_PUBLIC_*` values and restarted on port `3000`; `/` and `/replay` HTTP smokes passed.
- Docker daemon setup, Docker Compose, Docker-in-Docker, and blind Docker retries were not used.

## Real 4090 vLLM multi-action God Mode direction — 2026-05-25T14:51:04+09:00

- Status: complete locally; direct-process RunPod redeploy/smoke follows in this turn.
- Expanded the vLLM God Mode interpreter from one primary action to a bounded one-to-four action plan, still limited to the audited safe vocabulary.
- The deterministic dispatcher now aggregates sub-effects for combined commands such as rain + traffic congestion + taxi dispatch + citizen meeting, records every concrete event, then emits a `god_command_executed` summary event.
- The rules fallback also decomposes obvious multi-intent Korean commands, so the live demo remains visually strong even if vLLM falls back.
- `GodCommandResponse.ai_actions` and the browser God Mode result now expose the decomposed action sequence.
- Docker daemon setup, Docker Compose, Docker-in-Docker, and blind Docker retries remain excluded.

## Real 4090 vLLM multi-action God Mode deployment — 2026-05-25T15:08:57+09:00

- Status: complete and deployed to the verified direct-process RunPod runtime.
- Sync used tar-over-SSH fallback; existing real vLLM and real YOLO processes were preserved, then only the orchestrator was restarted with the updated multi-action interpreter.
- Direct health passed with `AETHERVILLE_VLLM_MODE=real`: orchestrator `ok`, vision `yolo:ok`, vLLM model list returned `Qwen/Qwen2.5-14B-Instruct-AWQ`, Redis memory fallback active.
- RunPod multi-action God Mode smoke passed: the command “도시에 비를 내리고 민지가 택시를 부르게 하고 출근길을 혼잡하게 만들고 민수와 만나게 해줘” returned `ai_mode=vllm`, `ai_actions=[rain, traffic_jam, taxi_call, meeting]`, `god_command_executed`, and 9 concrete/summary events.
- World-state smoke after the command proved all visible effects: weather `rain`, infrastructure `traffic congestion active`, taxi `v01` passenger `c01`, vehicle congestion tags, and 민지/민수 talking state.
- Local Next production server was restarted on port `3000` with tunnel `NEXT_PUBLIC_*` values; `/` and `/replay` HTTP smokes passed.
- Docker daemon setup, Docker Compose, Docker-in-Docker, and blind Docker retries were not used.

## God Mode voice/STT command path — 2026-05-25T15:15:03+09:00

- Status: complete locally; direct-process RunPod redeploy/smoke follows in this turn.
- Added shared `VoiceCommandRequest` and `VoiceCommandResponse` contracts and regenerated TypeScript.
- Added `/api/v1/god/voice`: the endpoint transcribes voice audio through the configured STT provider, converts the transcript into a voice `GodCommand`, then routes it through the same vLLM/rules multi-action dispatcher and broadcasts the resulting events.
- Added a default safe fallback provider and an optional lazy `faster-whisper` provider behind `AETHERVILLE_STT_MODE=faster_whisper`.
- Browser God Mode now enables microphone recording with `MediaRecorder`; it posts the audio blob plus current typed text as a deterministic fallback transcript.
- Direct-process startup now supports `AETHERVILLE_BOOTSTRAP_STT=1`, `AETHERVILLE_STT_INSTALL_PACKAGE`, `AETHERVILLE_STT_MODEL`, `AETHERVILLE_STT_DEVICE`, and `AETHERVILLE_STT_COMPUTE_TYPE`.
- Docker daemon setup, Docker Compose, Docker-in-Docker, and blind Docker retries remain excluded.

## God Mode voice/STT direct-process deployment — 2026-05-25T15:38:00+09:00

- Status: complete and deployed to the verified direct-process RunPod runtime.
- RunPod verify passed: SSH and RTX 4090 GPU visible; Docker commands remained intentionally skipped by policy.
- Synced repository with tar-over-SSH fallback; real vLLM, real YOLO, traffic policy checkpoint, and LSTM forecast checkpoint were preserved.
- Restarted only the orchestrator path with `AETHERVILLE_STT_MODE=faster_whisper`, `AETHERVILLE_BOOTSTRAP_STT=1`, `AETHERVILLE_STT_MODEL=base`, `AETHERVILLE_STT_DEVICE=cuda`, and the existing real-vLLM/GPU traffic checkpoint settings.
- Direct health passed with orchestrator `ok`, STT dependency `ok` (`faster-whisper configured model=base device=cuda`), vision `yolo:ok`, vLLM model `Qwen/Qwen2.5-14B-Instruct-AWQ`, and Redis memory fallback.
- Voice fallback smoke through the local tunnel passed: `POST /api/v1/god/voice` without an audio blob returned `stt_status=fallback`, `stt_mode=fallback`, nested `command.accepted=true`, `ai_mode=vllm`, and `ai_actions=[rain, taxi_call]`.
- Simulation was started after restart; `/api/v1/sim/status` advanced from tick 0 to tick 16 with `running=true`.
- Local Next production server was rebuilt/restarted on port `3000` with tunnel `NEXT_PUBLIC_*` values; `/` and `/replay` HTTP smokes passed.
- Truthfulness note: faster-whisper is installed/configured, but real audio transcription is not claimed until a microphone/audio-blob smoke returns `stt_status=ok`.
- Docker daemon setup, Docker Compose, Docker-in-Docker, and blind Docker retries were not used.

## Real audio STT smoke on RunPod faster-whisper — 2026-05-25T15:49:00+09:00

- Status: complete and verified against the active direct-process RunPod runtime.
- Added `scripts/voice_stt_smoke.py`, a dependency-free helper that base64-encodes an existing WAV/WEBM/MP3 file and posts it to `/api/v1/god/voice` with `--expect-status ok` for real STT proof.
- Generated a temporary Korean TTS WAV outside the repository and sent it through the local tunnel to the RunPod orchestrator.
- Real-audio smoke passed: transcript `도시에 비를 내리고 민지가 택시를 부르게 해줘`, `stt_status=ok`, `stt_mode=faster_whisper`, detail `model=base device=cuda compute=int8_float16`, nested `command.accepted=true`, `ai_mode=vllm`, and `ai_actions=[rain, taxi_call]`.
- Updated demo runbook, metrics, God Mode docs, demo script, readiness checklist, TASKS, and SESSION_HANDOFF to distinguish server-side real-audio STT proof from live browser microphone QA.
- Temporary audio/TTS artifacts were not committed. Docker daemon setup, Docker Compose, Docker-in-Docker, and blind Docker retries were not used.

## Browser demo runtime endpoint smoke hardening — 2026-05-25T16:12:00+09:00

- Status: complete locally; no RunPod service restart required.
- Headless Chromium demo audit found that plain `curl /` was too weak: the production page could render stale `http://localhost:8080` endpoint values if `next start` was launched after a build made with different `NEXT_PUBLIC_*` values.
- Updated the live Next page to `force-dynamic` and passed the runtime orchestrator URL into `SidePanels`, `VehicleCamPanel`, and `GodModeMicPanel` as props. Vehicle camera and God Mode browser calls no longer read stale client-bundle endpoint constants.
- Replay mode now passes `orchestratorUrl=null`, keeping replay deterministic and preventing background live camera/God Mode calls.
- Added `scripts/browser_demo_smoke.py` to run headless Chromium against live and replay routes, check required demo panels, verify selected endpoint rendering, and fail on Next client-side error markers.
- Verified production-style `next build && next start` with tunnel envs: live browser smoke saw `http://127.0.0.1:18080`, all core panels, no application error; replay smoke also passed.
- Docker daemon setup, Docker Compose, Docker-in-Docker, and blind Docker retries were not used.

## Full presenter rehearsal smoke — 2026-05-25T16:22:00+09:00

- Status: complete and verified against the active direct-process RunPod runtime plus local browser client.
- Added `scripts/demo_rehearsal.py`, a stdlib-only full demo rehearsal that verifies orchestrator health/dependencies, simulation start, CUDA-trained traffic policy, CUDA-trained LSTM forecast, real vehicle camera mode, deterministic learning status, vLLM multi-action God Mode, visible rain/taxi/congestion/meeting effects, and live/replay headless Chromium browser smokes.
- Rehearsal command passed with `ok=true` for `http://127.0.0.1:18080` and `http://127.0.0.1:3000`.
- Verified God Mode command returned `ai_mode=vllm` and `ai_actions=[rain, traffic_jam, taxi_call, meeting]`; subsequent world state showed `weather=rain`, taxi passenger/dispatch, congestion tags, and 민지/민수 talking state.
- Verified vehicle camera endpoint returned `mode=real` with a traffic-light detection from the RunPod vision path.
- Updated live demo runbook, 15-minute script, readiness checklist, TASKS, and SESSION_HANDOFF so this one-command rehearsal is part of the demo gate.
- Docker daemon setup, Docker Compose, Docker-in-Docker, and blind Docker retries were not used.

## Scene Director live impact polish — 2026-05-25T16:35:00+09:00

- Status: complete locally; production browser rebuild/rehearsal follows in this turn.
- Added a city `SCENE DIRECTOR · LIVE IMPACT` HUD so rain, traffic surge, taxi dispatch, citizen meeting, GPU policy, and LSTM forecast state are visible at a glance on the 3D scene.
- Added `SceneImpactPanel` / `Live impact board` to the panel deck with active/inactive situation cards and current learning loop evidence.
- Updated browser smoke expectations so live/replay Chromium checks fail if the Scene Director and impact board disappear.
- Updated the 15-minute script, runbook, readiness checklist, TASKS, and SESSION_HANDOFF to make the impact board part of the presentation gate.
- Docker daemon setup, Docker Compose, Docker-in-Docker, and blind Docker retries were not used.

## Screenshot visual smoke gate — 2026-05-25T17:08:33+09:00

- Status: complete locally; the live browser demo now has a real screenshot-based visual QA gate in addition to DOM marker smoke.
- Added `scripts/browser_visual_smoke.py`, which captures live/replay Chromium screenshots, validates 1920x1080 PNG dimensions, minimum bytes, sampled color diversity, luminance range, and optional DOM markers.
- Integrated the visual gate into `scripts/demo_rehearsal.py`; the full rehearsal now runs it by default and offers `--skip-visual-smoke` only for environments where Chromium screenshots cannot run.
- Verified current local client screenshots through the RunPod tunnel: live PNG `942655` bytes with `1454` sampled colors and luma range `236`; replay PNG `946968` bytes with `1750` sampled colors and luma range `236`.
- Screenshot artifacts are written under ignored `dogfood-output/visual-smoke/`; root one-off captures were removed before commit.
- Docker daemon setup, Docker Compose, Docker-in-Docker, and blind Docker retries were not used.

## Before/after God Mode impact smoke — 2026-05-25T17:33:28+09:00

- Status: complete locally against the active RunPod tunnel; this closes the “it looks like a looping video” demo-risk with measurable before/after evidence.
- Live Next route now fetches the current RunPod `/api/v1/sim/state` server-side on first render, so headless screenshots and first paint reflect the real world state before Socket.IO hydration instead of only the replay fallback.
- Added `scripts/browser_impact_smoke.py`, which resets the simulation to a clear baseline, captures a before screenshot, sends the combined God Mode command through the RunPod orchestrator, waits for rain/taxi/traffic/meeting effects, captures an after screenshot, and compares sampled pixels.
- Integrated the impact smoke into `scripts/demo_rehearsal.py`; full rehearsal now runs it by default, with `--skip-impact-smoke` only for environments where screenshots cannot run.
- Verification evidence: impact smoke passed with `ai_mode=vllm`, `ai_actions=[rain, traffic_jam, taxi_call, meeting]`, clear→rain world state, taxi dispatch, congestion tags, citizen meeting, mean RGB delta `11.036`, and changed sample ratio `0.4531`.
- Screenshot artifacts are written under ignored `dogfood-output/impact-smoke/` and are not committed. Docker daemon setup, Docker Compose, Docker-in-Docker, and blind Docker retries were not used.

## RunPod 4090 AI proof panel — 2026-05-25T17:53:50+09:00

- Status: complete locally; the live browser UI now has an explicit `RunPod AI proof` / `4090 실행 증거` panel for presentation truthfulness.
- Added `RunPodProofPanel`, which combines `/api/v1/health` dependency status with shared world state to show vLLM, YOLO vision, faster-whisper STT, 4090 traffic policy, 4090 LSTM forecast, adaptive loop, and direct-process/no-Docker runtime evidence.
- `SidePanels` now receives the server-fetched initial RunPod world state on the live route, so proof/traffic/learning panels no longer start from replay fallback before Socket.IO hydration.
- Browser smoke now requires the RunPod proof markers on both live and replay routes, while the panel honestly shows fallback/offline states if the live orchestrator is not available.
- Docker daemon setup, Docker Compose, Docker-in-Docker, and blind Docker retries were not used.

Verification update — 2026-05-25T18:04:10+09:00:

- Full `scripts/demo_rehearsal.py` passed after rebuilding/restarting the local production client with tunnel envs.
- Browser smoke confirmed `RunPod AI proof` / `4090 실행 증거` markers on live and replay routes.
- Impact smoke after the proof panel update measured mean RGB delta `22.062` and changed sample ratio `0.6373` while vLLM returned `rain + traffic_jam + taxi_call + meeting`.

## M11 — vLLM Autonomous City AI Loop — 2026-05-25T21:37:47+09:00

- Status: complete on branch `feat/llm-driven-city-loop` committed and pushed to `feat/llm-driven-city-loop`.
- Added interval-scoped City AI planning so the city is no longer only deterministic loop motion:
  - `CityWorldContext` summarizes citizens, vehicles, weather, traffic, learning, and recent events.
  - `OpenAICompatibleCityPlanner` calls the RunPod vLLM OpenAI-compatible endpoint only on an interval/event window, never per tick.
  - vLLM output is constrained to `CityAiPlan` JSON with safe actions: citizen movement, taxi dispatch, meeting, memory, traffic surge, weather, or no-op.
  - `SimulationEngine` validates plans and applies state only through Python executors.
  - Citizens can receive AI movement directives and visibly carry `AI계획` tags while moving.
  - `WorldStatePayload.city_ai` and `city_ai_plan` timeline events expose what the city AI decided.
  - Client Scene Director / 3D HUD now shows `CITY AI PLAN`, city AI mode/status, and actor focus derived from shared world state.
- Direct-process RunPod state:
  - SSH/GPU read-only verification succeeded after one transient SSH timeout retry; GPU remains NVIDIA GeForce RTX 4090.
  - Docker was not run.
  - Targeted tar-over-SSH sync was used because full repo tar sync can hang and remote `rsync` is unavailable.
  - Orchestrator was restarted only; existing real vLLM, real YOLO vision, STT, and traffic checkpoint paths were preserved.
  - Direct health passed for orchestrator, vision `18001`, real vLLM `8000/v1`, and Redis memory fallback.
- RunPod City AI smoke evidence:
  - Remote in-pod smoke: `scripts/city_ai_smoke.py --orchestrator-url http://127.0.0.1:8080 --expect-mode vllm --wait-seconds 50 --post-plan-seconds 4` passed with `mode=vllm`, `status=applied`, actions `call_taxi, meet`, movement observed for `c01`, `c02`, `v01`, and `city_ai_plan` in timeline.
  - Local tunnel smoke: `python3 scripts/city_ai_smoke.py --orchestrator-url http://127.0.0.1:18080 --expect-mode vllm --wait-seconds 20 --post-plan-seconds 2` passed with actions `move_citizen, call_taxi`, movement observed for `c01`, `c03`, `c04`, `v01`, and markers `citizen_ai_directive`, `taxi_dispatch`.
- Local verification passed:
  - `uv run pytest` — 47 passed.
  - `uv run ruff check server packages scripts` — pass.
  - `uv run mypy server packages` — pass.
  - `python3 -m py_compile scripts/city_ai_smoke.py` — pass.
  - `bash -n infra/runpod/*.sh` — pass.
  - `python3 -m json.tool project/TASKS.json` — pass.
  - `pnpm lint` — pass.
  - `pnpm typecheck` — pass.
  - `pnpm test` — 3 passed.
  - `pnpm test:e2e` — 1 passed.
  - `pnpm --filter @aetherville/client build` — pass.
  - `git diff --check` — pass.
  - `scripts/browser_demo_smoke.py --mode live --url http://127.0.0.1:3000/ --expected-endpoint http://127.0.0.1:18080` — pass.
- Operational note: vLLM can plan and direct city actions, but this is not model weight self-training. Persistent improvement still comes from the existing learning/memory state unless a separate approved training job is run.

## M11-002 — Scenario Director complex story execution — 2026-05-26T03:18:28+09:00

- Status: complete locally on branch `feat/llm-driven-city-loop`; focused dogfood passed.
- Added a bounded `ScenarioDirective` / `ScenarioStep` shared contract and generated TypeScript output. `WorldStatePayload.scenario` and `GodCommandResponse.scenario` now expose active/completed complex-story execution.
- Added a deterministic scenario compiler/executor for Korean audience-story commands such as “민수가 하린을 만난 뒤 택시를 불러 민지에게 가고, 드론은 서연에게 이동한 뒤 서연은 민지와 민수를 만나러 간다.” The engine advances visible citizen movement, meeting, taxi call/drive, drone movement, and group rendezvous steps over ticks.
- Updated citizens to support dynamic meeting points and release meetings when a participant receives a new movement/taxi directive, reducing teleport/stuck behavior.
- Added `ScenarioDirectorPanel`, `SCENARIO RUNNING/COMPLETE` HUD labels, scenario camera focus, drone target labels, and a God Mode `연쇄 상황` macro/result display.
- Added `scripts/scenario_directive_smoke.py`; local smoke passed against `http://127.0.0.1:18088` with required step types and visible movement progress.
- Dogfood used `agent-browser` against `http://127.0.0.1:3000` connected to local orchestrator `http://127.0.0.1:18088`; report saved at `dogfood-output/scenario-director-dogfood/report.md`. No reproducible issues were found. Console had React DevTools info plus WebGL ReadPixels performance warnings only.
- RunPod state touched: SSH/GPU verification passed; Docker was not run. A targeted backend/schema/script sync to the remote workspace completed using tar-over-SSH. The earlier full sync attempt was stopped because full tar sync can hang; no Docker/Compose path was attempted.
- Verification passed: `uv run pytest` (48 passed), `uv run ruff check server packages scripts`, `uv run mypy server packages`, `pnpm lint`, `pnpm typecheck`, `pnpm test`, `pnpm test:e2e`, `python3 -m json.tool project/TASKS.json`, `bash -n infra/runpod/*.sh`, `git diff --check`, `python3 scripts/scenario_directive_smoke.py --orchestrator-url http://127.0.0.1:18088 --wait-seconds 12`, and `python3 scripts/browser_demo_smoke.py --mode live --url http://127.0.0.1:3000/ --expected-endpoint http://127.0.0.1:18088`.
- Verification caveat: `pnpm --filter @aetherville/client build` was attempted but manually terminated after the known WSL/Next production build hang at “Creating an optimized production build ...”. Dev server was restarted cleanly and browser smoke/dogfood passed.
- Truthfulness: this makes complex natural-language situations visible and inspectable, but does not mean an LLM directly animates every frame or self-trains model weights.

## M11-003 — RunPod remote demo reflection for Scenario Director — 2026-05-26T03:58:00+09:00

- Status: complete against the active direct-process RunPod demo runtime.
- Targeted tar-over-SSH sync reflected the Scenario Director/shared-schema/server/smoke-script changes into the remote workspace. Full repo sync was avoided because remote `rsync` is unavailable and full tar sync can hang.
- Remote orchestrator was restarted only. Existing real vLLM, real YOLO vision on verified port `18001`, faster-whisper STT, traffic paths, and Redis memory fallback were preserved. Docker, Docker Compose, Docker-in-Docker, and blind Docker retries were not used.
- Remote/tunnel health evidence: orchestrator health ok, `/api/v1/sim/status` reachable, vision `18001` health ok with real YOLO mode, and vLLM `/v1/models` reachable through the local tunnel.
- Scenario smoke passed against `http://127.0.0.1:18080`: six-step story compiled/executed with `move_actor_to_actor`, `meet`, `call_taxi`, `taxi_drive_to_actor`, `drone_move_to_actor`, and `move_actor_to_group`; movement states were observed.
- Local Next dev was restarted on `0.0.0.0:3000` with `NEXT_PUBLIC_ORCHESTRATOR_URL=http://127.0.0.1:18080` and `NEXT_PUBLIC_SOCKET_URL=http://127.0.0.1:18080`. First compile was slow on WSL, but live route warmed successfully and rendered the RunPod tunnel endpoint.
- Browser smoke passed for live route with expected endpoint `http://127.0.0.1:18080`; replay route marker curl passed after compile warmup.
- Truthfulness: this is now a RunPod-backed live demo of bounded ScenarioDirective execution plus vLLM high-level city planning. It is not direct frame-by-frame LLM animation or autonomous model-weight self-training.

## Autonomous City Evolution goal split — 2026-05-26

- Status: planning complete; implementation was not reopened in this step.
- Added a master autonomous-city evolution goal and six dependent phase goals under `.codex/goals/`.
- The goal set defines “완전히 진화한 AI 도시” as a measurable bounded runtime: TaskGraph planning, inspectable entity brains, replanning/resilience, persistent learning/evolution state, causal AI UI observability, and final dogfood audit.
- Truthfulness guard: the plan explicitly forbids claiming model-weight self-training or unbounded AGI unless a separate verified training/checkpoint promotion path exists.
- Docker policy remains unchanged: direct-process runtime only for the verified RunPod path; no Docker/Compose/DinD/blind retries.

## M12-001 — TaskGraph Planner — 2026-05-26T04:50:58+09:00

- Status: complete locally for Goal 12 on branch `feat/llm-driven-city-loop`.
- Added shared TaskGraph contracts: `TaskGraph`, `TaskNode`, `TaskEdge`, `TaskCondition`, `TaskGraphPlan`, and `TaskGraphExecutionSnapshot`, plus generated TypeScript output.
- Implemented deterministic Korean TaskGraph compilation in `server/src/aetherville_server/scenario.py` for bounded actions: citizen movement, location movement, meetings, taxi call/pickup/drive, drone move/deliver, group rendezvous, rain/weather, traffic surge, remember, wait, and no-op.
- Integrated TaskGraph into `SimulationEngine.execute_god_command`: hard unknown/circular commands reject safely with `task_graph_rejected`; accepted complex graphs drive ScenarioDirective execution; simple commands keep old effects while exposing a completed graph.
- `WorldStatePayload.task_graph` now streams accepted/running/completed/rejected graph execution snapshots, synced to ScenarioDirective step status when applicable.
- `ScenarioDirectorPanel` now shows TaskGraph status, current node, assumptions, and rejection reason in addition to the scenario step timeline.
- Added Goal 12 tests for 10 Korean fixture families and runtime response/snapshot exposure.
- Verification passed: `uv run pytest packages/shared-schemas/tests server/orchestrator server/sim` — 56 passed; `uv run ruff check server packages scripts` — pass; `uv run mypy server packages` — pass; `pnpm typecheck` — pass; `pnpm test` — 3 passed; `python3 -m json.tool project/TASKS.json` — pass; `git diff --check` — pass.
- 5090 portability note added at `docs/rtx-5090-taskgraph-portability.md`; local backup created at `.omx/backups/aetherville-goal12-taskgraph-20260526-045058.tar.gz` with checksum `.omx/backups/aetherville-goal12-taskgraph-20260526-045058.tar.gz.sha256`. Secrets/env files are excluded.
- RunPod state: not touched in this turn. Docker/Compose/DinD were not run.


## M13–M17 — Autonomous City Evolution runtime — 2026-05-26T09:56:20+09:00

- Status: complete locally on branch `feat/llm-driven-city-loop`; final broad verification/backup/push follows.
- Goal 13: Added inspectable entity brains to shared schemas and `WorldStatePayload.entity_brains`. Citizens, taxi/vehicles, drones, and traffic lights now expose goal, next action, reason, source, constraints, progress, blocker/fallback, and updated tick. Replay fallback includes representative brain states.
- Goal 14: Added bounded deterministic replanner records and events. Synthetic tests cover actor/vehicle stuck, unreachable target, taxi unavailable, pickup timeout, group timeout, drone delay, low battery, traffic delay, and dependency deadlock. Replanner emits `task_blocked`, `task_replanned`, `task_recovered` and cannot loop indefinitely.
- Goal 15: Extended learning with trajectory events, outcome scores, learning signals, policy bias, and evolution snapshot. Persistence remains JSON-backed deterministic adaptation with `/api/v1/learning/reset`; no model-weight self-training is claimed.
- Goal 16: Added `AI operations` panel with `Entity intent`, `Replan feed`, and `Causal event chain`; strengthened `LearningPanel` with `Evolution state` and truthful “model-weight self-training: not verified” copy.
- Goal 17: Added `docs/autonomous-city-evolution-audit.md` and `scripts/autonomous_city_dogfood_smoke.py`; ten dogfood scenarios passed against a current local direct-process orchestrator on `18081`.
- Verification evidence so far: schema/server sim tests passed (61), ruff passed, mypy passed, pnpm lint/typecheck/test passed, replanner smoke passed, learning/evolution smoke passed, dogfood smoke passed, JSON/diff checks passed.
- RunPod state: current tunnel `http://127.0.0.1:18080` health is reachable; current-branch Goal 13–17 runtime was verified locally on `18081` because `18080` is occupied by the SSH tunnel. Redeploy remote direct-process services before claiming remote Goal 13–17 evidence.
- Docker/Compose/DinD were not run.

## M13–M17 final verification, backup, and push readiness — 2026-05-26T10:19:15+09:00

- Status: complete locally and ready to push on branch `feat/llm-driven-city-loop`.
- Final production client build passed: `pnpm --filter @aetherville/client build`.
- Browser live/replay smoke, visual smoke, and `pnpm test:e2e` passed after the AI operations/evolution UI changes.
- Local 5090 portability backup created at `.omx/backups/aetherville-goals13-17-autonomous-city-20260526-101816.tar.gz` with checksum `a628885b3b6729114069a6d8c5040584147f5aa100d57abf9e02a79fc03cbe1c`; backup path scan passed for secret/env/key filenames, with only the tracked env example file whitelisted.
- Current RunPod tunnel health remains reachable, but Goal 13–17 current-branch code was not redeployed remotely in this final local pass; sync/restart RunPod before presenting remote entity-brain/replan/evolution evidence.
- Docker, Docker Compose, Docker-in-Docker, and blind Docker retries were not run.


## RunPod orchestrator restart and local server bring-up — 2026-05-26T19:30:13+09:00

- Status: complete on branch `feat/llm-driven-city-loop`.
- Synced latest committed Goal 13–17 files to RunPod using targeted tar-over-SSH fallback after full repository tar sync showed the known no-output hang pattern. Remote `rsync` remains unavailable.
- Restarted only the RunPod direct-process orchestrator; existing real vLLM on `8000` and real YOLO vision on verified port `18001` were preserved. Docker, Docker Compose, Docker-in-Docker, and blind Docker retries were not used.
- Verified local tunnel health:
  - `http://127.0.0.1:18080/api/v1/health` reports orchestrator ok, vLLM ok, vision ok, faster-whisper STT ok, JSON learning ok, Redis memory fallback.
  - `http://127.0.0.1:18001/health` reports real Ultralytics YOLO enabled.
  - `http://127.0.0.1:18000/v1/models` reports the real vLLM model endpoint.
- Verified current remote Goal 13–17 state through the tunnel: `city_ai.mode=vllm`, `entity_brains=13`, `learning.evolution` present.
- Remote smokes passed against `http://127.0.0.1:18080`:
  - `scripts/scenario_directive_smoke.py`
  - `scripts/replanner_resilience_smoke.py`
  - `scripts/learning_evolution_smoke.py`
  - `scripts/autonomous_city_dogfood_smoke.py`
- Local browser server is running with tunnel endpoint envs at `http://127.0.0.1:3000/`; WSL network URL observed as `http://172.22.251.143:3000/` for same-machine LAN/Windows access.
- Browser smokes passed for live and replay routes against the local server.

## Repository root cleanup — 2026-05-26T21:20:00+09:00

- Status: complete on branch `feat/llm-driven-city-loop` pending final commit/push.
- Moved tracked project status/spec files from the repository root into `project/` so root now keeps only standard entrypoints and package/tooling files.
- Moved PRD source PDF to `project/source/`, GitHub issue template to `.github/ISSUE_TEMPLATE/`, and Docker Compose portability artifacts to `infra/docker/`.
- Updated `AGENTS.md`, `README.md`, `project/TASKS.json`, and status docs to reference the new paths.
- Local-only `.codex/`, `.agents/`, `codex/`, and `docs/` remain ignored and were not moved to avoid breaking local Codex/OMX/runtime surfaces.
- Docker, Docker Compose, Docker-in-Docker, and blind Docker retries were not run.

## RTX 5090 migration readiness — 2026-05-26T21:31:31+09:00

- Status: prepared on branch `feat/llm-driven-city-loop`; final commit/push follows.
- Added `project/RTX5090_MIGRATION_RUNBOOK.md` with the 4090-before-stop backup gate, 5090 `.env.runpod` setup, safe-smoke deploy, real-demo opt-in deploy, tunnel, health, and smoke gates.
- Added `infra/runpod/create_remote_handoff_backup.sh` to capture the current RunPod workspace and `/tmp/aetherville/learning_state.json` without secrets/model caches/dependency caches.
- Added `infra/runpod/deploy_5090_direct.sh` with `safe-smoke` and guarded `real-demo` profiles. `real-demo` requires `AETHERVILLE_APPROVE_REAL_AI=1` before vLLM/YOLO bootstrap.
- Hardened `infra/runpod/deploy_over_ssh.sh` so repository sync excludes `.omx` backups/caches and dry-run does not incorrectly require local rsync when tar-over-SSH fallback is available.
- Current 4090 SSH/GPU verification passed: RTX 4090 visible, remote workspace present, Docker intentionally skipped, direct-process policy unchanged.
- Remote handoff backup completed locally at `.omx/backups/runpod-remote-handoff-20260526-213131`; archive sha256 `92af4c5911d9d6633c8e34b227917f2eb00a8837cc7c8c21b360be87a810835b`; secret-like path scan passed. The remote archive includes the current remote workspace and runtime learning state, but not model caches or a full pod image.
- Important caveat: 5090 정상작동은 새 5090 팟에서 safe-smoke 및 real-demo health/smoke가 통과한 뒤에만 확정할 수 있다.
- Docker, Docker Compose, Docker-in-Docker, and blind Docker retries were not run.

## H100 direct-process real-demo bring-up — 2026-05-26T22:11:00+09:00

- Status: complete on branch `feat/llm-driven-city-loop`; final commit/push follows.
- Updated local ignored `infra/runpod/.env.runpod` to the new H100 pod values without printing or tracking secrets.
- H100 verification passed: NVIDIA H100 80GB HBM3, driver 580.126.09, CUDA 13.0, 80GB container disk, 250GB `/workspace`, Python 3.11.10. Docker was intentionally skipped.
- Safe-smoke deploy passed on the H100 pod: repository synced via tar-over-SSH, `uv` bootstrapped, mock vLLM, mock vision, orchestrator, simulation, and memory Redis fallback health passed.
- Real-demo deploy passed: vLLM `Qwen/Qwen2.5-14B-Instruct-AWQ` served on `:8000`, real Ultralytics YOLO served on verified vision port `18001`, orchestrator health returned ok with vLLM and vision ok, simulation started and ticking.
- Local SSH tunnel was switched from the previous 4090 pod to the H100 pod on local ports `18080`, `18000`, and `18001`; local health checks passed through the tunnel.
- Verification passed against H100 tunnel: scenario directive smoke, replanner resilience smoke, learning/evolution smoke, autonomous city dogfood smoke, browser live smoke, and browser replay smoke.
- `scripts/replanner_resilience_smoke.py` was hardened to re-fetch world state after timeline recovery events so it no longer races state snapshot propagation.
- Current truthful state: H100 is running real vLLM + real YOLO + deterministic JSON-backed learning/evolution. This is policy/experience self-learning, not live LLM weight fine-tuning.
- Docker, Docker Compose, Docker-in-Docker, and blind Docker retries were not run.

## OPS-H100-002 — Reward-gated policy promotion and H100 dogfood verification — 2026-05-26T23:37:58+09:00

- Status: implemented and verified against the H100 direct-process demo runtime; WSL lint/build caveat cleared after retry.
- Added policy candidate/promotion contracts to shared schemas and generated TypeScript: `PolicyCandidateSnapshot`, `PolicyPromotionSnapshot`, `LearningSnapshot.policy_candidates`, and `LearningSnapshot.promotion_gate`.
- Extended the JSON-backed learning loop with a deterministic reward gate. Every candidate evaluation scores recent taxi/replan/scenario/fallback/weather/traffic experience, records a candidate, and promotes only if the reward improves enough; otherwise the current live policy is retained. UI now shows the active policy, candidate count, promoted/rejected count, latest reward delta, and truthful “promotion-gated learning” copy.
- Fixed a demo-critical fallback gap: commands like “택시 없음 상황에서 민수가 택시를 불러 민지에게 간다” now parse the actual taxi action instead of the availability condition marker, compile into a TaskGraph/ScenarioDirective, and trigger immediate `taxi_unavailable` replan/recovery. Also fixed `taxi_drive_to_actor` timeout blocker return.
- Updated browser impact smoke so a taxi-deferred meeting event counts as valid evidence when the command intentionally schedules a meeting after taxi arrival; visual before/after diff remains required.
- H100 direct-process runtime was redeployed without Docker. Health passed through the local tunnel: orchestrator ok, vLLM ok, vision `18001` ok, simulation running, Redis memory fallback.
- H100/API verification passed: `learning_evolution_smoke`, `scenario_directive_smoke`, `city_ai_smoke`, `replanner_resilience_smoke`, and `autonomous_city_dogfood_smoke` all passed against `http://127.0.0.1:18080`.
- Local browser dogfood/smoke passed after warming slow WSL Next dev compilation: live route DOM smoke, replay route DOM smoke, visual smoke for live/replay screenshots, and impact smoke with before/after visual delta passed against local browser `http://127.0.0.1:3000/` connected to H100 tunnel `http://127.0.0.1:18080`.
- Local validation passed: `uv run pytest -q` (52 passed), targeted/full ruff checks after fixes, `uv run mypy server packages scripts/browser_impact_smoke.py`, `pnpm typecheck`, `pnpm test`, `python3 -m json.tool project/TASKS.json`, and `git diff --check`.
- Verification caveat cleared: after warmup, `pnpm lint` and `pnpm --filter @aetherville/client build` both passed on the WSL `/mnt/d` workspace.
- Docker, Docker Compose, Docker-in-Docker, and blind Docker retries were not run.

### OPS-H100-002 final verification addendum — 2026-05-26T23:52:40+09:00

- WSL warm retry succeeded: `pnpm lint` passed and `NEXT_TELEMETRY_DISABLED=1 timeout 900 pnpm --filter @aetherville/client build` passed.
- Production Next server started with H100 tunnel env on `http://127.0.0.1:3000`.
- Final production browser smokes passed:
  - `python3 scripts/browser_demo_smoke.py --mode live --url http://127.0.0.1:3000/ --expected-endpoint http://127.0.0.1:18080 --timeout-seconds 60`
  - `python3 scripts/browser_demo_smoke.py --mode replay --url http://127.0.0.1:3000/replay --timeout-seconds 60`
- H100 health remained ok after production browser smoke.

## OPS-H100-003 — Guarded model-weight training pipeline — 2026-05-27T00:26:30+09:00

- Status: implementation in progress on `master` after the demo runtime merge.
- Added the missing bridge from JSON-backed reward adaptation to real model-weight training: Experience Log JSONL, target-specific Dataset Builder, guarded trainer command paths, Evaluation Gate, Checkpoint Registry, Promotion/Rollback API, and UI evidence.
- Training targets now have explicit dataset formats: `vllm_lora` chat SFT JSONL, `yolo` pseudo-label manifest JSONL, `traffic_ppo` rollout JSONL, and `traffic_lstm` sequence JSONL.
- Real model-weight trainer execution is intentionally blocked unless `AETHERVILLE_APPROVE_MODEL_TRAINING=1` is set. Dry-run cycles build datasets and evaluation evidence without model downloads or GPU spend.
- Added `/api/v1/training/status`, `/api/v1/training/cycle`, and `/api/v1/training/rollback` to make checkpoint promotion/rollback observable from the orchestrator.
- Updated direct-process RunPod env/start/deploy scripts to carry `AETHERVILLE_TRAINING_DIR` and `AETHERVILLE_APPROVE_MODEL_TRAINING` without Docker.
- Added local scripts for the training cycle plus guarded vLLM LoRA and YOLO self-training entrypoints. PPO/LSTM reuse existing traffic checkpoint trainers behind the same promotion gate.
- Final local verification passed: `uv run pytest -q` (57 passed), `uv run ruff check server packages scripts`, `uv run mypy server packages scripts/model_training_cycle.py scripts/train_vllm_lora.py scripts/train_yolo_self_training.py`, `pnpm lint`, `pnpm typecheck`, `pnpm test`, `pnpm test:e2e`, `pnpm --filter @aetherville/client build`, dry-run training cycle smoke, `python3 -m json.tool project/TASKS.json`, `bash -n infra/runpod/*.sh`, and `git diff --check`.
- Docker, Docker Compose, Docker-in-Docker, and blind Docker retries were not run.
