"""
Main FastAPI application.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
import logging

from app.core.config import settings
from app.core.middleware import SecurityHeadersMiddleware, CSRFProtectionMiddleware
from app.api.v1.api import api_router

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL.upper()),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

logger = logging.getLogger(__name__)


def create_application() -> FastAPI:
    """Create and configure FastAPI application"""

    app = FastAPI(
        title=settings.APP_NAME,
        version=settings.APP_VERSION,
        description="Multi-tenant POP3/IMAP to Gmail forwarder with subscription management",
        docs_url="/api/docs",
        redoc_url="/api/redoc",
        openapi_url="/api/openapi.json",
    )

    # Security middleware (add before CORS)
    app.add_middleware(SecurityHeadersMiddleware)
    app.add_middleware(CSRFProtectionMiddleware)

    # CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Include API router
    app.include_router(api_router, prefix=settings.API_V1_PREFIX)

    @app.get("/")
    async def root():
        """Root endpoint"""
        return {
            "message": "POP3 Forwarder SaaS API",
            "version": settings.APP_VERSION,
            "docs": "/api/docs",
        }

    @app.get("/health")
    async def health_check():
        """Health check endpoint for container orchestration"""
        return {"status": "healthy"}

    @app.on_event("startup")
    async def startup_event():
        """Run on application startup"""
        logger.info(f"Starting {settings.APP_NAME} v{settings.APP_VERSION}")
        logger.info(f"Debug mode: {settings.DEBUG}")
        logger.info(f"API documentation: /api/docs")

    @app.on_event("shutdown")
    async def shutdown_event():
        """Run on application shutdown"""
        logger.info("Shutting down application")

    return app


app = create_application()
