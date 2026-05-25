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
5. Event-scoped City AI optionally summarizes world context and asks vLLM for a bounded high-level plan.
6. The simulation engine validates City AI actions and applies only the allowed executor vocabulary.
7. Traffic AI updates lights and forecast payload.
8. Orchestrator serializes state and broadcasts over Socket.IO.
9. Browser updates Three.js scene and UI panels.

## LLM call policy

- Do not call LLM every tick.
- Generate daily plans once per simulated day.
- Trigger dialogue/replanning only on events.
- Batch reflection periodically.
- Use vLLM continuous batching when available.
- City AI planning is interval/event scoped through `AETHERVILLE_CITY_AI_MODE` and `AETHERVILLE_CITY_AI_INTERVAL_TICKS`; vLLM returns JSON plans only, while Python simulation code executes movement, taxi, weather, memory, meeting, and traffic actions.
- Invalid, slow, or unavailable vLLM City AI output must fall back safely and must not mutate state directly.

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
