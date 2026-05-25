"""Deterministic vehicle path following and perception fusion."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Literal

from aetherville_schemas import Vec3, VehicleCameraFrame, VehicleState, YoloDetection
from aetherville_server.vehicles.pathfinding import GridPoint, astar_path
from aetherville_server.vehicles.trips import TripManager

VehicleRoute = tuple[tuple[float, float], ...]

VEHICLE_ROUTES: tuple[VehicleRoute, ...] = (
    ((-6.0, -3.0), (-3.0, -3.0), (0.0, -3.0), (3.0, -3.0), (6.0, -3.0)),
    ((-6.0, 0.0), (-3.0, 0.0), (0.0, 0.0), (0.0, 3.0), (0.0, 6.0)),
    ((3.0, -6.0), (3.0, -3.0), (3.0, 0.0), (6.0, 0.0), (6.0, 3.0)),
)


@dataclass(frozen=True)
class TaxiDispatch:
    vehicle_id: str
    passenger_id: str
    start_xz: tuple[float, float]
    pickup_xz: tuple[float, float]
    requested_tick: int


class VehicleController:
    """Path-following vehicle controller with mock camera detections."""

    def __init__(self) -> None:
        self.grid_path = astar_path(
            (-4, -4),
            (4, 4),
            obstacles={(-1, -1), (-1, 0), (0, -1), (1, 1)},
        )
        self.path = [_grid_to_vec3(point) for point in self.grid_path]
        self.trips = TripManager()
        self.trips.ensure_demo_trip(self.path)
        self._taxi_request: TaxiDispatch | None = None
        self._congestion_until_tick: int | None = None

    def request_taxi(
        self,
        passenger_id: str,
        vehicle_id: str = "v01",
        *,
        pickup_xz: tuple[float, float] | None = None,
        requested_tick: int = 0,
    ) -> None:
        """Dispatch the taxi toward the requested passenger, not just relabel it."""

        start_pos, _ = _pose_on_route(VEHICLE_ROUTES[0], requested_tick * 0.13)
        self._taxi_request = TaxiDispatch(
            vehicle_id=vehicle_id,
            passenger_id=passenger_id,
            start_xz=(start_pos[0], start_pos[2]),
            pickup_xz=pickup_xz or (-0.72, -0.72),
            requested_tick=requested_tick,
        )

    def activate_congestion(self, tick: int, duration_ticks: int = 900) -> None:
        """Make the next demo window visibly congested."""

        self._congestion_until_tick = tick + duration_ticks

    def congestion_active(self, tick: int) -> bool:
        return self._congestion_until_tick is not None and tick < self._congestion_until_tick

    def vehicle_states(
        self,
        tick: int,
        running: bool,
        *,
        learned_speed_factor: float = 1.0,
    ) -> list[VehicleState]:
        states: list[VehicleState] = []
        congested = self.congestion_active(tick)
        learned_speed_factor = min(1.0, max(0.4, learned_speed_factor))
        for index, route in enumerate(VEHICLE_ROUTES):
            vehicle_id = f"v{index + 1:02d}"
            route_speed = (
                (0.035 + index * 0.01)
                if congested
                else (0.13 + index * 0.025) * learned_speed_factor
            )
            pos, rot = _pose_on_route(route, tick * route_speed + index * 2.5)
            detections = mock_vehicle_detections(tick + index * 7)
            hazard = any(
                detection.label == "pedestrian"
                or detection.traffic_light_state == "red"
                for detection in detections
            )
            if not running:
                speed = 0.0
            elif congested:
                speed = 0.45
            elif hazard:
                speed = 0.9 * learned_speed_factor
            else:
                speed = (4.2 + index * 0.35) * learned_speed_factor
            passenger_id: str | None = None
            display_tags = ["차도", f"v{index + 1:02d}"]
            if congested:
                display_tags = ["정체", "저속", *display_tags]
            elif learned_speed_factor < 0.98:
                display_tags = [*display_tags, f"학습저속 {learned_speed_factor:.2f}x"]
            if index == 0:
                display_tags.insert(0, "TAXI")
            if self._taxi_request is not None and self._taxi_request.vehicle_id == vehicle_id:
                passenger_id = self._taxi_request.passenger_id
                pos, rot, taxi_speed, taxi_phase = _taxi_dispatch_pose(
                    self._taxi_request,
                    tick,
                    congested=congested,
                    learned_speed_factor=learned_speed_factor,
                )
                speed = 0.0 if not running else taxi_speed
                display_tags = ["택시 호출", taxi_phase, f"승객 {passenger_id}", *display_tags]
            states.append(
                VehicleState(
                    id=vehicle_id,
                    type="taxi" if index == 0 else "shuttle",
                    pos=pos,
                    rot=rot,
                    speed=speed,
                    passenger_id=passenger_id,
                    destination=[route[-1][0], 0.0, route[-1][1]],
                    yolo_detections=detections,
                    display_tags=display_tags,
                )
            )
        return states

    def camera_frame(self, vehicle_id: str, tick: int) -> VehicleCameraFrame:
        if vehicle_id != "v01":
            raise KeyError(vehicle_id)
        return VehicleCameraFrame(
            vehicle_id=vehicle_id,
            frame_b64=None,
            width=320,
            height=180,
            detections=mock_vehicle_detections(tick),
        )

    def _pose_at_tick(self, tick: int) -> tuple[Vec3, Vec3]:
        if len(self.path) < 2:
            return self.path[0], [0.0, 0.0, 0.0]

        segment_progress = (tick % ((len(self.path) - 1) * 5)) / 5.0
        index = int(segment_progress)
        local = segment_progress - index
        start = self.path[index]
        end = self.path[index + 1]
        pos: Vec3 = [
            round(start[0] + (end[0] - start[0]) * local, 3),
            0.0,
            round(start[2] + (end[2] - start[2]) * local, 3),
        ]
        yaw = math.atan2(end[0] - start[0], end[2] - start[2])
        return pos, [0.0, round(yaw, 3), 0.0]


def mock_vehicle_detections(tick: int) -> list[YoloDetection]:
    """Return deterministic schema-valid detections for camera and vehicle state."""

    traffic_light_state: Literal["red", "green"] = (
        "red" if (tick // 30) % 2 == 1 else "green"
    )
    detections = [
        YoloDetection(
            label="traffic_light",
            confidence=0.91,
            bbox=[236.0, 28.0, 262.0, 82.0],
            traffic_light_state=traffic_light_state,
            distance_m=18.5,
        )
    ]
    if 8 <= tick % 40 <= 18:
        detections.append(
            YoloDetection(
                label="pedestrian",
                confidence=0.87,
                bbox=[118.0, 66.0, 164.0, 170.0],
                traffic_light_state=None,
                distance_m=9.5,
            )
        )
    return detections


def _grid_to_vec3(point: GridPoint) -> Vec3:
    return [float(point[0]), 0.0, float(point[1])]


def _pose_on_route(route: VehicleRoute, progress: float) -> tuple[Vec3, Vec3]:
    segments: list[tuple[tuple[float, float], tuple[float, float], float]] = []
    total_length = 0.0
    for start, end in zip(route, route[1:], strict=False):
        length = math.dist(start, end)
        segments.append((start, end, length))
        total_length += length

    distance = progress % total_length
    for start, end, length in segments:
        if distance <= length:
            local = distance / max(length, 0.001)
            x = start[0] + (end[0] - start[0]) * local
            z = start[1] + (end[1] - start[1]) * local
            yaw = math.atan2(end[0] - start[0], end[1] - start[1])
            return [round(x, 3), 0.0, round(z, 3)], [0.0, round(yaw, 3), 0.0]
        distance -= length

    start, end, _ = segments[-1]
    yaw = math.atan2(end[0] - start[0], end[1] - start[1])
    return [end[0], 0.0, end[1]], [0.0, round(yaw, 3), 0.0]


def _taxi_dispatch_pose(
    dispatch: TaxiDispatch,
    tick: int,
    *,
    congested: bool,
    learned_speed_factor: float = 1.0,
) -> tuple[Vec3, Vec3, float, str]:
    elapsed = max(0, tick - dispatch.requested_tick)
    dispatch_speed = 0.025 if congested else 0.09 * learned_speed_factor
    start = dispatch.start_xz
    pickup = dispatch.pickup_xz
    dropoff = (6.0, -3.0)
    pickup_distance = math.dist(start, pickup)
    distance = elapsed * dispatch_speed

    if distance < pickup_distance:
        pos, rot = _interpolate_xz(start, pickup, distance / max(pickup_distance, 0.001))
        return pos, rot, 0.45 if congested else 2.8 * learned_speed_factor, "민지에게 이동"

    wait_ticks = 70
    arrival_tick = int(math.ceil(pickup_distance / dispatch_speed))
    if elapsed <= arrival_tick + wait_ticks:
        yaw = math.atan2(pickup[0] - start[0], pickup[1] - start[1])
        return [pickup[0], 0.0, pickup[1]], [0.0, round(yaw, 3), 0.0], 0.0, "픽업 대기"

    dropoff_progress = (elapsed - arrival_tick - wait_ticks) * dispatch_speed
    dropoff_distance = math.dist(pickup, dropoff)
    local = min(1.0, dropoff_progress / max(dropoff_distance, 0.001))
    pos, rot = _interpolate_xz(pickup, dropoff, local)
    phase = "민지 탑승" if local < 1.0 else "운행 완료"
    return pos, rot, 0.45 if congested else 3.2 * learned_speed_factor, phase


def _interpolate_xz(
    start: tuple[float, float],
    end: tuple[float, float],
    local: float,
) -> tuple[Vec3, Vec3]:
    clamped = min(1.0, max(0.0, local))
    x = start[0] + (end[0] - start[0]) * clamped
    z = start[1] + (end[1] - start[1]) * clamped
    yaw = math.atan2(end[0] - start[0], end[1] - start[1])
    return [round(x, 3), 0.0, round(z, 3)], [0.0, round(yaw, 3), 0.0]
