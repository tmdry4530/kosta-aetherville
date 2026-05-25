# DECISIONS.md — Project Aetherville ADR Log

## ADR-001: RunPod GPU backend is the primary inference/simulation host

- Status: accepted
- Context: The project requires GPU inference for vLLM, faster-whisper, and optional ONNX Runtime GPU. The user has already rented RunPod cloud.
- Decision: Codex should configure backend services through SSH to RunPod and keep the local machine focused on repository editing and browser rendering.
- Consequences:
  - SSH environment variables are required.
  - Direct-process runtime is the active execution strategy for the verified RunPod pod.
  - Docker Compose is optional future packaging/portability documentation only.
  - Direct-process runtime must exist for RunPod pods without Docker daemon.
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

## ADR-009: Verified RunPod execution uses direct-process runtime, not Docker-first deployment

- Status: accepted
- Context: Goal 00 verified RunPod SSH and GPU access, and the pod reports an NVIDIA GeForce RTX 4090. The current RunPod pod does not expose a usable Docker daemon. Docker daemon setup, Docker Compose execution, Docker-in-Docker, and blind Docker retries would add operational risk and are not required for the verified service path.
- Decision: Treat the RunPod pod itself as the execution environment. The active cloud runtime strategy is direct-process startup: vLLM or the OpenAI-compatible fallback through a documented direct command path, FastAPI orchestrator through `uvicorn`, vision through `uvicorn` or a deterministic stub, simulation as Python package/module code, and process management through shell scripts, tmux, nohup, or supervisor-compatible commands. Docker Compose artifacts are retained only as future portability/deployment documentation.
- Consequences:
  - Current cloud runtime acceptance must not require Docker execution.
  - Health checks and smoke tests must work against direct processes.
  - Deployment automation must prefer `--mode direct` and must not attempt Docker daemon setup or Docker-in-Docker on this pod.
  - `verify_runpod.sh` must not invoke Docker commands for this verified pod; it records the no-Docker direct-process policy instead.
  - `deploy_over_ssh.sh --mode compose` must fail fast as unsupported for the current execution path.
  - Future Docker packaging can be revisited only when a Docker-capable environment is explicitly selected and verified.
- Revisit when: the user moves to a Docker-capable VM/pod, adopts a managed inference endpoint, or explicitly approves a new containerized deployment target.


## ADR-010: Final demo operational risks are accepted for direct-process presentation

- Status: accepted
- Context: The master goal, Phase 99 re-audit, and final demo freeze pass are complete. The user explicitly accepted the remaining operational risks for the live demo.
- Decision: Proceed with the verified direct-process demo posture: public RunPod REST/WSS endpoints may remain untracked/unconfigured, SSH tunnel mode is an accepted fallback, vision runs on verified port `18001` while canonical `8001` is blocked on the current pod, real vLLM/YOLO/PPO/LSTM/STT workloads remain opt-in and are not started without a separate explicit model/runtime command, and remote sync may use tar-over-SSH while `rsync` is unavailable.
- Consequences:
  - The live demo can proceed using `docs/live-demo-runbook.md` Mode B when public endpoints are not configured.
  - `18001` is the accepted vision service port for the current pod demo.
  - Deterministic stubs remain demo-valid for ML-heavy paths until real workloads are separately approved with model names, cost/disk expectations, and rollback plan.
  - tar-over-SSH fallback is acceptable despite no delete semantics; stale remote file risk remains documented.
- Revisit when: public REST/WSS endpoints are configured, the pod template frees/proxies `8001`, remote `rsync` is installed, or real model workloads are explicitly requested.

## ADR-010 — Use explicit local CORS and quiet polling transport for the live demo

Date: 2026-05-25

Decision: The direct-process orchestrator allows only explicit local browser demo origins by default (`localhost`/`127.0.0.1`/`0.0.0.0` on ports `3000` and `3100`) and the browser client defaults Socket.IO to polling via `NEXT_PUBLIC_SOCKET_TRANSPORTS=polling`. Public or WSS demos can opt into `websocket,polling` through environment configuration.

Context: Dogfood QA showed the UI could display `connected` while REST God Mode commands were blocked by CORS, and WebSocket upgrade warnings created misleading console noise even though polling worked.

Consequences:
- Local-browser-to-RunPod tunnel demos can execute God Mode text commands without CORS failures.
- The default demo console stays quiet by using the verified polling path.
- Public deployment can still opt into WSS without changing code.
- Docker remains out of the current RunPod execution path.

Rejected: Enabling wildcard CORS for every origin by default, because explicit local demo origins are safer and enough for the approved presentation path.

## ADR-011: Demo self-learning uses persistent deterministic online adaptation before real training

- Status: accepted
- Context: The live demo must answer whether the city improves while the server stays online, but starting real vLLM fine-tuning, YOLO training, PPO training, LSTM retraining, or STT workloads without explicit model/cost approval would create GPU cost, disk, latency, and rollback risk. The approved current runtime is direct-process only.
- Decision: Add a JSON-backed deterministic online adaptation loop as the active demo self-learning layer. God Mode, 시민 기억, 택시, 날씨, and 교통 이벤트 are recorded as experience, persisted under the direct-process run directory, exposed through shared REST/state schemas, and fed back into traffic forecast pressure, vehicle speed factors, tags, and an AI learning panel.
- Consequences:
  - The demo can truthfully show persistent adaptation across long-running server sessions and process restarts without claiming real neural training.
  - Keeping the server running improves accumulated demo policy state only through observed/commanded events; it does not automatically train new vLLM/YOLO/PPO/LSTM weights.
  - Resetting the simulation does not clear the persisted learning snapshot unless the operator intentionally removes or changes the learning state path.
  - Real autonomous learning remains an explicit upgrade path requiring approved storage, training jobs, checkpoints, model names, cost limits, and rollback.
  - Docker remains excluded from the current RunPod execution path.
- Revisit when: real training/inference workloads are explicitly approved with model/runtime parameters, or a production persistence backend replaces JSON state.

## ADR-012: Approved 4090 workload runs real vLLM 14B AWQ before broader GPU training

- Status: accepted
- Context: The user approved active use of the RTX 4090 RunPod. The current pod driver exposes CUDA 12.8 capability and has enough disk for a quantized 14B model, but the newest vLLM release pulled CUDA 13-era Torch packages that failed against the pod driver.
- Decision: Run real vLLM through the existing direct-process port `8000` using `Qwen/Qwen2.5-14B-Instruct-AWQ`, `vllm==0.10.2`, `transformers==4.55.4`, model cache under `/workspace/aetherville-model-cache`, and OpenAI-compatible `/v1` APIs. Keep Docker out of the runtime. Connect citizen reflection to the real vLLM endpoint through a fallback-safe OpenAI-compatible planner.
- Consequences:
  - The demo now has a real 4090-backed LLM path for citizen reflection instead of only a mock fallback.
  - vLLM startup requires model-cache persistence and longer health waits than the mock fallback.
  - The CUDA/version pins are part of the current pod contract until the driver or image changes.
  - If real vLLM fails, deterministic cached planner fallback remains available without breaking the demo.
- Revisit when: the RunPod image/driver changes, a larger model is selected, or model serving moves to a managed endpoint.

## ADR-013: Vehicle camera panel proves request-scoped real YOLO instead of tick-loop inference

- Status: accepted
- Context: The demo could still look like a loop if the vehicle camera panel only displayed state-embedded mock detections while the separate vision service ran real YOLO. Running YOLO on every simulation tick would also waste GPU budget because real vLLM already occupies most RTX 4090 VRAM.
- Decision: Keep the simulation tick loop deterministic and cheap, but let `/api/v1/vehicles/{id}/camera` call the direct-process vision `/detect` endpoint when `AETHERVILLE_CAMERA_VISION_MODE=real`. The shared `VehicleCameraFrame` contract now reports `mode: mock|real`, and the browser panel polls the camera endpoint and badges `REAL YOLO · RunPod 4090` when real detections arrive.
- Consequences:
  - The 15-minute demo has visible proof that the vehicle camera path is backed by the real RunPod YOLO process.
  - GPU inference is request-scoped to the panel/smoke path, not multiplied by the 10 Hz world-state loop.
  - If real YOLO or the camera endpoint is unavailable, the UI falls back to state-embedded deterministic detections and stays demo-safe.
  - Docker remains excluded from the current execution strategy.
- Revisit when: a real camera frame stream exists, batching is needed, or YOLO moves to a dedicated inference process/GPU separate from vLLM.

## ADR-014: Use a short CUDA-trained traffic checkpoint before full PPO/LSTM jobs

- Status: accepted
- Context: The demo needed stronger proof that traffic AI is not only a fixed-cycle animation, but the current RunPod vLLM + YOLO workload already uses most RTX 4090 VRAM and the live demo must remain reliable.
- Decision: Add a lightweight traffic policy trainer that can use PyTorch/CUDA on the RunPod 4090 and export a small JSON linear policy checkpoint. Runtime inference stays torch-free: the orchestrator loads `AETHERVILLE_TRAFFIC_POLICY_CHECKPOINT`, exposes `TrafficAiSnapshot`, and drives signal phases from the checkpoint when present.
- Consequences:
  - The demo now has a measured GPU-trained traffic policy path with `torch_cuda` evidence.
  - The checkpoint reduced average queue by 31.628% versus fixed cycle in the deterministic `TrafficSignalEnv` benchmark used for the live slice.
  - Missing or underperforming checkpoints fall back to fixed-cycle/pressure-safe behavior, so demo reliability is preserved.
  - Full PPO and LSTM training remain upgrade paths for longer, broader traffic scenarios.
  - Docker remains excluded from the current RunPod execution strategy.
- Revisit when: a longer training window is approved, multiple intersections require a richer observation/action space, or traffic forecasting moves from deterministic facade to a trained sequence model.
