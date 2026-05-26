# FAILURE_PATTERNS.md

## F-001: Assuming Docker Compose works inside RunPod pod

- Severity: high
- Symptom: `docker: command not found` or `Cannot connect to the Docker daemon`
- Preventive rule: Always run `docker info` before choosing Compose path.
- Enforcement: `infra/runpod/bootstrap_runpod.sh` and `verify_runpod.sh` check Docker availability.

## F-002: Hardcoding RunPod SSH credentials

- Severity: critical
- Symptom: host/key/token appears in committed file or logs
- Preventive rule: Use `.env.runpod` and environment variables only.
- Enforcement: `.env.runpod` must be gitignored in target repo.

## F-003: Marking service complete without external port smoke test

- Severity: high
- Symptom: service works over SSH localhost but browser cannot connect
- Preventive rule: Verify both remote-local and public RunPod port URLs.

## F-004: Schema drift between Python and TypeScript

- Severity: high
- Symptom: backend sends fields the frontend does not parse or vice versa
- Preventive rule: Pydantic is source of truth; run generation and contract tests.

## F-005: Overbuilding models before playable slice

- Severity: medium
- Symptom: time spent tuning RL/YOLO before WebSocket/client demo works
- Preventive rule: Build mock-compatible interfaces first; replace internals later.
