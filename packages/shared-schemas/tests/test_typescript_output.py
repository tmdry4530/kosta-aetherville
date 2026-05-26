from __future__ import annotations

from pathlib import Path


def test_generated_typescript_contract_exists() -> None:
    generated = Path("packages/shared-schemas/src/typescript/index.ts")
    text = generated.read_text(encoding="utf-8")

    assert "GENERATED FILE" in text
    assert "export interface WorldStatePayload" in text
    assert "export type CommandPayload" in text
    assert "export interface SimStatusResponse" in text
    assert "export interface VoiceCommandRequest" in text
    assert "export interface VoiceCommandResponse" in text
    assert "export interface GodCommandResponse" in text
    assert "ai_actions: string[]" in text
    assert "export interface CitizenDetailResponse" in text
    assert "export interface MemoryRecord" in text
    assert "export interface DialogueResponse" in text
    assert "export interface VisionDetectResponse" in text
    assert "export interface VehicleCameraFrame" in text
    assert "export interface TripState" in text
    assert "export interface TrafficAiSnapshot" in text
    assert "export interface TrafficForecastAiSnapshot" in text
    assert "export interface LearningSnapshot" in text
    assert "export interface LearningStatusResponse" in text
    assert "export interface ModelTrainingSnapshot" in text
    assert "export interface TrainingCycleResponse" in text
    assert "export interface TrainingRollbackResponse" in text
    assert "export interface CityWorldContext" in text
    assert "export interface CityAiAction" in text
    assert "export interface CityAiPlan" in text
    assert "export interface CityAiSnapshot" in text
    assert "export interface ScenarioStep" in text
    assert "export interface ScenarioDirective" in text
    assert "export type TaskActionType" in text
    assert "export interface TaskCondition" in text
    assert "export interface TaskNode" in text
    assert "export interface TaskEdge" in text
    assert "export interface TaskGraph" in text
    assert "export interface TaskGraphPlan" in text
    assert "export interface TaskGraphExecutionSnapshot" in text
    assert "traffic_ai: TrafficAiSnapshot" in text
    assert "traffic_forecast_ai: TrafficForecastAiSnapshot" in text
    assert "learning: LearningSnapshot" in text
    assert "city_ai: CityAiSnapshot" in text
    assert "scenario?: ScenarioDirective | null" in text
    assert "task_graph?: TaskGraphExecutionSnapshot | null" in text
    assert "display_tags: string[]" in text
    assert "policy_bias: PolicyBiasSnapshot" in text
    assert "trajectory_events: TrajectoryEvent[]" in text
    assert "export interface PolicyCandidateSnapshot" in text
    assert "export interface PolicyPromotionSnapshot" in text
    assert "policy_candidates: PolicyCandidateSnapshot[]" in text
    assert "promotion_gate: PolicyPromotionSnapshot" in text
    assert "model_training: ModelTrainingSnapshot" in text
    assert "replans: ReplanRecord[]" in text
    assert "entity_brains: EntityBrainState[]" in text
    assert "export interface EvolutionSnapshot" in text
    assert "export interface ReplanRecord" in text
    assert "export interface EntityGoal" in text
    assert "export interface EntityBrainState" in text
