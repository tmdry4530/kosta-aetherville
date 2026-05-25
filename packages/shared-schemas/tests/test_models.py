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
    GodCommandResponse,
    HealthResponse,
    LearningSnapshot,
    LearningStatusResponse,
    MemoryRecord,
    PlanNode,
    TrafficAiSnapshot,
    TrafficForecastAiSnapshot,
    TripState,
    VehicleCameraFrame,
    VisionDetectResponse,
    VoiceCommandRequest,
    VoiceCommandResponse,
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
    assert payload.citizens[0].display_tags == ["시민", "인도"]
    assert payload.vehicles[0].yolo_detections[0].label == "pedestrian"
    assert payload.vehicles[0].display_tags == ["택시", "차도"]
    assert payload.traffic_lights[0].display_tags == ["신호등", "green"]
    assert payload.learning.mode == "deterministic_online_adaptation"
    assert payload.learning.experience_count == 0


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



def test_god_command_response_contract_exposes_ai_interpretation_metadata() -> None:
    response = GodCommandResponse.model_validate(
        {
            "accepted": True,
            "command_id": "cmd_test",
            "category": "infrastructure",
            "event": {
                "kind": "infrastructure_changed",
                "message": "Traffic congestion surge applied",
                "metadata": {"action": "traffic_jam", "ai_mode": "vllm"},
            },
            "envelope": {
                "v": 1,
                "type": "event",
                "ts": 1,
                "tick": 0,
                "payload": {"kind": "infrastructure_changed"},
            },
            "events": [],
            "envelopes": [],
            "ai_mode": "vllm",
            "ai_confidence": 0.87,
            "ai_reason": "vLLM selected traffic_jam",
            "ai_actions": ["traffic_jam"],
        }
    )

    assert response.ai_mode == "vllm"
    assert response.ai_confidence == 0.87
    assert response.ai_actions == ["traffic_jam"]

    with pytest.raises(ValidationError):
        GodCommandResponse.model_validate(
            response.model_dump(mode="json") | {"ai_mode": "unbounded"}
        )



def test_voice_command_contracts_validate() -> None:
    request = VoiceCommandRequest.model_validate(
        {
            "kind": "voice_command",
            "audio_blob_b64": "UklGRg==",
            "mime_type": "audio/webm",
            "user_id": "presenter",
            "fallback_transcript": "도시에 비를 내려줘",
            "language": "ko",
        }
    )
    response = VoiceCommandResponse.model_validate(
        {
            "transcript": "도시에 비를 내려줘",
            "stt_mode": "fallback",
            "stt_status": "fallback",
            "detail": "typed fallback",
            "command": {
                "accepted": True,
                "command_id": "cmd_voice",
                "category": "environment",
                "event": {
                    "kind": "weather_changed",
                    "message": "Weather changed to rain",
                    "metadata": {"weather": "rain"},
                },
                "envelope": {
                    "v": 1,
                    "type": "event",
                    "ts": 1,
                    "tick": 0,
                    "payload": {"kind": "weather_changed"},
                },
                "events": [],
                "envelopes": [],
                "ai_mode": "rules",
                "ai_confidence": None,
                "ai_reason": None,
                "ai_actions": [],
            },
        }
    )

    assert request.language == "ko"
    assert response.command.event.kind == "weather_changed"

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
            "mode": "real",
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
    assert frame.mode == "real"
    assert frame.width == 320
    assert trip.path[-1] == [4, 0, 4]


def test_learning_status_contract_validates() -> None:
    snapshot = LearningSnapshot.model_validate(
        {
            "storage": "json_persistence",
            "experience_count": 4,
            "adaptation_epoch": 1,
            "policy_version": "adaptive-demo-v1",
            "traffic_bias": 0.24,
            "taxi_success_rate": 0.62,
            "citizen_memory_count": 3,
            "weather_bias": 0.08,
            "last_updated_tick": 44,
            "insights": ["교통량 증가 패턴 학습"],
        }
    )
    status = LearningStatusResponse.model_validate(
        {
            "learning": snapshot.model_dump(mode="json"),
            "explanation": "deterministic online adaptation",
            "upgrade_path": ["PPO checkpoint"],
        }
    )

    assert status.learning.policy_version == "adaptive-demo-v1"
    assert status.learning.traffic_bias == 0.24


def test_traffic_ai_snapshot_contract_validates() -> None:
    snapshot = TrafficAiSnapshot.model_validate(
        {
            "mode": "checkpoint",
            "policy_version": "traffic-gpu-linear-v1",
            "checkpoint_loaded": True,
            "trained_on_gpu": True,
            "training_backend": "torch_cuda",
            "episodes": 240,
            "improvement_pct": 28.4,
            "avg_queue_fixed_cycle": 20.5,
            "avg_queue_candidate": 14.7,
            "last_action": 1,
            "detail": "RunPod CUDA-trained linear traffic policy",
        }
    )

    assert snapshot.mode == "checkpoint"
    assert snapshot.trained_on_gpu is True
    assert snapshot.last_action == 1


def test_traffic_forecast_ai_snapshot_contract_validates() -> None:
    snapshot = TrafficForecastAiSnapshot.model_validate(
        {
            "mode": "lstm_checkpoint",
            "forecast_version": "traffic-lstm-v1",
            "checkpoint_loaded": True,
            "trained_on_gpu": True,
            "training_backend": "torch_cuda",
            "sequence_length": 12,
            "horizon_minutes": [5, 10, 15],
            "mape": 7.4,
            "training_loss": 0.01,
            "detail": "RunPod CUDA-trained LSTM traffic forecast",
        }
    )

    assert snapshot.mode == "lstm_checkpoint"
    assert snapshot.trained_on_gpu is True
    assert snapshot.horizon_minutes == [5, 10, 15]
