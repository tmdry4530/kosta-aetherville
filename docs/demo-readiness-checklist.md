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
5. 10:00–12:00 — traffic forecast + GPU policy checkpoint badge when active.
6. 12:00–14:00 — God Mode text command and macro buttons.
7. 14:00–15:00 — replay fallback and metrics report.

## Failure fallback

- RunPod unreachable: switch to `/replay`.
- Voice/STT unavailable or `stt_status=fallback`: use text command or macro buttons; only claim real STT when response reports `stt_status=ok`.
- Real YOLO unavailable: continue with deterministic mock boxes and state that the panel is in fallback mode.
- Traffic checkpoint unavailable: show baseline controller and deterministic forecast.
- PPO/LSTM unavailable: explain that the current short CUDA-trained checkpoint is the demo-safe bridge before full PPO/LSTM training.
- Public WSS/REST not configured: use SSH/in-pod smoke evidence and replay route for presentation.

## Final freeze checklist

- [ ] `docs/live-demo-runbook.md` has been followed in Mode A or Mode B.
- [ ] RunPod direct-process services started with `AETHERVILLE_VISION_PORT=18001`.
- [ ] Orchestrator health returns `ok`.
- [ ] Learning status returns a `deterministic_online_adaptation` snapshot.
- [ ] Vision health returns `ok` on port `18001`.
- [ ] If using the 4090 traffic checkpoint, `/api/v1/sim/state` reports
      `traffic_ai.mode="checkpoint"` and `training_backend="torch_cuda"`.
- [ ] If using the 4090 LSTM forecast checkpoint, `/api/v1/sim/state` reports
      `traffic_forecast_ai.mode="lstm_checkpoint"` and
      `training_backend="torch_cuda"`.
- [ ] If using live microphone voice, `/api/v1/god/voice` reports
      `stt_status="ok"`; if it reports `fallback`, present it as the typed
      fallback transcript path. Server-side real-audio STT was verified with a
      temporary Korean WAV smoke on 2026-05-25.
- [ ] Socket.IO polling smoke receives `aetherville:state_update`.
- [ ] Local client starts with `NEXT_PUBLIC_ORCHESTRATOR_URL`,
      `NEXT_PUBLIC_SOCKET_URL`, and `NEXT_PUBLIC_SOCKET_TRANSPORTS=polling`
      set to the selected endpoint.
- [ ] If using `next build && next start` instead of `pnpm dev`, `next start` was
      launched with the selected `NEXT_PUBLIC_*` endpoint values; the live route is
      dynamic and reads them at process start.
- [ ] `python3 scripts/demo_rehearsal.py --orchestrator-url http://127.0.0.1:18080 --client-url http://127.0.0.1:3000 --expected-client-endpoint http://127.0.0.1:18080` passes.
- [ ] `python3 scripts/browser_demo_smoke.py --mode live --url http://127.0.0.1:3000/ --expected-endpoint http://127.0.0.1:18080` passes with no client-side exception.
- [ ] `python3 scripts/browser_demo_smoke.py --mode replay --url http://127.0.0.1:3000/replay` passes.
- [ ] `python3 scripts/browser_visual_smoke.py --mode both --client-url http://127.0.0.1:3000 --expected-endpoint http://127.0.0.1:18080` passes and records 1920x1080 nonblank screenshots under ignored `dogfood-output/visual-smoke/`.
- [ ] `python3 scripts/browser_impact_smoke.py --orchestrator-url http://127.0.0.1:18080 --client-url http://127.0.0.1:3000` passes and proves before/after God Mode screenshot delta plus rain/taxi/traffic/meeting state effects.
- [ ] Live route `/` renders city state.
- [ ] Replay route `/replay` works before the live demo begins.
- [ ] `SCENE DIRECTOR · LIVE IMPACT` HUD and `Live impact board` are visible before God Mode, then active cards light up after the combined command.
- [ ] God Mode text command has been tested once.
- [ ] `AI 학습 루프` panel is visible, and presenter says it is persistent
      deterministic adaptation rather than real neural-weight training.
- [ ] No Docker or Docker Compose command is part of the demo path.
