# SESSION_HANDOFF.md

## Current state

Master goal was re-audited as complete as of 2026-05-24T22:39:21+09:00 after the direct-process runtime strategy patch. All phases Goal 00, Phase 01–10, Phase 99, and the post-audit direct-process hardening pass have completion evidence.

Post-audit note: cloud runtime strategy is now explicitly documented as direct-process runtime. Docker is optional future packaging/portability documentation only and is not a current execution dependency.

## Final verification summary

- `git status --short`: ran; workspace files are untracked because this is a generated/new implementation workspace.
- `uv run pytest`: pass, 29 tests.
- `uv run pytest packages server`: pass, 52 tests.
- `uv run ruff check server packages scripts`: pass.
- `uv run mypy server packages`: pass.
- `pnpm lint`: pass.
- `pnpm typecheck`: pass.
- `pnpm test`: pass, 3 Node tests.
- `pnpm test:e2e`: pass, 1 replay fallback test.
- `pnpm --filter @aetherville/client build`: pass, `/` and `/replay` routes built.
- Client start smoke: pass on local port 3100 for `/` and `/replay`.
- RunPod SSH/GPU verification: pass.
- RunPod direct-process health: pass.
- RunPod final integration smoke: pass for REST world state, vehicle camera, vision detect, God Mode weather command, and Socket.IO polling state update.
- Re-audit local verification after script/doc hardening: pass for Python tests, ruff, mypy, pnpm lint/typecheck/test/e2e/build, and local client start smoke.
- Re-audit RunPod verification: pass with Docker commands skipped by policy.

## Verified RunPod state

- Docker daemon unavailable; direct-process runtime is active.
- The RunPod pod itself is the execution environment.
- Orchestrator: `:8080`.
- vLLM fallback: `:8000`.
- Vision: `:18001` because template nginx occupies `:8001`.
- Redis: memory fallback.
- GPU: RTX 4090 visible; no compute process during final verification.
- No real model/training/GPU workload was started.
- `verify_runpod.sh` no longer invokes Docker commands for this verified pod.
- `deploy_over_ssh.sh --mode compose` fails fast as unsupported for the current execution path.

## Residual risks

- Public RunPod URL/WSS endpoint exposure is not configured in tracked files.
- Vision architecture port `8001` still needs proxy/freeing/RunPod mapping before a public demo uses the canonical port.
- Real vLLM, YOLO, PPO/LSTM, and STT integrations are documented upgrade paths, not active workloads.
- Remote sync uses tar-over-SSH fallback because remote `rsync` is unavailable.
- Do not attempt Docker daemon setup, Docker Compose execution, Docker-in-Docker, or blind Docker retries on the current RunPod.

## Demo commands

```bash
uv run pytest packages server
pnpm lint
pnpm typecheck
pnpm test
pnpm test:e2e
pnpm dev
```

Open:

- Live city: `http://localhost:3000/`
- Replay fallback: `http://localhost:3000/replay`

RunPod checks:

```bash
bash infra/runpod/verify_runpod.sh
AETHERVILLE_VISION_PORT=18001 AETHERVILLE_REDIS_MODE=memory bash infra/runpod/health_check_direct.sh
```

Next autonomous direct-process milestone:

- If continuing beyond the completed master goal, keep using `infra/runpod/deploy_over_ssh.sh --mode direct`, `infra/runpod/start_direct_processes.sh`, and `infra/runpod/health_check_direct.sh`.
- Candidate next milestone: configure/document public REST/WSS endpoint exposure for the already verified direct-process services without introducing Docker as a dependency.

## Final demo freeze addendum — 2026-05-24T23:03:56+09:00

- Added live demo runbook: `docs/live-demo-runbook.md`.
- Added 15-minute script: `docs/demo-script-15min.md`.
- Demo connection modes are now documented:
  - Mode A: public RunPod endpoint.
  - Mode B: SSH tunnel to local `127.0.0.1:18080` for orchestrator and `127.0.0.1:18001` for vision.
- Direct-process scripts and examples now default the verified vision service path to port `18001` for the current pod.
- Local client demo envs:
  - public mode: set `NEXT_PUBLIC_ORCHESTRATOR_URL` and `NEXT_PUBLIC_SOCKET_URL` from ignored local RunPod public URL envs.
  - tunnel mode: set both to `http://127.0.0.1:18080`.
- Docker remains excluded from the current demo path.

Final demo freeze verification:

- `python3 -m json.tool TASKS.json`: pass.
- `bash -n infra/runpod/*.sh`: pass.
- `git diff --check`: pass.
- `pnpm typecheck`: pass.
- `pnpm --filter @aetherville/client build`: pass.
- SSH tunnel smoke with `scripts/demo_smoke.py`: pass against local tunnel endpoint.


## User-accepted final demo risks — 2026-05-24T23:51:11+09:00

The user approved the remaining operational risks for the live demo:

- Public RunPod REST/WSS URL not tracked; use local ignored env or SSH tunnel.
- Vision uses verified `18001` because canonical `8001` is blocked on this pod.
- Real vLLM/YOLO/PPO/LSTM/STT remain opt-in and require a separate explicit start request.
- tar-over-SSH sync fallback is accepted while remote `rsync` is unavailable.

Continue demo operation with `docs/live-demo-runbook.md`; do not start real model workloads or Docker without a new explicit request.

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

## Tagged grid / live stage handoff — 2026-05-25T06:05:46+09:00

Current demo state:

- Local client dev server is running on `http://127.0.0.1:3000` with explicit tunnel envs:
  - REST/socket: `http://127.0.0.1:18080`
  - Socket transport: `polling`
- RunPod direct-process services were redeployed and health-checked without Docker.
- Simulation is running; latest verified REST status reported 7 citizens, 3 vehicles, and 4 traffic lights.
- Live God Mode smoke passed for:
  - `민지랑 민수가 만난다`
  - `민지가 택시를 불러줘`
- Live browser smoke passed after waiting for polling connection: `connected`, tick advanced, and visual tags appeared in the city scene.
- Screenshot evidence: `/tmp/aetherville-live-grid-tags-connected.png`.

Operational notes:

- If the browser appears stale or styles do not change, kill the local Next dev process, remove `client/.next`, and restart `pnpm --filter @aetherville/client exec next dev -H 0.0.0.0 -p 3000` with the `NEXT_PUBLIC_*` tunnel envs. WSL/Next file watching did not always hot-reload CSS reliably.
- Keep using direct-process runtime only. Do not run Docker, Docker Compose, or Docker-in-Docker on the current RunPod pod.
- Current vision demo endpoint remains `18001`; `/api/v1/health` on vision returned 404 while `/health` returned ok.

## God Mode event feedback handoff — 2026-05-25T07:29:15+09:00

Current demo behavior after the latest patch:

- Open the Windows-accessible WSL URL, currently `http://172.22.251.143:3000/`.
- Use God Mode shortcuts:
  - `비 내리기`: visible rain streak overlay plus `RAIN ACTIVE · 비 내리는 중`; weather stays rain for the demo window.
  - `택시 호출`: taxi `v01` changes from a route loop into an active dispatch with tags like `민지에게 이동` / `민지 탑승`.
  - `차량 정체`: red traffic-surge overlay appears, vehicles show `정체/저속`, and the forecast panel switches to high-congestion styling.
- Latest browser evidence: `/tmp/aetherville-event-feedback-final.png`.
- Latest runtime smoke after deploy: weather remained `rain` after delay, infrastructure status was `traffic congestion active`, `v01` tag included `택시 호출` and `민지 탑승`, `v02` tag included `정체/저속`, and forecast indices were near/at `1.0`.
- Keep using direct-process runtime only. Do not run Docker, Docker Compose, or Docker-in-Docker on the current RunPod pod.

## Mini-GTA live city polish handoff — 2026-05-25T08:44:38+09:00

Current demo state:

- RunPod direct-process services were redeployed after the traffic command classification fix; Docker was not used.
- Local production client was rebuilt with current `NEXT_PUBLIC_*` tunnel endpoints and is running at the current WSL URL `http://172.22.251.143:3000/` while this session remains active.
- Verified God Mode shortcut sequence for demo:
  - `비 내려줘` -> rain badge/overlay plus in-scene rain streaks.
  - `민지가 택시를 부르게 해줘` -> taxi dispatch tags and pulsing taxi ring.
  - `교통량 증가시켜` -> infrastructure congestion, slow/queued vehicles, red traffic overlay, high forecast.
- Latest screenshot evidence: `/tmp/aetherville-mini-gta-envbuild.png`.
- If the local client is restarted in production mode, rebuild with the same `NEXT_PUBLIC_ORCHESTRATOR_URL`, `NEXT_PUBLIC_SOCKET_URL`, and `NEXT_PUBLIC_SOCKET_TRANSPORTS=polling` values first; for dev mode those envs can be provided at start.
- Keep using direct-process runtime only. Do not run Docker, Docker Compose, or Docker-in-Docker on this RunPod pod.

## Persistent AI learning handoff — 2026-05-25T11:47:49+09:00

Current implementation state:

- The city now includes a demo-safe persistent learning/adaptation loop.
- Learning state is stored by default at `AETHERVILLE_RUN_DIR/learning_state.json` or `AETHERVILLE_LEARNING_PATH` if configured.
- `/api/v1/learning/status` returns the current learning snapshot and explains the real upgrade path.
- `WorldStatePayload.learning` is emitted through REST and Socket.IO state updates.
- The browser shows `AI 학습 루프` under the city panels.
- God Mode commands that visibly feed learning:
  - `교통량 증가시켜` / `차량 정체` -> raises learned traffic pressure and slows future vehicles.
  - `민지가 택시를 불러줘` -> raises taxi dispatch success signal.
  - `도시에 비를 내려줘` -> raises weather adaptation signal.
  - `민지랑 민수가 만난다` or memory commands -> raises citizen memory signal.

Operational notes:

- This is not real model self-training; do not claim new neural weights are being trained live.
- Keeping the server running accumulates deterministic event experience and policy metadata; real PPO/LSTM/vLLM/YOLO/STT training remains opt-in.
- Keep using direct-process runtime only. Do not run Docker, Docker Compose, Docker-in-Docker, or blind Docker retries on this RunPod pod.

## Persistent AI learning deployed handoff — 2026-05-25T12:06:00+09:00

Current demo runtime:

- RunPod direct-process services are freshly redeployed and healthy.
- Local tunnel endpoints currently verified:
  - Orchestrator REST/Socket.IO: `http://127.0.0.1:18080`
  - Vision: `http://127.0.0.1:18001`
- Local production client is running on `http://127.0.0.1:3000/` / WSL network URL if needed, rebuilt with `NEXT_PUBLIC_ORCHESTRATOR_URL=http://127.0.0.1:18080`, `NEXT_PUBLIC_SOCKET_URL=http://127.0.0.1:18080`, and `NEXT_PUBLIC_SOCKET_TRANSPORTS=polling`.
- Latest learning smoke after three God Mode commands:
  - `experience_count=6`
  - `adaptation_epoch=2`
  - `policy_version=adaptive-demo-v2`
  - `traffic_bias=0.12`
  - `taxi_success_rate=0.59`
- The presenter can now answer: the current demo improves via persistent deterministic event adaptation while the server stays up; it is not real model self-training.

If restarting:

1. Keep tunnel open or start Mode B from `docs/live-demo-runbook.md`.
2. Rebuild/start client with the same `NEXT_PUBLIC_*` values if using production mode.
3. Verify `curl http://127.0.0.1:18080/api/v1/learning/status` before presenting the AI learning panel.
4. Do not run Docker, Docker Compose, Docker-in-Docker, or real model training without a separate explicit request.

## Real 4090 vLLM handoff — 2026-05-25T13:02:41+09:00

Current GPU state:

- Real vLLM is active on the RunPod RTX 4090 through direct-process runtime.
- Served model: `Qwen/Qwen2.5-14B-Instruct-AWQ`.
- Runtime pins for this pod: `vllm==0.10.2`, `transformers==4.55.4`, Torch CUDA 12.8.
- Model cache: `/workspace/aetherville-model-cache`.
- Local tunnel checks:
  - `http://127.0.0.1:18000/v1/models` returns the Qwen 14B AWQ model.
  - `http://127.0.0.1:18080/api/v1/health` reports `vllm:ok`.
  - `POST http://127.0.0.1:18080/api/v1/citizens/c01/reflect` uses real vLLM when orchestrator is started with `AETHERVILLE_LLM_MODE=vllm`.

Operational notes:

- Do not run `uv run` manually on the remote workspace for inspection unless needed; it may sync the project environment. Prefer `.venv/bin/python` for package version checks.
- If restarting real vLLM, use:
  `AETHERVILLE_VLLM_MODE=real AETHERVILLE_LLM_MODE=vllm AETHERVILLE_SKIP_UV_SYNC=1 AETHERVILLE_BOOTSTRAP_VLLM=1 AETHERVILLE_VLLM_INSTALL_PACKAGE="vllm==0.10.2" AETHERVILLE_VLLM_COMPAT_PACKAGE="transformers==4.55.4" MODEL_NAME=Qwen/Qwen2.5-14B-Instruct-AWQ VLLM_EXTRA_ARGS="--gpu-memory-utilization 0.88 --max-model-len 4096" bash infra/runpod/deploy_over_ssh.sh --mode direct`
- If CUDA/driver errors return, keep the vLLM and transformers pins; do not upgrade to latest vLLM blindly.
- Docker remains excluded from the current pod path.

## Real YOLO vision handoff — 2026-05-25T13:14:53+09:00

Current vision state:

- Vision service supports real YOLO when started with `AETHERVILLE_VISION_MODE=real`.
- Current model: `yolo11n.pt` loaded through Ultralytics.
- Current package: `ultralytics 8.4.53` in the RunPod uv environment.
- Current device: `AETHERVILLE_YOLO_DEVICE=0`.
- Local tunnel smoke:
  - `curl http://127.0.0.1:18001/health` reports `yolo:ok`.
  - `POST http://127.0.0.1:18001/detect` with no frame returns `mode=real`; the service creates a deterministic synthetic road frame for smoke.
- Real vLLM remains active simultaneously on `:8000`; keep VRAM pressure in mind before adding PPO/STT jobs.

Restart command pattern:

`AETHERVILLE_VLLM_MODE=real AETHERVILLE_LLM_MODE=vllm AETHERVILLE_VISION_MODE=real AETHERVILLE_BOOTSTRAP_YOLO=1 AETHERVILLE_YOLO_MODEL=yolo11n.pt AETHERVILLE_YOLO_DEVICE=0 AETHERVILLE_SKIP_UV_SYNC=1 bash infra/runpod/deploy_over_ssh.sh --mode direct`

Do not run Docker on this pod.

## Real YOLO camera panel handoff — 2026-05-25T13:22:50+09:00

Current implementation state:

- `/api/v1/vehicles/v01/camera` is still cheap/mock by default.
- Set `AETHERVILLE_CAMERA_VISION_MODE=real` or start direct processes with `AETHERVILLE_VISION_MODE=real` to enrich the camera endpoint through vision `/detect`.
- The browser vehicle camera panel polls the orchestrator camera endpoint every ~3.5 seconds and shows `REAL YOLO · RunPod 4090` when `VehicleCameraFrame.mode` is `real`.
- If real YOLO fails, the panel falls back to world-state mock detections so the demo does not break.

Next operator check after redeploy:

```bash
curl -fsS http://127.0.0.1:18080/api/v1/vehicles/v01/camera | python3 -m json.tool
```

Expected real-mode marker: `"mode": "real"` and at least one traffic-relevant detection from the vision service.

## Real YOLO camera panel deployment handoff — 2026-05-25T13:35:02+09:00

Verified runtime state:

- RunPod direct-process services are running without Docker.
- Existing real vLLM and real YOLO processes were preserved; orchestrator was restarted with the new camera enrichment path.
- Local tunnel endpoints verified:
  - orchestrator: `http://127.0.0.1:18080`
  - vLLM: `http://127.0.0.1:18000/v1`
  - vision: `http://127.0.0.1:18001`
- `/api/v1/vehicles/v01/camera` returned `mode: real` and a `traffic light` detection.
- Simulation is running; recent God Mode smokes activated rain, traffic congestion, and taxi dispatch.
- Local browser client is running on `http://127.0.0.1:3000/` with tunnel endpoint envs.

Demo talking point:

- The vehicle panel is no longer just a state-embedded mock overlay. It polls the orchestrator camera endpoint; in real mode the endpoint calls the RunPod vision service and badges `REAL YOLO · RunPod 4090` in the browser.

## Real traffic policy checkpoint handoff — 2026-05-25T13:50:33+09:00

Current runtime state:

- RunPod direct-process services are running without Docker.
- Real vLLM and real YOLO remain active.
- Traffic policy checkpoint exists under the RunPod model cache and was trained with `torch_cuda` on the RTX 4090.
- Orchestrator is running with `AETHERVILLE_TRAFFIC_POLICY_CHECKPOINT` set to that checkpoint.
- Local tunnel smoke showed:
  - `traffic_ai.mode`: `checkpoint`
  - `traffic_ai.trained_on_gpu`: `true`
  - `traffic_ai.training_backend`: `torch_cuda`
  - `traffic_ai.improvement_pct`: `31.628`
  - first traffic-light tags include `AI정책:checkpoint`

Demo talking point:

- The traffic panel is no longer only fixed-cycle/fallback. When the checkpoint is active, it shows `GPU POLICY` and the signal phase comes from the JSON checkpoint trained on the RunPod 4090. Full PPO/LSTM remains the next heavier upgrade path.

## Local client after traffic policy update — 2026-05-25T13:58:30+09:00

- Local client dev server is running on `http://127.0.0.1:3000/` with tunnel endpoint environment values.
- `/` and `/replay` HTTP smokes passed after recompilation.
- The traffic panel source now reads shared `traffic_ai` state and should show `GPU POLICY` when connected to the current RunPod orchestrator.

## Real LSTM forecast checkpoint handoff — 2026-05-25T14:09:29+09:00

Current runtime state:

- RunPod direct-process services are running without Docker.
- Real vLLM, real YOLO, traffic policy checkpoint, and LSTM forecast checkpoint are active together.
- LSTM forecast checkpoint path is under the RunPod model cache and was trained with `torch_cuda` on the RTX 4090.
- Orchestrator is running with both traffic checkpoint env vars set.
- Local tunnel smoke showed:
  - `traffic_forecast_ai.mode`: `lstm_checkpoint`
  - `traffic_forecast_ai.trained_on_gpu`: `true`
  - `traffic_forecast_ai.training_backend`: `torch_cuda`
  - `traffic_forecast_ai.mape`: `11.84`

Demo talking point:

- The traffic panel now has two real AI markers: `GPU POLICY` for signal control and `LSTM FORECAST` for congestion prediction. Runtime inference is exported-weight/pure-Python, so the demo remains stable even while vLLM and YOLO are active.

## Local client after LSTM forecast update — 2026-05-25T14:18:40+09:00

- Local client dev server is running on `http://127.0.0.1:3000/` with tunnel endpoint environment values.
- `client/.next` was cleared before restart to resolve a stale missing chunk error.
- `/` and `/replay` HTTP smokes passed after recompilation.
- The traffic panel source now reads both `traffic_ai` and `traffic_forecast_ai`; when connected to the current RunPod state it should show `GPU POLICY` and `LSTM FORECAST` badges.

## Real vLLM God Mode interpretation handoff — 2026-05-25T14:27:17+09:00

Current implementation state:

- God Mode text is still the reliable primary path; voice/STT remains optional/deferred.
- Set `AETHERVILLE_GOD_MODE_LLM=vllm` when starting the direct-process orchestrator to classify presenter commands through the real RunPod vLLM endpoint.
- The vLLM classifier is constrained to a fixed safe action vocabulary and cannot directly mutate simulation state. The deterministic dispatcher still applies all world effects.
- `GodCommandResponse.ai_mode` reports `vllm` or `rules`; `ai_confidence` and `ai_reason` are shown in the browser command result.
- If vLLM is slow, unreachable, or returns invalid JSON, God Mode falls back to the existing rules path so the demo remains usable.

Next operator check after redeploy:

```bash
curl -fsS -H 'content-type: application/json' \
  -d '{"kind":"god_command","input_modality":"text","raw_text":"출근길을 혼잡하게 만들어줘","audio_blob_b64":null,"user_id":"presenter"}' \
  http://127.0.0.1:18080/api/v1/god/command | python3 -m json.tool
```

Expected marker when enabled: `"ai_mode": "vllm"` and `"action": "traffic_jam"` inside event metadata. If marker is `rules`, check `AETHERVILLE_GOD_MODE_LLM` and vLLM health. Do not run Docker on this pod.

## Real vLLM God Mode deployment handoff — 2026-05-25T14:42:00+09:00

Verified runtime state:

- RunPod direct-process services are running without Docker.
- Real vLLM and real YOLO stayed resident; only the orchestrator was restarted after sync.
- Orchestrator is now running with:
  - `AETHERVILLE_LLM_MODE=vllm`
  - `AETHERVILLE_GOD_MODE_LLM=vllm`
  - `AETHERVILLE_CAMERA_VISION_MODE=real` inherited from vision mode
  - traffic policy and LSTM forecast checkpoint paths under the RunPod model cache
- Local tunnel God Mode smoke returned `ai_mode=vllm`, event action `traffic_jam`, and confidence `1.0` for “출근길을 혼잡하게 만들어줘”.
- Local browser server is running on `http://127.0.0.1:3000/` via `next start` with tunnel `NEXT_PUBLIC_ORCHESTRATOR_URL` and `NEXT_PUBLIC_SOCKET_URL` values.

Demo talking point:

- God Mode is no longer only keyword matching in the real-AI demo mode. Natural text is first interpreted by the real RunPod vLLM into a constrained action vocabulary, then the deterministic dispatcher applies visible weather/taxi/traffic/relationship/person effects. If vLLM fails, the UI reports `rules fallback` and the demo remains safe.

Do not run Docker, Docker Compose, Docker-in-Docker, or blind Docker retries on this pod.

## Multi-action God Mode handoff — 2026-05-25T14:51:04+09:00

Current implementation state:

- God Mode can now decompose one natural-language command into up to four safe actions.
- Real vLLM mode should return `ai_actions`, for example `rain + traffic_jam + taxi_call + meeting`.
- The simulation applies all deterministic sub-effects, records their concrete events, and adds a final `god_command_executed` summary event.
- Rules fallback also handles obvious combined Korean commands, so use this presenter command for a strong demo smoke:

```bash
curl -fsS -H 'content-type: application/json' \
  -d '{"kind":"god_command","input_modality":"text","raw_text":"도시에 비를 내리고 민지가 택시를 부르게 하고 출근길을 혼잡하게 만들고 민수와 만나게 해줘","audio_blob_b64":null,"user_id":"presenter"}' \
  http://127.0.0.1:18080/api/v1/god/command | python3 -m json.tool
```

Expected markers after RunPod redeploy: `ai_mode="vllm"`, at least three `ai_actions`, visible rain, congestion tags, taxi dispatch, and meeting/talking state. Do not run Docker on this pod.

## Multi-action God Mode deployment handoff — 2026-05-25T15:08:57+09:00

Verified runtime state:

- RunPod direct-process services are running without Docker.
- Real vLLM, real YOLO, traffic policy checkpoint, and LSTM forecast checkpoint remain active.
- Orchestrator was restarted after sync and now merges vLLM semantic actions with obvious literal command cues, preventing missed visible cues like “비” in multi-action prompts.
- Verified smoke command returned `ai_actions=[rain, traffic_jam, taxi_call, meeting]`, event kind `god_command_executed`, and 9 events.
- Verified state after smoke:
  - weather: `rain`
  - infrastructure: `traffic congestion active`
  - taxi v01 passenger: `c01`
  - congestion tags present on vehicle v02
  - 민지 and 민수 are mutually talking
- Local browser server is running on `http://127.0.0.1:3000/` through `next start` with tunnel endpoint values.

Presenter command to use:

`도시에 비를 내리고 민지가 택시를 부르게 하고 출근길을 혼잡하게 만들고 민수와 만나게 해줘`

Do not run Docker, Docker Compose, Docker-in-Docker, or blind Docker retries on this pod.

## God Mode voice/STT handoff — 2026-05-25T15:15:03+09:00

Current implementation state:

- The browser `Voice STT` button records microphone audio with `MediaRecorder` and sends it to `/api/v1/god/voice`.
- The server turns the transcript into a voice `GodCommand`, so voice and text share the same real vLLM multi-action dispatcher and deterministic effect safety rails.
- Default STT mode is fallback/stub. Real STT is opt-in with `AETHERVILLE_STT_MODE=faster_whisper`; startup can install the optional package with `AETHERVILLE_BOOTSTRAP_STT=1`.
- The browser sends the current text input as `fallback_transcript` so the demo remains usable when microphone permission, browser codecs, or model runtime fail.
- Do not claim verified real audio transcription until a real audio smoke returns `stt_status=ok`; fallback status is explicitly reported as fallback.

Smoke command without real audio:

```bash
curl -fsS -H 'content-type: application/json' \
  -d '{"kind":"voice_command","audio_blob_b64":null,"mime_type":"audio/webm","user_id":"presenter","fallback_transcript":"도시에 비를 내리고 민지가 택시를 부르게 해줘","language":"ko"}' \
  http://127.0.0.1:18080/api/v1/god/voice | python3 -m json.tool
```

Expected marker in fallback mode: `stt_status="fallback"` and nested `command.accepted=true`. Do not run Docker on this pod.

## God Mode voice/STT deployment handoff — 2026-05-25T15:38:00+09:00

Verified runtime state:

- RunPod direct-process services are running without Docker.
- Real vLLM, real YOLO, traffic policy checkpoint, LSTM forecast checkpoint, and optional faster-whisper STT config are active together.
- Orchestrator health reports STT dependency `ok` with `faster-whisper configured model=base device=cuda`.
- Local tunnel endpoints verified:
  - orchestrator: `http://127.0.0.1:18080/api/v1/health`
  - vision: `http://127.0.0.1:18001/health`
  - vLLM: `http://127.0.0.1:18000/v1/models`
- Voice fallback smoke passed with `stt_status=fallback`, `stt_mode=fallback`, nested `command.accepted=true`, `ai_mode=vllm`, and `ai_actions=[rain, taxi_call]`.
- Simulation is running after restart; `/api/v1/sim/status` advanced ticks with `running=true`.
- Local browser server is running on `http://127.0.0.1:3000/` via `next start` with tunnel endpoint values; `/` and `/replay` HTTP smokes passed.

Presenter guidance:

- Use the typed God Mode command for the most reliable live effect: `도시에 비를 내리고 민지가 택시를 부르게 하고 출근길을 혼잡하게 만들고 민수와 만나게 해줘`.
- The `Voice STT` button now records and calls `/api/v1/god/voice`; if the result shows `fallback`, say the demo used the typed fallback transcript. Only claim real STT when a real audio submission returns `stt_status=ok`.
- Do not run Docker, Docker Compose, Docker-in-Docker, or blind Docker retries on this pod.

## Real audio STT smoke handoff — 2026-05-25T15:49:00+09:00

Verified runtime state:

- RunPod direct-process orchestrator is still healthy with STT dependency `ok` and faster-whisper configured on CUDA.
- Server-side real-audio STT is now verified, not only fallback: `scripts/voice_stt_smoke.py` posted a temporary Korean WAV through `/api/v1/god/voice` and received `stt_status=ok`, `stt_mode=faster_whisper`, transcript match, `command.accepted=true`, `ai_mode=vllm`, and `ai_actions=[rain, taxi_call]`.
- The temporary audio file was outside the repository and was not committed.

Operator command shape for repeat smoke:

```bash
python3 scripts/voice_stt_smoke.py \
  --orchestrator-url http://127.0.0.1:18080 \
  --audio-file /tmp/aetherville_voice_ko.wav \
  --mime-type audio/wav \
  --expect-status ok
```

Presentation truthfulness:

- Server-side faster-whisper STT is verified with a real audio blob.
- Live browser microphone still depends on browser permission/codecs; claim it as real microphone STT only when the UI/API response shows `stt_status=ok`.
- Do not run Docker, Docker Compose, Docker-in-Docker, or blind Docker retries on this pod.

## Browser demo endpoint/runtime handoff — 2026-05-25T16:12:00+09:00

Verified local client state:

- `next build` now reports the live `/` route as dynamic server-rendered on demand.
- `next start` was launched with tunnel `NEXT_PUBLIC_*` values and rendered `http://127.0.0.1:18080` in the live endpoint grid.
- `scripts/browser_demo_smoke.py --mode live --url http://127.0.0.1:3000/ --expected-endpoint http://127.0.0.1:18080` passed: required demo panels were present and no client-side application error marker appeared.
- `scripts/browser_demo_smoke.py --mode replay --url http://127.0.0.1:3000/replay` passed.
- Replay mode passes `orchestratorUrl=null`, so it stays deterministic and does not accidentally call live camera/God Mode endpoints.

Use this browser smoke before presenting because plain `curl /` cannot catch hydrated client-side errors or stale endpoint rendering.
