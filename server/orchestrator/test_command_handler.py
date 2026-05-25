from __future__ import annotations

from aetherville_schemas import GodCommand
from aetherville_server.orchestrator import GodCommandDispatcher
from aetherville_server.orchestrator.vllm_command import (
    GodCommandInterpretation,
    _interpret_payload,
)


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


def test_taxi_command_uses_text_order_for_passenger_and_destination() -> None:
    dispatcher = GodCommandDispatcher()

    effect = dispatcher.dispatch(command("지호가 택시를 부르고, 하린에게 간다"))

    assert effect.event.kind == "trip_requested"
    assert effect.event.metadata["passenger_id"] == "c06"
    assert effect.event.metadata["passenger_name"] == "지호"
    assert effect.event.metadata["destination_citizen_id"] == "c05"
    assert effect.event.metadata["destination_citizen_name"] == "하린"


class FakeInterpreter:
    def __init__(self, interpretation: GodCommandInterpretation | None) -> None:
        self.interpretation = interpretation

    def interpret(self, command: GodCommand) -> GodCommandInterpretation | None:
        del command
        return self.interpretation


def test_vllm_interpretation_is_constrained_before_effects() -> None:
    interpretation = _interpret_payload(
        {
            "category": "anything",
            "action": "traffic_jam",
            "target": "east road",
            "confidence": 0.91,
            "reason": "Presenter asks for more traffic",
        }
    )

    assert interpretation is not None
    assert interpretation.category == "infrastructure"
    assert interpretation.action == "traffic_jam"
    assert interpretation.confidence == 0.91


def test_dispatcher_can_use_vllm_interpretation_without_unbounded_effects() -> None:
    dispatcher = GodCommandDispatcher(
        interpreter=FakeInterpreter(
            GodCommandInterpretation(
                category="infrastructure",
                action="traffic_jam",
                target="east road",
                confidence=0.88,
                reason="The command asks for congestion",
            )
        )
    )

    effect = dispatcher.dispatch(command("출근길을 훨씬 더 답답하게 만들어줘"))

    assert effect.category == "infrastructure"
    assert effect.ai_mode == "vllm"
    assert effect.ai_confidence == 0.88
    assert effect.event.metadata["action"] == "traffic_jam"
    assert effect.event.metadata["ai_mode"] == "vllm"


def test_dispatcher_falls_back_to_rules_when_vllm_interpretation_missing() -> None:
    dispatcher = GodCommandDispatcher(interpreter=FakeInterpreter(None))

    effect = dispatcher.dispatch(command("도시에 비를 내려줘"))

    assert effect.category == "environment"
    assert effect.ai_mode == "rules"
    assert effect.event.metadata["ai_mode"] == "rules"


def test_vllm_interpretation_accepts_bounded_multi_action_plan() -> None:
    interpretation = _interpret_payload(
        {
            "category": "event",
            "action": "rain",
            "actions": ["rain", "traffic_jam", "taxi_call", "meeting", "snow"],
            "target": "city demo",
            "confidence": 0.84,
            "reason": "Presenter requested a combined scene",
        }
    )

    assert interpretation is not None
    assert interpretation.actions == ("rain", "traffic_jam", "taxi_call", "meeting")
    assert interpretation.category == "environment"


def test_dispatcher_builds_multi_effect_from_vllm_plan() -> None:
    dispatcher = GodCommandDispatcher(
        interpreter=FakeInterpreter(
            GodCommandInterpretation(
                category="environment",
                action="rain",
                secondary_actions=("traffic_jam", "taxi_call", "meeting"),
                target="city demo",
                confidence=0.9,
                reason="multi-scene direction",
            )
        )
    )

    effect = dispatcher.dispatch(command("비 오게 하고 민지가 택시를 부르고 도로가 막혀 있게 해줘"))

    assert effect.event.kind == "god_command_executed"
    assert effect.event.metadata["action"] == "multi_action"
    assert effect.ai_actions == ("rain", "traffic_jam", "taxi_call", "meeting")
    assert [child.event.metadata["action"] for child in effect.sub_effects] == [
        "rain",
        "traffic_jam",
        "taxi_call",
        "meeting",
    ]
    assert all(child.event.metadata["ai_mode"] == "vllm" for child in effect.sub_effects)


def test_rules_path_supports_multi_action_demo_macro() -> None:
    dispatcher = GodCommandDispatcher(interpreter=FakeInterpreter(None))

    effect = dispatcher.dispatch(command("비 오고 민지가 택시를 부르고 교통량도 증가시켜"))

    assert effect.ai_mode == "rules"
    assert effect.ai_actions == ("rain", "traffic_jam", "taxi_call")
    assert effect.event.metadata["action"] == "multi_action"
