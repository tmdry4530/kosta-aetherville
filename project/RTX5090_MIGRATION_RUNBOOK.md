# RTX 5090 Migration Runbook — Project Aetherville

이 문서는 4090 RunPod 크레딧을 오래 쓰지 않고, 새 5090 팟을 만든 직후 Aetherville direct-process 데모를 최대한 빠르게 재현하기 위한 절차다.

## 진실 기준

- 현재 백업은 **코드/레포/로컬 운영 산출물/원격 workspace 스냅샷** 백업이다.
- 4090 팟 전체 디스크 이미지, 모델 캐시, SSH 설정, `.env.runpod`, Hugging Face token, 실행 중 프로세스 메모리 상태를 통째로 보존한 것은 아니다.
- 5090에서 “정상작동 확정”은 아래 smoke gate가 통과한 뒤에만 말한다.
- Docker, Docker Compose, Docker-in-Docker는 사용하지 않는다. 현재 경로는 direct-process runtime이다.

## 0. 4090 종료 전 마지막 백업

4090 팟이 아직 살아 있을 때 로컬에서 한 번 실행한다. 시크릿은 출력하지 않는다.

```bash
bash infra/runpod/verify_runpod.sh
bash infra/runpod/create_remote_handoff_backup.sh
```

성공 기준:

- `verify_runpod.sh`가 SSH/GPU/workspace를 확인한다.
- `create_remote_handoff_backup.sh`가 `.omx/backups/runpod-remote-handoff-*/` 아래에 archive, manifest, SHA256SUMS를 만든다.
- secret-like path scan이 통과한다.

이 백업은 remote workspace와 `/tmp/aetherville/learning_state.json`이 있으면 함께 담는다. 모델 캐시와 dependency/build/cache는 재생성 대상으로 보고 제외한다.

## 1. 5090 팟 생성 직후 로컬 설정

새 팟의 SSH 정보를 로컬 ignored 파일에만 넣는다.

```bash
cp infra/runpod/.env.runpod.example infra/runpod/.env.runpod
# infra/runpod/.env.runpod 편집
```

필수 값:

```text
RUNPOD_HOST=<new-5090-host>
RUNPOD_SSH_PORT=<new-ssh-port>
RUNPOD_USER=root
RUNPOD_SSH_KEY=<local-private-key-path>
RUNPOD_REMOTE_DIR=/workspace/aetherville
MODEL_NAME=Qwen/Qwen2.5-14B-Instruct-AWQ
```

주의:

- `.env.runpod` 내용을 채팅/로그/커밋에 남기지 않는다.
- 기존 4090 host/port가 남아 있으면 안 된다. 새 5090 값으로 바꾼다.
- public URL이 없으면 SSH tunnel 방식으로 충분하다.

## 2. 5090 SSH/GPU 검증

```bash
bash infra/runpod/verify_runpod.sh
```

성공 기준:

- SSH 접속 성공
- `nvidia-smi`에서 5090 GPU 확인
- remote workspace는 없어도 됨. deploy script가 생성한다.
- Docker 관련 확인/시도 없음

## 3. 빠른 safe-smoke 배포 — 모델 다운로드 없음

이 단계는 5090 기본 Python/네트워크/포트/direct-process 경로를 먼저 검증한다. real vLLM/YOLO를 아직 설치하거나 모델을 받지 않는다.

```bash
# Optional no-change connectivity/sync preview
bash infra/runpod/deploy_5090_direct.sh --profile safe-smoke --dry-run

# Actual safe-smoke deploy
bash infra/runpod/deploy_5090_direct.sh --profile safe-smoke
```

성공 기준:

- remote repository sync 완료
- uv가 없으면 user env에 bootstrap
- mock vLLM `:8000`, mock vision `:18001`, orchestrator `:8080` 기동
- remote `health_check_direct.sh` 통과

이 단계가 실패하면 real-demo로 넘어가지 않는다.

## 4. real-demo 배포 — vLLM/YOLO opt-in

5090 크레딧이 있고, 모델 다운로드/설치 시간을 쓰기로 결정한 뒤에만 실행한다.

```bash
AETHERVILLE_APPROVE_REAL_AI=1 \
AETHERVILLE_BOOTSTRAP_VLLM=1 \
AETHERVILLE_BOOTSTRAP_YOLO=1 \
AETHERVILLE_VLLM_INSTALL_PACKAGE='vllm==0.10.2' \
AETHERVILLE_VLLM_COMPAT_PACKAGE='transformers==4.55.4' \
MODEL_NAME='Qwen/Qwen2.5-14B-Instruct-AWQ' \
VLLM_GPU_MEMORY_UTILIZATION=0.90 \
VLLM_MAX_MODEL_LEN=8192 \
bash infra/runpod/deploy_5090_direct.sh --profile real-demo
```

성공 기준:

- real vLLM `/v1/models` 응답
- real YOLO vision service health 응답
- orchestrator health에서 vLLM/vision ok
- `city_ai.mode`가 `vllm` 경로로 노출

주의:

- RTX 5090 환경의 CUDA/PyTorch/vLLM 조합은 실제 pod image에 의존한다.
- vLLM 설치 또는 모델 로딩이 실패하면 safe-smoke는 유지하고, vLLM package/CUDA 호환성만 별도 조정한다.
- 이 실패는 코드 백업 실패가 아니라 런타임 휠/드라이버 호환성 문제로 분류한다.

## 5. 로컬 SSH tunnel

public endpoint가 없으면 로컬에서 tunnel을 연다.

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

## 6. 로컬 health gate

다른 터미널에서:

```bash
curl -fsS http://127.0.0.1:18080/api/v1/health | python3 -m json.tool
curl -fsS http://127.0.0.1:18080/api/v1/sim/status | python3 -m json.tool
curl -fsS http://127.0.0.1:18001/health | python3 -m json.tool
curl -fsS http://127.0.0.1:18000/v1/models | python3 -m json.tool
```

## 7. 로컬 브라우저 client

```bash
NEXT_PUBLIC_ORCHESTRATOR_URL=http://127.0.0.1:18080 \
NEXT_PUBLIC_SOCKET_URL=http://127.0.0.1:18080 \
NEXT_PUBLIC_SOCKET_TRANSPORTS=polling \
pnpm --filter @aetherville/client exec next dev -H 0.0.0.0 -p 3000
```

브라우저:

```text
http://127.0.0.1:3000/
http://127.0.0.1:3000/replay
```

## 8. 최종 smoke gate

```bash
python3 scripts/scenario_directive_smoke.py --orchestrator-url http://127.0.0.1:18080 --wait-seconds 12
python3 scripts/replanner_resilience_smoke.py --orchestrator-url http://127.0.0.1:18080 --wait-seconds 25
python3 scripts/learning_evolution_smoke.py --orchestrator-url http://127.0.0.1:18080 --repeat 2 --wait-seconds 25
python3 scripts/autonomous_city_dogfood_smoke.py --orchestrator-url http://127.0.0.1:18080 --wait-seconds 8
python3 scripts/browser_demo_smoke.py --mode live --url http://127.0.0.1:3000/ --expected-endpoint http://127.0.0.1:18080 --timeout-seconds 45
python3 scripts/browser_demo_smoke.py --mode replay --url http://127.0.0.1:3000/replay --timeout-seconds 45
```

5090 정상작동 판정:

- 위 smoke가 통과하면 4090 팟 삭제 가능
- 하나라도 실패하면 4090 삭제 전 실패 로그를 보존하고 safe-smoke fallback 또는 package 호환성 조정으로 복구

## 9. 빠른 장애 분류

| 증상 | 의미 | 조치 |
|---|---|---|
| SSH 실패 | 새 팟 SSH key/port/user 문제 | `.env.runpod`만 수정 후 `verify_runpod.sh` 재실행 |
| GPU 미표시 | RunPod image/runtime 문제 | 5090 GPU image 확인, 다른 template 사용 |
| uv 없음 | 정상 가능 | `deploy_5090_direct.sh`가 `AETHERVILLE_BOOTSTRAP_UV=1`로 설치 |
| safe-smoke 실패 | 기본 Python/포트/동기화 문제 | real-demo 금지, remote logs 확인 |
| real vLLM 설치 실패 | CUDA/PyTorch/vLLM wheel 호환성 문제 | safe-smoke 유지, vLLM package pin 조정 |
| 모델 로딩 실패 | 모델 접근/HF token/VRAM 설정 문제 | `MODEL_NAME`, token, `VLLM_EXTRA_ARGS` 확인 |
| client error/replay-clear | 브라우저 endpoint 문제 | tunnel/`NEXT_PUBLIC_*` 값을 5090 기준으로 재시작 |
