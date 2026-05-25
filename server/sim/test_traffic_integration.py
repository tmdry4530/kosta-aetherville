from __future__ import annotations

from aetherville_schemas import WorldStatePayload
from aetherville_server.sim import SimulationEngine


def test_simulation_snapshot_uses_traffic_ai_payloads() -> None:
    engine = SimulationEngine()
    engine.step()
    payload = WorldStatePayload.model_validate(engine.snapshot().model_dump())

    assert len(payload.traffic_lights) == 4
    assert {light.id for light in payload.traffic_lights} == {"tl_nw", "tl_ne", "tl_sw", "tl_se"}
    assert all("신호등" in light.display_tags for light in payload.traffic_lights)
    assert len(payload.traffic_forecast) == 3
    assert payload.traffic_forecast[-1].minute_offset == 15
