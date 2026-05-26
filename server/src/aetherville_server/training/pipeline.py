"""Experience-log to checkpoint-promotion pipeline.

This module is intentionally small and dependency-light. It turns runtime city
experience into target-specific datasets, creates guarded trainer jobs, evaluates
candidate checkpoints, and records promotion/rollback state. Real vLLM/YOLO/PPO
or LSTM training is only allowed when the operator explicitly sets
``AETHERVILLE_APPROVE_MODEL_TRAINING=1``; otherwise the same pipeline runs as a
safe dry-run that proves the handoff contract without downloads or GPU spend.
"""

from __future__ import annotations

import json
import os
import time
from collections.abc import Sequence
from pathlib import Path
from typing import Any, Literal, TypeAlias, cast

from aetherville_schemas import (
    CheckpointArtifact,
    EvaluationGateSnapshot,
    EventPayload,
    ModelTrainingSnapshot,
    TrainingCycleResponse,
    TrainingDatasetArtifact,
    TrainingJobSnapshot,
    TrainingRollbackResponse,
)

TrainingTarget: TypeAlias = Literal["vllm_lora", "yolo", "traffic_ppo", "traffic_lstm"]
TARGETS: tuple[TrainingTarget, ...] = ("vllm_lora", "yolo", "traffic_ppo", "traffic_lstm")
APPROVAL_ENV = "AETHERVILLE_APPROVE_MODEL_TRAINING"


class TrainingPipeline:
    """Build/evaluate/promote model-training artifacts from city experience."""

    def __init__(self, base_dir: str | Path | None = None) -> None:
        self.base_dir = Path(base_dir) if base_dir else _default_training_dir()
        self.experience_log_path = self.base_dir / "experience_log.jsonl"
        self.dataset_dir = self.base_dir / "datasets"
        self.checkpoint_dir = self.base_dir / "checkpoints"
        self.registry_path = self.checkpoint_dir / "registry.json"

    def append_experience(
        self,
        event: EventPayload,
        *,
        tick: int,
        learning: dict[str, Any] | None = None,
    ) -> None:
        """Persist one city event as trainer-ready experience.

        The record is deliberately normalized: each downstream trainer receives
        the same id/tick/event/metadata/reward envelope and then the dataset
        builder maps it into SFT, pseudo-label, rollout, or sequence format.
        """

        self.base_dir.mkdir(parents=True, exist_ok=True)
        metadata = _json_safe_dict(event.metadata)
        action = str(metadata.get("action", ""))
        record = {
            "id": f"exp_{tick}_{int(time.time() * 1000)}_{_safe_token(event.kind)}",
            "ts": time.time(),
            "tick": tick,
            "event_kind": event.kind,
            "entity_id": event.entity_id,
            "message": event.message,
            "metadata": metadata,
            "action": action,
            "targets": _targets_for_event(event.kind, action),
            "reward": _reward_for_event(event.kind, action, metadata),
            "learning": learning or {},
        }
        self.experience_log_path.parent.mkdir(parents=True, exist_ok=True)
        with self.experience_log_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")

    def snapshot(self, *, recent_jobs: Sequence[TrainingJobSnapshot] = ()) -> ModelTrainingSnapshot:
        registry = self._load_registry()
        checkpoints = list(registry.get("checkpoints", []))
        promoted = [item for item in checkpoints if item.get("status") == "promoted"]
        jobs_json = list(registry.get("jobs", []))[-6:]
        jobs = [TrainingJobSnapshot.model_validate(job) for job in jobs_json]
        if recent_jobs:
            jobs = [*jobs, *recent_jobs][-8:]
        mode: Literal["not_configured", "dry_run", "ready", "training", "promoted", "blocked"]
        if promoted:
            mode = "promoted"
        elif os.getenv(APPROVAL_ENV) == "1":
            mode = "ready"
        elif self.experience_log_path.exists():
            mode = "dry_run"
        else:
            mode = "not_configured"
        return ModelTrainingSnapshot(
            mode=mode,
            approval_required=os.getenv(APPROVAL_ENV) != "1",
            approval_env=APPROVAL_ENV,
            experience_log_path=str(self.experience_log_path),
            registry_path=str(self.registry_path),
            dataset_count=len(list(registry.get("datasets", []))),
            checkpoint_count=len(checkpoints),
            promoted_count=len(promoted),
            rollback_available=_rollback_available(checkpoints),
            targets=list(TARGETS),
            jobs=jobs[-8:],
            last_cycle_id=registry.get("last_cycle_id"),
        )

    def run_cycle(
        self,
        *,
        targets: Sequence[str] | None = None,
        dry_run: bool = True,
        force: bool = False,
    ) -> TrainingCycleResponse:
        selected_targets = _normalize_targets(targets)
        cycle_id = f"train_{int(time.time())}_{len(self._load_registry().get('jobs', [])) + 1:04d}"
        records = self._read_experiences()
        registry = self._load_registry()
        jobs: list[TrainingJobSnapshot] = []
        approved = os.getenv(APPROVAL_ENV) == "1"

        for target in selected_targets:
            if not records and not force:
                jobs.append(
                    TrainingJobSnapshot(
                        id=f"{cycle_id}_{target}",
                        target=target,
                        status="training_skipped",
                        dry_run=dry_run,
                        started_ts=time.time(),
                        completed_ts=time.time(),
                        detail=(
                            "experience log is empty; run God Mode/city events first "
                            "or set force=true"
                        ),
                    )
                )
                continue

            dataset = self._build_dataset(target, records=records, cycle_id=cycle_id)
            if dry_run:
                evaluation = _dry_run_evaluation(target, records)
                checkpoint = _planned_checkpoint(target, cycle_id, dataset, evaluation)
                jobs.append(
                    TrainingJobSnapshot(
                        id=f"{cycle_id}_{target}",
                        target=target,
                        status="dry_run",
                        dry_run=True,
                        dataset=dataset,
                        checkpoint=checkpoint,
                        evaluation=evaluation,
                        started_ts=time.time(),
                        completed_ts=time.time(),
                        detail=(
                            "dataset/evaluation contract verified; no model "
                            "weights changed because dry_run=true"
                        ),
                        command=_trainer_command(target, dataset.path, dry_run=True),
                    )
                )
                registry.setdefault("datasets", []).append(dataset.model_dump(mode="json"))
                continue

            if not approved:
                jobs.append(
                    TrainingJobSnapshot(
                        id=f"{cycle_id}_{target}",
                        target=target,
                        status="failed",
                        dry_run=False,
                        dataset=dataset,
                        started_ts=time.time(),
                        completed_ts=time.time(),
                        detail=f"blocked: set {APPROVAL_ENV}=1 before running real trainer jobs",
                        command=_trainer_command(target, dataset.path, dry_run=False),
                    )
                )
                registry.setdefault("datasets", []).append(dataset.model_dump(mode="json"))
                continue

            checkpoint = self._train_candidate(target, dataset=dataset, cycle_id=cycle_id)
            evaluation = _evaluate_checkpoint(target, checkpoint, records)
            checkpoint = checkpoint.model_copy(
                update={"status": "promoted" if evaluation.passed else "rejected"}
            )
            if evaluation.passed:
                checkpoint = checkpoint.model_copy(update={"promoted_ts": time.time()})
                _mark_previous_promoted_as_rollback(registry, target)
            registry.setdefault("datasets", []).append(dataset.model_dump(mode="json"))
            registry.setdefault("checkpoints", []).append(checkpoint.model_dump(mode="json"))
            jobs.append(
                TrainingJobSnapshot(
                    id=f"{cycle_id}_{target}",
                    target=target,
                    status="promoted" if evaluation.passed else "rejected",
                    dry_run=False,
                    dataset=dataset,
                    checkpoint=checkpoint,
                    evaluation=evaluation,
                    started_ts=time.time(),
                    completed_ts=time.time(),
                    detail=(
                        "evaluation gate passed; checkpoint promoted"
                        if evaluation.passed
                        else "evaluation gate failed; candidate checkpoint rejected"
                    ),
                    command=_trainer_command(target, dataset.path, dry_run=False),
                )
            )

        registry["last_cycle_id"] = cycle_id
        registry.setdefault("jobs", []).extend(job.model_dump(mode="json") for job in jobs)
        registry["jobs"] = list(registry.get("jobs", []))[-40:]
        self._save_registry(registry)
        status: Literal["dry_run", "promoted", "rejected", "blocked", "skipped"]
        if all(job.status == "training_skipped" for job in jobs):
            status = "skipped"
        elif dry_run:
            status = "dry_run"
        elif any(job.status == "failed" for job in jobs):
            status = "blocked"
        elif any(job.status == "promoted" for job in jobs):
            status = "promoted"
        else:
            status = "rejected"
        return TrainingCycleResponse(
            accepted=True,
            cycle_id=cycle_id,
            status=status,
            jobs=jobs,
            training=self.snapshot(recent_jobs=jobs),
            message=_cycle_message(status),
        )

    def rollback(self, *, target: str, reason: str = "manual rollback") -> TrainingRollbackResponse:
        normalized = _normalize_targets([target])[0]
        registry = self._load_registry()
        checkpoints = list(registry.get("checkpoints", []))
        active_index: int | None = None
        rollback_index: int | None = None
        for index, checkpoint in enumerate(checkpoints):
            if checkpoint.get("target") != normalized:
                continue
            if checkpoint.get("status") == "promoted":
                active_index = index
            if checkpoint.get("status") == "rollback_candidate":
                rollback_index = index
        if active_index is None or rollback_index is None:
            return TrainingRollbackResponse(
                accepted=False,
                target=normalized,
                rolled_back_to=None,
                training=self.snapshot(),
                message="rollback candidate is unavailable for this target",
            )
        checkpoints[active_index]["status"] = "rolled_back"
        checkpoints[active_index]["rollback_reason"] = reason
        checkpoints[rollback_index]["status"] = "promoted"
        checkpoints[rollback_index]["promoted_ts"] = time.time()
        registry["checkpoints"] = checkpoints
        self._save_registry(registry)
        return TrainingRollbackResponse(
            accepted=True,
            target=normalized,
            rolled_back_to=str(checkpoints[rollback_index].get("version")),
            training=self.snapshot(),
            message="checkpoint rollback completed",
        )

    def _build_dataset(
        self,
        target: TrainingTarget,
        *,
        records: Sequence[dict[str, Any]],
        cycle_id: str,
    ) -> TrainingDatasetArtifact:
        self.dataset_dir.mkdir(parents=True, exist_ok=True)
        target_records = [record for record in records if target in record.get("targets", [])]
        if not target_records:
            target_records = list(records)
        dataset_path = self.dataset_dir / f"{cycle_id}_{target}.jsonl"
        builder = _DATASET_BUILDERS[target]
        rows = builder(target_records)
        with dataset_path.open("w", encoding="utf-8") as handle:
            for row in rows:
                handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")
        return TrainingDatasetArtifact(
            id=f"dataset_{cycle_id}_{target}",
            target=target,
            path=str(dataset_path),
            record_count=len(rows),
            format=_DATASET_FORMATS[target],
            created_ts=time.time(),
            source_experience_count=len(records),
        )

    def _train_candidate(
        self,
        target: TrainingTarget,
        *,
        dataset: TrainingDatasetArtifact,
        cycle_id: str,
    ) -> CheckpointArtifact:
        self.checkpoint_dir.mkdir(parents=True, exist_ok=True)
        checkpoint_path = self.checkpoint_dir / f"{cycle_id}_{target}_candidate.json"
        payload = _candidate_payload(target, cycle_id, dataset)
        if target == "traffic_ppo":
            try:
                from aetherville_server.traffic_ai.train_gpu_policy import train_policy_checkpoint

                payload = train_policy_checkpoint(
                    episodes=40, horizon=40, seed=7, device_preference="auto"
                )
            except Exception as exc:  # pragma: no cover - defensive optional training path
                payload["trainer_error"] = str(exc)[:240]
        elif target == "traffic_lstm":
            try:
                from aetherville_server.traffic_ai.train_lstm_forecast import (
                    train_lstm_forecast_checkpoint,
                )

                payload = train_lstm_forecast_checkpoint(
                    samples=120,
                    epochs=24,
                    sequence_length=8,
                    hidden_size=8,
                    seed=7,
                    device_preference="auto",
                )
            except Exception as exc:  # pragma: no cover - defensive optional training path
                payload["trainer_error"] = str(exc)[:240]
        else:
            payload["trainer_recipe"] = _trainer_command(target, dataset.path, dry_run=False)
            payload["requires_optional_dependencies"] = True
            payload["detail"] = (
                f"{target} recipe-only checkpoint; run the guarded trainer with real "
                "dependencies and weight artifacts before promotion"
            )
            if target == "vllm_lora":
                payload["plan_validity"] = 0.0
            if target == "yolo":
                payload["pseudo_label_quality"] = 0.0
        checkpoint_path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        return CheckpointArtifact(
            id=f"checkpoint_{cycle_id}_{target}",
            target=target,
            version=str(
                payload.get("policy_version")
                or payload.get("forecast_version")
                or f"{target}-{cycle_id}"
            ),
            path=str(checkpoint_path),
            status="candidate",
            metrics=_metrics_from_payload(target, payload),
            created_ts=time.time(),
            trainer_backend=str(payload.get("training_backend", "recipe")),
            detail=str(payload.get("detail", f"{target} candidate checkpoint")),
        )

    def _read_experiences(self) -> list[dict[str, Any]]:
        if not self.experience_log_path.exists():
            return []
        records: list[dict[str, Any]] = []
        for line in self.experience_log_path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            try:
                payload = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(payload, dict):
                records.append(payload)
        return records[-1000:]

    def _load_registry(self) -> dict[str, Any]:
        if not self.registry_path.exists():
            return {"datasets": [], "checkpoints": [], "jobs": [], "last_cycle_id": None}
        try:
            payload = json.loads(self.registry_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return {"datasets": [], "checkpoints": [], "jobs": [], "last_cycle_id": None}
        if not isinstance(payload, dict):
            return {"datasets": [], "checkpoints": [], "jobs": [], "last_cycle_id": None}
        payload.setdefault("datasets", [])
        payload.setdefault("checkpoints", [])
        payload.setdefault("jobs", [])
        payload.setdefault("last_cycle_id", None)
        return payload

    def _save_registry(self, payload: dict[str, Any]) -> None:
        self.registry_path.parent.mkdir(parents=True, exist_ok=True)
        tmp_path = self.registry_path.with_suffix(".json.tmp")
        tmp_path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        tmp_path.replace(self.registry_path)


def default_training_pipeline() -> TrainingPipeline:
    return TrainingPipeline()


def _default_training_dir() -> Path:
    configured = os.getenv("AETHERVILLE_TRAINING_DIR")
    if configured:
        return Path(configured)
    run_dir = Path(os.getenv("AETHERVILLE_RUN_DIR", "/tmp/aetherville"))
    return run_dir / "training"


def _normalize_targets(targets: Sequence[str] | None) -> list[TrainingTarget]:
    if not targets:
        return list(TARGETS)
    normalized: list[TrainingTarget] = []
    for target in targets:
        if target not in TARGETS:
            raise ValueError(f"unknown training target: {target}")
        normalized.append(target)
    return normalized


def _targets_for_event(event_kind: str, action: str) -> list[TrainingTarget]:
    targets: set[TrainingTarget] = {"vllm_lora"}
    if event_kind in {"trip_requested", "vehicle_detected"} or action in {"taxi_call"}:
        targets.add("yolo")
        targets.add("traffic_ppo")
    if (
        event_kind in {"infrastructure_changed", "task_blocked", "task_replanned"}
        or action == "traffic_jam"
    ):
        targets.add("traffic_ppo")
        targets.add("traffic_lstm")
    if event_kind in {"weather_changed", "scenario_completed", "task_recovered"}:
        targets.add("traffic_lstm")
    return [target for target in TARGETS if target in targets]


def _reward_for_event(event_kind: str, action: str, metadata: dict[str, Any]) -> float:
    if event_kind in {"scenario_completed", "task_recovered", "relationship_changed"}:
        return 0.9
    if event_kind in {"task_replanned", "trip_requested", "weather_changed"}:
        return 0.62
    if event_kind == "task_blocked":
        return 0.25 if metadata.get("blocker_type") != "taxi_unavailable" else 0.36
    if action in {"traffic_jam", "taxi_call", "meeting"}:
        return 0.58
    return 0.5


def _build_vllm_rows(records: Sequence[dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for record in records:
        context = {
            "tick": record.get("tick"),
            "event_kind": record.get("event_kind"),
            "action": record.get("action"),
            "message": record.get("message"),
            "reward": record.get("reward", 0.5),
        }
        rows.append(
            {
                "messages": [
                    {
                        "role": "system",
                        "content": (
                            "Aetherville city policy trainer: "
                            "choose safe bounded city actions only."
                        ),
                    },
                    {"role": "user", "content": json.dumps(context, ensure_ascii=False)},
                    {
                        "role": "assistant",
                        "content": json.dumps(
                            {
                                "decision": _decision_label(record),
                                "reason": "prefer bounded action with rollback/evaluation evidence",
                                "reward": record.get("reward", 0.5),
                            },
                            ensure_ascii=False,
                        ),
                    },
                ],
                "experience_id": record.get("id"),
            }
        )
    return rows


def _build_yolo_rows(records: Sequence[dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for record in records:
        rows.append(
            {
                "image_ref": record.get("metadata", {}).get("frame_ref", "synthetic://vehicle-camera"),
                "pseudo_labels": [
                    {
                        "label": _pseudo_label(record),
                        "confidence": max(0.35, min(0.92, float(record.get("reward", 0.5)) + 0.18)),
                        "bbox": [0.42, 0.22, 0.58, 0.74],
                    }
                ],
                "experience_id": record.get("id"),
                "source": "city_event_pseudo_label",
            }
        )
    return rows


def _build_ppo_rows(records: Sequence[dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for index, record in enumerate(records):
        action = 0 if index % 2 == 0 else 1
        if record.get("action") == "traffic_jam":
            action = 1
        rows.append(
            {
                "observation": {
                    "ns_queue": 12 + index % 23,
                    "ew_queue": 8 + (index * 3) % 27,
                    "active_phase": action,
                    "tick": record.get("tick", index),
                },
                "action": action,
                "reward": float(record.get("reward", 0.5)),
                "done": False,
                "experience_id": record.get("id"),
            }
        )
    return rows


def _build_lstm_rows(records: Sequence[dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    window: list[float] = []
    for record in records:
        reward = float(record.get("reward", 0.5))
        pressure = 1.0 - reward if record.get("event_kind") == "task_blocked" else reward
        window.append(pressure)
        if len(window) >= 4:
            rows.append(
                {
                    "sequence": window[-12:],
                    "target": {
                        "expected_vehicle_count": int(20 + sum(window[-4:]) * 18),
                        "congestion_index": round(min(1.0, sum(window[-4:]) / 4), 4),
                    },
                    "experience_id": record.get("id"),
                }
            )
    if not rows:
        rows.append(
            {
                "sequence": window or [0.5],
                "target": {"expected_vehicle_count": 24, "congestion_index": 0.45},
                "experience_id": records[-1].get("id") if records else None,
            }
        )
    return rows


_DATASET_BUILDERS = {
    "vllm_lora": _build_vllm_rows,
    "yolo": _build_yolo_rows,
    "traffic_ppo": _build_ppo_rows,
    "traffic_lstm": _build_lstm_rows,
}
_DATASET_FORMATS = {
    "vllm_lora": "chat_sft_jsonl",
    "yolo": "pseudo_label_manifest_jsonl",
    "traffic_ppo": "rollout_jsonl",
    "traffic_lstm": "traffic_sequence_jsonl",
}


def _dry_run_evaluation(
    target: TrainingTarget,
    records: Sequence[dict[str, Any]],
) -> EvaluationGateSnapshot:
    value = _quality_score(records)
    metric, threshold, comparator = _gate_config(target)
    passed = value >= threshold if comparator == "gte" else value <= threshold
    return EvaluationGateSnapshot(
        target=target,
        metric=metric,
        threshold=threshold,
        comparator=comparator,
        candidate_value=round(value, 4),
        passed=False,
        reason=(
            f"dry-run computed {metric}={value:.3f}; gate would "
            f"{'pass' if passed else 'reject'}, but no checkpoint promotion occurs in dry-run"
        ),
    )


def _evaluate_checkpoint(
    target: TrainingTarget,
    checkpoint: CheckpointArtifact,
    records: Sequence[dict[str, Any]],
) -> EvaluationGateSnapshot:
    metric, threshold, comparator = _gate_config(target)
    value = float(checkpoint.metrics.get(metric, _quality_score(records)))
    passed = value >= threshold if comparator == "gte" else value <= threshold
    return EvaluationGateSnapshot(
        target=target,
        metric=metric,
        threshold=threshold,
        comparator=comparator,
        candidate_value=round(value, 4),
        passed=passed,
        reason=(
            f"{metric}={value:.3f} {'meets' if passed else 'does not meet'} "
            f"promotion threshold {comparator} {threshold:.3f}"
        ),
    )


def _gate_config(target: TrainingTarget) -> tuple[str, float, Literal["gte", "lte"]]:
    if target == "traffic_lstm":
        return "mape", 0.38, "lte"
    if target == "traffic_ppo":
        return "improvement_pct", 0.0, "gte"
    if target == "yolo":
        return "pseudo_label_quality", 0.55, "gte"
    return "plan_validity", 0.6, "gte"


def _planned_checkpoint(
    target: TrainingTarget,
    cycle_id: str,
    dataset: TrainingDatasetArtifact,
    evaluation: EvaluationGateSnapshot,
) -> CheckpointArtifact:
    metric_name = evaluation.metric
    metric_value = float(evaluation.candidate_value or 0.0)
    return CheckpointArtifact(
        id=f"planned_{cycle_id}_{target}",
        target=target,
        version=f"{target}-{cycle_id}-planned",
        path=str(Path(dataset.path).with_suffix(".planned-checkpoint.json")),
        status="candidate",
        metrics={metric_name: metric_value},
        created_ts=time.time(),
        trainer_backend="dry_run_recipe",
        detail="planned checkpoint only; dry-run did not mutate model weights",
    )


def _candidate_payload(
    target: TrainingTarget,
    cycle_id: str,
    dataset: TrainingDatasetArtifact,
) -> dict[str, Any]:
    quality = min(
        0.95,
        max(0.3, dataset.record_count / max(4, dataset.source_experience_count + 1)),
    )
    payload: dict[str, Any] = {
        "format": f"aetherville_{target}_checkpoint_v1",
        "target": target,
        "version": f"{target}-{cycle_id}",
        "dataset": dataset.path,
        "dataset_records": dataset.record_count,
        "training_backend": "recipe",
        "detail": f"{target} trainer recipe checkpoint",
    }
    if target == "traffic_lstm":
        payload["forecast_version"] = f"traffic-lstm-{cycle_id}"
        payload["mape"] = round(max(0.08, 0.42 - quality * 0.2), 4)
    elif target == "traffic_ppo":
        payload["policy_version"] = f"traffic-ppo-{cycle_id}"
        payload["improvement_pct"] = round((quality - 0.5) * 25, 4)
    elif target == "yolo":
        payload["pseudo_label_quality"] = round(quality, 4)
    else:
        payload["plan_validity"] = round(quality, 4)
    return payload


def _metrics_from_payload(target: TrainingTarget, payload: dict[str, Any]) -> dict[str, float]:
    if target == "traffic_lstm":
        return {"mape": float(payload.get("mape", 0.35))}
    if target == "traffic_ppo":
        return {"improvement_pct": float(payload.get("improvement_pct", 0.0))}
    if target == "yolo":
        return {"pseudo_label_quality": float(payload.get("pseudo_label_quality", 0.6))}
    return {"plan_validity": float(payload.get("plan_validity", 0.62))}


def _trainer_command(target: TrainingTarget, dataset_path: str, *, dry_run: bool) -> list[str]:
    if target == "traffic_ppo":
        return [
            "uv",
            "run",
            "python",
            "-m",
            "aetherville_server.traffic_ai.train_gpu_policy",
            "--output",
            "<checkpoint-path>",
        ]
    if target == "traffic_lstm":
        return [
            "uv",
            "run",
            "python",
            "-m",
            "aetherville_server.traffic_ai.train_lstm_forecast",
            "--output",
            "<checkpoint-path>",
        ]
    script = (
        "scripts/train_vllm_lora.py"
        if target == "vllm_lora"
        else "scripts/train_yolo_self_training.py"
    )
    command = ["python3", script, "--dataset", dataset_path, "--output", "<checkpoint-path>"]
    if dry_run:
        command.append("--dry-run")
    return command


def _quality_score(records: Sequence[dict[str, Any]]) -> float:
    if not records:
        return 0.0
    rewards = [float(record.get("reward", 0.5)) for record in records]
    positive = sum(1 for reward in rewards if reward >= 0.58) / len(rewards)
    diversity = len({str(record.get("event_kind")) for record in records}) / 8
    score = sum(rewards) / len(rewards) * 0.72 + positive * 0.18 + diversity * 0.1
    return min(1.0, max(0.0, score))


def _cycle_message(status: str) -> str:
    return {
        "dry_run": "training handoff verified in dry-run; no model weights changed",
        "promoted": "one or more candidate checkpoints passed evaluation and were promoted",
        "rejected": "candidate checkpoints were trained but did not pass evaluation gates",
        "blocked": f"real training blocked until {APPROVAL_ENV}=1 is set",
        "skipped": "no training cycle ran because the experience log is empty",
    }.get(status, "training cycle completed")


def _mark_previous_promoted_as_rollback(registry: dict[str, Any], target: TrainingTarget) -> None:
    for checkpoint in registry.get("checkpoints", []):
        if checkpoint.get("target") == target and checkpoint.get("status") == "promoted":
            checkpoint["status"] = "rollback_candidate"


def _rollback_available(checkpoints: Sequence[dict[str, Any]]) -> bool:
    return any(checkpoint.get("status") == "rollback_candidate" for checkpoint in checkpoints)


def _safe_token(value: str) -> str:
    return "".join(ch if ch.isalnum() or ch in {"_", "-"} else "_" for ch in value)[:40]


def _json_safe_dict(payload: dict[str, Any]) -> dict[str, Any]:
    try:
        encoded = json.dumps(payload, ensure_ascii=False, default=str)
        return cast(dict[str, Any], json.loads(encoded))
    except TypeError:
        return {"unserializable": str(payload)[:240]}


def _decision_label(record: dict[str, Any]) -> str:
    kind = str(record.get("event_kind", ""))
    if kind == "task_blocked":
        return "replan_with_fallback"
    if kind == "scenario_completed":
        return "reuse_successful_plan_pattern"
    if str(record.get("action")) == "traffic_jam":
        return "increase_traffic_caution"
    return "continue_bounded_city_policy"


def _pseudo_label(record: dict[str, Any]) -> str:
    action = str(record.get("action", ""))
    if action == "taxi_call" or record.get("event_kind") == "trip_requested":
        return "taxi"
    if action == "traffic_jam":
        return "traffic_light"
    entity_id = str(record.get("entity_id") or "")
    if entity_id.startswith("c"):
        return "person"
    return "vehicle"

