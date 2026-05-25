from __future__ import annotations

from typing import Any

import pytest
from fastapi.testclient import TestClient

from aetherville_schemas import (
    CitizenDetailResponse,
    CitizenListResponse,
    DialogueResponse,
    Envelope,
    EnvelopeType,
    GodCommandResponse,
    LearningStatusResponse,
    MemoryStreamResponse,
    ReflectionResponse,
    SimStatusResponse,
    VehicleCameraFrame,
    VisionDetectRequest,
    VisionDetectResponse,
    YoloDetection,
)
from aetherville_server import main
from aetherville_server.main import fastapi_app


def test_sim_status_uses_shared_response_model() -> None:
    response = TestClient(fastapi_app).get("/api/v1/sim/status")

    assert response.status_code == 200
    status = SimStatusResponse.model_validate(response.json())
    assert isinstance(status.running, bool)
    assert status.tick >= 0
    assert status.citizen_count == 7
    assert status.vehicle_count == 3
    assert status.traffic_light_count == 4


def test_god_command_uses_shared_request_and_response_models() -> None:
    response = TestClient(fastapi_app).post(
        "/api/v1/god/command",
        json={
            "kind": "god_command",
            "input_modality": "text",
            "raw_text": "도시에 비를 내려줘",
            "audio_blob_b64": None,
            "user_id": "presenter",
        },
    )

    assert response.status_code == 200
    body = GodCommandResponse.model_validate(response.json())
    assert body.accepted is True
    assert body.category == "environment"
    assert body.event.kind == "weather_changed"
    assert body.ai_mode == "rules"
    assert Envelope.model_validate(body.envelope.model_dump()).type is EnvelopeType.EVENT


def test_god_command_allows_local_browser_cors_preflight() -> None:
    client = TestClient(fastapi_app)
    for origin in ("http://127.0.0.1:3000", "http://127.0.0.1:3100"):
        response = client.options(
            "/api/v1/god/command",
            headers={
                "Origin": origin,
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "content-type",
            },
        )

        assert response.status_code == 200
        assert response.headers["access-control-allow-origin"] == origin
        assert "POST" in response.headers["access-control-allow-methods"]


def test_sim_control_and_snapshot_endpoints_use_shared_models() -> None:
    client = TestClient(fastapi_app)
    reset = client.post("/api/v1/sim/reset", json={"seed": 99})
    assert reset.status_code == 200
    assert SimStatusResponse.model_validate(reset.json()).tick == 0

    start = client.post("/api/v1/sim/start")
    assert start.status_code == 200
    assert SimStatusResponse.model_validate(start.json()).running is True

    snapshot = client.get("/api/v1/sim/state")
    assert snapshot.status_code == 200
    assert snapshot.json()["world"]["weather"] in {"clear", "rain"}
    assert "learning" in snapshot.json()

    stop = client.post("/api/v1/sim/stop")
    assert stop.status_code == 200
    assert SimStatusResponse.model_validate(stop.json()).running is False


def test_learning_status_endpoint_uses_shared_model() -> None:
    response = TestClient(fastapi_app).get("/api/v1/learning/status")

    assert response.status_code == 200
    status = LearningStatusResponse.model_validate(response.json())
    assert status.learning.mode == "deterministic_online_adaptation"
    assert status.explanation


def test_timeline_endpoint_returns_events_after_god_command() -> None:
    client = TestClient(fastapi_app)
    response = client.post(
        "/api/v1/god/command",
        json={
            "kind": "god_command",
            "input_modality": "text",
            "raw_text": "도시에 비를 내려줘",
            "audio_blob_b64": None,
            "user_id": "presenter",
        },
    )
    assert response.status_code == 200

    timeline = client.get("/api/v1/timeline")
    assert timeline.status_code == 200
    assert any(event["kind"] == "weather_changed" for event in timeline.json())


def test_citizen_rest_endpoints_use_shared_models() -> None:
    client = TestClient(fastapi_app)

    citizens = client.get("/api/v1/citizens")
    assert citizens.status_code == 200
    citizen_list = CitizenListResponse.model_validate(citizens.json())
    assert len(citizen_list.citizens) == 7
    assert [citizen.name for citizen in citizen_list.citizens[:2]] == ["민지", "민수"]

    detail = client.get("/api/v1/citizens/c01")
    assert detail.status_code == 200
    parsed_detail = CitizenDetailResponse.model_validate(detail.json())
    assert parsed_detail.plan_tree.children

    memories = client.get("/api/v1/citizens/c01/memories", params={"query": "harbor route"})
    assert memories.status_code == 200
    parsed_memories = MemoryStreamResponse.model_validate(memories.json())
    assert parsed_memories.memories[0].retrieval_score is not None


def test_citizen_dialogue_and_reflection_broadcast_events(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    emitted: list[tuple[str, dict[str, Any]]] = []

    async def fake_emit(event: str, data: dict[str, Any], to: str | None = None) -> None:
        del to
        emitted.append((event, data))

    monkeypatch.setattr(main.sio, "emit", fake_emit)
    client = TestClient(fastapi_app)

    dialogue = client.post(
        "/api/v1/citizens/c01/dialogue",
        json={"target_citizen_id": "c02", "topic": "traffic reroute"},
    )
    assert dialogue.status_code == 200
    parsed_dialogue = DialogueResponse.model_validate(dialogue.json())
    assert parsed_dialogue.events[0].kind == "dialog_started"

    reflection = client.post("/api/v1/citizens/c01/reflect")
    assert reflection.status_code == 200
    parsed_reflection = ReflectionResponse.model_validate(reflection.json())
    assert parsed_reflection.event.kind == "reflection_generated"
    assert {event for event, _ in emitted} == {"aetherville:event"}


def test_vehicle_camera_endpoint_uses_shared_schema() -> None:
    response = TestClient(fastapi_app).get("/api/v1/vehicles/v01/camera")

    assert response.status_code == 200
    frame = VehicleCameraFrame.model_validate(response.json())
    assert frame.vehicle_id == "v01"
    assert frame.mode == "mock"
    assert frame.detections


def test_vehicle_camera_endpoint_can_use_real_vision_boundary(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fake_post_vision_detect(request: VisionDetectRequest) -> VisionDetectResponse:
        assert request.camera_id == "v01-front"
        assert request.metadata["vehicle_id"] == "v01"
        return VisionDetectResponse(
            mode="real",
            detections=[
                YoloDetection(
                    label="traffic light",
                    confidence=0.93,
                    bbox=[274.0, 92.0, 288.0, 158.0],
                    traffic_light_state="unknown",
                )
            ],
        )

    monkeypatch.setenv("AETHERVILLE_CAMERA_VISION_MODE", "real")
    monkeypatch.setattr(main, "_post_vision_detect", fake_post_vision_detect)

    response = TestClient(fastapi_app).get("/api/v1/vehicles/v01/camera")

    assert response.status_code == 200
    frame = VehicleCameraFrame.model_validate(response.json())
    assert frame.mode == "real"
    assert frame.width == 640
    assert frame.height == 384
    assert [detection.label for detection in frame.detections] == ["traffic light"]
