"""Vision service for direct-process health checks and optional real YOLO."""

from __future__ import annotations

import base64
import importlib.util
import os
import threading
from io import BytesIO
from typing import Any, Literal

from fastapi import FastAPI

from aetherville_schemas import (
    HealthResponse,
    ServiceStatus,
    VisionDetectRequest,
    VisionDetectResponse,
    YoloDetection,
)
from aetherville_server import __version__
from aetherville_server.vehicles.controller import mock_vehicle_detections

app = FastAPI(
    title="Aetherville Vision Service",
    version=__version__,
    docs_url="/docs",
    openapi_url="/openapi.json",
)


class RealYoloUnavailable(RuntimeError):
    """Raised when the optional real YOLO runtime is not installed or loadable."""


class RealYoloDetector:
    """Lazy Ultralytics YOLO wrapper.

    Ultralytics' official Python API loads a model with `YOLO("yolo11n.pt")`
    and calls that model for prediction.  This wrapper keeps that dependency
    optional so the direct-process service can still run in deterministic mock
    mode on machines without YOLO weights.
    """

    def __init__(self) -> None:
        try:
            from ultralytics import YOLO  # type: ignore[import-not-found]
        except ImportError as exc:
            raise RealYoloUnavailable("ultralytics package is not installed") from exc

        model_name = os.getenv("AETHERVILLE_YOLO_MODEL", "yolo11n.pt")
        self.model_name = model_name
        self.device = os.getenv("AETHERVILLE_YOLO_DEVICE", "0")
        self.image_size = int(os.getenv("AETHERVILLE_YOLO_IMGSZ", "640"))
        self.confidence = float(os.getenv("AETHERVILLE_YOLO_CONF", "0.25"))
        allowed_raw = os.getenv(
            "AETHERVILLE_YOLO_ALLOWED_LABELS",
            "person,bicycle,car,motorcycle,bus,truck,traffic light,stop sign",
        )
        self.allowed_labels = {
            label.strip().lower() for label in allowed_raw.split(",") if label.strip()
        }
        self._model = YOLO(model_name)

    def detect(self, request: VisionDetectRequest) -> list[YoloDetection]:
        image = _decode_frame(request.frame_b64)
        results = self._model(
            image,
            imgsz=self.image_size,
            conf=self.confidence,
            device=self.device,
            verbose=False,
        )
        if not results:
            return []

        result = results[0]
        names = getattr(result, "names", {}) or {}
        boxes = getattr(result, "boxes", None)
        if boxes is None:
            return []

        detections: list[YoloDetection] = []
        for box in boxes:
            xyxy = box.xyxy[0].tolist()
            confidence = float(box.conf[0])
            class_id = int(box.cls[0])
            label = str(names.get(class_id, class_id))
            if self.allowed_labels and label.lower() not in self.allowed_labels:
                continue
            detections.append(
                YoloDetection(
                    label=label,
                    confidence=round(confidence, 4),
                    bbox=[round(float(value), 2) for value in xyxy],
                    traffic_light_state="unknown" if label == "traffic light" else None,
                    distance_m=None,
                )
            )
        return detections


_DETECTOR: RealYoloDetector | None = None
_DETECTOR_LOCK = threading.Lock()


def vision_mode() -> str:
    return os.getenv("AETHERVILLE_VISION_MODE", "mock").lower()


def get_real_detector() -> RealYoloDetector:
    global _DETECTOR
    if _DETECTOR is None:
        with _DETECTOR_LOCK:
            if _DETECTOR is None:
                _DETECTOR = RealYoloDetector()
    return _DETECTOR


def build_health_response() -> HealthResponse:
    mode = vision_mode()
    yolo_available = importlib.util.find_spec("ultralytics") is not None
    yolo_status: Literal["ok", "degraded", "down", "missing", "stub"] = (
        "ok" if mode == "real" and yolo_available else "stub"
    )
    yolo_model = os.getenv("AETHERVILLE_YOLO_MODEL", "yolo11n.pt")
    yolo_detail = (
        f"real Ultralytics YOLO enabled with model {yolo_model}"
        if mode == "real" and yolo_available
        else "deterministic mock detections; set AETHERVILLE_VISION_MODE=real for YOLO"
    )
    if mode == "real" and not yolo_available:
        yolo_status = "degraded"
        yolo_detail = "AETHERVILLE_VISION_MODE=real but ultralytics is not installed"

    return HealthResponse(
        service="vision",
        status="ok" if yolo_status != "degraded" else "degraded",
        version=__version__,
        dependencies=[
            ServiceStatus(
                name="yolo",
                status=yolo_status,
                detail=yolo_detail,
            )
        ],
    )


@app.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    return build_health_response()


@app.post("/detect", response_model=VisionDetectResponse)
async def detect(request: VisionDetectRequest) -> VisionDetectResponse:
    if vision_mode() == "real":
        try:
            detections = get_real_detector().detect(request)
            return VisionDetectResponse(mode="real", detections=detections)
        except (RealYoloUnavailable, OSError, ValueError, RuntimeError):
            # Preserve the contract and demo path if optional real inference is
            # not available or the supplied frame cannot be decoded.
            pass

    tick_raw = request.metadata.get("tick", 0)
    try:
        tick = int(tick_raw) if tick_raw is not None else 0
    except (TypeError, ValueError):
        tick = 0
    return VisionDetectResponse(detections=mock_vehicle_detections(tick))


def _decode_frame(frame_b64: str | None) -> Any:
    try:
        from PIL import Image, ImageDraw  # type: ignore[import-not-found]
    except ImportError as exc:
        raise RealYoloUnavailable("Pillow is required for real YOLO frame decode") from exc

    if frame_b64:
        raw = base64.b64decode(frame_b64)
        return Image.open(BytesIO(raw)).convert("RGB")

    image = Image.new("RGB", (640, 384), color=(25, 32, 43))
    draw = ImageDraw.Draw(image)
    draw.rectangle((0, 230, 640, 384), fill=(40, 40, 44))
    draw.rectangle((268, 80, 294, 180), fill=(18, 18, 18))
    draw.ellipse((274, 92, 288, 106), fill=(255, 0, 0))
    draw.ellipse((274, 118, 288, 132), fill=(255, 200, 0))
    draw.ellipse((274, 144, 288, 158), fill=(0, 220, 80))
    draw.rectangle((110, 178, 155, 314), fill=(235, 120, 180))
    draw.rectangle((330, 210, 515, 295), fill=(238, 185, 56))
    draw.ellipse((354, 280, 395, 322), fill=(5, 8, 12))
    draw.ellipse((450, 280, 491, 322), fill=(5, 8, 12))
    return image
