from __future__ import annotations

import asyncio

from aetherville_schemas import Envelope, EnvelopeType, WorldStatePayload
from aetherville_server.sim import SimulationConfig, SimulationEngine


def test_tick_scheduler_step_advances_full_world_state() -> None:
    engine = SimulationEngine(SimulationConfig(seed=7))
    first = engine.step()
    second = engine.step()

    assert first.tick == 1
    assert second.tick == 2
    payload = WorldStatePayload.model_validate(second.payload)
    assert payload.world.time_of_day == "09:30"
    assert payload.citizens
    assert payload.vehicles
    assert payload.drones
    assert payload.traffic_lights
    assert payload.traffic_forecast


def test_reset_is_deterministic_for_same_seed() -> None:
    engine = SimulationEngine(SimulationConfig(seed=1))
    engine.step()
    engine.reset(seed=123)
    state_a = engine.step().payload
    engine.reset(seed=123)
    state_b = engine.step().payload

    assert state_a == state_b


def test_async_run_broadcasts_sequential_ticks() -> None:
    async def scenario() -> list[int]:
        engine = SimulationEngine(SimulationConfig(tick_rate_hz=200))
        ticks: list[int] = []

        async def broadcast(envelope: Envelope) -> None:
            assert envelope.type is EnvelopeType.STATE_UPDATE
            ticks.append(envelope.tick)
            if len(ticks) >= 10:
                engine.stop()

        engine.start()
        await asyncio.wait_for(engine.run(broadcast), timeout=1.0)
        return ticks

    assert asyncio.run(scenario()) == list(range(1, 11))
