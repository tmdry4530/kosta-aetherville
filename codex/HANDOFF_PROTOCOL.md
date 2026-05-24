# Handoff Protocol

Before ending a long Codex session:

1. Update `PROGRESS.md`.
2. Update `TASKS.json` statuses.
3. Rewrite `SESSION_HANDOFF.md` with current state, tests, blockers, next files.
4. If a decision changed, update `DECISIONS.md`.
5. If a repeated failure occurred, update `FAILURE_PATTERNS.md`.

`SESSION_HANDOFF.md` must never be a generic summary. It must let a fresh Codex session resume with minimal ambiguity.
