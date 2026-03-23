"""
Main FastAPI application.
"""

from contextlib import asynccontextmanager
from collections.abc import AsyncIterator
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
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


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Application lifespan handler for startup and shutdown events."""
    # Startup
    logger.info(f"Starting {settings.APP_NAME} v{settings.APP_VERSION}")
    logger.info(f"Debug mode: {settings.DEBUG}")
    logger.info("API documentation: /api/docs")

    # Seed default database-backed settings (no-op if they already exist)
    try:
        from app.core.database import async_session_maker
        from app.services.config_service import ConfigService

        async with async_session_maker() as db:
            await ConfigService.seed_defaults(db)
    except Exception as exc:
        logger.warning("Could not seed default settings: %s", exc, exc_info=True)

    yield
    # Shutdown
    logger.info("Shutting down application")


def create_application() -> FastAPI:
    """Create and configure FastAPI application"""

    app = FastAPI(
        title=settings.APP_NAME,
        version=settings.APP_VERSION,
        description="Multi-tenant POP3/IMAP to Gmail forwarder with subscription management",
        docs_url="/api/docs",
        redoc_url="/api/redoc",
        openapi_url="/api/openapi.json",
        lifespan=lifespan,
    )

    # Security middleware (add before CORS)
    app.add_middleware(SecurityHeadersMiddleware)
    app.add_middleware(CSRFProtectionMiddleware)

    # CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
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

    return app


app = create_application()
