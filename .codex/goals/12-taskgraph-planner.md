# Goal 12 — TaskGraph Planner

## Objective

Convert free-form Korean city situations into an explicit, safe, executable task graph.

The goal is to replace brittle scenario-pattern handling with a general planning contract that can represent chained citizen, taxi, drone, weather, traffic, and meeting situations while still executing only bounded Python actions.

## Scope

Allowed implementation areas:

- `packages/shared-schemas/**`
- `server/src/aetherville_server/scenario.py`
- `server/src/aetherville_server/city_ai/**`
- `server/src/aetherville_server/orchestrator/**`
- `server/src/aetherville_server/sim/**`
- `scripts/*taskgraph*`, `scripts/*scenario*`
- `client/src/ui/ScenarioDirectorPanel.tsx` only for contract display compatibility
- tests under `server/**`, `packages/**`, `client/tests/**`
- docs/status files required by project protocol

Out of scope:

- Raw coordinate mutation by LLM output.
- Per-tick LLM planning.
- Model fine-tuning or training.
- New production dependencies unless explicitly justified.

## Required shared contracts

Add or extend shared schemas for:

- `TaskGraph`
- `TaskNode`
- `TaskEdge`
- `TaskCondition`
- `TaskGraphPlan`
- `TaskGraphExecutionSnapshot`

Each task node must include at least:

- stable id
- actor id or actor selector
- action type from a bounded vocabulary
- target actor/entity/location selector
- dependencies
- success condition
- failure condition
- timeout/retry policy
- human-readable reason
- current status

## Bounded action vocabulary

At minimum support:

- `move_actor_to_actor`
- `move_actor_to_location`
- `meet`
- `call_taxi`
- `taxi_pickup`
- `taxi_drive_to_actor`
- `drone_move_to_actor`
- `drone_deliver`
- `group_rendezvous`
- `set_weather`
- `traffic_surge`
- `remember`
- `wait`
- `no_op`

## Acceptance criteria

- Ten Korean fixture commands compile to valid `TaskGraphPlan` objects.
- Unknown actors produce an explicit rejected or clarification-needed graph, not a crash.
- Ambiguous commands choose safe defaults and record assumptions in the graph.
- Existing Scenario Director commands continue to work through the new graph path.
- LLM/vLLM planning can be enabled, but deterministic fallback must pass all fixtures.
- Generated TypeScript is updated from Python schema source.
- REST/God Mode response exposes the compiled graph or rejection reason.
- World state exposes active graph execution snapshot.

## Required test fixtures

Include at least these scenario families:

1. simple citizen meeting
2. citizen meeting then taxi trip
3. taxi trip then group rendezvous
4. drone delivery plus citizen movement
5. rain causing taxi delay
6. traffic surge causing vehicle slowdown
7. unknown citizen name
8. duplicate target names or ambiguous target
9. impossible ordering or circular dependency
10. long chained audience command with at least six steps

## Verification commands

```bash
uv run pytest packages/shared-schemas/tests server/orchestrator server/sim
uv run ruff check server packages scripts
uv run mypy server packages
pnpm typecheck
pnpm test
python3 -m json.tool TASKS.json
git diff --check
```

If RunPod is touched:

```bash
python3 scripts/scenario_directive_smoke.py --orchestrator-url http://127.0.0.1:18080 --wait-seconds 45
```

## Completion report

Report changed files, graph fixtures covered, verification results, RunPod state if touched, remaining parser/planner limitations, and next goal.
