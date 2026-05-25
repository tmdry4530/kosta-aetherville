# Live Demo Runbook — Project Aetherville

This runbook freezes the verified demo path: local browser client + RunPod
backend services running as direct processes. Do not use Docker, Docker Compose,
Docker-in-Docker, or blind Docker retries for the current pod.

All RunPod connection values must come from `infra/runpod/.env.runpod` or the
process environment. Do not print or commit the filled file.

## 0. Preflight

```bash
git status --short
python3 -m json.tool TASKS.json >/tmp/aetherville-tasks-check.json
bash -n infra/runpod/verify_runpod.sh \
  infra/runpod/deploy_over_ssh.sh \
  infra/runpod/bootstrap_runpod.sh \
  infra/runpod/start_direct_processes.sh \
  infra/runpod/stop_direct_processes.sh \
  infra/runpod/health_check_direct.sh
```

## 1. Start or refresh RunPod direct-process services

From the repository root on the local machine:

```bash
AETHERVILLE_BOOTSTRAP_UV=1 \
AETHERVILLE_VLLM_MODE=mock \
AETHERVILLE_REDIS_MODE=memory \
AETHERVILLE_VISION_PORT=18001 \
bash infra/runpod/deploy_over_ssh.sh --mode direct
```

This syncs the repo, starts or reuses repo-managed pid-file processes, and runs
`infra/runpod/health_check_direct.sh` remotely. Expected service ports on the
verified pod:

- Orchestrator REST + Socket.IO: `8080`
- vLLM OpenAI-compatible fallback: `8000`
- Vision mock or real YOLO service: `18001`
- Redis: memory fallback

For the approved RTX 4090 “real AI” demo mode, use the same direct-process path
with explicit opt-in variables:

```bash
AETHERVILLE_BOOTSTRAP_UV=1 \
AETHERVILLE_VLLM_MODE=real \
AETHERVILLE_LLM_MODE=vllm \
AETHERVILLE_GOD_MODE_LLM=vllm \
AETHERVILLE_STT_MODE=faster_whisper \
AETHERVILLE_BOOTSTRAP_STT=1 \
AETHERVILLE_STT_MODEL=base \
AETHERVILLE_STT_DEVICE=cuda \
AETHERVILLE_VISION_MODE=real \
AETHERVILLE_BOOTSTRAP_YOLO=1 \
AETHERVILLE_REDIS_MODE=memory \
AETHERVILLE_VISION_PORT=18001 \
AETHERVILLE_HEALTH_RETRIES=120 \
AETHERVILLE_HEALTH_SLEEP=2 \
bash infra/runpod/deploy_over_ssh.sh --mode direct
```

In this mode the orchestrator camera endpoint inherits
`AETHERVILLE_CAMERA_VISION_MODE=real`, so `/api/v1/vehicles/v01/camera` can
return `VehicleCameraFrame.mode="real"` and the browser vehicle panel can badge
`REAL YOLO · RunPod 4090`.

To include the verified CUDA-trained traffic policy, train/export the checkpoint
once on the pod, then restart the orchestrator with its path:

```bash
ssh "$RUNPOD_USER@$RUNPOD_HOST" -p "$RUNPOD_SSH_PORT" -i "$RUNPOD_SSH_KEY" \
  "cd \"$RUNPOD_REMOTE_DIR\" && mkdir -p /workspace/aetherville-model-cache/traffic && \
   .venv/bin/python -m aetherville_server.traffic_ai.train_gpu_policy \
     --output /workspace/aetherville-model-cache/traffic/traffic_policy_v1.json \
     --episodes 320 --horizon 80 --device cuda"

AETHERVILLE_BOOTSTRAP_UV=1 \
AETHERVILLE_VLLM_MODE=real \
AETHERVILLE_LLM_MODE=vllm \
AETHERVILLE_GOD_MODE_LLM=vllm \
AETHERVILLE_VISION_MODE=real \
AETHERVILLE_TRAFFIC_POLICY_CHECKPOINT=/workspace/aetherville-model-cache/traffic/traffic_policy_v1.json \
AETHERVILLE_REDIS_MODE=memory \
AETHERVILLE_VISION_PORT=18001 \
AETHERVILLE_HEALTH_RETRIES=120 \
AETHERVILLE_HEALTH_SLEEP=2 \
bash infra/runpod/deploy_over_ssh.sh --mode direct
```

Expected state marker after restart: `traffic_ai.mode="checkpoint"` and
`traffic_ai.training_backend="torch_cuda"`.

To include the verified CUDA-trained LSTM traffic forecast, train/export the
forecast checkpoint and restart the orchestrator with both traffic checkpoint
paths:

```bash
ssh "$RUNPOD_USER@$RUNPOD_HOST" -p "$RUNPOD_SSH_PORT" -i "$RUNPOD_SSH_KEY" \
  "cd \"$RUNPOD_REMOTE_DIR\" && mkdir -p /workspace/aetherville-model-cache/traffic && \
   .venv/bin/python -m aetherville_server.traffic_ai.train_lstm_forecast \
     --output /workspace/aetherville-model-cache/traffic/traffic_lstm_v1.json \
     --samples 960 --epochs 180 --sequence-length 12 --hidden-size 10 --device cuda"

AETHERVILLE_BOOTSTRAP_UV=1 \
AETHERVILLE_VLLM_MODE=real \
AETHERVILLE_LLM_MODE=vllm \
AETHERVILLE_GOD_MODE_LLM=vllm \
AETHERVILLE_VISION_MODE=real \
AETHERVILLE_TRAFFIC_POLICY_CHECKPOINT=/workspace/aetherville-model-cache/traffic/traffic_policy_v1.json \
AETHERVILLE_TRAFFIC_FORECAST_CHECKPOINT=/workspace/aetherville-model-cache/traffic/traffic_lstm_v1.json \
AETHERVILLE_REDIS_MODE=memory \
AETHERVILLE_VISION_PORT=18001 \
AETHERVILLE_HEALTH_RETRIES=120 \
AETHERVILLE_HEALTH_SLEEP=2 \
bash infra/runpod/deploy_over_ssh.sh --mode direct
```

Expected state marker after restart:
`traffic_forecast_ai.mode="lstm_checkpoint"` and
`traffic_forecast_ai.training_backend="torch_cuda"`.

God Mode vLLM smoke after real-mode restart:

```bash
curl -fsS -H 'content-type: application/json' \
  -d '{"kind":"god_command","input_modality":"text","raw_text":"도시에 비를 내리고 민지가 택시를 부르게 하고 출근길을 혼잡하게 만들고 민수와 만나게 해줘","audio_blob_b64":null,"user_id":"presenter"}' \
  http://127.0.0.1:18080/api/v1/god/command | python3 -m json.tool
```

Expected marker when enabled: `ai_mode="vllm"`, `ai_actions` containing several safe actions, and a `god_command_executed` summary event. If vLLM is unavailable, the command remains demo-safe and falls back to `ai_mode="rules"`.


### Voice/STT smokes

Fallback smoke, no real audio:

```bash
curl -fsS -H 'content-type: application/json' \
  -d '{"kind":"voice_command","audio_blob_b64":null,"mime_type":"audio/webm","user_id":"presenter","fallback_transcript":"도시에 비를 내리고 민지가 택시를 부르게 해줘","language":"ko"}' \
  http://127.0.0.1:18080/api/v1/god/voice | python3 -m json.tool
```

Fallback smoke should return `stt_status="fallback"` and nested `command.accepted=true`.

Real-audio STT smoke, using any temporary Korean WAV/WEBM/MP3 outside the repo:

```bash
python3 scripts/voice_stt_smoke.py \
  --orchestrator-url http://127.0.0.1:18080 \
  --audio-file /tmp/aetherville_voice_ko.wav \
  --mime-type audio/wav \
  --expect-status ok
```

Verified 2026-05-25: a temporary Korean TTS WAV saying “도시에 비를 내리고 민지가 택시를 부르게 해줘” returned `stt_status="ok"`, `stt_mode="faster_whisper"`, transcript match, nested `command.accepted=true`, `ai_mode="vllm"`, and `ai_actions=[rain, taxi_call]`. Human microphone permission still needs live browser QA; only claim real microphone STT after the browser response also reports `stt_status="ok"`.

## 2. Verify RunPod health

```bash
bash infra/runpod/verify_runpod.sh
```

The verifier checks SSH/GPU/runtime/process status and records the no-Docker
policy. It intentionally does not run Docker commands.

### In-pod direct health

If services were started by the deploy helper, direct health has already run. To
rerun it manually through SSH without exposing secrets:

```bash
set -a
source infra/runpod/.env.runpod
set +a
ssh -i "$RUNPOD_SSH_KEY" -p "$RUNPOD_SSH_PORT" "$RUNPOD_USER@$RUNPOD_HOST" \
  "cd \"$RUNPOD_REMOTE_DIR\" && AETHERVILLE_VISION_PORT=18001 AETHERVILLE_REDIS_MODE=memory bash infra/runpod/health_check_direct.sh"
```

## 3. Verify Socket.IO polling smoke

Use this stdlib polling smoke against either a public endpoint or the SSH tunnel
endpoint from Mode B below:

```bash
AETHERVILLE_ORCHESTRATOR_URL="${AETHERVILLE_ORCHESTRATOR_URL:-http://127.0.0.1:18080}" python3 - <<'PY'
import json
import os
import time
import urllib.parse
import urllib.request

base = os.environ["AETHERVILLE_ORCHESTRATOR_URL"].rstrip("/")
handshake_url = f"{base}/socket.io/?EIO=4&transport=polling&t={int(time.time() * 1000)}"
with urllib.request.urlopen(handshake_url, timeout=5) as response:
    handshake = response.read().decode()
assert handshake.startswith("0"), handshake
sid = json.loads(handshake[1:])["sid"]
encoded_sid = urllib.parse.quote(sid, safe="")
post_url = f"{base}/socket.io/?EIO=4&transport=polling&sid={encoded_sid}"
request = urllib.request.Request(
    post_url,
    data=b"40{}",
    method="POST",
    headers={"Content-Type": "text/plain;charset=UTF-8"},
)
with urllib.request.urlopen(request, timeout=5) as response:
    response.read()
received = ""
for _ in range(5):
    poll_url = f"{base}/socket.io/?EIO=4&transport=polling&sid={encoded_sid}&t={int(time.time() * 1000)}"
    with urllib.request.urlopen(poll_url, timeout=5) as response:
        received += response.read().decode(errors="replace")
    if "aetherville:state_update" in received:
        break
    time.sleep(0.2)
assert "aetherville:state_update" in received, received[:500]
print("Socket.IO polling smoke passed")
PY
```

## 4. Mode A — public RunPod endpoint

Use this mode only after RunPod exposes public HTTP(S) ports. Store these values
in a local shell or ignored env file; do not commit them.

```bash
set -a
source infra/runpod/.env.runpod
set +a

curl -fsS "$RUNPOD_PUBLIC_ORCHESTRATOR_URL/api/v1/health"
curl -fsS "$RUNPOD_PUBLIC_ORCHESTRATOR_URL/api/v1/learning/status"
curl -fsS "$RUNPOD_PUBLIC_VISION_URL/health"
python3 scripts/demo_smoke.py --orchestrator-url "$RUNPOD_PUBLIC_ORCHESTRATOR_URL"

# Then run the Socket.IO polling smoke from section 3 with:
# AETHERVILLE_ORCHESTRATOR_URL="$RUNPOD_PUBLIC_ORCHESTRATOR_URL"
```

Start the local client against the public endpoint:

```bash
set -a
source infra/runpod/.env.runpod
set +a

NEXT_PUBLIC_ORCHESTRATOR_URL="$RUNPOD_PUBLIC_ORCHESTRATOR_URL" \
NEXT_PUBLIC_SOCKET_URL="${RUNPOD_PUBLIC_SOCKET_URL:-$RUNPOD_PUBLIC_ORCHESTRATOR_URL}" \
NEXT_PUBLIC_SOCKET_TRANSPORTS="${NEXT_PUBLIC_SOCKET_TRANSPORTS:-polling}" \
pnpm dev
```


Production-style browser smoke after `next build && next start`:

Terminal 1:

```bash
pnpm --filter @aetherville/client build
NEXT_PUBLIC_ORCHESTRATOR_URL="$RUNPOD_PUBLIC_ORCHESTRATOR_URL" \
NEXT_PUBLIC_SOCKET_URL="${RUNPOD_PUBLIC_SOCKET_URL:-$RUNPOD_PUBLIC_ORCHESTRATOR_URL}" \
NEXT_PUBLIC_SOCKET_TRANSPORTS="${NEXT_PUBLIC_SOCKET_TRANSPORTS:-polling}" \
pnpm --filter @aetherville/client exec next start -H 0.0.0.0 -p 3000
```

Terminal 2:

```bash
python3 scripts/browser_demo_smoke.py \
  --mode live \
  --url http://127.0.0.1:3000/ \
  --expected-endpoint "$RUNPOD_PUBLIC_ORCHESTRATOR_URL"
python3 scripts/browser_demo_smoke.py \
  --mode replay \
  --url http://127.0.0.1:3000/replay
```

The live route is dynamically server-rendered, so `next start` reads the selected endpoint values at process start and passes the runtime orchestrator URL into browser panels.

Open:

- Live city: `http://localhost:3000/`
- Replay fallback: `http://localhost:3000/replay`

## 5. Mode B — SSH tunnel fallback

Use this mode when public RunPod REST/WSS URLs are not configured. Keep the
tunnel terminal open during the demo.

```bash
set -a
source infra/runpod/.env.runpod
set +a

ssh -N \
  -L 18080:127.0.0.1:8080 \
  -L 18000:127.0.0.1:8000 \
  -L 18001:127.0.0.1:18001 \
  -i "$RUNPOD_SSH_KEY" \
  -p "$RUNPOD_SSH_PORT" \
  "$RUNPOD_USER@$RUNPOD_HOST"
```

In a second terminal:

```bash
curl -fsS http://127.0.0.1:18080/api/v1/health
curl -fsS http://127.0.0.1:18080/api/v1/learning/status
curl -fsS http://127.0.0.1:18080/api/v1/vehicles/v01/camera
curl -fsS http://127.0.0.1:18080/api/v1/sim/state | python3 -m json.tool
curl -fsS http://127.0.0.1:18001/health
python3 scripts/demo_smoke.py --orchestrator-url http://127.0.0.1:18080
# Then run the Socket.IO polling smoke from section 3 with:
# AETHERVILLE_ORCHESTRATOR_URL=http://127.0.0.1:18080
```

Start the local client against the tunnel:

```bash
NEXT_PUBLIC_ORCHESTRATOR_URL=http://127.0.0.1:18080 \
NEXT_PUBLIC_SOCKET_URL=http://127.0.0.1:18080 \
NEXT_PUBLIC_SOCKET_TRANSPORTS=polling \
pnpm dev
```


Production-style browser smoke after `next build && next start`:

Terminal 1:

```bash
pnpm --filter @aetherville/client build
NEXT_PUBLIC_ORCHESTRATOR_URL=http://127.0.0.1:18080 \
NEXT_PUBLIC_SOCKET_URL=http://127.0.0.1:18080 \
NEXT_PUBLIC_SOCKET_TRANSPORTS=polling \
pnpm --filter @aetherville/client exec next start -H 0.0.0.0 -p 3000
```

Terminal 2:

```bash
python3 scripts/browser_demo_smoke.py \
  --mode live \
  --url http://127.0.0.1:3000/ \
  --expected-endpoint http://127.0.0.1:18080
python3 scripts/browser_demo_smoke.py \
  --mode replay \
  --url http://127.0.0.1:3000/replay
```

The live route is dynamically server-rendered, so `next start` reads the selected tunnel values at process start and passes the runtime orchestrator URL into browser panels.

Open:

- Live city: `http://localhost:3000/`
- Replay fallback: `http://localhost:3000/replay`

## 6. Demo fallback decision tree

- If RunPod SSH/GPU fails: stop live backend attempts and use `/replay`.
- If public endpoints fail: use Mode B SSH tunnel.
- If Socket.IO WebSocket upgrade fails: keep
  `NEXT_PUBLIC_SOCKET_TRANSPORTS=polling`; polling is the verified quiet demo
  transport and avoids misleading browser WebSocket warnings.
- If voice/STT is unavailable: use God Mode text input or macro buttons.
- If real YOLO/RL/LSTM/vLLM is unavailable: use deterministic stubs and explain
  the documented upgrade paths.

## 7. AI learning truthfulness note

- The visible `AI 학습 루프` panel is a persistent deterministic online
  adaptation loop, not live neural-network training.
- Keeping the direct-process server running accumulates event experience in
  JSON state and feeds it back into traffic pressure, taxi policy metadata, and
  UI tags.
- Real vLLM/YOLO/PPO/LSTM/STT training still requires a separate explicit
  opt-in with model names, storage, cost limits, and rollback plan.
