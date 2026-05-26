from __future__ import annotations

from aetherville_schemas import CityActorContext, CityWorldContext
from aetherville_server.city_ai import DeterministicCityPlanner


def test_deterministic_city_planner_returns_bounded_visible_actions() -> None:
    context = CityWorldContext(
        tick=120,
        time_of_day="09:42",
        weather="clear",
        citizens=[
            CityActorContext(
                id=f"c{index + 1:02d}",
                kind="citizen",
                name=name,
                pos=[float(index), 0.0, 0.0],
                status="observing",
                tags=[name],
            )
            for index, name in enumerate(["민지", "민수", "서연", "도윤", "하린", "지호"])
        ],
        vehicles=[
            CityActorContext(
                id="v01",
                kind="vehicle",
                name="taxi",
                pos=[-6.0, 0.0, -3.0],
                status="idle",
                tags=["TAXI"],
            )
        ],
        recent_events=[],
    )

    plan = DeterministicCityPlanner().plan(context)

    assert plan.source == "rules"
    assert plan.actions
    assert all(action.type != "no_op" for action in plan.actions)
    assert {action.type for action in plan.actions} <= {
        "move_citizen",
        "call_taxi",
        "meet",
        "remember",
        "traffic_surge",
        "set_weather",
    }
