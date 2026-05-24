# AGENTS.md — Project Aetherville Codex Contract

## Mission

Build Project Aetherville: a full-stack AI society simulator integrating LLM citizens, YOLO vision autonomous driving, RL traffic lights, time-series traffic forecasting, a cloud GPU inference backend, and a browser 3D client.

The backend runs on a rented RunPod GPU instance via SSH. The local machine runs Codex, repository editing, and the browser client. Cloud inference, orchestrator, simulation, vision, traffic AI, Redis, and optional TLS gateway run on RunPod or in equivalent cloud services.

## Non-negotiable architecture

- Cloud GPU server owns AI inference and simulation backend.
- Local browser owns UI and 3D rendering.
- Backend services:
  - vLLM OpenAI-compatible endpoint on `:8000`
  - Vision service on `:8001`
  - Orchestrator FastAPI/Socket.IO on `:8080`
  - Redis on `:6379`
  - optional Caddy/TLS on `:443`
- Client uses Next.js App Router + R3F/Three.js + Zustand + socket.io-client.
- Server uses FastAPI + asyncio + python-socketio + Pydantic schemas.
- Shared schemas are single source of truth; do not duplicate WS/REST contracts by hand.

## Work protocol

1. Read `SPEC.md`, `TEST_PLAN.md`, `DECISIONS.md`, and relevant `docs/*.md` before non-trivial implementation.
2. For long tasks, use the matching `.codex/goals/*.md` file as acceptance criteria.
3. Prefer `/plan` before broad edits.
4. Keep diffs scoped to the goal file.
5. Update `TASKS.json`, `PROGRESS.md`, and `SESSION_HANDOFF.md` whenever a milestone changes state.
6. If RunPod SSH, Docker, GPU, model download, or port exposure fails, stop blind retries and document the blocker.

## Package managers and commands

- Python: `uv`
- Node: `pnpm`
- Python lint/type: `ruff check .`, `mypy server packages`
- JS/TS lint/type: `pnpm lint`, `pnpm typecheck`
- Tests:
  - `uv run pytest`
  - `pnpm test`
  - `pnpm test:e2e` when browser workflow exists
- Docker path:
  - `docker compose -f docker-compose.yml -f docker-compose.cloud.yml config`
  - `docker compose -f docker-compose.yml -f docker-compose.cloud.yml up -d --build`

## RunPod rules

- Never hardcode SSH host, port, user, key path, Hugging Face token, JWT secret, or domain.
- Use `infra/runpod/.env.runpod` locally; keep it ignored.
- First SSH command must be read-only verification: `hostname`, `nvidia-smi`, `pwd`, `python --version`, `docker info`.
- Do not assume Docker daemon exists inside a RunPod pod. Detect it.
- If Docker is unavailable, switch to direct-process fallback and document the trade-off.
- Do not run destructive cleanup on `/workspace`, `/root`, or model cache without explicit user approval.

## Safety rails

- Do not commit `.env`, `.env.runpod`, private keys, tokens, model credentials, or generated large artifacts.
- Do not weaken tests to get green.
- Do not change public schemas without updating both Python and TypeScript schema outputs.
- Do not add new production dependencies without explaining why existing stack cannot solve it.
- Do not silently reduce scope; record scope cuts in `DECISIONS.md`.

## Completion report required

Every implementation turn must end with:

1. Changed files
2. Verification commands run
3. Pass/fail results
4. RunPod state if touched
5. Remaining blockers or risks
6. Next recommended goal file

## Langauage

- Always use Korean for chat, plan, tasks, etc