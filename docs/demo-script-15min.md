# 15-minute Demo Script — Project Aetherville

## 0:00–2:00 — Opening explanation

- Introduce Aetherville as an AI society simulator: RunPod GPU backend owns AI
  services and simulation, local browser owns 3D rendering.
- State the verified runtime: direct-process services on RunPod, no Docker in the
  current pod, deterministic stubs for demo-safe ML paths.
- Show the live client route and mention `/replay` as the failure fallback.

## 2:00–5:00 — Normal city simulation

- Before presenting, run `python3 scripts/demo_rehearsal.py --orchestrator-url http://127.0.0.1:18080 --client-url http://127.0.0.1:3000 --expected-client-endpoint http://127.0.0.1:18080` once against the selected Mode B tunnel or equivalent public endpoint.
- Open the live city route.
- Point out the `SCENE DIRECTOR · LIVE IMPACT` HUD first, then weather, tick count, citizens, vehicles, drones, traffic lights, and
  connection status.
- Explain that state arrives from the orchestrator REST/Socket.IO contract.

## 5:00–7:00 — Citizen and memory panel

- Select or highlight a citizen in the UI.
- Show persona, plan tree, memory stream, and recent dialogue/reflection events.
- Explain that LLM-like planning is cached/event-driven, not called every tick.

## 7:00–9:00 — Vehicle and vision panel

- Show the vehicle camera panel.
- Point out the `REAL YOLO · RunPod 4090` badge when the camera endpoint is running
  in real mode, and explain that the panel is polling
  `/api/v1/vehicles/v01/camera`.
- Explain that the verified demo uses vision service port `18001`; if real YOLO is
  unavailable, the panel falls back to deterministic detections instead of hiding
  the feature.

## 9:00–11:00 — Traffic panel

- Show traffic lights and the forecast chart.
- Point out the `GPU POLICY` badge when the RunPod checkpoint is active.
- Explain the measured traffic policy result: the current CUDA-trained
  checkpoint reduced average queue by `31.628%` versus fixed cycle in the
  deterministic traffic environment.
- Point out the `LSTM FORECAST` badge when the RunPod forecast checkpoint is
  active. The current CUDA-trained LSTM reports `MAPE 11.84%` on the demo
  forecast distribution.
- Explain that full PPO/LSTM training remains the upgrade path, but the demo is
  no longer just deterministic traffic bars: the signal action and the forecast
  can both be loaded from 4090-trained checkpoints.
- Mention that training jobs are intentionally not started during the live demo.

## 11:00–13:30 — God Mode command demo + AI learning panel

- Enter a multi-action text command such as “도시에 비를 내리고 민지가 택시를 부르게 하고 출근길을 혼잡하게 만들고 민수와 만나게 해줘” or use a macro button.
- Point out `vLLM NN%` and the `actions: rain + traffic_jam + taxi_call + meeting` sequence when `AETHERVILLE_GOD_MODE_LLM=vllm` is enabled; if it says `rules fallback`, explain the safety fallback.
- Confirm the visible world-state effect in the `SCENE DIRECTOR` HUD and `Live impact board`: RAIN, TAXI, TRAFFIC, MEETING, GPU POLICY, and LSTM FORECAST cards should light up after the combined command.
- Show the `AI 학습 루프` panel and point out experience count, epoch, policy
  version, traffic bias, and taxi success signal changing after commands.
- State clearly that this is persistent deterministic adaptation for demo
  safety, not live training of new vLLM/YOLO/PPO/LSTM weights.
- Optionally click `Voice STT`, speak the same command, then stop recording. If the result says `fallback`, explain that the demo safely used the typed fallback transcript. If it says `stt_status=ok`, it is the real faster-whisper path; the server-side real-audio smoke has already been verified with a temporary Korean WAV, but the live microphone path still depends on browser permission and codec capture.

## 13:30–15:00 — Fallback and wrap-up

- Open `/replay` and show that the client remains demonstrable without RunPod.
- Summarize residual risks: public endpoint setup, vision port mapping, and real
  ML workloads behind explicit cost/model approval.
- Close with next steps: public REST/WSS exposure and optional real model paths.
