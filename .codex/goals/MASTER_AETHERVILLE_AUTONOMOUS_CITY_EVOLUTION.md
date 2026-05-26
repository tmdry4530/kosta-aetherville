# MASTER_AETHERVILLE_AUTONOMOUS_CITY_EVOLUTION

## Objective

Upgrade Project Aetherville from a bounded RunPod-backed demo into a visibly autonomous multi-agent AI city runtime.

This master goal deliberately defines "완전히 진화한 AI 도시" as a measurable engineering target, not an unbounded AGI claim:

> A live city where free-form Korean situation requests become executable task graphs, citizens/vehicles/drones hold their own goals and reasons, failures trigger replanning, experience changes later decisions, and the browser explains the causal chain in real time.

## Current baseline

- Existing demo runtime is direct-process RunPod, not Docker-first.
- vLLM can interpret God Mode and City AI high-level bounded actions.
- Scenario Director can execute some complex Korean story commands as bounded steps.
- Browser already has city rendering, Scene Director, RunPod proof, learning, traffic, vehicle camera, God Mode, and replay fallback surfaces.
- Persistent adaptation exists, but it is not model-weight self-training.

## Non-negotiable constraints

- Do not run Docker, Docker Compose, Docker-in-Docker, or blind Docker retries on the verified RunPod path.
- Keep RunPod secrets only in ignored env files or process environment. Never print or commit them.
- LLMs may propose plans, task graphs, reasons, or bounded actions only. Raw LLM prose must never mutate simulation state directly.
- No per-tick LLM calls. Planning must be event-scoped, interval-scoped, or queue-backed.
- Shared schemas remain the source of truth for Python and TypeScript contracts.
- Replay fallback must continue to work when RunPod is unavailable.
- Do not claim autonomous model-weight self-training unless a separate training job, checkpoint promotion, smoke test, and rollback path are implemented and verified.

## Execution order

1. `.codex/goals/12-taskgraph-planner.md`
2. `.codex/goals/13-entity-brain-runtime.md`
3. `.codex/goals/14-replanner-resilience-runtime.md`
4. `.codex/goals/15-memory-learning-evolution-loop.md`
5. `.codex/goals/16-causal-ai-ui-observability.md`
6. `.codex/goals/17-autonomous-city-dogfood-audit.md`

## Definition of done for the full evolution goal

A final demo can be called an autonomous multi-agent AI city only when all of these are true:

- A presenter can enter at least ten varied Korean multi-actor scenarios, including chained citizen/taxi/drone/traffic/weather constraints.
- Each accepted scenario is compiled into a task graph with actors, actions, dependencies, success conditions, failure conditions, and bounded executor steps.
- Every active citizen, taxi, vehicle, and drone exposes current goal, next action, reason, progress, and blocked state through shared world state.
- The runtime detects at least these failure classes and recovers without manual reset: stuck actor, unavailable taxi, unreachable target, conflicting destination, traffic delay, and drone delay/low-battery simulation.
- The system records trajectory events, success/failure scores, replans, and learning signals; restarting the orchestrator preserves the learning state.
- The browser shows the active task graph, entity intent, replanning reason, learning evidence, and causal timeline, not just moving shapes.
- RunPod vLLM/vision/STT/traffic proof panels remain truthful: they show real, fallback, unavailable, or skipped states explicitly.
- Local replay mode still demonstrates the same UI surfaces with deterministic fallback data.
- Automated verification and dogfood evidence pass on local and, where required, RunPod direct-process runtime.

## Required verification minimums

Each phase must run the smallest relevant subset, and the final audit must attempt the full set:

```bash
python3 -m json.tool TASKS.json
bash -n infra/runpod/*.sh
git diff --check
uv run pytest
uv run ruff check server packages scripts
uv run mypy server packages
pnpm lint
pnpm typecheck
pnpm test
pnpm test:e2e
pnpm --filter @aetherville/client build
```

RunPod-facing phases must also verify via the selected public endpoint or SSH tunnel without exposing secrets:

```bash
curl -fsS http://127.0.0.1:18080/api/v1/health
curl -fsS http://127.0.0.1:18080/api/v1/sim/status
python3 scripts/browser_demo_smoke.py --mode live --url http://127.0.0.1:3000/ --expected-endpoint http://127.0.0.1:18080
```

## Per-phase completion report

Every implementation phase must report:

1. phase completed
2. changed files
3. verification commands/results
4. failed/skipped checks
5. RunPod state if touched
6. residual risks
7. next phase selected
