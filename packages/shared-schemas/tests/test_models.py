from __future__ import annotations

import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from aetherville_schemas import (
    CheckpointArtifact,
    CitizenDetailResponse,
    CityAiAction,
    CityAiPlan,
    CityAiSnapshot,
    CityWorldContext,
    EntityBlocker,
    EntityBrainState,
    EntityConstraint,
    EntityGoal,
    EntityProgress,
    Envelope,
    EnvelopeType,
    EvaluationGateSnapshot,
    EvolutionSnapshot,
    GodCommand,
    GodCommandResponse,
    HealthResponse,
    LearningSignal,
    LearningSnapshot,
    LearningStatusResponse,
    MemoryRecord,
    ModelTrainingSnapshot,
    PlanNode,
    ReplanRecord,
    RuntimeReloadRequest,
    RuntimeReloadResponse,
    RuntimeReloadTargetSnapshot,
    ScenarioDirective,
    ScenarioStep,
    TaskCondition,
    TaskGraph,
    TaskGraphExecutionSnapshot,
    TaskGraphPlan,
    TaskNode,
    TaskOutcomeScore,
    TrafficAiSnapshot,
    TrafficForecastAiSnapshot,
    TrainingCycleRequest,
    TrainingCycleResponse,
    TrainingDatasetArtifact,
    TrainingJobSnapshot,
    TrainingRollbackRequest,
    TrainingRollbackResponse,
    TrajectoryEvent,
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
    assert payload.city_ai.mode == "disabled"


def test_model_training_contract_validates_checkpoint_promotion_path() -> None:
    dataset = TrainingDatasetArtifact(
        id="dataset_test_vllm",
        target="vllm_lora",
        path="/tmp/aetherville/training/datasets/test.jsonl",
        record_count=12,
        format="chat_sft_jsonl",
        created_ts=1.0,
        source_experience_count=12,
    )
    checkpoint = CheckpointArtifact(
        id="checkpoint_test_vllm",
        target="vllm_lora",
        version="vllm_lora-test",
        path="/tmp/aetherville/training/checkpoints/test.json",
        status="candidate",
        metrics={"plan_validity": 0.72},
        created_ts=2.0,
        trainer_backend="dry_run_recipe",
        detail="candidate LoRA checkpoint",
    )
    evaluation = EvaluationGateSnapshot(
        target="vllm_lora",
        metric="plan_validity",
        threshold=0.6,
        comparator="gte",
        candidate_value=0.72,
        passed=True,
        reason="gate passed",
    )
    job = TrainingJobSnapshot(
        id="job_test_vllm",
        target="vllm_lora",
        status="dry_run",
        dry_run=True,
        dataset=dataset,
        checkpoint=checkpoint,
        evaluation=evaluation,
        started_ts=1.0,
        completed_ts=2.0,
        detail="dry-run verified",
        command=["python3", "scripts/train_vllm_lora.py", "--dry-run"],
    )
    snapshot = ModelTrainingSnapshot(
        mode="dry_run",
        experience_log_path="/tmp/aetherville/training/experience_log.jsonl",
        registry_path="/tmp/aetherville/training/checkpoints/registry.json",
        dataset_count=1,
        checkpoint_count=0,
        promoted_count=0,
        targets=["vllm_lora", "yolo", "traffic_ppo", "traffic_lstm"],
        jobs=[job],
        last_cycle_id="train_test",
    )
    response = TrainingCycleResponse(
        accepted=True,
        cycle_id="train_test",
        status="dry_run",
        jobs=[job],
        training=snapshot,
        message="training handoff verified",
    )
    rollback = TrainingRollbackResponse(
        accepted=False,
        target="vllm_lora",
        training=snapshot,
        message="rollback candidate is unavailable",
    )

    assert response.training.jobs[0].evaluation is not None
    assert response.training.jobs[0].evaluation.passed is True
    assert rollback.accepted is False
    assert TrainingCycleRequest(dry_run=True).targets == []
    assert TrainingRollbackRequest(target="traffic_ppo").reason == "manual rollback"
    reload_target = RuntimeReloadTargetSnapshot(
        target="traffic_ppo",
        status="hot_swapped",
        checkpoint_version="traffic-ppo-v1",
        checkpoint_path="/tmp/aetherville/training/checkpoints/traffic.json",
        verified=True,
        detail="traffic policy hot-swapped",
    )
    reload_response = RuntimeReloadResponse(
        accepted=True,
        reload_id="reload_test",
        reloaded=[reload_target],
        training=snapshot,
        message="runtime checkpoint reload completed",
    )
    assert reload_response.reloaded[0].verified is True
    assert RuntimeReloadRequest(targets=["yolo"]).reason == "manual runtime reload"

    with pytest.raises(ValidationError):
        TrainingDatasetArtifact.model_validate(dataset.model_dump() | {"target": "bad_target"})


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


def test_scenario_directive_contract_validates() -> None:
    step = ScenarioStep.model_validate(
        {
            "id": "taxi_drive_c02_to_c01",
            "type": "taxi_drive_to_actor",
            "status": "running",
            "actor_id": "c02",
            "target_actor_id": "c01",
            "target_actor_ids": [],
            "vehicle_id": "v01",
            "drone_id": None,
            "depends_on": ["taxi_call_c02_to_c01"],
            "started_tick": 42,
            "completed_tick": None,
            "visible_label": "택시가 민수를 민지에게 이동",
            "evidence": None,
            "metadata": {"target_xz": [1.0, -1.0]},
        }
    )
    scenario = ScenarioDirective.model_validate(
        {
            "id": "scenario_test",
            "raw_text": "민수가 택시로 민지에게 간다",
            "title": "택시·시민 연쇄 시나리오",
            "status": "running",
            "created_tick": 40,
            "updated_tick": 42,
            "current_step_id": step.id,
            "actors": ["c01", "c02"],
            "steps": [step.model_dump(mode="json")],
            "summary": "민수 택시 이동",
        }
    )

    response = GodCommandResponse.model_validate(
        {
            "accepted": True,
            "command_id": "cmd_scenario",
            "category": "event",
            "event": {
                "kind": "scenario_directive_created",
                "message": "Scenario directive created",
                "metadata": {"scenario_id": scenario.id},
            },
            "envelope": {
                "v": 1,
                "type": "event",
                "ts": 1,
                "tick": 40,
                "payload": {"kind": "scenario_directive_created"},
            },
            "events": [],
            "envelopes": [],
            "ai_mode": "rules",
            "ai_confidence": None,
            "ai_reason": "bounded scenario compiler",
            "ai_actions": ["scenario_directive", "taxi_drive_to_actor"],
            "scenario": scenario.model_dump(mode="json"),
        }
    )

    assert scenario.steps[0].type == "taxi_drive_to_actor"
    assert response.scenario is not None
    assert response.scenario.current_step_id == step.id

    with pytest.raises(ValidationError):
        ScenarioStep.model_validate(step.model_dump(mode="json") | {"type": "freeform"})


def test_task_graph_contract_validates_and_exposes_response_snapshot() -> None:
    node = TaskNode(
        id="c02_to_c01",
        action_type="move_actor_to_actor",
        actor_id="c02",
        target_actor_id="c01",
        success_condition=TaskCondition(
            kind="distance_less_than",
            description="민수가 민지 근처에 도착",
            entity_id="c02",
            target_id="c01",
            threshold=0.55,
            timeout_ticks=360,
        ),
        failure_condition=TaskCondition(
            kind="manual_review",
            description="도착하지 못하면 재계획 후보",
            entity_id="c02",
            target_id="c01",
            timeout_ticks=360,
        ),
        timeout_ticks=360,
        retry_limit=1,
        reason="민수를 민지에게 이동시켜 만남을 준비합니다.",
        visible_label="민수 → 민지 이동",
    )
    graph = TaskGraph(
        id="graph_test",
        raw_text="민수가 민지를 만난다",
        title="TaskGraph 시민 만남 시나리오",
        status="accepted",
        nodes=[node],
        edges=[],
        actors=["c01", "c02"],
        assumptions=[],
        summary="1개 task node",
    )
    plan = TaskGraphPlan(
        plan_id="plan_test",
        source="rules",
        confidence=0.86,
        graph=graph,
        executor_step_ids=[node.id],
        created_tick=7,
    )
    snapshot = TaskGraphExecutionSnapshot(
        graph_id=graph.id,
        plan_id=plan.plan_id,
        status="running",
        current_node_id=node.id,
        nodes=[node.model_copy(update={"status": "running"})],
        completed_count=0,
        total_count=1,
        updated_tick=8,
    )
    response = GodCommandResponse.model_validate(
        {
            "accepted": True,
            "command_id": "cmd_graph",
            "category": "event",
            "event": {
                "kind": "task_graph_planned",
                "message": "TaskGraph planned",
                "metadata": {"task_graph_id": graph.id},
            },
            "envelope": {
                "v": 1,
                "type": "event",
                "ts": 1,
                "tick": 7,
                "payload": {"kind": "task_graph_planned"},
            },
            "events": [],
            "envelopes": [],
            "task_graph": plan.model_dump(mode="json"),
        }
    )

    assert response.task_graph is not None
    assert response.task_graph.graph.nodes[0].action_type == "move_actor_to_actor"
    assert snapshot.current_node_id == node.id

    with pytest.raises(ValidationError):
        TaskNode.model_validate(node.model_dump(mode="json") | {"action_type": "teleport"})



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


def test_city_ai_contracts_validate() -> None:
    action = CityAiAction.model_validate(
        {
            "type": "call_taxi",
            "actor_id": "c06",
            "vehicle_id": "v01",
            "destination_actor_id": "c05",
            "reason": "지호가 하린을 만나러 가야 함",
        }
    )
    plan = CityAiPlan.model_validate(
        {
            "plan_id": "city_vllm_1",
            "source": "vllm",
            "confidence": 0.88,
            "summary": "지호 택시 이동",
            "actions": [action.model_dump(mode="json")],
        }
    )
    snapshot = CityAiSnapshot.model_validate(
        {
            "mode": "vllm",
            "status": "applied",
            "plan_id": plan.plan_id,
            "last_planned_tick": 120,
            "next_plan_tick": 240,
            "summary": plan.summary,
            "actions": [action.model_dump(mode="json")],
            "reason": "visible autonomous movement",
        }
    )
    context = CityWorldContext.model_validate(
        {
            "tick": 120,
            "time_of_day": "09:42",
            "weather": "clear",
            "citizens": [
                {
                    "id": "c06",
                    "kind": "citizen",
                    "name": "지호",
                    "pos": [0.0, 0.0, 0.0],
                    "status": "observing",
                    "tags": ["지호"],
                }
            ],
            "vehicles": [],
            "recent_events": [],
        }
    )

    assert snapshot.actions[0].type == "call_taxi"
    assert context.citizens[0].name == "지호"


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



def test_entity_brain_replan_and_evolution_contracts_validate() -> None:
    brain = EntityBrainState(
        entity_id="c02",
        entity_type="citizen",
        current_goal=EntityGoal(
            id="taxi_drive_c02_to_c01",
            title="민수가 민지에게 이동",
            target_id="c01",
            source="task_graph",
        ),
        next_action="taxi_drive_to_actor",
        reason="TaskGraph node is executing the taxi movement.",
        source="task_graph",
        progress=EntityProgress(progress_pct=0.62, current_step_id="taxi_drive_c02_to_c01"),
        constraints=[
            EntityConstraint(kind="traffic", description="traffic surge active", severity="warning")
        ],
        blocker=EntityBlocker(
            blocker_type="traffic_delay",
            reason="traffic exceeded deadline",
            replan_attempt=1,
            fallback_action="taxi_to_walking_safe_arrival",
        ),
        status="fallback",
        blocked_reason=None,
        updated_tick=44,
    )
    replan = ReplanRecord(
        id="replan_44_0001",
        tick=44,
        task_node_id="taxi_drive_c02_to_c01",
        entity_id="c02",
        blocker_type="traffic_delay",
        reason="traffic exceeded deadline",
        attempt=1,
        fallback_action="taxi_to_walking_safe_arrival",
        status="recovered",
    )
    learning = LearningSnapshot(
        experience_count=8,
        adaptation_epoch=2,
        policy_version="adaptive-demo-v2",
        traffic_bias=0.2,
        taxi_success_rate=0.7,
        citizen_memory_count=5,
        weather_bias=0.12,
        last_updated_tick=44,
        insights=["bounded fallback recovered a task"],
        trajectory_events=[
            TrajectoryEvent(
                id="traj_44_0001",
                tick=44,
                event_kind="task_recovered",
                entity_id="c02",
                action="task_recovered",
                summary="Recovered by bounded fallback",
            )
        ],
        outcome_scores=[
            TaskOutcomeScore(
                id="outcome_44_0001",
                task_id="taxi_drive_c02_to_c01",
                success=True,
                duration_ticks=44,
                replan_count=1,
                score=0.82,
                reason="Recovered with fallback",
            )
        ],
        signals=[
            LearningSignal(
                id="signal_44_0001",
                tick=44,
                kind="fallback_path",
                value=1.0,
                entity_id="c02",
                description="Fallback path selected",
            )
        ],
        evolution=EvolutionSnapshot(
            version="evolution-v2",
            storage="json_persistence",
            scenario_success_count=1,
            scenario_failure_count=1,
            replan_count=1,
            fallback_path_usage=1,
            taxi_pickup_success_rate=0.7,
            weather_delay_impact=0.12,
            traffic_delay_impact=0.2,
            citizen_meeting_success_count=1,
            repeated_actor_memory_count=5,
            last_signal="Fallback path selected",
        ),
    )

    payload = WorldStatePayload.model_validate(
        {
            "world": {"time_of_day": "09:34", "weather": "rain", "temperature": 20.0},
            "citizens": [],
            "vehicles": [],
            "drones": [],
            "traffic_lights": [],
            "traffic_forecast": [],
            "learning": learning.model_dump(mode="json"),
            "entity_brains": [brain.model_dump(mode="json")],
            "replans": [replan.model_dump(mode="json")],
        }
    )

    assert payload.entity_brains[0].current_goal.source == "task_graph"
    assert payload.replans[0].status == "recovered"
    assert payload.learning.evolution.version == "evolution-v2"
    assert payload.learning.signals[0].kind == "fallback_path"
