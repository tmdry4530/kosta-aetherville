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
    traffic_surge = dispatcher.dispatch(command("교통량 증가시켜"))
    assert traffic_surge.category == "infrastructure"
    assert traffic_surge.event.metadata["action"] == "traffic_jam"
    assert dispatcher.dispatch(command("민지가 택시를 불러줘")).event.kind == "trip_requested"
    relationship = dispatcher.dispatch(command("민지랑 민수가 만난다"))
    assert relationship.category == "relationship"
    assert relationship.event.metadata["action"] == "meeting"
    assert relationship.event.metadata["target"] == "c02"


def test_person_and_relationship_commands_inject_memories() -> None:
    dispatcher = GodCommandDispatcher()

    person = dispatcher.dispatch(command("민준에게 중요한 기억을 줘"))
    relationship = dispatcher.dispatch(command("민지랑 민수가 만난다"))

    assert person.memories[0].citizen_id == "c07"
    assert {memory.citizen_id for memory in relationship.memories} == {"c01", "c02"}
