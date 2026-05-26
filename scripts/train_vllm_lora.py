#!/usr/bin/env python3
"""Guarded vLLM/LLM LoRA training entrypoint.

Dry-run writes a trainer recipe. Real LoRA/SFT/DPO requires optional packages
(transformers/peft/datasets/trl or an equivalent trainer image) and explicit
AETHERVILLE_APPROVE_MODEL_TRAINING=1. This script is intentionally dependency
optional so the demo runtime does not pull model-training stacks by accident.
"""

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
    parser.add_argument(
        "--base-model",
        default=os.getenv("MODEL_NAME", "Qwen/Qwen2.5-14B-Instruct-AWQ"),
    )
    parser.add_argument("--method", choices=["sft", "dpo"], default="sft")
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
            import datasets  # type: ignore[import-not-found]  # noqa: F401
            import peft  # type: ignore[import-not-found]  # noqa: F401
            import transformers  # type: ignore[import-not-found]  # noqa: F401
        except ImportError as exc:
            raise SystemExit(
                "blocked: install optional LoRA trainer dependencies in the training env "
                "or run this through a trainer image; missing " + (exc.name or "unknown")
            ) from exc
        payload = _recipe(args, status="trainer_dependencies_verified")
        payload["detail"] = (
            "LoRA trainer dependency boundary verified. Wire project-specific "
            "SFT/DPO training loop here or run the generated dataset with TRL/PEFT."
        )
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(payload, ensure_ascii=False, indent=2))


def _recipe(args: argparse.Namespace, *, status: str) -> dict[str, object]:
    return {
        "format": "aetherville_vllm_lora_checkpoint_recipe_v1",
        "target": "vllm_lora",
        "status": status,
        "base_model": args.base_model,
        "method": args.method,
        "dataset": args.dataset,
        "created_ts": time.time(),
        "plan_validity": 0.62,
        "training_backend": "dry_run_recipe" if args.dry_run else "optional_peft_trl",
        "detail": "LoRA/SFT/DPO command path generated; no weights changed in dry-run.",
    }


if __name__ == "__main__":
    main()
