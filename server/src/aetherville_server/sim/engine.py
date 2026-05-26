"""Deterministic simulation engine for the first playable Aetherville slice."""

from __future__ import annotations

import asyncio
import math
import os
import random
import time
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Literal, cast
from uuid import uuid4

from aetherville_schemas import (
    CitizenState,
    CityActorContext,
    CityAiAction,
    CityAiPlan,
    CityAiSnapshot,
    CityTrafficContext,
    CityWorldContext,
    DroneState,
    EntityBlocker,
    EntityBrainState,
    EntityConstraint,
    EntityGoal,
    EntityProgress,
    Envelope,
    EnvelopeType,
    EventPayload,
    GodCommand,
    GodCommandResponse,
    LearningStatusResponse,
    ReplanRecord,
    ScenarioDirective,
    ScenarioStep,
    SimStatusResponse,
    TaskGraphExecutionSnapshot,
    TaskGraphPlan,
    TaskNode,
    TrafficAiSnapshot,
    TrafficLightState,
    VehicleCameraFrame,
    VehicleState,
    WorldClock,
    WorldStatePayload,
    make_state_update,
)
from aetherville_server.agents import CitizenAgentService
from aetherville_server.city_ai import CityPlanner, city_planner_from_env
from aetherville_server.learning import LearningStore
from aetherville_server.llm import planner_from_env
from aetherville_server.orchestrator import GodCommandDispatcher
from aetherville_server.scenario import compile_scenario_directive, compile_task_graph_plan
from aetherville_server.traffic_ai import (
    FixedCycleController,
    LstmForecastWrapper,
    TrafficPolicyWrapper,
)
from aetherville_server.vehicles import VehicleController

BroadcastCallback = Callable[[Envelope], Awaitable[None]]


@dataclass(frozen=True)
class SimulationConfig:
    tick_rate_hz: float = 10.0
    seed: int = 42
    start_minute: int = 9 * 60 + 30
    visible_citizen_count: int = 7


@dataclass(frozen=True)
class PendingTaxiMeeting:
    passenger_id: str
    target_id: str


@dataclass(frozen=True)
class DroneDirective:
    drone_id: str
    start_xz: tuple[float, float]
    target_xz: tuple[float, float]
    label: str
    requested_tick: int
    hold_until_tick: int


class SimulationEngine:
    """Small deterministic world model with a configurable async tick loop."""

    def __init__(
        self,
        config: SimulationConfig | None = None,
        citizen_service: CitizenAgentService | None = None,
        learning_store: LearningStore | None = None,
        city_planner: CityPlanner | None = None,
    ) -> None:
        self.config = config or SimulationConfig()
        self.tick = 0
        self.running = False
        self.speed_multiplier = 1.0
        self._seed = self.config.seed
        self._rng = random.Random(self._seed)
        self._weather = "clear"
        self._weather_lock_until_tick: int | None = None
        self._temperature = 21.5
        self._active_event: str | None = None
        self._infrastructure_status: str | None = None
        self._timeline: list[EventPayload] = []
        self._pending_taxi_meeting: PendingTaxiMeeting | None = None
        self._scenario: ScenarioDirective | None = None
        self._task_graph_plan: TaskGraphPlan | None = None
        self._drone_directives: dict[str, DroneDirective] = {}
        self._replans: list[ReplanRecord] = []
        self._forced_replanner_blockers: list[str] = []
        self._replan_attempts: dict[str, int] = {}
        self._city_planner = city_planner if city_planner is not None else city_planner_from_env()
        self._city_ai_mode = self._resolve_city_ai_mode()
        self._city_ai_interval_ticks = int(os.getenv("AETHERVILLE_CITY_AI_INTERVAL_TICKS", "120"))
        self._city_ai_next_plan_tick = self._city_ai_interval_ticks
        self._city_ai_task: asyncio.Task[None] | None = None
        self._city_ai_snapshot = CityAiSnapshot(
            mode=self._city_ai_mode,
            status="idle",
            next_plan_tick=self._city_ai_next_plan_tick,
            summary=(
                "city AI planner disabled"
                if self._city_planner is None
                else "city AI planner waiting for first planning window"
            ),
        )
        self.citizens = citizen_service or CitizenAgentService(
            count=self.config.visible_citizen_count,
            seed=self.config.seed,
            planner=planner_from_env(),
        )
        self.vehicles = VehicleController()
        self.traffic_controller = FixedCycleController()
        self.traffic_policy = TrafficPolicyWrapper.from_env()
        self.traffic_forecaster = LstmForecastWrapper()
        self.command_dispatcher = GodCommandDispatcher()
        self.learning = learning_store or LearningStore()

    @property
    def timeline(self) -> list[EventPayload]:
        return list(self._timeline)

    def start(self) -> SimStatusResponse:
        self.running = True
        return self.status()

    def stop(self) -> SimStatusResponse:
        self.running = False
        return self.status()

    def reset(self, seed: int | None = None) -> SimStatusResponse:
        if seed is not None:
            self._seed = seed
        self._rng = random.Random(self._seed)
        self.tick = 0
        self.running = False
        self.speed_multiplier = 1.0
        self._weather = "clear"
        self._weather_lock_until_tick = None
        self._temperature = 21.5
        self._active_event = None
        self._infrastructure_status = None
        self._pending_taxi_meeting = None
        self._scenario = None
        self._task_graph_plan = None
        self._drone_directives = {}
        self._replans = []
        self._forced_replanner_blockers = []
        self._replan_attempts = {}
        self._city_ai_next_plan_tick = self._city_ai_interval_ticks
        self._city_ai_snapshot = CityAiSnapshot(
            mode=self._city_ai_mode,
            status="idle",
            next_plan_tick=self._city_ai_next_plan_tick,
            summary=(
                "city AI planner disabled"
                if self._city_planner is None
                else "city AI planner waiting for first planning window"
            ),
        )
        self.citizens = CitizenAgentService(
            count=self.config.visible_citizen_count,
            seed=self._seed,
            planner=planner_from_env(),
        )
        self.vehicles = VehicleController()
        self.traffic_controller = FixedCycleController()
        self.traffic_policy = TrafficPolicyWrapper.from_env()
        self.traffic_forecaster = LstmForecastWrapper()
        self._timeline = [
            EventPayload(
                kind="memory_added",
                message=f"simulation reset with seed {self._seed}",
                metadata={"seed": self._seed},
            )
        ]
        return self.status()

    def step(self) -> Envelope:
        self.tick += 1
        self._maybe_complete_pending_taxi_meeting()
        self._advance_scenario()
        # Keep the first slice deterministic while still visibly changing state.
        weather_locked = (
            self._weather_lock_until_tick is not None
            and self.tick < self._weather_lock_until_tick
        )
        if self.tick % 120 == 0 and not weather_locked:
            self._weather = "rain" if self._weather == "clear" else "clear"
            self._record_event(
                EventPayload(
                    kind="weather_changed",
                    message=f"weather changed to {self._weather}",
                    metadata={"weather": self._weather, "tick": self.tick},
                )
            )
        if self.tick % 80 == 12:
            self._record_event(
                EventPayload(
                    kind="collision_avoided",
                    message="v01 slowed for a mock pedestrian detection",
                    entity_id="v01",
                    metadata={"vehicle_id": "v01", "tick": self.tick},
                )
            )
        return self.state_update()

    def snapshot(self) -> WorldStatePayload:
        self._maybe_complete_pending_taxi_meeting()
        angle = self.tick * 0.08
        minute = self.config.start_minute + int(self.tick * self.speed_multiplier / 10)
        time_of_day = f"{(minute // 60) % 24:02d}:{minute % 60:02d}"
        congestion_active = self.vehicles.congestion_active(self.tick)
        learning = self.learning.snapshot()
        learned_queue_boost = self.learning.learned_queue_boost()
        total_queue = (
            int(62 + 18 * abs(math.sin(angle))) + learned_queue_boost
            if congestion_active
            else int(12 + 20 * abs(math.sin(angle))) + learned_queue_boost
        )
        vehicles = self.vehicles.vehicle_states(
            self.tick,
            self.running,
            learned_speed_factor=self.learning.traffic_speed_factor(),
        )
        if learning.adaptation_epoch > 0:
            vehicles = [
                vehicle.model_copy(
                    update={
                        "display_tags": [
                            *vehicle.display_tags,
                            f"AI학습 v{learning.adaptation_epoch}",
                        ]
                    }
                )
                for vehicle in vehicles
            ]
        traffic_action: int | None = None
        traffic_ai = TrafficAiSnapshot()
        if self.traffic_policy.checkpoint_loaded:
            traffic_observation = self._traffic_policy_observation(total_queue)
            traffic_action = self.traffic_policy.select_action(traffic_observation)
            traffic_ai = self.traffic_policy.snapshot(last_action=traffic_action)

        traffic_lights = self.traffic_controller.lights_for_tick(
            self.tick,
            policy_action=traffic_action,
            policy_mode=traffic_ai.mode if traffic_action is not None else None,
        )
        if learning.adaptation_epoch > 0:
            traffic_lights = [
                light.model_copy(
                    update={
                        "display_tags": [
                            *light.display_tags,
                            "학습제어",
                            f"v{learning.adaptation_epoch}",
                        ]
                    }
                )
                for light in traffic_lights
            ]
        citizen_states = self.citizens.world_states(self.tick, self.running)
        drones = self._drone_states(citizen_states)
        task_graph = self._task_graph_snapshot()
        entity_brains = self._entity_brain_states(
            citizen_states,
            vehicles,
            drones,
            traffic_lights,
            task_graph=task_graph,
        )

        return WorldStatePayload(
            world=WorldClock(
                time_of_day=time_of_day,
                weather=self._weather,
                temperature=self._temperature,
                active_event=self._active_event,
                infrastructure_status=self._infrastructure_status,
            ),
            citizens=citizen_states,
            vehicles=vehicles,
            drones=drones,
            traffic_lights=traffic_lights,
            traffic_forecast=self.traffic_forecaster.predict(
                tick=self.tick,
                vehicle_count=len(vehicles),
                total_queue=total_queue,
            ),
            traffic_ai=traffic_ai,
            traffic_forecast_ai=self.traffic_forecaster.snapshot(),
            learning=learning,
            city_ai=self._city_ai_snapshot,
            scenario=self._scenario,
            task_graph=task_graph,
            entity_brains=entity_brains,
            replans=list(self._replans[-12:]),
        )

    def state_update(self) -> Envelope:
        return make_state_update(self.snapshot(), tick=self.tick)

    def status(self) -> SimStatusResponse:
        state = self.snapshot()
        return SimStatusResponse(
            tick=self.tick,
            running=self.running,
            speed_multiplier=self.speed_multiplier,
            time_of_day=state.world.time_of_day,
            citizen_count=len(state.citizens),
            vehicle_count=len(state.vehicles),
            traffic_light_count=len(state.traffic_lights),
        )

    def vehicle_camera_frame(self, vehicle_id: str) -> VehicleCameraFrame:
        return self.vehicles.camera_frame(vehicle_id, self.tick)

    def learning_status(self) -> LearningStatusResponse:
        return self.learning.status_response()

    def _resolve_city_ai_mode(self) -> Literal["disabled", "rules", "vllm"]:
        if self._city_planner is None:
            return "disabled"
        source = getattr(self._city_planner, "source", "rules")
        return "vllm" if source == "vllm" else "rules"

    def build_city_context(self) -> CityWorldContext:
        state = self.snapshot()
        total_queue = (
            state.traffic_forecast[0].expected_vehicle_count
            if state.traffic_forecast
            else len(state.vehicles)
        )
        forecast_pressure = (
            state.traffic_forecast[0].congestion_index if state.traffic_forecast else 0.0
        )
        return CityWorldContext(
            tick=self.tick,
            time_of_day=state.world.time_of_day,
            weather=state.world.weather,
            active_event=state.world.active_event,
            infrastructure_status=state.world.infrastructure_status,
            citizens=[
                CityActorContext(
                    id=citizen.id,
                    kind="citizen",
                    name=citizen.name,
                    pos=citizen.pos,
                    status=citizen.current_action,
                    tags=citizen.display_tags,
                )
                for citizen in state.citizens
            ],
            vehicles=[
                CityActorContext(
                    id=vehicle.id,
                    kind="vehicle",
                    name=vehicle.type,
                    pos=vehicle.pos,
                    status=f"speed={vehicle.speed:.2f} passenger={vehicle.passenger_id}",
                    tags=vehicle.display_tags,
                )
                for vehicle in state.vehicles
            ],
            traffic=CityTrafficContext(
                total_queue=total_queue,
                congestion_active=self.vehicles.congestion_active(self.tick),
                policy_mode=state.traffic_ai.mode,
                forecast_pressure=forecast_pressure,
            ),
            recent_events=[event.message for event in self._timeline[-8:]],
            learning=state.learning,
        )

    def run_city_planner_once(self) -> CityAiPlan | None:
        if self._city_planner is None:
            return None
        self._city_ai_snapshot = self._city_ai_snapshot.model_copy(update={"status": "planning"})
        context = self.build_city_context()
        try:
            plan = self._city_planner.plan(context)
            events = self._apply_city_ai_plan(plan)
            self._city_ai_next_plan_tick = self.tick + self._city_ai_interval_ticks
            self._city_ai_snapshot = CityAiSnapshot(
                mode="vllm" if plan.source == "vllm" else "rules",
                status="applied",
                plan_id=plan.plan_id,
                last_planned_tick=self.tick,
                next_plan_tick=self._city_ai_next_plan_tick,
                summary=plan.summary,
                actions=plan.actions,
                reason="; ".join(action.reason for action in plan.actions[:3]),
            )
            for event in events:
                self._record_event(event)
            return plan
        except (OSError, ValueError, KeyError) as exc:
            self._city_ai_next_plan_tick = self.tick + self._city_ai_interval_ticks
            self._city_ai_snapshot = self._city_ai_snapshot.model_copy(
                update={
                    "status": "error",
                    "last_planned_tick": self.tick,
                    "next_plan_tick": self._city_ai_next_plan_tick,
                    "summary": "city AI planner failed safely",
                    "reason": exc.__class__.__name__,
                }
            )
            return None

    async def _maybe_run_city_ai(self, broadcast: BroadcastCallback) -> None:
        if self._city_planner is None or self.tick < self._city_ai_next_plan_tick:
            return
        if self._city_ai_task is not None and not self._city_ai_task.done():
            return
        self._city_ai_task = asyncio.create_task(self._run_city_ai_task(broadcast))

    async def _run_city_ai_task(self, broadcast: BroadcastCallback) -> None:
        before_timeline_len = len(self._timeline)
        if self._city_planner is None:
            return
        self._city_ai_snapshot = self._city_ai_snapshot.model_copy(update={"status": "planning"})
        context = self.build_city_context()
        try:
            plan = await asyncio.to_thread(self._city_planner.plan, context)
            events = self._apply_city_ai_plan(plan)
            self._city_ai_next_plan_tick = self.tick + self._city_ai_interval_ticks
            self._city_ai_snapshot = CityAiSnapshot(
                mode="vllm" if plan.source == "vllm" else "rules",
                status="applied",
                plan_id=plan.plan_id,
                last_planned_tick=self.tick,
                next_plan_tick=self._city_ai_next_plan_tick,
                summary=plan.summary,
                actions=plan.actions,
                reason="; ".join(action.reason for action in plan.actions[:3]),
            )
            for event in events:
                self._record_event(event)
        except (OSError, ValueError, KeyError) as exc:
            self._city_ai_next_plan_tick = self.tick + self._city_ai_interval_ticks
            self._city_ai_snapshot = self._city_ai_snapshot.model_copy(
                update={
                    "status": "error",
                    "last_planned_tick": self.tick,
                    "next_plan_tick": self._city_ai_next_plan_tick,
                    "summary": "city AI planner failed safely",
                    "reason": exc.__class__.__name__,
                }
            )
        for event in self._timeline[before_timeline_len:]:
            await broadcast(self._event_envelope(event))
        await broadcast(self.state_update())

    def _apply_city_ai_plan(self, plan: CityAiPlan) -> list[EventPayload]:
        events = [
            EventPayload(
                kind="city_ai_plan",
                message=f"City AI plan applied: {plan.summary}",
                metadata={
                    "action": "city_ai_plan",
                    "plan_id": plan.plan_id,
                    "source": plan.source,
                    "confidence": plan.confidence,
                    "actions": [action.type for action in plan.actions],
                },
            )
        ]
        taxi_destinations: dict[str, str] = {}
        for action in plan.actions:
            event = self._apply_city_ai_action(plan, action, taxi_destinations)
            if event is not None:
                events.append(event)
        return events

    def _apply_city_ai_action(
        self,
        plan: CityAiPlan,
        action: CityAiAction,
        taxi_destinations: dict[str, str],
    ) -> EventPayload | None:
        metadata = {
            "source": "city_ai",
            "plan_id": plan.plan_id,
            "planner": plan.source,
            "action": action.type,
            "reason": action.reason,
        }
        if action.type == "no_op":
            return None
        if action.type == "set_weather" and action.weather is not None:
            self._weather = action.weather
            self._weather_lock_until_tick = self.tick + 900
            self._active_event = f"weather:{action.weather}"
            return EventPayload(
                kind="weather_changed",
                message=f"City AI changed weather to {action.weather}",
                metadata=metadata | {"weather": action.weather},
            )
        if action.type == "traffic_surge":
            self.vehicles.activate_congestion(self.tick)
            self._active_event = "traffic congestion"
            self._infrastructure_status = "traffic congestion active"
            return EventPayload(
                kind="infrastructure_changed",
                message="City AI increased traffic pressure",
                metadata=metadata | {"status": "traffic congestion active"},
            )
        if action.type == "move_citizen" and action.actor_id is not None:
            citizen_states = self.citizens.world_states(self.tick, self.running)
            actor = next(
                (citizen for citizen in citizen_states if citizen.id == action.actor_id),
                None,
            )
            target_xz = self._target_xz(action, citizen_states)
            if actor is None or target_xz is None:
                return None
            label = action.label or "AI 자율 이동"
            self.citizens.move_citizen(
                action.actor_id,
                start_xz=(actor.pos[0], actor.pos[2]),
                target_xz=target_xz,
                label=label,
                requested_tick=self.tick,
            )
            return EventPayload(
                kind="person_updated",
                message=f"City AI moved {actor.name}: {label}",
                entity_id=actor.id,
                metadata=metadata | {"citizen_id": actor.id, "label": label},
            )
        if action.type == "remember" and action.actor_id is not None:
            return self.citizens.append_memory(
                action.actor_id,
                action.memory or f"City AI plan remembered: {plan.summary}",
                tick=self.tick,
                importance=0.66,
                tags=["city-ai", plan.source],
            )
        if action.type == "call_taxi" and action.actor_id is not None:
            citizen_states = self.citizens.world_states(self.tick, self.running)
            passenger = next(
                (citizen for citizen in citizen_states if citizen.id == action.actor_id),
                None,
            )
            destination_id = action.destination_actor_id or action.target_id
            destination = next(
                (
                    citizen
                    for citizen in citizen_states
                    if destination_id is not None and citizen.id == destination_id
                ),
                None,
            )
            target_xz = self._target_xz(action, citizen_states)
            if passenger is None:
                return None
            self.citizens.clear_meeting_for(passenger.id)
            self.vehicles.request_taxi(
                passenger.id,
                vehicle_id=action.vehicle_id or "v01",
                passenger_name=passenger.name,
                pickup_xz=(passenger.pos[0], passenger.pos[2]),
                dropoff_xz=target_xz,
                dropoff_label=destination.name if destination else action.label,
                requested_tick=self.tick,
            )
            if destination_id is not None:
                taxi_destinations[passenger.id] = destination_id
            return EventPayload(
                kind="trip_requested",
                message=f"City AI dispatched taxi for {passenger.name}",
                entity_id=action.vehicle_id or "v01",
                metadata=metadata
                | {
                    "vehicle_id": action.vehicle_id or "v01",
                    "passenger_id": passenger.id,
                    "destination_citizen_id": destination_id,
                },
            )
        if action.type == "meet" and action.actor_id is not None and action.target_id is not None:
            waits_for_taxi = (
                action.after == "taxi_arrival"
                or taxi_destinations.get(action.actor_id) == action.target_id
            )
            if waits_for_taxi:
                self._pending_taxi_meeting = PendingTaxiMeeting(action.actor_id, action.target_id)
                return EventPayload(
                    kind="relationship_changed",
                    message="City AI scheduled a meeting after taxi arrival",
                    entity_id=action.actor_id,
                    metadata=metadata
                    | {
                        "source": action.actor_id,
                        "target": action.target_id,
                        "deferred_until": "taxi_arrival",
                    },
                )
            self.citizens.activate_meeting(action.actor_id, action.target_id)
            self._active_event = "citizen meeting"
            return EventPayload(
                kind="relationship_changed",
                message="City AI activated a citizen meeting",
                entity_id=action.actor_id,
                metadata=metadata | {"source": action.actor_id, "target": action.target_id},
            )
        return None

    @staticmethod
    def _target_xz(
        action: CityAiAction, citizens: list[CitizenState]
    ) -> tuple[float, float] | None:
        if action.destination is not None:
            return (action.destination[0], action.destination[2])
        target_id = action.destination_actor_id or action.target_id
        target = next(
            (citizen for citizen in citizens if target_id is not None and citizen.id == target_id),
            None,
        )
        if target is None:
            return None
        return (target.pos[0], target.pos[2])

    def _drone_states(self, citizens: list[CitizenState] | None = None) -> list[DroneState]:
        del citizens
        directive = self._drone_directives.get("d01")
        if directive is None:
            return [
                DroneState(
                    id="d01",
                    pos=[-2.0, 3.0, 2.0],
                    destination=[2.0, 3.0, -2.0],
                    cargo="medical-kit",
                    battery=0.94,
                )
            ]
        pos, moving = self._drone_directive_pose(directive)
        if self.tick > directive.hold_until_tick and not moving:
            self._drone_directives.pop(directive.drone_id, None)
        return [
            DroneState(
                id=directive.drone_id,
                pos=pos,
                destination=[directive.target_xz[0], 3.0, directive.target_xz[1]],
                cargo=directive.label,
                battery=0.92,
            )
        ]

    def _drone_directive_pose(self, directive: DroneDirective) -> tuple[list[float], bool]:
        elapsed = max(0, self.tick - directive.requested_tick)
        distance = math.dist(directive.start_xz, directive.target_xz)
        local = min(1.0, (elapsed * 0.1) / max(distance, 0.001))
        x = directive.start_xz[0] + (directive.target_xz[0] - directive.start_xz[0]) * local
        z = directive.start_xz[1] + (directive.target_xz[1] - directive.start_xz[1]) * local
        return [round(x, 3), 3.0, round(z, 3)], local < 1.0

    def _advance_scenario(self) -> None:
        if self._scenario is None or self._scenario.status in {"completed", "failed"}:
            return

        progressed = True
        while progressed:
            progressed = False
            for step in list(self._scenario.steps):
                current = self._scenario_step(step.id)
                if current is None or current.status != "pending":
                    continue
                if not self._scenario_dependencies_completed(current):
                    continue
                self._start_scenario_step(current)
                progressed = True

        for step in list(self._scenario.steps):
            current = self._scenario_step(step.id)
            if current is None or current.status != "running":
                continue
            if self._scenario_step_completed(current):
                self._complete_scenario_step(current)
                continue
            self._maybe_replan_step(current)

        self._refresh_scenario_status()

    def _scenario_step(self, step_id: str) -> ScenarioStep | None:
        if self._scenario is None:
            return None
        return next((step for step in self._scenario.steps if step.id == step_id), None)

    def _scenario_dependencies_completed(self, step: ScenarioStep) -> bool:
        return all(
            (dependency := self._scenario_step(dependency_id)) is not None
            and dependency.status == "completed"
            for dependency_id in step.depends_on
        )

    def _replace_scenario_step(self, step_id: str, **updates: object) -> ScenarioStep | None:
        if self._scenario is None:
            return None
        updated_step: ScenarioStep | None = None
        steps: list[ScenarioStep] = []
        for step in self._scenario.steps:
            if step.id == step_id:
                updated_step = step.model_copy(update=updates)
                steps.append(updated_step)
            else:
                steps.append(step)
        current_step_id = next((step.id for step in steps if step.status == "running"), None)
        self._scenario = self._scenario.model_copy(
            update={
                "steps": steps,
                "updated_tick": self.tick,
                "current_step_id": current_step_id,
                "status": "running",
            }
        )
        return updated_step

    def _task_graph_planned_event(self, plan: TaskGraphPlan) -> EventPayload:
        kind: Literal["task_graph_planned", "task_graph_rejected"] = (
            "task_graph_rejected" if plan.graph.status == "rejected" else "task_graph_planned"
        )
        action = "task_graph_rejected" if kind == "task_graph_rejected" else "task_graph_planned"
        return EventPayload(
            kind=kind,
            message=(
                f"TaskGraph rejected: {plan.graph.rejection_reason}"
                if kind == "task_graph_rejected"
                else f"TaskGraph planned: {plan.graph.title}"
            ),
            metadata={
                "category": "event",
                "action": action,
                "task_graph_id": plan.graph.id,
                "plan_id": plan.plan_id,
                "status": plan.graph.status,
                "node_count": len(plan.graph.nodes),
                "actions": [node.action_type for node in plan.graph.nodes],
                "actors": plan.graph.actors,
                "assumptions": plan.graph.assumptions,
                "rejection_reason": plan.graph.rejection_reason,
            },
        )

    def _task_graph_snapshot(self) -> TaskGraphExecutionSnapshot | None:
        plan = self._task_graph_plan
        if plan is None:
            return None

        status = plan.graph.status
        current_node_id: str | None = None
        nodes = list(plan.graph.nodes)
        if self._scenario is not None and self._scenario.raw_text == plan.graph.raw_text:
            step_by_node_id = {
                str(step.metadata.get("task_node_id", step.id)): step
                for step in self._scenario.steps
            }
            synced_nodes: list[TaskNode] = []
            for node in nodes:
                step = step_by_node_id.get(node.id)
                if step is None:
                    synced_nodes.append(node)
                    continue
                synced_nodes.append(
                    node.model_copy(
                        update={
                            "status": step.status,
                            "metadata": {
                                **node.metadata,
                                "scenario_status": step.status,
                                "scenario_evidence": step.evidence,
                                "started_tick": step.started_tick,
                                "completed_tick": step.completed_tick,
                            },
                        }
                    )
                )
            nodes = synced_nodes
            current_node_id = self._scenario.current_step_id
            if self._scenario.status == "running":
                status = "running"
            elif self._scenario.status == "completed":
                status = "completed"
            elif self._scenario.status == "failed":
                status = "failed"

        completed_count = sum(1 for node in nodes if node.status == "completed")
        return TaskGraphExecutionSnapshot(
            graph_id=plan.graph.id,
            plan_id=plan.plan_id,
            status=status,
            current_node_id=current_node_id,
            nodes=nodes,
            completed_count=completed_count,
            total_count=len(nodes),
            assumptions=plan.graph.assumptions,
            rejection_reason=plan.graph.rejection_reason,
            updated_tick=self.tick,
        )

    def _start_scenario_step(self, step: ScenarioStep) -> None:
        metadata = dict(step.metadata)
        if (
            isinstance(metadata.get("force_blocker_type"), str)
            and step.type in {"call_taxi", "set_weather", "traffic_surge", "remember", "wait"}
        ):
            self._replace_scenario_step(step.id, status="running", started_tick=self.tick)
            current = self._scenario_step(step.id)
            if current is not None:
                self._maybe_replan_step(current)
            return
        if step.type == "set_weather":
            weather = str(metadata.get("weather", "rain"))
            self._weather = weather
            self._weather_lock_until_tick = self.tick + 900
            self._active_event = f"scenario:weather:{weather}"
            self._record_scenario_event(
                "scenario_step_started",
                step,
                f"시나리오 날씨 적용: {weather}",
            )
            self._replace_scenario_step(
                step.id,
                status="completed",
                started_tick=self.tick,
                completed_tick=self.tick,
                evidence=f"weather={weather}",
                metadata=metadata | {"weather": weather},
            )
            return
        if step.type == "traffic_surge":
            self.vehicles.activate_congestion(self.tick)
            self._active_event = "scenario:traffic congestion"
            self._infrastructure_status = "traffic congestion active"
            self._record_scenario_event("scenario_step_started", step, "시나리오 교통량 증가 적용")
            self._replace_scenario_step(
                step.id,
                status="completed",
                started_tick=self.tick,
                completed_tick=self.tick,
                evidence="traffic congestion active",
            )
            return
        if step.type == "move_actor_to_actor":
            actor = self._citizen_state(step.actor_id)
            target = self._citizen_state(step.target_actor_id)
            if actor is None or target is None:
                self._fail_scenario_step(step, "actor or target missing")
                return
            target_xz = (target.pos[0], target.pos[2])
            self.citizens.move_citizen(
                actor.id,
                start_xz=(actor.pos[0], actor.pos[2]),
                target_xz=target_xz,
                label=step.visible_label,
                requested_tick=self.tick,
            )
            self._active_event = f"scenario:{step.visible_label}"
            self._record_scenario_event("scenario_step_started", step, step.visible_label)
            self._replace_scenario_step(
                step.id,
                status="running",
                started_tick=self.tick,
                metadata=metadata | {"target_xz": list(target_xz)},
            )
            return
        if step.type == "move_actor_to_location":
            actor = self._citizen_state(step.actor_id)
            location_xz = _metadata_xz(metadata.get("target_xz"))
            if actor is None or location_xz is None:
                self._fail_scenario_step(step, "actor or location target missing")
                return
            self.citizens.move_citizen(
                actor.id,
                start_xz=(actor.pos[0], actor.pos[2]),
                target_xz=location_xz,
                label=step.visible_label,
                requested_tick=self.tick,
            )
            self._active_event = f"scenario:{step.visible_label}"
            self._record_scenario_event("scenario_step_started", step, step.visible_label)
            self._replace_scenario_step(step.id, status="running", started_tick=self.tick)
            return
        if step.type == "meet":
            actor = self._citizen_state(step.actor_id)
            target = self._citizen_state(step.target_actor_id)
            if actor is None or target is None:
                self._fail_scenario_step(step, "meeting actor missing")
                return
            meeting_xz = ((actor.pos[0] + target.pos[0]) / 2, (actor.pos[2] + target.pos[2]) / 2)
            self.citizens.activate_meeting(actor.id, target.id, point_xz=meeting_xz)
            self._active_event = f"scenario:{step.visible_label}"
            self._record_scenario_event("scenario_step_started", step, step.visible_label)
            self._replace_scenario_step(
                step.id,
                status="running",
                started_tick=self.tick,
                metadata=metadata | {"meeting_xz": [meeting_xz[0], meeting_xz[1]]},
            )
            return
        if step.type == "call_taxi":
            self._dispatch_scenario_taxi(step)
            self._record_scenario_event("scenario_step_started", step, step.visible_label)
            self._replace_scenario_step(
                step.id,
                status="completed",
                started_tick=self.tick,
                completed_tick=self.tick,
                evidence="taxi dispatched",
            )
            return
        if step.type == "taxi_drive_to_actor":
            has_taxi = any(
                vehicle.passenger_id == step.actor_id
                for vehicle in self.vehicles.vehicle_states(self.tick, self.running)
            )
            if not has_taxi:
                self._dispatch_scenario_taxi(step)
            self._active_event = f"scenario:{step.visible_label}"
            self._record_scenario_event("scenario_step_started", step, step.visible_label)
            self._replace_scenario_step(step.id, status="running", started_tick=self.tick)
            return
        if step.type == "drone_move_to_actor":
            target = self._citizen_state(step.target_actor_id)
            if target is None:
                self._fail_scenario_step(step, "drone target missing")
                return
            current_drone = self._drone_states()[0]
            target_xz = (target.pos[0], target.pos[2])
            self._drone_directives[step.drone_id or "d01"] = DroneDirective(
                drone_id=step.drone_id or "d01",
                start_xz=(current_drone.pos[0], current_drone.pos[2]),
                target_xz=target_xz,
                label=step.visible_label,
                requested_tick=self.tick,
                hold_until_tick=self.tick + 720,
            )
            self._active_event = f"scenario:{step.visible_label}"
            self._record_scenario_event("scenario_step_started", step, step.visible_label)
            self._replace_scenario_step(
                step.id,
                status="running",
                started_tick=self.tick,
                metadata=metadata | {"target_xz": list(target_xz)},
            )
            return
        if step.type == "move_actor_to_group":
            actor = self._citizen_state(step.actor_id)
            targets = [self._citizen_state(target_id) for target_id in step.target_actor_ids]
            valid_targets = [target for target in targets if target is not None]
            if actor is None or not valid_targets:
                self._fail_scenario_step(step, "group target missing")
                return
            target_xz = (
                sum(target.pos[0] for target in valid_targets) / len(valid_targets),
                sum(target.pos[2] for target in valid_targets) / len(valid_targets),
            )
            self.citizens.move_citizen(
                actor.id,
                start_xz=(actor.pos[0], actor.pos[2]),
                target_xz=target_xz,
                label=step.visible_label,
                requested_tick=self.tick,
            )
            self._active_event = f"scenario:{step.visible_label}"
            self._record_scenario_event("scenario_step_started", step, step.visible_label)
            self._replace_scenario_step(
                step.id,
                status="running",
                started_tick=self.tick,
                metadata=metadata | {"target_xz": list(target_xz)},
            )
            return
        self._replace_scenario_step(
            step.id,
            status="completed",
            started_tick=self.tick,
            completed_tick=self.tick,
        )

    def _dispatch_scenario_taxi(self, step: ScenarioStep) -> None:
        passenger = self._citizen_state(step.actor_id)
        target = self._citizen_state(step.target_actor_id)
        if passenger is None:
            self._fail_scenario_step(step, "taxi passenger missing")
            return
        self.citizens.clear_meeting_for(passenger.id)
        self.vehicles.request_taxi(
            passenger.id,
            vehicle_id=step.vehicle_id or "v01",
            passenger_name=passenger.name,
            pickup_xz=(passenger.pos[0], passenger.pos[2]),
            dropoff_xz=(target.pos[0], target.pos[2]) if target else None,
            dropoff_label=target.name if target else step.visible_label,
            requested_tick=self.tick,
        )

    def _scenario_step_completed(self, step: ScenarioStep) -> bool:
        if step.started_tick is None:
            return False
        if step.type in {"move_actor_to_actor", "move_actor_to_location"}:
            return self._actor_reached_step_target(step)
        if step.type == "meet":
            return self.tick - step.started_tick >= 24
        if step.type == "taxi_drive_to_actor":
            return self.vehicles.taxi_trip_complete(
                self.tick,
                learned_speed_factor=self.learning.traffic_speed_factor(),
                congested=self.vehicles.congestion_active(self.tick),
            )
        if step.type == "drone_move_to_actor":
            target_xz = _metadata_xz(step.metadata.get("target_xz"))
            drone = self._drone_states()[0]
            return (
                target_xz is not None
                and math.dist((drone.pos[0], drone.pos[2]), target_xz) < 0.35
            )
        if step.type == "move_actor_to_group":
            return self._actor_reached_step_target(step)
        return True

    def _actor_reached_step_target(self, step: ScenarioStep) -> bool:
        actor = self._citizen_state(step.actor_id)
        target_xz = _metadata_xz(step.metadata.get("target_xz"))
        return (
            actor is not None
            and target_xz is not None
            and math.dist((actor.pos[0], actor.pos[2]), target_xz) < 0.55
        )

    def _complete_scenario_step(self, step: ScenarioStep) -> None:
        evidence = "completed"
        if step.type == "taxi_drive_to_actor":
            passenger = self._citizen_state(step.actor_id)
            target = self._citizen_state(step.target_actor_id)
            if passenger is not None and target is not None:
                self.citizens.move_citizen(
                    passenger.id,
                    start_xz=(target.pos[0], target.pos[2]),
                    target_xz=(target.pos[0], target.pos[2]),
                    label=f"{target.name} 도착",
                    requested_tick=self.tick,
                    hold_ticks=360,
                )
                evidence = f"{passenger.name} arrived near {target.name}"
        self._replace_scenario_step(
            step.id,
            status="completed",
            completed_tick=self.tick,
            evidence=evidence,
        )
        self._record_scenario_event("scenario_step_completed", step, f"완료: {step.visible_label}")

    def _fail_scenario_step(self, step: ScenarioStep, evidence: str) -> None:
        self._replace_scenario_step(
            step.id,
            status="failed",
            started_tick=step.started_tick or self.tick,
            completed_tick=self.tick,
            evidence=evidence,
        )
        if self._scenario is not None:
            self._scenario = self._scenario.model_copy(
                update={"status": "failed", "updated_tick": self.tick}
            )

    def _refresh_scenario_status(self) -> None:
        if self._scenario is None:
            return
        if any(step.status == "failed" for step in self._scenario.steps):
            self._scenario = self._scenario.model_copy(update={"status": "failed"})
            return
        if self._scenario.steps and all(
            step.status == "completed" for step in self._scenario.steps
        ):
            if self._scenario.status != "completed":
                self._record_event(
                    EventPayload(
                        kind="scenario_completed",
                        message=f"Scenario completed: {self._scenario.title}",
                        metadata={
                            "scenario_id": self._scenario.id,
                            "steps": [step.id for step in self._scenario.steps],
                        },
                    )
                )
            self._scenario = self._scenario.model_copy(
                update={
                    "status": "completed",
                    "current_step_id": None,
                    "updated_tick": self.tick,
                }
            )

    def force_replanner_blocker(self, blocker_type: str) -> None:
        """Queue a synthetic blocker for deterministic resilience tests/smokes."""

        self._forced_replanner_blockers.append(blocker_type)

    def _maybe_replan_step(self, step: ScenarioStep) -> bool:
        blocker_type = self._blocker_for_step(step)
        if blocker_type is None:
            return False

        attempt = self._replan_attempts.get(step.id, 0) + 1
        if attempt > 2:
            self._record_replan(
                step,
                blocker_type=blocker_type,
                attempt=attempt,
                fallback_action="fallback_complete",
                reason="max replan attempts reached; task is marked fallback-complete",
                recovered=False,
            )
            self._recover_scenario_step(step, blocker_type, "fallback_complete")
            return True

        self._replan_attempts[step.id] = attempt
        fallback_action = self._fallback_for_blocker(blocker_type, step)
        reason = self._blocker_reason(blocker_type, step)
        self._record_replan(
            step,
            blocker_type=blocker_type,
            attempt=attempt,
            fallback_action=fallback_action,
            reason=reason,
            recovered=True,
        )
        self._recover_scenario_step(step, blocker_type, fallback_action)
        return True

    def _blocker_for_step(self, step: ScenarioStep) -> str | None:
        metadata = dict(step.metadata)
        if metadata.get("recovered_by_replanner"):
            return None
        if self._forced_replanner_blockers:
            return self._forced_replanner_blockers.pop(0)
        forced = metadata.get("force_blocker_type")
        if isinstance(forced, str):
            return forced
        if step.started_tick is None:
            return None
        timeout = int(metadata.get("timeout_ticks", 240))
        if self.tick - step.started_tick <= timeout:
            return None
        if step.type in {"move_actor_to_actor", "move_actor_to_location"}:
            return "stuck_actor"
        if step.type == "taxi_drive_to_actor":
            (
                "traffic_delay"
                if self.vehicles.congestion_active(self.tick)
                else "pickup_timeout"
            )
        if step.type in {"drone_move_to_actor", "drone_deliver"}:
            return "drone_delay"
        if step.type in {"move_actor_to_group", "group_rendezvous"}:
            return "group_timeout"
        if step.depends_on:
            return "dependency_deadlock"
        return None

    def _record_replan(
        self,
        step: ScenarioStep,
        *,
        blocker_type: str,
        attempt: int,
        fallback_action: str,
        reason: str,
        recovered: bool,
    ) -> None:
        entity_id = self._entity_id_for_step(step)
        task_node_id = str(step.metadata.get("task_node_id", step.id))
        for status, kind, message in (
            (
                "blocked",
                "task_blocked",
                f"Task blocked: {step.visible_label} — {reason}",
            ),
            (
                "replanned",
                "task_replanned",
                f"Task replanned: {fallback_action} for {step.visible_label}",
            ),
            (
                "recovered",
                "task_recovered",
                f"Task recovered: {step.visible_label} via {fallback_action}",
            ),
        ):
            if status == "recovered" and not recovered:
                continue
            record = ReplanRecord(
                id=f"replan_{self.tick}_{len(self._replans) + 1:04d}_{status}",
                tick=self.tick,
                task_node_id=task_node_id,
                entity_id=entity_id,
                blocker_type=blocker_type,
                reason=reason,
                attempt=attempt,
                fallback_action=fallback_action,
                status=status,  # type: ignore[arg-type]
            )
            self._replans.append(record)
            self._record_event(
                EventPayload(
                    kind=kind,  # type: ignore[arg-type]
                    message=message,
                    entity_id=entity_id,
                    metadata={
                        "action": kind,
                        "scenario_id": self._scenario.id if self._scenario else None,
                        "step_id": step.id,
                        "task_node_id": task_node_id,
                        "step_type": step.type,
                        "blocker_type": blocker_type,
                        "replan_attempt": attempt,
                        "fallback_action": fallback_action,
                        "replan_record_id": record.id,
                    },
                )
            )

    def _recover_scenario_step(
        self,
        step: ScenarioStep,
        blocker_type: str,
        fallback_action: str,
    ) -> None:
        metadata = dict(step.metadata) | {
            "recovered_by_replanner": True,
            "blocker_type": blocker_type,
            "fallback_action": fallback_action,
            "replan_attempt": self._replan_attempts.get(step.id, 1),
        }
        evidence = f"replanned via {fallback_action} after {blocker_type}"
        if step.type in {"taxi_drive_to_actor", "move_actor_to_actor", "move_actor_to_group"}:
            actor = self._citizen_state(step.actor_id)
            target = self._citizen_state(step.target_actor_id)
            if actor is not None and target is not None:
                self.citizens.move_citizen(
                    actor.id,
                    start_xz=(target.pos[0], target.pos[2]),
                    target_xz=(target.pos[0], target.pos[2]),
                    label=f"fallback 도착: {target.name}",
                    requested_tick=self.tick,
                    hold_ticks=360,
                )
        if step.type in {"drone_move_to_actor", "drone_deliver"}:
            self._drone_directives.pop(step.drone_id or "d01", None)
        self._replace_scenario_step(
            step.id,
            status="completed",
            completed_tick=self.tick,
            evidence=evidence,
            metadata=metadata,
        )

    def _fallback_for_blocker(self, blocker_type: str, step: ScenarioStep) -> str:
        fallback_by_blocker = {
            "stuck_actor": "retry_route_then_short_walk",
            "stuck_vehicle": "reroute_vehicle_path",
            "target_unreachable": "alternate_meeting_point",
            "taxi_unavailable": "walking_fallback_or_wait",
            "pickup_timeout": "dispatch_backup_taxi",
            "group_timeout": "split_group_into_pair_meetings",
            "drone_delay": "drone_hover_then_reroute",
            "low_battery": "drone_hover_and_safe_return",
            "traffic_delay": "slowdown_acknowledge_and_extend_eta",
            "dependency_deadlock": "skip_satisfied_dependency_and_continue",
        }
        if (
            step.type == "taxi_drive_to_actor"
            and blocker_type in {"traffic_delay", "pickup_timeout"}
        ):
            return "taxi_to_walking_safe_arrival"
        return fallback_by_blocker.get(blocker_type, "fallback_complete")

    def _blocker_reason(self, blocker_type: str, step: ScenarioStep) -> str:
        reasons = {
            "stuck_actor": "actor progress did not improve within bounded ticks",
            "stuck_vehicle": "vehicle route appears stalled",
            "target_unreachable": "target cannot be reached with current graph edge",
            "taxi_unavailable": "requested taxi is unavailable in current state",
            "pickup_timeout": "passenger pickup exceeded the demo timeout",
            "group_timeout": "group rendezvous did not converge in time",
            "drone_delay": "drone movement exceeded expected time",
            "low_battery": "drone battery is below safe demo threshold",
            "traffic_delay": "traffic congestion exceeds task deadline",
            "dependency_deadlock": "graph dependency cannot be satisfied without fallback",
        }
        return reasons.get(blocker_type, f"{step.visible_label} requires bounded fallback")

    def _scenario_with_forced_blocker(
        self,
        raw_text: str,
        scenario: ScenarioDirective,
    ) -> ScenarioDirective:
        blocker_type = _blocker_type_from_text(raw_text)
        if blocker_type is None:
            return scenario
        steps: list[ScenarioStep] = []
        applied = False
        for step in scenario.steps:
            if not applied and _blocker_matches_step(blocker_type, step):
                steps.append(
                    step.model_copy(
                        update={
                            "metadata": dict(step.metadata)
                            | {
                                "force_blocker_type": blocker_type,
                                "timeout_ticks": 1,
                            }
                        }
                    )
                )
                applied = True
            else:
                steps.append(step)
        if not applied and steps:
            step = steps[0]
            steps[0] = step.model_copy(
                update={
                    "metadata": dict(step.metadata)
                    | {"force_blocker_type": blocker_type, "timeout_ticks": 1}
                }
            )
        return scenario.model_copy(update={"steps": steps})

    def _entity_brain_states(
        self,
        citizens: list[CitizenState],
        vehicles: list[VehicleState],
        drones: list[DroneState],
        traffic_lights: list[TrafficLightState],
        *,
        task_graph: TaskGraphExecutionSnapshot | None,
    ) -> list[EntityBrainState]:
        node_by_entity = self._task_nodes_by_entity(task_graph)
        recent_replans = self._recent_replans_by_entity()
        brains: list[EntityBrainState] = []

        for citizen in citizens:
            node = node_by_entity.get(citizen.id)
            replan = recent_replans.get(citizen.id)
            if node is not None:
                brains.append(self._brain_from_task_node(citizen, "citizen", node, replan))
                continue
            if replan is not None:
                brains.append(self._brain_from_replan(citizen.id, "citizen", replan))
                continue
            if "AI계획" in citizen.display_tags:
                brains.append(
                    EntityBrainState(
                        entity_id=citizen.id,
                        entity_type="citizen",
                        current_goal=EntityGoal(
                            id=f"city_ai_{citizen.id}",
                            title=citizen.current_action,
                            source="city_ai",
                        ),
                        next_action="continue_city_ai_directive",
                        reason=self._city_ai_snapshot.reason or self._city_ai_snapshot.summary,
                        source="city_ai",
                        progress=EntityProgress(progress_pct=0.55),
                        constraints=self._weather_traffic_constraints(),
                        status="moving" if citizen.anim == "walk" else "waiting",
                        updated_tick=self.tick,
                    )
                )
                continue
            if citizen.talking_to is not None:
                brains.append(
                    EntityBrainState(
                        entity_id=citizen.id,
                        entity_type="citizen",
                        current_goal=EntityGoal(
                            id=f"meeting_{citizen.id}_{citizen.talking_to}",
                            title=citizen.current_action,
                            target_id=citizen.talking_to,
                            source="god_mode",
                        ),
                        next_action="maintain_conversation",
                        reason=(
                            "시민 관계/기억 이벤트가 활성화되어 "
                            "같은 지점에서 만남을 유지합니다."
                        ),
                        source="god_mode",
                        progress=EntityProgress(progress_pct=0.85),
                        constraints=self._weather_traffic_constraints(),
                        status="interacting",
                        updated_tick=self.tick,
                    )
                )
                continue
            brains.append(self._routine_brain(citizen.id, "citizen", citizen.current_action))

        for vehicle in vehicles:
            node = node_by_entity.get(vehicle.id)
            if node is None and vehicle.passenger_id is not None:
                node = node_by_entity.get(vehicle.passenger_id)
            replan = recent_replans.get(vehicle.id) or (
                recent_replans.get(vehicle.passenger_id) if vehicle.passenger_id else None
            )
            if node is not None:
                brains.append(
                    self._brain_from_task_node(
                        vehicle,
                        "taxi" if vehicle.type == "taxi" else "vehicle",
                        node,
                        replan,
                    )
                )
                continue
            if replan is not None:
                brains.append(
                    self._brain_from_replan(
                        vehicle.id,
                        "taxi" if vehicle.type == "taxi" else "vehicle",
                        replan,
                    )
                )
                continue
            title = (
                f"승객 {vehicle.passenger_id} 픽업/이동"
                if vehicle.passenger_id
                else "순환 도로 주행"
            )
            brains.append(
                EntityBrainState(
                    entity_id=vehicle.id,
                    entity_type="taxi" if vehicle.type == "taxi" else "vehicle",
                    current_goal=EntityGoal(id=f"route_{vehicle.id}", title=title),
                    next_action="follow_route_or_dispatch",
                    reason="차량 컨트롤러가 경로·YOLO hazard·교통량을 반영해 속도를 조절합니다.",
                    source="routine" if vehicle.passenger_id is None else "god_mode",
                    progress=EntityProgress(progress_pct=min(1.0, vehicle.speed / 4.2)),
                    constraints=self._weather_traffic_constraints(vehicle=vehicle),
                    status="moving" if vehicle.speed > 0.05 else "waiting",
                    updated_tick=self.tick,
                )
            )

        for drone in drones:
            node = node_by_entity.get(drone.id)
            replan = recent_replans.get(drone.id)
            if node is not None:
                brains.append(self._brain_from_task_node(drone, "drone", node, replan))
                continue
            if replan is not None:
                brains.append(self._brain_from_replan(drone.id, "drone", replan))
                continue
            active = drone.destination is not None
            brains.append(
                EntityBrainState(
                    entity_id=drone.id,
                    entity_type="drone",
                    current_goal=EntityGoal(
                        id=f"drone_{drone.id}",
                        title=drone.cargo or "공중 순찰",
                    ),
                    next_action="hold_or_move_to_destination" if active else "hover",
                    reason=(
                        "드론은 배송/이동 directive가 있으면 목적지까지 이동하고 "
                        "아니면 안전 고도를 유지합니다."
                    ),
                    source="routine",
                    progress=EntityProgress(progress_pct=1.0 if active else 0.0),
                    constraints=[
                        EntityConstraint(
                            kind="battery",
                            description=f"battery {drone.battery:.0%}",
                            severity="warning" if drone.battery < 0.25 else "info",
                        )
                    ],
                    status="moving" if active else "idle",
                    updated_tick=self.tick,
                )
            )

        for light in traffic_lights[:2]:
            brains.append(
                EntityBrainState(
                    entity_id=light.id,
                    entity_type="traffic_light",
                    current_goal=EntityGoal(
                        id=f"signal_{light.id}",
                        title="교차로 phase 제어",
                        source="city_ai" if "학습제어" in light.display_tags else "routine",
                    ),
                    next_action=f"hold_{light.state}_for_{light.remaining_sec:.0f}s",
                    reason="고정 cycle 또는 학습된 교통 pressure가 신호 phase를 선택합니다.",
                    source="city_ai" if "학습제어" in light.display_tags else "routine",
                    progress=EntityProgress(
                        progress_pct=max(0.0, min(1.0, 1 - light.remaining_sec / 30))
                    ),
                    constraints=self._weather_traffic_constraints(),
                    status="planning" if "학습제어" in light.display_tags else "idle",
                    updated_tick=self.tick,
                )
            )

        return brains

    def _task_nodes_by_entity(
        self,
        task_graph: TaskGraphExecutionSnapshot | None,
    ) -> dict[str, TaskNode]:
        if task_graph is None:
            return {}
        result: dict[str, TaskNode] = {}
        for node in task_graph.nodes:
            ids = [
                node.actor_id,
                node.target_actor_id,
                node.target_entity_id,
                node.vehicle_id,
                node.drone_id,
                *node.target_actor_ids,
            ]
            for entity_id in ids:
                if entity_id and (node.status == "running" or entity_id not in result):
                    result[entity_id] = node
        return result

    def _recent_replans_by_entity(self) -> dict[str, ReplanRecord]:
        result: dict[str, ReplanRecord] = {}
        for record in self._replans[-12:]:
            if record.entity_id is not None:
                result[record.entity_id] = record
        return result

    def _brain_from_task_node(
        self,
        entity: CitizenState | VehicleState | DroneState,
        entity_type: Literal["citizen", "vehicle", "taxi", "drone"],
        node: TaskNode,
        replan: ReplanRecord | None,
    ) -> EntityBrainState:
        status = self._brain_status_for_node(node, replan)
        return EntityBrainState(
            entity_id=entity.id,
            entity_type=entity_type,
            current_goal=EntityGoal(
                id=node.id,
                title=node.visible_label,
                target_id=node.target_actor_id or node.target_entity_id,
                source="task_graph",
            ),
            next_action=node.action_type,
            reason=node.reason,
            source="task_graph" if replan is None else "fallback",
            progress=EntityProgress(
                progress_pct=self._node_progress(node),
                current_step_id=node.id,
                eta_ticks=max(0, node.timeout_ticks // 2),
            ),
            constraints=self._constraints_for_node(node, entity_type),
            blocker=self._blocker_from_replan(replan),
            status=status,
            blocked_reason=replan.reason if replan and replan.status != "recovered" else None,
            updated_tick=self.tick,
        )

    def _brain_from_replan(
        self,
        entity_id: str,
        entity_type: Literal["citizen", "vehicle", "taxi", "drone"],
        replan: ReplanRecord,
    ) -> EntityBrainState:
        return EntityBrainState(
            entity_id=entity_id,
            entity_type=entity_type,
            current_goal=EntityGoal(
                id=replan.task_node_id or replan.id,
                title=f"복구 경로: {replan.fallback_action}",
                source="fallback",
            ),
            next_action=replan.fallback_action,
            reason=replan.reason,
            source="fallback",
            progress=EntityProgress(progress_pct=1.0 if replan.status == "recovered" else 0.5),
            constraints=self._weather_traffic_constraints(),
            blocker=self._blocker_from_replan(replan),
            status="fallback" if replan.status == "recovered" else "blocked",
            blocked_reason=replan.reason if replan.status != "recovered" else None,
            updated_tick=self.tick,
        )

    def _routine_brain(
        self,
        entity_id: str,
        entity_type: Literal["citizen", "vehicle", "taxi", "drone"],
        title: str,
    ) -> EntityBrainState:
        return EntityBrainState(
            entity_id=entity_id,
            entity_type=entity_type,
            current_goal=EntityGoal(id=f"routine_{entity_id}", title=title),
            next_action="follow_daily_route",
            reason="명시 task가 없을 때 deterministic routine brain fallback이 상태를 설명합니다.",
            source="routine",
            progress=EntityProgress(progress_pct=(self.tick % 100) / 100),
            constraints=self._weather_traffic_constraints(),
            status="moving" if self.running else "idle",
            updated_tick=self.tick,
        )

    def _brain_status_for_node(
        self,
        node: TaskNode,
        replan: ReplanRecord | None,
    ) -> Literal[
        "idle",
        "planning",
        "moving",
        "waiting",
        "interacting",
        "blocked",
        "complete",
        "fallback",
    ]:
        if replan is not None:
            return "fallback" if replan.status == "recovered" else "blocked"
        if node.status == "completed":
            return "complete"
        if node.status == "pending":
            return "waiting"
        if node.action_type in {"meet", "remember"}:
            return "interacting"
        if node.action_type in {"call_taxi", "wait"}:
            return "waiting"
        if node.action_type in {"set_weather", "traffic_surge"}:
            return "planning"
        return "moving"

    @staticmethod
    def _node_progress(node: TaskNode) -> float:
        if node.status == "completed":
            return 1.0
        if node.status == "running":
            return 0.58
        if node.status == "failed":
            return 0.0
        return 0.18

    def _constraints_for_node(
        self,
        node: TaskNode,
        entity_type: str,
    ) -> list[EntityConstraint]:
        constraints = self._weather_traffic_constraints()
        if node.depends_on:
            constraints.append(
                EntityConstraint(
                    kind="dependency",
                    description=f"depends on {', '.join(node.depends_on)}",
                    severity="info",
                )
            )
        if node.timeout_ticks:
            constraints.append(
                EntityConstraint(
                    kind="deadline",
                    description=f"timeout {node.timeout_ticks} ticks",
                    severity="warning" if node.timeout_ticks < 120 else "info",
                )
            )
        if entity_type == "drone":
            constraints.append(
                EntityConstraint(
                    kind="battery",
                    description="safe demo battery budget",
                    severity="info",
                )
            )
        return constraints

    def _weather_traffic_constraints(
        self,
        *,
        vehicle: VehicleState | None = None,
    ) -> list[EntityConstraint]:
        constraints: list[EntityConstraint] = []
        if self._weather != "clear":
            constraints.append(
                EntityConstraint(
                    kind="weather",
                    description=f"weather={self._weather} increases caution",
                    severity="warning",
                )
            )
        if self.vehicles.congestion_active(self.tick):
            constraints.append(
                EntityConstraint(
                    kind="traffic",
                    description="traffic surge slows vehicles and can trigger replans",
                    severity="warning" if vehicle is None or vehicle.speed < 1.0 else "info",
                )
            )
        return constraints

    @staticmethod
    def _blocker_from_replan(replan: ReplanRecord | None) -> EntityBlocker | None:
        if replan is None:
            return None
        blocker_type = replan.blocker_type
        valid_blockers = {
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
        }
        typed_blocker = cast(
            Literal[
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
                "none",
            ],
            blocker_type if blocker_type in valid_blockers else "none",
        )
        return EntityBlocker(
            blocker_type=typed_blocker,
            reason=replan.reason,
            replan_attempt=replan.attempt,
            fallback_action=replan.fallback_action,
        )

    @staticmethod
    def _entity_id_for_step(step: ScenarioStep) -> str | None:
        return step.actor_id or step.vehicle_id or step.drone_id or step.target_actor_id

    def _citizen_state(self, citizen_id: str | None) -> CitizenState | None:
        if citizen_id is None:
            return None
        return next(
            (
                citizen
                for citizen in self.citizens.world_states(self.tick, self.running)
                if citizen.id == citizen_id
            ),
            None,
        )

    def _record_scenario_event(
        self,
        kind: Literal[
            "scenario_step_started",
            "scenario_step_completed",
        ],
        step: ScenarioStep,
        message: str,
    ) -> None:
        self._record_event(
            EventPayload(
                kind=kind,
                message=message,
                entity_id=step.actor_id or step.vehicle_id or step.drone_id,
                metadata={
                    "scenario_id": self._scenario.id if self._scenario else None,
                    "step_id": step.id,
                    "step_type": step.type,
                    "action": _learning_action_for_step(step.type),
                    "actor_id": step.actor_id,
                    "target_actor_id": step.target_actor_id,
                    "target_actor_ids": step.target_actor_ids,
                    "vehicle_id": step.vehicle_id,
                    "drone_id": step.drone_id,
                },
            )
        )

    def _maybe_complete_pending_taxi_meeting(self) -> None:
        pending = self._pending_taxi_meeting
        if pending is None:
            return
        if not self.vehicles.taxi_trip_complete(
            self.tick,
            learned_speed_factor=self.learning.traffic_speed_factor(),
            congested=self.vehicles.congestion_active(self.tick),
        ):
            return

        self.citizens.activate_meeting(pending.passenger_id, pending.target_id)
        self._active_event = "citizen meeting"
        self._pending_taxi_meeting = None
        self._record_event(
            EventPayload(
                kind="relationship_changed",
                message="Taxi arrival completed the requested citizen meeting",
                entity_id=pending.passenger_id,
                metadata={
                    "category": "relationship",
                    "action": "meeting",
                    "source": pending.passenger_id,
                    "target": pending.target_id,
                    "via": "taxi_arrival",
                },
            )
        )

    def _traffic_policy_observation(self, total_queue: int) -> dict[str, int]:
        wave = int(8 * math.sin(self.tick * 0.08))
        ns_queue = max(0, total_queue // 2 + wave)
        ew_queue = max(0, total_queue - ns_queue)
        active_phase = (
            0 if self.traffic_controller.phase_for_tick(self.tick) == "north_south" else 1
        )
        return {
            "ns_queue": ns_queue,
            "ew_queue": ew_queue,
            "active_phase": active_phase,
            "tick": self.tick,
        }

    def execute_god_command(self, command: GodCommand) -> GodCommandResponse:
        task_graph_plan = compile_task_graph_plan(command.raw_text, created_tick=self.tick)
        if (
            task_graph_plan.graph.status == "rejected"
            and task_graph_plan.graph.rejection_reason is not None
            and _hard_task_graph_rejection(task_graph_plan)
        ):
            self._task_graph_plan = task_graph_plan
            event = EventPayload(
                kind="task_graph_rejected",
                message=f"TaskGraph rejected: {task_graph_plan.graph.rejection_reason}",
                metadata={
                    "category": "event",
                    "action": "task_graph_rejected",
                    "task_graph_id": task_graph_plan.graph.id,
                    "plan_id": task_graph_plan.plan_id,
                    "rejection_reason": task_graph_plan.graph.rejection_reason,
                    "assumptions": task_graph_plan.graph.assumptions,
                },
            )
            self._record_event(event)
            envelope = self._event_envelope(event)
            return GodCommandResponse(
                accepted=False,
                command_id=f"cmd_{uuid4().hex[:8]}",
                category="event",
                event=event,
                envelope=envelope,
                events=[event],
                envelopes=[envelope],
                ai_mode="rules",
                ai_reason="TaskGraph planner rejected the command before execution",
                ai_actions=["task_graph_rejected"],
                task_graph=task_graph_plan,
                task_graph_rejection_reason=task_graph_plan.graph.rejection_reason,
            )

        scenario = compile_scenario_directive(command.raw_text, created_tick=self.tick)
        if scenario is not None:
            effect = self.command_dispatcher.dispatch(command)
            scenario = self._scenario_with_forced_blocker(command.raw_text, scenario)
            self._scenario = scenario
            self._task_graph_plan = task_graph_plan
            self._active_event = "scenario directive"
            graph_event = self._task_graph_planned_event(task_graph_plan)
            self._record_event(graph_event)
            event = EventPayload(
                kind="scenario_directive_created",
                message=f"Scenario directive created: {scenario.title}",
                metadata={
                    "category": "event",
                    "action": "scenario_directive",
                    "scenario_id": scenario.id,
                    "scenario_title": scenario.title,
                    "task_graph_id": task_graph_plan.graph.id,
                    "task_graph_status": task_graph_plan.graph.status,
                    "steps": [step.type for step in scenario.steps],
                    "actors": scenario.actors,
                    "assumptions": task_graph_plan.graph.assumptions,
                    "ai_mode": effect.ai_mode,
                    "ai_actions": list(effect.ai_actions),
                    "ai_confidence": effect.ai_confidence,
                    "ai_reason": effect.ai_reason,
                },
            )
            self._record_event(event)
            envelope = self._event_envelope(event)
            graph_envelope = self._event_envelope(graph_event)
            step_actions = [step.type for step in scenario.steps]
            return GodCommandResponse(
                accepted=True,
                command_id=f"cmd_{uuid4().hex[:8]}",
                category="event",
                event=event,
                envelope=envelope,
                events=[graph_event, event],
                envelopes=[graph_envelope, envelope],
                ai_mode=effect.ai_mode,
                ai_confidence=effect.ai_confidence,
                ai_reason=(
                    effect.ai_reason
                    or "bounded task graph compiled from presenter text"
                ),
                ai_actions=_unique_actions(
                    ["task_graph", "scenario_directive", *list(effect.ai_actions), *step_actions]
                ),
                scenario=scenario,
                task_graph=task_graph_plan,
                task_graph_rejection_reason=task_graph_plan.graph.rejection_reason,
            )

        effect = self.command_dispatcher.dispatch(command)
        graph_response_plan = task_graph_plan
        normal_graph_event: EventPayload | None = None
        if task_graph_plan.graph.status in {"accepted", "clarification_needed"}:
            graph_response_plan = _task_graph_with_status(
                task_graph_plan,
                graph_status="completed",
                node_status="completed",
            )
            self._task_graph_plan = graph_response_plan
            normal_graph_event = self._task_graph_planned_event(graph_response_plan)
        else:
            self._task_graph_plan = task_graph_plan

        events: list[EventPayload] = []
        application_effects = effect.sub_effects or (effect,)
        taxi_destinations: dict[str, str] = {}
        for applied_effect in application_effects:
            if applied_effect.event.metadata.get("action") == "taxi_call":
                passenger_id = str(applied_effect.event.metadata.get("passenger_id", "c01"))
                destination_id = applied_effect.event.metadata.get("destination_citizen_id")
                if destination_id is not None:
                    taxi_destinations[passenger_id] = str(destination_id)

        for applied_effect in application_effects:
            action = applied_effect.event.metadata.get("action")
            defer_meeting_until_taxi_arrival = False
            if action == "meeting":
                source = str(applied_effect.event.metadata.get("source", "c01"))
                target = str(applied_effect.event.metadata.get("target", "c02"))
                if taxi_destinations.get(source) == target:
                    self._pending_taxi_meeting = PendingTaxiMeeting(source, target)
                    applied_effect.event.metadata["deferred_until"] = "taxi_arrival"
                    defer_meeting_until_taxi_arrival = True

            if applied_effect.weather is not None:
                self._weather = applied_effect.weather
                self._weather_lock_until_tick = self.tick + 900
            if applied_effect.active_event is not None and not defer_meeting_until_taxi_arrival:
                self._active_event = applied_effect.active_event
            if applied_effect.infrastructure_status is not None:
                self._infrastructure_status = applied_effect.infrastructure_status
            if action == "meeting" and not defer_meeting_until_taxi_arrival:
                source = str(applied_effect.event.metadata.get("source", "c01"))
                target = str(applied_effect.event.metadata.get("target", "c02"))
                self.citizens.activate_meeting(source, target)
            if action == "taxi_call":
                passenger_id = str(applied_effect.event.metadata.get("passenger_id", "c01"))
                vehicle_id = str(applied_effect.event.metadata.get("vehicle_id", "v01"))
                passenger_name = str(
                    applied_effect.event.metadata.get("passenger_name", passenger_id)
                )
                destination_id = applied_effect.event.metadata.get("destination_citizen_id")
                destination_name = applied_effect.event.metadata.get("destination_citizen_name")
                citizens = self.citizens.world_states(self.tick, self.running)
                passenger = next(
                    (citizen for citizen in citizens if citizen.id == passenger_id),
                    None,
                )
                destination = next(
                    (
                        citizen
                        for citizen in citizens
                        if destination_id is not None and citizen.id == str(destination_id)
                    ),
                    None,
                )
                pickup_xz = (passenger.pos[0], passenger.pos[2]) if passenger else None
                dropoff_xz = (destination.pos[0], destination.pos[2]) if destination else None
                self.citizens.clear_meeting_for(passenger_id)
                self.vehicles.request_taxi(
                    passenger_id,
                    vehicle_id=vehicle_id,
                    passenger_name=passenger_name,
                    pickup_xz=pickup_xz,
                    dropoff_xz=dropoff_xz,
                    dropoff_label=str(destination_name) if destination_name else None,
                    requested_tick=self.tick,
                )
            if applied_effect.event.metadata.get("action") == "traffic_jam":
                self.vehicles.activate_congestion(self.tick)
            for memory in applied_effect.memories:
                events.append(
                    self.citizens.append_memory(
                        memory.citizen_id,
                        memory.text,
                        tick=self.tick,
                        importance=0.72,
                        tags=memory.tags,
                    )
                )
            events.append(applied_effect.event)

        if effect.sub_effects:
            events.append(effect.event)
        if normal_graph_event is not None:
            events.insert(0, normal_graph_event)
        for event in events:
            self._record_event(event)
        envelopes = [self._event_envelope(event) for event in events]
        envelope = envelopes[-1]
        return GodCommandResponse(
            accepted=True,
            command_id=f"cmd_{uuid4().hex[:8]}",
            category=effect.category,
            event=effect.event,
            envelope=envelope,
            events=events,
            envelopes=envelopes,
            ai_mode=effect.ai_mode,
            ai_confidence=effect.ai_confidence,
            ai_reason=effect.ai_reason,
            ai_actions=list(effect.ai_actions),
            task_graph=graph_response_plan,
            task_graph_rejection_reason=graph_response_plan.graph.rejection_reason,
        )

    def _record_event(self, event: EventPayload) -> None:
        self._timeline.append(event)
        self.learning.record_event(event, tick=self.tick)

    def _event_envelope(self, event: EventPayload) -> Envelope:
        return Envelope(
            type=EnvelopeType.EVENT,
            ts=time.time(),
            tick=self.tick,
            payload=event.model_dump(mode="json"),
        )

    async def run(self, broadcast: BroadcastCallback) -> None:
        interval = 1.0 / max(self.config.tick_rate_hz, 0.1)
        while self.running:
            envelope = self.step()
            await broadcast(envelope)
            await self._maybe_run_city_ai(broadcast)
            await asyncio.sleep(interval)


def _metadata_xz(value: object) -> tuple[float, float] | None:
    if not isinstance(value, list | tuple) or len(value) < 2:
        return None
    x, z = value[0], value[1]
    if not isinstance(x, int | float) or not isinstance(z, int | float):
        return None
    return (float(x), float(z))


def _task_graph_with_status(
    plan: TaskGraphPlan,
    *,
    graph_status: str,
    node_status: str,
) -> TaskGraphPlan:
    nodes = [
        node.model_copy(update={"status": node_status})
        for node in plan.graph.nodes
    ]
    graph = plan.graph.model_copy(update={"status": graph_status, "nodes": nodes})
    return plan.model_copy(update={"graph": graph})


def _hard_task_graph_rejection(plan: TaskGraphPlan) -> bool:
    reason = (plan.graph.rejection_reason or "").lower()
    return any(
        marker in reason
        for marker in (
            "unknown actors",
            "circular",
            "contradictory",
            "empty command",
        )
    )


def _unique_actions(actions: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for action in actions:
        if action in seen:
            continue
        seen.add(action)
        result.append(action)
    return result


BLOCKER_TEXT_MARKERS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("taxi_unavailable", ("택시 없음", "택시가 없음", "택시 불가", "taxi unavailable")),
    ("pickup_timeout", ("픽업 지연", "픽업 실패", "pickup timeout")),
    ("low_battery", ("배터리 부족", "low battery")),
    ("drone_delay", ("드론 지연", "드론 늦", "drone delay")),
    ("traffic_delay", ("교통 지연", "정체 지연", "traffic delay")),
    ("group_timeout", ("합류 지연", "group timeout")),
    ("dependency_deadlock", ("의존성 막힘", "deadlock")),
    ("target_unreachable", ("도착 불가", "갈 수 없", "unreachable")),
    ("stuck_vehicle", ("차량 멈춤", "vehicle stuck")),
    ("stuck_actor", ("막힘", "stuck", "못 움직")),
)


def _blocker_type_from_text(raw_text: str) -> str | None:
    lowered = raw_text.lower()
    for blocker_type, markers in BLOCKER_TEXT_MARKERS:
        if any(marker.lower() in lowered for marker in markers):
            return blocker_type
    return None


def _blocker_matches_step(blocker_type: str, step: ScenarioStep) -> bool:
    if blocker_type in {"taxi_unavailable", "pickup_timeout", "stuck_vehicle", "traffic_delay"}:
        return step.type in {"call_taxi", "taxi_pickup", "taxi_drive_to_actor"}
    if blocker_type in {"drone_delay", "low_battery"}:
        return step.type in {"drone_move_to_actor", "drone_deliver"}
    if blocker_type == "group_timeout":
        return step.type in {"move_actor_to_group", "group_rendezvous"}
    if blocker_type == "dependency_deadlock":
        return bool(step.depends_on)
    if blocker_type == "target_unreachable":
        return step.type in {"move_actor_to_actor", "move_actor_to_location", "taxi_drive_to_actor"}
    return step.type in {"move_actor_to_actor", "move_actor_to_location"}


def _learning_action_for_step(step_type: str) -> str:
    if step_type == "traffic_surge":
        return "traffic_jam"
    if step_type == "set_weather":
        return "weather_changed"
    if step_type in {"call_taxi", "taxi_pickup", "taxi_drive_to_actor"}:
        return "taxi_call"
    if step_type in {"meet", "move_actor_to_group", "group_rendezvous"}:
        return "meeting"
    if step_type == "remember":
        return "memory_added"
    return step_type
