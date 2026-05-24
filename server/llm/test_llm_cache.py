from __future__ import annotations

from aetherville_schemas import MemoryRecord
from aetherville_server.llm import CachedLLMPlanner


def test_daily_plan_is_cached_by_event_key() -> None:
    planner = CachedLLMPlanner()

    first = planner.daily_plan("c01", "민준 cafe owner harbor")
    second = planner.daily_plan("c01", "민준 cafe owner harbor")

    assert first == second
    assert planner.call_count == 1
    assert first.children[1].status == "active"


def test_reflection_is_cached_and_not_tick_driven() -> None:
    planner = CachedLLMPlanner()
    memories = [
        MemoryRecord(
            id="mem_c01_001",
            citizen_id="c01",
            text="rain changed the route",
            created_tick=7,
            importance=0.8,
            tags=["rain"],
        )
    ]

    first = planner.reflect("c01", memories)
    second = planner.reflect("c01", memories)

    assert first == second
    assert planner.call_count == 1
