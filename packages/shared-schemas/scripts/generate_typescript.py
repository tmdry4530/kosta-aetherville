#!/usr/bin/env python3
"""Generate the minimal TypeScript contract surface from the Pydantic source models.

This generator is intentionally simple for M0: Pydantic remains the source of
truth, and this file emits type aliases/interfaces that mirror the current
contracts. Phase 03 can replace it with a JSON Schema/Zod generator without
changing client imports.
"""

from __future__ import annotations

from pathlib import Path

OUTPUT = Path(__file__).resolve().parents[1] / "src" / "typescript" / "index.ts"

CONTENT = """// GENERATED FILE. Do not edit by hand.
// Source of truth: src/python/aetherville_schemas/models.py

export type Vec3 = [number, number, number];
export type BBox = [number, number, number, number];

export type EnvelopeType =
  | 'state_update'
  | 'state_diff'
  | 'event'
  | 'command'
  | 'ack'
  | 'error';

export interface Envelope<TPayload = unknown> {
  v: 1;
  type: EnvelopeType;
  ts: number;
  tick: number;
  payload: TPayload;
}

export interface WorldClock {
  time_of_day: string;
  weather: string;
  temperature: number;
  active_event?: string | null;
  infrastructure_status?: string | null;
}

export interface YoloDetection {
  label: string;
  confidence: number;
  bbox: BBox;
  traffic_light_state?: 'red' | 'yellow' | 'green' | 'unknown' | null;
  distance_m?: number | null;
}

export interface VisionDetectRequest {
  frame_b64?: string | null;
  camera_id: string;
  metadata: Record<string, unknown>;
}

export interface VisionDetectResponse {
  mode: 'mock' | 'real';
  detections: YoloDetection[];
}

export interface VehicleCameraFrame {
  vehicle_id: string;
  mode: 'mock' | 'real';
  frame_b64?: string | null;
  width: number;
  height: number;
  detections: YoloDetection[];
}

export interface CitizenState {
  id: string;
  name: string;
  pos: Vec3;
  rot: Vec3;
  anim: string;
  current_action: string;
  talking_to?: string | null;
  display_tags: string[];
}

export interface CitizenPersona {
  id: string;
  name: string;
  age: number;
  occupation: string;
  traits: string[];
  home_district: string;
  daily_goal: string;
}

export interface MemoryRecord {
  id: string;
  citizen_id: string;
  text: string;
  created_tick: number;
  importance: number;
  tags: string[];
  retrieval_score?: number | null;
}

export interface PlanNode {
  id: string;
  title: string;
  status: 'pending' | 'active' | 'done';
  children: PlanNode[];
}

export interface CitizenListResponse {
  citizens: CitizenPersona[];
}

export interface CitizenDetailResponse {
  persona: CitizenPersona;
  plan_tree: PlanNode;
  memories: MemoryRecord[];
}

export interface MemoryStreamResponse {
  citizen_id: string;
  memories: MemoryRecord[];
}

export interface ReflectionResponse {
  citizen_id: string;
  reflection: string;
  event: EventPayload;
  envelope: Envelope;
}

export interface DialogueRequest {
  target_citizen_id?: string | null;
  topic: string;
}

export interface DialogueResponse {
  citizen_id: string;
  target_citizen_id: string;
  events: EventPayload[];
  envelopes: Envelope[];
}

export interface VehicleState {
  id: string;
  type: string;
  pos: Vec3;
  rot: Vec3;
  speed: number;
  passenger_id?: string | null;
  destination?: Vec3 | null;
  yolo_detections: YoloDetection[];
  display_tags: string[];
}

export interface TripState {
  id: string;
  passenger_id?: string | null;
  vehicle_id: string;
  origin: Vec3;
  destination: Vec3;
  status: 'requested' | 'assigned' | 'enroute' | 'completed' | 'cancelled';
  path: Vec3[];
}

export interface DroneState {
  id: string;
  pos: Vec3;
  destination?: Vec3 | null;
  cargo?: string | null;
  battery: number;
}

export interface TrafficLightState {
  id: string;
  pos: Vec3;
  state: 'red' | 'yellow' | 'green';
  remaining_sec: number;
  display_tags: string[];
}

export interface TrafficForecastPoint {
  minute_offset: number;
  expected_vehicle_count: number;
  congestion_index: number;
}

export interface TrafficAiSnapshot {
  mode: 'fixed_cycle' | 'pressure_baseline' | 'checkpoint';
  policy_version: string;
  checkpoint_loaded: boolean;
  trained_on_gpu: boolean;
  training_backend: 'none' | 'torch_cuda' | 'torch_cpu' | 'json';
  episodes: number;
  improvement_pct: number;
  avg_queue_fixed_cycle?: number | null;
  avg_queue_candidate?: number | null;
  last_action?: 0 | 1 | null;
  detail: string;
}

export interface TrafficForecastAiSnapshot {
  mode: 'deterministic_fallback' | 'lstm_checkpoint';
  forecast_version: string;
  checkpoint_loaded: boolean;
  trained_on_gpu: boolean;
  training_backend: 'none' | 'torch_cuda' | 'torch_cpu' | 'json';
  sequence_length: number;
  horizon_minutes: number[];
  mape?: number | null;
  training_loss?: number | null;
  detail: string;
}

export interface LearningSnapshot {
  mode: 'deterministic_online_adaptation';
  storage: 'json_persistence' | 'memory';
  experience_count: number;
  adaptation_epoch: number;
  policy_version: string;
  traffic_bias: number;
  taxi_success_rate: number;
  citizen_memory_count: number;
  weather_bias: number;
  last_updated_tick: number;
  insights: string[];
}

export interface LearningStatusResponse {
  learning: LearningSnapshot;
  explanation: string;
  upgrade_path: string[];
}

export interface WorldStatePayload {
  world: WorldClock;
  citizens: CitizenState[];
  vehicles: VehicleState[];
  drones: DroneState[];
  traffic_lights: TrafficLightState[];
  traffic_forecast: TrafficForecastPoint[];
  traffic_ai: TrafficAiSnapshot;
  traffic_forecast_ai: TrafficForecastAiSnapshot;
  learning: LearningSnapshot;
}

export interface GodCommand {
  kind: 'god_command';
  input_modality: 'voice' | 'text';
  raw_text: string;
  audio_blob_b64?: string | null;
  user_id: string;
}

export interface SelectEntityCommand {
  kind: 'select_entity';
  entity_type: 'citizen' | 'vehicle' | 'drone';
  entity_id: string;
}

export interface SimControlCommand {
  kind: 'sim_control';
  action: 'pause' | 'resume' | 'set_speed' | 'reset';
  speed_multiplier?: number | null;
}

export type CommandPayload = GodCommand | SelectEntityCommand | SimControlCommand;

export interface EventPayload {
  kind:
    | 'dialog_started'
    | 'dialog_ended'
    | 'dialog_chunk'
    | 'memory_added'
    | 'reflection_generated'
    | 'trip_requested'
    | 'trip_completed'
    | 'collision_avoided'
    | 'god_command_executed'
    | 'weather_changed'
    | 'event_injected'
    | 'person_updated'
    | 'infrastructure_changed'
    | 'relationship_changed';
  message: string;
  entity_id?: string | null;
  metadata: Record<string, unknown>;
}

export interface AckPayload {
  ok: boolean;
  message: string;
  correlation_id?: string | null;
}

export interface ErrorPayload {
  code: string;
  message: string;
  retryable: boolean;
}

export interface SimStatusResponse {
  tick: number;
  running: boolean;
  speed_multiplier: number;
  time_of_day: string;
  citizen_count: number;
  vehicle_count: number;
  traffic_light_count: number;
}

export interface SimResetRequest {
  seed?: number | null;
}

export interface GodCommandResponse {
  accepted: boolean;
  command_id: string;
  category: 'environment' | 'event' | 'person' | 'infrastructure' | 'relationship';
  event: EventPayload;
  envelope: Envelope;
  events: EventPayload[];
  envelopes: Envelope[];
  ai_mode: 'rules' | 'vllm';
  ai_confidence?: number | null;
  ai_reason?: string | null;
}

export interface ServiceStatus {
  name: string;
  status: 'ok' | 'degraded' | 'down' | 'missing' | 'stub';
  detail?: string | null;
}

export interface HealthResponse {
  service: string;
  status: 'ok' | 'degraded' | 'down';
  version: string;
  dependencies: ServiceStatus[];
}
"""


def main() -> None:
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(CONTENT, encoding="utf-8")
    print(f"generated {OUTPUT}")


if __name__ == "__main__":
    main()
