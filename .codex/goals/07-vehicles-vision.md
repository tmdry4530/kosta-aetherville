# Goal 07 — Vehicles and Vision

## Objective

Implement vehicle movement, pathfinding, trip manager skeleton, vision service detect contract, and vehicle camera panel.

## Scope

- Allowed: `server/vehicles/**`, `server/vision/**`, `server/sim/**`, `client/src/ui/VehicleCamPanel*`, schemas/tests.

## Acceptance criteria

- Vehicles follow paths.
- A* pathfinding tested.
- Vision `/detect` returns schema-valid mock or real detections.
- Vehicle state includes detections.
- Browser overlays boxes in panel.

## Verification commands

```bash
uv run pytest server/vehicles server/vision packages
pnpm test
```

## Completion report

Report:

- changed files
- commands run and results
- blockers
- RunPod status if touched
- next goal
