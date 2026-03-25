"""Mail account management endpoints"""

from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc

from app.core.database import get_db
from app.core.deps import get_current_active_user
from app.core.security import encrypt_credential
from app.models.database_models import User, MailAccount, AccountStatus
from app.models.schemas import (
    MailAccountCreate,
    MailAccountResponse,
    MailAccountUpdate,
    MailAccountTestRequest,
    MailAccountTestResponse,
    MailAccountAutoDetectRequest,
    MailAccountAutoDetectResponse,
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

    # Check subscription limits
    result = await db.execute(
        select(MailAccount).where(MailAccount.user_id == current_user.id)
    )
    existing_accounts = result.scalars().all()

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
        update_data["encrypted_password"] = encrypt_credential(
            update_data.pop("password")
        )

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
