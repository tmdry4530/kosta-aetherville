"""Deterministic simulation engine for the first playable Aetherville slice."""

from __future__ import annotations

import asyncio
import math
import os
import random
import time
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Literal
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
    Envelope,
    EnvelopeType,
    EventPayload,
    GodCommand,
    GodCommandResponse,
    LearningStatusResponse,
    SimStatusResponse,
    TrafficAiSnapshot,
    VehicleCameraFrame,
    WorldClock,
    WorldStatePayload,
    make_state_update,
)
from aetherville_server.agents import CitizenAgentService
from aetherville_server.city_ai import CityPlanner, city_planner_from_env
from aetherville_server.learning import LearningStore
from aetherville_server.llm import planner_from_env
from aetherville_server.orchestrator import GodCommandDispatcher
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

        return WorldStatePayload(
            world=WorldClock(
                time_of_day=time_of_day,
                weather=self._weather,
                temperature=self._temperature,
                active_event=self._active_event,
                infrastructure_status=self._infrastructure_status,
            ),
            citizens=self.citizens.world_states(self.tick, self.running),
            vehicles=vehicles,
            drones=[
                DroneState(
                    id="d01",
                    pos=[-2.0, 3.0, 2.0],
                    destination=[2.0, 3.0, -2.0],
                    cargo="medical-kit",
                    battery=0.94,
                )
            ],
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
        effect = self.command_dispatcher.dispatch(command)

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
