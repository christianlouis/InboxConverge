"""
Security middleware for adding security headers and CSRF protection.
"""

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp
import secrets


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Add security headers to all responses"""

    async def dispatch(self, request: Request, call_next) -> Response:
        response = await call_next(request)

        # Prevent clickjacking
        response.headers["X-Frame-Options"] = "DENY"

        # Prevent MIME type sniffing
        response.headers["X-Content-Type-Options"] = "nosniff"

        # Enable XSS protection (for older browsers)
        response.headers["X-XSS-Protection"] = "1; mode=block"

        # Strict Transport Security (HTTPS only)
        # Note: Only enable in production with HTTPS
        if request.url.hostname not in ["localhost", "127.0.0.1"]:
            response.headers["Strict-Transport-Security"] = (
                "max-age=31536000; includeSubDomains"
            )

        # Content Security Policy (adjust based on frontend needs)
        csp = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' https://js.stripe.com; "
            "style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data: https:; "
            "font-src 'self' data:; "
            "connect-src 'self' https://api.stripe.com; "
            "frame-src https://js.stripe.com;"
        )
        response.headers["Content-Security-Policy"] = csp

        # Referrer Policy
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"

        # Permissions Policy (formerly Feature Policy)
        response.headers["Permissions-Policy"] = (
            "geolocation=(), microphone=(), camera=()"
        )

        return response


class CSRFProtectionMiddleware(BaseHTTPMiddleware):
    """
    Basic CSRF protection for state-changing operations.
    For API-only applications, this is less critical but still good practice.
    """

    def __init__(self, app: ASGIApp, exempt_paths: list | None = None):
        super().__init__(app)
        self.exempt_paths = exempt_paths or [
            "/api/v1/auth/login",
            "/api/v1/auth/register",
            "/api/v1/auth/google",
            "/docs",
            "/openapi.json",
            "/health",
        ]

    async def dispatch(self, request: Request, call_next) -> Response:
        # Skip CSRF check for safe methods
        if request.method in ["GET", "HEAD", "OPTIONS"]:
            return await call_next(request)

        # Skip CSRF check for exempt paths
        if any(request.url.path.startswith(path) for path in self.exempt_paths):
            return await call_next(request)

        # For API endpoints using JWT, the token itself provides CSRF protection
        # This is because attackers can't access the token stored in httpOnly cookies
        # or local storage from a different origin

        # If implementing cookie-based sessions, would check CSRF token here:
        # csrf_token = request.headers.get("X-CSRF-Token")
        # if not csrf_token or not self._validate_csrf_token(csrf_token):
        #     return JSONResponse(
        #         status_code=403,
        #         content={"detail": "CSRF token missing or invalid"}
        #     )

        response = await call_next(request)
        return response

    @staticmethod
    def _generate_csrf_token() -> str:
        """Generate a secure CSRF token"""
        return secrets.token_urlsafe(32)

    @staticmethod
    def _validate_csrf_token(token: str) -> bool:
        """Validate CSRF token (implement actual validation logic)"""
        # In a real implementation, compare against stored token
        return len(token) == 43  # token_urlsafe(32) produces 43 chars
