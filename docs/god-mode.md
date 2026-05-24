# God Mode Command Path

## Current demo mode

- Text command is the stable primary path.
- Voice/STT is represented by `VoiceCommandStub` and disabled in the browser until the text path is stable.
- `GodModeMicPanel` provides text input and macro buttons for demo reliability.

## Command categories

`GodCommandDispatcher` supports:

- `environment`: changes weather and emits `weather_changed`.
- `event`: injects a visible city event and emits `event_injected`.
- `person`: injects citizen memory and emits `person_updated`.
- `infrastructure`: updates visible infrastructure status and emits `infrastructure_changed`.
- `relationship`: injects memories for both related citizens and emits `relationship_changed`.

## Broadcast behavior

The orchestrator emits every resulting event envelope on `aetherville:event`, then emits a
fresh `aetherville:state_update` so the browser can show visible effects.

## Voice upgrade path

1. Keep the `GodCommand` schema unchanged.
2. Add browser recording once text command latency/effects are stable.
3. Run STT through a bounded service or faster-whisper worker only after model/cost approval.
4. Convert the transcript to the same `GodCommand` dispatcher path.
