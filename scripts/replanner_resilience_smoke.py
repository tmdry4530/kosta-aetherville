#!/usr/bin/env python3
"""Smoke-test bounded replanner recovery over the direct-process orchestrator."""

from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.error
import urllib.request
from typing import Any

DEFAULT_COMMAND = (
    "교통 지연 때문에 민수가 하린이를 만난 뒤 택시를 불러 민지에게 가고, "
    "드론은 서연에게 이동한 뒤 서연은 민지와 민수를 만나러 간다"
)


def request_json(url: str, *, method: str = "GET", payload: dict[str, Any] | None = None) -> Any:
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
    parser.add_argument("--wait-seconds", type=float, default=60.0)
    parser.add_argument("--no-reset", action="store_true")
    args = parser.parse_args()

    base_url = args.orchestrator_url.rstrip("/")
    if not args.no_reset:
        request_json(f"{base_url}/api/v1/sim/reset", method="POST", payload={"seed": 42})
    request_json(f"{base_url}/api/v1/sim/start", method="POST")
    response = request_json(
        f"{base_url}/api/v1/god/command",
        method="POST",
        payload={
            "kind": "god_command",
            "input_modality": "text",
            "raw_text": args.command,
            "audio_blob_b64": None,
            "user_id": "replanner-smoke",
        },
    )
    if not response.get("scenario"):
        raise SystemExit("scenario_directive missing; replanner smoke cannot proceed")

    deadline = time.monotonic() + args.wait_seconds
    seen: set[str] = set()
    records: list[dict[str, Any]] = []
    scenario_status = "running"
    while time.monotonic() < deadline:
        state = request_json(f"{base_url}/api/v1/sim/state")
        records = list(state.get("replans", []))
        seen.update(str(record.get("status")) for record in records)
        scenario = state.get("scenario") or {}
        scenario_status = str(scenario.get("status", "unknown"))
        timeline = request_json(f"{base_url}/api/v1/timeline")
        seen.update(
            str(event.get("kind"))
            for event in timeline
            if str(event.get("kind", "")).startswith("task_")
        )
        if {"task_blocked", "task_replanned", "task_recovered"}.issubset(seen):
            # Timeline events and world-state snapshots can be observed on adjacent
            # polling ticks. Re-fetch once so the final ReplanRecord assertion uses
            # the state that includes the just-seen recovery event.
            state = request_json(f"{base_url}/api/v1/sim/state")
            records = list(state.get("replans", []))
            break
        time.sleep(0.5)

    required = {"task_blocked", "task_replanned", "task_recovered"}
    missing = sorted(required.difference(seen))
    if missing:
        raise SystemExit(f"replanner events missing: {missing}; seen={sorted(seen)}")
    if not any(record.get("status") == "recovered" for record in records):
        raise SystemExit("no recovered ReplanRecord in world state")

    print(
        json.dumps(
            {
                "ok": True,
                "scenario_status": scenario_status,
                "seen": sorted(seen),
                "replans": records[-3:],
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
