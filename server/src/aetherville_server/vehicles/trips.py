"""Trip manager skeleton for assigning demo passengers to vehicles."""

from __future__ import annotations

from aetherville_schemas import TripState, Vec3


class TripManager:
    """In-memory trip state for the first vehicle/vision slice."""

    def __init__(self) -> None:
        self._trips: dict[str, TripState] = {}

    def ensure_demo_trip(self, path: list[Vec3]) -> TripState:
        trip = self._trips.get("trip_001")
        if trip is not None:
            return trip
        trip = TripState(
            id="trip_001",
            passenger_id="c01",
            vehicle_id="v01",
            origin=path[0],
            destination=path[-1],
            status="enroute",
            path=path,
        )
        self._trips[trip.id] = trip
        return trip

    def list_trips(self) -> list[TripState]:
        return list(self._trips.values())
