"""Event-scoped city planner that lets vLLM choose bounded simulation actions."""

from __future__ import annotations

import hashlib
import json
import os
import urllib.error
import urllib.request
from typing import Any, Literal, Protocol

from aetherville_schemas import (
    CityActorContext,
    CityAiAction,
    CityAiPlan,
    CityWorldContext,
)

_ALLOWED_ACTIONS = {
    "move_citizen",
    "call_taxi",
    "meet",
    "remember",
    "traffic_surge",
    "set_weather",
    "no_op",
}
_ALLOWED_WEATHER = {"clear", "rain", "snow"}


class CityPlanner(Protocol):
    """Generate a bounded high-level plan from the current city context."""

    def plan(self, context: CityWorldContext) -> CityAiPlan: ...


class DeterministicCityPlanner:
    """Safe local planner used for tests and as a vLLM fallback."""

    source = "rules"

    def plan(self, context: CityWorldContext) -> CityAiPlan:
        citizens = context.citizens
        vehicles = context.vehicles
        plan_index = (context.tick // 120) % 4
        actions: list[CityAiAction]
        summary: str

        if plan_index == 0 and len(citizens) >= 3:
            actor = citizens[2]
            target = citizens[0]
            actions = [
                CityAiAction(
                    type="move_citizen",
                    actor_id=actor.id,
                    destination_actor_id=target.id,
                    label=f"{target.name or target.id}에게 자율 이동",
                    reason=(
                        "fallback city planner keeps citizens reacting to nearby social activity"
                    ),
                ),
                CityAiAction(
                    type="remember",
                    actor_id=actor.id,
                    memory=(
                        f"AI 도시 운영자가 {target.name or target.id} 근처로 "
                        "이동하라고 판단했다."
                    ),
                    reason="record the autonomous movement intent for later reflection",
                ),
            ]
            summary = f"{actor.name or actor.id}가 {target.name or target.id} 근처로 이동"
        elif plan_index == 1 and len(citizens) >= 6 and vehicles:
            actions = [
                CityAiAction(
                    type="call_taxi",
                    actor_id="c06",
                    vehicle_id=vehicles[0].id,
                    destination_actor_id="c05",
                    label="하린에게 이동",
                    reason="fallback city planner schedules a taxi trip between active citizens",
                ),
                CityAiAction(
                    type="meet",
                    actor_id="c06",
                    target_id="c05",
                    after="taxi_arrival",
                    reason="meeting should happen only after taxi arrival",
                ),
            ]
            summary = "지호가 택시로 하린에게 이동"
        elif plan_index == 2:
            actions = [
                CityAiAction(
                    type="traffic_surge",
                    reason="fallback city planner raises traffic pressure for the traffic AI loop",
                )
            ]
            summary = "교통량 증가를 감지하고 신호 AI에 압력 부여"
        else:
            weather: Literal["clear", "rain"] = (
                "rain" if context.weather == "clear" else "clear"
            )
            actions = [
                CityAiAction(
                    type="set_weather",
                    weather=weather,
                    reason="fallback city planner changes weather to keep the environment reactive",
                )
            ]
            summary = f"날씨를 {weather} 상태로 전환"

        return CityAiPlan(
            plan_id=_plan_id("rules", context.tick, summary),
            source="rules",
            confidence=0.62,
            summary=summary,
            actions=actions,
        )


class OpenAICompatibleCityPlanner:
    """Use the RunPod vLLM OpenAI-compatible endpoint for city-level planning.

    vLLM only returns bounded JSON actions. The simulation engine remains the
    executor and validator, so arbitrary model text never mutates state directly.
    """

    source = "vllm"

    def __init__(
        self,
        *,
        base_url: str | None = None,
        model: str | None = None,
        timeout_sec: float | None = None,
        fallback: CityPlanner | None = None,
    ) -> None:
        configured_base_url = (
            base_url or os.getenv("AETHERVILLE_VLLM_URL") or "http://127.0.0.1:8000/v1"
        )
        self.base_url = configured_base_url.rstrip("/")
        self.model = model or os.getenv("AETHERVILLE_LLM_MODEL") or "Qwen/Qwen2.5-14B-Instruct-AWQ"
        self.timeout_sec = timeout_sec if timeout_sec is not None else float(
            os.getenv("AETHERVILLE_CITY_AI_LLM_TIMEOUT_SEC", "7")
        )
        self.fallback = fallback or DeterministicCityPlanner()
        self.fallback_count = 0

    def plan(self, context: CityWorldContext) -> CityAiPlan:
        try:
            payload = _extract_json(self._chat(self._prompt(context)))
            if payload is None:
                raise ValueError("vLLM city planner did not return JSON")
            return _plan_from_payload(payload, context)
        except (OSError, TimeoutError, KeyError, ValueError, urllib.error.URLError):
            self.fallback_count += 1
            fallback_plan = self.fallback.plan(context)
            return fallback_plan.model_copy(
                update={
                    "plan_id": _plan_id("fallback", context.tick, fallback_plan.summary),
                    "summary": f"vLLM fallback: {fallback_plan.summary}",
                }
            )

    def _chat(self, prompt: str) -> str:
        body = {
            "model": self.model,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "You are Project Aetherville's autonomous city director. "
                        "Return only compact JSON using the allowed action schema."
                    ),
                },
                {"role": "user", "content": prompt},
            ],
            "max_tokens": 420,
            "temperature": 0.2,
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
            raise ValueError("empty vLLM city plan")
        return content.strip()

    @staticmethod
    def _prompt(context: CityWorldContext) -> str:
        citizens = [
            {
                "id": actor.id,
                "name": actor.name,
                "pos": actor.pos,
                "status": actor.status,
                "tags": actor.tags[:4],
            }
            for actor in context.citizens[:7]
        ]
        vehicles = [
            {
                "id": actor.id,
                "pos": actor.pos,
                "status": actor.status,
                "tags": actor.tags[:4],
            }
            for actor in context.vehicles[:3]
        ]
        compact_context = {
            "tick": context.tick,
            "time_of_day": context.time_of_day,
            "weather": context.weather,
            "active_event": context.active_event,
            "infrastructure_status": context.infrastructure_status,
            "citizens": citizens,
            "vehicles": vehicles,
            "traffic": context.traffic.model_dump(mode="json"),
            "recent_events": context.recent_events[-6:],
            "learning": context.learning.model_dump(mode="json"),
        }
        return (
            "Plan the next 10-20 seconds of the city. Do not script coordinates frame by frame. "
            "Choose 1-3 safe actions that the simulator can execute. Prefer visible movement, "
            "citizen intent, taxi tasks, traffic pressure, weather, and memory updates.\n"
            "Allowed action types: move_citizen, call_taxi, meet, remember, traffic_surge, "
            "set_weather, no_op. Use actor_id/target_id/destination_actor_id from "
            "the provided IDs. "
            "For taxi-to-meeting, emit call_taxi then meet with after='taxi_arrival'. "
            "For weather, set weather to clear/rain/snow. Keep destination coordinates "
            "inside [-6, 6].\n"
            "Return exactly JSON: {\"summary\": string, \"confidence\": 0..1, "
            "\"actions\": [{\"type\": string, \"actor_id\": string|null, "
            "\"target_id\": string|null, \"vehicle_id\": string|null, "
            "\"destination_actor_id\": string|null, \"destination\": [x,0,z]|null, "
            "\"weather\": string|null, \"memory\": string|null, \"label\": string|null, "
            "\"after\": \"taxi_arrival\"|null, \"reason\": string}]}\n"
            f"City context: {json.dumps(compact_context, ensure_ascii=False)}"
        )


def city_planner_from_env() -> CityPlanner | None:
    mode = os.getenv("AETHERVILLE_CITY_AI_MODE", "disabled").strip().lower()
    if mode in {"off", "disabled", "0", "false", "no"}:
        return None
    if mode in {"vllm", "real", "openai"}:
        return OpenAICompatibleCityPlanner()
    return DeterministicCityPlanner()


def _plan_from_payload(payload: dict[str, Any], context: CityWorldContext) -> CityAiPlan:
    raw_actions = payload.get("actions", [])
    if not isinstance(raw_actions, list):
        raw_actions = []
    actions: list[CityAiAction] = []
    for item in raw_actions[:3]:
        if not isinstance(item, dict):
            continue
        action = _coerce_action(item, context)
        if action is not None:
            actions.append(action)
    if not actions:
        actions = [
            CityAiAction(
                type="no_op",
                reason="vLLM returned no executable city action",
            )
        ]
    summary = str(payload.get("summary", "vLLM city plan")).strip()[:140]
    if not summary:
        summary = "vLLM city plan"
    confidence = _coerce_confidence(payload.get("confidence"))
    return CityAiPlan(
        plan_id=_plan_id("vllm", context.tick, summary),
        source="vllm",
        confidence=confidence,
        summary=summary,
        actions=actions,
    )


def _coerce_action(payload: dict[str, Any], context: CityWorldContext) -> CityAiAction | None:
    action_type = str(payload.get("type", "no_op")).strip().lower()
    if action_type not in _ALLOWED_ACTIONS:
        return None
    citizen_names = _name_to_id(context.citizens)
    actor_id = _resolve_actor(payload.get("actor_id"), citizen_names)
    target_id = _resolve_actor(payload.get("target_id"), citizen_names)
    destination_actor_id = _resolve_actor(payload.get("destination_actor_id"), citizen_names)
    destination = _coerce_destination(payload.get("destination"))
    weather = str(payload.get("weather", "")).strip().lower() or None
    if weather not in _ALLOWED_WEATHER:
        weather = None
    after = payload.get("after")
    after_value = "taxi_arrival" if after == "taxi_arrival" else None
    vehicle_id = str(payload.get("vehicle_id") or "").strip()[:16] or None
    label = str(payload.get("label") or "").strip()[:60] or None
    memory = str(payload.get("memory") or "").strip()[:180] or None
    reason = str(payload.get("reason") or "vLLM selected a bounded city action").strip()[:180]
    return CityAiAction(
        type=action_type,  # type: ignore[arg-type]
        actor_id=actor_id,
        target_id=target_id,
        vehicle_id=vehicle_id,
        destination_actor_id=destination_actor_id,
        destination=destination,
        weather=weather,  # type: ignore[arg-type]
        memory=memory,
        label=label,
        after=after_value,  # type: ignore[arg-type]
        reason=reason or "vLLM selected a bounded city action",
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


def _coerce_confidence(value: Any) -> float:
    try:
        confidence = float(value)
    except (TypeError, ValueError):
        return 0.5
    return max(0.0, min(1.0, confidence))


def _coerce_destination(value: Any) -> list[float] | None:
    if not isinstance(value, list) or len(value) != 3:
        return None
    try:
        x = max(-6.0, min(6.0, float(value[0])))
        z = max(-6.0, min(6.0, float(value[2])))
    except (TypeError, ValueError):
        return None
    return [round(x, 3), 0.0, round(z, 3)]


def _name_to_id(actors: list[CityActorContext]) -> dict[str, str]:
    mapping: dict[str, str] = {}
    for actor in actors:
        mapping[actor.id] = actor.id
        if actor.name:
            mapping[actor.name] = actor.id
    return mapping


def _resolve_actor(value: Any, mapping: dict[str, str]) -> str | None:
    token = str(value or "").strip()
    if not token:
        return None
    return mapping.get(token, token[:16])


def _plan_id(source: str, tick: int, summary: str) -> str:
    digest = hashlib.sha1(f"{source}:{tick}:{summary}".encode()).hexdigest()[:8]
    return f"city_{source}_{tick}_{digest}"
