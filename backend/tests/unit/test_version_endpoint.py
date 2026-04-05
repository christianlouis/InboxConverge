"""
Unit tests for the version endpoint (api/v1/endpoints/version.py).
"""

import pytest
from httpx import AsyncClient, ASGITransport

from app.main import create_application


@pytest.fixture
def app():
    return create_application()


class TestVersionEndpoint:
    async def test_get_version_returns_200(self, app):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/api/v1/version")
        assert response.status_code == 200

    async def test_get_version_has_version_key(self, app):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/api/v1/version")
        data = response.json()
        assert "version" in data

    async def test_get_version_has_build_date_key(self, app):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/api/v1/version")
        data = response.json()
        assert "build_date" in data

    async def test_version_is_string_or_none(self, app):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/api/v1/version")
        data = response.json()
        assert isinstance(data["version"], str) or data["version"] is None
