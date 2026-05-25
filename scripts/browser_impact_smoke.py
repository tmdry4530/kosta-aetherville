#!/usr/bin/env python3
"""Before/after visual impact smoke for the live Aetherville demo.

This gate proves the demo is not merely a static or short-loop browser view: it
resets to a clear baseline, captures the live city, sends the presenter God Mode
command to the RunPod orchestrator, waits for concrete state effects, captures
the city again, and compares sampled screenshot pixels.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

from browser_visual_smoke import capture_screenshot, find_chrome, sample_png_rgb, validate_png

DEFAULT_COMMAND = (
    "도시에 비를 내리고 민지가 택시를 부르게 하고 "
    "출근길을 혼잡하게 만들고 민수와 만나게 해줘"
)
EXPECTED_ACTIONS = {"rain", "traffic_jam", "taxi_call", "meeting"}


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Verify visible before/after God Mode impact in the browser demo"
    )
    parser.add_argument("--orchestrator-url", default="http://127.0.0.1:18080")
    parser.add_argument("--client-url", default="http://127.0.0.1:3000")
    parser.add_argument("--god-command", default=DEFAULT_COMMAND)
    parser.add_argument("--output-dir", default="dogfood-output/impact-smoke")
    parser.add_argument("--chrome-bin", default=None)
    parser.add_argument("--width", type=int, default=1920)
    parser.add_argument("--height", type=int, default=1080)
    parser.add_argument("--min-mean-rgb-delta", type=float, default=1.0)
    parser.add_argument("--min-changed-sample-ratio", type=float, default=0.01)
    parser.add_argument("--wait-seconds", type=float, default=2.0)
    parser.add_argument("--timeout-seconds", type=int, default=30)
    parser.add_argument("--skip-reset", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    orchestrator_url = args.orchestrator_url.rstrip("/")
    client_url = args.client_url.rstrip("/") + "/"
    output_dir = Path(args.output_dir)
    chrome = args.chrome_bin or find_chrome()

    if args.dry_run:
        print(
            json.dumps(
                {
                    "orchestrator_url": orchestrator_url,
                    "client_url": client_url,
                    "output_dir": str(output_dir),
                    "chrome": chrome,
                    "skip_reset": args.skip_reset,
                    "god_command": args.god_command,
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return

    output_dir.mkdir(parents=True, exist_ok=True)
    checks: list[dict[str, Any]] = []

    if not args.skip_reset:
        reset_state = post_json(f"{orchestrator_url}/api/v1/sim/reset", {"seed": 4242})
        checks.append(
            check("simulation reset tick", reset_state.get("tick") == 0, 0, reset_state.get("tick"))
        )
    start_state = post_json(f"{orchestrator_url}/api/v1/sim/start", payload=None)
    checks.append(
        check(
            "simulation running",
            start_state.get("running") is True,
            True,
            start_state.get("running"),
        )
    )
    time.sleep(max(0.0, args.wait_seconds))

    before_state = get_json(f"{orchestrator_url}/api/v1/sim/state")
    checks.extend(validate_baseline(before_state, expect_clear=not args.skip_reset))

    before_path = output_dir / "aetherville-impact-before.png"
    checks.append(
        capture_screenshot(
            chrome=chrome,
            url=client_url,
            output_path=before_path,
            width=args.width,
            height=args.height,
            timeout_seconds=args.timeout_seconds,
        )
    )
    checks.extend(
        validate_png(
            before_path,
            expected_width=args.width,
            expected_height=args.height,
            min_bytes=200_000,
            min_unique_colors=24,
            min_luma_range=20,
        )["checks"]
    )

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
    checks.extend(validate_god_response(god_response))
    after_state = wait_for_visible_effects(orchestrator_url)
    checks.extend(validate_visible_effects(after_state))
    time.sleep(max(0.0, args.wait_seconds))

    after_path = output_dir / "aetherville-impact-after.png"
    checks.append(
        capture_screenshot(
            chrome=chrome,
            url=client_url,
            output_path=after_path,
            width=args.width,
            height=args.height,
            timeout_seconds=args.timeout_seconds,
        )
    )
    checks.extend(
        validate_png(
            after_path,
            expected_width=args.width,
            expected_height=args.height,
            min_bytes=200_000,
            min_unique_colors=24,
            min_luma_range=20,
        )["checks"]
    )

    diff = compare_png_samples(before_path, after_path)
    checks.append(
        check(
            "before/after mean rgb delta",
            diff["mean_rgb_delta"] >= args.min_mean_rgb_delta,
            f">={args.min_mean_rgb_delta}",
            round(diff["mean_rgb_delta"], 4),
        )
    )
    checks.append(
        check(
            "before/after changed sample ratio",
            diff["changed_sample_ratio"] >= args.min_changed_sample_ratio,
            f">={args.min_changed_sample_ratio}",
            round(diff["changed_sample_ratio"], 4),
        )
    )

    failures = [item for item in checks if not item["ok"]]
    summary = {
        "ok": not failures,
        "orchestrator": orchestrator_url,
        "client": client_url,
        "god_ai_mode": god_response.get("ai_mode"),
        "god_ai_actions": god_response.get("ai_actions"),
        "before_tick": before_state.get("tick"),
        "after_tick": after_state.get("tick"),
        "before_weather": before_state.get("world", {}).get("weather"),
        "after_weather": after_state.get("world", {}).get("weather"),
        "screenshots": {
            "before": str(before_path),
            "after": str(after_path),
        },
        "visual_diff": diff,
        "checks": checks,
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


def validate_baseline(state: dict[str, Any], *, expect_clear: bool) -> list[dict[str, Any]]:
    checks = [
        check(
            "baseline has citizens",
            bool(state.get("citizens")),
            "truthy",
            bool(state.get("citizens")),
        )
    ]
    if expect_clear:
        checks.append(
            check(
                "baseline clear weather",
                state.get("world", {}).get("weather") == "clear",
                "clear",
                state.get("world", {}).get("weather"),
            )
        )
    return checks


def validate_god_response(response: dict[str, Any]) -> list[dict[str, Any]]:
    actions = set(response.get("ai_actions") or [])
    return [
        check(
            "god command accepted",
            response.get("accepted") is True,
            True,
            response.get("accepted"),
        ),
        check(
            "god ai mode vllm",
            response.get("ai_mode") == "vllm",
            "vllm",
            response.get("ai_mode"),
        ),
        check(
            "god actions complete",
            EXPECTED_ACTIONS.issubset(actions),
            sorted(EXPECTED_ACTIONS),
            sorted(actions),
        ),
    ]


def wait_for_visible_effects(orchestrator_url: str) -> dict[str, Any]:
    deadline = time.monotonic() + 12
    latest: dict[str, Any] = {}
    while time.monotonic() < deadline:
        latest = get_json(f"{orchestrator_url}/api/v1/sim/state")
        if all(item["ok"] for item in validate_visible_effects(latest)):
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
        check(
            "after weather rain",
            world.get("weather") == "rain",
            "rain",
            world.get("weather"),
        ),
        check(
            "after taxi dispatch",
            bool(taxi.get("passenger_id") or "택시 호출" in taxi_tags),
            "truthy",
            taxi_tags,
        ),
        check(
            "after traffic tags",
            "정체" in vehicle_tags or "저속" in vehicle_tags,
            "정체/저속",
            vehicle_tags,
        ),
        check(
            "after citizen meeting",
            minji.get("talking_to") == "c02" or minsu.get("talking_to") == "c01",
            "c01<->c02",
            {"c01": minji.get("talking_to"), "c02": minsu.get("talking_to")},
        ),
    ]


def compare_png_samples(before_path: Path, after_path: Path) -> dict[str, Any]:
    before = sample_png_rgb(before_path.read_bytes())["pixels"]
    after = sample_png_rgb(after_path.read_bytes())["pixels"]
    if len(before) != len(after):
        raise SystemExit(f"sample count mismatch: {len(before)} != {len(after)}")
    total_delta = 0
    changed = 0
    for left, right in zip(before, after, strict=True):
        delta = sum(abs(a - b) for a, b in zip(left, right, strict=True)) / 3
        total_delta += delta
        if delta >= 3:
            changed += 1
    return {
        "sampled_pixels": len(before),
        "mean_rgb_delta": total_delta / len(before) if before else 0.0,
        "changed_samples": changed,
        "changed_sample_ratio": changed / len(before) if before else 0.0,
    }


def check(name: str, ok: bool, expected: Any, actual: Any) -> dict[str, Any]:
    return {"name": name, "ok": ok, "expected": expected, "actual": actual}


if __name__ == "__main__":
    main()
