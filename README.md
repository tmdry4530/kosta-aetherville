# Project Aetherville — Codex 전용 문서팩

이 문서팩은 `Project Aetherville PRD v1.0`을 Codex가 바로 실행 가능한 작업 계약으로 바꾼 것이다. 다른 AI 도구용 wrapper는 의도적으로 넣지 않았고, Codex가 항상 읽는 `AGENTS.md`, 장기 작업용 `.codex/goals/*`, 재사용 workflow용 `.agents/skills/*`, RunPod SSH 배포 문서와 검증 체크리스트만 포함한다.

## 사용 순서

1. 새 레포를 만들거나 기존 레포 루트에서 이 문서팩의 파일을 복사한다.
2. `source/Project Aetherville PRD.pdf`는 원본 근거 문서로 유지한다.
3. RunPod SSH 정보는 `infra/runpod/.env.runpod.example`을 복사해 `.env.runpod`에 채운다.
4. Codex를 레포 루트에서 시작한다.
5. `00-CODEX-FIRST-PROMPT.md`의 첫 프롬프트를 붙여 넣는다.
6. 바로 구현을 맡기지 말고 `/plan`으로 첫 계획을 받는다.
7. 이후 `.codex/goals/00-runpod-ssh-bootstrap.md`부터 `/goal`로 진행한다.

## 권장 첫 명령

```text
/plan Read AGENTS.md, SPEC.md, TEST_PLAN.md, DECISIONS.md, TASKS.json, docs/architecture-contract.md, and codex/RUNPOD_SSH_DEPLOYMENT.md. Then propose the safest M0 implementation plan. Do not edit files yet.
```

계획 확인 후:

```text
/goal Complete .codex/goals/00-runpod-ssh-bootstrap.md exactly. Treat it as the acceptance criteria. Use SSH only through env vars from infra/runpod/.env.runpod. Do not mark complete until verification commands pass or blockers are explicitly reported.
```

## 구성 요약

- `AGENTS.md`: Codex 루트 운영 계약
- `server/AGENTS.md`, `client/AGENTS.md`, `infra/AGENTS.md`, `packages/shared-schemas/AGENTS.md`, `scripts/AGENTS.md`: 디렉터리별 지시
- `SPEC.md`: PRD를 구현 스펙으로 압축
- `TEST_PLAN.md`: 검증 기준과 release gate
- `TASKS.json`: M0~M6 실행 작업 상태
- `.codex/goals/`: Codex `/goal`에 넣을 장기 작업 단위
- `.codex/prompts/`: 세션별 복붙 프롬프트
- `.agents/skills/`: Codex skills workflow
- `codex/RUNPOD_SSH_DEPLOYMENT.md`: RunPod SSH 운영 지침
- `infra/runpod/*.sh`: SSH 배포 보조 스크립트

## 중요한 전제

RunPod는 템플릿/이미지에 따라 컨테이너 내부에서 Docker daemon이 없을 수 있다. Codex는 먼저 `docker info`, `nvidia-smi`, `python`, `uv`, `node`, `pnpm`을 점검하고, Docker Compose 경로가 불가능하면 direct-process 경로로 fallback해야 한다.

## 현재 데모 실행

```bash
uv run pytest packages server
pnpm lint
pnpm typecheck
pnpm test
pnpm test:e2e
pnpm dev
```

- Live client: `http://localhost:3000/`
- Replay fallback: `http://localhost:3000/replay`
- RunPod backend health: use `infra/runpod/.env.runpod`, then `bash infra/runpod/verify_runpod.sh`.
- Direct-process cloud mode remains the supported path until Docker daemon is available.

## 데모 문서

- `docs/demo-scenario.md`
- `docs/demo-readiness-checklist.md`
- `docs/metrics-report.md`
- `docs/architecture-diagram.md`
