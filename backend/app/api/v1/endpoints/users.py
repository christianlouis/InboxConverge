"""User management endpoints"""

import asyncio
import smtplib
from email.mime.text import MIMEText
from email.utils import formatdate, make_msgid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db
from app.core.deps import get_current_active_user
from app.core.security import encrypt_credential, decrypt_credential
from app.models.database_models import User, UserSmtpConfig
from app.models.schemas import (
    UserDetailResponse,
    UserUpdate,
    UserSmtpConfigUpdate,
    UserSmtpConfigResponse,
    SmtpTestResponse,
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


@router.post("/smtp-config/test", response_model=SmtpTestResponse)
async def test_smtp_config(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Send a test email using the current user's saved SMTP configuration"""
    result = await db.execute(
        select(UserSmtpConfig).where(UserSmtpConfig.user_id == current_user.id)
    )
    config = result.scalar_one_or_none()

    if not config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No SMTP configuration found. Save one first.",
        )

    if not config.encrypted_password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No SMTP password stored. Save the configuration with a password first.",
        )

    password = decrypt_credential(config.encrypted_password)  # type: ignore[arg-type]
    recipient = current_user.email  # type: ignore[arg-type]

    def _send_test() -> None:
        msg = MIMEText(
            "This is a test email sent by InboxConverge to verify your SMTP settings.",
            "plain",
            "utf-8",
        )
        msg["From"] = config.username  # type: ignore[index]
        msg["To"] = recipient
        msg["Date"] = formatdate(localtime=True)
        msg["Message-ID"] = make_msgid()
        msg["Subject"] = "InboxConverge – SMTP Test"

        if config.use_tls:  # type: ignore[union-attr]
            server: smtplib.SMTP = smtplib.SMTP(
                config.host, config.port, timeout=30  # type: ignore[arg-type]
            )
            server.starttls()
        else:
            server = smtplib.SMTP_SSL(
                config.host, config.port, timeout=30  # type: ignore[arg-type]
            )

        try:
            server.login(config.username, password)  # type: ignore[arg-type]
            server.send_message(msg)
        finally:
            try:
                server.quit()
            except Exception:
                pass

    try:
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, _send_test)
        return SmtpTestResponse(
            success=True,
            message=f"Test email sent successfully to {recipient}.",
        )
    except smtplib.SMTPAuthenticationError as exc:
        smtp_err = exc.smtp_error
        detail = (
            smtp_err.decode(errors="replace")
            if isinstance(smtp_err, bytes)
            else str(exc)
        )
        return SmtpTestResponse(
            success=False,
            message=f"Authentication failed: {detail}",
        )
    except smtplib.SMTPException as exc:
        return SmtpTestResponse(success=False, message=f"SMTP error: {exc}")
    except OSError as exc:
        return SmtpTestResponse(
            success=False,
            message=f"Connection error: {exc}",
        )
