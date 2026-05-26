# Project Aetherville

> RunPod H100 direct-process 기반 AI 도시 시뮬레이터

Project Aetherville는 브라우저에서 보이는 3D 도시와 RunPod GPU 서버의 AI 백엔드를 연결한 데모 프로젝트입니다. 사용자는 God Mode 명령으로 날씨, 교통, 택시, 시민 관계를 바꾸고, 화면은 그 변화가 도시 상태·시민 기억·차량 카메라·교통 AI 패널에 동시에 반영되는 모습을 보여줍니다.

이 프로젝트는 단순히 “AI API를 호출했다”가 아니라, **AI가 도시 시스템 안에서 어떤 역할을 맡고, 그 결과가 사용자가 보는 화면에 어떻게 드러나는지**를 보여주는 데 초점을 둡니다.

## 현재 데모 런타임 상태

- 현재 검증된 라이브 데모는 새 RunPod H100 pod의 direct-process runtime에서 동작합니다.
- vLLM은 `Qwen/Qwen2.5-14B-Instruct-AWQ`, vision은 Ultralytics YOLO `yolo11n.pt`, orchestrator는 FastAPI/Socket.IO입니다.
- Docker는 현재 실행 경로가 아니며, RunPod HTTP Service/터널 설정이 없으면 임시 public orchestrator tunnel을 사용합니다.
- “자가학습”은 두 단계입니다. 기본 실행 중에는 reward-gated policy adaptation이 계속 동작하고, H100 승인 모드에서는 별도 trainer가 checkpoint를 만들고 eval gate를 통과한 것만 promotion/reload합니다.
- 현재 검증된 training/reload 범위: vLLM LoRA/SFT dataset+adapter manifest 등록, YOLO pseudo-label self-training artifact hot-swap, traffic PPO-style rollout policy hot-swap, traffic LSTM CUDA checkpoint hot-swap입니다. vLLM base model weight를 live inference 서버 안에서 직접 fine-tuning했다고 주장하지 않습니다.

## 기술 스택

| 영역 | 사용 기술 | 이 프로젝트에서의 역할 |
|---|---|---|
| Frontend | Next.js App Router, React, TypeScript | 발표자가 보는 live city/replay 화면, 패널 UI, God Mode 입력 화면 구성 |
| 3D Rendering | React Three Fiber, Three.js | 도시, 도로, 시민, 차량, 날씨, 카메라 뷰를 브라우저에서 렌더링 |
| Client State | Zustand | 연결 상태, 수신한 world state, UI 상태를 브라우저에서 관리 |
| Realtime | Socket.IO client/server | RunPod orchestrator의 tick/state update를 브라우저로 전달. 데모 안정성을 위해 polling 우선 |
| Backend API | FastAPI, Uvicorn, python-socketio, asyncio | REST API, Socket.IO, simulation loop, God Mode command, vehicle camera endpoint 제공 |
| Schema Contract | Pydantic, generated TypeScript | 서버와 클라이언트가 같은 world state, command, event, health 계약을 사용하도록 유지 |
| LLM Runtime | vLLM OpenAI-compatible API | 시민 reflection, God Mode 자연어 명령 해석, City AI 자율 계획 경로. 실패 시 deterministic fallback 유지 |
| Vision | Ultralytics YOLO, FastAPI vision service | 차량 카메라 화면의 detection 생성. real YOLO/fallback 상태를 UI에서 구분 |
| Traffic AI | CUDA-trained policy checkpoint, LSTM forecast checkpoint | 교통 신호 정책, 혼잡도 변화, forecast 패널 표시 |
| Voice/STT | MediaRecorder, faster-whisper opt-in | 브라우저 음성 입력과 서버 측 음성 명령 처리. 실패 시 typed fallback 사용 |
| Persistence | JSON-backed learning store, Experience Log JSONL, checkpoint registry | demo adaptation 상태, trainer-ready 경험 로그, promotion/rollback 상태 유지 |
| Model Training Pipeline | LoRA/SFT dataset builder, YOLO pseudo-label self-training, traffic PPO-style rollout, CUDA LSTM trainer | H100에서 승인된 trainer cycle → eval gate → checkpoint promotion → runtime reload |
| Runtime | RunPod H100/direct processes | vLLM, vision, orchestrator, simulation, STT/traffic AI를 Docker 없이 실행 |
| Tooling | pnpm, uv, pytest, ruff, mypy, browser smoke scripts | 설치, 타입검사, 테스트, 데모 리허설, visual/impact smoke 검증 |

## 아키텍처

Aetherville는 **로컬 브라우저 UI**와 **RunPod GPU 백엔드**를 분리합니다. 브라우저는 화면과 인터랙션을 담당하고, RunPod는 AI 추론과 시뮬레이션 상태를 담당합니다.

```text
┌──────────────────────────────────────────────────────────────┐
│                       MacBook / Local PC                      │
├──────────────────────────────────────────────────────────────┤
│ Next.js Client :3000                                          │
│                                                              │
│  ┌──────────────────┐   ┌─────────────────────────────────┐  │
│  │ 3D City Scene     │   │ Side Panels                     │  │
│  │ - roads/buildings │   │ - Citizen Memory                │  │
│  │ - citizens/cars   │   │ - Vehicle Camera                │  │
│  │ - rain/traffic    │   │ - Traffic Forecast              │  │
│  │ - Scene Director  │   │ - RunPod AI Proof               │  │
│  └──────────────────┘   │ - God Mode Console              │  │
│                         └─────────────────────────────────┘  │
│                                                              │
│  REST fetch + Socket.IO polling                              │
└──────────────────────────────┬───────────────────────────────┘
                               │
                               │ Mode A: public endpoint
                               │ Mode B: SSH tunnel
                               ▼
┌──────────────────────────────────────────────────────────────┐
│                    RunPod H100 Backend                    │
├──────────────────────────────────────────────────────────────┤
│ Orchestrator :8080                                            │
│ - FastAPI REST API                                            │
│ - Socket.IO state broadcast                                   │
│ - simulation tick loop                                        │
│ - God Mode dispatcher                                         │
│ - City AI bounded planner/executor                            │
│ - vehicle camera endpoint                                     │
│ - learning status endpoint                                    │
├──────────────────────────────────────────────────────────────┤
│ AI / Simulation Services                                      │
│ - vLLM :8000                LLM/God Mode/citizen reflection   │
│                              City AI planning                 │
│ - Vision :18001             YOLO detect/fallback detect       │
│ - Traffic policy checkpoint  signal control evidence          │
│ - LSTM forecast checkpoint   traffic forecast evidence        │
│ - faster-whisper opt-in      voice command transcription      │
│ - Redis or memory fallback   lightweight runtime state        │
└──────────────────────────────────────────────────────────────┘
```

### 데이터 흐름

```text
사용자 God Mode 입력
  → Browser God Mode panel
  → POST /api/v1/god/command 또는 /api/v1/god/voice
  → Orchestrator command dispatcher
  → vLLM 해석 또는 deterministic fallback
  → safe action list 생성
  → simulation world state 변경
  → REST state / Socket.IO state_update
  → 3D city, Scene Director, panels 갱신
```

자율 City AI 흐름:

```text
Simulation interval/event window
  → Orchestrator builds CityWorldContext
  → vLLM returns bounded CityAiPlan JSON
  → Simulation validates allowed actions only
  → citizens/taxi/weather/traffic/memory mutate through Python executors
  → WorldStatePayload.city_ai + city_ai_plan timeline event
  → 3D city camera, actor labels, Scene Director cards update
```

차량 vision 흐름:

```text
Browser Vehicle Camera panel
  → GET /api/v1/vehicles/{vehicle_id}/camera
  → Orchestrator camera endpoint
  → Vision service /detect
  → real YOLO 또는 fallback detection
  → Vehicle panel에 detection badge와 결과 표시
```

교통 AI 흐름:

```text
Simulation tick
  → traffic state 계산
  → traffic policy checkpoint 또는 fallback controller
  → signal phase / congestion / forecast update
  → Traffic panel과 Scene Director에 표시
```

### 주요 포트

| 포트 | 위치 | 용도 | 비고 |
|---:|---|---|---|
| `3000` | MacBook/local | Next.js browser client | 발표자가 여는 화면 |
| `8080` | RunPod | Orchestrator REST + Socket.IO | SSH tunnel에서는 local `18080`으로 연결 |
| `8000` | RunPod | vLLM OpenAI-compatible API | SSH tunnel에서는 local `18000`으로 연결 |
| `18001` | RunPod | Vision service | 현재 검증된 vision 포트 |
| `6379` | RunPod | Redis | 없으면 memory fallback 사용 |

### 학습/진화 원칙

- 기본 live tick loop는 안전한 JSON reward-gated adaptation을 즉시 반영합니다.
- 모든 학습 이벤트는 Experience Log JSONL로도 저장되어 `vLLM LoRA`, `YOLO pseudo-label`, `traffic PPO`, `traffic LSTM` dataset builder의 입력이 됩니다.
- 실제 model weight training은 `AETHERVILLE_APPROVE_MODEL_TRAINING=1`을 설정한 별도 training cycle에서만 실행됩니다.
- checkpoint는 Evaluation Gate를 통과해야 registry에서 promoted가 되고, 실패하면 rejected 상태로 남습니다.
- 데모 중에는 “weights가 바뀌었다”고 말하려면 non-dry-run trainer, promoted checkpoint, runtime reload/restart 증거가 있어야 합니다.

### 런타임 원칙

- 현재 RunPod 실행 경로는 Docker가 아니라 direct-process입니다.
- `infra/runpod/*.sh`가 uvicorn/vLLM/vision process를 시작·중지·검사합니다.
- 브라우저는 vLLM에 직접 붙지 않고 orchestrator에 붙습니다.
- City AI는 `AETHERVILLE_CITY_AI_MODE=vllm`일 때만 vLLM에 계획을 요청하고, 매 tick이 아니라 interval/event 단위로만 실행됩니다.
- vLLM만 살아 있어서는 데모가 완성되지 않습니다. orchestrator/simulation/vision 상태도 필요합니다.
- public endpoint가 없으면 MacBook에서 SSH tunnel을 열고 `127.0.0.1:18080`으로 접속합니다.

## 이 프로젝트에서 보여주고 싶은 것

### 1. 살아 움직이는 도시

도시는 정적인 배경이 아니라 서버에서 계속 tick이 흐르는 시뮬레이션입니다.

- 시민이 이동하고 기억을 남김
- 차량이 도로 위를 움직임
- 신호등과 교통 흐름이 변함
- 날씨와 이벤트가 도시 분위기를 바꿈
- 현재 상태가 여러 UI 패널에 동시에 표시됨
- 복합 상황 명령은 `Scenario Director`가 단계별로 실행함

목표는 보는 사람이 “그냥 10초짜리 반복 영상 아닌가?”라고 느끼지 않도록, 명령과 상태 변화가 명확하게 이어지는 도시를 만드는 것입니다.

### 2. God Mode로 도시 상황을 직접 바꾸는 경험

발표자는 자연어로 도시 상황을 지시할 수 있습니다.

```text
도시에 비를 내리고 민지가 택시를 부르게 하고 출근길을 혼잡하게 만들고 민수와 만나게 해줘
```

이 명령은 하나의 이벤트로 끝나지 않고 여러 변화로 나뉘어 적용됩니다.

- 비가 내림
- 택시 호출 상태가 생김
- 교통 혼잡이 증가함
- 시민 만남/대화 상태가 생김
- 화면의 Scene Director와 각 패널이 변화를 설명함

복합 스토리도 한 번에 지시할 수 있습니다.

```text
민수가 하린을 만난 뒤 택시를 불러 민지에게 가고,
드론은 서연에게 이동한 뒤 서연은 민지와 민수를 만나러 간다
```

이 경우 `Scenario Director`가 시민 이동 → 만남 → 택시 이동 → 드론 이동 → 합류 이동을 단계별로 표시하고, 3D 카메라는 현재 실행 중인 대상에 포커스를 둡니다.

즉, 이 프로젝트의 핵심 데모는 **사람의 자연어 지시가 도시 전체의 상황 변화로 번역되는 장면**입니다.

### 3. AI가 어디에 쓰였는지 화면에서 보이는 것

AI 기능이 내부에 숨어 있으면 데모에서 설득력이 약합니다. 그래서 Aetherville는 AI 사용 지점을 화면에 노출합니다.

- **RunPod AI proof panel**: 현재 연결된 AI 서비스와 GPU 기반 기능 표시
- **Scenario Director panel**: 복합 상황을 단계별 실행 타임라인으로 표시
- **Citizen memory panel**: 시민이 본 것과 반응 기록
- **Vehicle camera panel**: 차량 시점의 vision detection 표시
- **Traffic panel**: 교통 정책과 forecast 결과 표시
- **God Mode panel**: 명령 해석 결과와 적용된 action 표시

목표는 “이 버튼을 누르면 뭔가 변한다”가 아니라, **어떤 AI가 어떤 판단을 했고 그 결과가 어디에 반영됐는지**를 발표자가 설명할 수 있게 만드는 것입니다.

### 4. GPU 서버와 브라우저의 역할 분리

브라우저는 3D 렌더링과 인터랙션에 집중하고, 무거운 AI와 시뮬레이션은 RunPod H100 direct-process 서버가 담당합니다.

- 브라우저: 도시 화면, 패널, God Mode 입력
- RunPod: 시뮬레이션, LLM, vision, traffic AI, STT
- 연결: REST + Socket.IO

이 구조 덕분에 로컬 노트북은 발표 화면을 담당하고, GPU가 필요한 작업은 클라우드 서버에서 처리합니다.

### 5. 실패해도 발표가 끊기지 않는 fallback

라이브 AI 데모는 네트워크, GPU, 마이크 권한, 모델 로딩 같은 변수에 취약합니다. 그래서 Aetherville는 fallback을 명시적으로 준비했습니다.

- RunPod 연결이 불안하면 `/replay`로 전환
- real AI가 실패하면 deterministic fallback 표시
- 음성 STT가 실패하면 typed fallback 사용
- UI는 real/fallback/offline 상태를 구분해서 보여줌

이 프로젝트는 “무조건 성공한 척”하는 데모가 아니라, **현재 어떤 경로가 real이고 어떤 경로가 fallback인지 솔직하게 보여주는 데모**를 목표로 합니다.

## 주요 화면 구성

### Live City

3D 도시가 보이는 메인 화면입니다. 시민, 차량, 도로, 건물, 신호등, 날씨 효과가 함께 표시됩니다.

### Scene Director

현재 도시에서 중요한 변화가 무엇인지 요약합니다.

- rain
- taxi
- traffic
- meeting
- GPU policy
- forecast

### Citizen Memory

시민이 관찰한 사건과 반응을 보여줍니다. 도시가 단순 배경이 아니라 시민 상태를 가진 공간이라는 점을 보여주는 패널입니다.

### Vehicle Camera

차량 시점과 vision detection 결과를 보여줍니다. real YOLO 경로가 활성화되어 있으면 RunPod GPU 기반 vision임을 표시합니다.

### Traffic Forecast

교통량과 예측 결과를 보여줍니다. GPU에서 학습한 traffic policy/LSTM forecast가 연결되어 있을 때 그 근거를 표시합니다.

### God Mode

발표자가 도시 상황을 직접 바꾸는 명령 콘솔입니다. 텍스트 명령, 빠른 버튼, 음성 입력 fallback을 제공합니다.

### Replay Fallback

라이브 서버가 불안정할 때도 발표 흐름을 유지하기 위한 deterministic fallback 화면입니다.

## 현재 구현된 데모 포인트

- 브라우저 3D 도시 렌더링
- RunPod direct-process backend 연결
- Socket.IO 기반 상태 업데이트
- 시민 memory stream
- 차량 camera panel
- real/fallback vision detection 구분
- traffic AI / forecast 표시
- God Mode natural-language command
- multi-action city effect
- Scenario Director complex story timeline
- voice/STT endpoint와 typed fallback
- RunPod AI proof panel
- replay fallback
- browser smoke / visual smoke / impact smoke scripts

## 실행 방법

### 1. 설치

```bash
pnpm install
uv sync
```

### 2. 로컬 화면 실행

```bash
pnpm --filter @aetherville/client exec next dev -H 0.0.0.0 -p 3000
```

브라우저:

```text
http://127.0.0.1:3000/
```

Replay fallback:

```text
http://127.0.0.1:3000/replay
```

### 3. RunPod tunnel로 라이브 백엔드 연결

RunPod 접속 정보는 `infra/runpod/.env.runpod`에만 작성합니다. 실제 host, port, key path, token은 README나 로그에 남기지 않습니다.

```bash
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

다른 터미널에서 클라이언트 실행:

```bash
NEXT_PUBLIC_ORCHESTRATOR_URL=http://127.0.0.1:18080 \
NEXT_PUBLIC_SOCKET_URL=http://127.0.0.1:18080 \
NEXT_PUBLIC_SOCKET_TRANSPORTS=polling \
pnpm --filter @aetherville/client exec next dev -H 0.0.0.0 -p 3000
```

2026-05-26 기준 원격 데모는 이 tunnel 모드로 검증되어 있으며, `/`는
`REST http://127.0.0.1:18080`을 렌더링하고 `Scenario Director` 패널이 RunPod
orchestrator의 복합 상황 실행 상태를 표시합니다. WSL/Next dev는 cold start가
느릴 수 있으므로 발표 전에 `/`와 `/replay`를 한 번씩 열어 warmup합니다.

맥북 발표 세팅은 이 README의 “SSH tunnel 방식”과 “브라우저 확인” 절을 따르면 됩니다. 세부 운영 runbook은 로컬 작업환경에 `docs/`가 남아 있을 때만 보조 자료로 사용합니다.

## 발표 전 확인

### 기본 확인

```bash
curl -fsS http://127.0.0.1:18080/api/v1/health | python3 -m json.tool
curl -fsS http://127.0.0.1:18080/api/v1/sim/status | python3 -m json.tool
curl -fsS http://127.0.0.1:18001/health | python3 -m json.tool
```

### 브라우저 확인

```bash
python3 scripts/browser_demo_smoke.py \
  --mode live \
  --url http://127.0.0.1:3000/ \
  --expected-endpoint http://127.0.0.1:18080

python3 scripts/browser_demo_smoke.py \
  --mode replay \
  --url http://127.0.0.1:3000/replay
```

### 전체 리허설

```bash
python3 scripts/demo_rehearsal.py \
  --orchestrator-url http://127.0.0.1:18080 \
  --client-url http://127.0.0.1:3000 \
  --expected-client-endpoint http://127.0.0.1:18080
```

## 문서 인덱스

공유 저장소에서 추적하는 프로젝트 상태 문서는 `project/` 아래에 모았습니다. 로컬 에이전트/운영 runbook 성격의 `.codex/`, `.agents/`, `codex/`, `docs/`는 현재 `.gitignore` 대상입니다.

- `project/SPEC.md` — 구현 스펙
- `project/TEST_PLAN.md` — 테스트 계획
- `project/DECISIONS.md` — 주요 의사결정 기록
- `project/PROGRESS.md` — 구현/검증 진행 로그
- `project/SESSION_HANDOFF.md` — 현재 운영 handoff
- `project/TASKS.json` — 작업/마일스톤 상태
- `project/source/Project Aetherville PRD.pdf` — 원본 PRD 자료
- `project/RTX5090_MIGRATION_RUNBOOK.md` — 4090 종료 전 백업과 5090 direct-process 이관 절차
- `infra/docker/` — Docker Compose 포터빌리티 참고 자료. 현재 RunPod 실행 경로는 direct-process입니다.

## 주의 사항

- 현재 RunPod 실행 경로는 Docker가 아니라 direct-process입니다.
- Docker daemon setup, Docker Compose, Docker-in-Docker, blind Docker retry를 사용하지 않습니다.
- 현재 검증된 vision 포트는 `18001`입니다.
- public RunPod endpoint는 tracked config에 없습니다. 기본 발표 방식은 SSH tunnel입니다.
- `.env.runpod`, SSH key, token, model credential은 절대 커밋하지 않습니다.
- real AI 경로를 주장할 때는 health/smoke 결과로 확인한 뒤 말합니다.
