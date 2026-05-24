# Traffic AI Slice

## Current demo mode

- `FixedCycleController` drives deterministic north/south and east/west signal phases.
- `TrafficSignalEnv` exposes a small reset/step API for future PPO training/inference integration.
- `TrafficPolicyWrapper` loads a tiny JSON checkpoint when present and falls back to baseline pressure control otherwise.
- `LstmForecastWrapper` emits deterministic `TrafficForecastPoint` payloads with 5, 10, and 15 minute horizons.

## Runtime contract

- The simulation snapshot includes two traffic lights: `tl_ns` and `tl_ew`.
- `WorldStatePayload.traffic_forecast` is the client-visible forecast series.
- The browser traffic panel renders the forecast payload directly; no hand-written duplicate contract is used.

## Upgrade path

1. Keep the environment `reset()` / `step(action)` API stable.
2. Train PPO offline or in a controlled RunPod job only after explicit cost approval.
3. Export checkpoint metadata that `TrafficPolicyWrapper` can load.
4. Replace deterministic forecast internals with an LSTM model behind `LstmForecastWrapper`.
5. Preserve deterministic fallback when checkpoint/model files are missing.

## Cost/safety gates

- Phase 08 does not start PPO training or GPU inference.
- Checkpoints are optional; missing checkpoints must not block the playable demo.
- Any future training job must record GPU state, expected duration, model output path, and rollback/fallback behavior.
