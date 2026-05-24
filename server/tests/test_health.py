from __future__ import annotations

from fastapi.testclient import TestClient

from aetherville_schemas import HealthResponse
from aetherville_server.main import fastapi_app


def test_health_endpoint_uses_shared_schema() -> None:
    client = TestClient(fastapi_app)
    response = client.get("/api/v1/health")

    assert response.status_code == 200
    health = HealthResponse.model_validate(response.json())
    assert health.service == "orchestrator"
    assert health.status == "ok"
    assert {dependency.name for dependency in health.dependencies} >= {"redis", "vllm", "vision"}
