# MacBook Agent Setup — Project Aetherville

이 파일은 MacBook에 있는 코딩 에이전트가 **레포 클론 직후 로컬 브라우저에서 Aetherville 화면을 띄우고 RunPod direct-process 백엔드에 연결**하기 위한 실행 지침이다.

## 0. 절대 규칙

- Docker / Docker Compose를 실행하지 않는다. 현재 지원 런타임은 **RunPod direct-process**다.
- `.env`, `.env.*`, `infra/runpod/.env.runpod`, SSH private key, 토큰, 실제 호스트/포트/키 경로를 로그·커밋·채팅에 출력하지 않는다.
- 브라우저 클라이언트는 vLLM에 직접 붙지 않는다. 항상 orchestrator REST/Socket.IO endpoint에 붙는다.
- 현재 vision service의 검증 포트는 `18001`이다.
- public RunPod endpoint가 없으면 SSH tunnel 모드로 접속한다.
- self-learning 문구는 정확히 말한다: 현재 기본 데모는 reward-gated policy adaptation이며, 모델 weight fine-tuning은 별도 trainer/checkpoint pipeline이 필요하다.

## 1. MacBook 사전 설치

```bash
xcode-select --install || true

# Homebrew가 없으면 먼저 설치한다.
command -v brew >/dev/null 2>&1 || \
  /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

brew install git node@22 pnpm python@3.12 uv
corepack enable
corepack prepare pnpm@10.28.0 --activate
```

설치 확인:

```bash
git --version
node --version
pnpm --version
python3 --version
uv --version
```

## 2. 레포 클론 및 의존성 설치

```bash
git clone https://github.com/tmdry4530/Aetherville.git
cd Aetherville

git checkout master
git pull --ff-only origin master

pnpm install --frozen-lockfile
uv sync
```

빠른 로컬 검증:

```bash
python3 -m json.tool project/TASKS.json >/dev/null
bash -n infra/runpod/*.sh
pnpm typecheck
pnpm --filter @aetherville/client build
```

## 3. 연결 모드 선택

### Mode A — public RunPod endpoint 사용

RunPod가 public URL을 이미 제공한다면 MacBook에는 클라이언트 env만 만든다.

```bash
cat > client/.env.local <<'EOF_ENV'
NEXT_PUBLIC_ORCHESTRATOR_URL=https://YOUR_PUBLIC_ORCHESTRATOR_URL
NEXT_PUBLIC_SOCKET_URL=https://YOUR_PUBLIC_ORCHESTRATOR_URL
NEXT_PUBLIC_SOCKET_TRANSPORTS=polling
EOF_ENV
```

확인:

```bash
curl -fsS "$NEXT_PUBLIC_ORCHESTRATOR_URL/api/v1/health" || true
```

주의: 위 명령은 현재 shell에 변수를 export한 경우에만 동작한다. `.env.local` 내용을 출력하지 않는다.

### Mode B — SSH tunnel 사용, 권장 fallback

public endpoint가 없거나 불안정하면 SSH tunnel을 연다. 먼저 로컬 전용 RunPod env 파일을 만든다.

```bash
cp infra/runpod/.env.runpod.example infra/runpod/.env.runpod
chmod 600 infra/runpod/.env.runpod
```

`infra/runpod/.env.runpod`에 다음 값을 채운다. 실제 값은 출력하지 않는다.

```bash
RUNPOD_HOST=<runpod-host>
RUNPOD_SSH_PORT=<runpod-ssh-port>
RUNPOD_USER=root
RUNPOD_SSH_KEY=<private-key-file>
RUNPOD_REMOTE_DIR=/workspace/aetherville

AETHERVILLE_ORCHESTRATOR_PORT=8080
AETHERVILLE_VISION_PORT=18001
AETHERVILLE_VLLM_PORT=8000
AETHERVILLE_REDIS_MODE=memory
```

SSH/GPU read-only 검증:

```bash
set -a
source infra/runpod/.env.runpod
set +a

ssh -i "$RUNPOD_SSH_KEY" \
  -p "$RUNPOD_SSH_PORT" \
  -o BatchMode=yes \
  -o ConnectTimeout=15 \
  -o IdentitiesOnly=yes \
  "$RUNPOD_USER@$RUNPOD_HOST" \
  'hostname; nvidia-smi --query-gpu=name,memory.total --format=csv,noheader; pwd; python --version'
```

Tunnel 터미널을 하나 열어 계속 유지한다.

```bash
set -a
source infra/runpod/.env.runpod
set +a

ssh -N \
  -L 18080:127.0.0.1:${AETHERVILLE_ORCHESTRATOR_PORT:-8080} \
  -L 18001:127.0.0.1:${AETHERVILLE_VISION_PORT:-18001} \
  -L 18000:127.0.0.1:${AETHERVILLE_VLLM_PORT:-8000} \
  -p "$RUNPOD_SSH_PORT" \
  -i "$RUNPOD_SSH_KEY" \
  -o IdentitiesOnly=yes \
  "$RUNPOD_USER@$RUNPOD_HOST"
```

다른 터미널에서 MacBook 클라이언트 env를 tunnel에 맞춘다.

```bash
cat > client/.env.local <<'EOF_ENV'
NEXT_PUBLIC_ORCHESTRATOR_URL=http://127.0.0.1:18080
NEXT_PUBLIC_SOCKET_URL=http://127.0.0.1:18080
NEXT_PUBLIC_SOCKET_TRANSPORTS=polling
EOF_ENV
```

Tunnel health 확인:

```bash
curl -fsS http://127.0.0.1:18080/api/v1/health
curl -fsS http://127.0.0.1:18080/api/v1/sim/status
curl -fsS http://127.0.0.1:18001/health
curl -fsS http://127.0.0.1:18000/v1/models
```

## 4. RunPod 서비스 시작 또는 재시작

이미 RunPod에서 orchestrator/vision/vLLM이 실행 중이고 health가 통과하면 이 섹션은 건너뛴다.

### 안전 smoke runtime, 모델 다운로드 없음

```bash
bash infra/runpod/deploy_over_ssh.sh --dry-run --mode direct
bash infra/runpod/deploy_over_ssh.sh --mode direct
```

이 경로는 기본적으로 mock/cache/fallback 중심이며, 모델 다운로드를 요구하지 않는다.

### 새 5090/H100 pod에서 real-demo를 명시 승인하고 시작

GPU 비용과 모델 다운로드를 승인한 경우에만 실행한다.

```bash
bash infra/runpod/deploy_5090_direct.sh --profile safe-smoke --dry-run
bash infra/runpod/deploy_5090_direct.sh --profile safe-smoke

AETHERVILLE_APPROVE_REAL_AI=1 \
AETHERVILLE_STT_MODE=stub \
bash infra/runpod/deploy_5090_direct.sh --profile real-demo
```

remote process health는 deploy script가 실행한다. 수동 확인이 필요하면 tunnel 또는 remote shell에서 다음을 사용한다.

```bash
bash infra/runpod/health_check_direct.sh
```

## 5. 로컬 브라우저 클라이언트 실행

개발 모드:

```bash
pnpm --filter @aetherville/client dev -- -H 0.0.0.0 -p 3000
```

브라우저:

```bash
open http://127.0.0.1:3000/
open http://127.0.0.1:3000/replay
```

프로덕션 모드로 리허설:

```bash
pnpm --filter @aetherville/client build
pnpm --filter @aetherville/client exec next start -H 0.0.0.0 -p 3000
```

## 6. 화면 dogfood smoke

MacBook에서 브라우저가 열리는지, live/replay fallback이 동작하는지 확인한다.

```bash
python3 scripts/browser_demo_smoke.py \
  --mode live \
  --url http://127.0.0.1:3000/ \
  --expected-endpoint http://127.0.0.1:18080 \
  --timeout-seconds 60

python3 scripts/browser_demo_smoke.py \
  --mode replay \
  --url http://127.0.0.1:3000/replay \
  --timeout-seconds 60
```

가능하면 live interaction smoke도 실행한다.

```bash
python3 scripts/browser_impact_smoke.py \
  --client-url http://127.0.0.1:3000/ \
  --orchestrator-url http://127.0.0.1:18080 \
  --wait-seconds 8 \
  --timeout-seconds 120
```

## 7. 데모 중 확인해야 할 UI 상태

Live 화면에서 다음을 확인한다.

- 좌측/상단 hero 영역에 endpoint가 `http://127.0.0.1:18080` 또는 public orchestrator URL로 표시된다.
- connection 상태가 `connected` 또는 polling 연결 성공으로 표시된다.
- `Scenario Director`가 God Mode 명령을 단계별로 보여준다.
- `Citizen Memory`에 시민 이벤트/기억이 갱신된다.
- `Vehicle Camera`에 detection badge가 표시된다.
- `Traffic Forecast`가 혼잡/예측 값을 표시한다.
- `AI Learning Loop`는 reward/policy adaptation 증거를 보여준다.
- `/replay`는 RunPod 연결 없이도 발표 fallback 화면으로 열린다.

God Mode 추천 smoke 명령:

```text
택시 없음 상황에서 민수가 택시를 불러 민지에게 간다
```

```text
도시에 비를 내리고 민지가 택시를 부르게 하고 출근길을 혼잡하게 만들어줘
```

```text
민수가 하린을 만난 뒤 택시를 불러 민지에게 가고, 드론은 서연에게 이동한 뒤 서연은 민지와 민수를 만나러 간다
```

## 8. 문제 해결

### `http://127.0.0.1:3000` 연결 불가

```bash
lsof -iTCP:3000 -sTCP:LISTEN || true
pnpm --filter @aetherville/client dev -- -H 0.0.0.0 -p 3000
```

### UI가 `current mode: error` 또는 연결 실패 표시

1. Tunnel 터미널이 살아 있는지 확인한다.
2. Orchestrator health를 확인한다.

```bash
curl -fsS http://127.0.0.1:18080/api/v1/health
curl -fsS http://127.0.0.1:18080/api/v1/sim/status
```

3. 실패하면 RunPod direct-process health를 확인한다.

```bash
set -a
source infra/runpod/.env.runpod
set +a

ssh -i "$RUNPOD_SSH_KEY" -p "$RUNPOD_SSH_PORT" -o IdentitiesOnly=yes "$RUNPOD_USER@$RUNPOD_HOST" \
  'cd /workspace/aetherville && bash infra/runpod/health_check_direct.sh'
```

### Vision health 실패

현재 검증 포트는 `18001`이다. canonical `8001`을 가정하지 않는다.

```bash
curl -fsS http://127.0.0.1:18001/health
```

### vLLM 모델 응답 실패

```bash
curl -fsS http://127.0.0.1:18000/v1/models
```

- mock/fallback이면 `aetherville-mock-llm` 계열이 보여도 정상이다.
- real-demo에서 실패하면 GPU 메모리, 모델명, model cache, vLLM 로그를 확인한다.
- live model weight training은 현재 자동으로 수행되지 않는다.

### 즉시 fallback 발표

```bash
open http://127.0.0.1:3000/replay
```

## 9. 완료 기준

MacBook 세팅 완료로 간주하려면 다음이 모두 통과해야 한다.

```bash
python3 -m json.tool project/TASKS.json >/dev/null
bash -n infra/runpod/*.sh
pnpm typecheck
pnpm --filter @aetherville/client build
curl -fsS http://127.0.0.1:18080/api/v1/health
curl -fsS http://127.0.0.1:18080/api/v1/sim/status
curl -fsS http://127.0.0.1:18001/health
curl -fsS http://127.0.0.1:18000/v1/models
```

그리고 브라우저에서 다음 URL이 열려야 한다.

```text
http://127.0.0.1:3000/
http://127.0.0.1:3000/replay
```
