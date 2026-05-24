# Module Implementation Guide

## Citizen agents

Implement in stages:

1. Static persona fixture generation.
2. Memory stream object with recency/importance/relevance scoring.
3. Daily plan tree using LLM endpoint or deterministic fallback.
4. Event-driven dialogue trigger.
5. Reflection threshold and batch reflection.

Do not block tick loop on individual LLM calls. Use queues/semaphores.

## Vehicle control

Implement in stages:

1. Road graph and A* pathfinding.
2. Kinematic movement along waypoints.
3. PID-like speed target update.
4. Braking on pedestrian/red light detection.
5. Trip manager pickup/drop matching.

## Vision service

Implement in stages:

1. `/health` and `/detect` with mock detections.
2. Base64 image decode + schema validation.
3. ONNX Runtime wrapper.
4. Batch inference.
5. Auto-label/training scripts.

## Traffic AI

Implement in stages:

1. Fixed-cycle baseline.
2. `TrafficSignalEnv` reset/step.
3. PPO checkpoint wrapper.
4. LSTM/Darts forecast wrapper.
5. Baseline vs RL metrics.

## God Mode

Implement in stages:

1. Text command input.
2. Intent parser with fixed categories.
3. Dispatcher: weather/event/person/infrastructure/relationship.
4. Memory injection.
5. Browser mic → faster-whisper.

## Client

Implement in stages:

1. Connection store and Socket.IO client.
2. City scene shell.
3. Citizens/vehicles/traffic lights as simple meshes.
4. Side panels.
5. Replay mode.
6. Real GLB assets and animation.
