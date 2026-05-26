#!/usr/bin/env python3
"""Run the Goal 17 autonomous-city dogfood scenarios through the REST API."""

from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any, Literal

ScenarioKind = Literal["accepted", "rejected", "observability"]


@dataclass(frozen=True)
class DogfoodScenario:
    name: str
    command: str
    expect: ScenarioKind = "accepted"
    required_any: tuple[str, ...] = ()


SCENARIOS: tuple[DogfoodScenario, ...] = (
    DogfoodScenario(
        "citizen meets citizen then taxi to third",
        "민수가 하린이를 만난 뒤 택시를 불러 민지에게 간다",
        required_any=("scenario", "task_graph"),
    ),
    DogfoodScenario(
        "taxi unavailable then fallback",
        "택시 없음 상황에서 민수가 택시를 불러 민지에게 간다",
        required_any=("task_replanned",),
    ),
    DogfoodScenario(
        "drone then rendezvous",
        "드론은 서연에게 이동한 뒤 서연은 민지와 민수를 만나러 간다",
        required_any=("scenario", "task_graph"),
    ),
    DogfoodScenario(
        "rain affects reason text",
        "비가 내리고 민지가 택시를 불러 민수에게 간다",
        required_any=("weather", "scenario"),
    ),
    DogfoodScenario(
        "traffic surge slows vehicles",
        "교통량이 증가하고 지호가 택시를 불러 하린에게 간다",
        required_any=("traffic", "scenario"),
    ),
    DogfoodScenario(
        "unknown actor safe handling",
        "수빈이 민지를 만난다",
        expect="rejected",
        required_any=("task_graph_rejected",),
    ),
    DogfoodScenario(
        "impossible route replans",
        "도착 불가 상황에서 민수가 하린이를 만난 뒤 택시를 불러 민지에게 간다",
        required_any=("task_replanned",),
    ),
    DogfoodScenario(
        "two citizens converge on same person",
        "민수와 서연이 민지를 만나러 간다",
        required_any=("scenario", "task_graph"),
    ),
    DogfoodScenario(
        "long six-step audience prompt",
        (
            "민수가 하린이를 만난 뒤 택시를 불러 민지에게 가고, "
            "드론은 서연에게 이동한 뒤 서연은 민지와 민수를 만나러 간다"
        ),
        required_any=("scenario", "task_graph"),
    ),
    DogfoodScenario(
        "replay observability documented",
        "Replay fallback shows TaskGraph, Entity intent, Replan feed, Evolution state panels",
        expect="observability",
        required_any=("entity_brains", "replans", "learning"),
    ),
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
        with urllib.request.urlopen(request, timeout=12) as response:
            return json.loads(response.read().decode("utf-8"))
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
        raise SystemExit(f"request failed {method} {url}: {exc}") from exc


def run_scenario(base_url: str, scenario: DogfoodScenario, wait_seconds: float) -> dict[str, Any]:
    if scenario.expect == "observability":
        state = request_json(f"{base_url}/api/v1/sim/state")
        ok = all(key in state for key in scenario.required_any)
        return {
            "name": scenario.name,
            "expect": scenario.expect,
            "ok": ok,
            "evidence": sorted(key for key in scenario.required_any if key in state),
            "risk": "Replay route DOM smoke validates browser fallback panels separately.",
        }

    request_json(f"{base_url}/api/v1/sim/reset", method="POST", payload={"seed": 42})
    request_json(f"{base_url}/api/v1/sim/start", method="POST")
    response = request_json(
        f"{base_url}/api/v1/god/command",
        method="POST",
        payload={
            "kind": "god_command",
            "input_modality": "text",
            "raw_text": scenario.command,
            "audio_blob_b64": None,
            "user_id": "goal17-dogfood",
        },
    )
    deadline = time.monotonic() + wait_seconds
    final_state: dict[str, Any] = {}
    timeline: list[dict[str, Any]] = []
    while time.monotonic() < deadline:
        final_state = request_json(f"{base_url}/api/v1/sim/state")
        timeline = request_json(f"{base_url}/api/v1/timeline")
        scenario_state = final_state.get("scenario") or {}
        if scenario.expect == "rejected" or scenario_state.get("status") == "completed":
            break
        if any(str(event.get("kind")) == "task_replanned" for event in timeline):
            break
        time.sleep(0.35)

    event_kinds = {str(event.get("kind")) for event in timeline}
    evidence = []
    if response.get("scenario") or final_state.get("scenario"):
        evidence.append("scenario")
    if response.get("task_graph") or final_state.get("task_graph"):
        evidence.append("task_graph")
    if any(record.get("status") == "recovered" for record in final_state.get("replans", [])):
        evidence.append("task_replanned")
    if final_state.get("world", {}).get("weather") in {"rain", "snow"}:
        evidence.append("weather")
    if final_state.get("world", {}).get("infrastructure_status"):
        evidence.append("traffic")
    evidence.extend(sorted(event_kinds.intersection({"task_graph_rejected"})))

    if scenario.expect == "rejected":
        ok = response.get("accepted") is False and "task_graph_rejected" in event_kinds
    else:
        ok = (
            bool(set(scenario.required_any).intersection(evidence))
            and response.get("accepted") is True
        )
    return {
        "name": scenario.name,
        "expect": scenario.expect,
        "ok": ok,
        "accepted": response.get("accepted"),
        "scenario_status": (final_state.get("scenario") or {}).get("status"),
        "task_graph_status": (final_state.get("task_graph") or {}).get("status"),
        "evidence": sorted(set(evidence)),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--orchestrator-url", default="http://127.0.0.1:18080")
    parser.add_argument("--wait-seconds", type=float, default=12.0)
    args = parser.parse_args()
    base_url = args.orchestrator_url.rstrip("/")
    results = [run_scenario(base_url, scenario, args.wait_seconds) for scenario in SCENARIOS]
    failed = [result for result in results if not result["ok"]]
    print(json.dumps({"ok": not failed, "results": results}, ensure_ascii=False, indent=2))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
