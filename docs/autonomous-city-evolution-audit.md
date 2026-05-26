# Autonomous City Evolution Final Audit

Date: 2026-05-26
Branch: `feat/llm-driven-city-loop`
Runtime policy: direct-process only; Docker/Compose/DinD not used.

## Verdict

**PASS for the approved playable autonomous-city demo scope, with truthfulness caveats.**

The current implementation supports bounded TaskGraph planning, inspectable entity brains, deterministic bounded replanning, persistent JSON-backed learning/evolution state, and UI observability panels. It does **not** prove unbounded AGI, per-frame LLM control, or live model-weight self-training.

## Requirement-to-evidence matrix

| Requirement | Evidence file | Command / smoke result | Status | Residual risk |
| --- | --- | --- | --- | --- |
| TaskGraph planning | `server/src/aetherville_server/scenario.py`, `server/sim/test_taskgraph_planner.py`, shared schemas | `uv run pytest packages/shared-schemas/tests server/sim -q` → 61 passed | PASS | Deterministic Korean parser covers demo vocab, not arbitrary language. |
| Entity brain state | `WorldStatePayload.entity_brains`, `client/src/ui/AiOperationsPanel.tsx` | Tests assert citizen/taxi/drone brain states; browser smoke markers include `Entity intent` | PASS | Older saved states may omit brains; UI keeps fallback-safe rendering. |
| Replanner/resilience | `SimulationEngine.force_replanner_blocker`, `ReplanRecord`, `scripts/replanner_resilience_smoke.py` | Local current-branch smoke on `http://127.0.0.1:18081` passed with `task_blocked`, `task_replanned`, `task_recovered` | PASS | First policy is deterministic and bounded; no vLLM replan proposals yet. |
| Persistent learning/evolution | `server/src/aetherville_server/learning.py`, `/api/v1/learning/reset`, `scripts/learning_evolution_smoke.py` | Local smoke passed: experience 0→8, policy `adaptive-demo-v2`, JSON persistence path under `/tmp` | PASS | This is policy-bias adaptation, not neural checkpoint training. |
| Causal AI UI | `client/src/ui/AiOperationsPanel.tsx`, `LearningPanel`, `ScenarioDirectorPanel`, `RunPodProofPanel` | `pnpm test`, `pnpm typecheck`, browser smoke marker contract | PASS | Visual polish still depends on live browser warmup and viewport. |
| RunPod vLLM/vision/STT/traffic proof | `RunPodProofPanel`, `docs/demo-readiness-checklist.md`, prior M11 evidence | Current tunnel health `http://127.0.0.1:18080/api/v1/health` returned ok; vision uses `18001` | PASS for reachable runtime proof | Goal 13-17 current-branch code was verified locally on 18081; remote redeploy should be run before live demo. |
| Local client runtime | `client/src/app/page.tsx`, `SidePanels`, smoke scripts | `pnpm lint`, `pnpm typecheck`, `pnpm test`; browser smoke required after final client restart | PASS | Next dev cold compile on WSL can be slow. |
| Replay fallback | `client/src/app/replay`, `client/src/lib/mockWorld.ts` | Mock world includes TaskGraph, entity brains, replans, learning/evolution sample | PASS | Replay is deterministic and must be presented as fallback. |
| Security / secret handling | `.gitignore`, runbooks, backup excludes | No `.env.runpod`, SSH key paths, tokens, or secrets printed/committed in this audit | PASS | Do not paste local env files into chat/logs. |
| Presentation truthfulness | `docs/demo-script-15min.md`, this audit, `DECISIONS.md` | Copy states bounded plans + Python executor + JSON adaptation only | PASS | Presenter must avoid “완전 자가학습 모델” wording. |

## Ten dogfood scenarios

`python3 scripts/autonomous_city_dogfood_smoke.py --orchestrator-url http://127.0.0.1:18081 --wait-seconds 8` passed all 10 scenarios:

1. citizen A meets citizen B, then travels to citizen C by taxi — PASS.
2. taxi unavailable/delayed, then fallback selected — PASS with `task_replanned`.
3. drone moves to a citizen, then rendezvous happens — PASS.
4. rain starts mid-scenario and affects state/reason path — PASS.
5. traffic surge slows vehicles / traffic state visible — PASS.
6. unknown actor name handled safely — PASS with `task_graph_rejected`.
7. impossible route / blocked destination triggers replan — PASS with `task_replanned`.
8. two citizens meet the same person — PASS.
9. long six-step audience prompt — PASS.
10. replay fallback observability data present — PASS; browser replay smoke remains the UI proof gate.

## Commands run during this goal slice

```bash
python3 packages/shared-schemas/scripts/generate_typescript.py
python3 -m py_compile server/src/aetherville_server/sim/engine.py server/src/aetherville_server/learning.py server/src/aetherville_server/scenario.py server/src/aetherville_server/main.py scripts/replanner_resilience_smoke.py scripts/learning_evolution_smoke.py scripts/autonomous_city_dogfood_smoke.py
uv run pytest packages/shared-schemas/tests server/sim -q
uv run ruff check server packages scripts
uv run mypy server packages
pnpm lint
pnpm typecheck
pnpm test -- --runInBand 2>/dev/null || pnpm test
pnpm test:e2e
pnpm --filter @aetherville/client build
python3 -m json.tool TASKS.json
git diff --check
curl -fsS http://127.0.0.1:18080/api/v1/health
python3 scripts/replanner_resilience_smoke.py --orchestrator-url http://127.0.0.1:18081 --wait-seconds 25
python3 scripts/learning_evolution_smoke.py --orchestrator-url http://127.0.0.1:18081 --repeat 2 --wait-seconds 25
python3 scripts/autonomous_city_dogfood_smoke.py --orchestrator-url http://127.0.0.1:18081 --wait-seconds 8
python3 scripts/browser_demo_smoke.py --mode live --url http://127.0.0.1:3000/ --expected-endpoint http://127.0.0.1:18080 --timeout-seconds 45
python3 scripts/browser_demo_smoke.py --mode replay --url http://127.0.0.1:3000/replay --timeout-seconds 45
python3 scripts/browser_visual_smoke.py --mode both --client-url http://127.0.0.1:3000 --expected-endpoint http://127.0.0.1:18080
```

## Passed checks

- Shared schema tests and server simulation tests passed.
- Ruff and mypy passed after fixes.
- Client lint/typecheck/test passed.
- Replanner and learning smoke scripts passed against the current local direct-process orchestrator on `18081`.
- Current RunPod tunnel health on `18080` was reachable and reports direct-process dependencies.
- Final production build passed: `pnpm --filter @aetherville/client build`.
- Local portability backup created: `.omx/backups/aetherville-goals13-17-autonomous-city-20260526-101816.tar.gz` (`sha256=a628885b3b6729114069a6d8c5040584147f5aa100d57abf9e02a79fc03cbe1c`).

## Failed / skipped checks

- Final browser live/replay smoke, visual smoke, `pnpm test:e2e`, and `pnpm --filter @aetherville/client build` passed in the final verification pass.
- Browser impact smoke was not rerun for this Goal 13-17 slice; prior M10 impact evidence remains valid, and Goal 13-17 behavior is covered by scenario/replanner/learning/dogfood smokes.
- Remote RunPod redeploy for Goal 13-17 code was not performed in this audit slice; current-branch runtime proof used local direct-process port `18081` because `18080` is occupied by an SSH tunnel.

## Demo blockers

No code-level blocker for the approved playable demo. Operational blocker remains: before a live RunPod demo, redeploy/restart the remote direct-process orchestrator with this branch if the new Entity Brain/Replanner/Evolution panels must reflect remote state rather than local current-branch state.

## Non-blocking risks

- Replanner policy is deterministic; it recovers bounded demo blockers but does not solve arbitrary real-world navigation.
- Learning/evolution changes are JSON-backed policy-bias adaptations; no model weights are self-trained.
- vLLM is a bounded planner/interpreter when enabled; Python simulation executes validated actions.
- Browser startup on WSL can be slow; warm `/` and `/replay` before presenting.

## Exact next actions before presentation

1. Push this branch.
2. If presenting from RunPod, run the existing direct-process sync/restart path and verify `18080` smoke with the new scripts.
3. Start local client with the selected endpoint and run live + replay browser smoke.
4. Present with the truthfulness line: “vLLM chooses bounded plans when enabled; Python executes them; learning is persistent policy-bias adaptation, not model-weight self-training.”
