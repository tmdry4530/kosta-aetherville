from __future__ import annotations

from aetherville_server.voice import VoiceCommandStub


def test_voice_stub_is_optional_until_text_path_is_stable() -> None:
    stub = VoiceCommandStub()

    assert stub.transcribe(None) is None
    command = stub.command_from_transcript("도시에 비를 내려줘")
    assert command.input_modality == "voice"
    assert command.raw_text.startswith("도시에")
