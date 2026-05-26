#!/usr/bin/env python3
"""Smoke-test persistent deterministic learning/evolution state."""

from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.error
import urllib.request
from typing import Any

COMMANDS = (
    "교통량이 증가하고 비가 내린 뒤 민지가 택시를 불러 민수에게 간다",
    "교통 지연 때문에 민수가 하린이를 만난 뒤 택시를 불러 민지에게 가고, 드론은 서연에게 이동한다",
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
    parser.add_argument("--repeat", type=int, default=2)
    parser.add_argument("--wait-seconds", type=float, default=45.0)
    parser.add_argument("--no-reset-learning", action="store_true")
    args = parser.parse_args()

    base_url = args.orchestrator_url.rstrip("/")
    if not args.no_reset_learning:
        request_json(f"{base_url}/api/v1/learning/reset", method="POST")
    before = request_json(f"{base_url}/api/v1/learning/status")["learning"]
    request_json(f"{base_url}/api/v1/sim/reset", method="POST", payload={"seed": 42})
    request_json(f"{base_url}/api/v1/sim/start", method="POST")

    for index in range(max(1, args.repeat)):
        request_json(
            f"{base_url}/api/v1/god/command",
            method="POST",
            payload={
                "kind": "god_command",
                "input_modality": "text",
                "raw_text": COMMANDS[index % len(COMMANDS)],
                "audio_blob_b64": None,
                "user_id": "learning-smoke",
            },
        )
        deadline = time.monotonic() + args.wait_seconds / max(1, args.repeat)
        while time.monotonic() < deadline:
            state = request_json(f"{base_url}/api/v1/sim/state")
            learning = state.get("learning", {})
            if (
                learning.get("experience_count", 0) > before.get("experience_count", 0)
                and learning.get("signals")
            ):
                break
            time.sleep(0.5)

    after = request_json(f"{base_url}/api/v1/learning/status")["learning"]
    if after.get("experience_count", 0) <= before.get("experience_count", 0):
        raise SystemExit("learning experience_count did not increase")
    if not after.get("signals"):
        raise SystemExit("learning signals missing")
    evolution = after.get("evolution") or {}
    if not evolution.get("version"):
        raise SystemExit("evolution snapshot missing")
    promotion_gate = after.get("promotion_gate") or {}
    if promotion_gate.get("candidate_count", 0) < 1:
        raise SystemExit("policy promotion gate did not evaluate any candidates")
    if not after.get("policy_candidates"):
        raise SystemExit("policy candidates missing")
    if after.get("storage") != "json_persistence":
        raise SystemExit(f"unexpected learning storage: {after.get('storage')}")

    print(
        json.dumps(
            {
                "ok": True,
                "before_experience": before.get("experience_count"),
                "after_experience": after.get("experience_count"),
                "policy_version": after.get("policy_version"),
                "signals": after.get("signals", [])[-4:],
                "evolution": evolution,
                "promotion_gate": promotion_gate,
                "policy_candidates": after.get("policy_candidates", [])[-2:],
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
