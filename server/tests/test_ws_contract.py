from __future__ import annotations

import asyncio
from typing import Any

import pytest

from aetherville_schemas import Envelope, EnvelopeType, WorldStatePayload
from aetherville_server import main


def test_socket_connect_emits_ack_and_state_update(monkeypatch: pytest.MonkeyPatch) -> None:
    emitted: list[tuple[str, dict[str, Any], str | None]] = []

    async def fake_emit(event: str, data: dict[str, Any], to: str | None = None) -> None:
        emitted.append((event, data, to))

    monkeypatch.setattr(main.sio, "emit", fake_emit)

    asyncio.run(main.on_connect("sid-1", {}, None))

    assert [event for event, _, _ in emitted] == ["aetherville:ack", "aetherville:state_update"]
    ack = Envelope.model_validate(emitted[0][1])
    state = Envelope.model_validate(emitted[1][1])
    assert ack.type is EnvelopeType.ACK
    assert state.type is EnvelopeType.STATE_UPDATE
    assert emitted[1][2] == "sid-1"
    WorldStatePayload.model_validate(state.payload)


def test_socket_command_emits_event(monkeypatch: pytest.MonkeyPatch) -> None:
    emitted: list[tuple[str, dict[str, Any], str | None]] = []

    async def fake_emit(event: str, data: dict[str, Any], to: str | None = None) -> None:
        emitted.append((event, data, to))

    monkeypatch.setattr(main.sio, "emit", fake_emit)
    command = Envelope(
        type=EnvelopeType.COMMAND,
        tick=2,
        payload={
            "kind": "god_command",
            "input_modality": "text",
            "raw_text": "날씨를 맑게 바꿔줘",
            "audio_blob_b64": None,
            "user_id": "presenter",
        },
    )

    asyncio.run(main.on_command("sid-2", command.model_dump(mode="json")))

    assert emitted[0][0] == "aetherville:event"
    event_envelope = Envelope.model_validate(emitted[0][1])
    assert event_envelope.type is EnvelopeType.EVENT
    assert emitted[0][2] == "sid-2"
