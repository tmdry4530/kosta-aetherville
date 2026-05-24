from __future__ import annotations

from aetherville_schemas import DialogueResponse, MemoryStreamResponse
from aetherville_server.agents import CitizenAgentService, generate_citizen_personas


def test_twenty_citizens_are_fixture_generated() -> None:
    citizens = generate_citizen_personas()

    assert len(citizens) == 20
    assert len({citizen.id for citizen in citizens}) == 20
    assert citizens[0].daily_goal


def test_memory_retrieval_scores_and_sorts_results() -> None:
    service = CitizenAgentService()
    service.append_memory("c01", "rain closed the harbor route", tick=4, tags=["rain", "harbor"])
    service.append_memory("c01", "garden market opened", tick=5, tags=["garden"])

    response = service.memory_stream("c01", query="rain harbor")

    parsed = MemoryStreamResponse.model_validate(response.model_dump())
    assert parsed.memories[0].retrieval_score is not None
    assert parsed.memories[0].retrieval_score >= (parsed.memories[-1].retrieval_score or 0)
    assert "rain" in parsed.memories[0].text


def test_plan_tree_and_dialogue_events_exist() -> None:
    service = CitizenAgentService()
    detail = service.detail("c01")
    dialogue = service.start_dialogue("c01", "c02", topic="traffic reroute", tick=11)

    assert detail.plan_tree.children
    assert detail.plan_tree.status == "active"
    parsed = DialogueResponse.model_validate(dialogue.model_dump())
    assert [event.kind for event in parsed.events] == [
        "dialog_started",
        "dialog_chunk",
        "memory_added",
        "dialog_ended",
    ]
