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
