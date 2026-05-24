# packages/shared-schemas/AGENTS.md

## Scope

Shared Pydantic and generated TypeScript/Zod schemas.

## Rules

- Python/Pydantic is the source of truth.
- TypeScript outputs are generated.
- Do not hand-edit generated files unless generation is not implemented yet and the exception is documented.
- Every schema needs at least one valid fixture and one invalid fixture test.

## Required schema groups

- WebSocket envelopes
- World state
- Entities
- God Mode commands
- REST API responses
- Error payloads
