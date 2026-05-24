---
name: api-contract-audit
description: Use when changing WebSocket envelopes, REST endpoints, shared Pydantic models, or generated TypeScript types.
---

# API Contract Audit

1. Check Pydantic source models.
2. Check generated TypeScript/Zod output or generation script.
3. Validate fixtures for `state_update`, `event`, `command`, `ack`, `error`.
4. Confirm backend response models use shared schema.
5. Confirm client imports generated types.
6. Report schema drift and missing tests.
