# Goal 17 — Autonomous City Dogfood and Final Audit

## Objective

Prove that the evolved Aetherville runtime behaves like an autonomous multi-agent AI city under realistic and adversarial presentation scenarios.

This is an audit and hardening goal. Do not add new major features here unless a small test, runbook, or documentation fix is needed to close an evidence gap.

## Scope

Allowed:

- Read-only audit across repo, docs, tests, runtime state, and browser UI.
- Small docs/test/smoke/runbook fixes.
- Small bug fixes only if a required demo gate is demonstrably broken.

Out of scope:

- Opening a new architecture phase.
- Adding new AI capabilities not covered by Goals 12-16.
- Docker/Compose/DinD.
- Secret exposure.

## Required dogfood scenarios

Run at least ten scenarios through the live UI or API, including:

1. citizen A meets citizen B, then travels to citizen C by taxi
2. taxi unavailable or delayed, then alternate action selected
3. drone moves to a citizen, then another citizen rendezvous happens
4. rain starts mid-scenario and affects motion or reason text
5. traffic surge slows vehicles and triggers visible traffic state
6. unknown actor name is handled safely
7. impossible route or blocked destination triggers replan
8. two citizens are asked to meet the same person from different locations
9. long chained audience prompt with at least six dependent steps
10. replay fallback shows equivalent observability panels when live backend is unavailable

## Requirement-to-evidence matrix

Create or update `docs/autonomous-city-evolution-audit.md` with a matrix covering:

- TaskGraph planning
- Entity brain state
- Replanner/resilience
- Persistent learning/evolution
- Causal AI UI
- RunPod vLLM/vision/STT/traffic proof
- Local client runtime
- Replay fallback
- Security/secret handling
- Presentation truthfulness

Each row must include:

- requirement
- evidence file
- command or smoke result
- pass/fail/skipped
- residual risk

## Acceptance criteria

- All Goals 12-16 are either complete with evidence or explicitly marked incomplete with blocker/risk.
- Ten dogfood scenarios pass or have documented, non-demo-blocking limitations.
- No stale endpoint, Docker dependency, or secret leakage exists in tracked files.
- Browser live route and replay route both pass smoke.
- RunPod direct-process health is verified if the remote demo is in scope.
- Final report states exactly what can and cannot be claimed about autonomy and learning.

## Verification commands

```bash
git status --short
git log --oneline -5
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
python3 scripts/scenario_directive_smoke.py --orchestrator-url http://127.0.0.1:18080 --wait-seconds 45
python3 scripts/replanner_resilience_smoke.py --orchestrator-url http://127.0.0.1:18080 --wait-seconds 60
python3 scripts/learning_evolution_smoke.py --orchestrator-url http://127.0.0.1:18080 --repeat 2
python3 scripts/browser_demo_smoke.py --mode live --url http://127.0.0.1:3000/ --expected-endpoint http://127.0.0.1:18080
python3 scripts/browser_demo_smoke.py --mode replay --url http://127.0.0.1:3000/replay
python3 scripts/browser_visual_smoke.py --mode both --client-url http://127.0.0.1:3000 --expected-endpoint http://127.0.0.1:18080
```

If a command does not exist yet, mark it as a blocker for the relevant earlier goal; do not silently skip it.

## Final claim contract

Only claim:

- vLLM selects bounded plans if `city_ai.mode=vllm` and smoke evidence passed.
- Python simulation executes the validated actions.
- The city accumulates persistent experience if learning/evolution persistence is verified.
- Model weights self-train only if a separate training job and checkpoint promotion path is verified.

## Completion report

Report PASS/FAIL verdict, requirement-to-evidence matrix path, commands run, passed checks, failed/skipped checks, demo blockers, non-blocking risks, exact next actions, and RunPod state if touched.
