"""Train/export a lightweight traffic policy checkpoint with optional CUDA.

This is a demo-safe bridge between the deterministic traffic environment and a
future full PPO stack: training can use PyTorch on the RunPod 4090, while runtime
inference remains a tiny JSON linear policy that the orchestrator can load
without importing GPU libraries.
"""

from __future__ import annotations

import argparse
import json
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

    try:
        import torch  # type: ignore[import-not-found]
        import torch.nn.functional as functional  # type: ignore[import-not-found]
    except ImportError:
        return _pressure_checkpoint(
            episodes=0,
            horizon=horizon,
            trained_on_gpu=False,
            training_backend="json",
            detail="torch unavailable; exported deterministic pressure policy fallback",
        )

    random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)
    if device_preference == "cuda" and not torch.cuda.is_available():
        raise RuntimeError("--device=cuda requested but torch.cuda is unavailable")
    wants_cuda = device_preference == "cuda" or (
        device_preference == "auto" and torch.cuda.is_available()
    )
    device = torch.device("cuda" if wants_cuda else "cpu")

    features, labels = _build_training_set(episodes=episodes, horizon=horizon, seed=seed)
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


if __name__ == "__main__":
    main()
