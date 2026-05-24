# Git Workflow for Codex

- Keep each goal in a separate branch when possible.
- Commit only after tests pass or blocker is documented.
- Suggested branch names:
  - `codex/m0-runpod-bootstrap`
  - `codex/m0-foundation-monorepo`
  - `codex/m1-city-scene`
  - `codex/m2-citizen-agents`
- Do not force-push without explicit user instruction.
- Do not commit generated model files, caches, or RunPod env files.

## Suggested commit message format

```text
feat(m0): bootstrap RunPod backend diagnostics

affected:
- infra/runpod
- codex docs

verification:
- bash infra/runpod/verify_runpod.sh
```
