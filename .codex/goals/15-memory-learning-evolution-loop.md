# Goal 15 — Persistent Learning and Evolution Loop

## Objective

Turn city experience into persistent, measurable behavior changes without falsely claiming model-weight self-training.

The runtime should remember what happened, score success/failure, adjust future planning biases, and preserve learning state across orchestrator restarts.

## Scope

Allowed implementation areas:

- `packages/shared-schemas/**`
- `server/src/aetherville_server/learning*` or existing learning modules
- `server/src/aetherville_server/agents/**`
- `server/src/aetherville_server/sim/**`
- `server/src/aetherville_server/city_ai/**`
- `server/src/aetherville_server/traffic_ai/**` only for policy/bias metadata integration
- `client/src/ui/LearningPanel.tsx` and related panels
- scripts/tests/docs/status files

Out of scope:

- Silent fine-tuning of vLLM/YOLO/PPO/LSTM weights.
- Long-running paid training jobs without explicit approval.
- Unbounded logs that grow forever without compaction.

## Required shared contracts

Add or extend schemas for:

- `TrajectoryEvent`
- `TaskOutcomeScore`
- `LearningSignal`
- `PolicyBiasSnapshot`
- `EvolutionSnapshot`

## Required learning signals

Track at least:

- scenario success/failure
- task duration
- replan count
- taxi pickup success rate
- weather delay impact
- traffic delay impact
- citizen meeting success count
- repeated actor interaction memory
- fallback path usage

## Behavior adaptation requirements

The learning state must influence future runtime decisions in small, inspectable ways, for example:

- rainy weather increases taxi delay expectation and route caution
- repeated taxi failure increases walking/alternate taxi bias
- repeated traffic surge increases signal pressure or vehicle slowdown bias
- citizens remember recent meetings and can reference them in current action/reason
- scenarios that previously failed start with safer default timeouts or alternate meeting points

## Persistence requirements

- Store learning/evolution state in a deterministic JSON file or equivalent safe local persistence path.
- Do not commit generated runtime state.
- Load state on orchestrator start.
- Expose storage path/mode in health or world state without printing secrets.
- Provide a reset command or documented demo reset path.

## Acceptance criteria

- Learning state changes after a scenario run.
- State survives orchestrator restart.
- A repeated scenario shows at least one documented changed bias/reason from prior experience.
- Browser Learning panel shows evolution version, recent signals, success/failure counts, and active biases.
- Claims remain truthful: no model-weight self-training unless separate training artifacts are present and verified.
- Replay fallback includes deterministic learning/evolution sample data.

## Verification commands

```bash
uv run pytest server/sim server/agents server/tests packages/shared-schemas/tests
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
python3 scripts/learning_evolution_smoke.py --orchestrator-url http://127.0.0.1:18080 --repeat 2
```

## Completion report

Report persisted state path policy, learning signals implemented, before/after behavior evidence, verification results, RunPod state if touched, truthfulness caveats, and next goal.
