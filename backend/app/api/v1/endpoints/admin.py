"""Admin endpoints"""

import math
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.core.database import get_db
from app.core.deps import get_current_superuser
from app.core.gdpr import mask_email, mask_from_header
from app.models.database_models import (
    User,
    MailAccount,
    ProcessingLog,
    ProcessingRun,
    SubscriptionPlan,
    SubscriptionTier,
    AdminNotificationConfig,
)
from app.models.schemas import (
    AdminUserListResponse,
    AdminUserUpdate,
    UserDetailResponse,
    SubscriptionPlanResponse,
    SubscriptionPlanCreate,
    SubscriptionPlanUpdate,
    AdminNotificationConfigCreate,
    AdminNotificationConfigUpdate,
    AdminNotificationConfigResponse,
    NotificationTestRequest,
    NotificationTestResponse,
    AdminProcessingRunResponse,
    AdminProcessingLogResponse,
    PaginatedAdminRunsResponse,
    PaginatedAdminLogsResponse,
)
from app.services.notification_service import test_notification

router = APIRouter()


@router.get("/stats")
async def get_admin_stats(
    current_user: User = Depends(get_current_superuser),
    db: AsyncSession = Depends(get_db),
):
    """Get overall system statistics (admin only)"""

    # Count users
    user_count = await db.execute(select(func.count(User.id)))
    total_users = user_count.scalar()

    # Count accounts
    account_count = await db.execute(select(func.count(MailAccount.id)))
    total_accounts = account_count.scalar()

    # Count processing runs
    run_count = await db.execute(select(func.count(ProcessingRun.id)))
    total_runs = run_count.scalar()

    return {
        "total_users": total_users,
        "total_mail_accounts": total_accounts,
        "total_processing_runs": total_runs,
    }


# ── User management ────────────────────────────────────────────────────────────


@router.get("/users", response_model=List[AdminUserListResponse])
async def list_users(
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(get_current_superuser),
    db: AsyncSession = Depends(get_db),
):
    """List all users with their mail account counts (admin only)"""
    result = await db.execute(
        select(User).order_by(User.created_at.desc()).offset(skip).limit(limit)
    )
    users = result.scalars().all()

    # Fetch mail account counts per user in one query
    counts_result = await db.execute(
        select(MailAccount.user_id, func.count(MailAccount.id).label("cnt")).group_by(
            MailAccount.user_id
        )
    )
    counts = {row.user_id: row.cnt for row in counts_result}

    response = []
    for u in users:
        response.append(
            AdminUserListResponse(
                id=u.id,  # type: ignore[arg-type]
                email=u.email,  # type: ignore[arg-type]
                full_name=u.full_name,  # type: ignore[arg-type]
                is_active=u.is_active,  # type: ignore[arg-type]
                is_superuser=u.is_superuser,  # type: ignore[arg-type]
                subscription_tier=u.subscription_tier,  # type: ignore[arg-type]
                subscription_status=u.subscription_status,  # type: ignore[arg-type]
                google_id=u.google_id,  # type: ignore[arg-type]
                oauth_provider=u.oauth_provider,  # type: ignore[arg-type]
                last_login_at=u.last_login_at,  # type: ignore[arg-type]
                created_at=u.created_at,  # type: ignore[arg-type]
                mail_account_count=counts.get(u.id, 0),  # type: ignore[arg-type]
            )
        )
    return response


@router.get("/users/{user_id}", response_model=UserDetailResponse)
async def get_user(
    user_id: int,
    current_user: User = Depends(get_current_superuser),
    db: AsyncSession = Depends(get_db),
):
    """Get a specific user's details (admin only)"""
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )
    return user


@router.put("/users/{user_id}", response_model=UserDetailResponse)
async def update_user(
    user_id: int,
    user_update: AdminUserUpdate,
    current_user: User = Depends(get_current_superuser),
    db: AsyncSession = Depends(get_db),
):
    """Update a user's details, plan, or admin status (admin only)"""
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )

    if user_update.full_name is not None:
        user.full_name = user_update.full_name  # type: ignore[assignment]
    if user_update.email is not None:
        user.email = user_update.email  # type: ignore[assignment]
    if user_update.is_active is not None:
        user.is_active = user_update.is_active  # type: ignore[assignment]
    if user_update.is_superuser is not None:
        user.is_superuser = user_update.is_superuser  # type: ignore[assignment]
    if user_update.subscription_tier is not None:
        user.subscription_tier = SubscriptionTier(user_update.subscription_tier.value)  # type: ignore[assignment]
    if user_update.subscription_status is not None:
        user.subscription_status = user_update.subscription_status  # type: ignore[assignment]

    await db.commit()
    await db.refresh(user)
    return user


@router.delete("/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(
    user_id: int,
    current_user: User = Depends(get_current_superuser),
    db: AsyncSession = Depends(get_db),
):
    """Delete a user and all their data (admin only)"""
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )
    if user.id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete your own account via admin endpoint",
        )
    await db.delete(user)
    await db.commit()


# ── Plan management ────────────────────────────────────────────────────────────


@router.get("/plans", response_model=List[SubscriptionPlanResponse])
async def list_all_plans(
    current_user: User = Depends(get_current_superuser),
    db: AsyncSession = Depends(get_db),
):
    """List all subscription plans including inactive ones (admin only)"""
    result = await db.execute(select(SubscriptionPlan).order_by(SubscriptionPlan.tier))
    return result.scalars().all()


@router.post(
    "/plans",
    response_model=SubscriptionPlanResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_plan(
    plan_in: SubscriptionPlanCreate,
    current_user: User = Depends(get_current_superuser),
    db: AsyncSession = Depends(get_db),
):
    """Create a new subscription plan (admin only)"""
    existing = await db.execute(
        select(SubscriptionPlan).where(
            SubscriptionPlan.tier == SubscriptionTier(plan_in.tier.value)
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"A plan for tier '{plan_in.tier.value}' already exists",
        )

    plan = SubscriptionPlan(
        tier=SubscriptionTier(plan_in.tier.value),
        name=plan_in.name,
        description=plan_in.description,
        price_monthly=plan_in.price_monthly,
        price_yearly=plan_in.price_yearly,
        max_mail_accounts=plan_in.max_mail_accounts,
        max_emails_per_day=plan_in.max_emails_per_day,
        check_interval_minutes=plan_in.check_interval_minutes,
        support_level=plan_in.support_level,
        features=plan_in.features,
        is_active=plan_in.is_active,
    )
    db.add(plan)
    await db.commit()
    await db.refresh(plan)
    return plan


@router.put("/plans/{plan_id}", response_model=SubscriptionPlanResponse)
async def update_plan(
    plan_id: int,
    plan_update: SubscriptionPlanUpdate,
    current_user: User = Depends(get_current_superuser),
    db: AsyncSession = Depends(get_db),
):
    """Update a subscription plan's limits or pricing (admin only)"""
    result = await db.execute(
        select(SubscriptionPlan).where(SubscriptionPlan.id == plan_id)
    )
    plan = result.scalar_one_or_none()
    if not plan:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Plan not found"
        )

    if plan_update.name is not None:
        plan.name = plan_update.name  # type: ignore[assignment]
    if plan_update.description is not None:
        plan.description = plan_update.description  # type: ignore[assignment]
    if plan_update.price_monthly is not None:
        plan.price_monthly = plan_update.price_monthly  # type: ignore[assignment]
    if plan_update.price_yearly is not None:
        plan.price_yearly = plan_update.price_yearly  # type: ignore[assignment]
    if plan_update.max_mail_accounts is not None:
        plan.max_mail_accounts = plan_update.max_mail_accounts  # type: ignore[assignment]
    if plan_update.max_emails_per_day is not None:
        plan.max_emails_per_day = plan_update.max_emails_per_day  # type: ignore[assignment]
    if plan_update.check_interval_minutes is not None:
        plan.check_interval_minutes = plan_update.check_interval_minutes  # type: ignore[assignment]
    if plan_update.support_level is not None:
        plan.support_level = plan_update.support_level  # type: ignore[assignment]
    if plan_update.features is not None:
        plan.features = plan_update.features  # type: ignore[assignment]
    if plan_update.is_active is not None:
        plan.is_active = plan_update.is_active  # type: ignore[assignment]

    await db.commit()
    await db.refresh(plan)
    return plan


@router.delete("/plans/{plan_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_plan(
    plan_id: int,
    current_user: User = Depends(get_current_superuser),
    db: AsyncSession = Depends(get_db),
):
    """Delete a subscription plan (admin only)"""
    result = await db.execute(
        select(SubscriptionPlan).where(SubscriptionPlan.id == plan_id)
    )
    plan = result.scalar_one_or_none()
    if not plan:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Plan not found"
        )
    await db.delete(plan)
    await db.commit()


# ── Admin notification config management ──────────────────────────────────────


@router.get("/notifications", response_model=List[AdminNotificationConfigResponse])
async def list_admin_notification_configs(
    current_user: User = Depends(get_current_superuser),
    db: AsyncSession = Depends(get_db),
):
    """List all admin notification configurations (admin only)"""
    result = await db.execute(select(AdminNotificationConfig))
    return result.scalars().all()


@router.post(
    "/notifications",
    response_model=AdminNotificationConfigResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_admin_notification_config(
    config_in: AdminNotificationConfigCreate,
    current_user: User = Depends(get_current_superuser),
    db: AsyncSession = Depends(get_db),
):
    """Create a new admin notification configuration (admin only)"""
    config = AdminNotificationConfig(**config_in.dict())
    db.add(config)
    await db.commit()
    await db.refresh(config)
    return config


@router.get(
    "/notifications/{config_id}", response_model=AdminNotificationConfigResponse
)
async def get_admin_notification_config(
    config_id: int,
    current_user: User = Depends(get_current_superuser),
    db: AsyncSession = Depends(get_db),
):
    """Get a specific admin notification configuration (admin only)"""
    result = await db.execute(
        select(AdminNotificationConfig).where(AdminNotificationConfig.id == config_id)
    )
    config = result.scalar_one_or_none()
    if not config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Admin notification config not found",
        )
    return config


@router.put(
    "/notifications/{config_id}", response_model=AdminNotificationConfigResponse
)
async def update_admin_notification_config(
    config_id: int,
    config_in: AdminNotificationConfigUpdate,
    current_user: User = Depends(get_current_superuser),
    db: AsyncSession = Depends(get_db),
):
    """Update an admin notification configuration (admin only)"""
    result = await db.execute(
        select(AdminNotificationConfig).where(AdminNotificationConfig.id == config_id)
    )
    config = result.scalar_one_or_none()
    if not config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Admin notification config not found",
        )

    update_data = config_in.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(config, field, value)

    await db.commit()
    await db.refresh(config)
    return config


@router.delete("/notifications/{config_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_admin_notification_config(
    config_id: int,
    current_user: User = Depends(get_current_superuser),
    db: AsyncSession = Depends(get_db),
):
    """Delete an admin notification configuration (admin only)"""
    result = await db.execute(
        select(AdminNotificationConfig).where(AdminNotificationConfig.id == config_id)
    )
    config = result.scalar_one_or_none()
    if not config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Admin notification config not found",
        )
    await db.delete(config)
    await db.commit()


@router.post("/notifications/test", response_model=NotificationTestResponse)
async def test_admin_notification_config(
    request: NotificationTestRequest,
    current_user: User = Depends(get_current_superuser),
):
    """Test an admin notification channel by sending a test message (admin only)"""
    success, message = await test_notification(request.apprise_url)
    return NotificationTestResponse(success=success, message=message)
# ── Admin Logs ─────────────────────────────────────────────────────────────────


def _admin_paginate(total: int, page: int, page_size: int) -> dict:
    pages = max(1, math.ceil(total / page_size)) if total else 1
    return {"total": total, "page": page, "page_size": page_size, "pages": pages}


@router.get(
    "/processing-runs",
    response_model=PaginatedAdminRunsResponse,
    summary="List all processing runs across all users (admin only)",
)
async def admin_list_processing_runs(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    user_id: Optional[int] = Query(None, description="Filter by user ID"),
    account_id: Optional[int] = Query(None, description="Filter by mail account ID"),
    status_filter: Optional[str] = Query(
        None,
        alias="status",
        description="Filter by run status",
    ),
    current_user: User = Depends(get_current_superuser),
    db: AsyncSession = Depends(get_db),
):
    """
    Return a paginated list of all processing runs in the system with
    GDPR-masked user / account email addresses.
    """
    base = (
        select(
            ProcessingRun,
            MailAccount.name.label("account_name"),
            MailAccount.email_address.label("account_email"),
            MailAccount.user_id.label("uid"),
            User.email.label("user_email"),
        )
        .join(MailAccount, ProcessingRun.mail_account_id == MailAccount.id)
        .join(User, MailAccount.user_id == User.id)
    )

    if user_id is not None:
        base = base.where(MailAccount.user_id == user_id)
    if account_id is not None:
        base = base.where(ProcessingRun.mail_account_id == account_id)
    if status_filter:
        base = base.where(ProcessingRun.status == status_filter)

    total = (
        await db.execute(select(func.count()).select_from(base.subquery()))
    ).scalar_one()
    offset = (page - 1) * page_size
    rows = (
        await db.execute(
            base.order_by(ProcessingRun.started_at.desc())
            .offset(offset)
            .limit(page_size)
        )
    ).all()

    items = [
        AdminProcessingRunResponse(
            id=row.ProcessingRun.id,  # type: ignore[arg-type]
            mail_account_id=row.ProcessingRun.mail_account_id,  # type: ignore[arg-type]
            started_at=row.ProcessingRun.started_at,  # type: ignore[arg-type]
            completed_at=row.ProcessingRun.completed_at,  # type: ignore[arg-type]
            duration_seconds=row.ProcessingRun.duration_seconds,  # type: ignore[arg-type]
            emails_fetched=row.ProcessingRun.emails_fetched,  # type: ignore[arg-type]
            emails_forwarded=row.ProcessingRun.emails_forwarded,  # type: ignore[arg-type]
            emails_failed=row.ProcessingRun.emails_failed,  # type: ignore[arg-type]
            status=row.ProcessingRun.status,  # type: ignore[arg-type]
            error_message=row.ProcessingRun.error_message,  # type: ignore[arg-type]
            account_name=row.account_name,
            account_email=mask_email(row.account_email) if row.account_email else None,
            user_id=row.uid,
            user_email=mask_email(row.user_email) if row.user_email else None,
        )
        for row in rows
    ]

    return PaginatedAdminRunsResponse(
        items=items, **_admin_paginate(total, page, page_size)  # type: ignore[arg-type]
    )


@router.get(
    "/processing-logs",
    response_model=PaginatedAdminLogsResponse,
    summary="List all per-email processing logs across all users (admin only)",
)
async def admin_list_processing_logs(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    user_id: Optional[int] = Query(None, description="Filter by user ID"),
    account_id: Optional[int] = Query(None, description="Filter by mail account ID"),
    run_id: Optional[int] = Query(None, description="Filter by processing run ID"),
    level: Optional[str] = Query(
        None, description="Filter by level (INFO, WARNING, ERROR)"
    ),
    current_user: User = Depends(get_current_superuser),
    db: AsyncSession = Depends(get_db),
):
    """
    Return paginated per-email log entries with GDPR-masked sender addresses.
    Subject lines are shown as-is (the user owns their own mail content);
    sender addresses are pseudonymised for operator privacy.
    """
    base = select(
        ProcessingLog,
        User.email.label("user_email"),
    ).join(User, ProcessingLog.user_id == User.id)

    if user_id is not None:
        base = base.where(ProcessingLog.user_id == user_id)
    if account_id is not None:
        base = base.where(ProcessingLog.mail_account_id == account_id)
    if run_id is not None:
        base = base.where(ProcessingLog.processing_run_id == run_id)
    if level:
        base = base.where(ProcessingLog.level == level.upper())

    total = (
        await db.execute(select(func.count()).select_from(base.subquery()))
    ).scalar_one()
    offset = (page - 1) * page_size
    rows = (
        await db.execute(
            base.order_by(ProcessingLog.timestamp.desc())
            .offset(offset)
            .limit(page_size)
        )
    ).all()

    items = [
        AdminProcessingLogResponse(
            id=row.ProcessingLog.id,  # type: ignore[arg-type]
            timestamp=row.ProcessingLog.timestamp,  # type: ignore[arg-type]
            level=row.ProcessingLog.level,  # type: ignore[arg-type]
            message=row.ProcessingLog.message,  # type: ignore[arg-type]
            email_subject=row.ProcessingLog.email_subject,  # type: ignore[arg-type]
            email_from=(
                mask_from_header(row.ProcessingLog.email_from)
                if row.ProcessingLog.email_from
                else None
            ),
            success=row.ProcessingLog.success,  # type: ignore[arg-type]
            mail_account_id=row.ProcessingLog.mail_account_id,  # type: ignore[arg-type]
            processing_run_id=row.ProcessingLog.processing_run_id,  # type: ignore[arg-type]
            email_size_bytes=row.ProcessingLog.email_size_bytes,  # type: ignore[arg-type]
            error_details=row.ProcessingLog.error_details,  # type: ignore[arg-type]
            user_id=row.ProcessingLog.user_id,  # type: ignore[arg-type]
            user_email=mask_email(row.user_email) if row.user_email else None,
        )
        for row in rows
    ]

    return PaginatedAdminLogsResponse(
        items=items, **_admin_paginate(total, page, page_size)  # type: ignore[arg-type]
    )
