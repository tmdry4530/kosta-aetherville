"""Optional voice/STT support for God Mode."""

from .stt import (
    FasterWhisperTranscriber,
    TranscriptionResult,
    VoiceCommandStub,
    transcriber_from_env,
)

__all__ = [
    "FasterWhisperTranscriber",
    "TranscriptionResult",
    "VoiceCommandStub",
    "transcriber_from_env",
]
