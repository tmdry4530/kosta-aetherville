# Codex Operating Manual

## Standard loop

1. Read the relevant goal file.
2. `/plan` first if the goal touches more than one module.
3. Implement the smallest vertical slice.
4. Run verification commands.
5. Update `TASKS.json`, `PROGRESS.md`, `SESSION_HANDOFF.md`.
6. Report changed files, tests, RunPod status, and blockers.

## When to stop and ask/report

- RunPod SSH fails after basic diagnostics.
- Docker and direct-process paths are both impossible.
- A model download requires credentials not present.
- A goal requires a paid domain/TLS setup not provided.
- A test fails twice for the same reason.
- A requested change would contradict `DECISIONS.md`.

## Recommended goal cadence

- One `/goal` per milestone slice.
- Never combine M2 citizens + M3 vehicles + M4 traffic in one goal.
- Use `.codex/goals/99-final-audit.md` before demo freeze.
