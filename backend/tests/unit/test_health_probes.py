import pytest
from httpx import AsyncClient
from unittest.mock import AsyncMock, patch

@pytest.mark.asyncio
async def test_health_live(client: AsyncClient):
    response = await client.get("/health/live")
    assert response.status_code == 200
    assert response.json() == {"status": "alive"}

@pytest.mark.asyncio
async def test_health_ready_ok(client: AsyncClient):
    with patch("app.main.async_session_maker") as mock_db, \
         patch("app.main.redis.from_url") as mock_redis:
        
        # Mock DB
        mock_db_session = AsyncMock()
        mock_db.return_value.__aenter__.return_value = mock_db_session
        
        # Mock Redis
        mock_redis_conn = AsyncMock()
        mock_redis.return_value.__aenter__.return_value = mock_redis_conn
        
        response = await client.get("/health/ready")
        assert response.status_code == 200
        assert response.json() == {"status": "ready"}
        mock_db_session.execute.assert_called_once()
        mock_redis_conn.ping.assert_called_once()

@pytest.mark.asyncio
async def test_health_ready_db_down(client: AsyncClient):
    with patch("app.main.async_session_maker") as mock_db, \
         patch("app.main.redis.from_url") as mock_redis:
        
        # Mock DB throwing error
        mock_db_session = AsyncMock()
        mock_db_session.execute.side_effect = Exception("DB connection failed")
        mock_db.return_value.__aenter__.return_value = mock_db_session
        
        response = await client.get("/health/ready")
        assert response.status_code == 503
        assert response.json() == {"detail": "Database unavailable"}
        mock_redis.assert_not_called()

@pytest.mark.asyncio
async def test_health_ready_redis_down(client: AsyncClient):
    with patch("app.main.async_session_maker") as mock_db, \
         patch("app.main.redis.from_url") as mock_redis:
        
        # Mock DB
        mock_db_session = AsyncMock()
        mock_db.return_value.__aenter__.return_value = mock_db_session
        
        # Mock Redis throwing error
        mock_redis_conn = AsyncMock()
        mock_redis_conn.ping.side_effect = Exception("Redis connection failed")
        mock_redis.return_value.__aenter__.return_value = mock_redis_conn
        
        response = await client.get("/health/ready")
        assert response.status_code == 503
        assert response.json() == {"detail": "Redis unavailable"}
