# Risk Register

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| RunPod Docker daemon unavailable | medium | high | detect first; direct-process fallback |
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
