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
    NotificationConfigResponse,
    NotificationConfigUpdate,
)

router = APIRouter()


@router.post(
    "", response_model=NotificationConfigResponse, status_code=status.HTTP_201_CREATED
)
async def create_notification_config(
    config_in: NotificationConfigCreate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Create notification configuration"""
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
    """List all notification configurations"""
    result = await db.execute(
        select(NotificationConfig).where(NotificationConfig.user_id == current_user.id)
    )
    return result.scalars().all()
