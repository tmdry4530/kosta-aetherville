# 15-minute Demo Readiness Checklist

## Before the demo

- [ ] Run `bash infra/runpod/verify_runpod.sh`.
- [ ] Confirm direct-process runtime is active and no Docker command is needed.
- [ ] Run `bash infra/runpod/health_check_direct.sh` inside the synced workspace or through the deployment helper.
- [ ] Start local client with `pnpm dev`.
- [ ] Open the live route `/` and confirm connection/tick status.
- [ ] Open `/replay` in a second tab for fallback.

## 15-minute flow

1. 0:00–2:00 — architecture overview: RunPod backend + browser renderer.
2. 2:00–5:00 — city scene, citizens, vehicle motion, traffic lights.
3. 5:00–8:00 — memory panel and citizen dialogue/reflection events.
4. 8:00–10:00 — vehicle camera endpoint, real YOLO badge when available, and fallback slowdown boxes.
5. 10:00–12:00 — traffic forecast + fixed-cycle/PPO fallback explanation.
6. 12:00–14:00 — God Mode text command and macro buttons.
7. 14:00–15:00 — replay fallback and metrics report.

## Failure fallback

- RunPod unreachable: switch to `/replay`.
- Voice/STT unavailable: use text command or macro buttons.
- Real YOLO unavailable: continue with deterministic mock boxes and state that the panel is in fallback mode.
- PPO/LSTM unavailable: show baseline controller and deterministic forecast.
- Public WSS/REST not configured: use SSH/in-pod smoke evidence and replay route for presentation.

## Final freeze checklist

- [ ] `docs/live-demo-runbook.md` has been followed in Mode A or Mode B.
- [ ] RunPod direct-process services started with `AETHERVILLE_VISION_PORT=18001`.
- [ ] Orchestrator health returns `ok`.
- [ ] Learning status returns a `deterministic_online_adaptation` snapshot.
- [ ] Vision health returns `ok` on port `18001`.
- [ ] Socket.IO polling smoke receives `aetherville:state_update`.
- [ ] Local client starts with `NEXT_PUBLIC_ORCHESTRATOR_URL`,
      `NEXT_PUBLIC_SOCKET_URL`, and `NEXT_PUBLIC_SOCKET_TRANSPORTS=polling`
      set to the selected endpoint.
- [ ] If using `next build && next start` instead of `pnpm dev`, the build was
      created with the same selected `NEXT_PUBLIC_*` endpoint values.
- [ ] Live route `/` renders city state.
- [ ] Replay route `/replay` works before the live demo begins.
- [ ] God Mode text command has been tested once.
- [ ] `AI 학습 루프` panel is visible, and presenter says it is persistent
      deterministic adaptation rather than real neural-weight training.
- [ ] No Docker or Docker Compose command is part of the demo path.
