# MASTER_AETHERVILLE_FULL_DELIVERY

## Objective

Complete Project Aetherville from the current repository state through final integrated demo readiness.

The implementation must proceed through every existing goal file in `.codex/goals/` in dependency order, with an implement → verify → fix → document loop at each phase.

## Current known environment

- Goal 00 is complete.
- RunPod SSH connectivity is verified.
- GPU is NVIDIA GeForce RTX 4090.
- Docker daemon is unavailable on the RunPod.
- Cloud-side work must use direct-process fallback unless Docker becomes explicitly available and verified.
- Do not blind retry Docker or Docker Compose.

## Source of truth priority

1. This master goal.
2. Existing `.codex/goals/*.md` files.
3. `SPEC.md`
4. `TEST_PLAN.md`
5. `DECISIONS.md`
6. `TASKS.json`
7. `PROGRESS.md`
8. `SESSION_HANDOFF.md`
9. Project PRD and docs.

If any lower-priority document conflicts with the verified RunPod environment, update the document and proceed with the verified environment.

## Execution order

### Phase 01: Foundation Monorepo
Run:
- `.codex/goals/01-foundation-monorepo.md`

Required outcome:
- pnpm workspace present.
- uv/Python workspace present.
- server/client/shared-schemas scaffolding present.
- FastAPI orchestrator skeleton runnable.
- Next.js/R3F client skeleton runnable.
- direct-process cloud scripts present.

### Phase 02: Cloud Services Direct Process
Run:
- `.codex/goals/02-cloud-services-docker-compose.md`

Adjustment:
- Because Docker is unavailable, implement direct-process equivalents.
- Preserve Docker docs/artifacts only as future deployment artifacts.
- Do not require Docker for current acceptance.

Required outcome:
- vLLM direct-process path documented and scripted.
- orchestrator direct-process path runnable.
- vision service direct-process path runnable or stubbed with clear upgrade path.
- health checks available.

### Phase 03: Shared Schemas API WS
Run:
- `.codex/goals/03-shared-schemas-api-ws.md`

Required outcome:
- Pydantic models for WebSocket envelopes, world state, commands.
- TypeScript types or generated schema path.
- REST and WS contract tests.
- compatibility between server and client.

### Phase 04: Simulation Engine
Run:
- `.codex/goals/04-simulation-engine.md`

Required outcome:
- world tick loop.
- city map model.
- citizens/vehicles/traffic-light state primitives.
- deterministic seed mode.
- server state snapshot API.

### Phase 05: Client City Scene
Run:
- `.codex/goals/05-client-city-scene.md`

Required outcome:
- browser 3D city scene.
- tick/state rendering.
- buildings, roads, basic citizens/vehicles placeholders.
- connection state UI.
- replay or mock-state fallback if cloud unavailable.

### Phase 06: Citizen Agents
Run:
- `.codex/goals/06-citizen-agents.md`

Required outcome:
- persona generation or seeded demo personas.
- plan tree.
- memory stream.
- dialog trigger.
- reflection placeholder or real LLM path.
- memory panel in UI.

### Phase 07: Vehicles & Vision
Run:
- `.codex/goals/07-vehicles-vision.md`

Required outcome:
- vehicle pathfinding and kinematic movement.
- trip manager.
- vehicle camera panel.
- YOLO service path or deterministic simulated detections.
- documented YOLO training/inference upgrade path.
- collision/slowdown demo.

### Phase 08: Traffic AI
Run:
- `.codex/goals/08-traffic-ai.md`

Required outcome:
- traffic environment abstraction.
- baseline traffic-light controller.
- RL policy wrapper with mock/checkpoint fallback.
- traffic forecast panel.
- comparison metrics script.

### Phase 09: God Mode
Run:
- `.codex/goals/09-god-mode.md`

Required outcome:
- text command path.
- voice capture UI if feasible.
- command dispatcher.
- weather/event/person/infrastructure/relation command categories.
- visible effect in world state.
- fallback macro buttons for demo reliability.

### Phase 10: Polish Demo
Run:
- `.codex/goals/10-polish-demo.md`

Required outcome:
- demo scenario script.
- replay mode.
- failure fallback.
- README.
- architecture diagram placeholder or generated artifact.
- demo readiness checklist.

### Phase 99: Final Audit
Run:
- `.codex/goals/99-final-audit.md`

Required outcome:
- full local verification.
- RunPod direct-process verification.
- client/server integration verification.
- replay fallback verification.
- final acceptance checklist.
- final completion report.

## Per-phase loop

For every phase:

1. Read the phase goal file.
2. Restate acceptance criteria internally as checklist.
3. Implement the smallest coherent slice.
4. Run phase verification.
5. If verification fails:
   - classify failure as environment, dependency, implementation, test, or requirement conflict.
   - fix implementation/test/dependency failures.
   - do not blind retry the same failing command more than twice.
6. Update:
   - `TASKS.json`
   - `PROGRESS.md`
   - `SESSION_HANDOFF.md`
   - `DECISIONS.md` when an architectural decision changes.
7. Commit only if the repo convention allows it. Otherwise leave a clean final report.
8. Proceed to the next phase without asking the user unless a hard blocker is reached.

## Verification minimums

At minimum, attempt:

- Python syntax/import checks.
- Python unit tests where present.
- TypeScript typecheck where present.
- frontend lint/build where present.
- shared schema validation.
- API health check.
- WebSocket smoke test.
- client can connect to server or mock/replay state.
- RunPod SSH verification.
- direct-process RunPod service start smoke test.
- final integration smoke script.

If a command cannot run, record:
- command
- reason
- stderr summary
- missing dependency or environment blocker
- next concrete fix.

## Hard blockers

Stop and report only if:

- secret/API key is required and missing.
- RunPod is unreachable after documented retry.
- GPU is unavailable.
- disk space is insufficient and cleanup is unsafe.
- package install requires destructive system changes.
- a requirement requires paid external service not configured.
- human-only verification is unavoidable.
- continuing would risk leaking secrets or corrupting repo state.

## Safety rules

- Never print secrets.
- Never commit `.env.runpod`.
- Never expose private SSH key paths.
- Never modify unrelated files.
- Never delete user work.
- Never weaken tests to get green.
- Never mark complete based only on proxy signals.
- Do not use Docker unless Docker daemon is verified working.

## Final completion criteria

Master goal is complete only when:

- All phase goals are complete or explicitly marked with justified blocker.
- Final integration smoke test has been attempted.
- Client can show a playable city state.
- Server can emit world state.
- RunPod direct-process path is documented and smoke-tested.
- Demo fallback/replay mode exists.
- Final report includes:
  1. changed files
  2. phase-by-phase results
  3. verification commands
  4. passed checks
  5. failed/skipped checks
  6. RunPod status
  7. residual risks
  8. exact commands to run the demo