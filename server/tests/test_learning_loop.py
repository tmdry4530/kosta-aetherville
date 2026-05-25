from __future__ import annotations

from pathlib import Path

from aetherville_schemas import GodCommand, WorldStatePayload
from aetherville_server.learning import LearningStore
from aetherville_server.sim import SimulationEngine


def make_command(text: str) -> GodCommand:
    return GodCommand(input_modality="text", raw_text=text, user_id="presenter")


def test_god_mode_events_persist_and_affect_learning_snapshot(tmp_path: Path) -> None:
    learning_path = tmp_path / "learning_state.json"
    engine = SimulationEngine(learning_store=LearningStore(learning_path))

    engine.execute_god_command(make_command("교통량 증가시켜"))
    engine.execute_god_command(make_command("민지가 택시를 불러줘"))
    engine.execute_god_command(make_command("도시에 비를 내려줘"))

    state = WorldStatePayload.model_validate(engine.snapshot().model_dump(mode="json"))
    status = engine.learning_status()

    assert learning_path.exists()
    assert state.learning.experience_count >= 3
    assert state.learning.adaptation_epoch >= 1
    assert state.learning.traffic_bias > 0
    assert state.learning.taxi_success_rate > 0.5
    assert status.learning.storage == "json_persistence"
    assert status.upgrade_path
    assert any("AI학습" in tag for tag in state.vehicles[0].display_tags)
    assert any("학습제어" in tag for tag in state.traffic_lights[0].display_tags)

    reloaded = LearningStore(learning_path)
    assert reloaded.snapshot().experience_count == state.learning.experience_count
    assert reloaded.learned_queue_boost() > 0
