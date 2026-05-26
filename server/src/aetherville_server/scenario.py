"""Bounded natural-language scenario compiler for presenter-driven city stories.

The compiler intentionally does not let prose mutate raw simulation state.
It turns Korean demo instructions into a small, inspectable ``ScenarioDirective``
step graph; ``SimulationEngine`` owns execution and safety boundaries.
"""

from __future__ import annotations

from collections.abc import Iterable
from typing import Literal, TypeAlias
from uuid import uuid4

from aetherville_schemas import (
    ScenarioDirective,
    ScenarioStep,
    TaskCondition,
    TaskEdge,
    TaskGraph,
    TaskGraphPlan,
    TaskNode,
)
from aetherville_server.orchestrator.command_handler import NAME_TO_CITIZEN_ID

ID_TO_NAME = {citizen_id: name for name, citizen_id in NAME_TO_CITIZEN_ID.items()}
ScenarioStepType: TypeAlias = Literal[
    "move_actor_to_actor",
    "move_actor_to_location",
    "meet",
    "call_taxi",
    "taxi_pickup",
    "taxi_drive_to_actor",
    "drone_move_to_actor",
    "drone_deliver",
    "move_actor_to_group",
    "group_rendezvous",
    "remember",
    "set_weather",
    "traffic_surge",
    "wait",
]

TaskNodeAction: TypeAlias = Literal[
    "move_actor_to_actor",
    "move_actor_to_location",
    "meet",
    "call_taxi",
    "taxi_pickup",
    "taxi_drive_to_actor",
    "drone_move_to_actor",
    "drone_deliver",
    "group_rendezvous",
    "set_weather",
    "traffic_surge",
    "remember",
    "wait",
    "no_op",
]

UNKNOWN_NAME_MARKERS = (
    "수빈",
    "철수",
    "영희",
    "준호",
    "하늘",
    "예린",
    "소라",
    "태민",
    "없는시민",
    "알수없는",
)

LOCATION_TARGETS: dict[str, list[float]] = {
    "광장": [0.0, 0.0, 0.0],
    "중앙광장": [0.0, 0.0, 0.0],
    "병원": [-5.2, 0.0, 4.6],
    "학교": [4.8, 0.0, 4.2],
    "역": [-4.8, 0.0, -4.8],
    "공원": [5.0, 0.0, -4.2],
}


def compile_task_graph_plan(raw_text: str, *, created_tick: int) -> TaskGraphPlan:
    """Compile presenter text into an inspectable bounded task graph.

    This deterministic planner is the safe fallback for Goal 12.  It is
    intentionally conservative: if it cannot identify actors or if the prompt
    asks for contradictory ordering, it returns a rejected/clarification graph
    rather than throwing or mutating simulation state.
    """

    text = " ".join(raw_text.strip().split())
    plan_id = f"task_plan_{uuid4().hex[:8]}"
    graph_id = f"task_graph_{uuid4().hex[:8]}"

    if not text:
        return _task_graph_plan(
            plan_id,
            graph_id,
            text,
            created_tick,
            status="rejected",
            title="빈 상황 명령",
            summary="실행할 자연어 상황이 비어 있습니다.",
            rejection_reason="empty command",
        )

    unknown = _unknown_names(text)
    if unknown:
        return _task_graph_plan(
            plan_id,
            graph_id,
            text,
            created_tick,
            status="rejected",
            title="알 수 없는 actor",
            summary=f"등록되지 않은 시민 이름: {', '.join(unknown)}",
            rejection_reason=f"unknown actors: {', '.join(unknown)}",
            assumptions=["등록된 시민만 실행 actor로 사용할 수 있습니다."],
        )

    if _looks_circular(text):
        return _task_graph_plan(
            plan_id,
            graph_id,
            text,
            created_tick,
            status="rejected",
            title="순환 의존성 감지",
            summary="서로 앞뒤가 모순되는 실행 순서가 있어 graph를 만들 수 없습니다.",
            rejection_reason="circular or contradictory dependency requested",
        )

    mentioned_ids = _mentioned_actor_ids(text)
    assumptions: list[str] = []
    nodes: list[TaskNode] = []

    if _mentions_rain(text):
        nodes.append(
            _node(
                "weather_rain",
                "set_weather",
                visible_label="도시에 비 적용",
                reason="프롬프트에 비/폭우가 포함되어 날씨를 먼저 고정합니다.",
                success_kind="weather_applied",
                metadata={"weather": "rain"},
            )
        )
    elif "눈" in text:
        nodes.append(
            _node(
                "weather_snow",
                "set_weather",
                visible_label="도시에 눈 적용",
                reason="프롬프트에 눈이 포함되어 날씨를 먼저 고정합니다.",
                success_kind="weather_applied",
                metadata={"weather": "snow"},
            )
        )

    if _mentions_traffic_surge(text):
        nodes.append(
            _node(
                "traffic_surge",
                "traffic_surge",
                visible_label="교통량 증가 적용",
                reason="교통량/정체 조건이 이후 차량 이동에 영향을 줍니다.",
                success_kind="traffic_applied",
            )
        )

    meeting_pair = _first_meeting_pair(text)
    if meeting_pair is None and any(marker in text for marker in ("만나", "만난", "만남", "합류")):
        meeting_pair, meeting_assumption = _default_meeting_pair(text, mentioned_ids)
        if meeting_assumption:
            assumptions.append(meeting_assumption)

    last_dependency: str | None = nodes[-1].id if nodes else None
    if meeting_pair is not None:
        actor_id, target_id = meeting_pair
        move_id = f"{actor_id}_to_{target_id}"
        nodes.append(
            _node(
                move_id,
                "move_actor_to_actor",
                actor_id=actor_id,
                target_actor_id=target_id,
                depends_on=[last_dependency] if last_dependency else [],
                visible_label=f"{ID_TO_NAME[actor_id]} → {ID_TO_NAME[target_id]} 이동",
                reason=(
                    f"{ID_TO_NAME[actor_id]}가 "
                    f"{ID_TO_NAME[target_id]}를 만나야 하므로 먼저 이동합니다."
                ),
            )
        )
        nodes.append(
            _node(
                f"meet_{actor_id}_{target_id}",
                "meet",
                actor_id=actor_id,
                target_actor_id=target_id,
                depends_on=[move_id],
                visible_label=f"{ID_TO_NAME[actor_id]}·{ID_TO_NAME[target_id]} 만남",
                reason="두 시민이 같은 지점에 도착한 뒤 관계/대화 상태를 활성화합니다.",
                success_kind="duration_elapsed",
            )
        )
        last_dependency = nodes[-1].id

    if meeting_pair is None and "택시" not in text:
        movement_pair = _movement_pair(text)
        if movement_pair is not None:
            actor_id, target_id = movement_pair
            move_id = f"{actor_id}_to_{target_id}"
            nodes.append(
                _node(
                    move_id,
                    "move_actor_to_actor",
                    actor_id=actor_id,
                    target_actor_id=target_id,
                    depends_on=[last_dependency] if last_dependency else [],
                    visible_label=f"{ID_TO_NAME[actor_id]} → {ID_TO_NAME[target_id]} 이동",
                    reason=(
                        f"{ID_TO_NAME[actor_id]}가 "
                        f"{ID_TO_NAME[target_id]} 방향으로 이동해야 합니다."
                    ),
                )
            )
            last_dependency = move_id
        elif (location_target := _location_target(text)) is not None:
            location_actor_id = (
                mentioned_ids[0] if mentioned_ids else _default_actor([], avoid=None)
            )
            if location_actor_id is not None:
                location_name, location = location_target
                move_id = f"{location_actor_id}_to_{location_name}"
                nodes.append(
                    _node(
                        move_id,
                        "move_actor_to_location",
                        actor_id=location_actor_id,
                        location=location,
                        depends_on=[last_dependency] if last_dependency else [],
                        visible_label=f"{ID_TO_NAME[location_actor_id]} → {location_name} 이동",
                        reason=(
                            f"{ID_TO_NAME[location_actor_id]}가 "
                            f"{location_name} 위치로 이동해야 합니다."
                        ),
                        metadata={"target_xz": [location[0], location[2]]},
                    )
                )
                last_dependency = move_id

    taxi_actor = _taxi_actor(text, mentioned_ids, meeting_pair)
    taxi_target = _taxi_target(text, taxi_actor, mentioned_ids)
    if "택시" in text and taxi_actor is None:
        taxi_actor = _default_actor(mentioned_ids, avoid=None)
        if taxi_actor:
            assumptions.append(
                f"택시 호출 actor가 모호해 "
                f"{ID_TO_NAME[taxi_actor]}를 기본 호출자로 선택했습니다."
            )
    if "택시" in text and taxi_actor is not None and taxi_target is None:
        taxi_target = _default_actor(mentioned_ids, avoid=taxi_actor)
        if taxi_target:
            assumptions.append(
                f"택시 목적지가 모호해 "
                f"{ID_TO_NAME[taxi_target]}를 기본 목적지로 선택했습니다."
            )
    if "택시" in text and taxi_actor is not None:
        call_id = f"taxi_call_{taxi_actor}_to_{taxi_target or 'location'}"
        nodes.append(
            _node(
                call_id,
                "call_taxi",
                actor_id=taxi_actor,
                target_actor_id=taxi_target,
                target_entity_id="v01",
                vehicle_id="v01",
                depends_on=[last_dependency] if last_dependency else [],
                visible_label=f"{ID_TO_NAME[taxi_actor]} 택시 호출",
                reason=f"{ID_TO_NAME[taxi_actor]}가 다음 이동을 위해 택시를 호출합니다.",
                success_kind="entity_exists",
            )
        )
        last_dependency = call_id
        if "픽업" in text:
            pickup_id = f"taxi_pickup_{taxi_actor}"
            nodes.append(
                _node(
                    pickup_id,
                    "taxi_pickup",
                    actor_id=taxi_actor,
                    target_actor_id=taxi_actor,
                    target_entity_id="v01",
                    vehicle_id="v01",
                    depends_on=[call_id],
                    visible_label=f"택시가 {ID_TO_NAME[taxi_actor]} 픽업",
                    reason=(
                        "프롬프트가 픽업 단계를 명시했으므로 "
                        "택시 접근 단계를 graph에 보존합니다."
                    ),
                )
            )
            last_dependency = pickup_id
        if taxi_target is not None:
            drive_id = f"taxi_drive_{taxi_actor}_to_{taxi_target}"
            nodes.append(
                _node(
                    drive_id,
                    "taxi_drive_to_actor",
                    actor_id=taxi_actor,
                    target_actor_id=taxi_target,
                    target_entity_id="v01",
                    vehicle_id="v01",
                    depends_on=[last_dependency],
                    visible_label=(
                        f"택시가 {ID_TO_NAME[taxi_actor]}를 "
                        f"{ID_TO_NAME[taxi_target]}에게 이동"
                    ),
                    reason="택시 이동은 호출/픽업 이후 목적 시민 근처 도착을 성공 조건으로 둡니다.",
                )
            )
            last_dependency = drive_id

    drone_target = _drone_target(text)
    if "드론" in text and drone_target is None:
        drone_target = _default_actor(mentioned_ids, avoid=taxi_actor)
        if drone_target:
            assumptions.append(
                f"드론 목적지가 모호해 "
                f"{ID_TO_NAME[drone_target]}를 기본 목적지로 선택했습니다."
            )
    if "드론" in text and drone_target is not None:
        drone_action: TaskNodeAction = (
            "drone_deliver"
            if any(m in text for m in ("전달", "배송"))
            else "drone_move_to_actor"
        )
        nodes.append(
            _node(
                f"drone_to_{drone_target}",
                drone_action,
                target_actor_id=drone_target,
                target_entity_id="d01",
                drone_id="d01",
                depends_on=[],
                visible_label=f"드론 → {ID_TO_NAME[drone_target]} 이동",
                reason=f"드론이 {ID_TO_NAME[drone_target]}에게 이동/전달해야 합니다.",
            )
        )

    group_move = _group_move(text, mentioned_ids, taxi_actor, taxi_target)
    if group_move is not None:
        actor_id, target_actor_ids = group_move
        depends_on = [node.id for node in nodes if node.id.startswith("drone_to_")]
        if last_dependency:
            depends_on.append(last_dependency)
        nodes.append(
            _node(
                f"{actor_id}_to_group",
                "group_rendezvous",
                actor_id=actor_id,
                target_actor_ids=target_actor_ids,
                depends_on=_unique(depends_on),
                visible_label=(
                    f"{ID_TO_NAME[actor_id]} → "
                    f"{'·'.join(ID_TO_NAME[target_id] for target_id in target_actor_ids)} 합류"
                ),
                reason=(
                    "여러 actor가 같은 상황에 합류해야 하므로 "
                    "group rendezvous 노드를 생성합니다."
                ),
            )
        )

    if "기억" in text:
        actor = mentioned_ids[0] if mentioned_ids else "c01"
        if not mentioned_ids:
            assumptions.append("기억 대상이 모호해 민지를 기본 memory actor로 선택했습니다.")
        nodes.append(
            _node(
                f"remember_{actor}",
                "remember",
                actor_id=actor,
                depends_on=[nodes[-1].id] if nodes else [],
                visible_label=f"{ID_TO_NAME[actor]} 기억 기록",
                reason="프롬프트가 시민 기억 반영을 요구했습니다.",
                success_kind="memory_recorded",
            )
        )

    if "기다" in text or "대기" in text:
        wait_actor = mentioned_ids[0] if mentioned_ids else None
        nodes.append(
            _node(
                f"wait_{wait_actor or 'city'}",
                "wait",
                actor_id=wait_actor,
                depends_on=[nodes[-1].id] if nodes else [],
                visible_label=(
                    f"{ID_TO_NAME[wait_actor]} 대기" if wait_actor else "도시 상태 대기"
                ),
                reason="프롬프트가 대기/기다림 상태를 요구했습니다.",
                success_kind="duration_elapsed",
            )
        )

    if any(marker in text for marker in ("아무것도", "그대로 둬", "변경하지")):
        nodes.append(
            _node(
                "no_op",
                "no_op",
                depends_on=[nodes[-1].id] if nodes else [],
                visible_label="상태 유지",
                reason="프롬프트가 변화 없는 안전 동작을 요구했습니다.",
                success_kind="none",
            )
        )

    if not nodes:
        return _task_graph_plan(
            plan_id,
            graph_id,
            text,
            created_tick,
            status="rejected",
            title="지원되지 않는 상황 명령",
            summary="bounded action vocabulary로 변환할 수 있는 도시 행동이 없습니다.",
            rejection_reason="no supported bounded action detected",
        )

    edges = [
        TaskEdge(
            from_node_id=dependency,
            to_node_id=node.id,
            relation="enables",
            description=f"{dependency} 완료 후 {node.id} 실행",
        )
        for node in nodes
        for dependency in node.depends_on
    ]
    actors = sorted(
        {
            actor_id
            for node in nodes
            for actor_id in [node.actor_id, node.target_actor_id, *node.target_actor_ids]
            if actor_id is not None
        }
    )
    graph = TaskGraph(
        id=graph_id,
        raw_text=text,
        title=_title_for_task_nodes(nodes),
        status="accepted" if not assumptions else "clarification_needed",
        nodes=nodes,
        edges=edges,
        actors=actors,
        assumptions=assumptions,
        summary=(
            f"{len(nodes)}개 task node: "
            + " → ".join(node.visible_label for node in nodes[:6])
        ),
    )
    return TaskGraphPlan(
        plan_id=plan_id,
        source="rules",
        confidence=0.72 if assumptions else 0.86,
        graph=graph,
        executor_step_ids=[node.id for node in nodes],
        created_tick=created_tick,
    )


def scenario_directive_from_task_graph(
    plan: TaskGraphPlan, *, created_tick: int
) -> ScenarioDirective | None:
    graph = plan.graph
    if graph.status not in {"accepted", "clarification_needed"}:
        return None
    steps: list[ScenarioStep] = []
    for node in graph.nodes:
        step = _scenario_step_from_task_node(node)
        if step is not None:
            steps.append(step)
    if len(steps) < 2:
        return None
    return ScenarioDirective(
        id=f"scenario_{uuid4().hex[:8]}",
        raw_text=graph.raw_text,
        title=graph.title,
        status="running",
        created_tick=created_tick,
        updated_tick=created_tick,
        current_step_id=None,
        actors=graph.actors,
        steps=steps,
        summary=graph.summary,
    )


def _task_graph_plan(
    plan_id: str,
    graph_id: str,
    text: str,
    created_tick: int,
    *,
    status: Literal["accepted", "clarification_needed", "rejected"],
    title: str,
    summary: str,
    rejection_reason: str | None = None,
    assumptions: list[str] | None = None,
) -> TaskGraphPlan:
    graph = TaskGraph(
        id=graph_id,
        raw_text=text,
        title=title,
        status=status,
        nodes=[],
        edges=[],
        actors=[],
        assumptions=assumptions or [],
        rejection_reason=rejection_reason,
        summary=summary,
    )
    return TaskGraphPlan(
        plan_id=plan_id,
        source="rules",
        confidence=0.0 if status == "rejected" else 0.45,
        graph=graph,
        executor_step_ids=[],
        created_tick=created_tick,
    )


def _node(
    node_id: str,
    action_type: TaskNodeAction,
    *,
    visible_label: str,
    reason: str,
    actor_id: str | None = None,
    actor_selector: str | None = None,
    target_actor_id: str | None = None,
    target_actor_ids: list[str] | None = None,
    target_entity_id: str | None = None,
    target_selector: str | None = None,
    vehicle_id: str | None = None,
    drone_id: str | None = None,
    location: list[float] | None = None,
    depends_on: list[str] | None = None,
    success_kind: Literal[
        "entity_exists",
        "dependency_completed",
        "distance_less_than",
        "duration_elapsed",
        "weather_applied",
        "traffic_applied",
        "memory_recorded",
        "manual_review",
        "none",
    ] = "distance_less_than",
    metadata: dict[str, object] | None = None,
) -> TaskNode:
    timeout = (
        80
        if action_type in {"set_weather", "traffic_surge", "remember", "wait"}
        else 360
    )
    return TaskNode(
        id=node_id,
        action_type=action_type,
        actor_id=actor_id,
        actor_selector=actor_selector,
        target_actor_id=target_actor_id,
        target_actor_ids=target_actor_ids or [],
        target_entity_id=target_entity_id,
        target_selector=target_selector,
        vehicle_id=vehicle_id,
        drone_id=drone_id,
        location=location,
        depends_on=depends_on or [],
        success_condition=TaskCondition(
            kind=success_kind,
            description=f"성공 조건: {visible_label}",
            entity_id=actor_id or vehicle_id or drone_id or target_entity_id,
            target_id=target_actor_id or target_entity_id,
            threshold=0.55 if success_kind == "distance_less_than" else None,
            timeout_ticks=timeout,
        ),
        failure_condition=TaskCondition(
            kind="manual_review",
            description=f"{timeout} tick 안에 완료되지 않으면 replan 후보가 됩니다.",
            entity_id=actor_id or vehicle_id or drone_id or target_entity_id,
            target_id=target_actor_id or target_entity_id,
            timeout_ticks=timeout,
        ),
        timeout_ticks=timeout,
        retry_limit=1,
        reason=reason,
        visible_label=visible_label,
        metadata=metadata or {},
    )


def _scenario_step_from_task_node(node: TaskNode) -> ScenarioStep | None:
    action = node.action_type
    step_type: ScenarioStepType | None
    if action == "group_rendezvous":
        step_type = "move_actor_to_group"
    elif action == "drone_deliver":
        step_type = "drone_move_to_actor"
    elif action == "taxi_pickup":
        step_type = "call_taxi"
    elif action in {
        "move_actor_to_actor",
        "move_actor_to_location",
        "meet",
        "call_taxi",
        "taxi_drive_to_actor",
        "drone_move_to_actor",
        "remember",
        "set_weather",
        "traffic_surge",
        "wait",
    }:
        step_type = action  # type: ignore[assignment]
    else:
        step_type = None
    if step_type is None:
        return None
    return _step(
        node.id,
        step_type,
        actor_id=node.actor_id,
        target_actor_id=node.target_actor_id,
        target_actor_ids=node.target_actor_ids,
        vehicle_id=node.vehicle_id,
        drone_id=node.drone_id,
        depends_on=node.depends_on,
        visible_label=node.visible_label,
        metadata={
            **node.metadata,
            "task_node_id": node.id,
            "task_action_type": node.action_type,
            "timeout_ticks": node.timeout_ticks,
            "retry_limit": node.retry_limit,
            **(
                {"target_xz": [node.location[0], node.location[2]]}
                if node.location is not None
                else {}
            ),
        },
    )



def compile_scenario_directive(raw_text: str, *, created_tick: int) -> ScenarioDirective | None:
    """Compile a multi-actor God Mode situation into deterministic steps.

    Scenario execution now routes through the Goal 12 TaskGraph planner.  Simple
    one-effect commands still use normal God Mode effects, but complex commands
    become graph-backed ScenarioDirectives.
    """

    text = " ".join(raw_text.strip().split())
    if not text:
        return None

    action_count = _action_count(text)
    mentioned_ids = _mentioned_actor_ids(text)
    complex_markers = ("뒤", "그리고", "드론", "만나러", "합류", "픽업", "전달", "배송")
    is_complex = not (action_count < 2 and len(mentioned_ids) < 3) and (
        len(mentioned_ids) >= 3 or any(marker in text for marker in complex_markers)
    )
    if not is_complex:
        return None

    plan = compile_task_graph_plan(text, created_tick=created_tick)
    return scenario_directive_from_task_graph(plan, created_tick=created_tick)

def _step(
    step_id: str,
    step_type: ScenarioStepType,
    *,
    visible_label: str,
    actor_id: str | None = None,
    target_actor_id: str | None = None,
    target_actor_ids: list[str] | None = None,
    vehicle_id: str | None = None,
    drone_id: str | None = None,
    depends_on: list[str] | None = None,
    metadata: dict[str, object] | None = None,
) -> ScenarioStep:
    return ScenarioStep(
        id=step_id,
        type=step_type,
        actor_id=actor_id,
        target_actor_id=target_actor_id,
        target_actor_ids=target_actor_ids or [],
        vehicle_id=vehicle_id,
        drone_id=drone_id,
        depends_on=depends_on or [],
        visible_label=visible_label,
        metadata=metadata or {},
    )


def _mentioned_actor_ids(text: str) -> list[str]:
    return [citizen_id for name, citizen_id in NAME_TO_CITIZEN_ID.items() if name in text]


def _action_count(text: str) -> int:
    markers = [
        "만나",
        "만난",
        "택시",
        "드론",
        "이동",
        "간다",
        "가고",
        "비",
        "눈",
        "교통량",
        "정체",
        "기억",
        "뒤",
        "그리고",
    ]
    return sum(1 for marker in markers if marker in text)


def _mentions_rain(text: str) -> bool:
    return "비" in text or "폭우" in text or "rain" in text.lower()


def _mentions_traffic_surge(text: str) -> bool:
    return any(marker in text for marker in ("교통량", "정체", "혼잡", "차량 많"))


def _first_meeting_pair(text: str) -> tuple[str, str] | None:
    before_taxi = text.split("택시", maxsplit=1)[0]
    if "만나" not in before_taxi and "만난" not in before_taxi:
        return None

    names = _names_in_order(before_taxi)
    if len(names) >= 2:
        return NAME_TO_CITIZEN_ID[names[0]], NAME_TO_CITIZEN_ID[names[1]]
    return None


def _taxi_actor(
    text: str,
    mentioned_ids: list[str],
    first_meeting: tuple[str, str] | None,
) -> str | None:
    if "택시" not in text:
        return None
    if first_meeting is not None:
        return first_meeting[0]
    before_taxi = text.split("택시", maxsplit=1)[0]
    names_before = _names_in_order(before_taxi)
    if names_before:
        return NAME_TO_CITIZEN_ID[names_before[-1]]
    if first_meeting is not None:
        return first_meeting[0]
    return mentioned_ids[0] if mentioned_ids else None


def _taxi_target(text: str, taxi_actor: str | None, mentioned_ids: list[str]) -> str | None:
    if taxi_actor is None or "택시" not in text:
        return None
    after_taxi = text.split("택시", maxsplit=1)[1]
    names_after = [
        NAME_TO_CITIZEN_ID[name]
        for name in _names_in_order(after_taxi)
        if NAME_TO_CITIZEN_ID[name] != taxi_actor
    ]
    if names_after:
        return names_after[0]
    for citizen_id in mentioned_ids:
        if citizen_id != taxi_actor:
            return citizen_id
    return None


def _movement_pair(text: str) -> tuple[str, str] | None:
    if not any(marker in text for marker in ("이동", "걸어", "간다", "가고")):
        return None
    segment = text
    for delimiter in ("전달하고", "배송하고", "그리고", "뒤"):
        if delimiter in segment:
            segment = segment.split(delimiter, maxsplit=1)[1]
    names = _names_in_order(segment)
    if len(names) >= 2:
        return NAME_TO_CITIZEN_ID[names[0]], NAME_TO_CITIZEN_ID[names[1]]
    return None


def _location_target(text: str) -> tuple[str, list[float]] | None:
    for name, location in LOCATION_TARGETS.items():
        if name in text:
            return name, location
    return None


def _drone_target(text: str) -> str | None:
    if "드론" not in text:
        return None
    after_drone = text.split("드론", maxsplit=1)[1]
    names = _names_in_order(after_drone)
    return NAME_TO_CITIZEN_ID[names[0]] if names else None


def _group_move(
    text: str,
    mentioned_ids: list[str],
    taxi_actor: str | None,
    taxi_target: str | None,
) -> tuple[str, list[str]] | None:
    if "만나러" not in text and "합류" not in text:
        return None
    if "서연" in text and {"c01", "c02"}.issubset(set(mentioned_ids)):
        return "c03", ["c01", "c02"]
    if len(mentioned_ids) >= 3:
        actor_id = mentioned_ids[-1]
        targets = [
            target_id
            for target_id in (taxi_target, taxi_actor, *mentioned_ids)
            if target_id != actor_id
        ]
        return actor_id, _unique(targets)[:2]
    return None


def _names_in_order(text: str) -> list[str]:
    positions = [
        (text.find(name), name)
        for name in NAME_TO_CITIZEN_ID
        if name in text
    ]
    return [name for _position, name in sorted(positions)]


def _unique(values: Iterable[str | None]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        if value is None or value in seen:
            continue
        seen.add(value)
        result.append(value)
    return result



def _unknown_names(text: str) -> list[str]:
    return [
        name
        for name in UNKNOWN_NAME_MARKERS
        if name in text and name not in NAME_TO_CITIZEN_ID
    ]


def _looks_circular(text: str) -> bool:
    lowered = text.lower()
    return (
        "순환" in text
        or "circular" in lowered
        or ("전에" in text and "뒤" in text and "동시에" in text)
    )


def _default_actor(mentioned_ids: list[str], *, avoid: str | None) -> str | None:
    for candidate in mentioned_ids:
        if candidate != avoid:
            return candidate
    for candidate in ("c02", "c01", "c03", "c05"):
        if candidate != avoid:
            return candidate
    return None


def _default_meeting_pair(
    text: str, mentioned_ids: list[str]
) -> tuple[tuple[str, str] | None, str | None]:
    if len(mentioned_ids) >= 2:
        return (mentioned_ids[0], mentioned_ids[1]), None
    if len(mentioned_ids) == 1:
        target = mentioned_ids[0]
        actor = _default_actor([], avoid=target)
        if actor is None:
            return None, None
        return (
            (actor, target),
            f"만남 주체가 모호해 {ID_TO_NAME[actor]}를 기본 actor로 선택했습니다.",
        )
    if any(marker in text for marker in ("누군가", "어떤 시민", "시민")):
        return ("c02", "c01"), "actor와 target이 모호해 민수→민지 기본 만남으로 해석했습니다."
    return None, None


def _title_for_task_nodes(nodes: list[TaskNode]) -> str:
    actions = {node.action_type for node in nodes}
    has_taxi = "taxi_drive_to_actor" in actions
    has_drone = "drone_move_to_actor" in actions or "drone_deliver" in actions
    if has_taxi and has_drone:
        return "TaskGraph 택시·드론 복합 시나리오"
    if "group_rendezvous" in actions:
        return "TaskGraph 그룹 합류 시나리오"
    if "taxi_drive_to_actor" in actions or "call_taxi" in actions:
        return "TaskGraph 택시 이동 시나리오"
    if "drone_move_to_actor" in actions or "drone_deliver" in actions:
        return "TaskGraph 드론 시나리오"
    if "meet" in actions:
        return "TaskGraph 시민 만남 시나리오"
    return "TaskGraph 도시 상황 계획"


def _title_for_steps(steps: list[ScenarioStep]) -> str:
    if any(step.type == "taxi_drive_to_actor" for step in steps):
        return "택시·시민·드론 연쇄 시나리오"
    if any(step.type == "drone_move_to_actor" for step in steps):
        return "드론 합류 시나리오"
    return "AI 상황 디렉터 시나리오"
