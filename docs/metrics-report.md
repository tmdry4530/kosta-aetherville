# Metrics Report — Demo Readiness Snapshot

## Measurement

- Date: 2026-05-24
- Scope: Phase 10 local demo-readiness snapshot after Phases 01–09.
- RunPod mode: direct-process fallback.
- GPU workload: none; mock vLLM, mock vision, deterministic traffic/citizen/vehicle paths.

## Verification commands

| Command | Result |
|---|---|
| `uv run pytest packages server` | pass — 52 tests |
| `uv run ruff check server packages` | pass |
| `uv run mypy server packages` | pass |
| `pnpm lint` | pass |
| `pnpm typecheck` | pass |
| `pnpm test` | pass — 2 Node tests |
| `pnpm test:e2e` | pass — replay fallback static e2e |
| `pnpm --filter @aetherville/client build` | pass — `/` and `/replay` static routes |

## Demo metrics

| Metric | Current evidence | Target / note |
|---|---|---|
| Tick/state payload | Simulation tests and RunPod smokes pass | MVP deterministic state |
| Client city scene | Next build includes `/` | playable city shell |
| Replay fallback | `/replay` route and e2e test | switch when RunPod fails |
| God Mode effect | REST/RunPod smoke updated state | ≤ 3 sec target not benchmarked |
| Vision boxes | Mock detections in vehicle state + UI overlay | real YOLO deferred |
| Traffic forecast | 5/10/15 minute payload rendered | real LSTM deferred |

## Caveats

- Public RunPod URL exposure is not configured in tracked files.
- Vision default architecture port `8001` is still occupied by pod nginx; direct-process vision uses `18001`.
- Real vLLM, YOLO, PPO, LSTM, and STT model workloads are intentionally deferred behind explicit cost/model approval.
