# Architecture Contract

## High-level contract

```text
RunPod GPU Server
  ├─ vLLM Server :8000
  ├─ Vision Service :8001
  ├─ Simulation Engine modules
  ├─ Orchestrator FastAPI + Socket.IO :8080
  ├─ Redis :6379
  └─ optional Caddy :443
       │ WSS + REST
       ▼
Local Browser Client
  ├─ Next.js App Router
  ├─ R3F / Three.js city scene
  ├─ side panels: memory, vehicle cam, traffic chart, God Mode
  └─ Web Audio / text command input
```

## Runtime flow

1. Simulation advances virtual time.
2. Citizen agents read cached plans and react to events.
3. Vehicle control updates paths and kinematic state.
4. Vision service processes vehicle camera frames or returns mock detections.
5. Traffic AI updates lights and forecast payload.
6. Orchestrator serializes state and broadcasts over Socket.IO.
7. Browser updates Three.js scene and UI panels.

## LLM call policy

- Do not call LLM every tick.
- Generate daily plans once per simulated day.
- Trigger dialogue/replanning only on events.
- Batch reflection periodically.
- Use vLLM continuous batching when available.

## MVP simplifications allowed

- Mock YOLO detections until ONNX model is trained.
- Baseline traffic lights until PPO checkpoint exists.
- Text God Mode before voice God Mode.
- Placeholder GLB/cubes before final assets.

## MVP simplifications not allowed

- Breaking final API/WS contracts.
- Removing RunPod cloud path.
- Skipping replay fallback.
- Hardcoding demo data directly into UI without a state/event interface.
