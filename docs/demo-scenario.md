# Demo Scenario

## Screen layout

- Top: RunPod endpoint/connection controls and fallback navigation
- Middle: large 3D city view with scene legend, weather, traffic, and actor labels
- Bottom panel deck: Memory stream, Vehicle cam + YOLO boxes, Traffic forecast, AI learning loop, and God Mode mic/text command

## 15-minute flow

1. 0:00–2:00 — project intro and architecture.
2. 2:00–6:00 — morning commute: citizens move, vehicles drive, memory stream updates.
3. 6:00–9:00 — God Mode: heavy rain and lottery event.
4. 9:00–12:00 — audience command via text/voice.
5. 12:00–14:00 — replay/accelerated week video or state log.
6. 14:00–15:00 — metrics, zero-labeling explanation, references.

## Must-have fallback

- If RunPod connection fails: switch to replay mode.
- If voice fails: use text input.
- If real YOLO fails: use mock detections preserving UI contract.
- If RL underperforms: show baseline comparison and training curve.
