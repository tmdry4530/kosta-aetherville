# Goal 03 — Shared Schemas, REST, WebSocket

## Objective

Implement Pydantic models and generated TypeScript types for REST/WS contracts, then wire them into orchestrator and client.

## Scope

- Allowed: `packages/shared-schemas/**`, `server/orchestrator/**`, `client/src/ws/**`, contract tests.

## Acceptance criteria

- Envelope parses state_update/event/command/ack/error.
- REST `/api/v1/health`, `/sim/status`, `/god/command` use response models.
- Client receives tick updates.
- TypeScript types generated or documented.

## Verification commands

```bash
uv run pytest packages server
pnpm test
pnpm typecheck
```

## Completion report

Report:

- changed files
- commands run and results
- blockers
- RunPod status if touched
- next goal
