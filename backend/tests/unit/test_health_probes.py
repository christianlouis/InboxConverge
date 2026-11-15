"""Failure-path coverage for the Kubernetes health probes."""

from unittest.mock import AsyncMock, patch

import pytest


@pytest.mark.asyncio
async def test_liveness_is_independent_of_dependencies(client):
    with patch("app.main._database_health_check", side_effect=AssertionError), patch(
        "app.main._redis_health_check", side_effect=AssertionError
    ):
        response = await client.get("/health/live")

    assert response.status_code == 200
    assert response.json() == {"status": "alive"}


@pytest.mark.asyncio
async def test_readiness_returns_200_when_dependencies_are_available(client):
    with patch("app.main._database_health_check", new_callable=AsyncMock), patch(
        "app.main._redis_health_check", new_callable=AsyncMock
    ):
        response = await client.get("/health/ready")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ready",
        "checks": {"database": "ok", "redis": "ok"},
    }


@pytest.mark.asyncio
async def test_readiness_returns_503_without_dependency_details_when_database_is_down(
    client,
):
    with patch(
        "app.main._database_health_check",
        side_effect=RuntimeError("postgres password=super-secret"),
    ), patch("app.main._redis_health_check", new_callable=AsyncMock):
        response = await client.get("/health/ready")

    assert response.status_code == 503
    assert response.json() == {
        "status": "not_ready",
        "checks": {"database": "unavailable", "redis": "ok"},
    }
    assert "super-secret" not in response.text


@pytest.mark.asyncio
async def test_readiness_returns_503_when_redis_is_down(client):
    with patch("app.main._database_health_check", new_callable=AsyncMock), patch(
        "app.main._redis_health_check",
        side_effect=RuntimeError("redis://:secret@example"),
    ):
        response = await client.get("/health/ready")

    assert response.status_code == 503
    assert response.json()["checks"] == {"database": "ok", "redis": "unavailable"}
    assert "secret" not in response.text


@pytest.mark.asyncio
async def test_legacy_health_endpoint_remains_compatible(client):
    response = await client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}
