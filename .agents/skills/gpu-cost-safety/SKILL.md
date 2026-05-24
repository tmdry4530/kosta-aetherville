---
name: gpu-cost-safety
description: Use when starting, stopping, or auditing GPU services, model downloads, and long-running training/inference on RunPod.
---

# GPU Cost Safety

1. Confirm whether RunPod should stay running.
2. Check `nvidia-smi` and service process list.
3. Avoid unnecessary training before playable demo slice.
4. Stop idle services only with explicit approval or documented safe script.
5. Record cost/risk notes in `PROGRESS.md`.
