"""Failure-path coverage for the Kubernetes health probes."""

import asyncio
from unittest.mock import AsyncMock, patch

import pytest
from app.core.config import settings
from app.main import _database_health_check, _redis_health_check


@pytest.mark.asyncio
async def test_database_health_check_executes_select_one():
    session = AsyncMock()
    session_factory = AsyncMock()
    session_factory.return_value.__aenter__.return_value = session

    with patch("app.core.database.async_session_maker", session_factory):
        await _database_health_check()

    session.execute.assert_awaited_once()
    assert str(session.execute.await_args.args[0]) == "SELECT 1"


@pytest.mark.asyncio
async def test_redis_health_check_uses_bounded_timeouts_and_closes():
    connection = AsyncMock()
    redis_context = AsyncMock()
    redis_context.__aenter__.return_value = connection

    with patch("redis.asyncio.from_url", return_value=redis_context) as from_url:
        await _redis_health_check()

    from_url.assert_called_once_with(
        settings.REDIS_URL,
        socket_connect_timeout=2.0,
        socket_timeout=2.0,
    )
    connection.ping.assert_awaited_once()
    redis_context.__aexit__.assert_awaited_once()


@pytest.mark.asyncio
async def test_liveness_is_independent_of_dependencies(client):
    with (
        patch("app.main._database_health_check", side_effect=AssertionError),
        patch("app.main._redis_health_check", side_effect=AssertionError),
    ):
        response = await client.get("/health/live")

    assert response.status_code == 200
    assert response.json() == {"status": "alive"}


@pytest.mark.asyncio
async def test_readiness_returns_200_when_dependencies_are_available(client):
    with (
        patch("app.main._database_health_check", new_callable=AsyncMock),
        patch("app.main._redis_health_check", new_callable=AsyncMock),
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
    with (
        patch(
            "app.main._database_health_check",
            side_effect=RuntimeError("postgres password=super-secret"),
        ),
        patch("app.main._redis_health_check", new_callable=AsyncMock),
    ):
        response = await client.get("/health/ready")

    assert response.status_code == 503
    assert response.json() == {
        "status": "not_ready",
        "checks": {"database": "unavailable", "redis": "ok"},
    }
    assert "super-secret" not in response.text


@pytest.mark.asyncio
async def test_readiness_returns_503_when_redis_is_down(client):
    with (
        patch("app.main._database_health_check", new_callable=AsyncMock),
        patch(
            "app.main._redis_health_check",
            side_effect=RuntimeError("redis://:secret@example"),
        ),
    ):
        response = await client.get("/health/ready")

    assert response.status_code == 503
    assert response.json()["checks"] == {"database": "ok", "redis": "unavailable"}
    assert "secret" not in response.text


@pytest.mark.asyncio
async def test_readiness_times_out_a_blocked_dependency(client):
    async def blocked_probe():
        await asyncio.sleep(0.05)

    with (
        patch("app.main.HEALTH_CHECK_TIMEOUT_SECONDS", 0.01),
        patch("app.main._database_health_check", side_effect=blocked_probe),
        patch("app.main._redis_health_check", new_callable=AsyncMock),
    ):
        response = await client.get("/health/ready")

    assert response.status_code == 503
    assert response.json()["checks"] == {"database": "unavailable", "redis": "ok"}


@pytest.mark.asyncio
async def test_legacy_health_endpoint_remains_compatible(client):
    response = await client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}
