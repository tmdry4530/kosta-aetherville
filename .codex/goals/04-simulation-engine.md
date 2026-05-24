# Goal 04 — Simulation Engine Minimal Slice

## Objective

Implement deterministic world state tick loop with time, weather, event timeline, citizens/vehicles placeholders, and broadcast payload.

## Scope

- Allowed: `server/sim/**`, `server/orchestrator/**`, `packages/shared-schemas/**`, tests.

## Acceptance criteria

- Tick scheduler advances state.
- State contains world/citizens/vehicles/drones/traffic_lights/forecast.
- REST start/stop/reset/status works.
- WebSocket emits state at configurable rate.

## Verification commands

```bash
uv run pytest server/sim server/orchestrator packages
```

## Completion report

Report:

- changed files
- commands run and results
- blockers
- RunPod status if touched
- next goal
