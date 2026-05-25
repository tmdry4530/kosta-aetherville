"""Fixed-cycle traffic light controller used until PPO checkpoints exist."""

from __future__ import annotations

from typing import Literal

from aetherville_schemas import TrafficLightState

TrafficPhase = Literal["north_south", "east_west"]


class FixedCycleController:
    """Deterministic signal cycle with yellow transition windows."""

    def __init__(self, cycle_seconds: int = 30, yellow_seconds: int = 4) -> None:
        self.cycle_seconds = cycle_seconds
        self.yellow_seconds = yellow_seconds

    def phase_for_tick(self, tick: int) -> TrafficPhase:
        cycle_index = (tick // self.cycle_seconds) % 2
        return "north_south" if cycle_index == 0 else "east_west"

    def lights_for_tick(
        self,
        tick: int,
        *,
        policy_action: int | None = None,
        policy_mode: str | None = None,
    ) -> list[TrafficLightState]:
        phase = (
            "north_south"
            if policy_action == 0
            else "east_west"
            if policy_action == 1
            else self.phase_for_tick(tick)
        )
        elapsed = tick % self.cycle_seconds
        remaining = float(max(0, self.cycle_seconds - elapsed))
        ns_state = self._state_for_axis(phase == "north_south", remaining)
        ew_state = self._state_for_axis(phase == "east_west", remaining)
        policy_tags = [f"AI정책:{policy_mode}"] if policy_mode else []
        return [
            TrafficLightState(
                id="tl_nw",
                pos=[-3.0, 0.0, -3.0],
                state=ns_state,
                remaining_sec=remaining,
                display_tags=["신호등", ns_state, *policy_tags],
            ),
            TrafficLightState(
                id="tl_ne",
                pos=[3.0, 0.0, -3.0],
                state=ew_state,
                remaining_sec=remaining,
                display_tags=["신호등", ew_state, *policy_tags],
            ),
            TrafficLightState(
                id="tl_sw",
                pos=[-3.0, 0.0, 3.0],
                state=ew_state,
                remaining_sec=remaining,
                display_tags=["신호등", ew_state, *policy_tags],
            ),
            TrafficLightState(
                id="tl_se",
                pos=[3.0, 0.0, 3.0],
                state=ns_state,
                remaining_sec=remaining,
                display_tags=["신호등", ns_state, *policy_tags],
            ),
        ]

    def _state_for_axis(
        self, active: bool, remaining: float
    ) -> Literal["red", "yellow", "green"]:
        if not active:
            return "red"
        if remaining <= self.yellow_seconds:
            return "yellow"
        return "green"
