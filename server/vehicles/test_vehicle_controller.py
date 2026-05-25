from __future__ import annotations

from aetherville_schemas import VehicleCameraFrame, VehicleState
from aetherville_server.vehicles import VehicleController


def test_vehicle_follows_path_and_embeds_detections() -> None:
    controller = VehicleController()

    first = controller.vehicle_states(tick=0, running=True)[0]
    later = controller.vehicle_states(tick=10, running=True)[0]
    all_vehicles = controller.vehicle_states(tick=0, running=True)

    assert VehicleState.model_validate(first.model_dump()).id == "v01"
    assert len(all_vehicles) == 3
    assert all("차도" in vehicle.display_tags for vehicle in all_vehicles)
    assert first.pos != later.pos
    assert later.yolo_detections


def test_vehicle_slows_for_mock_hazard() -> None:
    controller = VehicleController()

    hazard = controller.vehicle_states(tick=10, running=True)[0]
    clear = controller.vehicle_states(tick=22, running=True)[0]

    assert any(detection.label == "pedestrian" for detection in hazard.yolo_detections)
    assert hazard.speed < clear.speed


def test_taxi_request_adds_visible_vehicle_tag() -> None:
    controller = VehicleController()
    controller.request_taxi("c01", pickup_xz=(0.0, 0.0), requested_tick=0)

    taxi = controller.vehicle_states(tick=3, running=True)[0]
    later = controller.vehicle_states(tick=20, running=True)[0]

    assert taxi.passenger_id == "c01"
    assert taxi.display_tags[0] == "택시 호출"
    assert "민지에게 이동" in taxi.display_tags
    assert taxi.pos != later.pos


def test_congestion_event_slows_and_tags_vehicles() -> None:
    controller = VehicleController()
    normal = controller.vehicle_states(tick=12, running=True)[1]

    controller.activate_congestion(tick=12)
    congested = controller.vehicle_states(tick=12, running=True)[1]

    assert congested.speed < normal.speed
    assert congested.display_tags[:2] == ["정체", "저속"]


def test_learned_speed_factor_slows_future_vehicle_motion() -> None:
    controller = VehicleController()

    normal = controller.vehicle_states(tick=20, running=True)[1]
    learned = controller.vehicle_states(tick=20, running=True, learned_speed_factor=0.8)[1]

    assert learned.speed < normal.speed
    assert "학습저속 0.80x" in learned.display_tags


def test_vehicle_camera_frame_contract() -> None:
    controller = VehicleController()
    frame = controller.camera_frame("v01", tick=10)

    assert VehicleCameraFrame.model_validate(frame.model_dump()).detections
    assert frame.width == 320
