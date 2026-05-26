"""Persistent learning loop for Aetherville.

The hot path remains safe JSON-backed reward adaptation, but every recorded
experience is also written into the guarded model-training pipeline. That gives
H100/5090 operators a concrete Experience Log → Dataset Builder → trainer →
evaluation → checkpoint promotion/rollback path without mutating weights during
the live tick loop.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Literal

from aetherville_schemas import (
    EventPayload,
    EvolutionSnapshot,
    LearningSignal,
    LearningSnapshot,
    LearningStatusResponse,
    PolicyBiasSnapshot,
    PolicyCandidateSnapshot,
    PolicyPromotionSnapshot,
    TaskOutcomeScore,
    TrajectoryEvent,
)
from aetherville_server.training import TrainingPipeline

DEFAULT_INSIGHT = (
    "아직 학습 신호가 부족합니다. God Mode나 시민 이벤트를 실행하면 적응이 시작됩니다."
)


class LearningStore:
    """Small JSON-backed online adaptation plus trainer handoff state.

    The store is deterministic and cheap enough for the single orchestrator
    process used by the RunPod direct-process runtime. Model weights are trained
    only by explicit background trainer cycles, then promoted or rolled back via
    the checkpoint registry.
    """

    def __init__(self, path: str | Path | None = None) -> None:
        self.path = Path(path) if path else _default_learning_path()
        training_base = self.path.parent / "training"
        self.training = TrainingPipeline(training_base)
        self._state = self._load_state()

    @property
    def persisted(self) -> bool:
        return self.path is not None

    def snapshot(self) -> LearningSnapshot:
        insights = list(self._state.get("insights", []))[-4:]
        if not insights:
            insights = [DEFAULT_INSIGHT]
        evolution = self._evolution_snapshot()
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
            trajectory_events=[
                TrajectoryEvent.model_validate(event)
                for event in list(self._state.get("trajectory_events", []))[-8:]
            ],
            outcome_scores=[
                TaskOutcomeScore.model_validate(score)
                for score in list(self._state.get("outcome_scores", []))[-6:]
            ],
            signals=[
                LearningSignal.model_validate(signal)
                for signal in list(self._state.get("signals", []))[-8:]
            ],
            policy_bias=self._policy_bias_snapshot(),
            evolution=evolution,
            policy_candidates=[
                PolicyCandidateSnapshot.model_validate(candidate)
                for candidate in list(self._state.get("policy_candidates", []))[-6:]
            ],
            promotion_gate=self._promotion_gate_snapshot(),
            model_training=self.training.snapshot(),
        )

    def status_response(self) -> LearningStatusResponse:
        return LearningStatusResponse(
            learning=self.snapshot(),
            explanation=(
                "현재 런타임은 JSON reward-gated adaptation을 즉시 반영하고, 동시에 "
                "Experience Log → Dataset Builder → guarded trainer → Evaluation Gate → "
                "Checkpoint Registry → Promotion/Rollback 파이프라인으로 모델 weight 학습 "
                "준비물을 생성합니다. 실제 weight training은 AETHERVILLE_APPROVE_MODEL_TRAINING=1 "
                "승인 후 별도 trainer job에서 실행됩니다."
            ),
            upgrade_path=[
                "Experience Log JSONL로 모든 God Mode/시민/교통/vision 이벤트 수집",
                "vLLM LoRA/SFT/DPO용 chat_sft_jsonl dataset builder",
                "YOLO pseudo-label manifest builder와 optional self-training script",
                "교통 PPO rollout dataset과 checkpoint trainer/evaluator",
                "LSTM traffic sequence dataset과 checkpoint trainer/evaluator",
                "Evaluation Gate 통과 checkpoint만 registry에서 promoted로 승격",
                "실패 checkpoint는 rejected, 문제 발생 시 rollback endpoint로 "
                "이전 promoted checkpoint 복구",
            ],
        )

    def record_event(self, event: EventPayload, *, tick: int) -> LearningSnapshot:
        metadata = event.metadata
        action = str(metadata.get("action", ""))
        self._state["experience_count"] = int(self._state.get("experience_count", 0)) + 1
        self._state["last_updated_tick"] = max(int(self._state.get("last_updated_tick", 0)), tick)
        self._append_trajectory_event(event, tick=tick, action=action)

        insight = self._insight_for_event(event, action)
        if event.kind == "memory_added":
            self._state["citizen_memory_count"] = int(
                self._state.get("citizen_memory_count", 0)
            ) + 1
            self._append_signal(
                "actor_memory",
                tick=tick,
                value=float(self._state["citizen_memory_count"]),
                entity_id=event.entity_id,
                description="시민 기억 이벤트를 누적해 다음 reason/회상 문구에 반영합니다.",
            )
        if event.kind == "weather_changed" or "weather" in metadata:
            self._state["weather_bias"] = _clamp01(
                float(self._state.get("weather_bias", 0.0)) + 0.08
            )
            self._state["weather_delay_impact"] = _clamp01(
                float(self._state.get("weather_delay_impact", 0.0)) + 0.08
            )
            self._append_signal(
                "weather_delay",
                tick=tick,
                value=float(self._state["weather_delay_impact"]),
                entity_id=event.entity_id,
                description=(
                    "비/날씨 경험이 다음 경로·택시 delay expectation을 "
                    "보수적으로 만듭니다."
                ),
            )
        if action == "traffic_jam" or event.kind == "infrastructure_changed":
            self._state["traffic_bias"] = _clamp01(
                float(self._state.get("traffic_bias", 0.0)) + 0.12
            )
            self._state["traffic_delay_impact"] = _clamp01(
                float(self._state.get("traffic_delay_impact", 0.0)) + 0.1
            )
            self._append_signal(
                "traffic_delay",
                tick=tick,
                value=float(self._state["traffic_delay_impact"]),
                entity_id=event.entity_id,
                description=(
                    "교통량/정체 경험이 다음 차량 속도와 신호 판단을 "
                    "더 조심스럽게 만듭니다."
                ),
            )
        if action == "taxi_call" or event.kind == "trip_requested":
            previous = float(self._state.get("taxi_success_rate", 0.5))
            self._state["taxi_success_rate"] = _clamp01(previous * 0.82 + 0.18)
            self._append_signal(
                "taxi_pickup",
                tick=tick,
                value=float(self._state["taxi_success_rate"]),
                entity_id=str(metadata.get("passenger_id", event.entity_id or "")) or None,
                description="택시 호출 경험을 누적해 다음 dispatch confidence를 조정합니다.",
            )
        if action == "meeting" or event.kind == "relationship_changed":
            self._state["citizen_memory_count"] = int(
                self._state.get("citizen_memory_count", 0)
            ) + 2
            self._state["citizen_meeting_success_count"] = int(
                self._state.get("citizen_meeting_success_count", 0)
            ) + 1
            self._append_signal(
                "citizen_meeting",
                tick=tick,
                value=float(self._state["citizen_meeting_success_count"]),
                entity_id=event.entity_id,
                description="시민 만남 성공을 다음 관계/기억 이유에 반영합니다.",
            )
        if event.kind == "scenario_completed":
            self._state["scenario_success_count"] = int(
                self._state.get("scenario_success_count", 0)
            ) + 1
            self._append_signal(
                "scenario_success",
                tick=tick,
                value=float(self._state["scenario_success_count"]),
                entity_id=event.entity_id,
                description=(
                    "시나리오 완료 경험이 다음 graph timeout/안전 기본값을 "
                    "보수적으로 조정합니다."
                ),
            )
            self._append_outcome(event, tick=tick, success=True)
        if event.kind == "task_blocked":
            self._state["scenario_failure_count"] = int(
                self._state.get("scenario_failure_count", 0)
            ) + 1
            blocker_type = str(metadata.get("blocker_type", ""))
            if blocker_type in {"taxi_unavailable", "pickup_timeout", "traffic_delay"}:
                self._state["taxi_success_rate"] = _clamp01(
                    float(self._state.get("taxi_success_rate", 0.5)) * 0.92
                )
            if blocker_type in {"drone_delay", "low_battery"}:
                self._state["drone_caution"] = _clamp01(
                    float(self._state.get("drone_caution", 0.0)) + 0.12
                )
            self._append_signal(
                "scenario_failure",
                tick=tick,
                value=float(self._state["scenario_failure_count"]),
                entity_id=event.entity_id,
                description="task blocker를 기록해 다음 계획에서 안전 fallback을 선호합니다.",
            )
            self._append_outcome(event, tick=tick, success=False)
        if event.kind == "task_replanned":
            self._state["replan_count"] = int(self._state.get("replan_count", 0)) + 1
            self._append_signal(
                "replan_count",
                tick=tick,
                value=float(self._state["replan_count"]),
                entity_id=event.entity_id,
                description="재계획 횟수를 누적해 future-safe 정책 bias를 강화합니다.",
            )
        if event.kind == "task_recovered":
            self._state["fallback_path_usage"] = int(
                self._state.get("fallback_path_usage", 0)
            ) + 1
            self._append_signal(
                "fallback_path",
                tick=tick,
                value=float(self._state["fallback_path_usage"]),
                entity_id=event.entity_id,
                description=(
                    "복구 fallback 사용을 기록해 다음 유사 상황에서 "
                    "안전 경로를 선호합니다."
                ),
            )
            self._append_outcome(event, tick=tick, success=True)

        if insight:
            insights = list(self._state.get("insights", []))
            insights.append(insight)
            self._state["insights"] = insights[-8:]

        self._state["adaptation_epoch"] = max(
            int(self._state.get("adaptation_epoch", 0)),
            int(self._state.get("experience_count", 0)) // 3,
        )
        self._state["policy_version"] = f"adaptive-demo-v{self._state['adaptation_epoch']}"
        self._maybe_evaluate_policy_candidate(tick=tick, source_signal=event.kind)
        self._save_state()
        self.training.append_experience(
            event,
            tick=tick,
            learning={
                "experience_count": self._state.get("experience_count", 0),
                "adaptation_epoch": self._state.get("adaptation_epoch", 0),
                "policy_version": self._state.get("active_policy_version"),
                "reward_score": self._reward_score(),
            },
        )
        return self.snapshot()

    def reset(self) -> LearningSnapshot:
        self._state = _default_state()
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
        if event.kind == "task_replanned":
            return "막힌 task를 감지하고 bounded fallback으로 재계획했습니다."
        if event.kind == "task_recovered":
            return "복구된 task 경험을 다음 계획의 안전 bias에 반영했습니다."
        if event.kind == "scenario_completed":
            return "시나리오 성공 궤적을 저장해 다음 graph 실행 근거로 사용합니다."
        return None

    def _append_trajectory_event(
        self,
        event: EventPayload,
        *,
        tick: int,
        action: str,
    ) -> None:
        trajectory = {
            "id": f"traj_{tick}_{len(self._state.get('trajectory_events', [])) + 1:04d}",
            "tick": tick,
            "event_kind": event.kind,
            "entity_id": event.entity_id,
            "action": action or None,
            "summary": event.message[:180],
        }
        events = list(self._state.get("trajectory_events", []))
        events.append(trajectory)
        self._state["trajectory_events"] = events[-80:]

    def _append_outcome(self, event: EventPayload, *, tick: int, success: bool) -> None:
        scores = list(self._state.get("outcome_scores", []))
        replan_count = int(self._state.get("replan_count", 0))
        duration = int(event.metadata.get("duration_ticks", max(1, tick)))
        score = 0.92 if success else 0.25
        if replan_count:
            score = max(0.45, score - min(replan_count, 4) * 0.04)
        scores.append(
            {
                "id": f"outcome_{tick}_{len(scores) + 1:04d}",
                "task_id": str(
                    event.metadata.get("scenario_id")
                    or event.metadata.get("step_id")
                    or event.metadata.get("task_graph_id")
                    or event.kind
                ),
                "success": success,
                "duration_ticks": duration,
                "replan_count": replan_count,
                "score": round(score, 3),
                "reason": event.message[:180],
            }
        )
        self._state["outcome_scores"] = scores[-40:]

    def _append_signal(
        self,
        kind: str,
        *,
        tick: int,
        value: float,
        entity_id: str | None,
        description: str,
    ) -> None:
        signals = list(self._state.get("signals", []))
        signals.append(
            {
                "id": f"signal_{tick}_{len(signals) + 1:04d}",
                "tick": tick,
                "kind": kind,
                "value": round(value, 4),
                "entity_id": entity_id,
                "description": description,
            }
        )
        self._state["signals"] = signals[-80:]
        self._state["last_signal"] = description

    def _policy_bias_snapshot(self) -> PolicyBiasSnapshot:
        replan_count = int(self._state.get("replan_count", 0))
        fallback_usage = int(self._state.get("fallback_path_usage", 0))
        return PolicyBiasSnapshot(
            taxi_caution=_clamp01(1.0 - float(self._state.get("taxi_success_rate", 0.5))),
            walking_bias=_clamp01(fallback_usage * 0.08),
            traffic_caution=float(self._state.get("traffic_bias", 0.0)),
            rain_delay_expectation=float(self._state.get("weather_bias", 0.0)),
            drone_caution=_clamp01(float(self._state.get("drone_caution", 0.0))),
            safer_timeout_bias=_clamp01(replan_count * 0.06),
        )

    def _promotion_gate_snapshot(self) -> PolicyPromotionSnapshot:
        return PolicyPromotionSnapshot(
            active_policy_version=str(
                self._state.get(
                    "active_policy_version",
                    self._state.get("policy_version", "adaptive-demo-v0"),
                )
            ),
            evaluator="deterministic_reward_gate",
            candidate_count=len(list(self._state.get("policy_candidates", []))),
            promoted_count=int(self._state.get("promoted_policy_count", 0)),
            rejected_count=int(self._state.get("rejected_policy_count", 0)),
            last_decision=str(self._state.get("last_promotion_decision", "none")),  # type: ignore[arg-type]
            last_promoted_version=self._state.get("last_promoted_version"),
            rollback_available=bool(self._state.get("rollback_policy_version")),
        )

    def _maybe_evaluate_policy_candidate(self, *, tick: int, source_signal: str) -> None:
        experience_count = int(self._state.get("experience_count", 0))
        evaluation_epoch = experience_count // 5
        if evaluation_epoch <= 0 or evaluation_epoch <= int(
            self._state.get("last_candidate_evaluation_epoch", 0)
        ):
            return

        self._state["last_candidate_evaluation_epoch"] = evaluation_epoch
        candidates = list(self._state.get("policy_candidates", []))
        candidate_version = f"adaptive-policy-candidate-v{evaluation_epoch}"
        score_before = float(self._state.get("active_policy_score", 0.5))
        score_after = self._reward_score()
        promoted = score_after >= max(0.55, score_before + 0.015)
        decision = "promoted" if promoted else "rejected"
        reason = (
            "reward gate promoted: 최근 경험이 택시 성공률·재계획 복구·"
            "시나리오 성공을 개선했습니다."
            if promoted
            else "reward gate rejected: 실패/재계획 비용 대비 개선 폭이 부족해 "
            "현재 정책을 유지합니다."
        )

        candidates.append(
            {
                "id": f"policy_candidate_{tick}_{len(candidates) + 1:04d}",
                "tick": tick,
                "candidate_version": candidate_version,
                "source_signal": source_signal,
                "score_before": round(score_before, 4),
                "score_after": round(score_after, 4),
                "promoted": promoted,
                "reason": reason,
            }
        )
        self._state["policy_candidates"] = candidates[-30:]
        self._state["last_promotion_decision"] = decision

        if promoted:
            previous_active = str(
                self._state.get("active_policy_version", self._state.get("policy_version"))
            )
            self._state["rollback_policy_version"] = previous_active
            self._state["active_policy_version"] = candidate_version
            self._state["active_policy_score"] = round(score_after, 4)
            self._state["last_promoted_version"] = candidate_version
            self._state["promoted_policy_count"] = int(
                self._state.get("promoted_policy_count", 0)
            ) + 1
            self._append_signal(
                "policy_promoted",
                tick=tick,
                value=score_after,
                entity_id=None,
                description="reward gate가 후보 정책을 live policy로 승격했습니다.",
            )
            insights = list(self._state.get("insights", []))
            insights.append(
                f"{candidate_version} 승격: reward {score_before:.2f} → {score_after:.2f}"
            )
            self._state["insights"] = insights[-8:]
        else:
            self._state["rejected_policy_count"] = int(
                self._state.get("rejected_policy_count", 0)
            ) + 1
            self._append_signal(
                "policy_rejected",
                tick=tick,
                value=score_after,
                entity_id=None,
                description="reward gate가 후보 정책을 보류하고 기존 live policy를 유지했습니다.",
            )

    def _reward_score(self) -> float:
        taxi_success = float(self._state.get("taxi_success_rate", 0.5))
        successes = int(self._state.get("scenario_success_count", 0))
        failures = int(self._state.get("scenario_failure_count", 0))
        replans = int(self._state.get("replan_count", 0))
        fallback_usage = int(self._state.get("fallback_path_usage", 0))
        meetings = int(self._state.get("citizen_meeting_success_count", 0))
        traffic_delay = float(self._state.get("traffic_delay_impact", 0.0))
        weather_delay = float(self._state.get("weather_delay_impact", 0.0))
        experience_count = max(1, int(self._state.get("experience_count", 1)))

        reliability = _clamp01(
            (successes + fallback_usage * 0.65 + meetings * 0.25) / experience_count
        )
        recovery = _clamp01(fallback_usage / max(1, replans))
        penalty = _clamp01((failures * 0.09 + replans * 0.025) / max(1, experience_count / 4))
        environment_pressure = _clamp01((traffic_delay + weather_delay) * 0.2)
        return _clamp01(
            0.38 * taxi_success
            + 0.28 * reliability
            + 0.2 * recovery
            + 0.14 * environment_pressure
            - penalty * 0.18
        )

    def _evolution_snapshot(self) -> EvolutionSnapshot:
        storage: Literal["json_persistence", "memory"] = (
            "json_persistence" if self.persisted else "memory"
        )
        epoch = int(self._state.get("adaptation_epoch", 0))
        return EvolutionSnapshot(
            version=f"evolution-v{epoch}",
            storage=storage,
            persistence_path=str(self.path) if self.persisted else None,
            scenario_success_count=int(self._state.get("scenario_success_count", 0)),
            scenario_failure_count=int(self._state.get("scenario_failure_count", 0)),
            replan_count=int(self._state.get("replan_count", 0)),
            fallback_path_usage=int(self._state.get("fallback_path_usage", 0)),
            taxi_pickup_success_rate=float(self._state.get("taxi_success_rate", 0.5)),
            weather_delay_impact=float(self._state.get("weather_delay_impact", 0.0)),
            traffic_delay_impact=float(self._state.get("traffic_delay_impact", 0.0)),
            citizen_meeting_success_count=int(
                self._state.get("citizen_meeting_success_count", 0)
            ),
            repeated_actor_memory_count=int(self._state.get("citizen_memory_count", 0)),
            last_signal=self._state.get("last_signal"),
        )


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
        "weather_delay_impact": 0.0,
        "traffic_delay_impact": 0.0,
        "scenario_success_count": 0,
        "scenario_failure_count": 0,
        "citizen_meeting_success_count": 0,
        "replan_count": 0,
        "fallback_path_usage": 0,
        "drone_caution": 0.0,
        "last_updated_tick": 0,
        "insights": [],
        "trajectory_events": [],
        "outcome_scores": [],
        "signals": [],
        "last_signal": None,
        "policy_candidates": [],
        "last_candidate_evaluation_epoch": 0,
        "active_policy_version": "adaptive-demo-v0",
        "active_policy_score": 0.5,
        "promoted_policy_count": 0,
        "rejected_policy_count": 0,
        "last_promotion_decision": "none",
        "last_promoted_version": None,
        "rollback_policy_version": None,
    }


def _clamp01(value: float) -> float:
    return min(1.0, max(0.0, round(value, 4)))
