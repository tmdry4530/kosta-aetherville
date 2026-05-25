# MacBook Demo Setup — Project Aetherville

이 문서는 **새 맥북 또는 다른 macOS 환경에서 레포를 클론한 뒤, 로컬 브라우저로 RunPod Aetherville 데모 화면을 바로 띄우기 위한 에이전트용 절차**입니다.

목표 화면:

```text
MacBook browser: http://127.0.0.1:3000/
        │
        ├─ Next.js client on MacBook :3000
        │
        └─ SSH tunnel on MacBook
             ├─ 127.0.0.1:18080 -> RunPod orchestrator :8080
             ├─ 127.0.0.1:18001 -> RunPod vision :18001
             └─ 127.0.0.1:18000 -> RunPod vLLM :8000
```

중요: 브라우저는 vLLM에 직접 붙지 않습니다. 브라우저는 orchestrator `:8080`에 붙고, orchestrator가 vLLM/vision/simulation/traffic/STT를 호출합니다. 따라서 vLLM만 살아 있으면 부족하며 orchestrator direct-process runtime도 살아 있어야 합니다.

## 절대 규칙

- Docker, Docker Compose, Docker-in-Docker, Docker daemon setup을 실행하지 마세요.
- RunPod 접속 정보는 `infra/runpod/.env.runpod` 또는 환경변수에서만 읽으세요.
- `.env.runpod`, SSH private key, token, Hugging Face token, JWT secret, 실제 host/port/key path를 로그/채팅/커밋에 출력하지 마세요.
- 현재 검증된 vision 포트는 `18001`입니다. canonical `8001`은 이 pod에서 막혀 있을 수 있습니다.
- real vLLM/YOLO/STT/traffic checkpoint 상태는 health/smoke 결과로 확인하기 전까지 발표에서 단정하지 마세요.
- 맥북 세팅 목적이면 기존 RunPod 프로세스를 함부로 stop/restart하지 말고, 먼저 tunnel + health check로 확인하세요.

## 0. macOS 기본 도구 준비

이미 설치되어 있으면 건너뛰어도 됩니다.

```bash
xcode-select --install || true
```

Homebrew가 없다면 설치합니다.

```bash
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
```

Apple Silicon Mac에서 brew shellenv가 필요하면 현재 shell에 반영합니다.

```bash
eval "$(/opt/homebrew/bin/brew shellenv)" 2>/dev/null || true
eval "$(/usr/local/bin/brew shellenv)" 2>/dev/null || true
```

필수 도구:

```bash
brew install git node pnpm python uv
```

버전 확인:

```bash
git --version
node --version
pnpm --version
python3 --version
uv --version
ssh -V
```

## 1. 레포 클론

```bash
git clone https://github.com/tmdry4530/kosta-aetherville.git
cd kosta-aetherville
```

이미 클론되어 있으면 최신 상태로 맞춥니다.

```bash
git pull --ff-only
```

현재 브랜치와 변경 상태 확인:

```bash
git status --short
git log --oneline -5
```

## 2. 의존성 설치

Node 의존성:

```bash
pnpm install
```

Python workspace 의존성:

```bash
uv sync
```

가벼운 로컬 검증:

```bash
python3 -m json.tool TASKS.json >/tmp/aetherville-tasks-check.json
pnpm typecheck
```

시간이 있으면 전체 기본 검증:

```bash
uv run pytest
uv run ruff check server packages scripts
uv run mypy server packages
pnpm lint
pnpm test
pnpm test:e2e
pnpm --filter @aetherville/client build
```

## 3. RunPod SSH 환경 파일 준비

예시 파일을 복사합니다.

```bash
cp infra/runpod/.env.runpod.example infra/runpod/.env.runpod
chmod 600 infra/runpod/.env.runpod
```

`infra/runpod/.env.runpod`를 로컬 편집기로 열고 값을 채웁니다.

```bash
${EDITOR:-vi} infra/runpod/.env.runpod
```

필수 항목:

```bash
RUNPOD_HOST=<provided-by-operator>
RUNPOD_SSH_PORT=<provided-by-operator>
RUNPOD_USER=root
RUNPOD_SSH_KEY=$HOME/.ssh/<private-key-file>
RUNPOD_REMOTE_DIR=/workspace/aetherville
```

권장 옵션:

```bash
RUNPOD_PUBLIC_ORCHESTRATOR_URL=http://YOUR_RUNPOD_HOST:8080
RUNPOD_PUBLIC_SOCKET_URL=http://YOUR_RUNPOD_HOST:8080
RUNPOD_PUBLIC_VISION_URL=http://YOUR_RUNPOD_HOST:18001
RUNPOD_PUBLIC_VLLM_URL=http://YOUR_RUNPOD_HOST:8000/v1
```

주의:

- 위 값은 예시 placeholder입니다. 실제 값은 문서나 채팅에 쓰지 마세요.
- SSH key 파일 권한은 보통 `chmod 600`이어야 합니다.
- key가 passphrase를 요구하면 macOS keychain/ssh-agent에 등록합니다.

```bash
chmod 600 "$HOME/.ssh/<private-key-file>"
ssh-add --apple-use-keychain "$HOME/.ssh/<private-key-file>" 2>/dev/null || ssh-add "$HOME/.ssh/<private-key-file>"
```

## 4. RunPod 접속/상태 확인

환경변수를 로드합니다.

```bash
set -a
source infra/runpod/.env.runpod
set +a
```

SSH read-only 확인:

```bash
ssh -i "$RUNPOD_SSH_KEY" -p "$RUNPOD_SSH_PORT" "$RUNPOD_USER@$RUNPOD_HOST" \
  'hostname && pwd && python --version && nvidia-smi --query-gpu=name,memory.used,memory.total --format=csv,noheader'
```

레포 제공 verifier:

```bash
bash infra/runpod/verify_runpod.sh
```

기대값:

- SSH 연결 가능.
- GPU 이름에 NVIDIA GeForce RTX 4090 표시.
- Docker는 현재 실행 경로에서 필요하지 않음.

## 5. SSH tunnel 열기 — 기본 추천 모드

새 터미널을 하나 열고 레포 루트에서 실행합니다. 이 터미널은 데모 중 계속 켜둡니다.

```bash
cd kosta-aetherville
set -a
source infra/runpod/.env.runpod
set +a

ssh -N \
  -L 18080:127.0.0.1:8080 \
  -L 18001:127.0.0.1:18001 \
  -L 18000:127.0.0.1:8000 \
  -i "$RUNPOD_SSH_KEY" \
  -p "$RUNPOD_SSH_PORT" \
  "$RUNPOD_USER@$RUNPOD_HOST"
```

터널 포트 의미:

| MacBook URL | RunPod target | 용도 |
|---|---|---|
| `http://127.0.0.1:18080` | `127.0.0.1:8080` | orchestrator REST + Socket.IO |
| `http://127.0.0.1:18001` | `127.0.0.1:18001` | vision health/detect |
| `http://127.0.0.1:18000` | `127.0.0.1:8000` | vLLM OpenAI-compatible API |

터널이 끊기면 브라우저 live 화면도 RunPod와 연결이 끊깁니다. 재연결은 같은 명령을 다시 실행하면 됩니다.

## 6. 터널 health 확인

다른 터미널에서:

```bash
curl -fsS http://127.0.0.1:18080/api/v1/health | python3 -m json.tool
curl -fsS http://127.0.0.1:18080/api/v1/sim/status | python3 -m json.tool
curl -fsS http://127.0.0.1:18001/health | python3 -m json.tool
curl -fsS http://127.0.0.1:18000/v1/models | python3 -m json.tool
```

기대값:

- orchestrator health: `status` 또는 service 상태가 `ok`.
- simulation status: tick/running 상태 반환.
- vision health: current pod에서는 `18001`에서 반환.
- vLLM models: real 또는 fallback OpenAI-compatible model list 반환.

만약 `18080` health가 실패하면 vLLM만 살아 있는 상태일 수 있습니다. 이 경우 MacBook 브라우저 데모는 정상 동작하지 않습니다. RunPod operator가 direct-process orchestrator를 다시 시작해야 합니다. 자세한 명령은 `docs/live-demo-runbook.md`를 따르세요.

## 7. MacBook 로컬 브라우저 클라이언트 실행

개발 서버 권장:

```bash
NEXT_PUBLIC_ORCHESTRATOR_URL=http://127.0.0.1:18080 \
NEXT_PUBLIC_SOCKET_URL=http://127.0.0.1:18080 \
NEXT_PUBLIC_SOCKET_TRANSPORTS=polling \
pnpm dev
```

브라우저:

```text
http://127.0.0.1:3000/
```

fallback route:

```text
http://127.0.0.1:3000/replay
```

화면에서 확인할 것:

- 연결 상태가 `connected` 또는 polling transport로 표시.
- REST/SOCKET endpoint가 `http://127.0.0.1:18080`으로 표시.
- `RunPod AI proof` / `4090 실행 증거` 패널이 보임.
- `Scene Director` / live impact board가 보임.
- Vehicle cam panel이 real YOLO 또는 fallback 상태를 명확히 표시.
- God Mode 명령 실행 후 rain/taxi/traffic/meeting 효과가 화면에 반영.

## 8. Production-style client 실행이 필요한 경우

`next start`를 쓰는 경우에도 같은 env를 build와 start에 모두 넣습니다.

```bash
NEXT_PUBLIC_ORCHESTRATOR_URL=http://127.0.0.1:18080 \
NEXT_PUBLIC_SOCKET_URL=http://127.0.0.1:18080 \
NEXT_PUBLIC_SOCKET_TRANSPORTS=polling \
pnpm --filter @aetherville/client build

NEXT_PUBLIC_ORCHESTRATOR_URL=http://127.0.0.1:18080 \
NEXT_PUBLIC_SOCKET_URL=http://127.0.0.1:18080 \
NEXT_PUBLIC_SOCKET_TRANSPORTS=polling \
pnpm --filter @aetherville/client exec next start -H 0.0.0.0 -p 3000
```

확인:

```bash
curl -fsS http://127.0.0.1:3000/ >/tmp/aetherville-home.html
curl -fsS http://127.0.0.1:3000/replay >/tmp/aetherville-replay.html
```

## 9. 발표 전 smoke test

로컬 브라우저 서버가 켜져 있고 tunnel이 살아 있을 때:

```bash
python3 scripts/browser_demo_smoke.py \
  --mode live \
  --url http://127.0.0.1:3000/ \
  --expected-endpoint http://127.0.0.1:18080

python3 scripts/browser_demo_smoke.py \
  --mode replay \
  --url http://127.0.0.1:3000/replay
```

전체 리허설:

```bash
python3 scripts/demo_rehearsal.py \
  --orchestrator-url http://127.0.0.1:18080 \
  --client-url http://127.0.0.1:3000 \
  --expected-client-endpoint http://127.0.0.1:18080
```

God Mode before/after proof:

```bash
python3 scripts/browser_impact_smoke.py \
  --orchestrator-url http://127.0.0.1:18080 \
  --client-url http://127.0.0.1:3000
```

## 10. 발표용 God Mode 명령

```text
도시에 비를 내리고 민지가 택시를 부르게 하고 출근길을 혼잡하게 만들고 민수와 만나게 해줘
```

정상 기대 효과:

- 비가 보임.
- 택시/차량 상태가 바뀜.
- 교통 혼잡/queue 지표가 증가.
- 민지/민수 만남 또는 대화 상태가 보임.
- God Mode result에 `vLLM` 또는 fallback rules 상태와 action list가 표시.
- Scene Director / RunPod AI proof 패널에서 현재 상태가 설명됨.

## 11. Public endpoint 모드가 있는 경우

운영자가 public RunPod REST/WSS URL을 제공한 경우 SSH tunnel 없이 실행할 수 있습니다. 이 값도 tracked file에 쓰지 말고 로컬 env로만 주입하세요.

```bash
NEXT_PUBLIC_ORCHESTRATOR_URL="$RUNPOD_PUBLIC_ORCHESTRATOR_URL" \
NEXT_PUBLIC_SOCKET_URL="$RUNPOD_PUBLIC_SOCKET_URL" \
NEXT_PUBLIC_SOCKET_TRANSPORTS=polling \
pnpm dev
```

주의:

- public URL에 CORS/port mapping/TLS가 실제로 구성되어 있어야 합니다.
- current verified fallback은 SSH tunnel mode입니다.
- public WSS를 쓰려면 Socket.IO transport와 proxy가 별도로 검증되어야 합니다. 데모 안정성은 polling이 우선입니다.

## 12. 문제 해결

### 화면은 뜨는데 `connected`가 안 됨

```bash
curl -fsS http://127.0.0.1:18080/api/v1/health | python3 -m json.tool
```

실패하면 SSH tunnel이 꺼졌거나 RunPod orchestrator가 죽은 것입니다.

### endpoint가 `localhost:8080` 또는 다른 주소로 보임

클라이언트를 올바른 env로 다시 실행하세요.

```bash
NEXT_PUBLIC_ORCHESTRATOR_URL=http://127.0.0.1:18080 \
NEXT_PUBLIC_SOCKET_URL=http://127.0.0.1:18080 \
NEXT_PUBLIC_SOCKET_TRANSPORTS=polling \
pnpm dev
```

### Vision panel이 안 맞음

현재 pod의 vision 포트는 `18001`입니다.

```bash
curl -fsS http://127.0.0.1:18001/health | python3 -m json.tool
```

### vLLM만 health가 되고 화면은 안 됨

정상 데모에는 orchestrator가 필요합니다.

```bash
curl -fsS http://127.0.0.1:18080/api/v1/health | python3 -m json.tool
```

orchestrator가 죽어 있으면 `docs/live-demo-runbook.md`의 direct-process 재시작 절차를 따르세요.

### `pnpm` 또는 `uv`가 없음

```bash
brew install pnpm uv
```

또는 Node corepack을 사용할 수 있습니다.

```bash
corepack enable
corepack prepare pnpm@10.28.0 --activate
```

### macOS가 SSH key 권한을 거부함

```bash
chmod 700 ~/.ssh
chmod 600 "$RUNPOD_SSH_KEY"
```

## 13. 성공 기준 체크리스트

- [ ] `git clone` 또는 `git pull --ff-only` 완료.
- [ ] `pnpm install` 완료.
- [ ] `uv sync` 완료.
- [ ] `infra/runpod/.env.runpod` 로컬 작성 완료, 커밋 안 됨.
- [ ] SSH read-only check에서 RTX 4090 확인.
- [ ] SSH tunnel 터미널이 살아 있음.
- [ ] `curl http://127.0.0.1:18080/api/v1/health` 통과.
- [ ] `curl http://127.0.0.1:18001/health` 통과.
- [ ] `pnpm dev` 또는 `next start`가 `:3000`에서 실행 중.
- [ ] `http://127.0.0.1:3000/`에서 endpoint가 `http://127.0.0.1:18080`으로 표시.
- [ ] `/replay` fallback 화면이 열림.
- [ ] `scripts/browser_demo_smoke.py` live/replay 통과.
- [ ] 발표 전 `scripts/demo_rehearsal.py` 통과.
