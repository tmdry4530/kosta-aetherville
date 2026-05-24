# infra/AGENTS.md

## Scope

- RunPod SSH scripts
- Dockerfiles/Compose
- Caddy/TLS config
- deployment docs

## Rules

- No secrets in committed files.
- Prefer idempotent scripts.
- Detect remote capabilities before install/deploy.
- Never assume Docker-in-Docker on RunPod.
- Make dry-run possible where safe.
- Include health checks for every service.

## Verification

```bash
bash infra/runpod/verify_runpod.sh
bash infra/runpod/deploy_over_ssh.sh --dry-run
```
