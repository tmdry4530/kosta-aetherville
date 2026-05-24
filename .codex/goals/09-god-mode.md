# Goal 09 — God Mode

## Objective

Implement God Mode text command, command dispatcher, memory injection, and then voice STT when stable.

## Scope

- Allowed: `server/voice/**`, `server/orchestrator/command_handler.py`, `server/sim/**`, `client/src/ui/GodModeMic*`, schemas/tests.

## Acceptance criteria

- Text command changes weather.
- Commands support environment/event/person/infrastructure/relationship categories.
- Events broadcast.
- Memory injection for relationship/person events.
- Voice path is optional until text path is stable.

## Verification commands

```bash
uv run pytest server/voice server/orchestrator server/sim packages
pnpm test
```

## Completion report

Report:

- changed files
- commands run and results
- blockers
- RunPod status if touched
- next goal
