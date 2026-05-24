# Goal 02 — Cloud Services Startup

## Objective

Implement Docker Compose and/or direct-process startup for vLLM, vision, orchestrator, Redis, and optional Caddy.

## Scope

- Allowed: `docker-compose*.yml`, `infra/docker/**`, `infra/runpod/**`, `server/**` service entrypoints, `.env.example`, docs.

## Acceptance criteria

- Compose config validates locally.
- Docker path documented.
- Direct process fallback documented.
- Health checks for vLLM/vision/orchestrator/redis.
- RunPod deployment script can sync repo and start selected mode.

## Verification commands

```bash
docker compose -f docker-compose.yml -f docker-compose.cloud.yml config
bash infra/runpod/deploy_over_ssh.sh --dry-run
```

## Completion report

Report:

- changed files
- commands run and results
- blockers
- RunPod status if touched
- next goal
