"""Mail account management endpoints"""

import math
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc, func

from app.core.database import get_db
from app.core.deps import get_current_active_user
from app.core.security import encrypt_credential
from app.models.database_models import (
    User,
    MailAccount,
    ProcessingLog,
    ProcessingRun,
    AccountStatus,
    SubscriptionPlan,
)
from app.models.schemas import (
    MailAccountCreate,
    MailAccountResponse,
    MailAccountUpdate,
    MailAccountTestRequest,
    MailAccountTestResponse,
    MailAccountAutoDetectRequest,
    MailAccountAutoDetectResponse,
    PaginatedProcessingRunsResponse,
    PaginatedProcessingLogsResponse,
    ProcessingRunDetailResponse,
    ProcessingLogDetailResponse,
)
from app.services.mail_processor import MailProcessor, MailServerAutoDetect
from app.core.config import settings

router = APIRouter()


@router.post(
    "", response_model=MailAccountResponse, status_code=status.HTTP_201_CREATED
)
async def create_mail_account(
    account_in: MailAccountCreate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a new mail account"""

    # Superusers are not subject to subscription limits
    if not current_user.is_superuser:
        # Count existing accounts for this user
        result = await db.execute(
            select(MailAccount).where(MailAccount.user_id == current_user.id)
        )
        existing_accounts = result.scalars().all()

        # Try to look up the limit from the active SubscriptionPlan in the DB first
        # so that admin-managed plan limits take effect immediately.
        plan_result = await db.execute(
            select(SubscriptionPlan).where(
                SubscriptionPlan.tier == current_user.subscription_tier,
                SubscriptionPlan.is_active.is_(True),
            )
        )
        plan = plan_result.scalar_one_or_none()

        if plan is not None:
            max_accounts = plan.max_mail_accounts
        else:
            # Fall back to env-var / config values when no plan row exists
            tier_limits = {
                "free": settings.TIER_FREE_MAX_ACCOUNTS,
                "basic": settings.TIER_BASIC_MAX_ACCOUNTS,
                "pro": settings.TIER_PRO_MAX_ACCOUNTS,
                "enterprise": settings.TIER_ENTERPRISE_MAX_ACCOUNTS,
            }
            max_accounts = tier_limits.get(current_user.subscription_tier.value, 1)

        if len(existing_accounts) >= max_accounts:
            raise HTTPException(
                status_code=status.HTTP_402_PAYMENT_REQUIRED,
                detail="Account limit reached. Upgrade your subscription to add more accounts.",
            )

    # Encrypt password
    encrypted_password = encrypt_credential(account_in.password)

    # Create account
    account = MailAccount(
        user_id=current_user.id,
        name=account_in.name,
        email_address=account_in.email_address,
        protocol=account_in.protocol,
        host=account_in.host,
        port=account_in.port,
        use_ssl=account_in.use_ssl,
        use_tls=account_in.use_tls,
        username=account_in.username,
        encrypted_password=encrypted_password,
        forward_to=account_in.forward_to,
        delivery_method=account_in.delivery_method,
        is_enabled=account_in.is_enabled,
        check_interval_minutes=account_in.check_interval_minutes,
        max_emails_per_check=account_in.max_emails_per_check,
        delete_after_forward=account_in.delete_after_forward,
    )

    db.add(account)
    await db.commit()
    await db.refresh(account)

    return account


@router.get("", response_model=List[MailAccountResponse])
async def list_mail_accounts(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """List all mail accounts for current user"""
    result = await db.execute(
        select(MailAccount)
        .where(MailAccount.user_id == current_user.id)
        .order_by(desc(MailAccount.created_at))
    )
    accounts = result.scalars().all()
    return accounts


@router.get("/{account_id}", response_model=MailAccountResponse)
async def get_mail_account(
    account_id: int,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Get a specific mail account"""
    result = await db.execute(
        select(MailAccount).where(
            MailAccount.id == account_id, MailAccount.user_id == current_user.id
        )
    )
    account = result.scalar_one_or_none()

    if not account:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Mail account not found"
        )

    return account


@router.put("/{account_id}", response_model=MailAccountResponse)
async def update_mail_account(
    account_id: int,
    account_update: MailAccountUpdate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Update a mail account"""
    result = await db.execute(
        select(MailAccount).where(
            MailAccount.id == account_id, MailAccount.user_id == current_user.id
        )
    )
    account = result.scalar_one_or_none()

    if not account:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Mail account not found"
        )

    # Update fields
    update_data = account_update.model_dump(exclude_unset=True)

    if "password" in update_data:
        password = update_data.pop("password")
        if password:  # Only update when a non-empty password is provided
            update_data["encrypted_password"] = encrypt_credential(password)

    for field, value in update_data.items():
        setattr(account, field, value)

    await db.commit()
    await db.refresh(account)

    return account


@router.delete("/{account_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_mail_account(
    account_id: int,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete a mail account"""
    result = await db.execute(
        select(MailAccount).where(
            MailAccount.id == account_id, MailAccount.user_id == current_user.id
        )
    )
    account = result.scalar_one_or_none()

    if not account:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Mail account not found"
        )

    await db.delete(account)
    await db.commit()


@router.patch("/{account_id}/toggle", response_model=MailAccountResponse)
async def toggle_mail_account(
    account_id: int,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Toggle the enabled/disabled state of a mail account"""
    result = await db.execute(
        select(MailAccount).where(
            MailAccount.id == account_id, MailAccount.user_id == current_user.id
        )
    )
    account = result.scalar_one_or_none()

    if not account:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Mail account not found"
        )

    account.is_enabled = not account.is_enabled  # type: ignore[assignment]

    # When re-enabling a previously errored account, reset status to ACTIVE
    # so the scheduler picks it up on the next run.
    if account.is_enabled and account.status == AccountStatus.ERROR:
        account.status = AccountStatus.ACTIVE  # type: ignore[assignment]

    await db.commit()
    await db.refresh(account)

    return account


@router.post("/test", response_model=MailAccountTestResponse)
async def test_mail_connection(
    test_request: MailAccountTestRequest,
    current_user: User = Depends(get_current_active_user),
):
    """Test connection to mail server"""

    # Create temporary account for testing
    temp_account = MailAccount(
        user_id=current_user.id,
        name="test",
        email_address="test@test.com",
        protocol=test_request.protocol,
        host=test_request.host,
        port=test_request.port,
        use_ssl=test_request.use_ssl,
        use_tls=test_request.use_tls,
        username=test_request.username,
        encrypted_password="",  # Not used for test
        forward_to="test@test.com",
    )

    processor = MailProcessor(temp_account, test_request.password)
    success, message = await processor.test_connection()

    return MailAccountTestResponse(success=success, message=message)


@router.post("/auto-detect", response_model=MailAccountAutoDetectResponse)
async def auto_detect_mail_settings(
    detect_request: MailAccountAutoDetectRequest,
    current_user: User = Depends(get_current_active_user),
):
    """Auto-detect mail server settings for an email address"""

    suggestions = MailServerAutoDetect.detect(detect_request.email_address)

    return MailAccountAutoDetectResponse(
        success=len(suggestions) > 0, suggestions=suggestions
    )


# ---------------------------------------------------------------------------
# Per-account processing runs & logs
# ---------------------------------------------------------------------------


@router.get(
    "/{account_id}/processing-runs",
    response_model=PaginatedProcessingRunsResponse,
    summary="List processing runs for a specific mail account",
)
async def list_account_runs(
    account_id: int,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    has_emails: Optional[bool] = Query(
        None,
        description="When true, only return runs that fetched at least one email",
    ),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Return paginated processing runs for a mail account owned by the user."""
    result = await db.execute(
        select(MailAccount).where(
            MailAccount.id == account_id,
            MailAccount.user_id == current_user.id,
        )
    )
    account = result.scalar_one_or_none()
    if not account:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Mail account not found"
        )

    base = select(ProcessingRun).where(ProcessingRun.mail_account_id == account_id)
    if has_emails is True:
        base = base.where(ProcessingRun.emails_fetched > 0)
    total = (
        await db.execute(select(func.count()).select_from(base.subquery()))
    ).scalar_one()

    offset = (page - 1) * page_size
    runs = (
        (
            await db.execute(
                base.order_by(desc(ProcessingRun.started_at))
                .offset(offset)
                .limit(page_size)
            )
        )
        .scalars()
        .all()
    )

    pages = max(1, math.ceil(total / page_size)) if total else 1
    items = [
        ProcessingRunDetailResponse(
            id=r.id,  # type: ignore[arg-type]
            mail_account_id=r.mail_account_id,  # type: ignore[arg-type]
            started_at=r.started_at,  # type: ignore[arg-type]
            completed_at=r.completed_at,  # type: ignore[arg-type]
            duration_seconds=r.duration_seconds,  # type: ignore[arg-type]
            emails_fetched=r.emails_fetched,  # type: ignore[arg-type]
            emails_forwarded=r.emails_forwarded,  # type: ignore[arg-type]
            emails_failed=r.emails_failed,  # type: ignore[arg-type]
            status=r.status,  # type: ignore[arg-type]
            error_message=r.error_message,  # type: ignore[arg-type]
            account_name=account.name,  # type: ignore[arg-type]
            account_email=account.email_address,  # type: ignore[arg-type]
        )
        for r in runs
    ]
    return PaginatedProcessingRunsResponse(
        items=items, total=total, page=page, page_size=page_size, pages=pages
    )


@router.get(
    "/{account_id}/logs",
    response_model=PaginatedProcessingLogsResponse,
    summary="List processing logs for a specific mail account",
)
async def list_account_logs(
    account_id: int,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    level: Optional[str] = Query(
        None, description="Filter by log level (INFO, WARNING, ERROR)"
    ),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Return paginated per-email log entries for a mail account owned by the user."""
    result = await db.execute(
        select(MailAccount).where(
            MailAccount.id == account_id,
            MailAccount.user_id == current_user.id,
        )
    )
    account = result.scalar_one_or_none()
    if not account:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Mail account not found"
        )

    base = select(ProcessingLog).where(
        ProcessingLog.mail_account_id == account_id,
        ProcessingLog.user_id == current_user.id,  # type: ignore[arg-type]
    )
    if level:
        base = base.where(ProcessingLog.level == level.upper())

    total = (
        await db.execute(select(func.count()).select_from(base.subquery()))
    ).scalar_one()

    offset = (page - 1) * page_size
    logs = (
        (
            await db.execute(
                base.order_by(ProcessingLog.timestamp.desc())
                .offset(offset)
                .limit(page_size)
            )
        )
        .scalars()
        .all()
    )

    pages = max(1, math.ceil(total / page_size)) if total else 1
    items = [
        ProcessingLogDetailResponse(
            id=log.id,  # type: ignore[arg-type]
            timestamp=log.timestamp,  # type: ignore[arg-type]
            level=log.level,  # type: ignore[arg-type]
            message=log.message,  # type: ignore[arg-type]
            email_subject=log.email_subject,  # type: ignore[arg-type]
            email_from=log.email_from,  # type: ignore[arg-type]
            success=log.success,  # type: ignore[arg-type]
            mail_account_id=log.mail_account_id,  # type: ignore[arg-type]
            processing_run_id=log.processing_run_id,  # type: ignore[arg-type]
            email_size_bytes=log.email_size_bytes,  # type: ignore[arg-type]
            error_details=log.error_details,  # type: ignore[arg-type]
        )
        for log in logs
    ]
    return PaginatedProcessingLogsResponse(
        items=items, total=total, page=page, page_size=page_size, pages=pages
    )
