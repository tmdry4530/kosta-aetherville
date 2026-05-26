from __future__ import annotations

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from aetherville_schemas import (
    EventPayload,
    GodCommand,
    ModelTrainingSnapshot,
    RuntimeReloadResponse,
    TrainingCycleResponse,
)
from aetherville_server.learning import LearningStore
from aetherville_server.main import fastapi_app
from aetherville_server.sim import SimulationEngine


def make_command(text: str) -> GodCommand:
    return GodCommand(input_modality="text", raw_text=text, user_id="presenter")


def seed_training_experience(engine: SimulationEngine) -> None:
    for command in (
        "교통량 증가시켜",
        "민지가 택시를 불러줘",
        "도시에 비를 내려줘",
        "민수와 하린이 만나게 해줘",
        "택시 없음 상황에서 민수가 택시를 불러 민지에게 간다",
    ):
        engine.execute_god_command(make_command(command))


def test_learning_store_writes_experience_log_and_dry_run_training_cycle(tmp_path: Path) -> None:
    learning_path = tmp_path / "learning_state.json"
    engine = SimulationEngine(learning_store=LearningStore(learning_path))
    seed_training_experience(engine)

    training = engine.learning_status().learning.model_training
    assert training.experience_log_path is not None
    experience_log = Path(training.experience_log_path)
    assert experience_log.exists()
    first_record = json.loads(experience_log.read_text(encoding="utf-8").splitlines()[0])
    assert "vllm_lora" in first_record["targets"]
    assert "reward" in first_record

    response = engine.learning.training.run_cycle(dry_run=True)

    assert response.status == "dry_run"
    assert len(response.jobs) == 4
    assert all(job.status == "dry_run" for job in response.jobs)
    assert all(job.dataset and Path(job.dataset.path).exists() for job in response.jobs)
    assert all(job.checkpoint is not None for job in response.jobs)
    assert response.training.dataset_count >= 4
    assert response.training.checkpoint_count == 0
    assert response.training.approval_required is True


def test_yolo_dry_run_handles_entityless_experience_records(tmp_path: Path) -> None:
    learning_path = tmp_path / "learning_state.json"
    store = LearningStore(learning_path)
    store.training.append_experience(
        EventPayload(
            kind="weather_changed",
            message="비가 내리기 시작했습니다.",
            entity_id=None,
            metadata={"weather": "rain"},
        ),
        tick=7,
        learning={"reward_score": 0.6},
    )

    response = store.training.run_cycle(dry_run=True, targets=["yolo"], force=True)

    assert response.status == "dry_run"
    assert response.jobs[0].status == "dry_run"
    assert response.jobs[0].dataset is not None
    rows = [
        json.loads(line)
        for line in Path(response.jobs[0].dataset.path).read_text(encoding="utf-8").splitlines()
    ]
    assert rows[0]["pseudo_labels"][0]["label"] == "vehicle"

def test_real_training_cycle_is_blocked_without_explicit_approval(tmp_path: Path) -> None:
    engine = SimulationEngine(learning_store=LearningStore(tmp_path / "learning_state.json"))
    seed_training_experience(engine)

    response = engine.learning.training.run_cycle(dry_run=False, targets=["vllm_lora"])

    assert response.status == "blocked"
    assert response.jobs[0].status == "failed"
    assert "AETHERVILLE_APPROVE_MODEL_TRAINING" in response.jobs[0].detail


def test_training_status_and_cycle_endpoints_use_shared_contract() -> None:
    client = TestClient(fastapi_app)
    client.post(
        "/api/v1/god/command",
        json={
            "kind": "god_command",
            "input_modality": "text",
            "raw_text": "교통량 증가시켜",
            "audio_blob_b64": None,
            "user_id": "presenter",
        },
    )

    status = client.get("/api/v1/training/status")
    assert status.status_code == 200
    snapshot = ModelTrainingSnapshot.model_validate(status.json())
    assert "vllm_lora" in snapshot.targets

    cycle = client.post(
        "/api/v1/training/cycle",
        json={"dry_run": True, "targets": ["vllm_lora", "traffic_ppo"], "force": True},
    )
    assert cycle.status_code == 200
    parsed = TrainingCycleResponse.model_validate(cycle.json())
    assert parsed.status == "dry_run"
    assert [job.target for job in parsed.jobs] == ["vllm_lora", "traffic_ppo"]


def test_training_rollback_reports_missing_candidate() -> None:
    client = TestClient(fastapi_app)
    response = client.post(
        "/api/v1/training/rollback",
        json={"target": "vllm_lora", "reason": "test rollback"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["accepted"] is False
    assert body["rolled_back_to"] is None


def test_execute_training_promotes_traffic_and_runtime_reload(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("AETHERVILLE_APPROVE_MODEL_TRAINING", "1")
    engine = SimulationEngine(learning_store=LearningStore(tmp_path / "learning_state.json"))
    seed_training_experience(engine)

    response = engine.learning.training.run_cycle(
        dry_run=False,
        targets=["traffic_ppo", "traffic_lstm"],
        force=True,
    )

    assert response.status == "promoted"
    assert [job.status for job in response.jobs] == ["promoted", "promoted"]
    assert all(job.checkpoint and Path(job.checkpoint.path).exists() for job in response.jobs)

    checkpoints = engine.learning.training.promoted_checkpoints(
        targets=["traffic_ppo", "traffic_lstm"]
    )
    reloads = engine.reload_training_checkpoints(checkpoints)

    assert {result.target for result in reloads} == {"traffic_ppo", "traffic_lstm"}
    assert all(result.status == "hot_swapped" and result.verified for result in reloads)
    state = engine.snapshot()
    assert state.traffic_ai.checkpoint_loaded is True
    assert state.traffic_forecast_ai.checkpoint_loaded is True
    engine.learning.training.record_runtime_reload(
        reload_id="reload_test",
        results=reloads,
        reason="test",
    )
    assert engine.learning.training.snapshot().reload_count == 1


def test_runtime_reload_endpoint_reports_missing_promoted_checkpoint() -> None:
    client = TestClient(fastapi_app)

    response = client.post(
        "/api/v1/runtime/reload",
        json={"targets": ["traffic_ppo"], "reason": "test"},
    )

    assert response.status_code == 200
    parsed = RuntimeReloadResponse.model_validate(response.json())
    assert parsed.accepted is False
    assert parsed.reloaded[0].status == "skipped"
