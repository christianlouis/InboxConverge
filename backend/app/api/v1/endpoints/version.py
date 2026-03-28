"""
Version endpoint – returns the application version and build date.
"""

from fastapi import APIRouter

from app.core.config import settings

router = APIRouter()


@router.get("")
async def get_version():
    """Return application version and build metadata."""
    return {
        "version": settings.APP_VERSION,
        "build_date": settings.BUILD_DATE or None,
    }
