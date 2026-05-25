from __future__ import annotations

import asyncio
import json
from pathlib import Path

import pytest

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
    assert len(payload.citizens) == 7
    assert len(payload.vehicles) == 3
    assert payload.drones
    assert len(payload.traffic_lights) == 4
    assert payload.traffic_forecast
    assert payload.traffic_ai.mode == "fixed_cycle"
    assert payload.traffic_forecast_ai.mode == "deterministic_fallback"
    assert payload.learning.mode == "deterministic_online_adaptation"
    assert payload.citizens[0].name == "민지"
    assert payload.citizens[0].display_tags[:2] == ["민지", "인도"]
    assert payload.vehicles[0].display_tags[:2] == ["TAXI", "차도"]


def test_reset_is_deterministic_for_same_seed() -> None:
    engine = SimulationEngine(SimulationConfig(seed=1))
    engine.step()
    engine.reset(seed=123)
    state_a = engine.step().payload
    engine.reset(seed=123)
    state_b = engine.step().payload

    assert state_a == state_b


def test_citizens_follow_waypoint_corridors_not_orbits() -> None:
    engine = SimulationEngine(SimulationConfig(seed=7))

    state_at_start = engine.snapshot()
    engine.tick = 20
    state_later = engine.snapshot()

    first_start = state_at_start.citizens[0]
    first_later = state_later.citizens[0]
    assert first_later.pos[0] > first_start.pos[0]
    assert first_later.pos[2] == first_start.pos[2]
    assert abs(first_later.rot[1] - 1.571) < 0.01
    assert first_later.anim == "idle"
    assert "인도" in first_later.display_tags


def test_simulation_loads_traffic_policy_checkpoint(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    checkpoint = tmp_path / "traffic_policy.json"
    checkpoint.write_text(
        json.dumps(
            {
                "policy_version": "traffic-gpu-linear-test",
                "weights": [[1.0, -1.0, 0.0, 0.0, 0.0], [-1.0, 1.0, 0.0, 0.0, 0.0]],
                "bias": [0.0, 0.0],
                "trained_on_gpu": True,
                "training_backend": "torch_cuda",
                "episodes": 24,
                "improvement_pct": 20.0,
                "avg_queue_fixed_cycle": 30.0,
                "avg_queue_candidate": 24.0,
                "detail": "test checkpoint",
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setenv("AETHERVILLE_TRAFFIC_POLICY_CHECKPOINT", str(checkpoint))

    state = SimulationEngine(SimulationConfig(seed=7)).snapshot()

    assert state.traffic_ai.mode == "checkpoint"
    assert state.traffic_ai.trained_on_gpu is True
    assert state.traffic_ai.last_action in (0, 1)
    assert any("AI정책:checkpoint" in tag for tag in state.traffic_lights[0].display_tags)


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
