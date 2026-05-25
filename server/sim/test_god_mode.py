from __future__ import annotations

from aetherville_schemas import (
    CityAiAction,
    CityAiPlan,
    CityWorldContext,
    GodCommand,
    WorldStatePayload,
)
from aetherville_server.orchestrator import GodCommandDispatcher
from aetherville_server.orchestrator.vllm_command import GodCommandInterpretation
from aetherville_server.sim import SimulationEngine


def make_command(text: str) -> GodCommand:
    return GodCommand(input_modality="text", raw_text=text, user_id="presenter")


def test_text_god_command_changes_weather_and_world_state() -> None:
    engine = SimulationEngine()

    response = engine.execute_god_command(make_command("도시에 비를 내려줘"))
    for _ in range(240):
        engine.step()
    state = WorldStatePayload.model_validate(engine.snapshot().model_dump())

    assert response.category == "environment"
    assert state.world.weather == "rain"
    assert state.world.active_event == "weather:rain"
    assert response.envelopes


def test_person_and_relationship_commands_inject_memory_events() -> None:
    engine = SimulationEngine()

    person = engine.execute_god_command(make_command("민준에게 오늘 일을 기억시켜줘"))
    relationship = engine.execute_god_command(make_command("민지랑 민수가 만난다"))
    state = WorldStatePayload.model_validate(engine.snapshot().model_dump())
    minji = next(citizen for citizen in state.citizens if citizen.name == "민지")
    minsu = next(citizen for citizen in state.citizens if citizen.name == "민수")

    assert person.category == "person"
    assert relationship.category == "relationship"
    assert any(event.kind == "memory_added" for event in person.events)
    assert sum(event.kind == "memory_added" for event in relationship.events) == 2
    assert minji.talking_to == minsu.id
    assert minsu.talking_to == minji.id
    assert "만남" in minji.display_tags


def test_infrastructure_command_has_visible_world_effect() -> None:
    engine = SimulationEngine()

    response = engine.execute_god_command(make_command("교통량 증가시켜"))
    state = WorldStatePayload.model_validate(engine.snapshot().model_dump())

    assert response.category == "infrastructure"
    assert response.event.metadata["action"] == "traffic_jam"
    assert state.world.infrastructure_status == "traffic congestion active"
    assert state.vehicles[1].display_tags[:2] == ["정체", "저속"]
    assert state.traffic_forecast[0].congestion_index >= 0.9
    assert state.learning.traffic_bias > 0


def test_taxi_command_adds_visible_taxi_tag() -> None:
    engine = SimulationEngine()

    response = engine.execute_god_command(make_command("민지가 택시를 불러줘"))
    state = WorldStatePayload.model_validate(engine.snapshot().model_dump())

    assert response.event.kind == "trip_requested"
    assert response.event.metadata["action"] == "taxi_call"
    assert state.vehicles[0].passenger_id == "c01"
    assert state.vehicles[0].display_tags[0] == "택시 호출"
    assert "민지 픽업 중" in state.vehicles[0].display_tags
    assert state.learning.taxi_success_rate > 0.5


class FakeInterpreter:
    def interpret(self, command: GodCommand) -> GodCommandInterpretation:
        del command
        return GodCommandInterpretation(
            category="infrastructure",
            action="traffic_jam",
            target="commute",
            confidence=0.93,
            reason="vLLM mapped the natural command to congestion",
        )


def test_god_command_response_exposes_vllm_interpretation_metadata() -> None:
    engine = SimulationEngine()
    engine.command_dispatcher = GodCommandDispatcher(interpreter=FakeInterpreter())

    response = engine.execute_god_command(make_command("출근길 압박감을 만들어줘"))

    assert response.ai_mode == "vllm"
    assert response.ai_confidence == 0.93
    assert response.ai_reason == "vLLM mapped the natural command to congestion"
    assert response.event.metadata["ai_mode"] == "vllm"
    assert response.event.metadata["action"] == "traffic_jam"


class MultiFakeInterpreter:
    def interpret(self, command: GodCommand) -> GodCommandInterpretation:
        del command
        return GodCommandInterpretation(
            category="environment",
            action="rain",
            secondary_actions=("traffic_jam", "taxi_call", "meeting"),
            target="demo scene",
            confidence=0.96,
            reason="vLLM decomposed a combined presenter command",
        )


def test_multi_action_god_command_applies_all_visible_effects() -> None:
    engine = SimulationEngine()
    engine.command_dispatcher = GodCommandDispatcher(interpreter=MultiFakeInterpreter())

    response = engine.execute_god_command(
        make_command("비 오게 하고 민지가 택시를 부르고 민수와 만나게 하고 교통량을 늘려줘")
    )
    state = WorldStatePayload.model_validate(engine.snapshot().model_dump())
    minji = next(citizen for citizen in state.citizens if citizen.name == "민지")
    minsu = next(citizen for citizen in state.citizens if citizen.name == "민수")

    assert response.ai_mode == "vllm"
    assert response.ai_actions == ["rain", "traffic_jam", "taxi_call", "meeting"]
    assert response.event.kind == "god_command_executed"
    assert len(response.events) >= 6
    assert state.world.weather == "rain"
    assert state.world.infrastructure_status == "traffic congestion active"
    assert state.vehicles[0].passenger_id == "c01"
    assert state.vehicles[1].display_tags[:2] == ["정체", "저속"]
    meeting_event = next(
        event
        for event in response.events
        if event.kind == "relationship_changed"
        and event.metadata.get("action") == "meeting"
    )
    assert meeting_event.metadata["deferred_until"] == "taxi_arrival"
    assert minji.talking_to is None
    assert minsu.talking_to is None

    engine.running = True
    for _ in range(900):
        engine.step()
    arrived_state = WorldStatePayload.model_validate(engine.snapshot().model_dump())
    minji = next(citizen for citizen in arrived_state.citizens if citizen.name == "민지")
    minsu = next(citizen for citizen in arrived_state.citizens if citizen.name == "민수")

    assert minji.talking_to == minsu.id
    assert minsu.talking_to == minji.id


class NamedTaxiMeetingInterpreter:
    def interpret(self, command: GodCommand) -> GodCommandInterpretation:
        del command
        return GodCommandInterpretation(
            category="infrastructure",
            action="taxi_call",
            secondary_actions=("meeting",),
            target="['지호','하린']",
            confidence=0.97,
            reason="지호가 택시를 타고 하린에게 이동해야 한다",
        )


def test_named_taxi_meeting_moves_before_relationship_activation() -> None:
    engine = SimulationEngine()
    engine.command_dispatcher = GodCommandDispatcher(
        interpreter=NamedTaxiMeetingInterpreter()
    )

    response = engine.execute_god_command(make_command("지호가 택시를 부르고, 하린에게 간다"))
    state = WorldStatePayload.model_validate(engine.snapshot().model_dump())
    taxi = state.vehicles[0]
    jiho = next(citizen for citizen in state.citizens if citizen.name == "지호")
    harin = next(citizen for citizen in state.citizens if citizen.name == "하린")
    taxi_event = next(event for event in response.events if event.kind == "trip_requested")
    meeting_event = next(
        event
        for event in response.events
        if event.kind == "relationship_changed"
        and event.metadata.get("action") == "meeting"
    )

    assert response.ai_actions == ["taxi_call", "meeting"]
    assert taxi_event.metadata["passenger_id"] == "c06"
    assert taxi_event.metadata["destination_citizen_id"] == "c05"
    assert meeting_event.metadata["deferred_until"] == "taxi_arrival"
    assert taxi.passenger_id == "c06"
    assert taxi.destination == [harin.pos[0], 0.0, harin.pos[2]]
    assert "민지에게 이동" not in taxi.display_tags
    assert any(tag in taxi.display_tags for tag in ("지호 픽업 중", "지호 탑승 대기"))
    assert jiho.talking_to is None
    assert harin.talking_to is None

    engine.running = True
    positions = []
    for _ in range(260):
        positions.append(tuple(engine.snapshot().vehicles[0].pos))
        engine.step()
    arrived_state = WorldStatePayload.model_validate(engine.snapshot().model_dump())
    jiho = next(citizen for citizen in arrived_state.citizens if citizen.name == "지호")
    harin = next(citizen for citizen in arrived_state.citizens if citizen.name == "하린")

    assert len(set(positions[:80])) > 8
    assert jiho.talking_to == harin.id
    assert harin.talking_to == jiho.id
    assert any(event.metadata.get("via") == "taxi_arrival" for event in engine.timeline)


class FakeCityPlanner:
    source = "vllm"

    def plan(self, context: CityWorldContext) -> CityAiPlan:
        assert context.citizens
        return CityAiPlan(
            plan_id="city_vllm_test",
            source="vllm",
            confidence=0.91,
            summary="서연이 민지에게 자율 이동",
            actions=[
                CityAiAction(
                    type="move_citizen",
                    actor_id="c03",
                    destination_actor_id="c01",
                    label="민지에게 자율 이동",
                    reason="vLLM chose a social movement objective",
                ),
                CityAiAction(
                    type="remember",
                    actor_id="c03",
                    memory="서연은 AI 도시 운영자의 판단으로 민지에게 이동했다.",
                    reason="movement intent should persist as memory",
                ),
            ],
        )


def test_city_ai_planner_moves_citizen_and_records_plan() -> None:
    engine = SimulationEngine(city_planner=FakeCityPlanner())

    plan = engine.run_city_planner_once()
    state = WorldStatePayload.model_validate(engine.snapshot().model_dump())
    seoyeon = next(citizen for citizen in state.citizens if citizen.id == "c03")

    assert plan is not None
    assert state.city_ai.mode == "vllm"
    assert state.city_ai.plan_id == "city_vllm_test"
    assert "AI계획" in seoyeon.display_tags
    assert any(event.kind == "city_ai_plan" for event in engine.timeline)
    assert any(
        event.kind == "memory_added" and event.entity_id == "c03"
        for event in engine.timeline
    )

    engine.running = True
    positions = []
    for _ in range(40):
        positions.append(tuple(engine.snapshot().citizens[2].pos))
        engine.step()

    assert len(set(positions)) > 8


class FakeTaxiCityPlanner:
    source = "vllm"

    def plan(self, context: CityWorldContext) -> CityAiPlan:
        del context
        return CityAiPlan(
            plan_id="city_vllm_taxi",
            source="vllm",
            confidence=0.94,
            summary="지호 택시 이동 후 하린 만남",
            actions=[
                CityAiAction(
                    type="call_taxi",
                    actor_id="c06",
                    vehicle_id="v01",
                    destination_actor_id="c05",
                    label="하린에게 이동",
                    reason="vLLM planned a taxi trip",
                ),
                CityAiAction(
                    type="meet",
                    actor_id="c06",
                    target_id="c05",
                    after="taxi_arrival",
                    reason="relationship starts after arrival",
                ),
            ],
        )


def test_city_ai_taxi_plan_executes_until_arrival() -> None:
    engine = SimulationEngine(city_planner=FakeTaxiCityPlanner())

    plan = engine.run_city_planner_once()
    state = WorldStatePayload.model_validate(engine.snapshot().model_dump())

    assert plan is not None
    assert state.vehicles[0].passenger_id == "c06"
    assert state.city_ai.actions[0].type == "call_taxi"
    assert any(
        event.metadata.get("deferred_until") == "taxi_arrival"
        for event in engine.timeline
    )

    engine.running = True
    for _ in range(280):
        engine.step()
    arrived_state = WorldStatePayload.model_validate(engine.snapshot().model_dump())
    jiho = next(citizen for citizen in arrived_state.citizens if citizen.id == "c06")
    harin = next(citizen for citizen in arrived_state.citizens if citizen.id == "c05")

    assert jiho.talking_to == "c05"
    assert harin.talking_to == "c06"
