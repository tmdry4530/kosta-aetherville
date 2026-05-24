from __future__ import annotations

from aetherville_schemas import GodCommand, WorldStatePayload
from aetherville_server.sim import SimulationEngine


def make_command(text: str) -> GodCommand:
    return GodCommand(input_modality="text", raw_text=text, user_id="presenter")


def test_text_god_command_changes_weather_and_world_state() -> None:
    engine = SimulationEngine()

    response = engine.execute_god_command(make_command("도시에 비를 내려줘"))
    state = WorldStatePayload.model_validate(engine.snapshot().model_dump())

    assert response.category == "environment"
    assert state.world.weather == "rain"
    assert state.world.active_event == "weather:rain"
    assert response.envelopes


def test_person_and_relationship_commands_inject_memory_events() -> None:
    engine = SimulationEngine()

    person = engine.execute_god_command(make_command("민준에게 오늘 일을 기억시켜줘"))
    relationship = engine.execute_god_command(make_command("민준과 서연의 관계를 친구로 바꿔줘"))

    assert person.category == "person"
    assert relationship.category == "relationship"
    assert any(event.kind == "memory_added" for event in person.events)
    assert sum(event.kind == "memory_added" for event in relationship.events) == 2


def test_infrastructure_command_has_visible_world_effect() -> None:
    engine = SimulationEngine()

    response = engine.execute_god_command(make_command("동쪽 도로 정체를 만들어줘"))
    state = WorldStatePayload.model_validate(engine.snapshot().model_dump())

    assert response.category == "infrastructure"
    assert state.world.infrastructure_status == "reroute active"
