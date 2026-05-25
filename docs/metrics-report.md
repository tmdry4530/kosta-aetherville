# Metrics Report — Demo Readiness Snapshot

## Measurement

- Date: 2026-05-25
- Scope: Phase 10 plus approved real 4090 vLLM/YOLO demo-readiness snapshot.
- RunPod mode: direct-process runtime.
- GPU workload: real vLLM plus optional real Ultralytics YOLO camera inference on the verified RTX 4090 path.

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
| Vision boxes | Vehicle camera endpoint can enrich from real RunPod YOLO; browser panel polls it and badges `REAL YOLO · RunPod 4090` | fallback keeps mock detections when YOLO is unavailable |
| Traffic forecast | RunPod CUDA-trained LSTM checkpoint loaded in world state | 11.84% MAPE on deterministic training distribution |
| Traffic policy | RunPod CUDA-trained checkpoint loaded in world state | 31.628% avg queue reduction vs fixed cycle |

## Caveats

- Public RunPod URL exposure is not configured in tracked files.
- Vision default architecture port `8001` is still occupied by pod nginx; direct-process vision uses `18001`.
- Full PPO and live-telemetry LSTM hardening remain deferred; STT has an implemented optional faster-whisper path with typed fallback safety.

## Real 4090 vLLM smoke — 2026-05-25

- Model: `Qwen/Qwen2.5-14B-Instruct-AWQ` served by real vLLM on the RunPod RTX 4090.
- Runtime pins: `vllm==0.10.2`, `transformers==4.55.4`, Torch CUDA 12.8-compatible stack.
- Smoke evidence:
  - `/v1/models` returned the Qwen 14B AWQ model.
  - `/v1/chat/completions` generated a Korean citizen line.
  - Orchestrator `/api/v1/health` reported `vllm:ok`.
  - `POST /api/v1/citizens/c01/reflect` returned a real model-generated Korean reflection.
- GPU memory after smoke: approximately 22.5 GiB VRAM used.
- Remaining real ML gaps: full PPO and verified real-audio STT smoke are still next GPU integration targets.

## Real 4090 YOLO smoke — 2026-05-25

- Vision mode: real Ultralytics YOLO.
- Model: `yolo11n.pt`.
- Package: `ultralytics 8.4.53`.
- Smoke evidence:
  - `/health` returned `yolo:ok`.
  - `/detect` returned `mode=real` on a deterministic synthetic road frame.
  - Real vLLM and real YOLO were active at the same time.
- GPU memory after combined real vLLM + YOLO smoke: approximately 23.1 GiB VRAM used.
- Follow-up integration — 2026-05-25:
  - Orchestrator `/api/v1/vehicles/{id}/camera` now calls vision `/detect` when `AETHERVILLE_CAMERA_VISION_MODE=real`.
  - `VehicleCameraFrame.mode` distinguishes `mock` and `real`.
  - Browser `VehicleCamPanel` polls the camera endpoint and shows `REAL YOLO · RunPod 4090` when the real path is active.
  - If the camera endpoint or real YOLO fails, the panel falls back to state-embedded mock detections instead of breaking the demo.

## Real 4090 traffic policy checkpoint — 2026-05-25

- Trainer: `aetherville_server.traffic_ai.train_gpu_policy`.
- Backend: `torch_cuda` on NVIDIA GeForce RTX 4090.
- Episodes/horizon: 320 episodes, horizon 80.
- Checkpoint: JSON linear policy under the RunPod model cache.
- Runtime: orchestrator loaded `AETHERVILLE_TRAFFIC_POLICY_CHECKPOINT` and
  `WorldStatePayload.traffic_ai` reported `mode=checkpoint`,
  `trained_on_gpu=true`, and `training_backend=torch_cuda`.
- Metric: average queue `32.913` vs fixed-cycle `48.138`, `31.628%` reduction.
- UI: traffic panel displays a `GPU POLICY` badge and queue-cut percentage from
  the shared `traffic_ai` state.

## Real 4090 LSTM traffic forecast checkpoint — 2026-05-25

- Trainer: `aetherville_server.traffic_ai.train_lstm_forecast`.
- Backend: `torch_cuda` on NVIDIA GeForce RTX 4090.
- Samples/epochs: 960 samples, 180 epochs.
- Sequence: length 12, hidden size 10.
- Checkpoint: JSON LSTM weights under the RunPod model cache.
- Runtime: orchestrator loaded `AETHERVILLE_TRAFFIC_FORECAST_CHECKPOINT` and
  `WorldStatePayload.traffic_forecast_ai` reported `mode=lstm_checkpoint`,
  `trained_on_gpu=true`, and `training_backend=torch_cuda`.
- Metric: `MAPE 11.84%`, training loss `2.911555`.
- UI: traffic panel displays an `LSTM FORECAST` badge and MAPE from shared state.

## Real 4090 God Mode vLLM interpretation — 2026-05-25

- Runtime flag: `AETHERVILLE_GOD_MODE_LLM=vllm`.
- Model path: OpenAI-compatible RunPod vLLM endpoint already serving `Qwen/Qwen2.5-14B-Instruct-AWQ`.
- Safety: vLLM only classifies text into a fixed safe action vocabulary; deterministic dispatcher applies effects.
- Contract/UI evidence: `GodCommandResponse` includes `ai_mode`, `ai_confidence`, and `ai_reason`; browser God Mode result displays `vLLM NN%` or `rules fallback`.
- Verification: targeted schema/orchestrator/simulation/API tests passed locally; RunPod smoke should confirm `ai_mode=vllm` after direct-process redeploy.


## Real 4090 multi-action God Mode direction — 2026-05-25

- Runtime flag: `AETHERVILLE_GOD_MODE_LLM=vllm`.
- Capability: one natural-language command can produce a bounded action sequence such as `rain + traffic_jam + taxi_call + meeting`.
- Safety: every action still maps to deterministic dispatcher effects; arbitrary state mutation remains disallowed.
- Contract/UI evidence: `GodCommandResponse.ai_actions` and event metadata expose the decomposed plan.
- Verification: targeted orchestrator/simulation/schema tests passed locally; RunPod smoke should confirm multi-action `ai_mode=vllm` after redeploy.


## God Mode voice/STT path — 2026-05-25

- API: `/api/v1/god/voice` accepts `VoiceCommandRequest` and returns `VoiceCommandResponse`.
- Browser: `GodModeMicPanel` records microphone audio with `MediaRecorder`.
- Runtime: default fallback/stub mode, optional `AETHERVILLE_STT_MODE=faster_whisper` for real STT.
- Truthfulness: `stt_status` distinguishes real transcription from typed fallback.
- Verification: local schema/API/voice tests passed; RunPod fallback smoke should be run after redeploy.
