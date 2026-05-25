#!/usr/bin/env python3
"""Headless Chromium smoke for the local Aetherville demo client.

This catches the class of failures that plain curl misses: hydrated client-side
exceptions and stale runtime endpoint rendering in the production Next app.
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys

COMMON_PANEL_MARKERS = (
    "SCENE DIRECTOR · LIVE IMPACT",
    "Live impact board",
    "RunPod AI proof",
    "4090 실행 증거",
    "Memory stream",
    "Vehicle cam",
    "Traffic forecast",
    "AI learning loop",
    "God Mode",
    "Voice STT",
)

MODE_MARKERS = {
    "live": ("Project Aetherville · Live City Shell", *COMMON_PANEL_MARKERS),
    "replay": ("Project Aetherville · Replay Mode", "Live city로 돌아가기", *COMMON_PANEL_MARKERS),
}
ERROR_MARKERS = (
    "Application error: a client-side exception has occurred",
    "__next_error__",
    "ChunkLoadError",
    "ReferenceError",
    "TypeError",
)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Smoke the local browser demo with headless Chromium"
    )
    parser.add_argument("--url", default="http://127.0.0.1:3000/")
    parser.add_argument("--expected-endpoint", default=None)
    parser.add_argument("--mode", choices=("live", "replay"), default="live")
    parser.add_argument("--chrome-bin", default=None)
    parser.add_argument("--timeout-seconds", type=int, default=20)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    chrome = args.chrome_bin or find_chrome()
    command = [
        chrome,
        "--headless=new",
        "--no-sandbox",
        "--window-size=1920,1080",
        "--timeout=8000",
        "--dump-dom",
        args.url,
    ]

    if args.dry_run:
        print(" ".join(command))
        return

    result = subprocess.run(
        command,
        check=False,
        capture_output=True,
        text=True,
        timeout=args.timeout_seconds,
    )
    dom = result.stdout
    stderr = result.stderr
    if result.returncode != 0:
        print(stderr[-2000:], file=sys.stderr)
        raise SystemExit(result.returncode)

    required_markers = MODE_MARKERS[args.mode]
    missing = [marker for marker in required_markers if marker not in dom]
    if args.expected_endpoint and args.expected_endpoint not in dom:
        missing.append(args.expected_endpoint)
    errors = [marker for marker in ERROR_MARKERS if marker in dom]

    summary = {
        "url": args.url,
        "chrome": chrome,
        "dom_bytes": len(dom.encode("utf-8")),
        "missing": missing,
        "errors": errors,
        "stderr_tail": stderr[-500:] if stderr else "",
    }
    print(summary)
    if missing or errors:
        raise SystemExit(1)


def find_chrome() -> str:
    for candidate in ("chromium", "chromium-browser", "google-chrome", "microsoft-edge"):
        path = shutil.which(candidate)
        if path:
            return path
    raise SystemExit("Chromium/Chrome executable not found")


if __name__ == "__main__":
    main()
