# Goal 00 — RunPod SSH Bootstrap

## Objective

Verify the rented RunPod instance, establish a safe SSH deployment path, and record the verified direct-process runtime decision for the current pod.

## Scope

- Allowed: `infra/runpod/**`, `codex/RUNPOD_SSH_DEPLOYMENT.md`, `PROGRESS.md`, `TASKS.json`, `SESSION_HANDOFF.md`
- Do not modify application source unless required for health check placeholders and explicitly justified.
- Never commit secrets or private keys.

## Acceptance criteria

- `.env.runpod` template exists and is ignored.
- `verify_runpod.sh` can check SSH, GPU, Python, Node, remote directory, optional public URLs, and the no-Docker direct-process policy.
- Deployment mode decision is recorded in `PROGRESS.md`.
- If SSH or GPU fails, blocker is precise and actionable.
- Docker daemon setup, Docker Compose execution, Docker-in-Docker, and blind Docker retries are not attempted.
- Direct-process runtime is documented.

## Verification commands

```bash
bash infra/runpod/verify_runpod.sh
bash infra/runpod/deploy_over_ssh.sh --dry-run
```

## Completion report

Report:

- changed files
- commands run and results
- blockers
- RunPod status if touched
- next goal

## Suggested `/goal`

```text
/goal Complete .codex/goals/00-runpod-ssh-bootstrap.md exactly. Use env vars only. Do not mark complete until SSH and GPU checks pass or blockers are reported.
```
