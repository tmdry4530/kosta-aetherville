# Goal 13 — Entity Brain Runtime

## Objective

Give every meaningful city entity an inspectable brain state: current goal, next action, reason, constraints, progress, and blocked status.

This makes the city feel agentic because citizens, taxis, vehicles, and drones no longer appear as anonymous moving geometry; each entity can explain what it is trying to do and why.

## Scope

Allowed implementation areas:

- `packages/shared-schemas/**`
- `server/src/aetherville_server/agents/**`
- `server/src/aetherville_server/sim/**`
- `server/src/aetherville_server/traffic_ai/**` only for exposed intent/status integration
- `client/src/components/CityPlaceholder.tsx`
- `client/src/components/SidePanels.tsx`
- `client/src/ui/**Brain*`, `client/src/ui/**Intent*`, existing panels as needed
- tests and smoke scripts
- docs/status files required by project protocol

Out of scope:

- New neural model training.
- Unbounded autonomous actions outside the TaskGraph/City AI vocabularies.
- Replacing the existing world state contract with UI-local state.

## Required shared contracts

Add or extend shared schemas for:

- `EntityBrainState`
- `EntityGoal`
- `EntityConstraint`
- `EntityProgress`
- `EntityBlocker`

Every citizen, vehicle/taxi, and drone should expose:

- `entity_id`
- `entity_type`
- `current_goal`
- `next_action`
- `reason`
- `source`: `task_graph | city_ai | god_mode | routine | fallback`
- `progress_pct`
- `status`: `idle | planning | moving | waiting | interacting | blocked | complete | fallback`
- `blocked_reason` if blocked
- `updated_tick`

## Acceptance criteria

- Each citizen in `WorldStatePayload` has an inspectable brain state or a deterministic routine brain fallback.
- Taxis/vehicles expose pickup/dropoff/route/blocked intent.
- Drones expose destination, task reason, and delivery/move status.
- TaskGraph nodes assign or update entity brain state as they execute.
- Existing City AI plans update the selected actors' brain state.
- Browser shows entity intent/reason on selection or in a compact AI control panel.
- Replay fallback includes representative brain states.
- Existing panels keep working when brain data is missing from older states.

## Verification commands

```bash
uv run pytest packages/shared-schemas/tests server/sim server/agents
uv run ruff check server packages scripts
uv run mypy server packages
pnpm lint
pnpm typecheck
pnpm test
pnpm test:e2e
python3 -m json.tool TASKS.json
git diff --check
```

Browser/runtime smoke:

```bash
python3 scripts/browser_demo_smoke.py --mode live --url http://127.0.0.1:3000/ --expected-endpoint http://127.0.0.1:18080
```

## Completion report

Report changed files, entity types covered, UI surfaces added, verification results, RunPod state if touched, remaining non-agentic entities, and next goal.
