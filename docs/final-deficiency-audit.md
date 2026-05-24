# Final Deficiency Audit — Project Aetherville

- Audit time: 2026-05-24
- Verdict: **PASS for the approved playable demo**
- Scope: documentation/test/runtime audit only. Master implementation phases were not reopened.
- Runtime policy: direct-process RunPod runtime only. Docker/Docker Compose/Docker-in-Docker were not run.

## Summary

The repository is ready for the approved 15-minute playable demo using the
verified direct-process RunPod runtime and local browser client. No blocking
implementation, test, documentation, RunPod, local runtime, fallback, or security
deficiency remains for the approved demo posture.

The audit found one non-blocking endpoint mismatch: the requested audit probe
`http://127.0.0.1:18001/api/v1/health` returns `404`, while the documented and
SPEC-defined vision health endpoint is `http://127.0.0.1:18001/health`, which
returns `200`. This is not a demo blocker because `SPEC.md`,
`docs/live-demo-runbook.md`, and the service implementation all define vision
health as `/health`.

## Requirement-to-evidence matrix

| Requirement | Evidence files | Command/test/smoke evidence | Status |
|---|---|---|---|
| Monorepo foundation exists | `README.md`, `.codex/goals/MASTER_AETHERVILLE_FULL_DELIVERY.md`, `TASKS.json`, `PROGRESS.md` | `uv run pytest` → 29 passed; `pnpm typecheck` passed | PASS |
| Shared schema is source of truth | `packages/shared-schemas/**`, `docs/api-ws-contract.md`, `TASKS.json` | `uv run pytest`; `pnpm test` → 3 Node tests, including generated state update bridge | PASS |
| Direct-process RunPod runtime is active | `DECISIONS.md` ADR-009/010, `docs/live-demo-runbook.md`, `infra/runpod/*.sh` | `bash -n infra/runpod/*.sh`; tunnel health `http://127.0.0.1:18080/api/v1/health` → 200 | PASS |
| Docker is not required/currently excluded | `DECISIONS.md`, `docs/live-demo-runbook.md`, `docs/risk-register.md`, `infra/runpod/deploy_over_ssh.sh` | No Docker command run; scripts reject/skip current Docker path | PASS |
| RunPod orchestrator health works | `docs/live-demo-runbook.md`, `SESSION_HANDOFF.md`, `PROGRESS.md` | `curl http://127.0.0.1:18080/api/v1/health` → 200, status `ok` | PASS |
| Simulation status works | `.codex/goals/04-simulation-engine.md`, `docs/live-demo-runbook.md` | `curl http://127.0.0.1:18080/api/v1/sim/status` → 200, 20 citizens, 1 vehicle | PASS |
| Vision health works on verified demo port | `docs/cloud-direct-process.md`, `docs/live-demo-runbook.md`, `docs/demo-script-15min.md` | `curl http://127.0.0.1:18001/health` → 200; deterministic YOLO stub reported | PASS |
| Vision canonical `8001` limitation is truthful | `DECISIONS.md`, `docs/risk-register.md`, `SESSION_HANDOFF.md`, `docs/demo-script-15min.md` | User accepted `18001`; docs state canonical `8001` is blocked on current pod | PASS |
| vLLM path is demo-safe fallback, not claimed real | `DECISIONS.md`, `docs/metrics-report.md`, `docs/live-demo-runbook.md` | Orchestrator health reports vLLM dependency ok via fallback; no real model claim | PASS |
| Real YOLO/PPO/LSTM/STT are not falsely claimed | `docs/demo-script-15min.md`, `docs/metrics-report.md`, `docs/risk-register.md`, `DECISIONS.md` | Docs explicitly say deterministic stubs / opt-in real workloads | PASS |
| Local client can render live route | `docs/live-demo-runbook.md`, `README.md` | Local client was initially down, then started; `curl http://127.0.0.1:3000/` passed | PASS |
| Replay fallback works | `docs/demo-readiness-checklist.md`, `docs/demo-script-15min.md`, client e2e test | `pnpm test:e2e` → 1 passed; `curl http://127.0.0.1:3000/replay` passed | PASS |
| 15-minute presentation flow exists | `docs/demo-script-15min.md`, `docs/demo-readiness-checklist.md` | Documentation reviewed; flow covers opening, city, memory, vision, traffic, God Mode, replay | PASS |
| Live demo runbook covers public and tunnel modes | `docs/live-demo-runbook.md` | Runbook contains Mode A public endpoint and Mode B SSH tunnel | PASS |
| Environment variables are local-only | `README.md`, `codex/RUNPOD_SSH_DEPLOYMENT.md`, `.env.example`, `infra/runpod/.env.runpod.example` | No `.env.runpod` content printed; git status clean before audit doc creation | PASS |
| Security/secret handling is acceptable | `AGENTS.md`, `DECISIONS.md`, `docs/live-demo-runbook.md` | No secrets/tokens/key paths included in this audit; tracked env remains example-only | PASS |
| Metrics report exists and is honest | `docs/metrics-report.md` | Report marks real ML workloads as deferred; benchmark gaps documented | PASS |
| Accepted operational risks are recorded | `docs/risk-register.md`, `DECISIONS.md`, `TASKS.json`, `PROGRESS.md`, `SESSION_HANDOFF.md` | User acceptance recorded in commit `43cfcd4` | PASS |

## Completed-claim evidence check

| Claim | Evidence |
|---|---|
| Master goal and Phase 99 are complete | `TASKS.json` tasks through `M7-005`; `PROGRESS.md`; `.codex/goals/99-final-audit.md` |
| Final demo freeze is complete | `docs/live-demo-runbook.md`, `docs/demo-script-15min.md`, `docs/demo-readiness-checklist.md`, commit `9d0e974` |
| Operational risks are accepted | `DECISIONS.md` ADR-010, `docs/risk-register.md`, commit `43cfcd4` |
| Local and Python tests pass | Current audit commands: `uv run pytest`, `uv run ruff check`, `uv run mypy` |
| Client tests/build pass | Current audit commands: `pnpm lint`, `pnpm typecheck`, `pnpm test`, `pnpm test:e2e`, client build |
| RunPod tunnel runtime is reachable | Current audit curls to `18080`; `scripts/demo_smoke.py --orchestrator-url http://127.0.0.1:18080` |

## Gap analysis

### Implementation

- No blocking implementation gaps for the approved demo.
- Real vLLM/YOLO/PPO/LSTM/STT are intentionally not active; this is documented
  and accepted, not a deficiency for the approved demo.

### Tests

- Required Python/TypeScript/client tests pass.
- No browser-driven visual QA was run in this audit; non-blocking because the
  requested audit commands use build/e2e/static route checks.

### Docs

- Required runbook, 15-minute script, readiness checklist, metrics report, and
  risk register exist.
- No blocking doc gaps found.

### Demo flow

- The 15-minute script covers opening explanation, normal city simulation,
  citizen/memory, vehicle/vision, traffic, God Mode, and fallback/replay.
- Demo can run in SSH tunnel mode now.

### RunPod runtime

- Orchestrator tunnel health: pass.
- Simulation status: pass.
- Vision `/health`: pass on `18001`.
- Non-blocking mismatch: `18001/api/v1/health` returns 404 because vision uses
  `/health` by contract.

### Local client runtime

- Initial probe found the local client down.
- It was restarted during the audit and both `/` and `/replay` passed.
- Operational note: if the browser cannot connect later, restart with the
  runbook command and verify port `3000`.

### Environment variables

- Required demo envs are documented.
- Public RunPod endpoint values remain local-only/untracked by design.

### Ports/tunnels

- SSH tunnel Mode B is active and verified:
  - orchestrator: `127.0.0.1:18080`
  - vLLM fallback tunnel: `127.0.0.1:18000`
  - vision: `127.0.0.1:18001`
- Public endpoint Mode A remains untested/unconfigured in tracked files; this is
  user-accepted and not a blocker.

### Fallback/replay

- Replay route passed e2e and current local curl check.
- Runbook and script describe replay fallback.

### Security/secret handling

- No `.env.runpod` values, SSH key paths, tokens, or secrets are included in
  this audit file.
- Docker was not run.

### Presentation truthfulness

- The presentation must say:
  - vLLM is a mock OpenAI-compatible fallback unless real mode is separately
    started and verified.
  - Vision is deterministic mock detections on `18001`, not real YOLO.
  - PPO/LSTM are wrapper/fallback paths, not trained live models.
  - STT/voice is optional; text God Mode is the reliable path.

## Commands run

```bash
git status --short
git log --oneline -5
python3 -m json.tool TASKS.json
bash -n infra/runpod/*.sh
git diff --check
uv run pytest
uv run ruff check server packages scripts
uv run mypy server packages
pnpm lint
pnpm typecheck
pnpm test
pnpm test:e2e
pnpm --filter @aetherville/client build
curl http://127.0.0.1:18080/api/v1/health
curl http://127.0.0.1:18080/api/v1/sim/status
curl http://127.0.0.1:18001/api/v1/health
curl http://127.0.0.1:18001/health
python3 scripts/demo_smoke.py --orchestrator-url http://127.0.0.1:18080
curl http://127.0.0.1:3000/
curl http://127.0.0.1:3000/replay
```

## Passed checks

- Git clean before writing this audit file.
- Latest commits visible: `43cfcd4`, `9d0e974`, `8546758`.
- `TASKS.json` JSON syntax passed.
- RunPod shell syntax passed.
- `git diff --check` passed.
- `uv run pytest` passed: 29 tests.
- `uv run ruff check server packages scripts` passed.
- `uv run mypy server packages` passed: 45 source files.
- `pnpm lint` passed.
- `pnpm typecheck` passed.
- `pnpm test` passed: 3 Node tests.
- `pnpm test:e2e` passed: 1 replay test.
- `pnpm --filter @aetherville/client build` passed; `/` and `/replay` built.
- Orchestrator health passed: HTTP 200, status `ok`.
- Simulation status passed: HTTP 200.
- Vision documented health passed: HTTP 200 on `/health`.
- Demo smoke over tunnel passed: health `ok`, 20 citizens, 1 vehicle, forecast
  offsets `[5, 10, 15]`.
- Local client `/` passed after restart.
- Local client `/replay` passed after restart.

## Failed or skipped checks

| Check | Result | Assessment |
|---|---|---|
| `curl http://127.0.0.1:18001/api/v1/health` | HTTP 404 | Non-blocking endpoint mismatch; vision contract is `/health`. |
| Public RunPod REST/WSS Mode A | Skipped | Public URLs are not configured in tracked files and this is user-accepted. |
| Real vLLM/YOLO/PPO/LSTM/STT inference | Skipped | Explicitly opt-in only; not part of approved playable demo proof. |
| Docker/Docker Compose | Skipped by rule | Must not run for current direct-process runtime. |

## Demo blockers

None for the approved direct-process/tunnel demo.

## Non-blocking risks

- Public RunPod REST/WSS endpoints are not configured in tracked files; use SSH
  tunnel Mode B unless local ignored public endpoint envs are supplied.
- Vision canonical `8001` is blocked on the current pod; demo uses verified
  `18001`.
- Real vLLM/YOLO/PPO/LSTM/STT remain deferred/opt-in.
- Remote `rsync` remains unavailable; tar-over-SSH sync fallback has no delete
  semantics.
- Local Next.js dev server may stop with its shell/session; restart it using the
  runbook command before presenting.

## Exact next actions

1. Keep the current tunnel/client running for the demo, or restart with:

   ```bash
   NEXT_PUBLIC_ORCHESTRATOR_URL=http://127.0.0.1:18080 \
   NEXT_PUBLIC_SOCKET_URL=http://127.0.0.1:18080 \
   pnpm --filter @aetherville/client exec next dev -H 0.0.0.0 -p 3000
   ```

2. Open:

   - Live: `http://127.0.0.1:3000/`
   - Replay: `http://127.0.0.1:3000/replay`

3. During the presentation, truthfully state that real ML workloads are upgrade
   paths and that the approved demo uses deterministic stubs/fallbacks.
4. Optional post-demo improvement: add a compatibility alias for vision
   `/api/v1/health` only if consumers require that path; it is not required for
   the current approved demo.
