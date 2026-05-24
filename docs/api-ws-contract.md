# API and WebSocket Contract

## WebSocket envelope

All messages use envelope pattern:

```json
{
  "v": 1,
  "type": "state_update | state_diff | event | command | ack | error",
  "ts": 1700000000.123,
  "tick": 12345,
  "payload": {}
}
```

## Server to client

### `state_update`

Required payload sections:

- `world`: `time_of_day`, `weather`, `temperature`
- optional world intervention fields: `active_event`, `infrastructure_status`
- `citizens`: id, name, pos, rot, anim, current_action, talking_to
- `vehicles`: id, type, pos, rot, speed, passenger_id, destination, yolo_detections
- `drones`: id, pos, destination, cargo, battery
- `traffic_lights`: id, pos, state, remaining_sec
- `traffic_forecast`: next_15min list

### `event`

Supported kinds:

- `dialog_started`
- `dialog_ended`
- `dialog_chunk`
- `memory_added`
- `reflection_generated`
- `trip_requested`
- `trip_completed`
- `collision_avoided`
- `god_command_executed`
- `weather_changed`
- `event_injected`
- `person_updated`
- `infrastructure_changed`
- `relationship_changed`

## Client to server

### `god_command`

```json
{
  "kind": "god_command",
  "input_modality": "voice | text",
  "raw_text": "도시에 갑자기 폭우가 내립니다",
  "audio_blob_b64": null,
  "user_id": "presenter"
}
```

God Mode responses include `category`:

- `environment`
- `event`
- `person`
- `infrastructure`
- `relationship`

Responses may contain multiple `events`/`envelopes` when a command also injects memories.

### `select_entity`

```json
{
  "kind": "select_entity",
  "entity_type": "citizen | vehicle | drone",
  "entity_id": "c01"
}
```

### `sim_control`

```json
{
  "kind": "sim_control",
  "action": "pause | resume | set_speed | reset",
  "speed_multiplier": 1.0
}
```

## REST endpoints

All endpoints use `/api/v1` prefix.

| Method | Path | Purpose |
|---|---|---|
| GET | `/sim/status` | current tick/time/counts |
| POST | `/sim/start` | start simulation |
| POST | `/sim/stop` | stop simulation |
| POST | `/sim/reset` | reset with optional seed |
| GET | `/citizens` | list citizens |
| GET | `/citizens/{id}` | citizen detail |
| GET | `/citizens/{id}/memories` | paginated memory stream |
| POST | `/citizens/{id}/reflect` | force reflection |
| GET | `/timeline` | event timeline |
| GET | `/vehicles/{id}/camera` | latest PNG camera frame |
| POST | `/god/command` | REST fallback command path |
| GET | `/health` | service health |
| GET | `/metrics` | Prometheus-compatible metrics |

## Contract test rules

- Every Pydantic model must have fixture parse tests.
- Every REST response must validate against shared schema or explicit response model.
- TypeScript client types must be generated, not rewritten by hand.

## Citizen agent REST payloads

Phase 06 adds shared-schema response models for citizen UI and agent events:

- `CitizenPersona`: id, name, age, occupation, traits, home district, daily goal.
- `PlanNode`: recursive plan tree with `pending | active | done` status.
- `MemoryRecord`: text, tick, importance, tags, and optional retrieval score.
- `CitizenDetailResponse`: persona, plan tree, and memory stream.
- `DialogueResponse` / `ReflectionResponse`: event envelopes that can be broadcast as `aetherville:event`.

The orchestrator exposes:

| Method | Path | Purpose |
|---|---|---|
| GET | `/citizens` | list the 20 deterministic demo personas |
| GET | `/citizens/{id}` | persona detail, plan tree, and seed memories |
| GET | `/citizens/{id}/memories?query=` | scored memory stream |
| POST | `/citizens/{id}/dialogue` | trigger dialogue/memory event envelopes |
| POST | `/citizens/{id}/reflect` | trigger cached reflection event envelope |

LLM policy remains event-driven: plans/reflections are cached and must not run once per simulation tick.

## Vehicle and vision payloads

Phase 07 adds shared-schema models for the camera/vision path:

- `VisionDetectRequest`: base64 frame, camera id, and metadata.
- `VisionDetectResponse`: `mock | real` mode plus `YoloDetection[]`.
- `VehicleCameraFrame`: vehicle id, optional frame payload, frame size, and detections.
- `TripState`: trip assignment, origin/destination, status, and path.

`VehicleState.yolo_detections` uses the same `YoloDetection` objects returned by `/detect`.
The browser camera panel overlays boxes from these detections, so mock and future real YOLO share one contract.
