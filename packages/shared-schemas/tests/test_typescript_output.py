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
    assert "traffic_ai: TrafficAiSnapshot" in text
    assert "traffic_forecast_ai: TrafficForecastAiSnapshot" in text
    assert "learning: LearningSnapshot" in text
    assert "display_tags: string[]" in text
