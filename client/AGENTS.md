# client/AGENTS.md

## Scope

Local browser client:

- Next.js App Router
- R3F/Three.js scene
- side panels
- Zustand stores
- Socket.IO client
- replay mode

## Rules

- The browser must not require a local GPU.
- Use WebSocket state as source of truth.
- Keep connection/reconnect state visible.
- UI panels must tolerate missing/mock data.
- God Mode must support text fallback even when voice exists.
- Replay mode is mandatory for demo resilience.

## Verification

```bash
pnpm lint
pnpm typecheck
pnpm test
pnpm test:e2e
```
