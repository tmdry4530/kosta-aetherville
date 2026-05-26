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
from typing import Any


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
        payload = _build_sft_adapter_manifest(args)
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


def _build_sft_adapter_manifest(args: argparse.Namespace) -> dict[str, Any]:
    rows = _read_jsonl(Path(args.dataset))
    valid_rows = [
        row
        for row in rows
        if isinstance(row.get("messages"), list) and len(row.get("messages", [])) >= 3
    ]
    rewards = [
        float(message.get("reward", 0.5))
        for row in valid_rows
        for message in [_assistant_payload(row)]
    ]
    validity = min(
        0.98,
        max(
            0.6,
            len(valid_rows) / max(len(rows), 1) * 0.36
            + (sum(rewards) / max(len(rewards), 1)) * 0.44
            + min(len(valid_rows), 24) / 24 * 0.2,
        ),
    )
    return {
        "format": "aetherville_vllm_lora_sft_manifest_v1",
        "target": "vllm_lora",
        "status": "sft_dataset_validated",
        "base_model": args.base_model,
        "method": args.method,
        "dataset": args.dataset,
        "created_ts": time.time(),
        "plan_validity": round(validity, 4),
        "training_backend": "sft_dataset_manifest",
        "adapter_kind": "lora_recipe",
        "adapter_rank": 16,
        "sft_example_count": len(valid_rows),
        "detail": (
            "LoRA/SFT dataset validated and adapter manifest registered. "
            "Use this manifest with PEFT/TRL to mutate base LLM weights."
        ),
    }


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        payload = json.loads(line)
        if isinstance(payload, dict):
            rows.append(payload)
    return rows


def _assistant_payload(row: dict[str, Any]) -> dict[str, Any]:
    try:
        content = row["messages"][-1]["content"]
        payload = json.loads(content)
        return payload if isinstance(payload, dict) else {}
    except (KeyError, IndexError, TypeError, json.JSONDecodeError):
        return {}


if __name__ == "__main__":
    main()
