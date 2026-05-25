#!/usr/bin/env python3
"""Smoke-test God Mode voice/STT with a real audio blob.

The script intentionally has no TTS dependency. Create or record an audio file
outside the repo, pass it with --audio-file, and this helper base64-encodes it
for /api/v1/god/voice. Use --expect-status ok to prove real STT; use fallback
only for demo safety-path checks.
"""

from __future__ import annotations

import argparse
import base64
import json
import sys
import urllib.error
import urllib.request
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser(description="Smoke /api/v1/god/voice with an audio file")
    parser.add_argument("--orchestrator-url", default="http://127.0.0.1:8080")
    parser.add_argument("--audio-file", required=True, help="Path to wav/webm/mp3 audio to send")
    parser.add_argument("--mime-type", default="audio/wav")
    parser.add_argument("--language", default="ko")
    parser.add_argument("--user-id", default="presenter")
    parser.add_argument("--fallback-transcript", default=None)
    parser.add_argument(
        "--expect-status",
        choices=("ok", "fallback", "unavailable"),
        default="ok",
        help="Expected stt_status; use ok to prove real audio transcription",
    )
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    audio_path = Path(args.audio_file)
    if not audio_path.is_file():
        raise SystemExit(f"audio file not found: {audio_path}")

    endpoint = f"{args.orchestrator_url.rstrip('/')}/api/v1/god/voice"
    if args.dry_run:
        print(
            json.dumps(
                {
                    "endpoint": endpoint,
                    "audio_file": str(audio_path),
                    "audio_bytes": audio_path.stat().st_size,
                    "mime_type": args.mime_type,
                    "expect_status": args.expect_status,
                },
                ensure_ascii=False,
            )
        )
        return

    payload = {
        "kind": "voice_command",
        "audio_blob_b64": base64.b64encode(audio_path.read_bytes()).decode("ascii"),
        "mime_type": args.mime_type,
        "user_id": args.user_id,
        "fallback_transcript": args.fallback_transcript,
        "language": args.language,
    }
    request = urllib.request.Request(
        endpoint,
        data=json.dumps(payload).encode("utf-8"),
        headers={"content-type": "application/json"},
        method="POST",
    )

    try:
        with urllib.request.urlopen(request, timeout=180) as response:
            response_payload = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        print(exc.read().decode("utf-8", errors="replace"), file=sys.stderr)
        raise

    summary = {
        "transcript": response_payload.get("transcript"),
        "stt_status": response_payload.get("stt_status"),
        "stt_mode": response_payload.get("stt_mode"),
        "detail": response_payload.get("detail"),
        "accepted": response_payload.get("command", {}).get("accepted"),
        "ai_mode": response_payload.get("command", {}).get("ai_mode"),
        "ai_actions": response_payload.get("command", {}).get("ai_actions"),
        "event_kind": response_payload.get("command", {}).get("event", {}).get("kind"),
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))

    if summary["stt_status"] != args.expect_status:
        raise SystemExit(
            f"expected stt_status={args.expect_status!r}, got {summary['stt_status']!r}"
        )
    if not summary["accepted"]:
        raise SystemExit("voice command was not accepted")


if __name__ == "__main__":
    main()
