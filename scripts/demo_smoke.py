#!/usr/bin/env python3
"""Demo smoke helper for local or RunPod-exposed orchestrator endpoints."""

from __future__ import annotations

import argparse
import json
import urllib.request


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--orchestrator-url", default="http://127.0.0.1:8080")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    if args.dry_run:
        print(f"would smoke {args.orchestrator_url}/api/v1/health")
        return

    health = get_json(f"{args.orchestrator_url}/api/v1/health")
    state = get_json(f"{args.orchestrator_url}/api/v1/sim/state")
    learning = get_json(f"{args.orchestrator_url}/api/v1/learning/status")
    print(
        json.dumps(
            {
                "health": health["status"],
                "citizens": len(state["citizens"]),
                "vehicles": len(state["vehicles"]),
                "traffic_forecast": [p["minute_offset"] for p in state["traffic_forecast"]],
                "learning_mode": learning["learning"]["mode"],
                "learning_epoch": learning["learning"]["adaptation_epoch"],
            },
            ensure_ascii=False,
        )
    )


def get_json(url: str) -> dict[str, object]:
    with urllib.request.urlopen(url, timeout=5) as response:
        return json.loads(response.read().decode("utf-8"))


if __name__ == "__main__":
    main()
