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


def test_learning_promotes_reward_gated_policy_candidates(tmp_path: Path) -> None:
    learning_path = tmp_path / "learning_state.json"
    engine = SimulationEngine(learning_store=LearningStore(learning_path))

    for command in (
        "교통량 증가시켜",
        "민지가 택시를 불러줘",
        "도시에 비를 내려줘",
        "민수와 하린이 만나게 해줘",
        "교통 지연 때문에 민수가 택시를 불러 민지에게 가게 해줘",
    ):
        engine.execute_god_command(make_command(command))

    learning = engine.learning_status().learning

    assert learning.policy_candidates
    assert learning.promotion_gate.candidate_count >= 1
    assert learning.promotion_gate.last_decision in {"promoted", "rejected"}
    assert learning.policy_candidates[-1].score_after >= 0
    assert any(signal.kind in {"policy_promoted", "policy_rejected"} for signal in learning.signals)

    reloaded = LearningStore(learning_path).snapshot()
    assert reloaded.promotion_gate.candidate_count == learning.promotion_gate.candidate_count
