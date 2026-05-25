"""God Mode text command dispatcher.

The dispatcher is intentionally deterministic and rule-based for the demo.  It
keeps command categories stable while the future voice/STT path and LLM command
parser mature.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

from aetherville_schemas import EventPayload, GodCommand

GodCommandCategory = Literal["environment", "event", "person", "infrastructure", "relationship"]

NAME_TO_CITIZEN_ID = {
    "민지": "c01",
    "민수": "c02",
    "서연": "c03",
    "도윤": "c04",
    "하린": "c05",
    "지호": "c06",
    "민준": "c07",
}


@dataclass(frozen=True)
class MemoryInjection:
    citizen_id: str
    text: str
    tags: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class GodCommandEffect:
    category: GodCommandCategory
    event: EventPayload
    weather: str | None = None
    active_event: str | None = None
    infrastructure_status: str | None = None
    memories: list[MemoryInjection] = field(default_factory=list)


class GodCommandDispatcher:
    """Map text commands into deterministic simulation effects."""

    def dispatch(self, command: GodCommand) -> GodCommandEffect:
        text = command.raw_text.strip()
        lowered = text.lower()
        category = self.classify(text)
        if category == "environment":
            weather = self._weather_from_text(text, lowered)
            return GodCommandEffect(
                category=category,
                weather=weather,
                active_event=f"weather:{weather}",
                event=EventPayload(
                    kind="weather_changed",
                    message=f"Weather changed to {weather}",
                    metadata={"category": category, "weather": weather},
                ),
                memories=[
                    MemoryInjection(
                        citizen_id="c01",
                        text=f"God Mode changed the weather to {weather}",
                        tags=["god-mode", "weather", weather],
                    )
                ],
            )
        if category == "person":
            return self._person_effect(text)
        if category == "relationship":
            return self._relationship_effect(text)
        if "택시" in text or "taxi" in lowered:
            return self._taxi_effect(text)
        if category == "infrastructure":
            if any(keyword in text for keyword in ("정체", "교통량", "혼잡", "막혀")) or any(
                keyword in lowered for keyword in ("traffic jam", "congestion", "jam")
            ):
                return GodCommandEffect(
                    category=category,
                    active_event="traffic congestion",
                    infrastructure_status="traffic congestion active",
                    event=EventPayload(
                        kind="infrastructure_changed",
                        message=f"Traffic congestion surge applied: {text}",
                        metadata={
                            "category": category,
                            "action": "traffic_jam",
                            "status": "traffic congestion active",
                        },
                    ),
                )
            return GodCommandEffect(
                category=category,
                active_event="infrastructure intervention",
                infrastructure_status="reroute active",
                event=EventPayload(
                    kind="infrastructure_changed",
                    message=f"Infrastructure command applied: {text}",
                    metadata={"category": category, "status": "reroute active"},
                ),
            )
        return GodCommandEffect(
            category="event",
            active_event=text,
            event=EventPayload(
                kind="event_injected",
                message=f"City event injected: {text}",
                metadata={"category": "event"},
            ),
        )

    def classify(self, text: str) -> GodCommandCategory:
        lowered = text.lower()
        if any(keyword in text for keyword in ("비", "맑", "눈", "폭우", "날씨")) or any(
            keyword in lowered for keyword in ("rain", "clear", "sun", "weather", "snow")
        ):
            return "environment"
        relationship_keywords = ("관계", "친구", "대화", "만나", "만난", "만날", "만남")
        if any(keyword in text for keyword in relationship_keywords) or any(
            keyword in lowered for keyword in ("relationship", "friend", "rival", "meet")
        ):
            return "relationship"
        if "택시" in text or "taxi" in lowered:
            return "infrastructure"
        if any(keyword in text for keyword in ("시민", "사람", *NAME_TO_CITIZEN_ID.keys())) or any(
            keyword in lowered for keyword in ("person", "citizen")
        ):
            return "person"
        infrastructure_terms = ("도로", "다리", "신호", "정체", "교통량", "혼잡", "막혀", "차량")
        infrastructure_terms_en = (
            "road",
            "bridge",
            "traffic",
            "infrastructure",
            "congestion",
            "jam",
        )
        if any(keyword in text for keyword in infrastructure_terms) or any(
            keyword in lowered for keyword in infrastructure_terms_en
        ):
            return "infrastructure"
        return "event"

    @staticmethod
    def _weather_from_text(text: str, lowered: str) -> str:
        if "비" in text or "폭우" in text or "rain" in lowered:
            return "rain"
        if "눈" in text or "snow" in lowered:
            return "snow"
        return "clear"

    @staticmethod
    def _person_effect(text: str) -> GodCommandEffect:
        citizen_id, citizen_name = _first_named_citizen(text, default=("c01", "민지"))
        return GodCommandEffect(
            category="person",
            active_event="person intervention",
            event=EventPayload(
                kind="person_updated",
                message=f"Person command applied: {text}",
                entity_id=citizen_id,
                metadata={"category": "person", "citizen_id": citizen_id, "name": citizen_name},
            ),
            memories=[
                MemoryInjection(
                    citizen_id=citizen_id,
                    text=f"Personal intervention remembered: {text}",
                    tags=["god-mode", "person", citizen_name],
                )
            ],
        )

    @staticmethod
    def _relationship_effect(text: str) -> GodCommandEffect:
        source_id, source_name = _first_named_citizen(text, default=("c01", "민지"))
        target_id, target_name = _second_named_citizen(
            text,
            source_id=source_id,
            default=("c02", "민수") if source_id != "c02" else ("c01", "민지"),
        )
        is_meeting = (
            "만나" in text
            or "만난" in text
            or "만날" in text
            or "만남" in text
            or "meet" in text.lower()
        )
        action = "meeting" if is_meeting else "relationship"
        message = (
            f"{source_name} and {target_name} are meeting on the sidewalk"
            if is_meeting
            else f"Relationship command applied: {text}"
        )
        return GodCommandEffect(
            category="relationship",
            active_event="citizen meeting" if is_meeting else "relationship intervention",
            event=EventPayload(
                kind="relationship_changed",
                message=message,
                entity_id=source_id,
                metadata={
                    "category": "relationship",
                    "action": action,
                    "source": source_id,
                    "target": target_id,
                    "source_name": source_name,
                    "target_name": target_name,
                },
            ),
            memories=[
                MemoryInjection(
                    citizen_id=source_id,
                    text=f"{source_name} remembered meeting {target_name}: {text}",
                    tags=["god-mode", "relationship", action, target_name],
                ),
                MemoryInjection(
                    citizen_id=target_id,
                    text=f"{target_name} remembered meeting {source_name}: {text}",
                    tags=["god-mode", "relationship", action, source_name],
                ),
            ],
        )

    @staticmethod
    def _taxi_effect(text: str) -> GodCommandEffect:
        citizen_id, citizen_name = _first_named_citizen(text, default=("c01", "민지"))
        return GodCommandEffect(
            category="infrastructure",
            active_event="taxi dispatch",
            event=EventPayload(
                kind="trip_requested",
                message=f"Taxi v01 dispatched for {citizen_name}",
                entity_id="v01",
                metadata={
                    "category": "infrastructure",
                    "action": "taxi_call",
                    "vehicle_id": "v01",
                    "passenger_id": citizen_id,
                    "passenger_name": citizen_name,
                    "command": text,
                },
            ),
            memories=[
                MemoryInjection(
                    citizen_id=citizen_id,
                    text=f"{citizen_name} called taxi v01: {text}",
                    tags=["god-mode", "taxi", "trip_requested", "v01"],
                )
            ],
        )


def _first_named_citizen(text: str, default: tuple[str, str]) -> tuple[str, str]:
    for name, citizen_id in NAME_TO_CITIZEN_ID.items():
        if name in text:
            return citizen_id, name
    return default


def _second_named_citizen(
    text: str, *, source_id: str, default: tuple[str, str]
) -> tuple[str, str]:
    for name, citizen_id in NAME_TO_CITIZEN_ID.items():
        if citizen_id != source_id and name in text:
            return citizen_id, name
    return default
