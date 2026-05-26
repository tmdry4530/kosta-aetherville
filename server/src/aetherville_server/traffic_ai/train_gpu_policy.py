"""Train/export a lightweight traffic policy checkpoint with optional CUDA.

This is a demo-safe bridge between the deterministic traffic environment and a
future full PPO stack: training can use PyTorch on the RunPod 4090, while runtime
inference remains a tiny JSON linear policy that the orchestrator can load
without importing GPU libraries.
"""

from __future__ import annotations

import argparse
import json
import os
import random
import tempfile
from pathlib import Path
from typing import Any

from aetherville_server.traffic_ai.env import TrafficSignalEnv
from aetherville_server.traffic_ai.metrics import compare_policies
from aetherville_server.traffic_ai.policy import FEATURE_NAMES


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, help="checkpoint JSON output path")
    parser.add_argument("--episodes", type=int, default=240)
    parser.add_argument("--horizon", type=int, default=80)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--device", default="auto", choices=["auto", "cuda", "cpu"])
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    checkpoint = train_policy_checkpoint(
        episodes=args.episodes,
        horizon=args.horizon,
        seed=args.seed,
        device_preference=args.device,
    )
    output.write_text(json.dumps(checkpoint, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"output": str(output), **checkpoint}, ensure_ascii=False, indent=2))


def train_policy_checkpoint(
    *,
    episodes: int = 240,
    horizon: int = 80,
    seed: int = 42,
    device_preference: str = "auto",
) -> dict[str, Any]:
    """Return a JSON-serializable checkpoint payload."""

    if episodes <= 0:
        return _pressure_checkpoint(
            episodes=0,
            horizon=horizon,
            trained_on_gpu=False,
            training_backend="json",
            detail="deterministic pressure policy checkpoint",
        )

    random.seed(seed)
    if os.getenv("AETHERVILLE_TRAFFIC_PPO_BACKEND", "stdlib").lower() != "torch_supervised":
        return _train_policy_checkpoint_ppo_stdlib(
            episodes=episodes,
            horizon=horizon,
            seed=seed,
        )

    features, labels = _build_training_set(episodes=episodes, horizon=horizon, seed=seed)
    try:
        import torch  # type: ignore[import-not-found]
        import torch.nn.functional as functional  # type: ignore[import-not-found]
    except ImportError:
        return _train_policy_checkpoint_stdlib(
            features=features,
            labels=labels,
            episodes=episodes,
            horizon=horizon,
        )

    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)
    if device_preference == "cuda" and not torch.cuda.is_available():
        raise RuntimeError("--device=cuda requested but torch.cuda is unavailable")
    wants_cuda = device_preference == "cuda" or (
        device_preference == "auto" and torch.cuda.is_available()
    )
    device = torch.device("cuda" if wants_cuda else "cpu")

    x = torch.tensor(features, dtype=torch.float32, device=device)
    y = torch.tensor(labels, dtype=torch.long, device=device)
    model = torch.nn.Linear(len(FEATURE_NAMES), 2, device=device)
    optimizer = torch.optim.AdamW(model.parameters(), lr=0.04, weight_decay=0.001)

    last_loss = 0.0
    for _ in range(220):
        optimizer.zero_grad(set_to_none=True)
        logits = model(x)
        loss = functional.cross_entropy(logits, y)
        loss.backward()
        optimizer.step()
        last_loss = float(loss.detach().cpu())

    weights = model.weight.detach().cpu().tolist()
    bias = model.bias.detach().cpu().tolist()
    trained_payload = _payload_from_weights(
        weights=weights,
        bias=bias,
        episodes=episodes,
        horizon=horizon,
        trained_on_gpu=device.type == "cuda",
        training_backend=f"torch_{device.type}",
        detail=(
            "RunPod CUDA-trained linear traffic policy"
            if device.type == "cuda"
            else "CPU-trained linear traffic policy"
        ),
        loss=last_loss,
    )

    if float(trained_payload["improvement_pct"]) <= 0:
        fallback = _pressure_checkpoint(
            episodes=episodes,
            horizon=horizon,
            trained_on_gpu=device.type == "cuda",
            training_backend=f"torch_{device.type}",
            detail="trained model underperformed; exported pressure-policy safety checkpoint",
        )
        fallback["training_loss"] = last_loss
        fallback["selection"] = "safety_pressure_policy"
        return fallback

    trained_payload["selection"] = "trained_linear_policy"
    return trained_payload


def _train_policy_checkpoint_stdlib(
    *,
    features: list[list[float]],
    labels: list[int],
    episodes: int,
    horizon: int,
) -> dict[str, Any]:
    """Train a tiny softmax policy from real environment rollouts without torch.

    This is not a full PPO optimizer, but it does perform an actual rollout
    collection + gradient update cycle and exports the same lightweight runtime
    checkpoint shape.  H100 runs with torch can still use the CUDA path above.
    """

    weights = [[0.0 for _ in FEATURE_NAMES], [0.0 for _ in FEATURE_NAMES]]
    bias = [0.0, 0.0]
    learning_rate = 0.08
    last_loss = 0.0
    for _epoch in range(120):
        total_loss = 0.0
        for row, label in zip(features, labels, strict=True):
            score0 = (
                sum(weight * value for weight, value in zip(weights[0], row, strict=True))
                + bias[0]
            )
            score1 = (
                sum(weight * value for weight, value in zip(weights[1], row, strict=True))
                + bias[1]
            )
            max_score = max(score0, score1)
            exp0 = pow(2.718281828459045, score0 - max_score)
            exp1 = pow(2.718281828459045, score1 - max_score)
            denom = exp0 + exp1
            prob0 = exp0 / denom
            prob1 = exp1 / denom
            target0 = 1.0 if label == 0 else 0.0
            target1 = 1.0 - target0
            total_loss += -(
                target0 * _safe_log(prob0)
                + target1 * _safe_log(prob1)
            )
            grad0 = prob0 - target0
            grad1 = prob1 - target1
            for index, value in enumerate(row):
                weights[0][index] -= learning_rate * grad0 * value
                weights[1][index] -= learning_rate * grad1 * value
            bias[0] -= learning_rate * grad0
            bias[1] -= learning_rate * grad1
        last_loss = total_loss / max(len(features), 1)
        learning_rate *= 0.985

    payload = _payload_from_weights(
        weights=weights,
        bias=bias,
        episodes=episodes,
        horizon=horizon,
        trained_on_gpu=False,
        training_backend="json",
        detail="stdlib rollout-trained linear traffic policy",
        loss=last_loss,
    )
    payload["selection"] = "stdlib_rollout_policy"
    return payload


def _train_policy_checkpoint_ppo_stdlib(
    *,
    episodes: int,
    horizon: int,
    seed: int,
) -> dict[str, Any]:
    """Run a bounded PPO-style rollout update without heavyweight deps."""

    rng = random.Random(seed)
    weights = [
        [0.35, -0.35, -0.04, 0.0, 0.0],
        [-0.35, 0.35, 0.04, 0.0, 0.0],
    ]
    bias = [0.0, 0.0]
    learning_rate = 0.035
    clip_epsilon = 0.2
    rollout_steps = 0
    reward_total = 0.0
    for _episode in range(episodes):
        env = TrafficSignalEnv(horizon=horizon)
        observation = env.reset()
        episode_rewards: list[float] = []
        episode_rows: list[tuple[list[float], int, float]] = []
        for _step in range(horizon):
            row = _features(observation)
            prob0, prob1 = _policy_probs(weights, bias, row)
            action = 0 if rng.random() <= prob0 else 1
            next_observation, reward, done, _info = env.step(action)
            episode_rows.append((row, action, prob0 if action == 0 else prob1))
            episode_rewards.append(float(reward))
            reward_total += float(reward)
            rollout_steps += 1
            observation = next_observation
            if done:
                break
        baseline = sum(episode_rewards) / max(len(episode_rewards), 1)
        for (row, action, old_prob), reward in zip(episode_rows, episode_rewards, strict=True):
            advantage = max(-1.0, min(1.0, (reward - baseline) / 25.0))
            prob0, prob1 = _policy_probs(weights, bias, row)
            current_prob = prob0 if action == 0 else prob1
            ratio = current_prob / max(old_prob, 1e-6)
            clipped_ratio = max(1.0 - clip_epsilon, min(1.0 + clip_epsilon, ratio))
            scale = -advantage * clipped_ratio
            grad0 = (prob0 - (1.0 if action == 0 else 0.0)) * scale
            grad1 = (prob1 - (1.0 if action == 1 else 0.0)) * scale
            for index, value in enumerate(row):
                weights[0][index] -= learning_rate * grad0 * value
                weights[1][index] -= learning_rate * grad1 * value
            bias[0] -= learning_rate * grad0
            bias[1] -= learning_rate * grad1
        learning_rate *= 0.995

    payload = _payload_from_weights(
        weights=weights,
        bias=bias,
        episodes=episodes,
        horizon=horizon,
        trained_on_gpu=False,
        training_backend="json",
        detail="stdlib PPO-style rollout-trained traffic policy",
        loss=None,
    )
    payload["selection"] = "ppo_style_rollout_policy"
    payload["algorithm"] = "clipped_policy_gradient_smoke"
    payload["ppo_clip_epsilon"] = clip_epsilon
    payload["rollout_steps"] = rollout_steps
    payload["mean_rollout_reward"] = round(reward_total / max(rollout_steps, 1), 6)
    if float(payload["improvement_pct"]) <= 0:
        fallback = _pressure_checkpoint(
            episodes=episodes,
            horizon=horizon,
            trained_on_gpu=False,
            training_backend="json",
            detail="PPO-style policy underperformed; exported pressure-policy safety checkpoint",
        )
        fallback["selection"] = "ppo_safety_pressure_policy"
        fallback["algorithm"] = "clipped_policy_gradient_smoke"
        fallback["ppo_clip_epsilon"] = clip_epsilon
        fallback["rollout_steps"] = rollout_steps
        fallback["mean_rollout_reward"] = round(reward_total / max(rollout_steps, 1), 6)
        return fallback
    return payload


def _build_training_set(
    *,
    episodes: int,
    horizon: int,
    seed: int,
) -> tuple[list[list[float]], list[int]]:
    rng = random.Random(seed)
    features: list[list[float]] = []
    labels: list[int] = []
    for episode in range(episodes):
        env = TrafficSignalEnv(horizon=horizon)
        observation = env.reset()
        for step in range(horizon):
            features.append(_features(observation))
            labels.append(0 if observation["ns_queue"] >= observation["ew_queue"] else 1)
            if episode % 3 == 0:
                action = rng.randint(0, 1)
            elif episode % 3 == 1:
                action = step % 2
            else:
                action = labels[-1]
            observation, _, done, _ = env.step(action)
            if done:
                break
    return features, labels


def _payload_from_weights(
    *,
    weights: list[list[float]],
    bias: list[float],
    episodes: int,
    horizon: int,
    trained_on_gpu: bool,
    training_backend: str,
    detail: str,
    loss: float | None = None,
) -> dict[str, Any]:
    with tempfile.TemporaryDirectory(prefix="aetherville-traffic-") as temp_dir:
        checkpoint_path = Path(temp_dir) / "candidate.json"
        checkpoint_path.write_text(
            json.dumps({"weights": weights, "bias": bias}, ensure_ascii=False),
            encoding="utf-8",
        )
        metrics = compare_policies(steps=horizon, checkpoint_path=checkpoint_path)

    fixed = float(metrics["fixed_cycle"]["avg_queue"])
    candidate = float(metrics["candidate"]["avg_queue"])
    improvement = float(metrics["improvement_pct_vs_fixed"])
    payload: dict[str, Any] = {
        "format": "aetherville_traffic_policy_v1",
        "policy_version": "traffic-gpu-linear-v1",
        "policy_kind": "linear_queue_actor",
        "feature_names": list(FEATURE_NAMES),
        "weights": weights,
        "bias": bias,
        "trained_on_gpu": trained_on_gpu,
        "training_backend": training_backend,
        "episodes": episodes,
        "horizon": horizon,
        "avg_queue_fixed_cycle": fixed,
        "avg_queue_candidate": candidate,
        "improvement_pct": improvement,
        "detail": detail,
    }
    if loss is not None:
        payload["training_loss"] = round(loss, 6)
    return payload


def _pressure_checkpoint(
    *,
    episodes: int,
    horizon: int,
    trained_on_gpu: bool,
    training_backend: str,
    detail: str,
) -> dict[str, Any]:
    return _payload_from_weights(
        weights=[
            [1.0, -1.0, 0.0, 0.0, 0.0],
            [-1.0, 1.0, 0.0, 0.0, 0.0],
        ],
        bias=[0.0, 0.0],
        episodes=episodes,
        horizon=horizon,
        trained_on_gpu=trained_on_gpu,
        training_backend=training_backend,
        detail=detail,
    )


def _features(observation: dict[str, int]) -> list[float]:
    return [
        observation["ns_queue"] / 80.0,
        observation["ew_queue"] / 80.0,
        float(observation["active_phase"]),
        min(1.0, observation["tick"] / 120.0),
        1.0,
    ]


def _policy_probs(
    weights: list[list[float]],
    bias: list[float],
    row: list[float],
) -> tuple[float, float]:
    score0 = sum(weight * value for weight, value in zip(weights[0], row, strict=True)) + bias[0]
    score1 = sum(weight * value for weight, value in zip(weights[1], row, strict=True)) + bias[1]
    max_score = max(score0, score1)
    exp0 = pow(2.718281828459045, score0 - max_score)
    exp1 = pow(2.718281828459045, score1 - max_score)
    denom = exp0 + exp1
    return exp0 / denom, exp1 / denom


def _safe_log(value: float) -> float:
    import math

    return math.log(max(value, 1e-9))


if __name__ == "__main__":
    main()
