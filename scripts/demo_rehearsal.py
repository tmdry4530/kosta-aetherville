#!/usr/bin/env python3
"""Full presenter rehearsal smoke for Project Aetherville.

This script is intentionally stdlib-only. It verifies the direct-process
orchestrator, 4090-backed AI evidence, God Mode visible effects, vehicle camera,
and the local browser live/replay routes when a client URL is provided.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
import urllib.error
import urllib.request
from typing import Any

DEFAULT_COMMAND = (
    "도시에 비를 내리고 민지가 택시를 부르게 하고 "
    "출근길을 혼잡하게 만들고 민수와 만나게 해줘"
)
EXPECTED_ACTIONS = {"rain", "traffic_jam", "taxi_call", "meeting"}


def main() -> None:
    parser = argparse.ArgumentParser(description="Run a full Aetherville demo rehearsal smoke")
    parser.add_argument("--orchestrator-url", default="http://127.0.0.1:18080")
    parser.add_argument("--client-url", default="http://127.0.0.1:3000")
    parser.add_argument("--expected-client-endpoint", default=None)
    parser.add_argument("--god-command", default=DEFAULT_COMMAND)
    parser.add_argument("--expect-ai-mode", default="vllm", choices=("vllm", "rules", "any"))
    parser.add_argument("--skip-browser", action="store_true")
    parser.add_argument("--skip-visual-smoke", action="store_true")
    parser.add_argument("--skip-impact-smoke", action="store_true")
    parser.add_argument("--skip-god-command", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    orchestrator_url = args.orchestrator_url.rstrip("/")
    client_url = args.client_url.rstrip("/")
    expected_endpoint = args.expected_client_endpoint or orchestrator_url

    if args.dry_run:
        print(
            json.dumps(
                {
                    "orchestrator_url": orchestrator_url,
                    "client_url": client_url,
                    "expected_client_endpoint": expected_endpoint,
                    "god_command": args.god_command,
                    "skip_browser": args.skip_browser,
                    "skip_visual_smoke": args.skip_visual_smoke,
                    "skip_impact_smoke": args.skip_impact_smoke,
                    "skip_god_command": args.skip_god_command,
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return

    checks: list[dict[str, Any]] = []

    health = get_json(f"{orchestrator_url}/api/v1/health")
    checks.append(assert_equal("orchestrator health", health.get("status"), "ok"))
    dependency_status = {
        item.get("name"): item.get("status")
        for item in health.get("dependencies", [])
    }
    for dependency in ("simulation", "learning", "stt", "vision", "vllm"):
        checks.append(
            assert_equal(f"dependency {dependency}", dependency_status.get(dependency), "ok")
        )

    status = post_json(f"{orchestrator_url}/api/v1/sim/start", payload=None)
    checks.append(assert_equal("simulation running", status.get("running"), True))

    state_before = get_json(f"{orchestrator_url}/api/v1/sim/state")
    checks.extend(validate_ai_snapshots(state_before))

    camera = get_json(f"{orchestrator_url}/api/v1/vehicles/v01/camera")
    checks.append(assert_equal("vehicle camera mode", camera.get("mode"), "real"))
    checks.append(assert_truthy("vehicle camera detections", camera.get("detections")))

    learning = get_json(f"{orchestrator_url}/api/v1/learning/status")
    checks.append(
        assert_equal(
            "learning mode",
            learning.get("learning", {}).get("mode"),
            "deterministic_online_adaptation",
        )
    )

    god_response: dict[str, Any] | None = None
    if not args.skip_god_command:
        god_response = post_json(
            f"{orchestrator_url}/api/v1/god/command",
            {
                "kind": "god_command",
                "input_modality": "text",
                "raw_text": args.god_command,
                "audio_blob_b64": None,
                "user_id": "presenter",
            },
            timeout=120,
        )
        checks.extend(validate_god_response(god_response, args.expect_ai_mode))
        state_after = wait_for_visible_effects(orchestrator_url)
        checks.extend(validate_visible_effects(state_after))

    if not args.skip_browser:
        checks.append(
            run_browser_smoke(
                mode="live",
                url=f"{client_url}/",
                expected_endpoint=expected_endpoint,
            )
        )
        checks.append(run_browser_smoke(mode="replay", url=f"{client_url}/replay"))
        if not args.skip_visual_smoke:
            checks.append(run_visual_smoke(client_url=client_url))
        if not args.skip_impact_smoke:
            checks.append(
                run_impact_smoke(orchestrator_url=orchestrator_url, client_url=client_url)
            )

    failures = [check for check in checks if not check["ok"]]
    summary = {
        "ok": not failures,
        "orchestrator": orchestrator_url,
        "client": None if args.skip_browser else client_url,
        "checks": checks,
        "god_ai_mode": god_response.get("ai_mode") if god_response else None,
        "god_ai_actions": god_response.get("ai_actions") if god_response else None,
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    if failures:
        raise SystemExit(1)


def get_json(url: str, timeout: int = 10) -> dict[str, Any]:
    with urllib.request.urlopen(url, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def post_json(url: str, payload: dict[str, Any] | None, timeout: int = 10) -> dict[str, Any]:
    data = b"" if payload is None else json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(
        url,
        data=data,
        headers={"content-type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        print(exc.read().decode("utf-8", errors="replace"), file=sys.stderr)
        raise


def validate_ai_snapshots(state: dict[str, Any]) -> list[dict[str, Any]]:
    traffic_ai = state.get("traffic_ai", {})
    forecast_ai = state.get("traffic_forecast_ai", {})
    return [
        assert_equal("traffic policy mode", traffic_ai.get("mode"), "checkpoint"),
        assert_equal("traffic policy backend", traffic_ai.get("training_backend"), "torch_cuda"),
        assert_equal("traffic policy gpu", traffic_ai.get("trained_on_gpu"), True),
        assert_equal("forecast mode", forecast_ai.get("mode"), "lstm_checkpoint"),
        assert_equal("forecast backend", forecast_ai.get("training_backend"), "torch_cuda"),
        assert_equal("forecast gpu", forecast_ai.get("trained_on_gpu"), True),
    ]


def validate_god_response(response: dict[str, Any], expect_ai_mode: str) -> list[dict[str, Any]]:
    checks = [
        assert_equal("god command accepted", response.get("accepted"), True),
        assert_equal(
            "god event kind",
            response.get("event", {}).get("kind"),
            "god_command_executed",
        ),
    ]
    ai_mode = response.get("ai_mode")
    if expect_ai_mode != "any":
        checks.append(assert_equal("god ai mode", ai_mode, expect_ai_mode))
    actions = set(response.get("ai_actions") or [])
    checks.append(assert_subset("god ai actions", EXPECTED_ACTIONS, actions))
    return checks


def wait_for_visible_effects(orchestrator_url: str) -> dict[str, Any]:
    deadline = time.monotonic() + 12
    latest: dict[str, Any] = {}
    while time.monotonic() < deadline:
        latest = get_json(f"{orchestrator_url}/api/v1/sim/state")
        checks = validate_visible_effects(latest)
        if all(check["ok"] for check in checks):
            return latest
        time.sleep(1)
    return latest


def validate_visible_effects(state: dict[str, Any]) -> list[dict[str, Any]]:
    world = state.get("world", {})
    vehicles = state.get("vehicles", [])
    citizens = state.get("citizens", [])
    taxi = next((vehicle for vehicle in vehicles if vehicle.get("id") == "v01"), {})
    minji = next((citizen for citizen in citizens if citizen.get("id") == "c01"), {})
    minsu = next((citizen for citizen in citizens if citizen.get("id") == "c02"), {})
    vehicle_tags = " ".join(" ".join(vehicle.get("display_tags", [])) for vehicle in vehicles)
    taxi_tags = " ".join(taxi.get("display_tags", []))
    return [
        assert_equal("visible rain", world.get("weather"), "rain"),
        assert_truthy(
            "taxi passenger/dispatch",
            taxi.get("passenger_id") or "택시 호출" in taxi_tags,
        ),
        assert_truthy("traffic congestion tags", "정체" in vehicle_tags or "저속" in vehicle_tags),
        assert_truthy(
            "citizen meeting/talking",
            minji.get("talking_to") == "c02" or minsu.get("talking_to") == "c01",
        ),
    ]


def run_browser_smoke(mode: str, url: str, expected_endpoint: str | None = None) -> dict[str, Any]:
    command = [sys.executable, "scripts/browser_demo_smoke.py", "--mode", mode, "--url", url]
    if expected_endpoint:
        command.extend(["--expected-endpoint", expected_endpoint])
    result = subprocess.run(command, check=False, capture_output=True, text=True, timeout=45)
    return {
        "name": f"browser smoke {mode}",
        "ok": result.returncode == 0,
        "expected": "exit 0",
        "actual": f"exit {result.returncode}",
        "detail": (result.stdout + result.stderr)[-1200:],
    }


def run_visual_smoke(client_url: str) -> dict[str, Any]:
    command = [
        sys.executable,
        "scripts/browser_visual_smoke.py",
        "--mode",
        "both",
        "--client-url",
        client_url,
        "--skip-dom-smoke",
    ]
    result = subprocess.run(command, check=False, capture_output=True, text=True, timeout=90)
    return {
        "name": "browser visual smoke",
        "ok": result.returncode == 0,
        "expected": "exit 0",
        "actual": f"exit {result.returncode}",
        "detail": (result.stdout + result.stderr)[-1600:],
    }


def run_impact_smoke(orchestrator_url: str, client_url: str) -> dict[str, Any]:
    command = [
        sys.executable,
        "scripts/browser_impact_smoke.py",
        "--orchestrator-url",
        orchestrator_url,
        "--client-url",
        client_url,
    ]
    result = subprocess.run(command, check=False, capture_output=True, text=True, timeout=150)
    return {
        "name": "browser impact smoke",
        "ok": result.returncode == 0,
        "expected": "exit 0",
        "actual": f"exit {result.returncode}",
        "detail": (result.stdout + result.stderr)[-1800:],
    }


def assert_equal(name: str, actual: Any, expected: Any) -> dict[str, Any]:
    return {"name": name, "ok": actual == expected, "expected": expected, "actual": actual}


def assert_truthy(name: str, actual: Any) -> dict[str, Any]:
    return {"name": name, "ok": bool(actual), "expected": "truthy", "actual": actual}


def assert_subset(name: str, expected_subset: set[str], actual: set[str]) -> dict[str, Any]:
    return {
        "name": name,
        "ok": expected_subset.issubset(actual),
        "expected": sorted(expected_subset),
        "actual": sorted(actual),
    }


if __name__ == "__main__":
    main()
