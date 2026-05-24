# DECISIONS.md — Project Aetherville ADR Log

## ADR-001: RunPod GPU backend is the primary inference/simulation host

- Status: accepted
- Context: The project requires GPU inference for vLLM, faster-whisper, and optional ONNX Runtime GPU. The user has already rented RunPod cloud.
- Decision: Codex should configure backend services through SSH to RunPod and keep the local machine focused on repository editing and browser rendering.
- Consequences:
  - SSH environment variables are required.
  - Docker Compose path is preferred only when Docker daemon is available.
  - Direct-process fallback must exist for RunPod pods without Docker daemon.
- Revisit when: the user moves to a VM with full Docker support or a managed inference endpoint.

## ADR-002: Shared schemas are the single source of truth

- Status: accepted
- Context: WebSocket and REST contracts are core to this app.
- Decision: Define Pydantic models first in `packages/shared-schemas/src/python/aetherville_schemas`, then generate TypeScript/Zod outputs.
- Consequences:
  - No duplicated hand-written TypeScript schema unless generated or explicitly documented.
  - Contract tests are mandatory for message envelopes and state updates.

## ADR-003: Build demo-first vertical slices

- Status: accepted
- Context: The PRD is broad: citizens, vehicles, vision, RL, forecasting, voice, and 3D rendering.
- Decision: Implement minimum playable slices before optimizing models.
- Order:
  1. Cloud health + WebSocket tick
  2. Browser city scene
  3. Mock citizens/vehicles/traffic
  4. Real agent/vision/RL integration
- Consequences: Mock services are allowed only when they preserve the final interface.

## ADR-004: Replay mode is required, not optional

- Status: accepted
- Context: Demo risks include internet failure, RunPod interruption, and GPU/model latency.
- Decision: Client must support replay mode from recorded state/event streams.
- Consequences: Orchestrator must be able to write replay logs or a snapshot stream.

## ADR-005: God Mode text command ships before voice

- Status: accepted
- Context: Voice adds STT, microphone permissions, latency, and noisy room risk.
- Decision: Implement text command path first with the same command dispatcher; add Web Audio/faster-whisper later.
- Consequences: UI should expose text fallback even after microphone integration.

## ADR-006: Foundation monorepo uses uv workspace plus pnpm workspace

- Status: accepted
- Context: The project needs Python cloud services, generated shared contracts, and a browser client to evolve in one repository without duplicating API/WS schemas.
- Decision: Use a root `uv` workspace for `server` and `packages/shared-schemas`, and a root `pnpm` workspace for `client` and `packages/shared-schemas` TypeScript exports. Pydantic remains the source of truth; TypeScript output is generated into the shared schema package.
- Consequences:
  - Python verification starts with `uv sync` and `uv run pytest`.
  - Client verification starts with `pnpm install`, `pnpm lint`, and `pnpm typecheck`.
  - Schema changes must update Pydantic models first and regenerate TypeScript before client use.
- Revisit when: Phase 03 replaces the M0 TypeScript generator with a stricter JSON Schema/Zod generation pipeline.

## ADR-007: Direct-process cloud runtime uses safe mock services before real GPU model startup

- Status: accepted
- Context: The current RunPod pod has GPU visibility but no Docker daemon, no redis-server, no node/pnpm, no uv on the default PATH, and no configured public service URLs. Real vLLM model download would add cost, disk, and credential risk before the playable demo contracts are stable.
- Decision: Use direct-process FastAPI services for orchestrator, vision mock, and OpenAI-compatible vLLM fallback. Install `uv` user-locally on the pod when explicitly bootstrapping direct mode. Use Redis memory fallback until a Redis binary or managed Redis path is available. Do not start real vLLM unless `AETHERVILLE_VLLM_MODE=real` and an approved `MODEL_NAME` are provided.
- Consequences:
  - Phase 02 can verify cloud health without GPU spend or model credentials.
  - `:8000` and `:8080` are active on RunPod; vision uses `:18001` for now because the pod template owns `:8001` with nginx.
  - The final demo must resolve vision public/default port exposure by freeing/proxying `:8001` or documenting an explicit port mapping.
- Revisit when: the RunPod template changes, Docker becomes available, Redis is installed, or real vLLM model access is approved.

## ADR-008: Citizen LLM interfaces are event-driven and cached before real vLLM integration

- Status: accepted
- Context: Citizen agents need personas, plans, memory, dialogue, and reflection, but RunPod real vLLM startup remains opt-in to avoid model download, credential, disk, and GPU cost risk before final demo integration.
- Decision: Use deterministic persona fixtures and a cached LLM facade for daily plans/reflections. Planning and reflection are triggered by explicit events/endpoints, not by the simulation tick loop.
- Consequences:
  - Phase 06 can verify citizen behavior without GPU spend.
  - The API shape remains compatible with a later vLLM-backed planner.
  - Tests assert cache reuse so future implementations do not regress into per-tick LLM calls.
- Revisit when: real vLLM model access is approved and a batch planning/reflection worker is introduced.
