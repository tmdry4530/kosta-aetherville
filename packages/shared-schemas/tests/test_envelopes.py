from __future__ import annotations

import json
from pathlib import Path
from typing import cast

from aetherville_schemas import (
    AckPayload,
    Envelope,
    EnvelopeType,
    ErrorPayload,
    EventPayload,
    GodCommand,
)

FIXTURES = Path(__file__).parent / "fixtures"


def load_fixture(name: str) -> dict[str, object]:
    return cast(dict[str, object], json.loads((FIXTURES / name).read_text(encoding="utf-8")))


def test_event_envelope_parses_payload() -> None:
    envelope = Envelope.model_validate(load_fixture("event.json"))
    payload = EventPayload.model_validate(envelope.payload)

    assert envelope.type is EnvelopeType.EVENT
    assert payload.kind == "weather_changed"
    assert payload.metadata["weather"] == "rain"


def test_command_envelope_parses_god_command_payload() -> None:
    envelope = Envelope.model_validate(load_fixture("command.json"))
    payload = GodCommand.model_validate(envelope.payload)

    assert envelope.type is EnvelopeType.COMMAND
    assert payload.user_id == "presenter"
    assert payload.input_modality == "text"


def test_ack_envelope_parses_payload() -> None:
    envelope = Envelope.model_validate(load_fixture("ack.json"))
    payload = AckPayload.model_validate(envelope.payload)

    assert envelope.type is EnvelopeType.ACK
    assert payload.ok is True
    assert payload.correlation_id == "cmd_001"


def test_error_envelope_parses_payload() -> None:
    envelope = Envelope.model_validate(load_fixture("error.json"))
    payload = ErrorPayload.model_validate(envelope.payload)

    assert envelope.type is EnvelopeType.ERROR
    assert payload.code == "bad_command"
    assert payload.retryable is False
