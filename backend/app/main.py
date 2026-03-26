"""
Main FastAPI application.
"""

import asyncio
import os
import re
import time
from contextlib import asynccontextmanager
from collections.abc import AsyncIterator
from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST
import logging
from alembic.config import Config as AlembicConfig
from alembic import command as alembic_command

from app.core.config import settings
from app.core.middleware import SecurityHeadersMiddleware, CSRFProtectionMiddleware
from app.core.metrics import HTTP_REQUESTS_TOTAL, HTTP_REQUEST_DURATION_SECONDS
from app.api.v1.api import api_router

# Absolute path to alembic.ini – one level above this file's directory
# (backend/app/main.py → backend/alembic.ini)
_ALEMBIC_INI = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "alembic.ini")
)

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

    # Ensure all database tables exist (idempotent; safe to run on every startup)
    try:
        from app.core.database import engine, Base
        import app.models.database_models  # noqa: F401 - register all ORM models

        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("Database tables verified/created")
    except Exception as exc:
        logger.error(
            "Could not create database tables: %s — API requests requiring DB will fail",
            exc,
            exc_info=True,
        )

    # Apply schema migrations for columns added to existing tables.
    # Alembic's ADD COLUMN IF NOT EXISTS migrations are idempotent – safe for
    # both fresh installs (create_all already added the columns) and existing
    # deployments (where the columns may be absent).
    try:

        def _run_alembic_upgrade() -> None:
            alembic_cfg = AlembicConfig(_ALEMBIC_INI)
            alembic_command.upgrade(alembic_cfg, "head")

        await asyncio.to_thread(_run_alembic_upgrade)
        logger.info("Database schema migrations applied")
    except Exception as exc:
        logger.error(
            "Could not apply schema migrations: %s — some columns may be missing",
            exc,
            exc_info=True,
        )

    # Seed default database-backed settings (no-op if they already exist)
    try:
        from app.core.database import async_session_maker
        from app.services.config_service import ConfigService

        async with async_session_maker() as db:
            await ConfigService.seed_defaults(db)
    except Exception as exc:
        logger.warning("Could not seed default settings: %s", exc, exc_info=True)

    # Ensure the configured ADMIN_EMAIL user has is_superuser=True.
    # This runs on every startup so that existing accounts created before the
    # auto-promotion login logic existed are also promoted correctly.
    if settings.ADMIN_EMAIL:
        try:
            from sqlalchemy import select, func
            from app.core.database import async_session_maker
            from app.models.database_models import User

            async with async_session_maker() as db:
                result = await db.execute(
                    select(User).where(
                        func.lower(User.email) == settings.ADMIN_EMAIL.lower()
                    )
                )
                admin_user = result.scalar_one_or_none()
                if admin_user and not admin_user.is_superuser:
                    admin_user.is_superuser = True  # type: ignore[assignment]
                    await db.commit()
                    logger.info(
                        "Auto-promoted admin user to superuser on startup: %s",
                        admin_user.email,
                    )
        except Exception as exc:
            logger.warning(
                "Could not auto-promote admin user on startup: %s", exc, exc_info=True
            )

    yield
    # Shutdown
    logger.info("Shutting down application")


def create_application() -> FastAPI:
    """Create and configure FastAPI application"""

    app = FastAPI(
        title=settings.APP_NAME,
        version=settings.APP_VERSION,
        description="Poll your legacy POP3/IMAP inboxes and deliver everything to Gmail. For real people, not enterprises.",
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

    @app.middleware("http")
    async def prometheus_middleware(request: Request, call_next):
        """Record per-request Prometheus metrics."""
        # Normalize the path so high-cardinality IDs don't explode label sets.
        path = request.url.path
        # Strip numeric path segments (e.g. /api/v1/accounts/42 → /api/v1/accounts/{id})
        normalized = re.sub(r"/\d+", "/{id}", path)

        start = time.perf_counter()
        response = await call_next(request)
        duration = time.perf_counter() - start

        HTTP_REQUESTS_TOTAL.labels(
            method=request.method,
            endpoint=normalized,
            status_code=str(response.status_code),
        ).inc()
        HTTP_REQUEST_DURATION_SECONDS.labels(
            method=request.method,
            endpoint=normalized,
        ).observe(duration)

        return response

    @app.get("/")
    async def root():
        """Root endpoint"""
        return {
            "message": "InboxConverge API",
            "version": settings.APP_VERSION,
            "docs": "/api/docs",
        }

    @app.get("/health")
    async def health_check():
        """Health check endpoint for container orchestration"""
        return {"status": "healthy"}

    @app.get("/metrics", include_in_schema=False)
    async def metrics():
        """Prometheus metrics endpoint."""
        data = generate_latest()
        return Response(content=data, media_type=CONTENT_TYPE_LATEST)

    return app


app = create_application()
