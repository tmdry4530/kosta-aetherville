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
    SimStatusResponse,
    VehicleCameraFrame,
    WorldClock,
    WorldStatePayload,
    make_state_update,
)
from aetherville_server.agents import CitizenAgentService
from aetherville_server.orchestrator import GodCommandDispatcher
from aetherville_server.traffic_ai import FixedCycleController, LstmForecastWrapper
from aetherville_server.vehicles import VehicleController

BroadcastCallback = Callable[[Envelope], Awaitable[None]]


@dataclass(frozen=True)
class SimulationConfig:
    tick_rate_hz: float = 10.0
    seed: int = 42
    start_minute: int = 9 * 60 + 30


class SimulationEngine:
    """Small deterministic world model with a configurable async tick loop."""

    def __init__(
        self,
        config: SimulationConfig | None = None,
        citizen_service: CitizenAgentService | None = None,
    ) -> None:
        self.config = config or SimulationConfig()
        self.tick = 0
        self.running = False
        self.speed_multiplier = 1.0
        self._seed = self.config.seed
        self._rng = random.Random(self._seed)
        self._weather = "clear"
        self._temperature = 21.5
        self._active_event: str | None = None
        self._infrastructure_status: str | None = None
        self._timeline: list[EventPayload] = []
        self.citizens = citizen_service or CitizenAgentService(seed=self.config.seed)
        self.vehicles = VehicleController()
        self.traffic_controller = FixedCycleController()
        self.traffic_forecaster = LstmForecastWrapper()
        self.command_dispatcher = GodCommandDispatcher()

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
        self._temperature = 21.5
        self._active_event = None
        self._infrastructure_status = None
        self.citizens = CitizenAgentService(seed=self._seed)
        self.vehicles = VehicleController()
        self.traffic_controller = FixedCycleController()
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
        if self.tick % 120 == 0:
            self._weather = "rain" if self._weather == "clear" else "clear"
            self._timeline.append(
                EventPayload(
                    kind="weather_changed",
                    message=f"weather changed to {self._weather}",
                    metadata={"weather": self._weather, "tick": self.tick},
                )
            )
        if self.tick % 80 == 12:
            self._timeline.append(
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
        total_queue = int(12 + 20 * abs(math.sin(angle)))

        return WorldStatePayload(
            world=WorldClock(
                time_of_day=time_of_day,
                weather=self._weather,
                temperature=self._temperature,
                active_event=self._active_event,
                infrastructure_status=self._infrastructure_status,
            ),
            citizens=self.citizens.world_states(self.tick, self.running),
            vehicles=self.vehicles.vehicle_states(self.tick, self.running),
            drones=[
                DroneState(
                    id="d01",
                    pos=[-2.0, 3.0, 2.0],
                    destination=[2.0, 3.0, -2.0],
                    cargo="medical-kit",
                    battery=0.94,
                )
            ],
            traffic_lights=self.traffic_controller.lights_for_tick(self.tick),
            traffic_forecast=self.traffic_forecaster.predict(
                tick=self.tick,
                vehicle_count=1,
                total_queue=total_queue,
            ),
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

    def execute_god_command(self, command: GodCommand) -> GodCommandResponse:
        effect = self.command_dispatcher.dispatch(command)
        if effect.weather is not None:
            self._weather = effect.weather
        if effect.active_event is not None:
            self._active_event = effect.active_event
        if effect.infrastructure_status is not None:
            self._infrastructure_status = effect.infrastructure_status

        events: list[EventPayload] = []
        for memory in effect.memories:
            events.append(
                self.citizens.append_memory(
                    memory.citizen_id,
                    memory.text,
                    tick=self.tick,
                    importance=0.72,
                    tags=memory.tags,
                )
            )
        events.append(effect.event)
        self._timeline.extend(events)
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
        )

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
