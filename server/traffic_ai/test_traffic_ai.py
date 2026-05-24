from __future__ import annotations

import json
from pathlib import Path

from aetherville_schemas import TrafficForecastPoint
from aetherville_server.traffic_ai import (
    FixedCycleController,
    LstmForecastWrapper,
    TrafficPolicyWrapper,
    TrafficSignalEnv,
)
from aetherville_server.traffic_ai.metrics import compare_policies


def test_fixed_cycle_baseline_switches_phases() -> None:
    controller = FixedCycleController(cycle_seconds=30, yellow_seconds=4)

    early = controller.lights_for_tick(2)
    late = controller.lights_for_tick(31)
    yellow = controller.lights_for_tick(28)

    assert early[0].state == "green"
    assert late[0].state == "red"
    assert late[1].state == "green"
    assert yellow[0].state == "yellow"


def test_traffic_signal_env_reset_and_step() -> None:
    env = TrafficSignalEnv(horizon=2)

    observation = env.reset()
    next_observation, reward, done, info = env.step(1)

    assert observation["tick"] == 0
    assert next_observation["active_phase"] == 1
    assert reward < 0
    assert done is False
    assert info["total_queue"] >= 0


def test_policy_wrapper_loads_checkpoint_or_falls_back(tmp_path: Path) -> None:
    fallback = TrafficPolicyWrapper()
    checkpoint = tmp_path / "ppo-policy.json"
    checkpoint.write_text(json.dumps({"preferred_action": 1}), encoding="utf-8")
    loaded = TrafficPolicyWrapper(checkpoint)

    assert fallback.mode == "baseline"
    assert fallback.select_action({"ns_queue": 9, "ew_queue": 2, "active_phase": 0, "tick": 0}) == 0
    assert loaded.mode == "checkpoint"
    assert loaded.select_action({"ns_queue": 9, "ew_queue": 2, "active_phase": 0, "tick": 0}) == 1


def test_lstm_forecast_wrapper_returns_schema_payload() -> None:
    forecast = LstmForecastWrapper().predict(tick=12, vehicle_count=4, total_queue=18)

    assert len(forecast) == 3
    assert all(TrafficForecastPoint.model_validate(point.model_dump()) for point in forecast)
    assert forecast[-1].minute_offset == 15


def test_metrics_script_compares_baseline_and_candidate() -> None:
    report = compare_policies(steps=5)

    assert set(report) == {"baseline", "candidate"}
    assert "avg_queue" in report["baseline"]
