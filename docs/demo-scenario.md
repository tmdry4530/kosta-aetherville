# Demo Scenario

## Screen layout

- Main: 3D city view
- Right top: Memory stream for selected citizen
- Right middle: Vehicle cam + YOLO boxes
- Bottom left: Traffic forecast chart
- Bottom right: God Mode mic/text command

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
