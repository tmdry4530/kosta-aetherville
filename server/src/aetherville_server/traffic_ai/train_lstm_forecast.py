"""Train/export a lightweight LSTM traffic forecast checkpoint with optional CUDA."""

from __future__ import annotations

import argparse
import json
import math
import random
from pathlib import Path
from typing import Any

FEATURE_NAMES = ["sin_tick", "cos_tick", "vehicle_count", "total_queue", "bias"]
HORIZON_MINUTES = [5, 10, 15]
EXPECTED_SCALE = 140.0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True)
    parser.add_argument("--samples", type=int, default=960)
    parser.add_argument("--epochs", type=int, default=180)
    parser.add_argument("--sequence-length", type=int, default=12)
    parser.add_argument("--hidden-size", type=int, default=10)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--device", default="auto", choices=["auto", "cuda", "cpu"])
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    payload = train_lstm_forecast_checkpoint(
        samples=args.samples,
        epochs=args.epochs,
        sequence_length=args.sequence_length,
        hidden_size=args.hidden_size,
        seed=args.seed,
        device_preference=args.device,
    )
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "output": str(output),
                "forecast_version": payload["forecast_version"],
                "trained_on_gpu": payload["trained_on_gpu"],
                "training_backend": payload["training_backend"],
                "samples": payload["samples"],
                "epochs": payload["epochs"],
                "training_loss": payload["training_loss"],
                "mape": payload["mape"],
                "detail": payload["detail"],
            },
            ensure_ascii=False,
            indent=2,
        )
    )


def train_lstm_forecast_checkpoint(
    *,
    samples: int = 960,
    epochs: int = 180,
    sequence_length: int = 12,
    hidden_size: int = 10,
    seed: int = 42,
    device_preference: str = "auto",
) -> dict[str, Any]:
    try:
        import torch  # type: ignore[import-not-found]
    except ImportError:
        return _fallback_checkpoint(
            samples=samples,
            epochs=0,
            sequence_length=sequence_length,
            hidden_size=hidden_size,
            detail="torch unavailable; exported deterministic LSTM-shaped fallback",
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

    features, targets = _build_dataset(samples=samples, sequence_length=sequence_length, seed=seed)
    x = torch.tensor(features, dtype=torch.float32, device=device)
    y = torch.tensor(targets, dtype=torch.float32, device=device)
    model = torch.nn.LSTM(input_size=len(FEATURE_NAMES), hidden_size=hidden_size, batch_first=True)
    head = torch.nn.Linear(hidden_size, len(HORIZON_MINUTES) * 2)
    model.to(device)
    head.to(device)
    optimizer = torch.optim.AdamW(
        [*model.parameters(), *head.parameters()],
        lr=0.025,
        weight_decay=0.0005,
    )
    loss_fn = torch.nn.MSELoss()

    last_loss = 0.0
    for _ in range(epochs):
        optimizer.zero_grad(set_to_none=True)
        encoded, _ = model(x)
        prediction = head(encoded[:, -1, :])
        loss = loss_fn(prediction, y)
        loss.backward()
        optimizer.step()
        last_loss = float(loss.detach().cpu())

    with torch.no_grad():
        encoded, _ = model(x)
        prediction = head(encoded[:, -1, :]).detach().cpu().tolist()
    mape = _mape(prediction, targets)
    return _checkpoint_from_model(
        model=model,
        head=head,
        samples=samples,
        epochs=epochs,
        sequence_length=sequence_length,
        hidden_size=hidden_size,
        trained_on_gpu=device.type == "cuda",
        training_backend=f"torch_{device.type}",
        training_loss=last_loss,
        mape=mape,
        detail=(
            "RunPod CUDA-trained LSTM traffic forecast"
            if device.type == "cuda"
            else "CPU-trained LSTM traffic forecast"
        ),
    )


def _build_dataset(
    *,
    samples: int,
    sequence_length: int,
    seed: int,
) -> tuple[list[list[list[float]]], list[list[float]]]:
    rng = random.Random(seed)
    features: list[list[list[float]]] = []
    targets: list[list[float]] = []
    for _index in range(samples):
        start_tick = rng.randint(0, 1600)
        base_vehicle_count = rng.randint(3, 9)
        congestion_bias = rng.uniform(0.0, 28.0)
        sequence: list[list[float]] = []
        for offset in range(sequence_length):
            tick = start_tick + offset
            total_queue = _queue_at_tick(tick, congestion_bias)
            sequence.append(_features(tick, base_vehicle_count, total_queue))
        final_tick = start_tick + sequence_length - 1
        targets.append(_target(final_tick, base_vehicle_count, congestion_bias))
        features.append(sequence)
    return features, targets


def _features(tick: int, vehicle_count: int, total_queue: float) -> list[float]:
    return [
        math.sin(tick * 0.04),
        math.cos(tick * 0.04),
        vehicle_count / 10.0,
        total_queue / 120.0,
        1.0,
    ]


def _target(tick: int, vehicle_count: int, congestion_bias: float) -> list[float]:
    expected_values: list[float] = []
    congestion_values: list[float] = []
    for minute in HORIZON_MINUTES:
        future_tick = tick + minute * 12
        total_queue = _queue_at_tick(future_tick, congestion_bias)
        wave = abs(math.sin(future_tick * 0.04))
        expected = vehicle_count + total_queue + 18 + minute * 1.8 + wave * 12
        congestion = min(1.0, 0.18 + total_queue / 80 + wave * 0.28)
        expected_values.append(_logit(max(0.001, min(0.999, expected / EXPECTED_SCALE))))
        congestion_values.append(_logit(max(0.001, min(0.999, congestion))))
    return [*expected_values, *congestion_values]


def _queue_at_tick(tick: int, congestion_bias: float) -> float:
    wave = abs(math.sin(tick * 0.08))
    rush = 22.0 if 450 <= tick % 900 <= 620 else 0.0
    return 12.0 + 20.0 * wave + congestion_bias + rush


def _checkpoint_from_model(
    *,
    model: Any,
    head: Any,
    samples: int,
    epochs: int,
    sequence_length: int,
    hidden_size: int,
    trained_on_gpu: bool,
    training_backend: str,
    training_loss: float,
    mape: float,
    detail: str,
) -> dict[str, Any]:
    state = model.state_dict()
    head_state = head.state_dict()
    return {
        "format": "aetherville_traffic_lstm_v1",
        "forecast_version": "traffic-lstm-v1",
        "feature_names": FEATURE_NAMES,
        "horizon_minutes": HORIZON_MINUTES,
        "expected_scale": EXPECTED_SCALE,
        "sequence_length": sequence_length,
        "hidden_size": hidden_size,
        "lstm": {
            "weight_ih": state["weight_ih_l0"].detach().cpu().tolist(),
            "weight_hh": state["weight_hh_l0"].detach().cpu().tolist(),
            "bias_ih": state["bias_ih_l0"].detach().cpu().tolist(),
            "bias_hh": state["bias_hh_l0"].detach().cpu().tolist(),
        },
        "head": {
            "weight": head_state["weight"].detach().cpu().tolist(),
            "bias": head_state["bias"].detach().cpu().tolist(),
        },
        "trained_on_gpu": trained_on_gpu,
        "training_backend": training_backend,
        "samples": samples,
        "epochs": epochs,
        "training_loss": round(training_loss, 6),
        "mape": round(mape, 3),
        "detail": detail,
    }


def _fallback_checkpoint(
    *,
    samples: int,
    epochs: int,
    sequence_length: int,
    hidden_size: int,
    detail: str,
) -> dict[str, Any]:
    return {
        "format": "aetherville_traffic_lstm_v1",
        "forecast_version": "traffic-lstm-fallback-v1",
        "feature_names": FEATURE_NAMES,
        "horizon_minutes": HORIZON_MINUTES,
        "expected_scale": EXPECTED_SCALE,
        "sequence_length": sequence_length,
        "hidden_size": hidden_size,
        "lstm": {
            "weight_ih": [[0.0 for _ in FEATURE_NAMES] for _ in range(hidden_size * 4)],
            "weight_hh": [[0.0 for _ in range(hidden_size)] for _ in range(hidden_size * 4)],
            "bias_ih": [0.0 for _ in range(hidden_size * 4)],
            "bias_hh": [0.0 for _ in range(hidden_size * 4)],
        },
        "head": {
            "weight": [[0.0 for _ in range(hidden_size)] for _ in range(len(HORIZON_MINUTES) * 2)],
            "bias": [
                _logit(0.42),
                _logit(0.48),
                _logit(0.54),
                _logit(0.35),
                _logit(0.42),
                _logit(0.5),
            ],
        },
        "trained_on_gpu": False,
        "training_backend": "json",
        "samples": samples,
        "epochs": epochs,
        "training_loss": None,
        "mape": None,
        "detail": detail,
    }


def _mape(predictions: list[list[float]], targets: list[list[float]]) -> float:
    expected_errors: list[float] = []
    for prediction, target in zip(predictions, targets, strict=True):
        for pred_value, target_value in zip(prediction[:3], target[:3], strict=True):
            predicted = _sigmoid(pred_value) * EXPECTED_SCALE
            actual = _sigmoid(target_value) * EXPECTED_SCALE
            expected_errors.append(abs(predicted - actual) / max(actual, 0.001))
    return sum(expected_errors) / max(len(expected_errors), 1) * 100.0


def _sigmoid(value: float) -> float:
    if value >= 0:
        z = math.exp(-value)
        return 1.0 / (1.0 + z)
    z = math.exp(value)
    return z / (1.0 + z)


def _logit(value: float) -> float:
    return math.log(value / (1.0 - value))


if __name__ == "__main__":
    main()
