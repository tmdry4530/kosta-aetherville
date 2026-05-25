# 15-minute Demo Script — Project Aetherville

## 0:00–2:00 — Opening explanation

- Introduce Aetherville as an AI society simulator: RunPod GPU backend owns AI
  services and simulation, local browser owns 3D rendering.
- State the verified runtime: direct-process services on RunPod, no Docker in the
  current pod, deterministic stubs for demo-safe ML paths.
- Show the live client route and mention `/replay` as the failure fallback.

## 2:00–5:00 — Normal city simulation

- Open the live city route.
- Point out weather, tick count, citizens, vehicles, drones, traffic lights, and
  connection status.
- Explain that state arrives from the orchestrator REST/Socket.IO contract.

## 5:00–7:00 — Citizen and memory panel

- Select or highlight a citizen in the UI.
- Show persona, plan tree, memory stream, and recent dialogue/reflection events.
- Explain that LLM-like planning is cached/event-driven, not called every tick.

## 7:00–9:00 — Vehicle and vision panel

- Show the vehicle camera panel.
- Point out deterministic detection boxes and vehicle slowdown behavior.
- Explain that the verified demo uses vision service port `18001`; real YOLO is a
  documented GPU upgrade path.

## 9:00–11:00 — Traffic panel

- Show traffic lights and the forecast chart.
- Explain fixed-cycle baseline, PPO wrapper fallback, and deterministic forecast
  payloads.
- Mention that training jobs are intentionally not started during the live demo.

## 11:00–13:30 — God Mode command demo + AI learning panel

- Enter a text command such as “make it rainy” or use a macro button.
- Confirm the visible world-state effect and event timeline update.
- Show the `AI 학습 루프` panel and point out experience count, epoch, policy
  version, traffic bias, and taxi success signal changing after commands.
- State clearly that this is persistent deterministic adaptation for demo
  safety, not live training of new vLLM/YOLO/PPO/LSTM weights.
- If voice is unavailable, explain that text is the supported reliable path.

## 13:30–15:00 — Fallback and wrap-up

- Open `/replay` and show that the client remains demonstrable without RunPod.
- Summarize residual risks: public endpoint setup, vision port mapping, and real
  ML workloads behind explicit cost/model approval.
- Close with next steps: public REST/WSS exposure and optional real model paths.
