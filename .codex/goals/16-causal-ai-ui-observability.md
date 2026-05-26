# Goal 16 — Causal AI UI and Observability

## Objective

Make the autonomous city understandable on screen.

The browser should clearly show what the AI understood, what each entity is trying to do, why a replan happened, what was learned, and which RunPod AI services are real or fallback.

## Scope

Allowed implementation areas:

- `client/src/app/**`
- `client/src/components/**`
- `client/src/ui/**`
- `client/src/lib/**`
- `packages/shared-schemas/**` only if UI needs contract additions
- `scripts/browser_*smoke.py`, `scripts/demo_rehearsal.py`
- docs/status files required by project protocol

Out of scope:

- Backend planning logic except minor contract additions needed for UI.
- Visual effects that hide truthfulness or fake AI states.
- Removing replay fallback.

## Required UI surfaces

Add or strengthen panels for:

- active task graph timeline
- per-entity brain/intent inspector
- current replan/blocker feed
- causal event chain: command → graph → entity actions → outcome → learning
- RunPod AI proof state: vLLM, YOLO, STT, traffic, forecast, direct-process runtime
- learning/evolution state with truthful wording
- presenter-safe status banner showing live/tunnel/replay mode

## Visual requirements

- Actor, taxi, drone, and group targets must be visually distinguishable.
- Active graph step must focus/highlight the relevant entity without freezing motion.
- Blocked/replanned steps must show distinct color/status.
- Rain, traffic surge, taxi dispatch, drone motion, and meeting states must be visible without reading logs.
- Layout must remain usable at 1920x1080 for a 15-minute presentation.

## Acceptance criteria

- Browser smoke fails if TaskGraph, entity intent, replan feed, learning/evolution, or RunPod proof markers disappear.
- Visual smoke captures nonblank 1920x1080 live and replay screenshots.
- Impact smoke shows visible before/after delta for a multi-action command.
- Scenario smoke plus browser smoke demonstrates at least one complex story timeline in the UI.
- Replay route shows the same panels with deterministic fallback labels.
- UI copy avoids overclaiming model-weight self-training.

## Verification commands

```bash
pnpm lint
pnpm typecheck
pnpm test
pnpm test:e2e
pnpm --filter @aetherville/client build
python3 scripts/browser_demo_smoke.py --mode live --url http://127.0.0.1:3000/ --expected-endpoint http://127.0.0.1:18080
python3 scripts/browser_demo_smoke.py --mode replay --url http://127.0.0.1:3000/replay
python3 scripts/browser_visual_smoke.py --mode both --client-url http://127.0.0.1:3000 --expected-endpoint http://127.0.0.1:18080
python3 scripts/browser_impact_smoke.py --orchestrator-url http://127.0.0.1:18080 --client-url http://127.0.0.1:3000
python3 -m json.tool TASKS.json
git diff --check
```

## Completion report

Report changed UI surfaces, screenshot/smoke evidence, copy/truthfulness checks, verification results, RunPod state if touched, remaining UX risks, and next goal.
