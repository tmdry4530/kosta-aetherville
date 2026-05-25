"""LSTM-compatible forecast facade with checkpoint and fallback output."""

from __future__ import annotations

import json
import math
import os
from pathlib import Path
from typing import Any

from aetherville_schemas import TrafficForecastAiSnapshot, TrafficForecastPoint


class LstmForecastWrapper:
    """Traffic forecast wrapper with pure-Python LSTM checkpoint inference.

    Training may use PyTorch/CUDA on RunPod, but runtime inference deliberately
    stays stdlib-only so the orchestrator tick loop does not import torch or
    allocate GPU memory.
    """

    def __init__(
        self,
        horizon_minutes: tuple[int, ...] = (5, 10, 15),
        checkpoint_path: str | Path | None = None,
    ) -> None:
        self.horizon_minutes = horizon_minutes
        self.mode = "deterministic_fallback"
        self._checkpoint_path = (
            Path(checkpoint_path) if checkpoint_path else forecast_path_from_env()
        )
        self._checkpoint: dict[str, Any] | None = None
        self._snapshot = TrafficForecastAiSnapshot(
            horizon_minutes=list(horizon_minutes),
            detail="deterministic forecast fallback",
        )
        if self._checkpoint_path and self._checkpoint_path.exists():
            self._checkpoint = json.loads(self._checkpoint_path.read_text(encoding="utf-8"))
            self.mode = "lstm_checkpoint"
            self.horizon_minutes = tuple(
                int(value)
                for value in self._checkpoint.get("horizon_minutes", horizon_minutes)
            )
            self._snapshot = _snapshot_from_checkpoint(self._checkpoint)

    def predict(
        self, *, tick: int, vehicle_count: int, total_queue: int
    ) -> list[TrafficForecastPoint]:
        if self._checkpoint is not None:
            return self._predict_with_checkpoint(
                tick=tick,
                vehicle_count=vehicle_count,
                total_queue=total_queue,
            )
        return _fallback_forecast(
            tick=tick,
            vehicle_count=vehicle_count,
            total_queue=total_queue,
            horizon_minutes=self.horizon_minutes,
        )

    def snapshot(self) -> TrafficForecastAiSnapshot:
        return self._snapshot

    def _predict_with_checkpoint(
        self,
        *,
        tick: int,
        vehicle_count: int,
        total_queue: int,
    ) -> list[TrafficForecastPoint]:
        assert self._checkpoint is not None
        sequence_length = int(self._checkpoint["sequence_length"])
        features = [
            _features_for_tick(
                current_tick=max(0, tick - sequence_length + 1 + offset),
                vehicle_count=vehicle_count,
                total_queue=total_queue,
            )
            for offset in range(sequence_length)
        ]
        outputs = _lstm_forward(self._checkpoint, features)
        expected_scale = float(self._checkpoint.get("expected_scale", 120.0))
        horizons = [int(value) for value in self._checkpoint["horizon_minutes"]]
        points: list[TrafficForecastPoint] = []
        for index, minute in enumerate(horizons):
            expected_raw = outputs[index]
            congestion_raw = outputs[index + len(horizons)]
            expected = max(0, int(round(_sigmoid(expected_raw) * expected_scale)))
            congestion = min(1.0, max(0.0, round(_sigmoid(congestion_raw), 3)))
            points.append(
                TrafficForecastPoint(
                    minute_offset=minute,
                    expected_vehicle_count=expected,
                    congestion_index=congestion,
                )
            )
        return points


def forecast_path_from_env() -> Path | None:
    raw_path = os.getenv("AETHERVILLE_TRAFFIC_FORECAST_CHECKPOINT")
    return Path(raw_path) if raw_path else None


def _fallback_forecast(
    *,
    tick: int,
    vehicle_count: int,
    total_queue: int,
    horizon_minutes: tuple[int, ...],
) -> list[TrafficForecastPoint]:
    points: list[TrafficForecastPoint] = []
    for minute in horizon_minutes:
        wave = abs(math.sin((tick + minute * 12) * 0.04))
        expected = int(vehicle_count + total_queue + 18 + minute * 1.8 + wave * 12)
        congestion = min(1.0, round(0.18 + total_queue / 80 + wave * 0.28, 3))
        points.append(
            TrafficForecastPoint(
                minute_offset=minute,
                expected_vehicle_count=expected,
                congestion_index=congestion,
            )
        )
    return points


def _snapshot_from_checkpoint(checkpoint: dict[str, Any]) -> TrafficForecastAiSnapshot:
    return TrafficForecastAiSnapshot(
        mode="lstm_checkpoint",
        forecast_version=str(checkpoint.get("forecast_version", "traffic-lstm-v1")),
        checkpoint_loaded=True,
        trained_on_gpu=bool(checkpoint.get("trained_on_gpu", False)),
        training_backend=str(checkpoint.get("training_backend", "json")),  # type: ignore[arg-type]
        sequence_length=int(checkpoint.get("sequence_length", 0)),
        horizon_minutes=[int(value) for value in checkpoint.get("horizon_minutes", [])],
        mape=_optional_float(checkpoint.get("mape")),
        training_loss=_optional_float(checkpoint.get("training_loss")),
        detail=str(checkpoint.get("detail", "LSTM checkpoint forecast loaded")),
    )


def _lstm_forward(checkpoint: dict[str, Any], sequence: list[list[float]]) -> list[float]:
    weights = checkpoint["lstm"]
    weight_ih = weights["weight_ih"]
    weight_hh = weights["weight_hh"]
    bias_ih = weights["bias_ih"]
    bias_hh = weights["bias_hh"]
    hidden_size = int(checkpoint["hidden_size"])
    h = [0.0 for _ in range(hidden_size)]
    c = [0.0 for _ in range(hidden_size)]

    for features in sequence:
        gates = [
            sum(weight * value for weight, value in zip(row, features, strict=True))
            + sum(weight * value for weight, value in zip(hidden_row, h, strict=True))
            + bias_i
            + bias_h
            for row, hidden_row, bias_i, bias_h in zip(
                weight_ih, weight_hh, bias_ih, bias_hh, strict=True
            )
        ]
        input_gate = [_sigmoid(value) for value in gates[:hidden_size]]
        forget_gate = [_sigmoid(value) for value in gates[hidden_size : hidden_size * 2]]
        cell_gate = [math.tanh(value) for value in gates[hidden_size * 2 : hidden_size * 3]]
        output_gate = [_sigmoid(value) for value in gates[hidden_size * 3 : hidden_size * 4]]
        c = [
            forget * prev_cell + input_value * candidate
            for forget, prev_cell, input_value, candidate in zip(
                forget_gate, c, input_gate, cell_gate, strict=True
            )
        ]
        h = [
            output * math.tanh(cell)
            for output, cell in zip(output_gate, c, strict=True)
        ]

    head_weight = checkpoint["head"]["weight"]
    head_bias = checkpoint["head"]["bias"]
    return [
        sum(weight * value for weight, value in zip(row, h, strict=True)) + bias
        for row, bias in zip(head_weight, head_bias, strict=True)
    ]


def _features_for_tick(
    *,
    current_tick: int,
    vehicle_count: int,
    total_queue: int,
) -> list[float]:
    return [
        math.sin(current_tick * 0.04),
        math.cos(current_tick * 0.04),
        vehicle_count / 10.0,
        total_queue / 120.0,
        1.0,
    ]


def _sigmoid(value: float) -> float:
    if value >= 0:
        z = math.exp(-value)
        return 1.0 / (1.0 + z)
    z = math.exp(value)
    return z / (1.0 + z)


def _optional_float(value: Any) -> float | None:
    return None if value is None else float(value)
