# New H100 Account Handoff and Remaining Risk Plan

이 문서는 기존 계정 문제로 새 계정의 H100 RunPod/클라우드를 대여했을 때, MacBook/Windows 로컬 에이전트가 **현재 `master` 브랜치 상태를 새 H100 direct-process 런타임으로 복구하고 다음 작업을 이어가기 위한 실행 문서**다.

## 0. 현재 보존 상태

- GitHub `master`에는 demo-ready direct-process runtime과 guarded model-training pipeline이 푸시되어 있다.
- 기존 RunPod workspace/runtime handoff backup은 `.omx/backups/` 아래에 생성한다. `.omx/`는 로컬 백업 영역이며 커밋하지 않는다.
- 백업은 시크릿, `.env.runpod`, SSH key, 모델 캐시, `.safetensors`, `.bin`, `.pt`, `.gguf`, dependency cache, media 파일을 제외한다.
- Docker/Compose/DinD는 현재 실행 경로가 아니다.

## 1. 새 H100에서 가장 먼저 해야 할 일

새 계정의 H100 접속 정보는 절대 문서/채팅/로그에 출력하지 말고 로컬 `infra/runpod/.env.runpod`에만 넣는다.

```bash
cp infra/runpod/.env.runpod.example infra/runpod/.env.runpod
chmod 600 infra/runpod/.env.runpod
```

필수 값:

```bash
RUNPOD_HOST=<new-h100-host>
RUNPOD_SSH_PORT=<new-h100-ssh-port>
RUNPOD_USER=root
RUNPOD_SSH_KEY=<private-key-file>
RUNPOD_REMOTE_DIR=/workspace/aetherville

AETHERVILLE_ORCHESTRATOR_PORT=8080
AETHERVILLE_VISION_PORT=18001
AETHERVILLE_VLLM_PORT=8000
AETHERVILLE_REDIS_MODE=memory
AETHERVILLE_TRAINING_DIR=/workspace/aetherville-training
AETHERVILLE_APPROVE_MODEL_TRAINING=0
```

첫 SSH는 read-only verification만 한다.

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
  'hostname; nvidia-smi --query-gpu=name,driver_version,memory.total --format=csv,noheader; pwd; python --version; df -h / /workspace 2>/dev/null || df -h'
```

## 2. 새 H100 direct-process 배포 순서

모델 다운로드 없이 먼저 safe smoke를 한다.

```bash
bash infra/runpod/deploy_5090_direct.sh --profile safe-smoke --dry-run
bash infra/runpod/deploy_5090_direct.sh --profile safe-smoke
```

safe smoke health가 통과하면 real vLLM/YOLO demo profile을 승인한다.

```bash
AETHERVILLE_APPROVE_REAL_AI=1 \
AETHERVILLE_STT_MODE=stub \
bash infra/runpod/deploy_5090_direct.sh --profile real-demo
```

주의:

- 이 명령은 direct-process만 사용한다.
- Docker/Compose/DinD를 실행하지 않는다.
- 모델 다운로드 비용/시간은 새 H100 계정 크레딧과 네트워크 상태에 의존한다.
- real-demo가 실패하면 blind retry하지 말고 health/log 원인을 기록한다.

## 3. 로컬 tunnel과 health

public endpoint가 없으면 tunnel을 연다.

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

다른 터미널에서 health 확인:

```bash
curl -fsS http://127.0.0.1:18080/api/v1/health | python3 -m json.tool
curl -fsS http://127.0.0.1:18080/api/v1/sim/status | python3 -m json.tool
curl -fsS http://127.0.0.1:18080/api/v1/training/status | python3 -m json.tool
curl -fsS http://127.0.0.1:18001/health | python3 -m json.tool
curl -fsS http://127.0.0.1:18000/v1/models | python3 -m json.tool
```

## 4. 로컬 브라우저 복구

```bash
cat > client/.env.local <<'EOF_ENV'
NEXT_PUBLIC_ORCHESTRATOR_URL=http://127.0.0.1:18080
NEXT_PUBLIC_SOCKET_URL=http://127.0.0.1:18080
NEXT_PUBLIC_SOCKET_TRANSPORTS=polling
EOF_ENV

pnpm install --frozen-lockfile
uv sync
pnpm --filter @aetherville/client dev -- -H 0.0.0.0 -p 3000
```

브라우저:

```bash
open http://127.0.0.1:3000/
open http://127.0.0.1:3000/replay
```

## 5. 새 H100 검증 체크리스트

```bash
python3 -m json.tool project/TASKS.json >/dev/null
bash -n infra/runpod/*.sh
uv run pytest -q
uv run ruff check server packages scripts
uv run mypy server packages scripts/model_training_cycle.py scripts/train_vllm_lora.py scripts/train_yolo_self_training.py
pnpm lint
pnpm typecheck
pnpm test
pnpm test:e2e
NEXT_TELEMETRY_DISABLED=1 pnpm --filter @aetherville/client build
```

Runtime smoke:

```bash
python3 scripts/scenario_directive_smoke.py --orchestrator-url http://127.0.0.1:18080
python3 scripts/replanner_resilience_smoke.py --orchestrator-url http://127.0.0.1:18080 --wait-seconds 70
python3 scripts/learning_evolution_smoke.py --orchestrator-url http://127.0.0.1:18080 --repeat 2 --wait-seconds 25
python3 scripts/autonomous_city_dogfood_smoke.py --orchestrator-url http://127.0.0.1:18080
python3 scripts/browser_demo_smoke.py --mode live --url http://127.0.0.1:3000/ --expected-endpoint http://127.0.0.1:18080 --timeout-seconds 60
python3 scripts/browser_demo_smoke.py --mode replay --url http://127.0.0.1:3000/replay --timeout-seconds 60
```

Training dry-run smoke:

```bash
python3 scripts/model_training_cycle.py \
  --orchestrator-url http://127.0.0.1:18080 \
  --force
```

## 6. 다음에 해야 할 작업

### P0 — 새 H100 계정 복구

1. 새 계정 H100 `.env.runpod` 작성.
2. read-only SSH/GPU/disk/Python 검증.
3. safe-smoke direct deploy.
4. real-demo vLLM/YOLO deploy.
5. tunnel health + browser live/replay smoke.
6. current demo command 3개 dogfood:
   - `택시 없음 상황에서 민수가 택시를 불러 민지에게 간다`
   - `도시에 비를 내리고 민지가 택시를 부르게 하고 출근길을 혼잡하게 만들어줘`
   - `민수가 하린을 만난 뒤 택시를 불러 민지에게 가고, 드론은 서연에게 이동한 뒤 서연은 민지와 민수를 만나러 간다`

### P1 — model weight training 실제화

현재 구현은 training handoff + dry-run + guarded trainer boundary다. “모델 weight가 실제 바뀜”을 말하려면 다음을 해야 한다.

1. H100에서 경험 로그를 충분히 생성한다.
2. `AETHERVILLE_APPROVE_MODEL_TRAINING=1`을 명시하고 target별 non-dry-run training을 실행한다.
3. traffic PPO/LSTM부터 시작한다. 이유: 이미 JSON checkpoint runtime과 evaluator가 가장 안정적이다.
4. vLLM LoRA는 AWQ serving model과 training base model을 분리한다.
5. YOLO는 pseudo-label manifest를 실제 Ultralytics dataset YAML로 변환하는 단계를 추가한다.
6. promoted checkpoint가 생성되면 orchestrator/runtime reload 또는 restart를 검증한다.

권장 순서:

```bash
AETHERVILLE_APPROVE_MODEL_TRAINING=1 \
python3 scripts/model_training_cycle.py \
  --orchestrator-url http://127.0.0.1:18080 \
  --execute \
  --target traffic_ppo

AETHERVILLE_APPROVE_MODEL_TRAINING=1 \
python3 scripts/model_training_cycle.py \
  --orchestrator-url http://127.0.0.1:18080 \
  --execute \
  --target traffic_lstm
```

vLLM/YOLO는 trainer dependencies와 dataset conversion을 먼저 확인한 뒤 실행한다.

### P2 — runtime reload 완성

- `training.status`에서 promoted checkpoint를 읽고, traffic policy / forecast env를 자동 갱신하는 reload endpoint 추가.
- vLLM LoRA adapter를 vLLM에 load하거나 restart하는 명령 path 추가.
- YOLO promoted artifact를 vision service가 load하도록 restart/reload path 추가.
- reload 후 smoke가 실패하면 rollback endpoint로 이전 promoted checkpoint 복구.

### P3 — presentation truth hardening

- UI에 `dry_run`, `promoted`, `approval_required`, `rollback_available`를 명확히 유지한다.
- 발표 문구에서 “자가학습”은 다음처럼 구분한다.
  - 현재 즉시 동작: reward-gated policy adaptation.
  - 준비 완료: Experience Log → trainer → eval → checkpoint promotion.
  - 실제 완료 조건: promoted non-dry-run checkpoint + runtime reload 검증.

## 7. 남은 리스크와 해결 방법

| 리스크 | 영향 | 해결 방법 |
|---|---|---|
| 새 H100 SSH 정보 미확정 | 배포 불가 | `.env.runpod`에만 입력하고 read-only 검증부터 진행 |
| 기존 백업은 모델 캐시/weight 제외 | 모델 재다운로드 필요 | 새 H100에서 real-demo profile로 재다운로드 또는 별도 모델 cache backup 승인 필요 |
| vLLM은 inference 서버 | 켜놓아도 자동 fine-tuning 없음 | LoRA/SFT/DPO trainer job + promoted adapter + reload 검증 필요 |
| AWQ serving model은 training base로 부적합할 수 있음 | LoRA 학습 실패/품질 저하 | serving model과 trainable base model 분리 |
| YOLO self-training은 manifest까지만 안전 구현 | real YOLO weight 변경 미검증 | pseudo-label → Ultralytics YAML 변환 + train + eval + promoted artifact 필요 |
| traffic PPO/LSTM은 가장 가까운 real training target | 아직 새 H100 non-dry-run 검증 전 | 먼저 PPO/LSTM을 execute target으로 검증 |
| Redis memory fallback | pod restart 시 일부 runtime state 손실 | Experience Log/registry는 파일로 유지하고, 장기적으로 Redis/Postgres/volume 연결 |
| public endpoint 없음 | 외부 MacBook 접속 불편 | SSH tunnel mode 유지 또는 RunPod public port/TLS 설정 |
| STT는 stub/fallback 가능 | 음성 시연 리스크 | typed fallback 유지, real STT는 별도 smoke 후만 주장 |
| 비용/크레딧 부족 | training 중단 | dry-run 먼저, target별 짧은 training window, 로그 보고 후 계속 |
| Docker 실행 유혹 | 정책 위반/시간 낭비 | direct-process만 사용, Docker/Compose/DinD 금지 |

## 8. 완료 판정 기준

새 H100 이전 완료:

- 새 H100 safe-smoke deploy 통과.
- real-demo health에서 orchestrator/vLLM/vision ok.
- local browser live/replay smoke 통과.
- God Mode 복합 상황 3개가 화면에서 이동/재계획/패널 업데이트로 보임.

진짜 model-weight self-learning 완료:

- Experience Log가 target별 dataset으로 변환됨.
- 최소 traffic PPO 또는 LSTM non-dry-run trainer가 실행됨.
- Evaluation Gate가 checkpoint를 promoted로 승격함.
- runtime이 promoted checkpoint를 load/restart함.
- smoke가 이전보다 나빠지지 않음.
- rollback path가 실패 케이스에서 동작함.
