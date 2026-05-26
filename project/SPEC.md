# SPEC.md — Project Aetherville Implementation Spec for Codex

## Product definition

Project Aetherville is a browser-viewed, cloud-inferred AI city simulator. It combines:

- LLM-based autonomous citizens with memory, reflection, plan trees, and dialogue
- YOLO-based vehicle camera perception
- Kinematic autonomous vehicle/drone control
- PPO-based traffic signal control
- LSTM traffic forecasting
- God Mode voice/text intervention
- RunPod GPU backend + local browser rendering

## MVP target

The first playable MVP must demonstrate:

1. RunPod backend boots and exposes health endpoints.
2. vLLM or configured fallback model answers a Korean test prompt.
3. Orchestrator emits tick/state updates over WebSocket.
4. Browser client renders a simple 3D city with citizens/vehicles placeholders.
5. Shared schema validates `state_update`, `event`, `command`, `ack`, and `error` envelopes.
6. God Mode text command changes weather and injects a memory/event.
7. Vision service returns mock detections first, then YOLO ONNX when available.
8. Traffic AI can run baseline fixed cycle first, then PPO checkpoint when trained.

## Cloud/backend scope

RunPod must host:

- `vllm` service or direct vLLM process
- `vision` FastAPI service
- `orchestrator` FastAPI + Socket.IO service
- `redis`
- optional `caddy` for TLS/WSS

Required ports:

| Service | Default port | Required health check |
|---|---:|---|
| vLLM | 8000 | `/v1/models` or simple chat completion |
| Vision | 8001 | `/health` |
| Orchestrator | 8080 | `/api/v1/health`, Socket.IO connect |
| Redis | 6379 | `redis-cli ping` or service-level ping |
| TLS gateway | 443 | HTTPS/WSS smoke check |

## Local/client scope

Local development must support:

- `pnpm install`
- `pnpm dev`
- `NEXT_PUBLIC_ORCHESTRATOR_URL`
- `NEXT_PUBLIC_SOCKET_URL`
- local replay mode for offline demo fallback

## Out of scope for first implementation pass

- Real robot/vehicle hardware
- LLM fine-tuning
- Production-grade auth beyond demo JWT/token gate
- Paid domain/TLS unless the user provides domain information
- Manual YOLO labeling
- Blockchain, VR/WebXR, mobile app

## Quality targets

- Tick loop: minimum 10 Hz for MVP; design toward 60 Hz broadcast/diff later
- WebSocket broadcast latency target: ≤ 50 ms in healthy cloud path
- YOLO target after real model integration: ≥ 50 FPS aggregate, mAP@0.5 ≥ 0.85
- God Mode command effect target: ≤ 3 sec
- Demo survival: replay mode must work when RunPod/network fails

## Implementation strategy

Build vertical slices in this order:

1. RunPod SSH + repo sync + health checks
2. Monorepo skeleton + shared schema package
3. Orchestrator tick + WebSocket state update
4. Client 3D placeholder city
5. Citizen minimal agent loop + memory panel
6. Vehicle + mock vision path
7. Real YOLO service integration
8. Traffic baseline + PPO wrapper
9. God Mode text first, voice later
10. Demo hardening + replay mode
