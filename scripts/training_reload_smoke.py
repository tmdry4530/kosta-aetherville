#!/usr/bin/env python3
"""Verify promoted training checkpoints can be reloaded by the runtime."""

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
    parser.add_argument("--orchestrator-url", help="Live orchestrator URL")
    parser.add_argument("--training-dir", help="Local training dir when not using orchestrator")
    parser.add_argument("--target", action="append", choices=TARGETS, dest="targets")
    parser.add_argument("--execute", action="store_true", help="Run non-dry-run trainer cycle")
    parser.add_argument("--force", action="store_true", help="Run with sparse/empty experience log")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    targets = args.targets or ["traffic_ppo", "traffic_lstm"]
    if args.execute and os.getenv("AETHERVILLE_APPROVE_MODEL_TRAINING") != "1":
        raise SystemExit("blocked: set AETHERVILLE_APPROVE_MODEL_TRAINING=1 before --execute")

    if args.orchestrator_url:
        base = args.orchestrator_url.rstrip("/")
        cycle = _post_json(
            f"{base}/api/v1/training/cycle",
            {"dry_run": not args.execute, "targets": targets, "force": args.force},
        )
        if args.execute and cycle.get("status") not in {"promoted", "rejected"}:
            raise SystemExit(f"unexpected training status: {cycle.get('status')}")
        reload_response = _post_json(
            f"{base}/api/v1/runtime/reload",
            {"targets": targets, "reason": "training reload smoke"},
        )
        state = _get_json(f"{base}/api/v1/sim/state")
    else:
        pipeline = TrainingPipeline(Path(args.training_dir) if args.training_dir else None)
        cycle = pipeline.run_cycle(
            targets=targets,
            dry_run=not args.execute,
            force=args.force,
        ).model_dump(mode="json")
        reload_response = {
            "accepted": False,
            "message": (
                "local pipeline cycle completed; runtime reload requires orchestrator-url "
                "or direct SimulationEngine test"
            ),
            "reloaded": [],
        }
        state = {}

    print(
        json.dumps(
            {
                "cycle_status": cycle.get("status"),
                "reload": reload_response,
                "traffic_ai": state.get("traffic_ai"),
                "traffic_forecast_ai": state.get("traffic_forecast_ai"),
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    if args.orchestrator_url:
        _assert_runtime_reload(targets, reload_response, state)


def _assert_runtime_reload(
    targets: list[str],
    reload_response: dict[str, Any],
    state: dict[str, Any],
) -> None:
    reloaded = {item.get("target"): item for item in reload_response.get("reloaded", [])}
    missing = [target for target in targets if target not in reloaded]
    if missing:
        raise SystemExit(f"reload response missing targets: {missing}")
    if "traffic_ppo" in targets and not state.get("traffic_ai", {}).get("checkpoint_loaded"):
        raise SystemExit("traffic PPO checkpoint was not loaded into runtime")
    if "traffic_lstm" in targets and not state.get("traffic_forecast_ai", {}).get(
        "checkpoint_loaded"
    ):
        raise SystemExit("traffic LSTM checkpoint was not loaded into runtime")


def _post_json(url: str, payload: dict[str, Any]) -> dict[str, Any]:
    request = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"content-type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=900) as response:
        return cast(dict[str, Any], json.loads(response.read().decode("utf-8")))


def _get_json(url: str) -> dict[str, Any]:
    with urllib.request.urlopen(url, timeout=30) as response:
        return cast(dict[str, Any], json.loads(response.read().decode("utf-8")))


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        sys.exit(130)
