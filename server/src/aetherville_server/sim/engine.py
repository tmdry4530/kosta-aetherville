"""Deterministic simulation engine for the first playable Aetherville slice."""

from __future__ import annotations

import asyncio
import math
import random
import time
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from uuid import uuid4

from aetherville_schemas import (
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


class SimulationEngine:
    """Small deterministic world model with a configurable async tick loop."""

    def __init__(
        self,
        config: SimulationConfig | None = None,
        citizen_service: CitizenAgentService | None = None,
        learning_store: LearningStore | None = None,
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
        for applied_effect in application_effects:
            if applied_effect.weather is not None:
                self._weather = applied_effect.weather
                self._weather_lock_until_tick = self.tick + 900
            if applied_effect.active_event is not None:
                self._active_event = applied_effect.active_event
            if applied_effect.infrastructure_status is not None:
                self._infrastructure_status = applied_effect.infrastructure_status
            if applied_effect.event.metadata.get("action") == "meeting":
                source = str(applied_effect.event.metadata.get("source", "c01"))
                target = str(applied_effect.event.metadata.get("target", "c02"))
                self.citizens.activate_meeting(source, target)
            if applied_effect.event.metadata.get("action") == "taxi_call":
                passenger_id = str(applied_effect.event.metadata.get("passenger_id", "c01"))
                vehicle_id = str(applied_effect.event.metadata.get("vehicle_id", "v01"))
                passenger = next(
                    (
                        citizen
                        for citizen in self.citizens.world_states(self.tick, self.running)
                        if citizen.id == passenger_id
                    ),
                    None,
                )
                pickup_xz = (passenger.pos[0], passenger.pos[2]) if passenger else None
                self.vehicles.request_taxi(
                    passenger_id,
                    vehicle_id=vehicle_id,
                    pickup_xz=pickup_xz,
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
            await asyncio.sleep(interval)
