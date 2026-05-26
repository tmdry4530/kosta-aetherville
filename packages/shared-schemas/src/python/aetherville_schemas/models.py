"""Pydantic source-of-truth schemas for REST and WebSocket contracts."""

from __future__ import annotations

import time
from enum import StrEnum
from typing import Annotated, Any, Literal, TypeAlias

from pydantic import BaseModel, ConfigDict, Field

Vec3: TypeAlias = Annotated[list[float], Field(min_length=3, max_length=3)]
BBox: TypeAlias = Annotated[list[float], Field(min_length=4, max_length=4)]


class StrictModel(BaseModel):
    """Base model that rejects schema drift in fixtures and service payloads."""

    model_config = ConfigDict(extra="forbid")


class EnvelopeType(StrEnum):
    STATE_UPDATE = "state_update"
    STATE_DIFF = "state_diff"
    EVENT = "event"
    COMMAND = "command"
    ACK = "ack"
    ERROR = "error"


class Envelope(StrictModel):
    v: Literal[1] = 1
    type: EnvelopeType
    ts: float = Field(default_factory=time.time, ge=0)
    tick: int = Field(ge=0)
    payload: dict[str, Any] = Field(default_factory=dict)


class WorldClock(StrictModel):
    time_of_day: str = Field(pattern=r"^\d{2}:\d{2}$")
    weather: str
    temperature: float
    active_event: str | None = None
    infrastructure_status: str | None = None


class YoloDetection(StrictModel):
    label: str
    confidence: float = Field(ge=0, le=1)
    bbox: BBox
    traffic_light_state: Literal["red", "yellow", "green", "unknown"] | None = None
    distance_m: float | None = Field(default=None, ge=0)


class VisionDetectRequest(StrictModel):
    frame_b64: str | None = None
    camera_id: str = "mock-camera"
    metadata: dict[str, Any] = Field(default_factory=dict)


class VisionDetectResponse(StrictModel):
    mode: Literal["mock", "real"] = "mock"
    detections: list[YoloDetection]


class VehicleCameraFrame(StrictModel):
    vehicle_id: str
    mode: Literal["mock", "real"] = "mock"
    frame_b64: str | None = None
    width: int = Field(gt=0)
    height: int = Field(gt=0)
    detections: list[YoloDetection] = Field(default_factory=list)


class CitizenState(StrictModel):
    id: str
    name: str
    pos: Vec3
    rot: Vec3 = Field(default_factory=lambda: [0.0, 0.0, 0.0])
    anim: str = "idle"
    current_action: str = "observing"
    talking_to: str | None = None
    display_tags: list[str] = Field(default_factory=list)


class CitizenPersona(StrictModel):
    id: str
    name: str
    age: int = Field(ge=0)
    occupation: str
    traits: list[str] = Field(default_factory=list)
    home_district: str
    daily_goal: str


class MemoryRecord(StrictModel):
    id: str
    citizen_id: str
    text: str
    created_tick: int = Field(ge=0)
    importance: float = Field(ge=0, le=1)
    tags: list[str] = Field(default_factory=list)
    retrieval_score: float | None = Field(default=None, ge=0)


class PlanNode(StrictModel):
    id: str
    title: str
    status: Literal["pending", "active", "done"] = "pending"
    children: list[PlanNode] = Field(default_factory=list)


class CitizenListResponse(StrictModel):
    citizens: list[CitizenPersona]


class CitizenDetailResponse(StrictModel):
    persona: CitizenPersona
    plan_tree: PlanNode
    memories: list[MemoryRecord] = Field(default_factory=list)


class MemoryStreamResponse(StrictModel):
    citizen_id: str
    memories: list[MemoryRecord]


class ReflectionResponse(StrictModel):
    citizen_id: str
    reflection: str
    event: EventPayload
    envelope: Envelope


class DialogueRequest(StrictModel):
    target_citizen_id: str | None = None
    topic: str = "daily life"


class DialogueResponse(StrictModel):
    citizen_id: str
    target_citizen_id: str
    events: list[EventPayload]
    envelopes: list[Envelope]


class VehicleState(StrictModel):
    id: str
    type: str
    pos: Vec3
    rot: Vec3 = Field(default_factory=lambda: [0.0, 0.0, 0.0])
    speed: float = Field(ge=0)
    passenger_id: str | None = None
    destination: Vec3 | None = None
    yolo_detections: list[YoloDetection] = Field(default_factory=list)
    display_tags: list[str] = Field(default_factory=list)


class TripState(StrictModel):
    id: str
    passenger_id: str | None = None
    vehicle_id: str
    origin: Vec3
    destination: Vec3
    status: Literal["requested", "assigned", "enroute", "completed", "cancelled"]
    path: list[Vec3] = Field(default_factory=list)


class DroneState(StrictModel):
    id: str
    pos: Vec3
    destination: Vec3 | None = None
    cargo: str | None = None
    battery: float = Field(ge=0, le=1)


class TrafficLightState(StrictModel):
    id: str
    pos: Vec3
    state: Literal["red", "yellow", "green"]
    remaining_sec: float = Field(ge=0)
    display_tags: list[str] = Field(default_factory=list)


class TrafficForecastPoint(StrictModel):
    minute_offset: int = Field(ge=0)
    expected_vehicle_count: int = Field(ge=0)
    congestion_index: float = Field(ge=0, le=1)


class TrafficAiSnapshot(StrictModel):
    mode: Literal["fixed_cycle", "pressure_baseline", "checkpoint"] = "fixed_cycle"
    policy_version: str = "fixed-cycle-v0"
    checkpoint_loaded: bool = False
    trained_on_gpu: bool = False
    training_backend: Literal["none", "torch_cuda", "torch_cpu", "json"] = "none"
    episodes: int = Field(default=0, ge=0)
    improvement_pct: float = 0.0
    avg_queue_fixed_cycle: float | None = Field(default=None, ge=0)
    avg_queue_candidate: float | None = Field(default=None, ge=0)
    last_action: Literal[0, 1] | None = None
    detail: str = "fixed cycle baseline"


class TrafficForecastAiSnapshot(StrictModel):
    mode: Literal["deterministic_fallback", "lstm_checkpoint"] = "deterministic_fallback"
    forecast_version: str = "deterministic-forecast-v0"
    checkpoint_loaded: bool = False
    trained_on_gpu: bool = False
    training_backend: Literal["none", "torch_cuda", "torch_cpu", "json"] = "none"
    sequence_length: int = Field(default=0, ge=0)
    horizon_minutes: list[int] = Field(default_factory=list)
    mape: float | None = Field(default=None, ge=0)
    training_loss: float | None = Field(default=None, ge=0)
    detail: str = "deterministic forecast fallback"


class TrajectoryEvent(StrictModel):
    id: str
    tick: int = Field(ge=0)
    event_kind: str
    entity_id: str | None = None
    action: str | None = None
    summary: str


class TaskOutcomeScore(StrictModel):
    id: str
    task_id: str
    success: bool
    duration_ticks: int = Field(default=0, ge=0)
    replan_count: int = Field(default=0, ge=0)
    score: float = Field(default=0.0, ge=0, le=1)
    reason: str


class LearningSignal(StrictModel):
    id: str
    tick: int = Field(ge=0)
    kind: Literal[
        "scenario_success",
        "scenario_failure",
        "task_duration",
        "replan_count",
        "taxi_pickup",
        "weather_delay",
        "traffic_delay",
        "citizen_meeting",
        "actor_memory",
        "fallback_path",
        "policy_candidate",
        "policy_promoted",
        "policy_rejected",
    ]
    value: float = 0.0
    entity_id: str | None = None
    description: str


class PolicyBiasSnapshot(StrictModel):
    taxi_caution: float = Field(default=0.0, ge=0, le=1)
    walking_bias: float = Field(default=0.0, ge=0, le=1)
    traffic_caution: float = Field(default=0.0, ge=0, le=1)
    rain_delay_expectation: float = Field(default=0.0, ge=0, le=1)
    drone_caution: float = Field(default=0.0, ge=0, le=1)
    safer_timeout_bias: float = Field(default=0.0, ge=0, le=1)


class EvolutionSnapshot(StrictModel):
    version: str = "evolution-v0"
    storage: Literal["json_persistence", "memory"] = "memory"
    persistence_path: str | None = None
    scenario_success_count: int = Field(default=0, ge=0)
    scenario_failure_count: int = Field(default=0, ge=0)
    replan_count: int = Field(default=0, ge=0)
    fallback_path_usage: int = Field(default=0, ge=0)
    taxi_pickup_success_rate: float = Field(default=0.5, ge=0, le=1)
    weather_delay_impact: float = Field(default=0.0, ge=0, le=1)
    traffic_delay_impact: float = Field(default=0.0, ge=0, le=1)
    citizen_meeting_success_count: int = Field(default=0, ge=0)
    repeated_actor_memory_count: int = Field(default=0, ge=0)
    last_signal: str | None = None


class PolicyCandidateSnapshot(StrictModel):
    id: str
    tick: int = Field(ge=0)
    candidate_version: str
    source_signal: str
    score_before: float = Field(ge=0, le=1)
    score_after: float = Field(ge=0, le=1)
    promoted: bool = False
    reason: str


class PolicyPromotionSnapshot(StrictModel):
    active_policy_version: str = "adaptive-demo-v0"
    evaluator: str = "deterministic_reward_gate"
    candidate_count: int = Field(default=0, ge=0)
    promoted_count: int = Field(default=0, ge=0)
    rejected_count: int = Field(default=0, ge=0)
    last_decision: Literal["none", "promoted", "rejected"] = "none"
    last_promoted_version: str | None = None
    rollback_available: bool = False




TrainingTarget: TypeAlias = Literal["vllm_lora", "yolo", "traffic_ppo", "traffic_lstm"]
TrainingJobStatus: TypeAlias = Literal[
    "queued",
    "dataset_ready",
    "training_skipped",
    "training",
    "trained",
    "evaluated",
    "promoted",
    "rejected",
    "failed",
    "dry_run",
]
CheckpointStatus: TypeAlias = Literal[
    "candidate",
    "promoted",
    "rejected",
    "rolled_back",
    "rollback_candidate",
]
RuntimeReloadStatus: TypeAlias = Literal[
    "hot_swapped",
    "registered",
    "restart_required",
    "skipped",
    "failed",
]


class TrainingDatasetArtifact(StrictModel):
    id: str
    target: TrainingTarget
    path: str
    record_count: int = Field(ge=0)
    format: str
    created_ts: float = Field(ge=0)
    source_experience_count: int = Field(default=0, ge=0)


class CheckpointArtifact(StrictModel):
    id: str
    target: TrainingTarget
    version: str
    path: str
    status: CheckpointStatus = "candidate"
    metrics: dict[str, float] = Field(default_factory=dict)
    created_ts: float = Field(ge=0)
    promoted_ts: float | None = Field(default=None, ge=0)
    trainer_backend: str = "unknown"
    detail: str


class EvaluationGateSnapshot(StrictModel):
    target: TrainingTarget
    metric: str
    threshold: float
    comparator: Literal["gte", "lte"]
    candidate_value: float | None = None
    passed: bool = False
    reason: str


class TrainingJobSnapshot(StrictModel):
    id: str
    target: TrainingTarget
    status: TrainingJobStatus
    dry_run: bool = True
    dataset: TrainingDatasetArtifact | None = None
    checkpoint: CheckpointArtifact | None = None
    evaluation: EvaluationGateSnapshot | None = None
    started_ts: float = Field(ge=0)
    completed_ts: float | None = Field(default=None, ge=0)
    detail: str
    command: list[str] = Field(default_factory=list)


class ModelTrainingSnapshot(StrictModel):
    mode: Literal["not_configured", "dry_run", "ready", "training", "promoted", "blocked"] = (
        "not_configured"
    )
    approval_required: bool = True
    approval_env: str = "AETHERVILLE_APPROVE_MODEL_TRAINING"
    experience_log_path: str | None = None
    registry_path: str | None = None
    dataset_count: int = Field(default=0, ge=0)
    checkpoint_count: int = Field(default=0, ge=0)
    promoted_count: int = Field(default=0, ge=0)
    rollback_available: bool = False
    targets: list[TrainingTarget] = Field(default_factory=list)
    jobs: list[TrainingJobSnapshot] = Field(default_factory=list)
    last_cycle_id: str | None = None
    reload_count: int = Field(default=0, ge=0)
    last_reload_ts: float | None = Field(default=None, ge=0)


class TrainingCycleRequest(StrictModel):
    dry_run: bool = True
    targets: list[TrainingTarget] = Field(default_factory=list)
    force: bool = False


class TrainingCycleResponse(StrictModel):
    accepted: bool
    cycle_id: str
    status: Literal["dry_run", "promoted", "rejected", "blocked", "skipped"]
    jobs: list[TrainingJobSnapshot] = Field(default_factory=list)
    training: ModelTrainingSnapshot
    message: str


class TrainingRollbackRequest(StrictModel):
    target: TrainingTarget
    reason: str = "manual rollback"


class TrainingRollbackResponse(StrictModel):
    accepted: bool
    target: TrainingTarget
    rolled_back_to: str | None = None
    training: ModelTrainingSnapshot
    message: str


class RuntimeReloadTargetSnapshot(StrictModel):
    target: TrainingTarget
    status: RuntimeReloadStatus
    checkpoint_version: str | None = None
    checkpoint_path: str | None = None
    verified: bool = False
    detail: str


class RuntimeReloadRequest(StrictModel):
    targets: list[TrainingTarget] = Field(default_factory=list)
    checkpoint_path: str | None = None
    reason: str = "manual runtime reload"


class RuntimeReloadResponse(StrictModel):
    accepted: bool
    reload_id: str
    reloaded: list[RuntimeReloadTargetSnapshot] = Field(default_factory=list)
    training: ModelTrainingSnapshot | None = None
    message: str


class LearningSnapshot(StrictModel):
    mode: Literal["deterministic_online_adaptation"] = "deterministic_online_adaptation"
    storage: Literal["json_persistence", "memory"] = "memory"
    experience_count: int = Field(default=0, ge=0)
    adaptation_epoch: int = Field(default=0, ge=0)
    policy_version: str = "adaptive-demo-v0"
    traffic_bias: float = Field(default=0.0, ge=0, le=1)
    taxi_success_rate: float = Field(default=0.5, ge=0, le=1)
    citizen_memory_count: int = Field(default=0, ge=0)
    weather_bias: float = Field(default=0.0, ge=0, le=1)
    last_updated_tick: int = Field(default=0, ge=0)
    insights: list[str] = Field(default_factory=list)
    trajectory_events: list[TrajectoryEvent] = Field(default_factory=list)
    outcome_scores: list[TaskOutcomeScore] = Field(default_factory=list)
    signals: list[LearningSignal] = Field(default_factory=list)
    policy_bias: PolicyBiasSnapshot = Field(default_factory=PolicyBiasSnapshot)
    evolution: EvolutionSnapshot = Field(default_factory=EvolutionSnapshot)
    policy_candidates: list[PolicyCandidateSnapshot] = Field(default_factory=list)
    promotion_gate: PolicyPromotionSnapshot = Field(default_factory=PolicyPromotionSnapshot)
    model_training: ModelTrainingSnapshot = Field(default_factory=ModelTrainingSnapshot)


class LearningStatusResponse(StrictModel):
    learning: LearningSnapshot
    explanation: str
    upgrade_path: list[str] = Field(default_factory=list)


class CityActorContext(StrictModel):
    id: str
    kind: Literal["citizen", "vehicle", "drone", "traffic_light"]
    name: str | None = None
    pos: Vec3
    status: str
    tags: list[str] = Field(default_factory=list)


class CityTrafficContext(StrictModel):
    total_queue: int = Field(default=0, ge=0)
    congestion_active: bool = False
    policy_mode: str = "fixed_cycle"
    forecast_pressure: float = Field(default=0.0, ge=0, le=1)


class CityWorldContext(StrictModel):
    tick: int = Field(ge=0)
    time_of_day: str = Field(pattern=r"^\d{2}:\d{2}$")
    weather: str
    active_event: str | None = None
    infrastructure_status: str | None = None
    citizens: list[CityActorContext] = Field(default_factory=list)
    vehicles: list[CityActorContext] = Field(default_factory=list)
    traffic: CityTrafficContext = Field(default_factory=CityTrafficContext)
    recent_events: list[str] = Field(default_factory=list)
    learning: LearningSnapshot = Field(default_factory=LearningSnapshot)


class CityAiAction(StrictModel):
    type: Literal[
        "move_citizen",
        "call_taxi",
        "meet",
        "remember",
        "traffic_surge",
        "set_weather",
        "no_op",
    ]
    actor_id: str | None = None
    target_id: str | None = None
    vehicle_id: str | None = None
    destination_actor_id: str | None = None
    destination: Vec3 | None = None
    weather: Literal["clear", "rain", "snow"] | None = None
    memory: str | None = None
    label: str | None = None
    after: Literal["taxi_arrival"] | None = None
    reason: str = "city AI selected this action"


class CityAiPlan(StrictModel):
    plan_id: str
    source: Literal["rules", "vllm"] = "rules"
    confidence: float = Field(default=0.5, ge=0, le=1)
    summary: str
    actions: list[CityAiAction] = Field(default_factory=list)


class CityAiSnapshot(StrictModel):
    mode: Literal["disabled", "rules", "vllm"] = "disabled"
    status: Literal["idle", "planning", "applied", "fallback", "error"] = "idle"
    plan_id: str | None = None
    last_planned_tick: int = Field(default=0, ge=0)
    next_plan_tick: int = Field(default=0, ge=0)
    summary: str = "city AI planner disabled"
    actions: list[CityAiAction] = Field(default_factory=list)
    reason: str | None = None


class EntityGoal(StrictModel):
    id: str
    title: str
    target_id: str | None = None
    source: Literal["task_graph", "city_ai", "god_mode", "routine", "fallback"] = "routine"


class EntityConstraint(StrictModel):
    kind: Literal["deadline", "route", "weather", "traffic", "dependency", "battery", "safety"]
    description: str
    severity: Literal["info", "warning", "critical"] = "info"


class EntityProgress(StrictModel):
    progress_pct: float = Field(default=0.0, ge=0, le=1)
    current_step_id: str | None = None
    eta_ticks: int | None = Field(default=None, ge=0)


class EntityBlocker(StrictModel):
    blocker_type: Literal[
        "stuck_actor",
        "stuck_vehicle",
        "target_unreachable",
        "taxi_unavailable",
        "pickup_timeout",
        "group_timeout",
        "drone_delay",
        "low_battery",
        "traffic_delay",
        "dependency_deadlock",
        "none",
    ] = "none"
    reason: str | None = None
    replan_attempt: int = Field(default=0, ge=0)
    fallback_action: str | None = None


class EntityBrainState(StrictModel):
    entity_id: str
    entity_type: Literal["citizen", "vehicle", "taxi", "drone", "traffic_light"]
    current_goal: EntityGoal
    next_action: str
    reason: str
    source: Literal["task_graph", "city_ai", "god_mode", "routine", "fallback"] = "routine"
    progress: EntityProgress = Field(default_factory=EntityProgress)
    constraints: list[EntityConstraint] = Field(default_factory=list)
    blocker: EntityBlocker | None = None
    status: Literal[
        "idle",
        "planning",
        "moving",
        "waiting",
        "interacting",
        "blocked",
        "complete",
        "fallback",
    ] = "idle"
    blocked_reason: str | None = None
    updated_tick: int = Field(ge=0)


class ReplanRecord(StrictModel):
    id: str
    tick: int = Field(ge=0)
    task_node_id: str | None = None
    entity_id: str | None = None
    blocker_type: str
    reason: str
    attempt: int = Field(default=0, ge=0)
    fallback_action: str
    status: Literal["blocked", "replanned", "recovered"] = "blocked"



TaskActionType: TypeAlias = Literal[
    "move_actor_to_actor",
    "move_actor_to_location",
    "meet",
    "call_taxi",
    "taxi_pickup",
    "taxi_drive_to_actor",
    "drone_move_to_actor",
    "drone_deliver",
    "group_rendezvous",
    "set_weather",
    "traffic_surge",
    "remember",
    "wait",
    "no_op",
]
TaskStatus: TypeAlias = Literal[
    "pending",
    "running",
    "completed",
    "failed",
    "skipped",
    "rejected",
]
TaskGraphStatus: TypeAlias = Literal[
    "accepted",
    "clarification_needed",
    "rejected",
    "running",
    "completed",
    "failed",
]


class TaskCondition(StrictModel):
    kind: Literal[
        "entity_exists",
        "dependency_completed",
        "distance_less_than",
        "duration_elapsed",
        "weather_applied",
        "traffic_applied",
        "memory_recorded",
        "manual_review",
        "none",
    ] = "none"
    description: str
    entity_id: str | None = None
    target_id: str | None = None
    threshold: float | None = Field(default=None, ge=0)
    timeout_ticks: int | None = Field(default=None, ge=0)
    metadata: dict[str, Any] = Field(default_factory=dict)


class TaskEdge(StrictModel):
    from_node_id: str
    to_node_id: str
    relation: Literal["blocks", "enables", "after", "parallel"] = "enables"
    description: str = "dependency edge"


class TaskNode(StrictModel):
    id: str
    action_type: TaskActionType
    status: TaskStatus = "pending"
    actor_id: str | None = None
    actor_selector: str | None = None
    target_actor_id: str | None = None
    target_actor_ids: list[str] = Field(default_factory=list)
    target_entity_id: str | None = None
    target_selector: str | None = None
    vehicle_id: str | None = None
    drone_id: str | None = None
    location: Vec3 | None = None
    depends_on: list[str] = Field(default_factory=list)
    success_condition: TaskCondition
    failure_condition: TaskCondition
    timeout_ticks: int = Field(default=300, ge=0)
    retry_limit: int = Field(default=1, ge=0, le=5)
    reason: str
    visible_label: str
    metadata: dict[str, Any] = Field(default_factory=dict)


class TaskGraph(StrictModel):
    id: str
    raw_text: str
    title: str
    status: TaskGraphStatus = "accepted"
    nodes: list[TaskNode] = Field(default_factory=list)
    edges: list[TaskEdge] = Field(default_factory=list)
    actors: list[str] = Field(default_factory=list)
    assumptions: list[str] = Field(default_factory=list)
    rejection_reason: str | None = None
    summary: str


class TaskGraphPlan(StrictModel):
    plan_id: str
    source: Literal["rules", "vllm"] = "rules"
    confidence: float = Field(default=0.72, ge=0, le=1)
    graph: TaskGraph
    executor_step_ids: list[str] = Field(default_factory=list)
    created_tick: int = Field(ge=0)


class TaskGraphExecutionSnapshot(StrictModel):
    graph_id: str
    plan_id: str
    status: TaskGraphStatus
    current_node_id: str | None = None
    nodes: list[TaskNode] = Field(default_factory=list)
    completed_count: int = Field(default=0, ge=0)
    total_count: int = Field(default=0, ge=0)
    assumptions: list[str] = Field(default_factory=list)
    rejection_reason: str | None = None
    updated_tick: int = Field(ge=0)

class ScenarioStep(StrictModel):
    id: str
    type: Literal[
        "move_actor_to_actor",
        "move_actor_to_location",
        "meet",
        "call_taxi",
        "taxi_pickup",
        "taxi_drive_to_actor",
        "drone_move_to_actor",
        "drone_deliver",
        "move_actor_to_group",
        "group_rendezvous",
        "remember",
        "set_weather",
        "traffic_surge",
        "wait",
    ]
    status: Literal["pending", "running", "completed", "failed", "skipped"] = "pending"
    actor_id: str | None = None
    target_actor_id: str | None = None
    target_actor_ids: list[str] = Field(default_factory=list)
    vehicle_id: str | None = None
    drone_id: str | None = None
    depends_on: list[str] = Field(default_factory=list)
    started_tick: int | None = Field(default=None, ge=0)
    completed_tick: int | None = Field(default=None, ge=0)
    visible_label: str
    evidence: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class ScenarioDirective(StrictModel):
    id: str
    raw_text: str
    title: str
    status: Literal["idle", "running", "completed", "failed"] = "idle"
    created_tick: int = Field(ge=0)
    updated_tick: int = Field(ge=0)
    current_step_id: str | None = None
    actors: list[str] = Field(default_factory=list)
    steps: list[ScenarioStep] = Field(default_factory=list)
    summary: str


class WorldStatePayload(StrictModel):
    world: WorldClock
    citizens: list[CitizenState] = Field(default_factory=list)
    vehicles: list[VehicleState] = Field(default_factory=list)
    drones: list[DroneState] = Field(default_factory=list)
    traffic_lights: list[TrafficLightState] = Field(default_factory=list)
    traffic_forecast: list[TrafficForecastPoint] = Field(default_factory=list)
    traffic_ai: TrafficAiSnapshot = Field(default_factory=TrafficAiSnapshot)
    traffic_forecast_ai: TrafficForecastAiSnapshot = Field(
        default_factory=TrafficForecastAiSnapshot
    )
    learning: LearningSnapshot = Field(default_factory=LearningSnapshot)
    city_ai: CityAiSnapshot = Field(default_factory=CityAiSnapshot)
    scenario: ScenarioDirective | None = None
    task_graph: TaskGraphExecutionSnapshot | None = None
    entity_brains: list[EntityBrainState] = Field(default_factory=list)
    replans: list[ReplanRecord] = Field(default_factory=list)


class EventPayload(StrictModel):
    kind: Literal[
        "dialog_started",
        "dialog_ended",
        "dialog_chunk",
        "memory_added",
        "reflection_generated",
        "trip_requested",
        "trip_completed",
        "collision_avoided",
        "god_command_executed",
        "weather_changed",
        "event_injected",
        "city_ai_plan",
        "scenario_directive_created",
        "scenario_step_started",
        "scenario_step_completed",
        "scenario_completed",
        "task_graph_planned",
        "task_graph_rejected",
        "task_blocked",
        "task_replanned",
        "task_recovered",
        "learning_signal",
        "evolution_updated",
        "person_updated",
        "infrastructure_changed",
        "relationship_changed",
    ]
    message: str
    entity_id: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class GodCommand(StrictModel):
    kind: Literal["god_command"] = "god_command"
    input_modality: Literal["voice", "text"]
    raw_text: str = Field(min_length=1)
    audio_blob_b64: str | None = None
    user_id: str


class SelectEntityCommand(StrictModel):
    kind: Literal["select_entity"] = "select_entity"
    entity_type: Literal["citizen", "vehicle", "drone"]
    entity_id: str


class SimControlCommand(StrictModel):
    kind: Literal["sim_control"] = "sim_control"
    action: Literal["pause", "resume", "set_speed", "reset"]
    speed_multiplier: float | None = Field(default=None, gt=0)


CommandPayload: TypeAlias = GodCommand | SelectEntityCommand | SimControlCommand


class AckPayload(StrictModel):
    ok: bool = True
    message: str
    correlation_id: str | None = None


class ErrorPayload(StrictModel):
    code: str
    message: str
    retryable: bool = False


class SimStatusResponse(StrictModel):
    tick: int = Field(ge=0)
    running: bool
    speed_multiplier: float = Field(gt=0)
    time_of_day: str = Field(pattern=r"^\d{2}:\d{2}$")
    citizen_count: int = Field(ge=0)
    vehicle_count: int = Field(ge=0)
    traffic_light_count: int = Field(ge=0)


class SimResetRequest(StrictModel):
    seed: int | None = None


class VoiceCommandRequest(StrictModel):
    kind: Literal["voice_command"] = "voice_command"
    audio_blob_b64: str | None = None
    mime_type: str = "audio/webm"
    user_id: str = "presenter"
    fallback_transcript: str | None = None
    language: str | None = "ko"


class GodCommandResponse(StrictModel):
    accepted: bool
    command_id: str
    category: Literal["environment", "event", "person", "infrastructure", "relationship"]
    event: EventPayload
    envelope: Envelope
    events: list[EventPayload] = Field(default_factory=list)
    envelopes: list[Envelope] = Field(default_factory=list)
    ai_mode: Literal["rules", "vllm"] = "rules"
    ai_confidence: float | None = Field(default=None, ge=0, le=1)
    ai_reason: str | None = None
    ai_actions: list[str] = Field(default_factory=list)
    scenario: ScenarioDirective | None = None
    task_graph: TaskGraphPlan | None = None
    task_graph_rejection_reason: str | None = None


class VoiceCommandResponse(StrictModel):
    transcript: str
    stt_mode: Literal["stub", "faster_whisper", "fallback"]
    stt_status: Literal["ok", "fallback", "unavailable"]
    detail: str | None = None
    command: GodCommandResponse


class ServiceStatus(StrictModel):
    name: str
    status: Literal["ok", "degraded", "down", "missing", "stub"]
    detail: str | None = None


class HealthResponse(StrictModel):
    service: str
    status: Literal["ok", "degraded", "down"]
    version: str
    dependencies: list[ServiceStatus] = Field(default_factory=list)


def make_state_update(payload: WorldStatePayload, tick: int) -> Envelope:
    return Envelope(
        type=EnvelopeType.STATE_UPDATE,
        tick=tick,
        payload=payload.model_dump(mode="json"),
    )
