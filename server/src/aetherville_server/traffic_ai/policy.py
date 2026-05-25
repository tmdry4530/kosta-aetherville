"""Traffic policy wrapper with checkpoint fallback to pressure control."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Literal, cast

from aetherville_schemas import TrafficAiSnapshot

FEATURE_NAMES = ("ns_queue", "ew_queue", "active_phase", "tick", "bias")


def checkpoint_path_from_env() -> Path | None:
    """Return the optional checkpoint path configured for direct-process runtime."""

    raw_path = os.getenv("AETHERVILLE_TRAFFIC_POLICY_CHECKPOINT")
    return Path(raw_path) if raw_path else None


class TrafficPolicyWrapper:
    """Load a small policy checkpoint if present, otherwise use pressure control.

    The checkpoint is intentionally JSON so the orchestrator can load it without
    importing heavy ML libraries.  A separate optional training script can use
    PyTorch/CUDA on RunPod and export these lightweight inference weights.
    """

    def __init__(self, checkpoint_path: str | Path | None = None) -> None:
        self.checkpoint_path = Path(checkpoint_path) if checkpoint_path else None
        self.mode = "pressure_baseline"
        self.policy_version = "pressure-baseline-v0"
        self.trained_on_gpu = False
        self.training_backend = "none"
        self.episodes = 0
        self.improvement_pct = 0.0
        self.avg_queue_fixed_cycle: float | None = None
        self.avg_queue_candidate: float | None = None
        self.detail = "pressure baseline fallback"
        self._preferred_action: int | None = None
        self._weights: list[list[float]] | None = None
        self._bias: list[float] | None = None
        if self.checkpoint_path and self.checkpoint_path.exists():
            payload = json.loads(self.checkpoint_path.read_text(encoding="utf-8"))
            self._load_payload(payload)

    @classmethod
    def from_env(cls) -> TrafficPolicyWrapper:
        return cls(checkpoint_path_from_env())

    @property
    def checkpoint_loaded(self) -> bool:
        return self.mode == "checkpoint"

    def select_action(self, observation: dict[str, int]) -> int:
        if self._weights is not None and self._bias is not None:
            features = _features(observation)
            scores = [
                sum(weight * value for weight, value in zip(row, features, strict=True)) + bias
                for row, bias in zip(self._weights, self._bias, strict=True)
            ]
            return 0 if scores[0] >= scores[1] else 1
        if self._preferred_action in (0, 1):
            return self._preferred_action
        return 0 if observation["ns_queue"] >= observation["ew_queue"] else 1

    def snapshot(self, last_action: int | None = None) -> TrafficAiSnapshot:
        action: Literal[0, 1] | None = (
            cast(Literal[0, 1], last_action) if last_action in (0, 1) else None
        )
        return TrafficAiSnapshot(
            mode=self.mode,  # type: ignore[arg-type]
            policy_version=self.policy_version,
            checkpoint_loaded=self.checkpoint_loaded,
            trained_on_gpu=self.trained_on_gpu,
            training_backend=self.training_backend,  # type: ignore[arg-type]
            episodes=self.episodes,
            improvement_pct=round(self.improvement_pct, 3),
            avg_queue_fixed_cycle=self.avg_queue_fixed_cycle,
            avg_queue_candidate=self.avg_queue_candidate,
            last_action=action,
            detail=self.detail,
        )

    def _load_payload(self, payload: dict[str, Any]) -> None:
        weights = payload.get("weights")
        bias = payload.get("bias")
        if isinstance(weights, list) and isinstance(bias, list):
            self._weights = [[float(value) for value in row] for row in weights]
            self._bias = [float(value) for value in bias]
            invalid_shape = len(self._weights) != 2 or any(
                len(row) != len(FEATURE_NAMES) for row in self._weights
            )
            if invalid_shape:
                raise ValueError("traffic checkpoint weights must be 2 x feature_count")
            if len(self._bias) != 2:
                raise ValueError("traffic checkpoint bias must contain two action scores")
        elif "preferred_action" in payload:
            self._preferred_action = int(payload.get("preferred_action", 0))
        else:
            raise ValueError("traffic checkpoint requires weights/bias or preferred_action")

        self.mode = "checkpoint"
        self.policy_version = str(payload.get("policy_version", "traffic-checkpoint-v1"))
        self.trained_on_gpu = bool(payload.get("trained_on_gpu", False))
        self.training_backend = str(payload.get("training_backend", "json"))
        self.episodes = int(payload.get("episodes", 0))
        self.improvement_pct = float(payload.get("improvement_pct", 0.0))
        self.avg_queue_fixed_cycle = _optional_float(payload.get("avg_queue_fixed_cycle"))
        self.avg_queue_candidate = _optional_float(payload.get("avg_queue_candidate"))
        self.detail = str(payload.get("detail", "checkpoint policy loaded"))


def _features(observation: dict[str, int]) -> list[float]:
    return [
        observation["ns_queue"] / 80.0,
        observation["ew_queue"] / 80.0,
        float(observation["active_phase"]),
        min(1.0, observation["tick"] / 120.0),
        1.0,
    ]


def _optional_float(value: Any) -> float | None:
    return None if value is None else float(value)
