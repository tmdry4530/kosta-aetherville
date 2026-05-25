# God Mode Command Path

## Current demo mode

- Text command is the stable primary path.
- Optional real 4090 vLLM interpretation is enabled with `AETHERVILLE_GOD_MODE_LLM=vllm`; rules remain the fallback.
- Voice/STT is available through `/api/v1/god/voice`; fallback/stub mode remains the default until real STT is enabled.
- `GodModeMicPanel` provides text input, macro buttons, and a `MediaRecorder` voice capture button for demo reliability.

## Command categories

`GodCommandDispatcher` supports:

- `environment`: changes weather and emits `weather_changed`.
- `event`: injects a visible city event and emits `event_injected`.
- `person`: injects citizen memory and emits `person_updated`.
- `infrastructure`: updates visible infrastructure status and emits `infrastructure_changed`.
- `relationship`: injects memories for both related citizens and emits `relationship_changed`.

## Real vLLM interpretation mode

When `AETHERVILLE_GOD_MODE_LLM=vllm` is set on the orchestrator, the command path is:

1. Send presenter text to the OpenAI-compatible RunPod vLLM `/chat/completions` endpoint.
2. Require a compact JSON classification with one to four safe actions from the fixed vocabulary: `rain`, `clear`, `snow`, `traffic_jam`, `taxi_call`, `meeting`, `memory`, `person_update`, `relationship`, or `generic`.
3. Apply only the existing deterministic dispatcher effects for those actions.
4. Emit concrete sub-effect events plus one `god_command_executed` summary event for multi-action plans.
5. Return `GodCommandResponse.ai_mode`, `ai_confidence`, `ai_reason`, and `ai_actions` so the browser can display `vLLM NN%`, the action sequence, or `rules fallback`.

The model never executes arbitrary state changes. Timeout, invalid JSON, disabled env, or vLLM failure falls back to the deterministic rules dispatcher, which also handles obvious multi-intent commands such as rain + taxi + traffic.

## Broadcast behavior

The orchestrator emits every resulting event envelope on `aetherville:event`, then emits a
fresh `aetherville:state_update` so the browser can show visible effects.

## Voice path

1. Browser `MediaRecorder` captures audio and posts `VoiceCommandRequest` to `/api/v1/god/voice`.
2. The server uses the configured STT provider. Default mode is fallback/stub; real mode is `AETHERVILLE_STT_MODE=faster_whisper`.
3. The endpoint reports `stt_status=ok|fallback|unavailable` and never hides fallback use.
4. The transcript is converted to the same `GodCommand` dispatcher path as text commands.
5. If browser microphone/STT fails, the current text input is sent as `fallback_transcript` so the demo remains reliable. Server-side real-audio STT has been verified with `scripts/voice_stt_smoke.py`; human microphone success should still be confirmed in the browser by checking `stt_status="ok"`.
