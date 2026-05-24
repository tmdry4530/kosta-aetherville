"""Tiny Gym-like environment for traffic signal policy tests."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class TrafficObservation:
    ns_queue: int
    ew_queue: int
    active_phase: int
    tick: int

    def as_dict(self) -> dict[str, int]:
        return {
            "ns_queue": self.ns_queue,
            "ew_queue": self.ew_queue,
            "active_phase": self.active_phase,
            "tick": self.tick,
        }


class TrafficSignalEnv:
    """Deterministic reset/step API compatible with future PPO wrapping."""

    def __init__(self, horizon: int = 60) -> None:
        self.horizon = horizon
        self._tick = 0
        self._active_phase = 0
        self._ns_queue = 4
        self._ew_queue = 6

    def reset(self) -> dict[str, int]:
        self._tick = 0
        self._active_phase = 0
        self._ns_queue = 4
        self._ew_queue = 6
        return self._observation().as_dict()

    def step(self, action: int) -> tuple[dict[str, int], float, bool, dict[str, float]]:
        if action not in (0, 1):
            raise ValueError("traffic action must be 0 or 1")
        self._active_phase = action
        self._tick += 1

        arrivals_ns = 2 + (self._tick % 3 == 0)
        arrivals_ew = 1 + (self._tick % 4 == 0)
        served_ns = 3 if self._active_phase == 0 else 0
        served_ew = 3 if self._active_phase == 1 else 0
        self._ns_queue = max(0, self._ns_queue + int(arrivals_ns) - served_ns)
        self._ew_queue = max(0, self._ew_queue + int(arrivals_ew) - served_ew)

        pressure = abs(self._ns_queue - self._ew_queue)
        total_queue = self._ns_queue + self._ew_queue
        reward = -float(total_queue + pressure * 0.2)
        done = self._tick >= self.horizon
        return self._observation().as_dict(), reward, done, {"total_queue": float(total_queue)}

    def _observation(self) -> TrafficObservation:
        return TrafficObservation(
            ns_queue=self._ns_queue,
            ew_queue=self._ew_queue,
            active_phase=self._active_phase,
            tick=self._tick,
        )
