from __future__ import annotations

from fastapi.testclient import TestClient

from aetherville_schemas import VisionDetectResponse
from aetherville_server import vision


def test_vision_detect_returns_shared_schema_valid_detections() -> None:
    response = TestClient(vision.app).post(
        "/detect",
        json={"frame_b64": None, "camera_id": "v01-front", "metadata": {"tick": 10}},
    )

    assert response.status_code == 200
    parsed = VisionDetectResponse.model_validate(response.json())
    assert parsed.mode == "mock"
    assert {detection.label for detection in parsed.detections} >= {"traffic_light", "pedestrian"}
