# Metrics Report — Demo Readiness Snapshot

## Measurement

- Date: 2026-05-24
- Scope: Phase 10 local demo-readiness snapshot after Phases 01–09.
- RunPod mode: direct-process runtime.
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

## Real 4090 vLLM smoke — 2026-05-25

- Model: `Qwen/Qwen2.5-14B-Instruct-AWQ` served by real vLLM on the RunPod RTX 4090.
- Runtime pins: `vllm==0.10.2`, `transformers==4.55.4`, Torch CUDA 12.8-compatible stack.
- Smoke evidence:
  - `/v1/models` returned the Qwen 14B AWQ model.
  - `/v1/chat/completions` generated a Korean citizen line.
  - Orchestrator `/api/v1/health` reported `vllm:ok`.
  - `POST /api/v1/citizens/c01/reflect` returned a real model-generated Korean reflection.
- GPU memory after smoke: approximately 22.5 GiB VRAM used.
- Remaining real ML gaps: YOLO, PPO/LSTM, and STT are still next GPU integration targets.

## Real 4090 YOLO smoke — 2026-05-25

- Vision mode: real Ultralytics YOLO.
- Model: `yolo11n.pt`.
- Package: `ultralytics 8.4.53`.
- Smoke evidence:
  - `/health` returned `yolo:ok`.
  - `/detect` returned `mode=real` on a deterministic synthetic road frame.
  - Real vLLM and real YOLO were active at the same time.
- GPU memory after combined real vLLM + YOLO smoke: approximately 23.1 GiB VRAM used.
- Remaining gap: browser vehicle camera still displays state-embedded detections; next step is feeding real `/detect` results into vehicle camera/state or a live frame stream.
