"""Comparison metrics for baseline and checkpoint-backed traffic policies."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from aetherville_server.traffic_ai.env import TrafficSignalEnv
from aetherville_server.traffic_ai.policy import TrafficPolicyWrapper


def compare_policies(steps: int = 30, checkpoint_path: str | Path | None = None) -> dict[str, Any]:
    fixed_cycle = _rollout_action_selector(
        "fixed_cycle",
        steps,
        lambda observation: (observation["tick"] // 30) % 2,
    )
    pressure_baseline = _rollout(TrafficPolicyWrapper(), steps)
    candidate = _rollout(TrafficPolicyWrapper(checkpoint_path), steps)
    return {
        "fixed_cycle": fixed_cycle,
        "pressure_baseline": pressure_baseline,
        "candidate": candidate,
        "improvement_pct_vs_fixed": round(
            _improvement(fixed_cycle["avg_queue"], candidate["avg_queue"]), 3
        ),
    }


def _rollout(policy: TrafficPolicyWrapper, steps: int) -> dict[str, float | str]:
    return _rollout_action_selector(policy.mode, steps, policy.select_action)


def _rollout_action_selector(
    mode: str,
    steps: int,
    select_action: Any,
) -> dict[str, float | str]:
    env = TrafficSignalEnv(horizon=steps)
    observation = env.reset()
    reward_sum = 0.0
    queue_sum = 0.0
    for _ in range(steps):
        observation, reward, done, info = env.step(select_action(observation))
        reward_sum += reward
        queue_sum += info["total_queue"]
        if done:
            break
    return {
        "mode": mode,
        "reward_sum": round(reward_sum, 3),
        "avg_queue": round(queue_sum / max(steps, 1), 3),
    }


def _improvement(baseline_avg_queue: float | str, candidate_avg_queue: float | str) -> float:
    baseline = float(baseline_avg_queue)
    candidate = float(candidate_avg_queue)
    if baseline <= 0:
        return 0.0
    return max(0.0, ((baseline - candidate) / baseline) * 100.0)


def main() -> None:
    print(json.dumps(compare_policies(), indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
