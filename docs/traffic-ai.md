# Traffic AI Slice

## Current demo mode

- `FixedCycleController` drives deterministic north/south and east/west signal phases.
- `TrafficSignalEnv` exposes a small reset/step API for future PPO training/inference integration.
- `TrafficPolicyWrapper` loads a JSON checkpoint when present and falls back to baseline pressure control otherwise.
- `LstmForecastWrapper` emits deterministic `TrafficForecastPoint` payloads with 5, 10, and 15 minute horizons.
- `TrafficAiSnapshot` is included in every world state so the browser can show whether traffic lights are fixed-cycle or checkpoint-driven.

## Runtime contract

- The simulation snapshot includes four visible traffic lights: `tl_nw`, `tl_ne`, `tl_sw`, and `tl_se`.
- `WorldStatePayload.traffic_forecast` is the client-visible forecast series.
- `WorldStatePayload.traffic_ai` exposes policy mode, checkpoint status, GPU training backend, queue-improvement metrics, and last selected signal action.
- The browser traffic panel renders the forecast payload directly; no hand-written duplicate contract is used.

## Real 4090 checkpoint path

The approved direct-process RunPod path now includes a real CUDA-trained traffic
policy checkpoint:

- Trainer: `python -m aetherville_server.traffic_ai.train_gpu_policy`
- Output: `/workspace/aetherville-model-cache/traffic/traffic_policy_v1.json`
- Runtime env: `AETHERVILLE_TRAFFIC_POLICY_CHECKPOINT=<checkpoint-json>`
- Verified backend: `torch_cuda` on NVIDIA GeForce RTX 4090.
- Verified training run: 320 episodes, horizon 80.
- Verified metric: average queue `32.913` vs fixed-cycle `48.138`, a `31.628%`
  queue reduction in the deterministic traffic environment.

Runtime inference is intentionally JSON/linear so the orchestrator can load the
checkpoint without importing torch or increasing tick-loop latency. Full PPO can
replace the trainer later while preserving the same checkpoint boundary.

## Real 4090 LSTM forecast path

The approved direct-process RunPod path also includes a real CUDA-trained LSTM
forecast checkpoint:

- Trainer: `python -m aetherville_server.traffic_ai.train_lstm_forecast`
- Output: `/workspace/aetherville-model-cache/traffic/traffic_lstm_v1.json`
- Runtime env: `AETHERVILLE_TRAFFIC_FORECAST_CHECKPOINT=<checkpoint-json>`
- Verified backend: `torch_cuda` on NVIDIA GeForce RTX 4090.
- Verified training run: 960 samples, 180 epochs, sequence length 12, hidden size 10.
- Verified metric: `MAPE 11.84%`, satisfying the demo target of ≤15% on the
  deterministic forecast training distribution.

Runtime inference is pure Python LSTM math using exported weights. The
orchestrator does not import torch for forecast inference, but the browser sees
`WorldStatePayload.traffic_forecast_ai.mode="lstm_checkpoint"` and can badge
the panel as `LSTM FORECAST`.

## Upgrade path

1. Keep the environment `reset()` / `step(action)` API stable.
2. Replace the lightweight CUDA policy-distillation trainer with full PPO when a longer training window is approved.
3. Export checkpoint metadata that `TrafficPolicyWrapper` can load.
4. Broaden the LSTM training distribution with live traffic telemetry once available.
5. Preserve deterministic fallback when checkpoint/model files are missing.

## Cost/safety gates

- Checkpoints are optional; missing checkpoints must not block the playable demo.
- The current 4090 training job is short and exports only a small JSON checkpoint.
- Longer PPO/LSTM training jobs must record GPU state, expected duration, model output path, and rollback/fallback behavior.
