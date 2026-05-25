"""Persistent demo learning loop for Aetherville.

This is intentionally not GPU model training.  It records live city experience
signals, persists an adaptive policy snapshot, and feeds that snapshot back into
simulation forecasts/tags so a long-running direct-process demo visibly evolves
without starting costly model downloads or training jobs.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from aetherville_schemas import EventPayload, LearningSnapshot, LearningStatusResponse

DEFAULT_INSIGHT = (
    "아직 학습 신호가 부족합니다. God Mode나 시민 이벤트를 실행하면 적응이 시작됩니다."
)


class LearningStore:
    """Small JSON-backed online adaptation state.

    The store is deterministic, cheap, and process-safe enough for the single
    orchestrator process used by the RunPod direct-process runtime.  It is a
    persistence/adaptation layer, not a replacement for future PPO/LSTM/vLLM
    training pipelines.
    """

    def __init__(self, path: str | Path | None = None) -> None:
        self.path = Path(path) if path else _default_learning_path()
        self._state = self._load_state()

    @property
    def persisted(self) -> bool:
        return self.path is not None

    def snapshot(self) -> LearningSnapshot:
        insights = list(self._state.get("insights", []))[-4:]
        if not insights:
            insights = [DEFAULT_INSIGHT]
        return LearningSnapshot(
            storage="json_persistence" if self.persisted else "memory",
            experience_count=int(self._state.get("experience_count", 0)),
            adaptation_epoch=int(self._state.get("adaptation_epoch", 0)),
            policy_version=str(self._state.get("policy_version", "adaptive-demo-v0")),
            traffic_bias=float(self._state.get("traffic_bias", 0.0)),
            taxi_success_rate=float(self._state.get("taxi_success_rate", 0.5)),
            citizen_memory_count=int(self._state.get("citizen_memory_count", 0)),
            weather_bias=float(self._state.get("weather_bias", 0.0)),
            last_updated_tick=int(self._state.get("last_updated_tick", 0)),
            insights=insights,
        )

    def status_response(self) -> LearningStatusResponse:
        return LearningStatusResponse(
            learning=self.snapshot(),
            explanation=(
                "현재 학습 루프는 비용 안전한 deterministic online adaptation입니다. "
                "서버가 실행되는 동안 God Mode, 시민 기억, 택시, 정체 이벤트를 JSON 상태로 "
                "누적하고 다음 forecast/tag/데모 정책에 즉시 반영합니다."
            ),
            upgrade_path=[
                "Redis/Postgres/Vector DB로 경험 로그 영속화",
                "PPO 교통 신호 정책 오프라인 학습 후 checkpoint 배포",
                "LSTM/Transformer 교통 예측 재학습 잡 추가",
                "승인된 real vLLM으로 시민 reflection/plan batch worker 연결",
            ],
        )

    def record_event(self, event: EventPayload, *, tick: int) -> LearningSnapshot:
        metadata = event.metadata
        action = str(metadata.get("action", ""))
        self._state["experience_count"] = int(self._state.get("experience_count", 0)) + 1
        self._state["last_updated_tick"] = max(int(self._state.get("last_updated_tick", 0)), tick)

        insight = self._insight_for_event(event, action)
        if event.kind == "memory_added":
            self._state["citizen_memory_count"] = int(
                self._state.get("citizen_memory_count", 0)
            ) + 1
        if event.kind == "weather_changed" or "weather" in metadata:
            self._state["weather_bias"] = _clamp01(
                float(self._state.get("weather_bias", 0.0)) + 0.08
            )
        if action == "traffic_jam" or event.kind == "infrastructure_changed":
            self._state["traffic_bias"] = _clamp01(
                float(self._state.get("traffic_bias", 0.0)) + 0.12
            )
        if action == "taxi_call" or event.kind == "trip_requested":
            previous = float(self._state.get("taxi_success_rate", 0.5))
            self._state["taxi_success_rate"] = _clamp01(previous * 0.82 + 0.18)
        if action == "meeting" or event.kind == "relationship_changed":
            self._state["citizen_memory_count"] = int(
                self._state.get("citizen_memory_count", 0)
            ) + 2

        if insight:
            insights = list(self._state.get("insights", []))
            insights.append(insight)
            self._state["insights"] = insights[-8:]

        self._state["adaptation_epoch"] = max(
            int(self._state.get("adaptation_epoch", 0)),
            int(self._state.get("experience_count", 0)) // 3,
        )
        self._state["policy_version"] = f"adaptive-demo-v{self._state['adaptation_epoch']}"
        self._save_state()
        return self.snapshot()

    def learned_queue_boost(self) -> int:
        """Extra queue pressure learned from repeated congestion commands."""

        return int(round(float(self._state.get("traffic_bias", 0.0)) * 42))

    def traffic_speed_factor(self) -> float:
        """Speed multiplier for learned traffic pressure when no explicit jam is active."""

        return max(0.72, 1.0 - float(self._state.get("traffic_bias", 0.0)) * 0.34)

    def _load_state(self) -> dict[str, Any]:
        if self.path.exists():
            try:
                payload = json.loads(self.path.read_text(encoding="utf-8"))
                if isinstance(payload, dict):
                    return _default_state() | payload
            except (json.JSONDecodeError, OSError):
                return _default_state()
        return _default_state()

    def _save_state(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        tmp_path = self.path.with_suffix(f"{self.path.suffix}.tmp")
        tmp_path.write_text(json.dumps(self._state, ensure_ascii=False, indent=2), encoding="utf-8")
        tmp_path.replace(self.path)

    @staticmethod
    def _insight_for_event(event: EventPayload, action: str) -> str | None:
        if action == "traffic_jam":
            return "교통량 증가 패턴을 학습해 forecast 혼잡도를 더 민감하게 보정했습니다."
        if action == "taxi_call":
            return "민지의 택시 호출 경험을 누적해 택시 dispatch 성공률을 업데이트했습니다."
        if action == "meeting":
            return "시민 만남 이벤트를 기억 그래프 신호로 반영했습니다."
        if event.kind == "weather_changed":
            return "날씨 개입 경험을 누적해 비/시야 이벤트 대응 가중치를 올렸습니다."
        if event.kind == "memory_added":
            return "시민 기억 스트림이 증가해 검색/회상 신호가 강화됐습니다."
        return None


def _default_learning_path() -> Path:
    configured = os.getenv("AETHERVILLE_LEARNING_PATH")
    if configured:
        return Path(configured)
    run_dir = Path(os.getenv("AETHERVILLE_RUN_DIR", "/tmp/aetherville"))
    return run_dir / "learning_state.json"


def _default_state() -> dict[str, Any]:
    return {
        "experience_count": 0,
        "adaptation_epoch": 0,
        "policy_version": "adaptive-demo-v0",
        "traffic_bias": 0.0,
        "taxi_success_rate": 0.5,
        "citizen_memory_count": 0,
        "weather_bias": 0.0,
        "last_updated_tick": 0,
        "insights": [],
    }


def _clamp01(value: float) -> float:
    return min(1.0, max(0.0, round(value, 4)))
