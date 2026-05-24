# Project Aetherville gstack + dogfood audit

Date: 2026-05-25T00:36:00+09:00
Mode: report-only QA using gstack QA rubric plus dogfood browser exploration.
Runtime: local Next.js client connected to verified RunPod direct-process services through local tunnel endpoints.
Docker: not used.

## Verdict

**RESOLVED for the approved playable demo.** Base city, replay fallback, RunPod direct-process health, Socket.IO polling, God Mode text commands, replay discoverability, and mobile first-viewport polish are now verified after the risk-resolution patch.

Original audit findings are kept below for traceability. The resolution pass added FastAPI CORS for local demo origins, kept the client request typed against the shared `GodCommand` schema, made polling the default quiet Socket.IO transport, added visible replay navigation, and adjusted the mobile layout so the connection status no longer overlays the city scene.

## Evidence artifacts

| Artifact | Path |
|---|---|
| gstack QA report | `.gstack/qa-reports/aetherville-20260525-002316/report.md` |
| gstack baseline JSON | `.gstack/qa-reports/aetherville-20260525-002316/baseline.json` |
| dogfood report | `dogfood-output/aetherville-20260525-002316/report.md` |
| screenshots | `dogfood-output/aetherville-20260525-002316/screenshots/` |
| issue video | `dogfood-output/aetherville-20260525-002316/videos/issue-001-godmode-cors-contract-repro.webm` |
| runtime curl evidence | `dogfood-output/aetherville-20260525-002316/runtime-health-curls.txt` |
| God Mode CORS/schema curl evidence | `dogfood-output/aetherville-20260525-002316/god-command-cors-curl.txt` |
| Socket.IO smoke evidence | `dogfood-output/aetherville-20260525-002316/socketio-smoke.txt` |
| demo smoke output | `dogfood-output/aetherville-20260525-002316/demo-smoke.txt` |

Raw artifact directories are intentionally ignored by git after this audit because they are local generated QA outputs.

## Requirement-to-evidence matrix

| Requirement | Evidence | Result |
|---|---|---|
| Use gstack for QA | gstack repo found and global Codex skills registered under `~/.codex/skills/gstack-*`; `browse` resolves to the gstack binary through `~/.local/bin`; `browse status` is healthy | Pass; former host-tool browser issue repaired |
| Use dogfood for UI exploration | `agent-browser` dogfood session `aetherville-dogfood-20260525`; screenshots/video/report in `dogfood-output/aetherville-20260525-002316` | Pass |
| Home live UI loads | `curl http://127.0.0.1:3000/` 200; `dogfood-home-initial.png` | Pass |
| Replay fallback loads | `curl http://127.0.0.1:3000/replay` 200; `dogfood-replay-initial.png` | Pass |
| RunPod orchestrator REST health | `runtime-health-curls.txt` shows `18080/api/v1/health` 200 | Pass |
| Simulation status | `runtime-health-curls.txt` shows `18080/api/v1/sim/status` 200 | Pass |
| Vision health uses verified `18001` | `runtime-health-curls.txt` shows `18001/health` 200 | Pass |
| Socket.IO/WSS or polling smoke | `socketio-smoke.txt` shows polling handshake 200; risk-resolution browser run showed `transport: polling` and empty console/errors | Pass |
| God Mode connected command path | Original browser repro showed CORS/schema failure; risk-resolution pass shows CORS preflight 200 and POST 200 with shared `GodCommand` payload | Pass after fix |
| Responsive demo surface | Desktop/tablet/mobile screenshots captured; risk-resolution mobile screenshot shows the connection card no longer overlays the city scene | Pass after polish |
| Security/secret handling | Commands avoided `.env.runpod`, SSH key paths, tokens, and Docker | Pass |

## Issues found

### HIGH: God Mode connected command path blocked

- User-visible result: UI says `connection: connected`, but after `실행` it displays offline fallback instead of live command execution.
- Browser evidence: `dogfood-output/aetherville-20260525-002316/screenshots/issue-001-video-result-fallback.png` and `dogfood-output/aetherville-20260525-002316/videos/issue-001-godmode-cors-contract-repro.webm`.
- Console evidence: `dogfood-output/aetherville-20260525-002316/issue-001-video-console.txt`.
- API evidence: `dogfood-output/aetherville-20260525-002316/god-command-cors-curl.txt` shows preflight `405 Method Not Allowed`; direct POST with client-shaped `command` body returns `422` because shared schema fields are missing.
- Demo impact: blocker if the 15-minute script claims live connected God Mode. Workaround is to present it honestly as offline/replay fallback until fixed.

### MEDIUM: Replay fallback is not discoverable in UI

- `/replay` works directly, but the home UI exposes no anchor/link to it.
- Evidence: `dogfood-output/aetherville-20260525-002316/dom-counts-accessibility.txt` reports `anchors: 0` and `dogfood-output/aetherville-20260525-002316/screenshots/dogfood-home-initial.png` has no visible replay entry point.
- Demo impact: operator must know the direct route from the runbook.

### LOW: Socket.IO WebSocket upgrade warning

- Clean home load emits a WebSocket closed warning, while polling handshake succeeds.
- Evidence: `dogfood-output/aetherville-20260525-002316/home-console-clean.txt`, `dogfood-output/aetherville-20260525-002316/socketio-smoke.txt`.
- Demo impact: not user-visible, but noisy during QA and can be misread as live connectivity failure.

### LOW: Mobile first viewport is crowded

- At `390x844`, oversized hero text and the floating status pill crowd the city scene.
- Evidence: `dogfood-output/aetherville-20260525-002316/screenshots/dogfood-home-mobile-390x844.png`.
- Demo impact: prefer desktop for the live presentation.

## Commands run

```bash
git status --short --branch --untracked-files=all
command -v gstack
/home/chamdom/gstack/browse/dist/browse --help
/home/chamdom/gstack/browse/dist/browse goto http://127.0.0.1:3000/
agent-browser --session aetherville-dogfood-20260525 open http://127.0.0.1:3000/
agent-browser --session aetherville-dogfood-20260525 screenshot --annotate dogfood-output/aetherville-20260525-002316/screenshots/dogfood-home-initial.png
agent-browser --session aetherville-dogfood-20260525 snapshot -i
agent-browser --session aetherville-dogfood-20260525 record start dogfood-output/aetherville-20260525-002316/videos/issue-001-godmode-cors-contract-repro.webm
curl http://127.0.0.1:18080/api/v1/health
curl http://127.0.0.1:18080/api/v1/sim/status
curl http://127.0.0.1:18001/health
curl 'http://127.0.0.1:18080/socket.io/?EIO=4&transport=polling&t=aetherville_dogfood'
python3 scripts/demo_smoke.py --orchestrator-url http://127.0.0.1:18080
```

## Original next actions status

1. God Mode CORS/schema contract: **resolved**.
2. Replay/fallback link: **resolved**.
3. Socket.IO warning: **resolved for demo** by defaulting to polling, with WSS still opt-in by env.
4. Mobile polish: **resolved for first-viewport demo use**.
5. Local gstack `browse` host issue: **resolved**. gstack Codex skills are linked globally, `bun` now resolves to the non-snap user install, and `browse status` starts healthy through the gstack binary.

## Verification after report write

| Command | Result |
|---|---|
| `python3 -m json.tool TASKS.json` | PASS |
| `git diff --check` | PASS |
| `pnpm typecheck` | PASS |
| `pnpm test` | PASS, 3 client tests |
| `pnpm test:e2e` | PASS, 1 replay fallback E2E test |
| `uv run pytest` | PASS, 29 Python tests |
| `python3 scripts/demo_smoke.py --orchestrator-url http://127.0.0.1:18080` | PASS, health ok with 20 citizens and 1 vehicle |

## RunPod/local runtime state observed

- RunPod direct-process tunnel endpoints were reachable locally during this audit.
- Orchestrator health/status passed on local tunnel `18080`.
- Vision health passed on verified demo port `18001`.
- Local Next client served `/` and `/replay` on `3000`.
- Docker and Docker Compose were not run.


## Risk resolution pass — 2026-05-25T01:24:00+09:00

| Prior risk | Resolution | Evidence |
|---|---|---|
| God Mode connected command path blocked by CORS/schema concerns | FastAPI now allows local demo origins including `127.0.0.1:3000` and `127.0.0.1:3100`; client command payload is typed as shared `GodCommand`; remote RunPod was redeployed and restarted | `OPTIONS /api/v1/god/command` from `http://127.0.0.1:3100` returned 200 with `access-control-allow-origin`; browser macro command returned `person: Person command applied...` with empty console/errors |
| Replay fallback not discoverable | Live page now has `Replay fallback 열기`; replay page has `Live city로 돌아가기` | Agent-browser snapshot lists both links on `/`; replay screenshot lists return link |
| WebSocket upgrade warning | Client default transport is `polling`; runbook documents `NEXT_PUBLIC_SOCKET_TRANSPORTS=polling`; UI shows `transport: polling` | Clean browser console after God Mode submit was empty |
| Mobile viewport crowded / status overlay | Mobile CSS makes connection card static between hero and scene and reduces hero scale | `/tmp/aetherville-risk-browser-fixed/mobile-fixed.png` shows no overlay on the city scene |
| Deploy sync could include local QA artifacts | `deploy_over_ssh.sh` now excludes `.gstack/` and `dogfood-output/` from rsync/tar sync | `bash -n infra/runpod/*.sh` passed |

Resolution verification commands:

```bash
uv run pytest server/tests/test_api_contracts.py
pnpm test
pnpm typecheck
bash -n infra/runpod/*.sh
AETHERVILLE_BOOTSTRAP_UV=1 AETHERVILLE_VLLM_MODE=mock AETHERVILLE_REDIS_MODE=memory AETHERVILLE_VISION_PORT=18001 bash infra/runpod/deploy_over_ssh.sh --mode direct
curl -i -X OPTIONS http://127.0.0.1:18080/api/v1/god/command -H 'Origin: http://127.0.0.1:3100' -H 'Access-Control-Request-Method: POST' -H 'Access-Control-Request-Headers: content-type'
curl -i -X POST http://127.0.0.1:18080/api/v1/god/command -H 'Origin: http://127.0.0.1:3100' -H 'Content-Type: application/json' --data '{"kind":"god_command","input_modality":"text","raw_text":"민준에게 오늘 카페 손님을 기억시켜줘","audio_blob_b64":null,"user_id":"presenter"}'
NEXT_TELEMETRY_DISABLED=1 NEXT_PUBLIC_ORCHESTRATOR_URL=http://127.0.0.1:18080 NEXT_PUBLIC_SOCKET_URL=http://127.0.0.1:18080 NEXT_PUBLIC_SOCKET_TRANSPORTS=polling pnpm exec next dev -H 127.0.0.1 -p 3100
agent-browser --session aetherville-risk-fixed-final open http://127.0.0.1:3100/
NEXT_TELEMETRY_DISABLED=1 pnpm --filter @aetherville/client build
```

Current residual project-demo risks: none known for the approved deterministic/direct-process demo path. Real vLLM/YOLO/PPO/LSTM/STT remain explicitly documented opt-in upgrades, not unresolved demo risks.

## gstack tooling repair pass — 2026-05-25T02:22:00+09:00

The earlier host-tool note is now closed. The installed gstack repo at `~/.gstack/repos/gstack` was registered for Codex with namespaced `gstack-*` skills, and user-level command shims were added under `~/.local/bin` so `bun` uses the non-snap user install and `browse` resolves to gstack instead of the system `xdg-open` alias.

Verification:

| Command | Result |
|---|---|
| `bash ~/.gstack/repos/gstack/setup --host codex --prefix --quiet --no-team` with user-level Bun first on `PATH` | PASS; linked `gstack-*` Codex skills |
| `command -v bun && bun --version` | PASS; user-level Bun `1.2.18` |
| `command -v browse && browse --help` | PASS; gstack browse help displayed |
| `browse status` | PASS; daemon launched healthy on `about:blank` |

This repair is local tooling only. It does not change the approved Project Aetherville demo runtime, does not use Docker, and does not touch secrets.
