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
    checkpoint.write_text(
        json.dumps(
            {
                "policy_version": "traffic-gpu-linear-test",
                "weights": [[1.0, -1.0, 0.0, 0.0, 0.0], [-1.0, 1.0, 0.0, 0.0, 0.0]],
                "bias": [0.0, 0.0],
                "trained_on_gpu": True,
                "training_backend": "torch_cuda",
                "episodes": 10,
                "improvement_pct": 22.5,
                "avg_queue_fixed_cycle": 20.0,
                "avg_queue_candidate": 15.5,
                "detail": "test checkpoint",
            }
        ),
        encoding="utf-8",
    )
    loaded = TrafficPolicyWrapper(checkpoint)

    assert fallback.mode == "pressure_baseline"
    assert fallback.select_action({"ns_queue": 9, "ew_queue": 2, "active_phase": 0, "tick": 0}) == 0
    assert loaded.mode == "checkpoint"
    assert loaded.snapshot(last_action=1).trained_on_gpu is True
    assert loaded.select_action({"ns_queue": 9, "ew_queue": 2, "active_phase": 0, "tick": 0}) == 0
    assert loaded.select_action({"ns_queue": 2, "ew_queue": 9, "active_phase": 0, "tick": 0}) == 1


def test_lstm_forecast_wrapper_returns_schema_payload() -> None:
    forecast = LstmForecastWrapper().predict(tick=12, vehicle_count=4, total_queue=18)

    assert len(forecast) == 3
    assert all(TrafficForecastPoint.model_validate(point.model_dump()) for point in forecast)
    assert forecast[-1].minute_offset == 15


def test_metrics_script_compares_baseline_and_candidate() -> None:
    report = compare_policies(steps=5)

    assert set(report) == {
        "fixed_cycle",
        "pressure_baseline",
        "candidate",
        "improvement_pct_vs_fixed",
    }
    assert "avg_queue" in report["fixed_cycle"]
