# Risk Register

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| RunPod Docker daemon unavailable | medium | high | do not retry Docker; use direct-process runtime |
| vLLM 14B AWQ latency too high | medium | high | plan caching, batching, 7B fallback |
| Spot instance interruption | high | medium | on-demand before demo, snapshot restore |
| Internet failure during demo | medium | critical | replay mode, recorded videos, tethering |
| LLM unsafe/awkward dialogue | medium | medium | system prompts, output filters, seed scenarios |
| Concurrent citizens deadlock | medium | high | semaphores, queues, load tests |
| YOLO training quality low | low | medium | augmentation, validation sample review |
| RL under baseline | medium | low | reward shaping, show training curve/baseline |
| Client FPS below 60 | medium | medium | LOD, dynamic entity count, lower shadows |
| Voice recognition fails | medium | low | headset, text fallback, macro buttons |
| Cost overrun | low | low | daily cap/checklist, stop idle pod |


## Accepted for final demo freeze

As of 2026-05-24T23:51:11+09:00, the user accepted these operational risks for the live demo:

- Public RunPod REST/WSS URLs are not stored in tracked config; use ignored env values or SSH tunnel mode.
- Vision canonical port `8001` is blocked on the current pod; demo vision uses verified port `18001`.
- Real vLLM, YOLO, PPO/LSTM, and STT remain opt-in upgrade paths and are not started by default.
- Remote `rsync` is unavailable; tar-over-SSH sync fallback is accepted.
