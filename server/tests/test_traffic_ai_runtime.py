from __future__ import annotations

import json
from pathlib import Path

from aetherville_server.traffic_ai.env import TrafficSignalEnv
from aetherville_server.traffic_ai.metrics import compare_policies
from aetherville_server.traffic_ai.policy import TrafficPolicyWrapper
from aetherville_server.traffic_ai.train_gpu_policy import train_policy_checkpoint


def test_traffic_env_reset_step_contract() -> None:
    env = TrafficSignalEnv(horizon=3)
    observation = env.reset()

    assert observation == {"ns_queue": 4, "ew_queue": 6, "active_phase": 0, "tick": 0}

    next_observation, reward, done, info = env.step(1)

    assert next_observation["active_phase"] == 1
    assert reward < 0
    assert done is False
    assert info["total_queue"] > 0


def test_policy_checkpoint_loads_linear_weights(tmp_path: Path) -> None:
    checkpoint = tmp_path / "traffic_policy.json"
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

    policy = TrafficPolicyWrapper(checkpoint)

    assert policy.select_action({"ns_queue": 20, "ew_queue": 3, "active_phase": 1, "tick": 5}) == 0
    assert policy.select_action({"ns_queue": 2, "ew_queue": 18, "active_phase": 0, "tick": 6}) == 1
    snapshot = policy.snapshot(last_action=1)
    assert snapshot.mode == "checkpoint"
    assert snapshot.trained_on_gpu is True
    assert snapshot.policy_version == "traffic-gpu-linear-test"
    assert snapshot.last_action == 1


def test_policy_metrics_compare_against_fixed_cycle(tmp_path: Path) -> None:
    checkpoint = tmp_path / "traffic_policy.json"
    payload = train_policy_checkpoint(episodes=0, horizon=30)
    checkpoint.write_text(json.dumps(payload), encoding="utf-8")

    metrics = compare_policies(steps=30, checkpoint_path=checkpoint)

    assert metrics["fixed_cycle"]["mode"] == "fixed_cycle"
    assert metrics["candidate"]["mode"] == "checkpoint"
    assert metrics["improvement_pct_vs_fixed"] >= 0
