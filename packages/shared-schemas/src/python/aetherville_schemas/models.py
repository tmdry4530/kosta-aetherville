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


class LearningStatusResponse(StrictModel):
    learning: LearningSnapshot
    explanation: str
    upgrade_path: list[str] = Field(default_factory=list)


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
