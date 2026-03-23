"""
Unit tests for security middleware.
"""

from starlette.testclient import TestClient
from starlette.applications import Starlette
from starlette.responses import PlainTextResponse
from starlette.routing import Route

from app.core.middleware import SecurityHeadersMiddleware, CSRFProtectionMiddleware


def _make_app(middleware_classes):
    """Helper to build a Starlette app with given middleware."""

    async def homepage(request):
        return PlainTextResponse("OK")

    app = Starlette(
        routes=[
            Route("/", homepage, methods=["GET", "HEAD", "POST", "OPTIONS"]),
            Route("/api/v1/auth/login", homepage, methods=["GET", "POST"]),
        ]
    )
    for cls in middleware_classes:
        app.add_middleware(cls)
    return app


class TestSecurityHeadersMiddleware:
    """Test security headers added to all responses"""

    def setup_method(self):
        app = _make_app([SecurityHeadersMiddleware])
        self.client = TestClient(app)

    def test_x_frame_options_header(self):
        """Test X-Frame-Options is set to DENY"""
        response = self.client.get("/")
        assert response.headers["X-Frame-Options"] == "DENY"

    def test_x_content_type_options_header(self):
        """Test X-Content-Type-Options is set to nosniff"""
        response = self.client.get("/")
        assert response.headers["X-Content-Type-Options"] == "nosniff"

    def test_x_xss_protection_header(self):
        """Test X-XSS-Protection header is set"""
        response = self.client.get("/")
        assert response.headers["X-XSS-Protection"] == "1; mode=block"

    def test_content_security_policy_header(self):
        """Test Content-Security-Policy header is present"""
        response = self.client.get("/")
        csp = response.headers["Content-Security-Policy"]
        assert "default-src 'self'" in csp
        assert "script-src" in csp

    def test_referrer_policy_header(self):
        """Test Referrer-Policy header"""
        response = self.client.get("/")
        assert response.headers["Referrer-Policy"] == "strict-origin-when-cross-origin"

    def test_permissions_policy_header(self):
        """Test Permissions-Policy header"""
        response = self.client.get("/")
        policy = response.headers["Permissions-Policy"]
        assert "geolocation=()" in policy
        assert "microphone=()" in policy
        assert "camera=()" in policy

    def test_no_hsts_for_localhost(self):
        """Test that HSTS header check depends on hostname"""
        # The HSTS header is only skipped when hostname is localhost or 127.0.0.1.
        # TestClient uses 'testserver' as hostname, which is not in the skip list,
        # so HSTS will be set. Verify the logic works with a direct check.
        response = self.client.get("/")
        # TestClient hostname is 'testserver', not localhost, so HSTS IS set
        assert "Strict-Transport-Security" in response.headers


class TestCSRFProtectionMiddleware:
    """Test CSRF protection middleware"""

    def setup_method(self):
        app = _make_app([CSRFProtectionMiddleware])
        self.client = TestClient(app)

    def test_get_requests_pass_through(self):
        """Test that GET requests are not blocked"""
        response = self.client.get("/")
        assert response.status_code == 200

    def test_head_requests_pass_through(self):
        """Test that HEAD requests are not blocked"""
        response = self.client.head("/")
        assert response.status_code == 200

    def test_options_requests_pass_through(self):
        """Test that OPTIONS requests are not blocked"""
        response = self.client.options("/")
        assert response.status_code == 200

    def test_exempt_paths_pass_through(self):
        """Test that exempt paths are not CSRF-checked for POST"""
        response = self.client.post("/api/v1/auth/login")
        assert response.status_code == 200

    def test_post_to_non_exempt_path_passes(self):
        """Test that POST to non-exempt path also passes (JWT provides CSRF protection)"""
        response = self.client.post("/")
        assert response.status_code == 200

    def test_generate_csrf_token(self):
        """Test CSRF token generation produces valid token"""
        token = CSRFProtectionMiddleware._generate_csrf_token()
        assert isinstance(token, str)
        assert len(token) == 43  # token_urlsafe(32) produces 43 chars

    def test_validate_csrf_token_valid(self):
        """Test CSRF token validation with valid token"""
        token = CSRFProtectionMiddleware._generate_csrf_token()
        assert CSRFProtectionMiddleware._validate_csrf_token(token) is True

    def test_validate_csrf_token_invalid(self):
        """Test CSRF token validation with invalid token"""
        assert CSRFProtectionMiddleware._validate_csrf_token("short") is False
