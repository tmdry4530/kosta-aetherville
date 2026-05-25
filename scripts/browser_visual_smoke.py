#!/usr/bin/env python3
"""Screenshot-based visual smoke for the Aetherville browser demo.

The existing browser smoke verifies DOM markers. This script adds a real
headless Chromium screenshot gate so the demo cannot accidentally pass with a
blank canvas, wrong viewport, or missing high-contrast visual scene.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import struct
import subprocess
import sys
import zlib
from pathlib import Path
from typing import Any
from urllib.parse import urljoin

PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"
MODE_PATHS = {"live": "/", "replay": "/replay"}
SUPPORTED_COLOR_TYPES = {0: 1, 2: 3, 6: 4}


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Capture and validate browser screenshots for the Aetherville demo"
    )
    parser.add_argument("--client-url", default="http://127.0.0.1:3000")
    parser.add_argument(
        "--url",
        default=None,
        help="single URL override; incompatible with --mode both",
    )
    parser.add_argument("--mode", choices=("live", "replay", "both"), default="both")
    parser.add_argument("--expected-endpoint", default=None)
    parser.add_argument("--output-dir", default="dogfood-output/visual-smoke")
    parser.add_argument("--chrome-bin", default=None)
    parser.add_argument("--width", type=int, default=1920)
    parser.add_argument("--height", type=int, default=1080)
    parser.add_argument("--min-bytes", type=int, default=200_000)
    parser.add_argument("--min-unique-colors", type=int, default=24)
    parser.add_argument("--min-luma-range", type=int, default=20)
    parser.add_argument("--timeout-seconds", type=int, default=30)
    parser.add_argument("--skip-dom-smoke", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    if args.url and args.mode == "both":
        raise SystemExit("--url can only be used with --mode live or --mode replay")

    chrome = args.chrome_bin or find_chrome()
    output_dir = Path(args.output_dir)
    modes = ("live", "replay") if args.mode == "both" else (args.mode,)
    urls = {mode: args.url or mode_url(args.client_url, mode) for mode in modes}

    if args.dry_run:
        print(
            json.dumps(
                {
                    "chrome": chrome,
                    "output_dir": str(output_dir),
                    "width": args.width,
                    "height": args.height,
                    "urls": urls,
                    "skip_dom_smoke": args.skip_dom_smoke,
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return

    output_dir.mkdir(parents=True, exist_ok=True)
    checks: list[dict[str, Any]] = []
    screenshots: list[dict[str, Any]] = []

    for mode, url in urls.items():
        screenshot_path = output_dir / f"aetherville-{mode}-{args.width}x{args.height}.png"
        capture = capture_screenshot(
            chrome=chrome,
            url=url,
            output_path=screenshot_path,
            width=args.width,
            height=args.height,
            timeout_seconds=args.timeout_seconds,
        )
        checks.append(capture)
        if capture["ok"]:
            visual = validate_png(
                screenshot_path,
                expected_width=args.width,
                expected_height=args.height,
                min_bytes=args.min_bytes,
                min_unique_colors=args.min_unique_colors,
                min_luma_range=args.min_luma_range,
            )
            checks.extend(visual["checks"])
            screenshots.append(visual["summary"])
        if not args.skip_dom_smoke:
            checks.append(
                run_dom_smoke(
                    mode=mode,
                    url=url,
                    expected_endpoint=args.expected_endpoint if mode == "live" else None,
                )
            )

    failures = [check for check in checks if not check["ok"]]
    summary = {
        "ok": not failures,
        "chrome": chrome,
        "output_dir": str(output_dir),
        "screenshots": screenshots,
        "checks": checks,
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    if failures:
        raise SystemExit(1)


def mode_url(client_url: str, mode: str) -> str:
    base = client_url.rstrip("/") + "/"
    return urljoin(base, MODE_PATHS[mode].lstrip("/"))


def find_chrome() -> str:
    for candidate in ("chromium", "chromium-browser", "google-chrome", "microsoft-edge"):
        path = shutil.which(candidate)
        if path:
            return path
    raise SystemExit("Chromium/Chrome executable not found")


def capture_screenshot(
    *,
    chrome: str,
    url: str,
    output_path: Path,
    width: int,
    height: int,
    timeout_seconds: int,
) -> dict[str, Any]:
    command = [
        chrome,
        "--headless=new",
        "--no-sandbox",
        f"--window-size={width},{height}",
        "--timeout=10000",
        f"--screenshot={output_path}",
        url,
    ]
    result = subprocess.run(
        command,
        check=False,
        capture_output=True,
        text=True,
        timeout=timeout_seconds,
    )
    return {
        "name": f"capture screenshot {url}",
        "ok": result.returncode == 0 and output_path.exists(),
        "expected": "exit 0 and screenshot file exists",
        "actual": f"exit {result.returncode}; exists={output_path.exists()}",
        "detail": (result.stdout + result.stderr)[-1000:],
    }


def run_dom_smoke(mode: str, url: str, expected_endpoint: str | None) -> dict[str, Any]:
    command = [sys.executable, "scripts/browser_demo_smoke.py", "--mode", mode, "--url", url]
    if expected_endpoint:
        command.extend(["--expected-endpoint", expected_endpoint])
    result = subprocess.run(command, check=False, capture_output=True, text=True, timeout=45)
    return {
        "name": f"dom smoke {mode}",
        "ok": result.returncode == 0,
        "expected": "exit 0",
        "actual": f"exit {result.returncode}",
        "detail": (result.stdout + result.stderr)[-1200:],
    }


def validate_png(
    path: Path,
    *,
    expected_width: int,
    expected_height: int,
    min_bytes: int,
    min_unique_colors: int,
    min_luma_range: int,
) -> dict[str, Any]:
    data = path.read_bytes()
    png = decode_png_for_metrics(data)
    digest = hashlib.sha256(data).hexdigest()[:16]
    summary = {
        "path": str(path),
        "bytes": len(data),
        "sha256_prefix": digest,
        "width": png["width"],
        "height": png["height"],
        "bit_depth": png["bit_depth"],
        "color_type": png["color_type"],
        "sampled_pixels": png["sampled_pixels"],
        "unique_colors": png["unique_colors"],
        "luma_range": png["luma_range"],
    }
    checks = [
        check("png signature", data.startswith(PNG_SIGNATURE), True, data[:8].hex()),
        check("png width", png["width"] == expected_width, expected_width, png["width"]),
        check("png height", png["height"] == expected_height, expected_height, png["height"]),
        check("png byte size", len(data) >= min_bytes, f">={min_bytes}", len(data)),
        check(
            "visual color diversity",
            png["unique_colors"] >= min_unique_colors,
            f">={min_unique_colors}",
            png["unique_colors"],
        ),
        check(
            "visual luminance range",
            png["luma_range"] >= min_luma_range,
            f">={min_luma_range}",
            png["luma_range"],
        ),
    ]
    return {"summary": summary, "checks": checks}


def decode_png_for_metrics(data: bytes) -> dict[str, int]:
    sample = sample_png_rgb(data)
    pixels = sample["pixels"]
    lumas = [(299 * r + 587 * g + 114 * b) // 1000 for r, g, b in pixels]
    return {
        "width": sample["width"],
        "height": sample["height"],
        "bit_depth": sample["bit_depth"],
        "color_type": sample["color_type"],
        "sampled_pixels": len(pixels),
        "unique_colors": len(set(pixels)),
        "luma_range": max(lumas) - min(lumas) if lumas else 0,
    }


def sample_png_rgb(data: bytes, *, rows: int = 72, columns: int = 96) -> dict[str, Any]:
    if not data.startswith(PNG_SIGNATURE):
        raise SystemExit("screenshot is not a PNG")

    pos = len(PNG_SIGNATURE)
    width = height = bit_depth = color_type = interlace = -1
    idat_parts: list[bytes] = []
    while pos + 8 <= len(data):
        length = struct.unpack(">I", data[pos : pos + 4])[0]
        chunk_type = data[pos + 4 : pos + 8]
        chunk_data = data[pos + 8 : pos + 8 + length]
        pos += 12 + length
        if chunk_type == b"IHDR":
            width, height, bit_depth, color_type, _compression, _filter, interlace = struct.unpack(
                ">IIBBBBB", chunk_data
            )
        elif chunk_type == b"IDAT":
            idat_parts.append(chunk_data)
        elif chunk_type == b"IEND":
            break

    if bit_depth != 8 or color_type not in SUPPORTED_COLOR_TYPES or interlace != 0:
        raise SystemExit(
            "unsupported PNG format: "
            f"bit_depth={bit_depth}, color_type={color_type}, interlace={interlace}"
        )
    if width <= 0 or height <= 0 or not idat_parts:
        raise SystemExit("invalid PNG metadata")

    bpp = SUPPORTED_COLOR_TYPES[color_type]
    stride = width * bpp
    raw = zlib.decompress(b"".join(idat_parts))
    expected_raw_len = (stride + 1) * height
    if len(raw) < expected_raw_len:
        raise SystemExit(f"truncated PNG scanlines: {len(raw)} < {expected_raw_len}")

    prev = bytearray(stride)
    row_step = max(1, height // 72)
    col_step = max(1, width // 96)
    if rows > 0:
        row_step = max(1, height // rows)
    if columns > 0:
        col_step = max(1, width // columns)
    pixels: list[tuple[int, int, int]] = []

    offset = 0
    for y in range(height):
        filter_type = raw[offset]
        row = bytearray(raw[offset + 1 : offset + 1 + stride])
        offset += stride + 1
        unfilter_row(row, prev, bpp, filter_type)
        if y % row_step == 0:
            for x in range(0, width, col_step):
                i = x * bpp
                if color_type == 0:
                    r = g = b = row[i]
                else:
                    r, g, b = row[i], row[i + 1], row[i + 2]
                pixels.append((r, g, b))
        prev = row

    return {
        "width": width,
        "height": height,
        "bit_depth": bit_depth,
        "color_type": color_type,
        "pixels": pixels,
    }


def unfilter_row(row: bytearray, prev: bytearray, bpp: int, filter_type: int) -> None:
    if filter_type == 0:
        return
    if filter_type == 1:
        for i in range(len(row)):
            left = row[i - bpp] if i >= bpp else 0
            row[i] = (row[i] + left) & 0xFF
        return
    if filter_type == 2:
        for i in range(len(row)):
            row[i] = (row[i] + prev[i]) & 0xFF
        return
    if filter_type == 3:
        for i in range(len(row)):
            left = row[i - bpp] if i >= bpp else 0
            up = prev[i]
            row[i] = (row[i] + ((left + up) // 2)) & 0xFF
        return
    if filter_type == 4:
        for i in range(len(row)):
            left = row[i - bpp] if i >= bpp else 0
            up = prev[i]
            upper_left = prev[i - bpp] if i >= bpp else 0
            row[i] = (row[i] + paeth(left, up, upper_left)) & 0xFF
        return
    raise SystemExit(f"unsupported PNG filter type: {filter_type}")


def paeth(left: int, up: int, upper_left: int) -> int:
    p = left + up - upper_left
    pa = abs(p - left)
    pb = abs(p - up)
    pc = abs(p - upper_left)
    if pa <= pb and pa <= pc:
        return left
    if pb <= pc:
        return up
    return upper_left


def check(name: str, ok: bool, expected: Any, actual: Any) -> dict[str, Any]:
    return {"name": name, "ok": ok, "expected": expected, "actual": actual}


if __name__ == "__main__":
    main()
