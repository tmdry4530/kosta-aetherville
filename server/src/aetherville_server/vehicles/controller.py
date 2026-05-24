"""Deterministic vehicle path following and perception fusion."""

from __future__ import annotations

import math
from typing import Literal

from aetherville_schemas import Vec3, VehicleCameraFrame, VehicleState, YoloDetection
from aetherville_server.vehicles.pathfinding import GridPoint, astar_path
from aetherville_server.vehicles.trips import TripManager


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

    def vehicle_states(self, tick: int, running: bool) -> list[VehicleState]:
        pos, rot = self._pose_at_tick(tick)
        detections = mock_vehicle_detections(tick)
        hazard = any(
            detection.label == "pedestrian"
            or detection.traffic_light_state == "red"
            for detection in detections
        )
        speed = 0.0 if not running else (0.9 if hazard else 4.2)
        return [
            VehicleState(
                id="v01",
                type="taxi",
                pos=pos,
                rot=rot,
                speed=speed,
                passenger_id="c01",
                destination=self.path[-1],
                yolo_detections=detections,
            )
        ]

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
