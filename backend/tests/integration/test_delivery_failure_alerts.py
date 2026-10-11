"""Database-backed regression tests for delivery failure handling."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.models.database_models import (
    AccountStatus,
    DeliveryMethod,
    DownloadedMessageId,
    MailAccount,
    ProcessingRun,
)
from app.workers import tasks


@pytest.mark.asyncio
async def test_missing_delivery_method_marks_account_and_alerts(
    db_engine, db_session: AsyncSession, test_user
):
    """A missing SMTP fallback must use the persisted error notification path."""

    account = MailAccount(
        user_id=test_user.id,
        name="Production Gmail source",
        email_address="source@example.com",
        protocol="POP3_SSL",
        host="pop.example.com",
        port=995,
        use_ssl=True,
        username="source@example.com",
        encrypted_password="encrypted-source-password",
        forward_to="destination@example.com",
        delivery_method=DeliveryMethod.GMAIL_API,
        is_enabled=True,
    )
    db_session.add(account)
    await db_session.commit()
    await db_session.refresh(account)

    task_sessionmaker = async_sessionmaker(
        db_engine, class_=AsyncSession, expire_on_commit=False
    )
    processor = MagicMock()
    processor.fetch_emails = AsyncMock(
        return_value=([b"From: sender@example.com\r\n\r\nmessage"], ["uid-1"])
    )
    notification_state = {}

    async def record_notification(**kwargs):
        async with task_sessionmaker() as verify_notification_db:
            notification_account = await verify_notification_db.scalar(
                select(MailAccount).where(MailAccount.id == account.id)
            )
            notification_state["status"] = notification_account.status
            notification_state["last_error_message"] = (
                notification_account.last_error_message
            )
        return 1

    notify = AsyncMock(side_effect=record_notification)

    with (
        patch.object(tasks, "async_session_maker", task_sessionmaker),
        patch.object(tasks, "decrypt_credential", return_value="source-password"),
        patch.object(tasks, "MailProcessor", return_value=processor),
        patch.object(
            tasks.ConfigService,
            "get_smtp_config",
            new_callable=AsyncMock,
            return_value={
                "host": "smtp.example.com",
                "port": 587,
                "username": "",
                "password": "",
                "use_tls": True,
            },
        ),
        patch.object(tasks, "send_user_notification", notify),
    ):
        await tasks.process_mail_account.run(account.id)

    async with task_sessionmaker() as verify_db:
        saved_account = await verify_db.scalar(
            select(MailAccount).where(MailAccount.id == account.id)
        )
        saved_run = await verify_db.scalar(
            select(ProcessingRun).where(ProcessingRun.mail_account_id == account.id)
        )
        saved_uid = await verify_db.scalar(
            select(DownloadedMessageId).where(
                DownloadedMessageId.mail_account_id == account.id
            )
        )

    assert saved_account.status == AccountStatus.ERROR
    assert "No delivery method configured" in saved_account.last_error_message
    assert saved_account.last_successful_check_at is None
    assert saved_account.error_notification_sent is True
    assert saved_run.status == "failed"
    assert "No delivery method configured" in saved_run.error_message
    assert saved_uid is None
    assert notification_state["status"] == AccountStatus.ERROR
    assert "No delivery method configured" in notification_state["last_error_message"]
    notify.assert_awaited_once_with(
        db=notify.await_args.kwargs["db"],
        user_id=test_user.id,
        title="InboxRescue: Mail Processing Error",
        body="InboxRescue could not process mail account 'Production Gmail source'. "
        "Check the account status and logs.",
        notify_on_error=True,
    )
