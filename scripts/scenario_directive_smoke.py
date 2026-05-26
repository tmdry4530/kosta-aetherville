#!/usr/bin/env python3
"""Smoke-test the bounded ScenarioDirective God Mode path."""

from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.error
import urllib.request
from typing import Any

DEFAULT_COMMAND = (
    "민수가 하린이를 만난 뒤 택시를 불러 민지에게 가고, "
    "드론은 서연에게 이동한 뒤 서연은 민지와 민수를 만나러 간다"
)


def request_json(
    url: str,
    *,
    method: str = "GET",
    payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    body = None if payload is None else json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(
        url,
        data=body,
        method=method,
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            return json.loads(response.read().decode("utf-8"))
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
        raise SystemExit(f"request failed {method} {url}: {exc}") from exc


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--orchestrator-url", default="http://127.0.0.1:18080")
    parser.add_argument("--command", default=DEFAULT_COMMAND)
    parser.add_argument("--wait-seconds", type=float, default=45.0)
    parser.add_argument("--no-start", action="store_true")
    args = parser.parse_args()

    base_url = args.orchestrator_url.rstrip("/")
    if not args.no_start:
        request_json(f"{base_url}/api/v1/sim/start", method="POST")

    response = request_json(
        f"{base_url}/api/v1/god/command",
        method="POST",
        payload={
            "kind": "god_command",
            "input_modality": "text",
            "raw_text": args.command,
            "audio_blob_b64": None,
            "user_id": "scenario-smoke",
        },
    )
    scenario = response.get("scenario")
    if not scenario:
        raise SystemExit("scenario_directive missing from GodCommandResponse")
    step_types = [step.get("type") for step in scenario.get("steps", [])]
    required = {
        "move_actor_to_actor",
        "meet",
        "call_taxi",
        "taxi_drive_to_actor",
        "drone_move_to_actor",
        "move_actor_to_group",
    }
    missing = sorted(required.difference(step_types))
    if missing:
        raise SystemExit(f"scenario steps missing: {missing}")

    deadline = time.monotonic() + args.wait_seconds
    seen_running: set[str] = set()
    seen_completed: set[str] = set()
    while time.monotonic() < deadline:
        state = request_json(f"{base_url}/api/v1/sim/state")
        active = state.get("scenario")
        if active:
            for step in active.get("steps", []):
                if step.get("status") == "running":
                    seen_running.add(str(step.get("type")))
                if step.get("status") == "completed":
                    seen_completed.add(str(step.get("type")))
            if active.get("status") == "completed":
                break
        time.sleep(0.5)

    expected_running = {"move_actor_to_actor", "drone_move_to_actor", "taxi_drive_to_actor"}
    if not expected_running.intersection(seen_running | seen_completed):
        raise SystemExit("scenario did not visibly advance any movement step")

    print(
        json.dumps(
            {
                "ok": True,
                "scenario_id": scenario.get("id"),
                "step_types": step_types,
                "seen_running": sorted(seen_running),
                "seen_completed": sorted(seen_completed),
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
