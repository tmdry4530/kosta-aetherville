// GENERATED FILE. Do not edit by hand.
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

export interface TrajectoryEvent {
  id: string;
  tick: number;
  event_kind: string;
  entity_id?: string | null;
  action?: string | null;
  summary: string;
}

export interface TaskOutcomeScore {
  id: string;
  task_id: string;
  success: boolean;
  duration_ticks: number;
  replan_count: number;
  score: number;
  reason: string;
}

export interface LearningSignal {
  id: string;
  tick: number;
  kind:
    | 'scenario_success'
    | 'scenario_failure'
    | 'task_duration'
    | 'replan_count'
    | 'taxi_pickup'
    | 'weather_delay'
    | 'traffic_delay'
    | 'citizen_meeting'
    | 'actor_memory'
    | 'fallback_path';
  value: number;
  entity_id?: string | null;
  description: string;
}

export interface PolicyBiasSnapshot {
  taxi_caution: number;
  walking_bias: number;
  traffic_caution: number;
  rain_delay_expectation: number;
  drone_caution: number;
  safer_timeout_bias: number;
}

export interface EvolutionSnapshot {
  version: string;
  storage: 'json_persistence' | 'memory';
  persistence_path?: string | null;
  scenario_success_count: number;
  scenario_failure_count: number;
  replan_count: number;
  fallback_path_usage: number;
  taxi_pickup_success_rate: number;
  weather_delay_impact: number;
  traffic_delay_impact: number;
  citizen_meeting_success_count: number;
  repeated_actor_memory_count: number;
  last_signal?: string | null;
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
  trajectory_events: TrajectoryEvent[];
  outcome_scores: TaskOutcomeScore[];
  signals: LearningSignal[];
  policy_bias: PolicyBiasSnapshot;
  evolution: EvolutionSnapshot;
}

export interface LearningStatusResponse {
  learning: LearningSnapshot;
  explanation: string;
  upgrade_path: string[];
}

export interface CityActorContext {
  id: string;
  kind: 'citizen' | 'vehicle' | 'drone' | 'traffic_light';
  name?: string | null;
  pos: Vec3;
  status: string;
  tags: string[];
}

export interface CityTrafficContext {
  total_queue: number;
  congestion_active: boolean;
  policy_mode: string;
  forecast_pressure: number;
}

export interface CityWorldContext {
  tick: number;
  time_of_day: string;
  weather: string;
  active_event?: string | null;
  infrastructure_status?: string | null;
  citizens: CityActorContext[];
  vehicles: CityActorContext[];
  traffic: CityTrafficContext;
  recent_events: string[];
  learning: LearningSnapshot;
}

export interface CityAiAction {
  type:
    | 'move_citizen'
    | 'call_taxi'
    | 'meet'
    | 'remember'
    | 'traffic_surge'
    | 'set_weather'
    | 'no_op';
  actor_id?: string | null;
  target_id?: string | null;
  vehicle_id?: string | null;
  destination_actor_id?: string | null;
  destination?: Vec3 | null;
  weather?: 'clear' | 'rain' | 'snow' | null;
  memory?: string | null;
  label?: string | null;
  after?: 'taxi_arrival' | null;
  reason: string;
}

export interface CityAiPlan {
  plan_id: string;
  source: 'rules' | 'vllm';
  confidence: number;
  summary: string;
  actions: CityAiAction[];
}

export interface CityAiSnapshot {
  mode: 'disabled' | 'rules' | 'vllm';
  status: 'idle' | 'planning' | 'applied' | 'fallback' | 'error';
  plan_id?: string | null;
  last_planned_tick: number;
  next_plan_tick: number;
  summary: string;
  actions: CityAiAction[];
  reason?: string | null;
}


export interface EntityGoal {
  id: string;
  title: string;
  target_id?: string | null;
  source: 'task_graph' | 'city_ai' | 'god_mode' | 'routine' | 'fallback';
}

export interface EntityConstraint {
  kind: 'deadline' | 'route' | 'weather' | 'traffic' | 'dependency' | 'battery' | 'safety';
  description: string;
  severity: 'info' | 'warning' | 'critical';
}

export interface EntityProgress {
  progress_pct: number;
  current_step_id?: string | null;
  eta_ticks?: number | null;
}

export interface EntityBlocker {
  blocker_type:
    | 'stuck_actor'
    | 'stuck_vehicle'
    | 'target_unreachable'
    | 'taxi_unavailable'
    | 'pickup_timeout'
    | 'group_timeout'
    | 'drone_delay'
    | 'low_battery'
    | 'traffic_delay'
    | 'dependency_deadlock'
    | 'none';
  reason?: string | null;
  replan_attempt: number;
  fallback_action?: string | null;
}

export interface EntityBrainState {
  entity_id: string;
  entity_type: 'citizen' | 'vehicle' | 'taxi' | 'drone' | 'traffic_light';
  current_goal: EntityGoal;
  next_action: string;
  reason: string;
  source: 'task_graph' | 'city_ai' | 'god_mode' | 'routine' | 'fallback';
  progress: EntityProgress;
  constraints: EntityConstraint[];
  blocker?: EntityBlocker | null;
  status:
    | 'idle'
    | 'planning'
    | 'moving'
    | 'waiting'
    | 'interacting'
    | 'blocked'
    | 'complete'
    | 'fallback';
  blocked_reason?: string | null;
  updated_tick: number;
}

export interface ReplanRecord {
  id: string;
  tick: number;
  task_node_id?: string | null;
  entity_id?: string | null;
  blocker_type: string;
  reason: string;
  attempt: number;
  fallback_action: string;
  status: 'blocked' | 'replanned' | 'recovered';
}

export type TaskActionType =
  | 'move_actor_to_actor'
  | 'move_actor_to_location'
  | 'meet'
  | 'call_taxi'
  | 'taxi_pickup'
  | 'taxi_drive_to_actor'
  | 'drone_move_to_actor'
  | 'drone_deliver'
  | 'group_rendezvous'
  | 'set_weather'
  | 'traffic_surge'
  | 'remember'
  | 'wait'
  | 'no_op';

export type TaskStatus = 'pending' | 'running' | 'completed' | 'failed' | 'skipped' | 'rejected';

export type TaskGraphStatus =
  | 'accepted'
  | 'clarification_needed'
  | 'rejected'
  | 'running'
  | 'completed'
  | 'failed';

export interface TaskCondition {
  kind:
    | 'entity_exists'
    | 'dependency_completed'
    | 'distance_less_than'
    | 'duration_elapsed'
    | 'weather_applied'
    | 'traffic_applied'
    | 'memory_recorded'
    | 'manual_review'
    | 'none';
  description: string;
  entity_id?: string | null;
  target_id?: string | null;
  threshold?: number | null;
  timeout_ticks?: number | null;
  metadata: Record<string, unknown>;
}

export interface TaskEdge {
  from_node_id: string;
  to_node_id: string;
  relation: 'blocks' | 'enables' | 'after' | 'parallel';
  description: string;
}

export interface TaskNode {
  id: string;
  action_type: TaskActionType;
  status: TaskStatus;
  actor_id?: string | null;
  actor_selector?: string | null;
  target_actor_id?: string | null;
  target_actor_ids: string[];
  target_entity_id?: string | null;
  target_selector?: string | null;
  vehicle_id?: string | null;
  drone_id?: string | null;
  location?: Vec3 | null;
  depends_on: string[];
  success_condition: TaskCondition;
  failure_condition: TaskCondition;
  timeout_ticks: number;
  retry_limit: number;
  reason: string;
  visible_label: string;
  metadata: Record<string, unknown>;
}

export interface TaskGraph {
  id: string;
  raw_text: string;
  title: string;
  status: TaskGraphStatus;
  nodes: TaskNode[];
  edges: TaskEdge[];
  actors: string[];
  assumptions: string[];
  rejection_reason?: string | null;
  summary: string;
}

export interface TaskGraphPlan {
  plan_id: string;
  source: 'rules' | 'vllm';
  confidence: number;
  graph: TaskGraph;
  executor_step_ids: string[];
  created_tick: number;
}

export interface TaskGraphExecutionSnapshot {
  graph_id: string;
  plan_id: string;
  status: TaskGraphStatus;
  current_node_id?: string | null;
  nodes: TaskNode[];
  completed_count: number;
  total_count: number;
  assumptions: string[];
  rejection_reason?: string | null;
  updated_tick: number;
}

export interface ScenarioStep {
  id: string;
  type:
    | 'move_actor_to_actor'
    | 'move_actor_to_location'
    | 'meet'
    | 'call_taxi'
    | 'taxi_pickup'
    | 'taxi_drive_to_actor'
    | 'drone_move_to_actor'
    | 'drone_deliver'
    | 'move_actor_to_group'
    | 'group_rendezvous'
    | 'remember'
    | 'set_weather'
    | 'traffic_surge'
    | 'wait';
  status: 'pending' | 'running' | 'completed' | 'failed' | 'skipped';
  actor_id?: string | null;
  target_actor_id?: string | null;
  target_actor_ids: string[];
  vehicle_id?: string | null;
  drone_id?: string | null;
  depends_on: string[];
  started_tick?: number | null;
  completed_tick?: number | null;
  visible_label: string;
  evidence?: string | null;
  metadata: Record<string, unknown>;
}

export interface ScenarioDirective {
  id: string;
  raw_text: string;
  title: string;
  status: 'idle' | 'running' | 'completed' | 'failed';
  created_tick: number;
  updated_tick: number;
  current_step_id?: string | null;
  actors: string[];
  steps: ScenarioStep[];
  summary: string;
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
  city_ai: CityAiSnapshot;
  scenario?: ScenarioDirective | null;
  task_graph?: TaskGraphExecutionSnapshot | null;
  entity_brains: EntityBrainState[];
  replans: ReplanRecord[];
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
    | 'city_ai_plan'
    | 'scenario_directive_created'
    | 'scenario_step_started'
    | 'scenario_step_completed'
    | 'scenario_completed'
    | 'task_graph_planned'
    | 'task_graph_rejected'
    | 'task_blocked'
    | 'task_replanned'
    | 'task_recovered'
    | 'learning_signal'
    | 'evolution_updated'
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
  ai_actions: string[];
  scenario?: ScenarioDirective | null;
  task_graph?: TaskGraphPlan | null;
  task_graph_rejection_reason?: string | null;
}

export interface VoiceCommandRequest {
  kind: 'voice_command';
  audio_blob_b64?: string | null;
  mime_type: string;
  user_id: string;
  fallback_transcript?: string | null;
  language?: string | null;
}

export interface VoiceCommandResponse {
  transcript: string;
  stt_mode: 'stub' | 'faster_whisper' | 'fallback';
  stt_status: 'ok' | 'fallback' | 'unavailable';
  detail?: string | null;
  command: GodCommandResponse;
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
