# Goal 99 — Final Audit

## Objective

Audit the entire repo against PRD-derived acceptance criteria before demo or submission.

## Scope

- Read-only first. Only edit docs/checklists if missing evidence.
- Do not change implementation during audit unless user approves.

## Acceptance criteria

- All M0-M6 tasks statuses are accurate.
- Tests/metrics/demos have evidence.
- RunPod endpoints documented.
- README has setup and demo instructions.
- Known risks are listed.

## Verification commands

```bash
git status --short
uv run pytest
pnpm lint
pnpm typecheck
pnpm test
```

## Completion report

Report:

- changed files
- commands run and results
- blockers
- RunPod status if touched
- next goal
