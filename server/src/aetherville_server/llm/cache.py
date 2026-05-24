"""Event-driven cached LLM facade for the playable citizen slice.

This module intentionally does not call an external model.  It mirrors the
future vLLM boundary while proving the important runtime invariant: planning
and reflection happen on explicit events and are cached, never inside the
simulation tick loop.
"""

from __future__ import annotations

import hashlib

from aetherville_schemas import MemoryRecord, PlanNode


class CachedLLMPlanner:
    """Deterministic stand-in for vLLM-backed citizen planning/reflection."""

    def __init__(self) -> None:
        self._cache: dict[str, str | PlanNode] = {}
        self.call_count = 0

    def _remember(self, key: str, value: str | PlanNode) -> str | PlanNode:
        self.call_count += 1
        self._cache[key] = value
        return value

    def daily_plan(self, citizen_id: str, persona_summary: str) -> PlanNode:
        key = f"daily-plan:{citizen_id}:{self._fingerprint(persona_summary)}"
        cached = self._cache.get(key)
        if isinstance(cached, PlanNode):
            return cached

        plan = PlanNode(
            id=f"plan_{citizen_id}",
            title=f"{persona_summary} daily loop",
            status="active",
            children=[
                PlanNode(id=f"plan_{citizen_id}_morning", title="open routine", status="done"),
                PlanNode(
                    id=f"plan_{citizen_id}_midday",
                    title="react to city events",
                    status="active",
                ),
                PlanNode(id=f"plan_{citizen_id}_evening", title="reflect and summarize"),
            ],
        )
        remembered = self._remember(key, plan)
        assert isinstance(remembered, PlanNode)
        return remembered

    def reflect(self, citizen_id: str, memories: list[MemoryRecord]) -> str:
        memory_key = "|".join(memory.id for memory in memories)
        key = f"reflection:{citizen_id}:{self._fingerprint(memory_key)}"
        cached = self._cache.get(key)
        if isinstance(cached, str):
            return cached

        if memories:
            top_memory = max(memories, key=lambda memory: memory.importance)
            reflection = f"{citizen_id} learned: {top_memory.text}"
        else:
            reflection = f"{citizen_id} has no memories to reflect on yet"
        remembered = self._remember(key, reflection)
        assert isinstance(remembered, str)
        return remembered

    @staticmethod
    def _fingerprint(value: str) -> str:
        return hashlib.sha1(value.encode("utf-8")).hexdigest()[:12]
