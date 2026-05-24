"""Minimal citizen persona, memory, planning, and dialogue interfaces."""

from __future__ import annotations

import math
import random
import time

from aetherville_schemas import (
    CitizenDetailResponse,
    CitizenListResponse,
    CitizenPersona,
    CitizenState,
    DialogueResponse,
    Envelope,
    EnvelopeType,
    EventPayload,
    MemoryRecord,
    MemoryStreamResponse,
    PlanNode,
    ReflectionResponse,
)
from aetherville_server.llm import CachedLLMPlanner

NAMES = [
    "민준",
    "서연",
    "도윤",
    "하린",
    "지호",
    "유나",
    "현우",
    "가은",
    "준서",
    "수아",
    "지민",
    "예린",
    "시우",
    "나연",
    "태오",
    "다은",
    "로이",
    "아린",
    "선우",
    "해나",
]
OCCUPATIONS = [
    "cafe owner",
    "traffic analyst",
    "paramedic",
    "drone mechanic",
    "teacher",
    "urban gardener",
    "taxi dispatcher",
    "street artist",
    "robotics student",
    "market vendor",
]
TRAITS = ["curious", "cautious", "social", "methodical", "playful", "resilient"]
DISTRICTS = ["harbor", "midtown", "skyline", "garden", "old-town"]

CitizenRoute = tuple[tuple[float, float], ...]

CITIZEN_ROUTES: tuple[CitizenRoute, ...] = (
    ((-5.2, -2.7), (-2.4, -2.7), (-0.8, -0.9), (1.6, -0.9), (4.9, 0.8)),
    ((2.8, -5.1), (2.8, -1.4), (1.1, 0.0), (-1.3, 0.0), (-1.3, 4.8)),
    ((-4.8, 2.9), (-2.0, 2.9), (-0.7, 1.0), (0.7, 1.0), (3.9, 3.6)),
    ((4.9, -2.6), (2.1, -2.6), (0.9, -0.4), (-0.9, -0.4), (-4.7, -1.5)),
    ((-5.1, 0.9), (-2.2, 0.9), (-0.6, 2.4), (1.3, 2.4), (4.7, 1.2)),
)


def generate_citizen_personas(count: int = 20, seed: int = 42) -> list[CitizenPersona]:
    """Generate deterministic demo personas without touching an external LLM."""

    rng = random.Random(seed)
    citizens: list[CitizenPersona] = []
    for index in range(count):
        name = NAMES[index % len(NAMES)]
        occupation = OCCUPATIONS[index % len(OCCUPATIONS)]
        district = DISTRICTS[index % len(DISTRICTS)]
        traits = rng.sample(TRAITS, k=2)
        citizens.append(
            CitizenPersona(
                id=f"c{index + 1:02d}",
                name=name,
                age=22 + (index * 7) % 43,
                occupation=occupation,
                traits=traits,
                home_district=district,
                daily_goal=f"keep the {district} district running as {occupation}",
            )
        )
    return citizens


class CitizenAgentService:
    """In-memory citizen runtime with deterministic fixtures and scored retrieval."""

    def __init__(self, count: int = 20, seed: int = 42, planner: CachedLLMPlanner | None = None):
        self.seed = seed
        self._planner = planner or CachedLLMPlanner()
        self._personas = generate_citizen_personas(count=count, seed=seed)
        self._plans: dict[str, PlanNode] = {}
        self._memories: dict[str, list[MemoryRecord]] = {}
        for persona in self._personas:
            self._plans[persona.id] = self._planner.daily_plan(
                persona.id, f"{persona.name} {persona.occupation} {persona.home_district}"
            )
            self._memories[persona.id] = [
                MemoryRecord(
                    id=f"mem_{persona.id}_seed",
                    citizen_id=persona.id,
                    text=f"{persona.name} remembers opening the {persona.home_district} route",
                    created_tick=0,
                    importance=0.55,
                    tags=[persona.home_district, persona.occupation],
                )
            ]

    @property
    def planner_call_count(self) -> int:
        return self._planner.call_count

    def list_personas(self) -> CitizenListResponse:
        return CitizenListResponse(citizens=list(self._personas))

    def detail(self, citizen_id: str) -> CitizenDetailResponse:
        persona = self._get_persona(citizen_id)
        return CitizenDetailResponse(
            persona=persona,
            plan_tree=self._plans[persona.id],
            memories=list(self._memories[persona.id]),
        )

    def memory_stream(self, citizen_id: str, query: str | None = None) -> MemoryStreamResponse:
        if query:
            memories = self.retrieve_memories(citizen_id, query=query)
        else:
            self._get_persona(citizen_id)
            memories = list(reversed(self._memories[citizen_id]))
        return MemoryStreamResponse(citizen_id=citizen_id, memories=memories)

    def retrieve_memories(self, citizen_id: str, query: str, limit: int = 5) -> list[MemoryRecord]:
        self._get_persona(citizen_id)
        query_tokens = self._tokens(query)
        scored: list[MemoryRecord] = []
        for memory in self._memories[citizen_id]:
            memory_tokens = self._tokens(" ".join([memory.text, *memory.tags]))
            overlap = len(query_tokens & memory_tokens)
            score = round(memory.importance + overlap * 0.25, 4)
            scored.append(memory.model_copy(update={"retrieval_score": score}))
        return sorted(scored, key=lambda memory: memory.retrieval_score or 0, reverse=True)[:limit]

    def append_memory(
        self,
        citizen_id: str,
        text: str,
        *,
        tick: int,
        importance: float = 0.5,
        tags: list[str] | None = None,
    ) -> EventPayload:
        self._get_persona(citizen_id)
        memory = MemoryRecord(
            id=f"mem_{citizen_id}_{len(self._memories[citizen_id]) + 1:03d}",
            citizen_id=citizen_id,
            text=text,
            created_tick=tick,
            importance=importance,
            tags=tags or [],
        )
        self._memories[citizen_id].append(memory)
        return EventPayload(
            kind="memory_added",
            message=text,
            entity_id=citizen_id,
            metadata={"memory_id": memory.id, "importance": importance, "tags": memory.tags},
        )

    def reflect(self, citizen_id: str, *, tick: int) -> ReflectionResponse:
        memories = self._memories[self._get_persona(citizen_id).id]
        reflection = self._planner.reflect(citizen_id, memories)
        event = self.append_memory(
            citizen_id,
            reflection,
            tick=tick,
            importance=0.75,
            tags=["reflection"],
        )
        event = EventPayload(
            kind="reflection_generated",
            message=reflection,
            entity_id=citizen_id,
            metadata=event.metadata,
        )
        return ReflectionResponse(
            citizen_id=citizen_id,
            reflection=reflection,
            event=event,
            envelope=self._event_envelope(event, tick=tick),
        )

    def start_dialogue(
        self,
        citizen_id: str,
        target_citizen_id: str | None,
        *,
        topic: str,
        tick: int,
    ) -> DialogueResponse:
        persona = self._get_persona(citizen_id)
        target = self._get_persona(target_citizen_id or self._default_dialogue_target(citizen_id))
        events = [
            EventPayload(
                kind="dialog_started",
                message=f"{persona.name} started a dialogue with {target.name} about {topic}",
                entity_id=persona.id,
                metadata={"target_citizen_id": target.id, "topic": topic},
            ),
            EventPayload(
                kind="dialog_chunk",
                message=f"{persona.name}: {topic} affects my plan for {persona.home_district}.",
                entity_id=persona.id,
                metadata={"target_citizen_id": target.id},
            ),
            self.append_memory(
                persona.id,
                f"Discussed {topic} with {target.name}",
                tick=tick,
                importance=0.68,
                tags=["dialogue", topic],
            ),
            EventPayload(
                kind="dialog_ended",
                message=f"{persona.name} and {target.name} ended their dialogue",
                entity_id=persona.id,
                metadata={"target_citizen_id": target.id},
            ),
        ]
        return DialogueResponse(
            citizen_id=persona.id,
            target_citizen_id=target.id,
            events=events,
            envelopes=[self._event_envelope(event, tick=tick) for event in events],
        )

    def world_states(self, tick: int, running: bool) -> list[CitizenState]:
        states: list[CitizenState] = []
        for index, persona in enumerate(self._personas):
            route = CITIZEN_ROUTES[index % len(CITIZEN_ROUTES)]
            group_offset = (index // len(CITIZEN_ROUTES)) * 0.18
            lane_offset = ((index % 3) - 1) * 0.14
            progress = tick * (0.045 + (index % 4) * 0.006) + index * 1.35
            x, z, yaw = _pose_on_route(route, progress)
            pos = [
                round(x + lane_offset, 3),
                0.0,
                round(z + group_offset, 3),
            ]
            states.append(
                CitizenState(
                    id=persona.id,
                    name=persona.name,
                    pos=pos,
                    rot=[0.0, round(yaw, 3), 0.0],
                    anim="walk" if running else "idle",
                    current_action=self._plans[persona.id].children[1].title,
                    talking_to=None,
                )
            )
        return states

    def _get_persona(self, citizen_id: str) -> CitizenPersona:
        for persona in self._personas:
            if persona.id == citizen_id:
                return persona
        raise KeyError(citizen_id)

    def _default_dialogue_target(self, citizen_id: str) -> str:
        index = next(i for i, persona in enumerate(self._personas) if persona.id == citizen_id)
        return self._personas[(index + 1) % len(self._personas)].id

    @staticmethod
    def _event_envelope(event: EventPayload, *, tick: int) -> Envelope:
        return Envelope(
            type=EnvelopeType.EVENT,
            ts=time.time(),
            tick=tick,
            payload=event.model_dump(mode="json"),
        )

    @staticmethod
    def _tokens(text: str) -> set[str]:
        return {token.strip(".,:;!?").lower() for token in text.split() if token.strip(".,:;!?")}


def _pose_on_route(route: CitizenRoute, progress: float) -> tuple[float, float, float]:
    """Return a deterministic sidewalk/crosswalk pose on a waypoint route."""

    if len(route) < 2:
        x, z = route[0]
        return x, z, 0.0

    segments: list[tuple[tuple[float, float], tuple[float, float], float]] = []
    total_length = 0.0
    for start, end in zip(route, route[1:], strict=False):
        length = math.dist(start, end)
        segments.append((start, end, length))
        total_length += length

    distance = progress % total_length
    for start, end, length in segments:
        if distance <= length:
            local = distance / max(length, 0.001)
            x = start[0] + (end[0] - start[0]) * local
            z = start[1] + (end[1] - start[1]) * local
            yaw = math.atan2(end[0] - start[0], end[1] - start[1])
            return x, z, yaw
        distance -= length

    start, end, _ = segments[-1]
    yaw = math.atan2(end[0] - start[0], end[1] - start[1])
    return end[0], end[1], yaw
