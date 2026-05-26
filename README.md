# Project Aetherville

> RunPod H100 상시 운영 기반 AI 도시 시뮬레이터

Project Aetherville는 **맥북 브라우저에서 보는 3D 도시**와 **상시 구동 중인 RunPod H100 AI 서버**를 연결한 데모 프로젝트입니다. 사용자는 God Mode에 자연어로 도시 상황을 입력하고, H100 서버는 그 명령을 도시 상태·시민 기억·차량 카메라·교통 정책·학습 루프에 반영합니다.

이 프로젝트가 보여주고 싶은 핵심은 “AI API를 한 번 호출했다”가 아니라, **AI가 도시 안의 여러 시스템을 판단하고, 그 판단이 화면에서 바로 보이는 경험**입니다.

맥북에서 시연할 때는 [`MACBOOK_DEMO_QUICKSTART.md`](MACBOOK_DEMO_QUICKSTART.md)를 먼저 보면 됩니다. 실제 endpoint, SSH 값, 토큰은 git에 넣지 않고 맥북 로컬 설정 파일에만 저장합니다.

## 현재 데모 기준

Aetherville는 H100 서버가 계속 켜져 있고, 브라우저는 그 서버에 붙어 화면만 렌더링하는 구성을 기준으로 설명합니다.

- **H100 서버**: vLLM, vision service, orchestrator, simulation, learning/checkpoint registry를 실행합니다.
- **맥북 브라우저**: Next.js/R3F 화면, God Mode 입력, 상태 패널, replay fallback을 담당합니다.
- **연결 방식**: public endpoint가 있으면 바로 연결하고, 없으면 SSH tunnel로 `localhost`에 붙입니다.
- **자가학습 표현**: 실행 중 reward-gated policy adaptation은 계속 반영됩니다. 모델 weight를 바꾸는 학습은 trainer가 checkpoint를 만들고 평가를 통과한 것만 승격/reload하는 방식입니다.
- **현재 검증 범위**: vLLM LoRA/SFT manifest, YOLO pseudo-label artifact, traffic policy checkpoint, traffic LSTM forecast checkpoint의 promotion/reload 경로가 준비되어 있습니다.

정확히 말하면, 이 프로젝트는 “완전한 AGI 도시”가 아니라 **AI 판단·시뮬레이션·학습 아티팩트 승격을 한 화면에서 보여주는 playable AI city demo**입니다.

## 이 프로젝트에서 보여주고 싶은 것

### 1. 그냥 배경이 아닌 살아 움직이는 도시

도시는 미리 찍어둔 영상이 아니라 서버 tick에 따라 계속 변하는 상태입니다.

- 시민이 이동하고 기억을 남김
- 차량이 도로 위에서 목적지를 향해 이동함
- 신호등과 교통 흐름이 변함
- 날씨와 이벤트가 도시 분위기를 바꿈
- 중요한 변화가 여러 UI 패널에 동시에 표시됨
- 복합 상황은 `Scenario Director`가 단계별로 풀어서 실행함

목표는 보는 사람이 “그냥 반복 영상 아닌가?”라고 느끼지 않도록, **명령 → 판단 → 이동 → 패널 변화**가 이어지는 도시를 보여주는 것입니다.

### 2. God Mode로 도시를 직접 움직이는 경험

발표자는 텍스트로 도시 상황을 지시할 수 있습니다.

```text
민수가 하린을 만난 뒤 택시를 불러 민지에게 가고,
드론은 서연에게 이동한 뒤 서연은 민지와 민수를 만나러 간다
```

이런 명령은 하나의 이벤트로 끝나지 않습니다.

- 시민 이동
- 만남 이벤트
- 택시 호출
- 차량 이동
- 드론 이동
- 최종 합류
- 시민 기억 및 상태 패널 갱신

처럼 여러 단계로 분해되어 화면에 나타납니다.

### 3. AI가 어디에 쓰였는지 숨기지 않는 화면

Aetherville는 AI 기능을 내부 로그에만 숨기지 않고, 발표자가 설명할 수 있도록 화면에 노출합니다.

- **Scenario Director**: 복합 명령이 어떤 단계로 실행되는지 보여줌
- **Citizen Memory**: 시민이 본 사건과 반응을 보여줌
- **Vehicle Camera**: 차량 시점의 vision detection 결과를 보여줌
- **Traffic Forecast**: 교통 정책과 예측 결과를 보여줌
- **AI Learning Loop**: reward, policy bias, checkpoint 상태를 보여줌
- **God Mode**: 사용자의 자연어 명령과 적용된 도시 action을 연결함

즉, 핵심은 “버튼을 누르니 뭔가 변한다”가 아니라 **AI 판단이 도시 상태로 번역되는 과정**입니다.

### 4. H100 서버와 브라우저의 역할 분리

맥북은 화면을 보여주는 데 집중하고, 무거운 AI와 시뮬레이션은 H100 서버가 맡습니다.

- 맥북: 3D 렌더링, 패널 UI, God Mode 입력
- H100: LLM 추론, vision, traffic AI, simulation loop, learning registry
- 연결: REST + Socket.IO polling

이 구조 덕분에 맥북 성능에 의존하지 않고, 같은 H100 서버에 연결하면 다른 환경에서도 같은 도시 상태를 볼 수 있습니다.

## 기술 스택

| 영역 | 사용 기술 | 역할 |
|---|---|---|
| Frontend | Next.js App Router, React, TypeScript | 브라우저 화면, God Mode 입력, 패널 UI |
| 3D Rendering | React Three Fiber, Three.js | 도시, 도로, 시민, 차량, 날씨, 카메라 연출 |
| Client State | Zustand | 연결 상태와 world state 관리 |
| Realtime | Socket.IO client/server | 서버 tick과 도시 상태를 브라우저로 전달 |
| Backend API | FastAPI, Uvicorn, python-socketio, asyncio | REST API, Socket.IO, simulation loop, command dispatcher |
| Schema Contract | Pydantic, generated TypeScript | 서버와 클라이언트의 world state/API 계약 일치 |
| LLM Runtime | vLLM OpenAI-compatible API | God Mode 해석, 시민 reflection, City AI 계획 |
| Vision | Ultralytics YOLO, FastAPI vision service | 차량 카메라 detection과 vision evidence 생성 |
| Traffic AI | Policy checkpoint, LSTM forecast checkpoint | 교통 신호 정책과 혼잡 예측 |
| Learning Store | JSON-backed experience log, checkpoint registry | reward 기록, policy adaptation, promotion/rollback 상태 |
| Training Pipeline | LoRA/SFT dataset builder, YOLO pseudo-label, traffic rollout trainer, LSTM trainer | H100 trainer cycle, 평가, checkpoint 승격, runtime reload |
| Runtime | RunPod H100 direct process | AI 서버와 시뮬레이션을 상시 실행 |
| Tooling | pnpm, uv, pytest, ruff, mypy, browser smoke scripts | 설치, 타입검사, 테스트, 브라우저 검증 |

## 아키텍처

Aetherville는 **로컬 브라우저 UI**와 **H100 AI 백엔드**를 분리합니다. 브라우저는 시각화와 입력을 담당하고, H100 서버는 AI 추론과 도시 상태를 담당합니다.

```text
┌──────────────────────────────────────────────────────────────┐
│                       MacBook / Local PC                      │
├──────────────────────────────────────────────────────────────┤
│ Next.js Client :3000                                          │
│                                                              │
│  ┌──────────────────┐   ┌─────────────────────────────────┐  │
│  │ 3D City Scene     │   │ City Panels                     │  │
│  │ - roads/buildings │   │ - Scenario Director             │  │
│  │ - citizens/cars   │   │ - Citizen Memory                │  │
│  │ - weather/traffic │   │ - Vehicle Camera                │  │
│  │ - camera focus    │   │ - Traffic Forecast              │  │
│  └──────────────────┘   │ - AI Learning Loop              │  │
│                         │ - God Mode Console              │  │
│                         └─────────────────────────────────┘  │
│                                                              │
│  REST fetch + Socket.IO polling                              │
└──────────────────────────────┬───────────────────────────────┘
                               │
                               │ public endpoint 또는 SSH tunnel
                               ▼
┌──────────────────────────────────────────────────────────────┐
│                    RunPod H100 AI Backend                     │
├──────────────────────────────────────────────────────────────┤
│ Orchestrator :8080                                            │
│ - FastAPI REST API                                            │
│ - Socket.IO state broadcast                                   │
│ - simulation tick loop                                        │
│ - God Mode dispatcher                                         │
│ - City AI planner/executor                                    │
│ - vehicle camera endpoint                                     │
│ - learning status endpoint                                    │
├──────────────────────────────────────────────────────────────┤
│ AI / Simulation Services                                      │
│ - vLLM :8000                LLM/God Mode/citizen reflection   │
│ - Vision :18001             YOLO detection                    │
│ - Traffic policy checkpoint  signal control evidence          │
│ - LSTM forecast checkpoint   traffic forecast evidence        │
│ - Learning registry         promotion / rollback state        │
└──────────────────────────────────────────────────────────────┘
```

## 데이터 흐름

### God Mode 명령

```text
사용자 텍스트 입력
  → Browser God Mode panel
  → POST /api/v1/god/command
  → Orchestrator command dispatcher
  → vLLM 해석 또는 deterministic fallback
  → safe action list 생성
  → simulation world state 변경
  → REST state / Socket.IO state_update
  → 3D city, Scenario Director, panels 갱신
```

### City AI 자율 계획

```text
Simulation interval/event window
  → Orchestrator builds CityWorldContext
  → vLLM returns bounded CityAiPlan JSON
  → Simulation validates allowed actions
  → citizens/taxi/weather/traffic/memory mutate through executors
  → WorldStatePayload.city_ai + city_ai_plan timeline event
  → 3D city camera, actor labels, Scenario Director cards update
```

### 차량 vision

```text
Browser Vehicle Camera panel
  → GET /api/v1/vehicles/{vehicle_id}/camera
  → Orchestrator camera endpoint
  → Vision service /detect
  → YOLO 또는 deterministic detection
  → Vehicle panel에 detection badge와 결과 표시
```

### 교통 AI

```text
Simulation tick
  → traffic state 계산
  → traffic policy checkpoint 또는 fallback controller
  → signal phase / congestion / forecast update
  → Traffic panel과 Scenario Director에 표시
```

## 주요 포트

| 포트 | 위치 | 용도 | 비고 |
|---:|---|---|---|
| `3000` | MacBook/local | Next.js browser client | 시연 화면 |
| `8080` | H100 | Orchestrator REST + Socket.IO | tunnel에서는 local `18080` |
| `8000` | H100 | vLLM OpenAI-compatible API | tunnel에서는 local `18000` |
| `18001` | H100 | Vision service | 현재 사용하는 vision 포트 |
| `6379` | H100 | Redis compatible state | 없으면 memory fallback |

## 학습과 진화 방식

Aetherville의 “학습”은 두 층으로 나뉩니다.

### 1. 실행 중 adaptation

도시가 돌아가는 동안 reward와 경험 로그를 저장하고, policy bias를 조정합니다. 이 경로는 빠르고 안전해서 데모 중에도 계속 반영됩니다.

### 2. checkpoint 기반 모델 개선

모델 weight나 학습 아티팩트는 바로 바꾸지 않습니다. 대신 아래 흐름을 거칩니다.

```text
Experience Log
  → Dataset Builder
  → Trainer
  → Evaluation Gate
  → Checkpoint Registry
  → Promotion / Rejection
  → Runtime Reload
```

이 방식은 실시간성과 안정성 사이의 균형을 맞추기 위한 선택입니다. 모델이 갑자기 나빠지면 전체 도시가 흔들릴 수 있기 때문에, 좋아진 checkpoint만 승격하고 실패한 결과는 거절하거나 rollback합니다.

## 트레이드오프

### H100 상시 운영을 선택한 이유

- 장점: vLLM, vision, traffic AI를 항상 준비해둘 수 있어 데모 시작이 빠릅니다.
- 장점: 맥북 성능과 무관하게 같은 AI 백엔드를 사용할 수 있습니다.
- 단점: 클라우드 비용이 계속 발생합니다.
- 단점: 서버 상태, public endpoint, tunnel 상태를 운영해야 합니다.

### 브라우저와 AI 서버를 분리한 이유

- 장점: 브라우저는 가볍고, AI 서버는 무거운 추론과 시뮬레이션에 집중합니다.
- 장점: 다른 노트북에서도 같은 endpoint에 붙으면 같은 데모를 볼 수 있습니다.
- 단점: 네트워크가 불안정하면 live 화면 품질이 떨어질 수 있습니다.

### checkpoint 승격 방식을 선택한 이유

- 장점: 학습 결과를 평가한 뒤 좋은 결과만 도시 런타임에 반영할 수 있습니다.
- 장점: 실패한 학습 결과를 rollback할 수 있습니다.
- 단점: “켜놓으면 weight가 즉시 계속 바뀐다”는 방식보다 느립니다.
- 단점: trainer, registry, evaluation gate를 별도로 관리해야 합니다.

### deterministic fallback을 남긴 이유

- 장점: AI 서비스가 흔들려도 화면 흐름이 완전히 멈추지 않습니다.
- 장점: 어떤 경로가 real이고 어떤 경로가 fallback인지 UI에서 설명할 수 있습니다.
- 단점: fallback 상태가 오래 지속되면 “진짜 AI 도시”라는 인상이 약해질 수 있습니다.

## 주요 화면 구성

### Live City

시민, 차량, 도로, 건물, 신호등, 날씨 효과가 함께 보이는 메인 화면입니다. 카메라는 현재 중요한 사건이나 이동 대상에 포커스를 둡니다.

### Scenario Director

복합 명령이 어떤 단계로 실행되고 있는지 보여줍니다. 예를 들어 `meeting → taxi → drone → join` 같은 순서가 카드로 표시됩니다.

### Citizen Memory

시민이 관찰한 사건과 반응을 보여줍니다. 도시가 단순 배경이 아니라 시민 상태와 기억을 가진 공간이라는 점을 보여주는 패널입니다.

### Vehicle Camera

차량 시점과 detection 결과를 보여줍니다. 차량이 어디를 보고 있고, 어떤 객체를 인식했는지 설명할 수 있습니다.

### Traffic Forecast

교통량과 예측 결과를 보여줍니다. traffic policy와 LSTM forecast checkpoint가 연결되어 있을 때 그 근거를 패널에 표시합니다.

### God Mode

발표자가 도시 상황을 직접 바꾸는 텍스트 명령 콘솔입니다. 복합 명령을 입력하면 도시 상태와 화면 패널이 함께 변합니다.

### Replay Fallback

라이브 연결이 불안정할 때도 프로젝트 의도를 설명할 수 있는 deterministic fallback 화면입니다.

## 현재 구현된 데모 포인트

- 브라우저 3D 도시 렌더링
- H100 backend 연결
- Socket.IO 기반 상태 업데이트
- 시민 memory stream
- 차량 camera panel
- vision detection 구분
- traffic AI / forecast 표시
- God Mode natural-language command
- multi-action city effect
- Scenario Director complex story timeline
- AI Learning Loop
- checkpoint promotion / runtime reload 경로
- replay fallback
- browser smoke / visual smoke / impact smoke scripts

## 실행 방법

### 1. 설치

```bash
pnpm install
uv sync
```

### 2. H100 연결 설정

맥북에서 public endpoint를 받은 경우 `client/.env.local`에 orchestrator URL을 넣습니다.

```bash
NEXT_PUBLIC_ORCHESTRATOR_URL=https://YOUR_H100_ORCHESTRATOR_URL
NEXT_PUBLIC_SOCKET_URL=https://YOUR_H100_ORCHESTRATOR_URL
NEXT_PUBLIC_SOCKET_TRANSPORTS=polling
```

public endpoint가 없으면 SSH tunnel을 열고 `127.0.0.1:18080`으로 연결합니다.

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

`tunnel` 방식에서는 클라이언트 env를 아래처럼 둡니다.

```bash
NEXT_PUBLIC_ORCHESTRATOR_URL=http://127.0.0.1:18080
NEXT_PUBLIC_SOCKET_URL=http://127.0.0.1:18080
NEXT_PUBLIC_SOCKET_TRANSPORTS=polling
```

### 3. 로컬 화면 실행

```bash
pnpm dev
```

브라우저에서 엽니다.

```text
http://localhost:3000/
```

라이브 연결이 불안정할 때는 replay 화면을 사용합니다.

```text
http://localhost:3000/replay
```

## 문서 인덱스

공유 저장소에서 추적하는 프로젝트 상태 문서는 `project/` 아래에 모았습니다. 로컬 에이전트/운영 runbook 성격의 `.codex/`, `.agents/`, `codex/`, `docs/`, `.github/`는 현재 `.gitignore` 대상입니다.

- `project/SPEC.md` — 구현 스펙
- `project/TEST_PLAN.md` — 테스트 계획
- `project/DECISIONS.md` — 주요 의사결정 기록
- `project/PROGRESS.md` — 구현/검증 진행 로그
- `project/SESSION_HANDOFF.md` — 현재 운영 handoff
- `project/TASKS.json` — 작업/마일스톤 상태
- `project/source/Project Aetherville PRD.pdf` — 원본 PRD 자료
- `project/RTX5090_MIGRATION_RUNBOOK.md` — GPU 서버 이관 절차

## 주의 사항

- H100 서버가 AI 추론과 simulation loop를 담당합니다.
- 브라우저는 vLLM에 직접 붙지 않고 orchestrator에 붙습니다.
- 현재 사용하는 vision 포트는 `18001`입니다.
- public endpoint와 SSH 값은 tracked config에 넣지 않습니다.
- `.env.runpod`, SSH key, token, model credential은 절대 커밋하지 않습니다.
- real AI 경로를 설명할 때는 health/smoke 결과로 확인한 범위만 말합니다.
- 모델 weight가 즉시 계속 바뀐다고 말하지 않습니다. 학습 결과는 checkpoint 승격과 runtime reload를 통해 반영됩니다.
