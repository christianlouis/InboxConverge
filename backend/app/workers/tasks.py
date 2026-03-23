"""
Celery tasks for background email processing.
"""

import asyncio
import os
from datetime import datetime, timedelta
from celery import Task
import logging

from app.workers.celery_app import celery_app
from app.core.database import async_session_maker
from app.core.security import decrypt_credential
from app.models.database_models import (
    MailAccount,
    ProcessingRun,
    ProcessingLog,
    AccountStatus,
    DeliveryMethod,
    GmailCredential,
)
from app.services.mail_processor import MailProcessor
from app.services.gmail_service import GmailService, GmailInjectionError
from app.core.config import settings
from sqlalchemy import select, and_

logger = logging.getLogger(__name__)


class AsyncTask(Task):
    """Base task class that handles async operations"""

    def __call__(self, *args, **kwargs):
        """Run async task in event loop"""
        # Use asyncio.run() for better event loop management
        return asyncio.run(self.run(*args, **kwargs))


@celery_app.task(base=AsyncTask, name="app.workers.tasks.process_mail_account")
async def process_mail_account(account_id: int):
    """
    Process a single mail account - fetch and forward emails.

    Args:
        account_id: ID of mail account to process
    """
    async with async_session_maker() as db:
        try:
            # Get account
            result = await db.execute(
                select(MailAccount).where(MailAccount.id == account_id)
            )
            account = result.scalar_one_or_none()

            if not account or not account.is_enabled:
                logger.warning(f"Account {account_id} not found or disabled")
                return

            # Create processing run
            run = ProcessingRun(
                mail_account_id=account.id,
                started_at=datetime.utcnow(),
                status="running",
            )
            db.add(run)
            await db.commit()
            await db.refresh(run)

            # Decrypt password
            password = decrypt_credential(account.encrypted_password)  # type: ignore[arg-type]

            # Create processor
            processor = MailProcessor(account, password)

            # Fetch emails
            emails = await processor.fetch_emails(account.max_emails_per_check)  # type: ignore[arg-type]

            run.emails_fetched = len(emails)  # type: ignore[assignment]

            # Forward emails
            emails_forwarded = 0
            emails_failed = 0

            # Determine delivery method
            use_gmail_api = account.delivery_method == DeliveryMethod.GMAIL_API

            gmail_service = None
            smtp_config = None

            if use_gmail_api:
                # Get user's Gmail credentials
                gmail_cred_result = await db.execute(
                    select(GmailCredential).where(
                        GmailCredential.user_id == account.user_id,
                        GmailCredential.is_valid == True,  # noqa: E712
                    )
                )
                gmail_cred = gmail_cred_result.scalar_one_or_none()

                if gmail_cred:
                    access_token = decrypt_credential(gmail_cred.encrypted_access_token)  # type: ignore[arg-type]
                    refresh_token = (
                        decrypt_credential(gmail_cred.encrypted_refresh_token)  # type: ignore[arg-type]
                        if gmail_cred.encrypted_refresh_token
                        else None
                    )
                    gmail_service = GmailService(
                        access_token=access_token,
                        refresh_token=refresh_token,
                        client_id=settings.GOOGLE_CLIENT_ID,
                        client_secret=settings.GOOGLE_CLIENT_SECRET,
                    )
                else:
                    logger.warning(
                        f"Gmail API credentials not found for user {account.user_id}, "
                        f"falling back to SMTP for account {account.id}"
                    )
                    use_gmail_api = False  # type: ignore[assignment]

            if not use_gmail_api:
                # Fall back to SMTP
                smtp_config = {
                    "host": os.getenv("SMTP_HOST", "smtp.gmail.com"),
                    "port": int(os.getenv("SMTP_PORT", "587")),
                    "username": os.getenv("SMTP_USER", ""),
                    "password": os.getenv("SMTP_PASSWORD", ""),
                    "use_tls": os.getenv("SMTP_USE_TLS", "true").lower() == "true",
                }

                if not smtp_config["username"] or not smtp_config["password"]:
                    logger.error(
                        f"SMTP credentials not configured for account {account.id}"
                    )
                    run.status = "failed"  # type: ignore[assignment]
                    run.error_message = "No delivery method configured (SMTP credentials missing and Gmail API not set up)"  # type: ignore[assignment]
                    await db.commit()
                    return

            for email_data in emails:
                try:
                    if use_gmail_api and gmail_service:
                        # Inject via Gmail API (preferred)
                        await gmail_service.inject_email(
                            raw_email=email_data,
                            label_ids=["INBOX"],
                            source_account_name=account.name,  # type: ignore[arg-type]
                        )
                        emails_forwarded += 1
                    else:
                        # Forward via SMTP (fallback)
                        success = await MailProcessor.forward_email(
                            email_data, account.name, account.forward_to, smtp_config  # type: ignore[arg-type]
                        )
                        if success:
                            emails_forwarded += 1
                        else:
                            emails_failed += 1

                except (GmailInjectionError, Exception) as e:
                    logger.error(f"Error delivering email: {e}")
                    emails_failed += 1

            # Update run
            run.emails_forwarded = emails_forwarded  # type: ignore[assignment]
            run.emails_failed = emails_failed  # type: ignore[assignment]
            run.completed_at = datetime.utcnow()  # type: ignore[assignment]
            run.duration_seconds = (run.completed_at - run.started_at).total_seconds()
            run.status = "completed" if emails_failed == 0 else "partial_failure"  # type: ignore[assignment]

            # Update account
            account.total_emails_processed += emails_forwarded  # type: ignore[assignment]
            account.total_emails_failed += emails_failed  # type: ignore[assignment]
            account.last_check_at = datetime.utcnow()  # type: ignore[assignment]

            if emails_failed == 0:
                account.last_successful_check_at = datetime.utcnow()  # type: ignore[assignment]
                account.status = AccountStatus.ACTIVE  # type: ignore[assignment]
            else:
                account.status = AccountStatus.ERROR  # type: ignore[assignment]
                account.last_error_at = datetime.utcnow()  # type: ignore[assignment]
                account.last_error_message = f"{emails_failed} emails failed to forward"  # type: ignore[assignment]

            await db.commit()

            logger.info(
                f"Processed account {account.id}: "
                f"{emails_forwarded} forwarded, {emails_failed} failed"
            )

        except Exception as e:
            logger.error(f"Error processing account {account_id}: {e}")

            # Mark run as failed
            if "run" in locals():
                run.status = "failed"  # type: ignore[assignment]
                run.error_message = str(e)  # type: ignore[assignment]
                run.completed_at = datetime.utcnow()  # type: ignore[assignment]
                run.duration_seconds = (
                    run.completed_at - run.started_at
                ).total_seconds()

                # Update account error status
                if "account" in locals() and account is not None:
                    account.status = AccountStatus.ERROR  # type: ignore[assignment]
                    account.last_error_at = datetime.utcnow()  # type: ignore[assignment]
                    account.last_error_message = str(e)  # type: ignore[assignment]

                await db.commit()


@celery_app.task(base=AsyncTask, name="app.workers.tasks.process_all_enabled_accounts")
async def process_all_enabled_accounts():
    """
    Process all enabled mail accounts.
    This task is scheduled to run periodically.
    """
    async with async_session_maker() as db:
        try:
            # Get all enabled accounts
            result = await db.execute(
                select(MailAccount).where(
                    and_(
                        MailAccount.is_enabled == True,  # noqa: E712
                        MailAccount.status.in_(
                            [AccountStatus.ACTIVE, AccountStatus.TESTING]
                        ),
                    )
                )
            )
            accounts = result.scalars().all()

            logger.info(f"Processing {len(accounts)} enabled mail accounts")

            # Process each account
            for account in accounts:
                # Check if it's time to check this account
                if account.last_check_at:
                    time_since_last_check = datetime.utcnow() - account.last_check_at
                    if time_since_last_check.total_seconds() < (
                        account.check_interval_minutes * 60
                    ):
                        logger.debug(f"Skipping account {account.id} - not time yet")
                        continue

                # Queue processing task
                process_mail_account.delay(account.id)

        except Exception as e:
            logger.error(f"Error processing accounts: {e}")


@celery_app.task(base=AsyncTask, name="app.workers.tasks.cleanup_old_logs")
async def cleanup_old_logs(days_to_keep: int = 30):
    """
    Clean up old processing logs and runs.

    Args:
        days_to_keep: Number of days of logs to retain
    """
    async with async_session_maker() as db:
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=days_to_keep)

            # Delete old processing runs
            result = await db.execute(
                select(ProcessingRun).where(ProcessingRun.started_at < cutoff_date)
            )
            old_runs = result.scalars().all()

            for run in old_runs:
                await db.delete(run)

            # Delete old processing logs
            result = await db.execute(
                select(ProcessingLog).where(ProcessingLog.timestamp < cutoff_date)
            )
            old_logs = result.scalars().all()

            for log in old_logs:
                await db.delete(log)

            await db.commit()

            logger.info(
                f"Cleaned up {len(old_runs)} old processing runs and "
                f"{len(old_logs)} old logs"
            )

        except Exception as e:
            logger.error(f"Error cleaning up logs: {e}")
