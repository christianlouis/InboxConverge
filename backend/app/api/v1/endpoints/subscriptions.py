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
    """
    List subscription plans shown in marketing / pricing pages.

    Zero-price plans (price_monthly == 0) are intentionally excluded so that
    enterprise / white-label deployments that assign a free plan to all users
    don't surface that plan in the public pricing UI.
    """
    result = await db.execute(
        select(SubscriptionPlan).where(
            SubscriptionPlan.is_active.is_(True),
            SubscriptionPlan.price_monthly > 0,
        )
    )
    return result.scalars().all()


@router.get("/current")
async def get_current_subscription(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Get current user's subscription details including plan limits"""
    plan_result = await db.execute(
        select(SubscriptionPlan).where(
            SubscriptionPlan.tier == current_user.subscription_tier,
            SubscriptionPlan.is_active.is_(True),
        )
    )
    plan = plan_result.scalar_one_or_none()

    return {
        "tier": current_user.subscription_tier,
        "status": current_user.subscription_status,
        "expires_at": current_user.subscription_expires_at,
        "max_mail_accounts": plan.max_mail_accounts if plan else None,
        "max_emails_per_day": plan.max_emails_per_day if plan else None,
        "check_interval_minutes": plan.check_interval_minutes if plan else None,
    }
