# MacBook Demo Quickstart — Aetherville

이 파일은 **맥북 시연자가 레포를 클론한 뒤 로컬 브라우저에서 H100 RunPod 백엔드에 연결해 바로 데모 화면을 여는 절차**만 압축한 실행 문서다.

## 핵심 원칙

- `.env`, `.env.local`, `infra/runpod/.env.runpod`, SSH 키, 토큰, public tunnel URL은 git에 커밋하지 않는다.
- MacBook에는 시연 직전에 안전한 채널로 endpoint/SSH 값을 전달하고, 로컬 ignored 파일에만 저장한다.
- Docker는 사용하지 않는다. 현재 런타임은 RunPod direct-process다.
- 브라우저는 vLLM에 직접 붙지 않고 orchestrator REST/Socket.IO에 붙는다.
- vision service 검증 포트는 `18001`이다.

## 1. 레포 준비

```bash
git clone https://github.com/tmdry4530/Aetherville.git
cd Aetherville
git checkout master
git pull --ff-only origin master

corepack enable
corepack prepare pnpm@10.28.0 --activate
pnpm install --frozen-lockfile
uv sync
```

빠른 검증:

```bash
python3 -m json.tool project/TASKS.json >/dev/null
bash -n infra/runpod/*.sh scripts/*.sh
pnpm typecheck
pnpm --filter @aetherville/client build
```

## 2. 연결 모드 선택

### Mode A — public RunPod / tunnel URL로 바로 연결

시연 담당자가 public orchestrator URL을 안전한 채널로 받은 경우:

```bash
export AETHERVILLE_DEMO_ORCHESTRATOR_URL='https://REPLACE_WITH_LIVE_ORCHESTRATOR_URL'
bash scripts/write_macbook_demo_env.sh --mode public
```

health 확인:

```bash
curl -fsS "$AETHERVILLE_DEMO_ORCHESTRATOR_URL/api/v1/health" | python3 -m json.tool
curl -fsS "$AETHERVILLE_DEMO_ORCHESTRATOR_URL/api/v1/sim/status" | python3 -m json.tool
curl -fsS "$AETHERVILLE_DEMO_ORCHESTRATOR_URL/api/v1/training/status" | python3 -m json.tool
```

### Mode B — SSH tunnel fallback

public URL이 없으면 MacBook에서 tunnel을 연다. 먼저 로컬 전용 RunPod env를 만든다.

```bash
cp infra/runpod/.env.runpod.example infra/runpod/.env.runpod
chmod 600 infra/runpod/.env.runpod
```

`infra/runpod/.env.runpod`에는 실제 값을 직접 채운다. 이 파일 내용은 출력하지 않는다.

```text
RUNPOD_HOST=<runpod-host>
RUNPOD_SSH_PORT=<runpod-ssh-port>
RUNPOD_USER=<runpod-user>
RUNPOD_SSH_KEY=<private-key-file>
RUNPOD_REMOTE_DIR=/workspace/aetherville
AETHERVILLE_ORCHESTRATOR_PORT=8080
AETHERVILLE_VISION_PORT=18001
AETHERVILLE_VLLM_PORT=8000
```

터널 전용 터미널:

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

다른 터미널에서 클라이언트 env 작성:

```bash
bash scripts/write_macbook_demo_env.sh --mode tunnel
```

health 확인:

```bash
curl -fsS http://127.0.0.1:18080/api/v1/health | python3 -m json.tool
curl -fsS http://127.0.0.1:18080/api/v1/sim/status | python3 -m json.tool
curl -fsS http://127.0.0.1:18080/api/v1/training/status | python3 -m json.tool
curl -fsS http://127.0.0.1:18001/health | python3 -m json.tool
curl -fsS http://127.0.0.1:18000/v1/models | python3 -m json.tool
```

## 3. 로컬 브라우저 실행

Next.js는 기본적으로 localhost에서 열린다. 시연용으로는 아래 중 하나만 실행하면 된다.

```bash
pnpm dev
```

또는 명시적으로 client만 실행:

```bash
pnpm --filter @aetherville/client dev -- -H 127.0.0.1 -p 3000
```

브라우저:

```bash
open http://localhost:3000/
open http://localhost:3000/replay
```

프로덕션 리허설:

```bash
pnpm --filter @aetherville/client build
pnpm --filter @aetherville/client exec next start -H 127.0.0.1 -p 3000
```

## 4. 시연 전 화면 체크

```bash
python3 scripts/browser_demo_smoke.py \
  --mode live \
  --url http://127.0.0.1:3000/ \
  --timeout-seconds 60

python3 scripts/browser_demo_smoke.py \
  --mode replay \
  --url http://127.0.0.1:3000/replay \
  --timeout-seconds 60
```

UI에서 확인할 것:

- connection 상태가 `connected` 또는 polling 연결 성공으로 표시된다.
- endpoint가 Mode A public URL 또는 Mode B `http://127.0.0.1:18080`으로 표시된다.
- God Mode 명령 후 Scenario Director가 단계별 이동/상황을 보여준다.
- Citizen Memory, Vehicle Camera, Traffic Forecast, AI Learning Loop 패널이 갱신된다.
- 연결 장애 시 `/replay`가 발표 fallback으로 열린다.

추천 God Mode 명령:

```text
민수가 하린을 만난 뒤 택시를 불러 민지에게 가고, 드론은 서연에게 이동한 뒤 서연은 민지와 민수를 만나러 간다
```

## 5. 문제 발생 시

### `localhost:3000`이 안 열림

```bash
lsof -iTCP:3000 -sTCP:LISTEN || true
pnpm --filter @aetherville/client dev -- -H 127.0.0.1 -p 3000
```

### 화면이 error/replay 모드로 고정됨

Mode A라면 public URL health를, Mode B라면 tunnel health를 다시 확인한다.

```bash
# Mode B 기준
curl -fsS http://127.0.0.1:18080/api/v1/health
curl -fsS http://127.0.0.1:18080/api/v1/sim/status
```

### 즉시 발표 fallback

```bash
open http://localhost:3000/replay
```
