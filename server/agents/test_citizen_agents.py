from __future__ import annotations

import json
from typing import Any

import pytest

from aetherville_schemas import DialogueResponse, MemoryStreamResponse
from aetherville_server.agents import CitizenAgentService, generate_citizen_personas
from aetherville_server.llm import OpenAICompatiblePlanner


def test_twenty_citizens_are_fixture_generated() -> None:
    citizens = generate_citizen_personas()

    assert len(citizens) == 20
    assert len({citizen.id for citizen in citizens}) == 20
    assert [citizens[0].name, citizens[1].name] == ["민지", "민수"]
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


def test_meeting_state_tags_specific_people() -> None:
    service = CitizenAgentService(count=7)
    service.activate_meeting("c01", "c02")

    states = service.world_states(tick=12, running=True)
    minji = next(state for state in states if state.name == "민지")
    minsu = next(state for state in states if state.name == "민수")

    assert minji.talking_to == minsu.id
    assert minsu.talking_to == minji.id
    assert "만남" in minji.display_tags


def test_openai_compatible_planner_reflects_with_vllm_payload(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, object] = {}

    class FakeResponse:
        def __enter__(self) -> FakeResponse:
            return self

        def __exit__(self, exc_type: object, exc: object, tb: object) -> None:
            del exc_type, exc, tb
            return None

        @staticmethod
        def read() -> bytes:
            return json.dumps(
                {"choices": [{"message": {"content": "민지는 비와 정체를 함께 기억한다."}}]}
            ).encode()

    def fake_urlopen(request: Any, timeout: float) -> FakeResponse:
        captured["url"] = request.full_url
        captured["timeout"] = timeout
        captured["body"] = json.loads(request.data.decode())
        return FakeResponse()

    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)
    planner = OpenAICompatiblePlanner(base_url="http://vllm.local/v1", model="demo-model")
    service = CitizenAgentService(count=1, planner=planner)
    service.append_memory("c01", "rain and traffic surge changed the city", tick=7)

    reflection = service.reflect("c01", tick=8)

    assert reflection.reflection == "민지는 비와 정체를 함께 기억한다."
    assert captured["url"] == "http://vllm.local/v1/chat/completions"
    assert captured["body"]["model"] == "demo-model"  # type: ignore[index]
