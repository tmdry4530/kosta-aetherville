"""Comparison metrics for baseline and checkpoint-backed traffic policies."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from aetherville_server.traffic_ai.env import TrafficSignalEnv
from aetherville_server.traffic_ai.policy import TrafficPolicyWrapper


def compare_policies(steps: int = 30, checkpoint_path: str | Path | None = None) -> dict[str, Any]:
    baseline = _rollout(TrafficPolicyWrapper(), steps)
    candidate = _rollout(TrafficPolicyWrapper(checkpoint_path), steps)
    return {"baseline": baseline, "candidate": candidate}


def _rollout(policy: TrafficPolicyWrapper, steps: int) -> dict[str, float | str]:
    env = TrafficSignalEnv(horizon=steps)
    observation = env.reset()
    reward_sum = 0.0
    queue_sum = 0.0
    for _ in range(steps):
        observation, reward, done, info = env.step(policy.select_action(observation))
        reward_sum += reward
        queue_sum += info["total_queue"]
        if done:
            break
    return {
        "mode": policy.mode,
        "reward_sum": round(reward_sum, 3),
        "avg_queue": round(queue_sum / max(steps, 1), 3),
    }


def main() -> None:
    print(json.dumps(compare_policies(), indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
