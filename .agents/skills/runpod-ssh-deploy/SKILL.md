---
name: runpod-ssh-deploy
description: Use when deploying or verifying Aetherville backend services over SSH on RunPod. Checks SSH, GPU, Docker availability, direct-process fallback, and service health.
---

# RunPod SSH Deploy Skill

1. Read `codex/RUNPOD_SSH_DEPLOYMENT.md`.
2. Load variables from `infra/runpod/.env.runpod` without printing secrets.
3. Run `bash infra/runpod/verify_runpod.sh`.
4. If Docker daemon works, prefer Compose path.
5. If Docker daemon does not work, document direct-process fallback.
6. Verify service health from inside the pod and from local public RunPod URLs when available.
7. Update `PROGRESS.md` and `SESSION_HANDOFF.md` with exact state.
