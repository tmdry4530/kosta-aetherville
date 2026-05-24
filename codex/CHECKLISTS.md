# Checklists

## Pre-edit checklist

- [ ] Read goal file
- [ ] Read `AGENTS.md`
- [ ] Read relevant nested `AGENTS.md`
- [ ] Read `TEST_PLAN.md`
- [ ] Identify allowed paths
- [ ] Identify verification commands

## RunPod checklist

- [ ] `.env.runpod` exists locally and is ignored
- [ ] SSH connects
- [ ] GPU visible
- [ ] Docker availability checked
- [ ] Remote workspace exists
- [ ] Ports exposed in RunPod UI
- [ ] Health checks pass or blockers documented

## Final report checklist

- [ ] Changed files
- [ ] Commands run
- [ ] Pass/fail
- [ ] RunPod services state
- [ ] Metrics if relevant
- [ ] Next goal

## 15-minute demo dry-run checklist

- [ ] Live route `/` renders city state.
- [ ] Replay route `/replay` works without RunPod.
- [ ] Memory, vehicle cam, traffic, and God Mode panels are visible.
- [ ] God Mode text command has a visible state effect.
- [ ] RunPod direct health check is green or fallback route is ready.
- [ ] `docs/metrics-report.md` is current.
