"""Optional speech-to-text path for God Mode voice commands."""

from __future__ import annotations

import base64
import os
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from aetherville_schemas import GodCommand

SttMode = Literal["stub", "faster_whisper", "fallback"]
SttStatus = Literal["ok", "fallback", "unavailable"]


@dataclass(frozen=True)
class TranscriptionResult:
    transcript: str | None
    mode: SttMode
    status: SttStatus
    detail: str | None = None


class VoiceCommandStub:
    """Build a voice-mode command from an already supplied transcript.

    The stub is intentionally useful for demos: the browser can still capture a
    voice blob while sending the current text input as a deterministic fallback
    transcript if real STT is unavailable.
    """

    mode: SttMode = "stub"

    def transcribe(
        self,
        audio_blob_b64: str | None,
        *,
        mime_type: str = "audio/webm",
        language: str | None = "ko",
        fallback_transcript: str | None = None,
    ) -> TranscriptionResult:
        del audio_blob_b64, mime_type, language
        if fallback_transcript and fallback_transcript.strip():
            return TranscriptionResult(
                transcript=fallback_transcript.strip(),
                mode="fallback",
                status="fallback",
                detail="typed fallback transcript used because real STT is disabled",
            )
        return TranscriptionResult(
            transcript=None,
            mode="stub",
            status="unavailable",
            detail="set AETHERVILLE_STT_MODE=faster_whisper to enable real STT",
        )

    def command_from_transcript(self, transcript: str, user_id: str = "presenter") -> GodCommand:
        return GodCommand(
            input_modality="voice",
            raw_text=transcript,
            audio_blob_b64=None,
            user_id=user_id,
        )

    def health_status(self) -> Literal["ok", "degraded", "stub"]:
        return "stub"

    def health_detail(self) -> str:
        return "voice fallback only; faster-whisper disabled"


class FasterWhisperTranscriber(VoiceCommandStub):
    """Lazy faster-whisper provider for direct-process RunPod STT."""

    mode: SttMode = "faster_whisper"

    def __init__(
        self,
        *,
        model_size: str | None = None,
        device: str | None = None,
        compute_type: str | None = None,
    ) -> None:
        self.model_size = model_size or os.getenv("AETHERVILLE_STT_MODEL", "base")
        self.device = device or os.getenv("AETHERVILLE_STT_DEVICE", "cuda")
        self.compute_type = compute_type or os.getenv(
            "AETHERVILLE_STT_COMPUTE_TYPE", "int8_float16"
        )
        self._model: object | None = None

    def transcribe(
        self,
        audio_blob_b64: str | None,
        *,
        mime_type: str = "audio/webm",
        language: str | None = "ko",
        fallback_transcript: str | None = None,
    ) -> TranscriptionResult:
        if not audio_blob_b64:
            if fallback_transcript and fallback_transcript.strip():
                return TranscriptionResult(
                    transcript=fallback_transcript.strip(),
                    mode="fallback",
                    status="fallback",
                    detail="no audio blob supplied; typed fallback transcript used",
                )
            return TranscriptionResult(
                transcript=None,
                mode="faster_whisper",
                status="unavailable",
                detail="no audio blob supplied for faster-whisper",
            )
        try:
            audio_path = _write_audio_blob(audio_blob_b64, mime_type=mime_type)
            transcript = self._transcribe_path(audio_path, language=language)
        except Exception as exc:  # pragma: no cover - exercised on RunPod only
            if fallback_transcript and fallback_transcript.strip():
                return TranscriptionResult(
                    transcript=fallback_transcript.strip(),
                    mode="fallback",
                    status="fallback",
                    detail=f"faster-whisper failed; typed fallback used: {type(exc).__name__}",
                )
            return TranscriptionResult(
                transcript=None,
                mode="faster_whisper",
                status="unavailable",
                detail=f"faster-whisper unavailable: {type(exc).__name__}",
            )
        finally:
            if "audio_path" in locals():
                Path(audio_path).unlink(missing_ok=True)

        if transcript:
            return TranscriptionResult(
                transcript=transcript,
                mode="faster_whisper",
                status="ok",
                detail=f"model={self.model_size} device={self.device} compute={self.compute_type}",
            )
        return super().transcribe(
            audio_blob_b64,
            mime_type=mime_type,
            language=language,
            fallback_transcript=fallback_transcript,
        )

    def _transcribe_path(self, audio_path: str, *, language: str | None) -> str | None:
        model = self._ensure_model()
        segments, _info = model.transcribe(  # type: ignore[attr-defined]
            audio_path,
            language=language,
            vad_filter=True,
            beam_size=1,
        )
        transcript = " ".join(segment.text.strip() for segment in segments).strip()
        return transcript or None

    def _ensure_model(self) -> object:
        if self._model is None:
            from faster_whisper import WhisperModel  # type: ignore[import-not-found]

            self._model = WhisperModel(
                self.model_size,
                device=self.device,
                compute_type=self.compute_type,
            )
        return self._model

    def health_status(self) -> Literal["ok", "degraded", "stub"]:
        try:
            import faster_whisper  # noqa: F401
        except Exception:
            return "degraded"
        return "ok"

    def health_detail(self) -> str:
        return f"faster-whisper configured model={self.model_size} device={self.device}"


def _write_audio_blob(audio_blob_b64: str, *, mime_type: str) -> str:
    suffix = ".webm"
    if "wav" in mime_type:
        suffix = ".wav"
    elif "mpeg" in mime_type or "mp3" in mime_type:
        suffix = ".mp3"
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as handle:
        handle.write(base64.b64decode(audio_blob_b64))
        return handle.name


def transcriber_from_env() -> VoiceCommandStub:
    mode = os.getenv("AETHERVILLE_STT_MODE", "stub").strip().lower()
    if mode in {"real", "faster_whisper", "whisper"}:
        return FasterWhisperTranscriber()
    return VoiceCommandStub()
