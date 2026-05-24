# Goal 10 — Polish and Demo

## Objective

Harden the system for a 15-minute demo: replay mode, metrics report, demo script, and resilience checks.

## Scope

- Allowed: `client/**`, `server/**`, `docs/**`, `scripts/**`, `README.md`, tests.

## Acceptance criteria

- Replay mode works.
- Metrics report template filled.
- Demo scenario documented.
- 15-minute dry run checklist exists.
- RunPod failure fallback tested or documented.

## Verification commands

```bash
uv run pytest
pnpm lint
pnpm typecheck
pnpm test
pnpm test:e2e
```

## Completion report

Report:

- changed files
- commands run and results
- blockers
- RunPod status if touched
- next goal
