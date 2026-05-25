from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from aetherville_schemas import (
    HealthResponse,
    VisionDetectRequest,
    VisionDetectResponse,
    YoloDetection,
)
from aetherville_server import vision, vllm_fallback


def test_vision_health_uses_shared_schema() -> None:
    response = TestClient(vision.app).get("/health")

    assert response.status_code == 200
    health = HealthResponse.model_validate(response.json())
    assert health.service == "vision"
    assert health.dependencies[0].status == "stub"


def test_vision_detect_returns_mock_shared_detection() -> None:
    response = TestClient(vision.app).post("/detect", json={"frame_b64": None})

    assert response.status_code == 200
    body = VisionDetectResponse.model_validate(response.json())
    assert body.mode == "mock"
    assert body.detections[0].label == "traffic_light"


def test_vision_detect_can_use_real_yolo_boundary(monkeypatch: pytest.MonkeyPatch) -> None:
    class FakeDetector:
        @staticmethod
        def detect(request: VisionDetectRequest) -> list[YoloDetection]:
            assert request.camera_id == "v01-front"
            return [
                YoloDetection(
                    label="car",
                    confidence=0.91,
                    bbox=[10.0, 20.0, 100.0, 140.0],
                    traffic_light_state=None,
                )
            ]

    monkeypatch.setenv("AETHERVILLE_VISION_MODE", "real")
    monkeypatch.setattr(vision, "get_real_detector", lambda: FakeDetector())

    response = TestClient(vision.app).post(
        "/detect",
        json={"frame_b64": None, "camera_id": "v01-front", "metadata": {"tick": 10}},
    )

    assert response.status_code == 200
    body = VisionDetectResponse.model_validate(response.json())
    assert body.mode == "real"
    assert body.detections[0].label == "car"


def test_vllm_fallback_models_endpoint_is_openai_compatible_enough_for_smoke() -> None:
    response = TestClient(vllm_fallback.app).get("/v1/models")

    assert response.status_code == 200
    assert response.json()["data"][0]["id"] == "aetherville-mock-llm"


def test_vllm_fallback_chat_handles_korean_prompt() -> None:
    response = TestClient(vllm_fallback.app).post(
        "/v1/chat/completions",
        json={
            "model": "aetherville-mock-llm",
            "messages": [{"role": "user", "content": "서울 날씨를 설명해줘"}],
        },
    )

    assert response.status_code == 200
    content = response.json()["choices"][0]["message"]["content"]
    assert "Aetherville" in content
    assert "서울 날씨" in content
