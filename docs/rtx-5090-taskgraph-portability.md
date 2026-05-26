# RTX 5090 TaskGraph Runtime Portability Notes

Status: Goal 12 local implementation backup prepared for a future 5090 machine.

## What is portable

The repository now contains the TaskGraph planner contract and deterministic fallback implementation needed to move from the current 4090 environment to a future 5090 RunPod/direct-process machine:

- shared Python schemas and generated TypeScript contract for `TaskGraph*`
- deterministic Korean fixture compiler in `server/src/aetherville_server/scenario.py`
- SimulationEngine TaskGraph response/snapshot integration
- Scenario Director UI compatibility for `worldState.task_graph`
- tests proving 10 Korean scenario families, God Mode response exposure, and world-state snapshot exposure

## Local backup artifact

A local archive was created at:

```text
.omx/backups/aetherville-goal12-taskgraph-20260526-045058.tar.gz
.omx/backups/aetherville-goal12-taskgraph-20260526-045058.tar.gz.sha256
```

The archive intentionally excludes secrets and heavyweight generated/runtime folders:

- `.git/`
- `.omx/`
- `.venv/`
- `node_modules/`
- `client/.next/`
- Python/pytest/mypy/ruff caches
- `dogfood-output/`
- `.env`, `.env.*`, and `infra/runpod/.env.runpod`

Create or refresh the archive from the repo root with:

```bash
mkdir -p .omx/backups
tar --exclude='./.git' \
  --exclude='./.omx' \
  --exclude='./.venv' \
  --exclude='./node_modules' \
  --exclude='./client/.next' \
  --exclude='./**/__pycache__' \
  --exclude='./.pytest_cache' \
  --exclude='./.mypy_cache' \
  --exclude='./.ruff_cache' \
  --exclude='./dogfood-output' \
  --exclude='./.env' \
  --exclude='./.env.*' \
  --exclude='./infra/runpod/.env.runpod' \
  -czf .omx/backups/aetherville-goal12-taskgraph-20260526-045058.tar.gz .
sha256sum .omx/backups/aetherville-goal12-taskgraph-20260526-045058.tar.gz > .omx/backups/aetherville-goal12-taskgraph-20260526-045058.tar.gz.sha256
```

## Restore on a 5090 machine

```bash
mkdir -p ~/aetherville-restore
cd ~/aetherville-restore
tar -xzf /path/to/aetherville-goal12-taskgraph-*.tar.gz
```

Then install dependencies without Docker:

```bash
uv sync
pnpm install
python3 packages/shared-schemas/scripts/generate_typescript.py
```

Recreate secrets from a secure source only after extraction. Do not expect them in the archive:

```bash
# create infra/runpod/.env.runpod locally from the secure credential source
# do not commit or print this file
```

## Direct-process 5090 smoke path

On the 5090 RunPod/container, keep the same direct-process policy:

```bash
export AETHERVILLE_VLLM_MODE=mock          # switch to real only after model access is approved
export AETHERVILLE_REDIS_MODE=memory       # or configure external Redis
export AETHERVILLE_VISION_PORT=18001       # verified demo vision port pattern
bash infra/runpod/start_direct_processes.sh
bash infra/runpod/health_check_direct.sh
```

Run Goal 12 contract checks:

```bash
uv run pytest packages/shared-schemas/tests server/orchestrator server/sim
uv run ruff check server packages scripts
uv run mypy server packages
pnpm typecheck
pnpm test
python3 -m json.tool TASKS.json
git diff --check
```

## Truthfulness constraints

- TaskGraph planning is a bounded executable contract, not unverified AGI.
- vLLM may help classify/plan, but deterministic fallback must pass all fixtures.
- The simulation executes validated Python actions; raw LLM text never mutates coordinates directly.
- Keeping the server on can accumulate configured learning/memory state, but it does not train model weights unless a separate training/checkpoint promotion path is implemented and verified.
- Do not run Docker, Docker Compose, Docker-in-Docker, or blind Docker retries on the verified direct-process path.
