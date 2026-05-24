"""Vision service stub for direct-process and Compose health checks.

The M0/M1 service preserves the final HTTP surface without requiring a YOLO
model download. Real ONNX/YOLO inference lands in the vehicles/vision phase.
"""

from __future__ import annotations

from fastapi import FastAPI

from aetherville_schemas import (
    HealthResponse,
    ServiceStatus,
    VisionDetectRequest,
    VisionDetectResponse,
)
from aetherville_server import __version__
from aetherville_server.vehicles.controller import mock_vehicle_detections

app = FastAPI(
    title="Aetherville Vision Service",
    version=__version__,
    docs_url="/docs",
    openapi_url="/openapi.json",
)


def build_health_response() -> HealthResponse:
    return HealthResponse(
        service="vision",
        status="ok",
        version=__version__,
        dependencies=[
            ServiceStatus(
                name="yolo",
                status="stub",
                detail="deterministic mock detections until ONNX/YOLO integration",
            )
        ],
    )


@app.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    return build_health_response()


@app.post("/detect", response_model=VisionDetectResponse)
async def detect(request: VisionDetectRequest) -> VisionDetectResponse:
    tick_raw = request.metadata.get("tick", 0)
    try:
        tick = int(tick_raw) if tick_raw is not None else 0
    except (TypeError, ValueError):
        tick = 0
    return VisionDetectResponse(detections=mock_vehicle_detections(tick))
