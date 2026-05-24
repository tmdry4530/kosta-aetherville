"""Voice path placeholder.

Real faster-whisper/STT is intentionally deferred until text God Mode is stable
and model/runtime cost is approved.
"""

from __future__ import annotations

from aetherville_schemas import GodCommand


class VoiceCommandStub:
    """Build a voice-mode command from an already supplied transcript."""

    def transcribe(self, audio_blob_b64: str | None) -> str | None:
        del audio_blob_b64
        return None

    def command_from_transcript(self, transcript: str, user_id: str = "presenter") -> GodCommand:
        return GodCommand(
            input_modality="voice",
            raw_text=transcript,
            audio_blob_b64=None,
            user_id=user_id,
        )
