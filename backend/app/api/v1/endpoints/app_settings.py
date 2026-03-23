"""Admin API endpoints for managing database-backed application settings."""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, ConfigDict
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_superuser
from app.models.database_models import User
from app.services.config_service import BOOTSTRAP_KEYS, ConfigService

router = APIRouter()


# ── Schemas ────────────────────────────────────────────────────────


class AppSettingResponse(BaseModel):
    """Public representation of a stored setting."""

    id: int
    key: str
    value: Optional[str] = None
    value_type: str
    description: Optional[str] = None
    is_secret: bool
    category: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class AppSettingCreate(BaseModel):
    """Payload for creating / updating a setting."""

    key: str
    value: str
    value_type: str = "string"
    description: Optional[str] = None
    is_secret: bool = False
    category: Optional[str] = None


# ── Endpoints ──────────────────────────────────────────────────────


@router.get("", response_model=List[AppSettingResponse])
async def list_settings(
    category: Optional[str] = Query(None, description="Filter by category"),
    current_user: User = Depends(get_current_superuser),
    db: AsyncSession = Depends(get_db),
):
    """List all application settings (admin only).

    Secrets are returned with their values masked.
    """
    settings = await ConfigService.list_all(db, category=category)
    results: List[AppSettingResponse] = []
    for s in settings:
        val = s.value if not s.is_secret else "********"  # type: ignore[arg-type]
        results.append(
            AppSettingResponse(
                id=s.id,  # type: ignore[arg-type]
                key=s.key,  # type: ignore[arg-type]
                value=val,  # type: ignore[arg-type]
                value_type=s.value_type or "string",  # type: ignore[arg-type]
                description=s.description,  # type: ignore[arg-type]
                is_secret=s.is_secret,  # type: ignore[arg-type]
                category=s.category,  # type: ignore[arg-type]
            )
        )
    return results


@router.put("/{key}", response_model=AppSettingResponse)
async def upsert_setting(
    key: str,
    payload: AppSettingCreate,
    current_user: User = Depends(get_current_superuser),
    db: AsyncSession = Depends(get_db),
):
    """Create or update a setting (admin only).

    Bootstrap settings (DATABASE_URL, SECRET_KEY, ENCRYPTION_KEY) cannot
    be stored in the database — they must be set via environment variables.
    """
    if key in BOOTSTRAP_KEYS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"'{key}' is a bootstrap setting and cannot be stored in the "
                "database. Set it via environment variables."
            ),
        )

    setting = await ConfigService.set(
        key=key,
        value=payload.value,
        db=db,
        value_type=payload.value_type,
        description=payload.description,
        is_secret=payload.is_secret,
        category=payload.category,
    )

    return AppSettingResponse(
        id=setting.id,  # type: ignore[arg-type]
        key=setting.key,  # type: ignore[arg-type]
        value="********" if setting.is_secret else setting.value,  # type: ignore[arg-type]
        value_type=setting.value_type or "string",  # type: ignore[arg-type]
        description=setting.description,  # type: ignore[arg-type]
        is_secret=setting.is_secret,  # type: ignore[arg-type]
        category=setting.category,  # type: ignore[arg-type]
    )


@router.delete("/{key}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_setting(
    key: str,
    current_user: User = Depends(get_current_superuser),
    db: AsyncSession = Depends(get_db),
):
    """Delete a setting from the database (admin only)."""
    if key in BOOTSTRAP_KEYS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(f"'{key}' is a bootstrap setting and cannot be deleted."),
        )

    deleted = await ConfigService.delete(key, db)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Setting '{key}' not found",
        )


@router.post("/seed-defaults", status_code=status.HTTP_200_OK)
async def seed_default_settings(
    current_user: User = Depends(get_current_superuser),
    db: AsyncSession = Depends(get_db),
):
    """Seed default settings into the database (admin only).

    Only creates settings that do not already exist.
    """
    count = await ConfigService.seed_defaults(db)
    return {"message": f"Seeded {count} default settings", "created": count}
