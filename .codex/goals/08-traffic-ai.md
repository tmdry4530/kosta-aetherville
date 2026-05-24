# Goal 08 — Traffic AI

## Objective

Implement traffic signal baseline, PPO env/wrapper, LSTM forecast wrapper, and traffic chart payloads.

## Scope

- Allowed: `server/traffic_ai/**`, `server/sim/**`, `client/src/ui/TrafficChartPanel*`, schemas/tests.

## Acceptance criteria

- Fixed cycle baseline works.
- `TrafficSignalEnv` reset/step tested.
- PPO wrapper loads checkpoint if present and falls back to baseline.
- Forecast payload visible in client.

## Verification commands

```bash
uv run pytest server/traffic_ai server/sim packages
pnpm test
```

## Completion report

Report:

- changed files
- commands run and results
- blockers
- RunPod status if touched
- next goal
