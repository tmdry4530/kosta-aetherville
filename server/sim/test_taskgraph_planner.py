from __future__ import annotations

import pytest

from aetherville_schemas import GodCommand, TaskGraphPlan, WorldStatePayload
from aetherville_server.scenario import (
    compile_task_graph_plan,
    scenario_directive_from_task_graph,
)
from aetherville_server.sim import SimulationEngine


def make_command(text: str) -> GodCommand:
    return GodCommand(input_modality="text", raw_text=text, user_id="presenter")


TASKGRAPH_FIXTURES = [
    (
        "simple citizen meeting",
        "민지랑 민수가 만난다",
        "accepted",
        {"move_actor_to_actor", "meet"},
    ),
    (
        "citizen meeting then taxi trip",
        "민수가 하린이를 만난 뒤 택시를 불러 민지에게 간다",
        "accepted",
        {"move_actor_to_actor", "meet", "call_taxi", "taxi_drive_to_actor"},
    ),
    (
        "taxi trip then group rendezvous",
        "지호가 택시로 하린에게 간 뒤 서연과 민지를 만나러 간다",
        "accepted",
        {"call_taxi", "taxi_drive_to_actor", "group_rendezvous"},
    ),
    (
        "drone delivery plus citizen movement",
        "드론은 서연에게 의료키트를 전달하고 민수는 민지에게 이동한다",
        "accepted",
        {"drone_deliver", "move_actor_to_actor"},
    ),
    (
        "rain causing taxi delay",
        "비가 오면 민지가 택시를 불러 민수에게 간다",
        "accepted",
        {"set_weather", "call_taxi", "taxi_drive_to_actor"},
    ),
    (
        "traffic surge causing vehicle slowdown",
        "교통량이 증가하고 지호가 택시를 불러 하린에게 간다",
        "accepted",
        {"traffic_surge", "call_taxi", "taxi_drive_to_actor"},
    ),
    (
        "unknown citizen name",
        "수빈이 민지를 만난다",
        "rejected",
        set(),
    ),
    (
        "duplicate or ambiguous target",
        "누군가 민지를 만나러 간다",
        "clarification_needed",
        {"move_actor_to_actor", "meet"},
    ),
    (
        "impossible circular ordering",
        "민수가 하린을 만난 뒤 동시에 만나기 전에 순환 계획을 실행한다",
        "rejected",
        set(),
    ),
    (
        "long chained audience command",
        (
            "민수가 하린이를 만난 뒤 택시를 불러 민지에게 가고, "
            "드론은 서연에게 이동한 뒤 서연은 민지와 민수를 만나러 간다"
        ),
        "accepted",
        {
            "move_actor_to_actor",
            "meet",
            "call_taxi",
            "taxi_drive_to_actor",
            "drone_move_to_actor",
            "group_rendezvous",
        },
    ),
]


@pytest.mark.parametrize(("name", "text", "status", "required_actions"), TASKGRAPH_FIXTURES)
def test_korean_fixture_compiles_to_task_graph_plan(
    name: str,
    text: str,
    status: str,
    required_actions: set[str],
) -> None:
    plan = compile_task_graph_plan(text, created_tick=12)
    actions = {node.action_type for node in plan.graph.nodes}

    assert isinstance(plan, TaskGraphPlan), name
    assert plan.graph.status == status
    assert required_actions.issubset(actions)
    assert plan.created_tick == 12
    assert plan.graph.raw_text == " ".join(text.split())
    assert len(plan.executor_step_ids) == len(plan.graph.nodes)
    if status == "rejected":
        assert plan.graph.rejection_reason
    else:
        assert not plan.graph.rejection_reason
        for node in plan.graph.nodes:
            assert node.id
            assert node.success_condition.description
            assert node.failure_condition.description
            assert node.timeout_ticks > 0
            assert node.retry_limit >= 0
            assert node.reason
            assert node.status == "pending"


def test_ambiguous_fixture_records_safe_default_assumption() -> None:
    plan = compile_task_graph_plan("누군가 민지를 만나러 간다", created_tick=3)

    assert plan.graph.status == "clarification_needed"
    assert plan.graph.assumptions
    assert plan.graph.nodes[0].actor_id == "c02"
    assert plan.graph.nodes[0].target_actor_id == "c01"


def test_location_wait_and_no_op_actions_are_bounded() -> None:
    location = compile_task_graph_plan("민수가 중앙광장으로 이동한다", created_tick=0)
    wait = compile_task_graph_plan("민지가 잠시 기다린다", created_tick=0)
    no_op = compile_task_graph_plan("도시는 그대로 둬 아무것도 하지마", created_tick=0)

    assert [node.action_type for node in location.graph.nodes] == ["move_actor_to_location"]
    assert location.graph.nodes[0].location == [0.0, 0.0, 0.0]
    assert [node.action_type for node in wait.graph.nodes] == ["wait"]
    assert [node.action_type for node in no_op.graph.nodes] == ["no_op"]


def test_existing_complex_scenario_director_uses_task_graph_path() -> None:
    text = (
        "민수가 하린이를 만난 뒤 택시를 불러 민지에게 가고, "
        "드론은 서연에게 이동한 뒤 서연은 민지와 민수를 만나러 간다"
    )
    plan = compile_task_graph_plan(text, created_tick=0)
    scenario = scenario_directive_from_task_graph(plan, created_tick=0)

    assert scenario is not None
    assert [step.type for step in scenario.steps] == [
        "move_actor_to_actor",
        "meet",
        "call_taxi",
        "taxi_drive_to_actor",
        "drone_move_to_actor",
        "move_actor_to_group",
    ]
    assert all(step.metadata.get("task_node_id") for step in scenario.steps)


def test_god_command_response_and_world_state_expose_task_graph_snapshot() -> None:
    engine = SimulationEngine()
    engine.running = True

    response = engine.execute_god_command(
        make_command(
            "민수가 하린이를 만난 뒤 택시를 불러 민지에게 가고, "
            "드론은 서연에게 이동한 뒤 서연은 민지와 민수를 만나러 간다"
        )
    )
    state = WorldStatePayload.model_validate(engine.snapshot().model_dump(mode="json"))

    assert response.accepted is True
    assert response.task_graph is not None
    assert response.scenario is not None
    assert response.events[0].kind == "task_graph_planned"
    assert state.task_graph is not None
    assert state.task_graph.status == "running"
    assert state.task_graph.total_count == len(response.task_graph.graph.nodes)

    for _ in range(720):
        engine.step()
    final_state = WorldStatePayload.model_validate(engine.snapshot().model_dump(mode="json"))

    assert final_state.task_graph is not None
    assert final_state.task_graph.status == "completed"
    assert final_state.task_graph.completed_count == final_state.task_graph.total_count


def test_unknown_actor_is_rejected_without_crashing_runtime() -> None:
    engine = SimulationEngine()

    response = engine.execute_god_command(make_command("수빈이 민지를 만난다"))
    state = WorldStatePayload.model_validate(engine.snapshot().model_dump(mode="json"))

    assert response.accepted is False
    assert response.task_graph is not None
    assert response.task_graph.graph.status == "rejected"
    assert "unknown actors" in (response.task_graph_rejection_reason or "")
    assert response.event.kind == "task_graph_rejected"
    assert state.task_graph is not None
    assert state.task_graph.status == "rejected"


def test_simple_god_mode_command_keeps_old_effect_and_exposes_completed_graph() -> None:
    engine = SimulationEngine()

    response = engine.execute_god_command(make_command("민지랑 민수가 만난다"))
    state = WorldStatePayload.model_validate(engine.snapshot().model_dump(mode="json"))
    minji = next(citizen for citizen in state.citizens if citizen.id == "c01")
    minsu = next(citizen for citizen in state.citizens if citizen.id == "c02")

    assert response.category == "relationship"
    assert response.task_graph is not None
    assert response.task_graph.graph.status == "completed"
    assert state.task_graph is not None
    assert state.task_graph.status == "completed"
    assert {node.action_type for node in state.task_graph.nodes} == {
        "move_actor_to_actor",
        "meet",
    }
    assert minji.talking_to == minsu.id
    assert minsu.talking_to == minji.id


def test_world_state_exposes_entity_brains_for_task_graph_vehicle_and_drone() -> None:
    engine = SimulationEngine()
    engine.running = True

    engine.execute_god_command(
        make_command(
            "민수가 하린이를 만난 뒤 택시를 불러 민지에게 가고, "
            "드론은 서연에게 이동한 뒤 서연은 민지와 민수를 만나러 간다"
        )
    )
    for _ in range(4):
        engine.step()
    state = WorldStatePayload.model_validate(engine.snapshot().model_dump(mode="json"))
    brains = {brain.entity_id: brain for brain in state.entity_brains}

    assert {"c01", "c02", "v01", "d01"}.issubset(brains)
    assert brains["c02"].current_goal.title
    assert brains["v01"].entity_type == "taxi"
    assert brains["d01"].next_action in {"drone_move_to_actor", "hold_or_move_to_destination"}
    assert all(brain.reason for brain in brains.values())


def test_city_ai_plan_updates_entity_brain_state() -> None:
    from aetherville_schemas import CityAiAction, CityAiPlan, CityWorldContext

    class BrainPlanner:
        source = "vllm"

        def plan(self, context: CityWorldContext) -> CityAiPlan:
            assert context.citizens
            return CityAiPlan(
                plan_id="brain_city_plan",
                source="vllm",
                summary="서연이 민지에게 이동",
                actions=[
                    CityAiAction(
                        type="move_citizen",
                        actor_id="c03",
                        destination_actor_id="c01",
                        label="민지에게 자율 이동",
                        reason="vLLM bounded plan selected c03 social movement",
                    )
                ],
            )

    engine = SimulationEngine(city_planner=BrainPlanner())
    engine.run_city_planner_once()
    state = WorldStatePayload.model_validate(engine.snapshot().model_dump(mode="json"))
    seoyeon_brain = next(brain for brain in state.entity_brains if brain.entity_id == "c03")

    assert seoyeon_brain.source == "city_ai"
    assert seoyeon_brain.status in {"moving", "waiting"}
    assert "vLLM bounded plan" in seoyeon_brain.reason or state.city_ai.summary


@pytest.mark.parametrize(
    "blocker_type",
    [
        "stuck_actor",
        "stuck_vehicle",
        "target_unreachable",
        "taxi_unavailable",
        "pickup_timeout",
        "group_timeout",
        "drone_delay",
        "low_battery",
        "traffic_delay",
        "dependency_deadlock",
    ],
)
def test_forced_replanner_blockers_emit_recovery_events(blocker_type: str) -> None:
    engine = SimulationEngine()
    engine.running = True
    engine.force_replanner_blocker(blocker_type)
    engine.execute_god_command(
        make_command(
            "민수가 하린이를 만난 뒤 택시를 불러 민지에게 가고, "
            "드론은 서연에게 이동한 뒤 서연은 민지와 민수를 만나러 간다"
        )
    )

    for _ in range(8):
        engine.step()

    state = WorldStatePayload.model_validate(engine.snapshot().model_dump(mode="json"))
    event_kinds = [event.kind for event in engine.timeline]

    assert "task_blocked" in event_kinds
    assert "task_replanned" in event_kinds
    assert "task_recovered" in event_kinds
    assert any(record.blocker_type == blocker_type for record in state.replans)
    assert state.learning.evolution.replan_count >= 1
    assert state.learning.evolution.fallback_path_usage >= 1


def test_replanner_and_learning_state_keep_complex_scenario_moving() -> None:
    engine = SimulationEngine()
    engine.running = True
    engine.force_replanner_blocker("traffic_delay")
    engine.execute_god_command(
        make_command(
            "민수가 하린이를 만난 뒤 택시를 불러 민지에게 가고, "
            "드론은 서연에게 이동한 뒤 서연은 민지와 민수를 만나러 간다"
        )
    )

    for _ in range(720):
        engine.step()
    state = WorldStatePayload.model_validate(engine.snapshot().model_dump(mode="json"))

    assert state.scenario is not None
    assert state.scenario.status == "completed"
    assert state.learning.trajectory_events
    assert state.learning.outcome_scores
    assert any(signal.kind == "fallback_path" for signal in state.learning.signals)
    assert state.learning.evolution.scenario_success_count >= 1
    assert state.learning.evolution.scenario_failure_count >= 1
