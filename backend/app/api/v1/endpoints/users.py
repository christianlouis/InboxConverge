"""User management endpoints"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db
from app.core.deps import get_current_active_user
from app.core.security import encrypt_credential
from app.models.database_models import User, UserSmtpConfig
from app.models.schemas import (
    UserDetailResponse,
    UserUpdate,
    UserSmtpConfigUpdate,
    UserSmtpConfigResponse,
)

router = APIRouter()


@router.get("/me", response_model=UserDetailResponse)
async def get_current_user_profile(
    current_user: User = Depends(get_current_active_user),
):
    """Get current user profile"""
    return current_user


@router.put("/me", response_model=UserDetailResponse)
async def update_current_user_profile(
    user_update: UserUpdate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Update current user profile"""
    if user_update.email:
        current_user.email = user_update.email  # type: ignore[assignment]
    if user_update.full_name:
        current_user.full_name = user_update.full_name  # type: ignore[assignment]

    await db.commit()
    await db.refresh(current_user)
    return current_user


@router.get("/smtp-config", response_model=UserSmtpConfigResponse)
async def get_smtp_config(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Get the current user's SMTP relay configuration"""
    result = await db.execute(
        select(UserSmtpConfig).where(UserSmtpConfig.user_id == current_user.id)
    )
    config = result.scalar_one_or_none()

    if not config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No SMTP configuration found. Save one first.",
        )

    return UserSmtpConfigResponse(
        id=config.id,  # type: ignore[arg-type]
        user_id=config.user_id,  # type: ignore[arg-type]
        host=config.host,  # type: ignore[arg-type]
        port=config.port,  # type: ignore[arg-type]
        username=config.username,  # type: ignore[arg-type]
        use_tls=config.use_tls,  # type: ignore[arg-type]
        has_password=bool(config.encrypted_password),
        created_at=config.created_at,  # type: ignore[arg-type]
        updated_at=config.updated_at,  # type: ignore[arg-type]
    )


@router.put("/smtp-config", response_model=UserSmtpConfigResponse)
async def upsert_smtp_config(
    config_in: UserSmtpConfigUpdate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Create or update the current user's SMTP relay configuration"""
    result = await db.execute(
        select(UserSmtpConfig).where(UserSmtpConfig.user_id == current_user.id)
    )
    config = result.scalar_one_or_none()

    if config:
        config.host = config_in.host  # type: ignore[assignment]
        config.port = config_in.port  # type: ignore[assignment]
        config.username = config_in.username  # type: ignore[assignment]
        config.use_tls = config_in.use_tls  # type: ignore[assignment]
        if config_in.password is not None:
            config.encrypted_password = encrypt_credential(config_in.password)  # type: ignore[assignment]
    else:
        config = UserSmtpConfig(
            user_id=current_user.id,
            host=config_in.host,
            port=config_in.port,
            username=config_in.username,
            encrypted_password=(
                encrypt_credential(config_in.password) if config_in.password else ""
            ),
            use_tls=config_in.use_tls,
        )
        db.add(config)

    await db.commit()
    await db.refresh(config)

    return UserSmtpConfigResponse(
        id=config.id,  # type: ignore[arg-type]
        user_id=config.user_id,  # type: ignore[arg-type]
        host=config.host,  # type: ignore[arg-type]
        port=config.port,  # type: ignore[arg-type]
        username=config.username,  # type: ignore[arg-type]
        use_tls=config.use_tls,  # type: ignore[arg-type]
        has_password=bool(config.encrypted_password),
        created_at=config.created_at,  # type: ignore[arg-type]
        updated_at=config.updated_at,  # type: ignore[arg-type]
    )


@router.delete("/smtp-config", status_code=status.HTTP_204_NO_CONTENT)
async def delete_smtp_config(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete the current user's SMTP relay configuration"""
    result = await db.execute(
        select(UserSmtpConfig).where(UserSmtpConfig.user_id == current_user.id)
    )
    config = result.scalar_one_or_none()
    if config:
        await db.delete(config)
        await db.commit()
