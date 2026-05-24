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
- Vision deterministic stub: `18001`
- Redis: memory fallback

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


> Production build note: `NEXT_PUBLIC_*` values are baked into the Next.js
> bundle at build time. For demo safety, prefer `pnpm dev` as shown above. If
> using `next build && next start`, run the build command with the same
> `NEXT_PUBLIC_ORCHESTRATOR_URL`, `NEXT_PUBLIC_SOCKET_URL`, and
> `NEXT_PUBLIC_SOCKET_TRANSPORTS` values selected for Mode A.

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


> Production build note: `NEXT_PUBLIC_*` values are baked into the Next.js
> bundle at build time. For demo safety, prefer `pnpm dev` as shown above. If
> using `next build && next start`, run the build command with the same tunnel
> endpoint values shown here.

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
