# Goal 01 — Foundation Monorepo

## Objective

Create the pnpm + uv monorepo skeleton and minimum packages/services for M0.

## Scope

- Allowed: root config, `packages/shared-schemas/**`, `server/**`, `client/**`, `docs/**`, `PROGRESS.md`, `TASKS.json`, `SESSION_HANDOFF.md`.

## Acceptance criteria

- `pnpm-workspace.yaml`, root `pyproject.toml`, `.env.example` exist.
- Shared schemas package has Pydantic envelope/state/command models.
- Server orchestrator has `/api/v1/health`.
- Client can install and render placeholder page.
- Basic tests exist.

## Verification commands

```bash
uv sync
pnpm install
uv run pytest
pnpm lint
pnpm typecheck
```

## Completion report

Report:

- changed files
- commands run and results
- blockers
- RunPod status if touched
- next goal
