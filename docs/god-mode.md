# God Mode Command Path

## Current demo mode

- Text command is the stable primary path.
- Optional real 4090 vLLM interpretation is enabled with `AETHERVILLE_GOD_MODE_LLM=vllm`; rules remain the fallback.
- Voice/STT is represented by `VoiceCommandStub` and disabled in the browser until the text path is stable.
- `GodModeMicPanel` provides text input and macro buttons for demo reliability.

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

## Voice upgrade path

1. Keep the `GodCommand` schema unchanged.
2. Add browser recording once text command latency/effects are stable.
3. Run STT through a bounded service or faster-whisper worker only after model/cost approval.
4. Convert the transcript to the same `GodCommand` dispatcher path.
