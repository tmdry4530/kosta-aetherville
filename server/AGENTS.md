# server/AGENTS.md

## Scope

Backend services for RunPod/cloud:

- orchestrator
- sim
- agents
- vehicles
- vision
- traffic_ai
- llm
- voice

## Rules

- Use FastAPI + asyncio patterns.
- Never block the tick loop on LLM/vision calls.
- Use queues/semaphores for GPU-bound requests.
- All request/response schemas must come from shared schema package.
- Each service must expose `/health`.
- Prefer mock-compatible interfaces before real model integration.

## Verification

Run from repo root:

```bash
uv run ruff check server packages
uv run mypy server packages
uv run pytest server packages
```
