# Goal 06 — Citizen Agents

## Objective

Implement minimal citizen persona, memory stream, planning, dialogue event, and reflection interfaces.

## Scope

- Allowed: `server/agents/**`, `server/llm/**`, `server/orchestrator/**`, `client/src/ui/MemoryPanel*`, schemas/tests.

## Acceptance criteria

- 20 citizens can be fixture-generated.
- Memory retrieval score implemented and tested.
- Plan tree exists.
- Dialogue/memory events broadcast.
- LLM calls are cached/event-driven, not per tick.

## Verification commands

```bash
uv run pytest server/agents server/llm packages
pnpm test
```

## Completion report

Report:

- changed files
- commands run and results
- blockers
- RunPod status if touched
- next goal
