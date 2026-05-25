from __future__ import annotations

from aetherville_server.voice import FasterWhisperTranscriber, VoiceCommandStub


def test_voice_stub_uses_typed_fallback_until_real_stt_is_available() -> None:
    stub = VoiceCommandStub()

    unavailable = stub.transcribe(None)
    assert unavailable.transcript is None
    assert unavailable.status == "unavailable"

    result = stub.transcribe(None, fallback_transcript="도시에 비를 내려줘")
    assert result.transcript == "도시에 비를 내려줘"
    assert result.mode == "fallback"

    command = stub.command_from_transcript(result.transcript)
    assert command.input_modality == "voice"
    assert command.raw_text.startswith("도시에")


def test_faster_whisper_provider_keeps_fallback_without_audio() -> None:
    provider = FasterWhisperTranscriber(model_size="tiny", device="cpu", compute_type="int8")

    result = provider.transcribe(None, fallback_transcript="민지가 택시를 불러줘")

    assert result.transcript == "민지가 택시를 불러줘"
    assert result.mode == "fallback"
    assert result.status == "fallback"
