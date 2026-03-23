"""Subscription and payment endpoints"""

from typing import List
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db
from app.core.deps import get_current_active_user
from app.models.database_models import User, SubscriptionPlan
from app.models.schemas import SubscriptionPlanResponse

router = APIRouter()


@router.get("/plans", response_model=List[SubscriptionPlanResponse])
async def list_subscription_plans(db: AsyncSession = Depends(get_db)):
    """List all available subscription plans"""
    result = await db.execute(
        select(SubscriptionPlan).where(SubscriptionPlan.is_active == True)  # noqa: E712
    )
    return result.scalars().all()


@router.get("/current")
async def get_current_subscription(
    current_user: User = Depends(get_current_active_user),
):
    """Get current user's subscription details"""
    return {
        "tier": current_user.subscription_tier,
        "status": current_user.subscription_status,
        "expires_at": current_user.subscription_expires_at,
    }
