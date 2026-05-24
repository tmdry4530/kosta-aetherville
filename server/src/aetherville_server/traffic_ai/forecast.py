"""LSTM-compatible forecast facade with deterministic fallback output."""

from __future__ import annotations

import math

from aetherville_schemas import TrafficForecastPoint


class LstmForecastWrapper:
    """Forecast wrapper that keeps the final interface without model weights."""

    def __init__(self, horizon_minutes: tuple[int, ...] = (5, 10, 15)) -> None:
        self.horizon_minutes = horizon_minutes
        self.mode = "deterministic-fallback"

    def predict(
        self, *, tick: int, vehicle_count: int, total_queue: int
    ) -> list[TrafficForecastPoint]:
        points: list[TrafficForecastPoint] = []
        for minute in self.horizon_minutes:
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
