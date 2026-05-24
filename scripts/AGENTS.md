# scripts/AGENTS.md

## Scope

Automation scripts:

- persona generation
- city map generation
- YOLO auto-labeling/training
- traffic PPO training
- latency benchmarks
- deployment helpers

## Rules

- Scripts must support `--dry-run` when they touch remote systems or create/delete many files.
- Long-running scripts must log progress.
- Model/data outputs must go to ignored artifact directories unless explicitly documented.
- Avoid hardcoded absolute paths.
