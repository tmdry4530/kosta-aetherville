#!/usr/bin/env python3
"""Guarded YOLO pseudo-label self-training entrypoint."""

from __future__ import annotations

import argparse
import json
import os
import time
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--base-model", default=os.getenv("AETHERVILLE_YOLO_MODEL", "yolo11n.pt"))
    parser.add_argument("--epochs", type=int, default=8)
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    if args.dry_run:
        payload = _recipe(args, status="dry_run")
    else:
        if os.getenv("AETHERVILLE_APPROVE_MODEL_TRAINING") != "1":
            raise SystemExit("blocked: set AETHERVILLE_APPROVE_MODEL_TRAINING=1")
        try:
            import ultralytics  # type: ignore[import-not-found]  # noqa: F401
        except ImportError as exc:
            raise SystemExit(
                "blocked: install ultralytics in the training env before YOLO self-training"
            ) from exc
        payload = _recipe(args, status="trainer_dependencies_verified")
        payload["detail"] = (
            "YOLO dependency boundary verified. Convert pseudo-label manifest to "
            "Ultralytics dataset YAML and run model.train in the training window."
        )
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(payload, ensure_ascii=False, indent=2))


def _recipe(args: argparse.Namespace, *, status: str) -> dict[str, object]:
    return {
        "format": "aetherville_yolo_self_training_recipe_v1",
        "target": "yolo",
        "status": status,
        "base_model": args.base_model,
        "dataset": args.dataset,
        "epochs": args.epochs,
        "created_ts": time.time(),
        "pseudo_label_quality": 0.58,
        "training_backend": "dry_run_recipe" if args.dry_run else "ultralytics",
        "detail": "YOLO pseudo-label self-training path generated; no weights changed in dry-run.",
    }


if __name__ == "__main__":
    main()
