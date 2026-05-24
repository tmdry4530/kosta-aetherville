from __future__ import annotations

from aetherville_schemas import GodCommand
from aetherville_server.orchestrator import GodCommandDispatcher


def command(text: str) -> GodCommand:
    return GodCommand(input_modality="text", raw_text=text, user_id="presenter")


def test_dispatcher_supports_required_categories() -> None:
    dispatcher = GodCommandDispatcher()

    assert dispatcher.dispatch(command("도시에 비를 내려줘")).category == "environment"
    assert dispatcher.dispatch(command("도시에 축제 이벤트를 만들어줘")).category == "event"
    assert dispatcher.dispatch(command("민준에게 중요한 기억을 줘")).category == "person"
    assert dispatcher.dispatch(command("동쪽 도로 정체를 만들어줘")).category == "infrastructure"
    relationship = dispatcher.dispatch(command("민준과 서연의 관계를 친구로 바꿔줘"))
    assert relationship.category == "relationship"


def test_person_and_relationship_commands_inject_memories() -> None:
    dispatcher = GodCommandDispatcher()

    person = dispatcher.dispatch(command("민준에게 중요한 기억을 줘"))
    relationship = dispatcher.dispatch(command("민준과 서연의 관계를 친구로 바꿔줘"))

    assert person.memories[0].citizen_id == "c01"
    assert {memory.citizen_id for memory in relationship.memories} == {"c01", "c02"}
