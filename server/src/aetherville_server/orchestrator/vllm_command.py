"""Fallback-safe vLLM interpretation for God Mode text commands."""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any, Literal

from aetherville_schemas import GodCommand

GodCommandCategory = Literal["environment", "event", "person", "infrastructure", "relationship"]
GodCommandAction = Literal[
    "rain",
    "clear",
    "snow",
    "traffic_jam",
    "taxi_call",
    "meeting",
    "memory",
    "person_update",
    "relationship",
    "generic",
]

_ALLOWED_CATEGORIES: set[str] = {
    "environment",
    "event",
    "person",
    "infrastructure",
    "relationship",
}
_ALLOWED_ACTIONS: set[str] = {
    "rain",
    "clear",
    "snow",
    "traffic_jam",
    "taxi_call",
    "meeting",
    "memory",
    "person_update",
    "relationship",
    "generic",
}
_ACTION_CATEGORY: dict[str, str] = {
    "rain": "environment",
    "clear": "environment",
    "snow": "environment",
    "traffic_jam": "infrastructure",
    "taxi_call": "infrastructure",
    "meeting": "relationship",
    "relationship": "relationship",
    "memory": "person",
    "person_update": "person",
    "generic": "event",
}


@dataclass(frozen=True)
class GodCommandInterpretation:
    """Constrained, safe interpretation of a free-form presenter command."""

    category: GodCommandCategory
    action: GodCommandAction
    target: str | None
    confidence: float
    reason: str
    source: Literal["vllm"] = "vllm"
    secondary_actions: tuple[GodCommandAction, ...] = ()

    @property
    def actions(self) -> tuple[GodCommandAction, ...]:
        """Return the deduplicated bounded action sequence requested by vLLM."""

        ordered: list[GodCommandAction] = []
        for action in (self.action, *self.secondary_actions):
            if action not in ordered:
                ordered.append(action)
        return tuple(ordered)


class VllmGodCommandInterpreter:
    """Use the OpenAI-compatible RunPod vLLM endpoint to classify God Mode commands.

    The interpreter never applies effects directly.  It only maps free text into
    the small action vocabulary consumed by the deterministic dispatcher, so an
    invalid/slow/unsafe model answer falls back to the rules path.
    """

    def __init__(
        self,
        *,
        base_url: str | None = None,
        model: str | None = None,
        timeout_sec: float | None = None,
    ) -> None:
        configured_base_url = (
            base_url or os.getenv("AETHERVILLE_VLLM_URL") or "http://127.0.0.1:8000/v1"
        )
        self.base_url = configured_base_url.rstrip("/")
        self.model = model or os.getenv("AETHERVILLE_LLM_MODEL") or "Qwen/Qwen2.5-14B-Instruct-AWQ"
        self.timeout_sec = timeout_sec if timeout_sec is not None else float(
            os.getenv("AETHERVILLE_GOD_MODE_LLM_TIMEOUT_SEC", "6")
        )

    @classmethod
    def from_env(cls) -> VllmGodCommandInterpreter | None:
        mode = os.getenv("AETHERVILLE_GOD_MODE_LLM", "rules").strip().lower()
        if mode not in {"vllm", "real", "openai"}:
            return None
        return cls()

    def interpret(self, command: GodCommand) -> GodCommandInterpretation | None:
        prompt = self._prompt(command.raw_text)
        try:
            content = self._chat(prompt)
            payload = _extract_json(content)
            if payload is None:
                return None
            return _interpret_payload(payload)
        except (OSError, TimeoutError, KeyError, ValueError, urllib.error.URLError):
            return None

    def _chat(self, prompt: str) -> str:
        body = {
            "model": self.model,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "You are Project Aetherville's God Mode command classifier. "
                        "Return only compact JSON. Do not invent new actions. "
                        "Use Korean for the reason field so presenter UI stays audience-ready."
                    ),
                },
                {"role": "user", "content": prompt},
            ],
            "max_tokens": 220,
            "temperature": 0.0,
        }
        request = urllib.request.Request(
            f"{self.base_url}/chat/completions",
            data=json.dumps(body, ensure_ascii=False).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(request, timeout=self.timeout_sec) as response:
            payload = json.loads(response.read().decode("utf-8"))
        content = payload["choices"][0]["message"]["content"]
        if not isinstance(content, str) or not content.strip():
            raise ValueError("empty vLLM command interpretation")
        return content.strip()

    @staticmethod
    def _prompt(raw_text: str) -> str:
        return (
            "Classify the presenter command into one to four safe Aetherville actions.\n"
            "Allowed categories: environment, event, person, infrastructure, relationship.\n"
            "Allowed actions: rain, clear, snow, traffic_jam, taxi_call, meeting, memory, "
            "person_update, relationship, generic.\n"
            "Rules:\n"
            "- rain/clear/snow are weather changes.\n"
            "- traffic_jam means increase congestion/traffic volume.\n"
            "- taxi_call means a citizen requests taxi v01.\n"
            "- meeting means named citizens should meet/talk.\n"
            "- memory/person_update means a citizen receives a remembered intervention.\n"
            "- If several effects are requested, include them in actions in execution order.\n"
            "- Keep actions to at most four items and only use the allowed action strings.\n"
            "- Write reason in concise Korean, not raw English schema commentary.\n"
            "Return exactly JSON with keys: category, action, actions, target, "
            "confidence, reason.\n"
            f"Command: {raw_text}"
        )


def _extract_json(content: str) -> dict[str, Any] | None:
    stripped = content.strip()
    if stripped.startswith("```"):
        stripped = stripped.strip("`").removeprefix("json").strip()
    start = stripped.find("{")
    end = stripped.rfind("}")
    if start < 0 or end <= start:
        return None
    loaded = json.loads(stripped[start : end + 1])
    return loaded if isinstance(loaded, dict) else None


def _interpret_payload(payload: dict[str, Any]) -> GodCommandInterpretation | None:
    raw_category = str(payload.get("category", "event")).strip().lower()
    raw_actions = _coerce_actions(payload)
    primary_action = raw_actions[0] if raw_actions else "generic"
    normalized_category = _ACTION_CATEGORY.get(primary_action, raw_category)
    if normalized_category not in _ALLOWED_CATEGORIES:
        normalized_category = "event"
    confidence = _coerce_confidence(payload.get("confidence"))
    target = payload.get("target")
    if target is not None:
        target = str(target).strip()[:80] or None
    reason = str(payload.get("reason", "vLLM classified the God Mode command")).strip()[:180]
    if not reason:
        reason = "vLLM classified the God Mode command"
    return GodCommandInterpretation(
        category=normalized_category,  # type: ignore[arg-type]
        action=primary_action,  # type: ignore[arg-type]
        target=target,
        confidence=confidence,
        reason=reason,
        secondary_actions=tuple(raw_actions[1:]),  # type: ignore[arg-type]
    )


def _coerce_actions(payload: dict[str, Any]) -> list[str]:
    raw_actions = payload.get("actions")
    candidates: list[Any]
    if isinstance(raw_actions, list):
        candidates = raw_actions
    else:
        candidates = [payload.get("action", "generic")]
    actions: list[str] = []
    for candidate in candidates:
        action = str(candidate).strip().lower()
        if action not in _ALLOWED_ACTIONS:
            continue
        if action not in actions:
            actions.append(action)
        if len(actions) >= 4:
            break
    if not actions:
        actions.append("generic")
    return actions


def _coerce_confidence(value: Any) -> float:
    try:
        confidence = float(value)
    except (TypeError, ValueError):
        return 0.5
    return max(0.0, min(1.0, confidence))
