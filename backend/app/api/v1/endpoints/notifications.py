"""Notification configuration endpoints"""

from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db
from app.core.deps import get_current_active_user
from app.models.database_models import User, NotificationConfig
from app.models.schemas import (
    NotificationConfigCreate,
    NotificationConfigUpdate,
    NotificationConfigResponse,
    NotificationTestRequest,
    NotificationTestResponse,
)
from app.services.notification_service import test_notification

router = APIRouter()


@router.post(
    "", response_model=NotificationConfigResponse, status_code=status.HTTP_201_CREATED
)
async def create_notification_config(
    config_in: NotificationConfigCreate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a new notification configuration"""
    config = NotificationConfig(user_id=current_user.id, **config_in.dict())
    db.add(config)
    await db.commit()
    await db.refresh(config)
    return config


@router.get("", response_model=List[NotificationConfigResponse])
async def list_notification_configs(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """List all notification configurations for the current user"""
    result = await db.execute(
        select(NotificationConfig).where(NotificationConfig.user_id == current_user.id)
    )
    return result.scalars().all()


@router.get("/{config_id}", response_model=NotificationConfigResponse)
async def get_notification_config(
    config_id: int,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Get a specific notification configuration"""
    result = await db.execute(
        select(NotificationConfig).where(
            NotificationConfig.id == config_id,
            NotificationConfig.user_id == current_user.id,
        )
    )
    config = result.scalar_one_or_none()
    if not config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Notification config not found",
        )
    return config


@router.put("/{config_id}", response_model=NotificationConfigResponse)
async def update_notification_config(
    config_id: int,
    config_in: NotificationConfigUpdate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Update a notification configuration"""
    result = await db.execute(
        select(NotificationConfig).where(
            NotificationConfig.id == config_id,
            NotificationConfig.user_id == current_user.id,
        )
    )
    config = result.scalar_one_or_none()
    if not config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Notification config not found",
        )

    update_data = config_in.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(config, field, value)

    await db.commit()
    await db.refresh(config)
    return config


@router.delete("/{config_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_notification_config(
    config_id: int,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete a notification configuration"""
    result = await db.execute(
        select(NotificationConfig).where(
            NotificationConfig.id == config_id,
            NotificationConfig.user_id == current_user.id,
        )
    )
    config = result.scalar_one_or_none()
    if not config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Notification config not found",
        )

    await db.delete(config)
    await db.commit()


@router.post("/test", response_model=NotificationTestResponse)
async def test_notification_config(
    request: NotificationTestRequest,
    current_user: User = Depends(get_current_active_user),
):
    """Test a notification channel by sending a test message"""
    success, message = await test_notification(request.apprise_url)
    return NotificationTestResponse(success=success, message=message)
