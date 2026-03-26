"""
Unit tests for the FastAPI application factory and core endpoints.
"""

import pytest
from httpx import AsyncClient, ASGITransport
from app.main import create_application


@pytest.fixture
def app():
    """Create a fresh application instance for testing."""
    return create_application()


@pytest.mark.asyncio
class TestRootEndpoint:
    """Test root endpoint"""

    async def test_root_returns_200(self, app):
        """Test that root endpoint returns 200"""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/")

        assert response.status_code == 200

    async def test_root_returns_api_info(self, app):
        """Test that root returns API information"""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/")

        data = response.json()
        assert "message" in data
        assert "version" in data
        assert "docs" in data
        assert data["docs"] == "/api/docs"


@pytest.mark.asyncio
class TestHealthEndpoint:
    """Test health check endpoint"""

    async def test_health_returns_200(self, app):
        """Test that health endpoint returns 200"""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/health")

        assert response.status_code == 200

    async def test_health_returns_healthy(self, app):
        """Test that health endpoint returns healthy status"""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/health")

        data = response.json()
        assert data["status"] == "healthy"


@pytest.mark.asyncio
class TestSecurityHeaders:
    """Test that security headers are present in responses"""

    async def test_security_headers_on_root(self, app):
        """Test security headers on root endpoint"""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/")

        assert response.headers["X-Frame-Options"] == "DENY"
        assert response.headers["X-Content-Type-Options"] == "nosniff"
        assert response.headers["X-XSS-Protection"] == "1; mode=block"

    async def test_security_headers_on_health(self, app):
        """Test security headers on health endpoint"""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/health")

        assert response.headers["X-Frame-Options"] == "DENY"


@pytest.mark.asyncio
class TestApplicationFactory:
    """Test the create_application factory"""

    async def test_app_title(self, app):
        """Test that app has correct title"""
        assert app.title == "InboxConverge"

    async def test_app_version(self, app):
        """Test that app has a version"""
        assert app.version is not None
        assert len(app.version) > 0

    async def test_openapi_endpoint(self, app):
        """Test that OpenAPI schema is available"""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/api/openapi.json")

        assert response.status_code == 200
        schema = response.json()
        assert "openapi" in schema
        assert "info" in schema
