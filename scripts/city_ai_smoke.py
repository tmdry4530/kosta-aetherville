#!/usr/bin/env python3
"""Smoke-test that the autonomous City AI planner produces and executes a plan."""

from __future__ import annotations

import argparse
import json
import math
import time
import urllib.error
import urllib.request
from typing import Any

JsonPayload = dict[str, Any] | list[Any]


def request_json(
    url: str, *, method: str = "GET", body: dict[str, Any] | None = None
) -> JsonPayload:
    data = None if body is None else json.dumps(body).encode("utf-8")
    request = urllib.request.Request(
        url,
        data=data,
        method=method,
        headers={"content-type": "application/json"},
    )
    with urllib.request.urlopen(request, timeout=8) as response:
        return json.loads(response.read().decode("utf-8"))


def actor_positions(state: dict[str, Any]) -> dict[str, tuple[float, float, float]]:
    positions: dict[str, tuple[float, float, float]] = {}
    for section in ("citizens", "vehicles"):
        for actor in state.get(section, []):
            pos = actor.get("pos") or [0, 0, 0]
            if len(pos) >= 3:
                positions[str(actor.get("id"))] = (float(pos[0]), float(pos[1]), float(pos[2]))
    return positions


def distance(a: tuple[float, float, float], b: tuple[float, float, float]) -> float:
    return math.dist(a, b)


def action_actor_ids(actions: list[dict[str, Any]]) -> set[str]:
    actor_ids: set[str] = set()
    for action in actions:
        for key in ("actor_id", "target_id", "vehicle_id", "destination_actor_id"):
            value = action.get(key)
            if isinstance(value, str) and value:
                actor_ids.add(value)
    if any(action.get("type") == "call_taxi" for action in actions):
        actor_ids.add("v01")
    return actor_ids


def visible_execution_markers(state: dict[str, Any], actions: list[dict[str, Any]]) -> list[str]:
    markers: list[str] = []
    tags = " ".join(
        tag
        for section in ("citizens", "vehicles", "traffic_lights")
        for actor in state.get(section, [])
        for tag in actor.get("display_tags", [])
    )
    active_event = str(state.get("world", {}).get("active_event") or "")
    infrastructure = str(state.get("world", {}).get("infrastructure_status") or "")
    weather = str(state.get("world", {}).get("weather") or "")
    if "AI계획" in tags:
        markers.append("citizen_ai_directive")
    if "택시 호출" in tags or any(actor.get("passenger_id") for actor in state.get("vehicles", [])):
        markers.append("taxi_dispatch")
    if "congestion" in infrastructure or "traffic congestion" in active_event or "정체" in tags:
        markers.append("traffic_surge")
    if any(
        action.get("type") == "set_weather" and action.get("weather") == weather
        for action in actions
    ):
        markers.append(f"weather_{weather}")
    return markers


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--orchestrator-url", default="http://127.0.0.1:18080")
    parser.add_argument("--wait-seconds", type=float, default=20.0)
    parser.add_argument("--post-plan-seconds", type=float, default=5.0)
    parser.add_argument("--poll-seconds", type=float, default=0.75)
    parser.add_argument("--expect-mode", choices=["any", "rules", "vllm"], default="any")
    parser.add_argument(
        "--no-start",
        action="store_true",
        help="do not POST /sim/start before polling",
    )
    args = parser.parse_args()

    base_url = args.orchestrator_url.rstrip("/")
    if not args.no_start:
        request_json(f"{base_url}/api/v1/sim/start", method="POST")

    start = time.monotonic()
    first_state: dict[str, Any] | None = None
    planned_state: dict[str, Any] | None = None
    while time.monotonic() - start <= args.wait_seconds:
        state = request_json(f"{base_url}/api/v1/sim/state")
        if not isinstance(state, dict):
            raise RuntimeError("state endpoint did not return a JSON object")
        first_state = first_state or state
        city_ai = state.get("city_ai") or {}
        mode = city_ai.get("mode")
        status = city_ai.get("status")
        actions = city_ai.get("actions") or []
        if status == "applied" and mode != "disabled" and actions:
            planned_state = state
            break
        time.sleep(args.poll_seconds)

    if planned_state is None or first_state is None:
        raise SystemExit("FAIL city AI did not apply a non-empty plan within the wait window")

    city_ai = planned_state["city_ai"]
    if args.expect_mode != "any" and city_ai.get("mode") != args.expect_mode:
        raise SystemExit(
            f"FAIL expected city_ai.mode={args.expect_mode}, got {city_ai.get('mode')}"
        )

    before_positions = actor_positions(first_state)
    planned_positions = actor_positions(planned_state)
    actions = city_ai.get("actions") or []
    ids_to_check = action_actor_ids(actions)
    moved: list[str] = []
    for actor_id in ids_to_check:
        if actor_id in before_positions and actor_id in planned_positions:
            if distance(before_positions[actor_id], planned_positions[actor_id]) > 0.05:
                moved.append(actor_id)

    time.sleep(args.post_plan_seconds)
    final_state = request_json(f"{base_url}/api/v1/sim/state")
    if not isinstance(final_state, dict):
        raise RuntimeError("state endpoint did not return a JSON object")
    final_positions = actor_positions(final_state)
    for actor_id in ids_to_check:
        if actor_id in planned_positions and actor_id in final_positions:
            if distance(planned_positions[actor_id], final_positions[actor_id]) > 0.05:
                moved.append(actor_id)

    timeline = request_json(f"{base_url}/api/v1/timeline")
    timeline_has_plan = isinstance(timeline, list) and any(
        event.get("kind") == "city_ai_plan" for event in timeline if isinstance(event, dict)
    )
    markers = visible_execution_markers(final_state, actions)
    if not timeline_has_plan:
        raise SystemExit("FAIL timeline does not include city_ai_plan event")
    if not moved and not markers:
        raise SystemExit(
            "FAIL city AI plan applied but no visible execution marker or movement was observed"
        )

    print(
        json.dumps(
            {
                "ok": True,
                "mode": city_ai.get("mode"),
                "status": city_ai.get("status"),
                "plan_id": city_ai.get("plan_id"),
                "summary": city_ai.get("summary"),
                "actions": [action.get("type") for action in actions],
                "moved": sorted(set(moved)),
                "markers": markers,
                "timeline_has_city_ai_plan": timeline_has_plan,
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except urllib.error.URLError as exc:
        raise SystemExit(f"FAIL HTTP request failed: {exc}") from exc
