# Vision / YOLO Upgrade Path

## Current demo mode

- The active Phase 07 implementation uses deterministic mock detections.
- `/detect` accepts `VisionDetectRequest` and returns `VisionDetectResponse`.
- Vehicle state embeds the same `YoloDetection` schema used by the vision service.
- This keeps the browser camera overlay, vehicle slowdown demo, and API contract stable without downloading models or starting GPU inference.

## Real inference path

1. Keep the HTTP contract unchanged:
   - request: `frame_b64`, `camera_id`, `metadata`
   - response: `mode`, `detections[]`
2. Add a model loader behind the vision service boundary.
3. Decode the frame to an image tensor.
4. Run YOLO/ONNX inference on the RunPod GPU.
5. Convert boxes/classes/confidence to shared `YoloDetection`.
6. Preserve deterministic mock fallback when the model is missing or disabled.

## Safety and cost gates

- Do not download model weights without explicit model/storage approval.
- Do not start long training jobs during demo readiness work.
- Keep real inference opt-in via environment, for example `AETHERVILLE_VISION_MODE=real`.
- Continue to report GPU process state through `nvidia-smi` before and after real inference tests.

## Target metrics after real integration

- Aggregate camera inference target from `SPEC.md`: at least 50 FPS aggregate.
- Detection quality target from `SPEC.md`: mAP@0.5 at least 0.85 after a real dataset/training path exists.
- Phase 07 only proves the service contract and UI overlay with mock-safe detections.

## Real YOLO activation evidence — 2026-05-25

- Real inference mode is implemented behind `AETHERVILLE_VISION_MODE=real`.
- RunPod package: `ultralytics 8.4.53`.
- Model: `yolo11n.pt`.
- Device: `AETHERVILLE_YOLO_DEVICE=0` on the RTX 4090.
- `/health` reports `yolo:ok` when the optional runtime is installed.
- `/detect` returns `VisionDetectResponse(mode="real", detections=[...])` and preserves mock fallback on decode/runtime failure.
- The smoke path uses a deterministic synthetic road frame when `frame_b64` is omitted; real camera frames should be provided through the same `frame_b64` contract.
- Default real-mode post-filter keeps traffic-relevant COCO labels: person, bicycle, car, motorcycle, bus, truck, traffic light, and stop sign.
