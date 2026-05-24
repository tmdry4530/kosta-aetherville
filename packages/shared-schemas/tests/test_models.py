from __future__ import annotations

import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from aetherville_schemas import (
    CitizenDetailResponse,
    Envelope,
    EnvelopeType,
    GodCommand,
    HealthResponse,
    MemoryRecord,
    PlanNode,
    TripState,
    VehicleCameraFrame,
    VisionDetectResponse,
    WorldStatePayload,
    make_state_update,
)

FIXTURES = Path(__file__).parent / "fixtures"


def test_state_update_fixture_parses() -> None:
    raw = json.loads((FIXTURES / "state_update.json").read_text(encoding="utf-8"))
    envelope = Envelope.model_validate(raw)
    payload = WorldStatePayload.model_validate(envelope.payload)

    assert envelope.type is EnvelopeType.STATE_UPDATE
    assert envelope.tick == 12
    assert payload.world.weather == "clear"
    assert payload.citizens[0].id == "c01"
    assert payload.vehicles[0].yolo_detections[0].label == "pedestrian"


def test_invalid_envelope_type_is_rejected() -> None:
    with pytest.raises(ValidationError):
        Envelope.model_validate({"v": 1, "type": "unknown", "ts": 1, "tick": 0, "payload": {}})


def test_god_command_validates_text_payload() -> None:
    command = GodCommand.model_validate(
        {
            "kind": "god_command",
            "input_modality": "text",
            "raw_text": "도시에 비가 내리게 해줘",
            "audio_blob_b64": None,
            "user_id": "presenter",
        }
    )

    assert command.raw_text.startswith("도시에")


def test_make_state_update_roundtrip() -> None:
    raw = json.loads((FIXTURES / "state_update.json").read_text(encoding="utf-8"))
    payload = WorldStatePayload.model_validate(raw["payload"])
    envelope = make_state_update(payload, tick=99)

    assert Envelope.model_validate(envelope.model_dump(mode="json")).tick == 99


def test_health_response_contract_accepts_stub_dependencies() -> None:
    health = HealthResponse.model_validate(
        {
            "service": "orchestrator",
            "status": "ok",
            "version": "0.1.0",
            "dependencies": [
                {"name": "redis", "status": "stub", "detail": "in-memory fallback"}
            ],
        }
    )

    assert health.dependencies[0].status == "stub"


def test_citizen_agent_contracts_validate() -> None:
    detail = CitizenDetailResponse.model_validate(
        {
            "persona": {
                "id": "c01",
                "name": "민준",
                "age": 31,
                "occupation": "cafe owner",
                "traits": ["curious"],
                "home_district": "harbor",
                "daily_goal": "open cafe",
            },
            "plan_tree": {
                "id": "plan_c01",
                "title": "daily loop",
                "status": "active",
                "children": [
                    {
                        "id": "plan_c01_morning",
                        "title": "open cafe",
                        "status": "done",
                        "children": [],
                    }
                ],
            },
            "memories": [
                {
                    "id": "mem_c01_001",
                    "citizen_id": "c01",
                    "text": "rain started",
                    "created_tick": 4,
                    "importance": 0.8,
                    "tags": ["weather"],
                    "retrieval_score": 1.05,
                }
            ],
        }
    )

    assert isinstance(detail.plan_tree, PlanNode)
    assert isinstance(detail.memories[0], MemoryRecord)
    assert detail.memories[0].retrieval_score == 1.05


def test_vehicle_and_vision_contracts_validate() -> None:
    detection = {
        "label": "pedestrian",
        "confidence": 0.87,
        "bbox": [118, 66, 164, 170],
        "traffic_light_state": None,
        "distance_m": 9.5,
    }
    response = VisionDetectResponse.model_validate({"mode": "mock", "detections": [detection]})
    frame = VehicleCameraFrame.model_validate(
        {
            "vehicle_id": "v01",
            "frame_b64": None,
            "width": 320,
            "height": 180,
            "detections": [detection],
        }
    )
    trip = TripState.model_validate(
        {
            "id": "trip_001",
            "passenger_id": "c01",
            "vehicle_id": "v01",
            "origin": [-4, 0, -4],
            "destination": [4, 0, 4],
            "status": "enroute",
            "path": [[-4, 0, -4], [4, 0, 4]],
        }
    )

    assert response.detections[0].label == "pedestrian"
    assert frame.width == 320
    assert trip.path[-1] == [4, 0, 4]
