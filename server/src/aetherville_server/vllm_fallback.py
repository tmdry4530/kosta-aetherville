"""OpenAI-compatible fallback service for vLLM health and prompt smoke tests.

This is not a replacement for real vLLM. It preserves the endpoint contract when
model access is unavailable, so orchestration and client integration can be
verified before a GPU model download is approved.
"""

from __future__ import annotations

import time
from typing import Any

from fastapi import FastAPI
from pydantic import BaseModel, ConfigDict, Field

from aetherville_schemas import HealthResponse, ServiceStatus
from aetherville_server import __version__

app = FastAPI(
    title="Aetherville vLLM Fallback",
    version=__version__,
    docs_url="/docs",
    openapi_url="/openapi.json",
)


class ChatMessage(BaseModel):
    model_config = ConfigDict(extra="allow")

    role: str
    content: str


class ChatCompletionRequest(BaseModel):
    model_config = ConfigDict(extra="allow")

    model: str = "aetherville-mock-llm"
    messages: list[ChatMessage] = Field(default_factory=list)


def build_health_response() -> HealthResponse:
    return HealthResponse(
        service="vllm-fallback",
        status="ok",
        version=__version__,
        dependencies=[
            ServiceStatus(
                name="gpu-model",
                status="stub",
                detail="real vLLM process can replace this service when model access is ready",
            )
        ],
    )


@app.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    return build_health_response()


@app.get("/v1/models")
async def list_models() -> dict[str, Any]:
    return {
        "object": "list",
        "data": [
            {
                "id": "aetherville-mock-llm",
                "object": "model",
                "created": 0,
                "owned_by": "aetherville",
            }
        ],
    }


@app.post("/v1/chat/completions")
async def chat_completions(request: ChatCompletionRequest) -> dict[str, Any]:
    prompt = request.messages[-1].content if request.messages else ""
    content = (
        "안녕하세요. 저는 Aetherville 데모용 결정론적 LLM fallback입니다. "
        f"수신한 프롬프트: {prompt[:120]}"
    )
    return {
        "id": "chatcmpl-aetherville-fallback",
        "object": "chat.completion",
        "created": int(time.time()),
        "model": request.model,
        "choices": [
            {
                "index": 0,
                "message": {"role": "assistant", "content": content},
                "finish_reason": "stop",
            }
        ],
        "usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
    }
