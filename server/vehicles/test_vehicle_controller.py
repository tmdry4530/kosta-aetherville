from __future__ import annotations

from aetherville_schemas import VehicleCameraFrame, VehicleState
from aetherville_server.vehicles import VehicleController


def test_vehicle_follows_path_and_embeds_detections() -> None:
    controller = VehicleController()

    first = controller.vehicle_states(tick=0, running=True)[0]
    later = controller.vehicle_states(tick=10, running=True)[0]

    assert VehicleState.model_validate(first.model_dump()).id == "v01"
    assert first.pos != later.pos
    assert later.yolo_detections


def test_vehicle_slows_for_mock_hazard() -> None:
    controller = VehicleController()

    hazard = controller.vehicle_states(tick=10, running=True)[0]
    clear = controller.vehicle_states(tick=22, running=True)[0]

    assert any(detection.label == "pedestrian" for detection in hazard.yolo_detections)
    assert hazard.speed < clear.speed


def test_vehicle_camera_frame_contract() -> None:
    controller = VehicleController()
    frame = controller.camera_frame("v01", tick=10)

    assert VehicleCameraFrame.model_validate(frame.model_dump()).detections
    assert frame.width == 320
