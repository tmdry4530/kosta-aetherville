#!/usr/bin/env python3
"""Run an Aetherville guarded model-training cycle.

Default mode is dry-run: build/evaluate the training handoff without model
weight mutation or GPU spend. Use --execute only after setting
AETHERVILLE_APPROVE_MODEL_TRAINING=1.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.request
from pathlib import Path
from typing import Any, cast

from aetherville_server.training import TrainingPipeline

TARGETS = ["vllm_lora", "yolo", "traffic_ppo", "traffic_lstm"]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--orchestrator-url", help="Optional live orchestrator URL")
    parser.add_argument("--target", action="append", choices=TARGETS, dest="targets")
    parser.add_argument(
        "--execute",
        action="store_true",
        help="Run real trainer jobs; requires approval env",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Run even when experience log is sparse",
    )
    parser.add_argument(
        "--training-dir",
        help="Local training artifact dir when not using orchestrator",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    dry_run = not args.execute
    if args.execute and os.getenv("AETHERVILLE_APPROVE_MODEL_TRAINING") != "1":
        raise SystemExit(
            "blocked: set AETHERVILLE_APPROVE_MODEL_TRAINING=1 before --execute"
        )
    if args.orchestrator_url:
        payload = {
            "dry_run": dry_run,
            "targets": args.targets or [],
            "force": args.force,
        }
        response = _post_json(f"{args.orchestrator_url.rstrip('/')}/api/v1/training/cycle", payload)
    else:
        pipeline = TrainingPipeline(Path(args.training_dir) if args.training_dir else None)
        response = pipeline.run_cycle(
            targets=args.targets,
            dry_run=dry_run,
            force=args.force,
        ).model_dump(mode="json")
    print(json.dumps(response, ensure_ascii=False, indent=2))
    if response.get("status") in {"blocked", "rejected"} and args.execute:
        sys.exit(1)


def _post_json(url: str, payload: dict[str, Any]) -> dict[str, Any]:
    request = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"content-type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        return cast(dict[str, Any], json.loads(response.read().decode("utf-8")))


if __name__ == "__main__":
    main()
