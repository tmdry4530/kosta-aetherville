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
        if category == "infrastructure":
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
        if any(keyword in text for keyword in ("관계", "친구", "대화")) or any(
            keyword in lowered for keyword in ("relationship", "friend", "rival")
        ):
            return "relationship"
        if any(keyword in text for keyword in ("시민", "사람", "민준", "서연")) or any(
            keyword in lowered for keyword in ("person", "citizen")
        ):
            return "person"
        if any(keyword in text for keyword in ("도로", "다리", "신호", "정체")) or any(
            keyword in lowered for keyword in ("road", "bridge", "traffic", "infrastructure")
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
        return GodCommandEffect(
            category="person",
            active_event="person intervention",
            event=EventPayload(
                kind="person_updated",
                message=f"Person command applied: {text}",
                entity_id="c01",
                metadata={"category": "person", "citizen_id": "c01"},
            ),
            memories=[
                MemoryInjection(
                    citizen_id="c01",
                    text=f"Personal intervention remembered: {text}",
                    tags=["god-mode", "person"],
                )
            ],
        )

    @staticmethod
    def _relationship_effect(text: str) -> GodCommandEffect:
        return GodCommandEffect(
            category="relationship",
            active_event="relationship intervention",
            event=EventPayload(
                kind="relationship_changed",
                message=f"Relationship command applied: {text}",
                entity_id="c01",
                metadata={"category": "relationship", "source": "c01", "target": "c02"},
            ),
            memories=[
                MemoryInjection(
                    citizen_id="c01",
                    text=f"Relationship with c02 changed: {text}",
                    tags=["god-mode", "relationship", "c02"],
                ),
                MemoryInjection(
                    citizen_id="c02",
                    text=f"Relationship with c01 changed: {text}",
                    tags=["god-mode", "relationship", "c01"],
                ),
            ],
        )
