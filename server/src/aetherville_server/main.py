"""FastAPI + Socket.IO orchestrator skeleton."""

from __future__ import annotations

import asyncio
import json
import os
import time
import urllib.error
import urllib.request
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any, Literal

import socketio  # type: ignore[import-untyped]
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import ValidationError

from aetherville_schemas import (
    AckPayload,
    CitizenDetailResponse,
    CitizenListResponse,
    DialogueRequest,
    DialogueResponse,
    Envelope,
    EnvelopeType,
    EventPayload,
    GodCommand,
    GodCommandResponse,
    HealthResponse,
    LearningStatusResponse,
    MemoryStreamResponse,
    ReflectionResponse,
    ServiceStatus,
    SimResetRequest,
    SimStatusResponse,
    VehicleCameraFrame,
    VisionDetectRequest,
    VisionDetectResponse,
    VoiceCommandRequest,
    VoiceCommandResponse,
    WorldStatePayload,
)
from aetherville_server import __version__
from aetherville_server.sim import SimulationConfig, SimulationEngine
from aetherville_server.voice import transcriber_from_env


@asynccontextmanager
async def app_lifespan(app: FastAPI) -> AsyncIterator[None]:
    del app
    try:
        yield
    finally:
        await stop_simulation_task()


fastapi_app = FastAPI(
    title="Aetherville Orchestrator",
    version=__version__,
    docs_url="/api/docs",
    openapi_url="/api/openapi.json",
    lifespan=app_lifespan,
)


def parse_cors_origins() -> list[str]:
    """Return explicit browser origins allowed to call REST demo endpoints."""

    configured = os.getenv("AETHERVILLE_CORS_ORIGINS")
    if configured:
        return [origin.strip() for origin in configured.split(",") if origin.strip()]
    return [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://0.0.0.0:3000",
        "http://localhost:3100",
        "http://127.0.0.1:3100",
        "http://0.0.0.0:3100",
    ]


fastapi_app.add_middleware(
    CORSMiddleware,
    allow_origins=parse_cors_origins(),
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["content-type", "authorization"],
)

sio = socketio.AsyncServer(
    async_mode="asgi",
    cors_allowed_origins="*",
    logger=False,
    engineio_logger=False,
)

TICK_RATE_HZ = float(os.getenv("AETHERVILLE_TICK_RATE_HZ", "10"))
simulation = SimulationEngine(SimulationConfig(tick_rate_hz=TICK_RATE_HZ))
voice_transcriber = transcriber_from_env()
_simulation_task: asyncio.Task[None] | None = None


async def broadcast_state_update(envelope: Envelope) -> None:
    await sio.emit("aetherville:state_update", envelope.model_dump(mode="json"))


async def emit_god_command_response(response: GodCommandResponse, to: str | None = None) -> None:
    envelopes = response.envelopes or [response.envelope]
    for envelope in envelopes:
        await sio.emit("aetherville:event", envelope.model_dump(mode="json"), to=to)
    await sio.emit(
        "aetherville:state_update",
        simulation.state_update().model_dump(mode="json"),
        to=to,
    )


def ensure_simulation_task() -> None:
    global _simulation_task
    if _simulation_task is None or _simulation_task.done():
        _simulation_task = asyncio.create_task(simulation.run(broadcast_state_update))


async def stop_simulation_task() -> None:
    simulation.stop()
    if _simulation_task is not None and not _simulation_task.done():
        try:
            await asyncio.wait_for(_simulation_task, timeout=1.0)
        except TimeoutError:
            _simulation_task.cancel()


def probe_http_dependency(name: str, url: str, timeout: float = 0.5) -> ServiceStatus:
    try:
        with urllib.request.urlopen(url, timeout=timeout) as response:
            status_code = getattr(response, "status", 200)
    except (OSError, urllib.error.URLError) as exc:
        return ServiceStatus(name=name, status="down", detail=f"{url} unreachable: {exc}")

    if 200 <= status_code < 300:
        return ServiceStatus(name=name, status="ok", detail=url)
    return ServiceStatus(name=name, status="degraded", detail=f"{url} returned {status_code}")


def camera_vision_mode() -> str:
    """Return the camera enrichment mode without forcing real YOLO by default."""

    return os.getenv(
        "AETHERVILLE_CAMERA_VISION_MODE",
        os.getenv("AETHERVILLE_VISION_MODE", "mock"),
    ).lower()


def _post_vision_detect(request: VisionDetectRequest) -> VisionDetectResponse:
    """Call the direct-process vision service using only stdlib HTTP."""

    vision_url = os.getenv("AETHERVILLE_VISION_URL", "http://127.0.0.1:8001").rstrip("/")
    encoded = json.dumps(request.model_dump(mode="json")).encode("utf-8")
    http_request = urllib.request.Request(
        f"{vision_url}/detect",
        data=encoded,
        headers={"content-type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(http_request, timeout=2.0) as response:
        body = response.read().decode("utf-8")
    return VisionDetectResponse.model_validate(json.loads(body))


def enrich_camera_frame_with_vision(
    frame: VehicleCameraFrame,
    *,
    tick: int,
) -> VehicleCameraFrame:
    """Replace mock camera boxes with real YOLO detections when explicitly enabled.

    This is intentionally request-scoped: the simulation tick loop stays cheap,
    while the vehicle camera panel can prove the real RunPod vision service is
    active without turning every world-state tick into a GPU inference job.
    """

    if camera_vision_mode() != "real":
        return frame

    request = VisionDetectRequest(
        frame_b64=frame.frame_b64,
        camera_id=f"{frame.vehicle_id}-front",
        metadata={
            "tick": tick,
            "vehicle_id": frame.vehicle_id,
            "frame_width": frame.width,
            "frame_height": frame.height,
        },
    )
    try:
        vision_response = _post_vision_detect(request)
    except (
        OSError,
        TimeoutError,
        urllib.error.URLError,
        json.JSONDecodeError,
        ValidationError,
        ValueError,
    ):
        return frame

    if vision_response.mode != "real":
        return frame

    real_width = 640 if frame.frame_b64 is None else frame.width
    real_height = 384 if frame.frame_b64 is None else frame.height
    return frame.model_copy(
        update={
            "mode": "real",
            "width": real_width,
            "height": real_height,
            "detections": vision_response.detections,
        }
    )


def build_health_response() -> HealthResponse:
    """Return orchestrator health and optional direct-process dependency probes."""

    dependencies = [
        ServiceStatus(
            name="simulation",
            status="ok",
            detail=f"deterministic tick loop configured at {TICK_RATE_HZ:g} Hz",
        ),
        ServiceStatus(
            name="learning",
            status="ok",
            detail="deterministic online adaptation JSON persistence active",
        ),
        ServiceStatus(
            name="stt",
            status=voice_transcriber.health_status(),
            detail=voice_transcriber.health_detail(),
        ),
    ]

    if os.getenv("AETHERVILLE_PROBE_DEPENDENCIES") == "1":
        vision_url = os.getenv("AETHERVILLE_VISION_URL", "http://127.0.0.1:8001")
        vllm_url = os.getenv("AETHERVILLE_VLLM_URL", "http://127.0.0.1:8000/v1")
        redis_mode = os.getenv("AETHERVILLE_REDIS_MODE", "memory")

        dependencies.extend(
            [
                ServiceStatus(
                    name="redis",
                    status="stub" if redis_mode == "memory" else "degraded",
                    detail=(
                        "in-memory fallback selected"
                        if redis_mode == "memory"
                        else (
                            "external redis health is checked by "
                            "infra/runpod/health_check_direct.sh"
                        )
                    ),
                ),
                probe_http_dependency("vision", f"{vision_url.rstrip('/')}/health"),
                probe_http_dependency("vllm", f"{vllm_url.rstrip('/')}/models"),
            ]
        )
    else:
        dependencies.extend(
            [
                ServiceStatus(
                    name="redis",
                    status="stub",
                    detail="direct-process Redis or in-memory fallback lands in Goal 02",
                ),
                ServiceStatus(
                    name="vllm",
                    status="missing",
                    detail="set AETHERVILLE_PROBE_DEPENDENCIES=1 to probe direct-process service",
                ),
                ServiceStatus(
                    name="vision",
                    status="missing",
                    detail="set AETHERVILLE_PROBE_DEPENDENCIES=1 to probe direct-process service",
                ),
            ]
        )

    overall: Literal["ok", "degraded", "down"] = (
        "ok" if all(item.status != "down" for item in dependencies) else "degraded"
    )
    return HealthResponse(
        service="orchestrator",
        status=overall,
        version=__version__,
        dependencies=dependencies,
    )


@fastapi_app.get("/api/v1/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    return build_health_response()


@fastapi_app.get("/health", response_model=HealthResponse)
async def root_health() -> HealthResponse:
    return build_health_response()


@fastapi_app.get("/api/v1/sim/status", response_model=SimStatusResponse)
async def sim_status() -> SimStatusResponse:
    return simulation.status()


@fastapi_app.get("/api/v1/sim/state", response_model=WorldStatePayload)
async def sim_state() -> WorldStatePayload:
    return simulation.snapshot()


@fastapi_app.get("/api/v1/learning/status", response_model=LearningStatusResponse)
async def learning_status() -> LearningStatusResponse:
    return simulation.learning_status()


@fastapi_app.post("/api/v1/sim/start", response_model=SimStatusResponse)
async def sim_start() -> SimStatusResponse:
    status = simulation.start()
    ensure_simulation_task()
    return status


@fastapi_app.post("/api/v1/sim/stop", response_model=SimStatusResponse)
async def sim_stop() -> SimStatusResponse:
    await stop_simulation_task()
    return simulation.status()


@fastapi_app.post("/api/v1/sim/reset", response_model=SimStatusResponse)
async def sim_reset(request: SimResetRequest | None = None) -> SimStatusResponse:
    await stop_simulation_task()
    return simulation.reset(seed=request.seed if request else None)


@fastapi_app.get("/api/v1/timeline", response_model=list[EventPayload])
async def timeline() -> list[EventPayload]:
    return simulation.timeline


@fastapi_app.get("/api/v1/citizens", response_model=CitizenListResponse)
async def list_citizens() -> CitizenListResponse:
    return simulation.citizens.list_personas()


@fastapi_app.get("/api/v1/citizens/{citizen_id}", response_model=CitizenDetailResponse)
async def citizen_detail(citizen_id: str) -> CitizenDetailResponse:
    try:
        return simulation.citizens.detail(citizen_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=f"unknown citizen {citizen_id}") from exc


@fastapi_app.get("/api/v1/citizens/{citizen_id}/memories", response_model=MemoryStreamResponse)
async def citizen_memories(citizen_id: str, query: str | None = None) -> MemoryStreamResponse:
    try:
        return simulation.citizens.memory_stream(citizen_id, query=query)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=f"unknown citizen {citizen_id}") from exc


@fastapi_app.post("/api/v1/citizens/{citizen_id}/reflect", response_model=ReflectionResponse)
async def reflect_citizen(citizen_id: str) -> ReflectionResponse:
    try:
        response = simulation.citizens.reflect(citizen_id, tick=simulation.tick)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=f"unknown citizen {citizen_id}") from exc
    await sio.emit("aetherville:event", response.envelope.model_dump(mode="json"))
    return response


@fastapi_app.post("/api/v1/citizens/{citizen_id}/dialogue", response_model=DialogueResponse)
async def start_citizen_dialogue(
    citizen_id: str, request: DialogueRequest | None = None
) -> DialogueResponse:
    request = request or DialogueRequest()
    try:
        response = simulation.citizens.start_dialogue(
            citizen_id,
            request.target_citizen_id,
            topic=request.topic,
            tick=simulation.tick,
        )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=f"unknown citizen {exc.args[0]}") from exc
    for envelope in response.envelopes:
        await sio.emit("aetherville:event", envelope.model_dump(mode="json"))
    return response


@fastapi_app.get("/api/v1/vehicles/{vehicle_id}/camera", response_model=VehicleCameraFrame)
async def vehicle_camera(vehicle_id: str) -> VehicleCameraFrame:
    try:
        frame = simulation.vehicle_camera_frame(vehicle_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=f"unknown vehicle {vehicle_id}") from exc
    return await asyncio.to_thread(enrich_camera_frame_with_vision, frame, tick=simulation.tick)


@fastapi_app.post("/api/v1/god/command", response_model=GodCommandResponse)
async def god_command(command: GodCommand) -> GodCommandResponse:
    response = simulation.execute_god_command(command)
    await emit_god_command_response(response)
    return response


@fastapi_app.post("/api/v1/god/voice", response_model=VoiceCommandResponse)
async def god_voice(request: VoiceCommandRequest) -> VoiceCommandResponse:
    result = await asyncio.to_thread(
        voice_transcriber.transcribe,
        request.audio_blob_b64,
        mime_type=request.mime_type,
        language=request.language,
        fallback_transcript=request.fallback_transcript,
    )
    if not result.transcript:
        raise HTTPException(
            status_code=422,
            detail=result.detail or "voice transcript unavailable",
        )
    command = voice_transcriber.command_from_transcript(result.transcript, request.user_id)
    response = simulation.execute_god_command(command)
    await emit_god_command_response(response)
    return VoiceCommandResponse(
        transcript=result.transcript,
        stt_mode=result.mode,
        stt_status=result.status,
        detail=result.detail,
        command=response,
    )


async def on_connect(sid: str, environ: dict[str, Any], auth: dict[str, Any] | None) -> None:
    del environ, auth
    ack = Envelope(
        type=EnvelopeType.ACK,
        ts=time.time(),
        tick=0,
        payload=AckPayload(message="connected to Aetherville orchestrator").model_dump(
            mode="json"
        ),
    )
    await sio.emit("aetherville:ack", ack.model_dump(mode="json"), to=sid)
    state_update = simulation.state_update()
    await sio.emit("aetherville:state_update", state_update.model_dump(mode="json"), to=sid)


async def on_command(sid: str, data: dict[str, Any]) -> None:
    envelope = Envelope.model_validate(data)
    if envelope.type is EnvelopeType.COMMAND:
        command = GodCommand.model_validate(envelope.payload)
        response = simulation.execute_god_command(command)
        await emit_god_command_response(response, to=sid)


async def on_disconnect(sid: str) -> None:
    del sid


sio.on("connect", handler=on_connect)
sio.on("command", handler=on_command)
sio.on("disconnect", handler=on_disconnect)

asgi_app = socketio.ASGIApp(sio, other_asgi_app=fastapi_app, socketio_path="socket.io")
app = asgi_app
