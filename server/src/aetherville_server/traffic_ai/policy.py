"""PPO policy wrapper with checkpoint fallback to baseline pressure control."""

from __future__ import annotations

import json
from pathlib import Path


class TrafficPolicyWrapper:
    """Load a tiny policy checkpoint if present, otherwise use baseline action."""

    def __init__(self, checkpoint_path: str | Path | None = None) -> None:
        self.checkpoint_path = Path(checkpoint_path) if checkpoint_path else None
        self.mode = "baseline"
        self._preferred_action: int | None = None
        if self.checkpoint_path and self.checkpoint_path.exists():
            payload = json.loads(self.checkpoint_path.read_text(encoding="utf-8"))
            self._preferred_action = int(payload.get("preferred_action", 0))
            self.mode = "checkpoint"

    def select_action(self, observation: dict[str, int]) -> int:
        if self._preferred_action in (0, 1):
            return self._preferred_action
        return 0 if observation["ns_queue"] >= observation["ew_queue"] else 1
