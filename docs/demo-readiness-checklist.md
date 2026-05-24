# 15-minute Demo Readiness Checklist

## Before the demo

- [ ] Run `bash infra/runpod/verify_runpod.sh`.
- [ ] Confirm Docker remains direct-process fallback if daemon is unavailable.
- [ ] Run `bash infra/runpod/health_check_direct.sh` inside the synced workspace or through the deployment helper.
- [ ] Start local client with `pnpm dev`.
- [ ] Open the live route `/` and confirm connection/tick status.
- [ ] Open `/replay` in a second tab for fallback.

## 15-minute flow

1. 0:00–2:00 — architecture overview: RunPod backend + browser renderer.
2. 2:00–5:00 — city scene, citizens, vehicle motion, traffic lights.
3. 5:00–8:00 — memory panel and citizen dialogue/reflection events.
4. 8:00–10:00 — vehicle camera mock YOLO boxes and slowdown.
5. 10:00–12:00 — traffic forecast + fixed-cycle/PPO fallback explanation.
6. 12:00–14:00 — God Mode text command and macro buttons.
7. 14:00–15:00 — replay fallback and metrics report.

## Failure fallback

- RunPod unreachable: switch to `/replay`.
- Voice/STT unavailable: use text command or macro buttons.
- Real YOLO unavailable: continue with deterministic mock boxes.
- PPO/LSTM unavailable: show baseline controller and deterministic forecast.
- Public WSS/REST not configured: use SSH/in-pod smoke evidence and replay route for presentation.
