# Goal 14 — Replanner and Resilience Runtime

## Objective

Detect stalled or impossible city tasks and recover automatically with bounded replanning.

The city should not freeze after zooming to a taxi or actor. If a plan is blocked, the runtime must explain the blocker, choose a safe fallback, and keep the demo moving.

## Scope

Allowed implementation areas:

- `packages/shared-schemas/**`
- `server/src/aetherville_server/sim/**`
- `server/src/aetherville_server/city_ai/**`
- `server/src/aetherville_server/scenario.py`
- `server/src/aetherville_server/orchestrator/**`
- `scripts/*replan*`, `scripts/*scenario*`, `scripts/*demo*`
- client UI panels needed to expose replan/blocker state
- tests and docs/status files required by project protocol

Out of scope:

- Raw LLM execution or direct model-authored coordinates.
- Infinite retry loops.
- Replanning by calling vLLM every tick.

## Required behaviors

Implement a bounded monitor that can detect:

- actor stuck for N ticks
- vehicle/taxi stuck for N ticks
- target unreachable
- taxi unavailable
- passenger pickup timeout
- group rendezvous timeout
- drone movement timeout or simulated low battery
- traffic delay exceeding task deadline
- graph dependency deadlock

For every blocker, emit:

- `blocked` task/entity status
- reason
- replan attempt number
- selected fallback action
- timeline event
- UI-visible explanation

## Replanning policy

The first implementation may be deterministic. It must support at least:

- retry same route once
- choose alternate meeting point
- dispatch another taxi or wait if no taxi exists
- convert taxi trip to walking fallback if short distance
- ask drone to hover/wait/reroute
- split group rendezvous into sequential pair meetings
- degrade gracefully to replay-safe deterministic state

Optional vLLM replanning may propose a bounded fallback action, but Python code must validate and apply it.

## Acceptance criteria

- Synthetic tests can force each major blocker and observe recovery.
- A complex six-step scenario completes or reaches an explicit fallback-complete state without hanging indefinitely.
- Timeline includes `task_blocked`, `task_replanned`, and `task_recovered` events.
- Browser shows blocked/replanned status in the Scenario Director or AI operations panel.
- Replanner has max attempt limits and cannot loop forever.
- Existing smoke tests still pass.

## Verification commands

```bash
uv run pytest server/sim server/orchestrator packages/shared-schemas/tests
uv run ruff check server packages scripts
uv run mypy server packages
pnpm lint
pnpm typecheck
pnpm test
python3 -m json.tool TASKS.json
git diff --check
```

New smoke command expected from this goal:

```bash
python3 scripts/replanner_resilience_smoke.py --orchestrator-url http://127.0.0.1:18080 --wait-seconds 60
```

## Completion report

Report blocker types covered, recovery evidence, max retry policy, verification results, RunPod state if touched, remaining non-recoverable cases, and next goal.
