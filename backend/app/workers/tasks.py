"""
Celery tasks for background email processing.
"""

import asyncio
import email as email_lib
import time
from datetime import datetime, timedelta, timezone
from celery import Task
import logging

from app.workers.celery_app import celery_app
from app.core.database import async_session_maker, engine
from app.core.security import decrypt_credential, encrypt_credential
from app.core.metrics import (
    MAIL_PROCESSING_RUNS_TOTAL,
    MAIL_PROCESSING_EMAILS_TOTAL,
    MAIL_PROCESSING_DURATION_SECONDS,
    ACTIVE_MAIL_ACCOUNTS,
    GMAIL_CREDENTIALS_INVALIDATED_TOTAL,
    CELERY_TASKS_TOTAL,
    CELERY_TASK_DURATION_SECONDS,
)
from app.models.database_models import (
    MailAccount,
    ProcessingRun,
    ProcessingLog,
    AccountStatus,
    DeliveryMethod,
    GmailCredential,
    DownloadedMessageId,
    UserSmtpConfig,
)
from app.services.mail_processor import MailProcessor
from app.services.gmail_service import GmailService
from app.services.config_service import ConfigService
from app.services.notification_service import send_user_notification
from app.core.config import settings
from sqlalchemy import select, delete

logger = logging.getLogger(__name__)


def _as_utc(dt: datetime) -> datetime:
    """Return *dt* with UTC tzinfo, attaching it if the datetime is naive."""
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


class AsyncTask(Task):
    """Base task class that handles async operations"""

    def __call__(self, *args, **kwargs):
        """Run async task in event loop"""

        async def _run():
            try:
                return await self.run(*args, **kwargs)
            finally:
                # Dispose the connection pool before the event loop closes.
                # Each asyncio.run() creates a fresh event loop; if pooled
                # asyncpg connections are still open when the loop is torn
                # down, asyncpg raises "Exception terminating connection".
                # Disposing the engine here closes those connections cleanly
                # inside the same loop, before asyncio.run() shuts it down.
                await engine.dispose()

        return asyncio.run(_run())


@celery_app.task(base=AsyncTask, name="app.workers.tasks.process_mail_account")
async def process_mail_account(account_id: int):
    """
    Process a single mail account - fetch and forward emails.

    Args:
        account_id: ID of mail account to process
    """
    _task_start = time.monotonic()
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
                started_at=datetime.now(timezone.utc),
                status="running",
            )
            db.add(run)
            await db.commit()
            await db.refresh(run)

            # Decrypt password
            password = decrypt_credential(account.encrypted_password)  # type: ignore[arg-type]

            # Load already-downloaded UIDs to prevent re-processing
            seen_result = await db.execute(
                select(DownloadedMessageId.message_uid).where(
                    DownloadedMessageId.mail_account_id == account.id
                )
            )
            already_seen_uids = set(seen_result.scalars().all())

            # Create processor
            processor = MailProcessor(account, password)

            # Fetch emails (returns raw bytes + new UIDs)
            emails, new_uids = await processor.fetch_emails(
                account.max_emails_per_check,  # type: ignore[arg-type]
                already_seen_uids=already_seen_uids,
            )

            run.emails_fetched = len(emails)  # type: ignore[assignment]
            MAIL_PROCESSING_EMAILS_TOTAL.labels(operation="fetched").inc(len(emails))

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
                # Fall back to SMTP – check per-user config first, then global
                user_smtp_result = await db.execute(
                    select(UserSmtpConfig).where(
                        UserSmtpConfig.user_id == account.user_id
                    )
                )
                user_smtp = user_smtp_result.scalar_one_or_none()

                if user_smtp and user_smtp.username and user_smtp.encrypted_password:
                    smtp_config = {
                        "host": user_smtp.host,
                        "port": user_smtp.port,
                        "username": user_smtp.username,
                        "password": decrypt_credential(user_smtp.encrypted_password),  # type: ignore[arg-type]
                        "use_tls": user_smtp.use_tls,
                    }
                else:
                    smtp_config = await ConfigService.get_smtp_config(db=db)

                if not smtp_config["username"] or not smtp_config["password"]:
                    logger.error(
                        f"SMTP credentials not configured for account {account.id}"
                    )
                    run.status = "failed"  # type: ignore[assignment]
                    run.error_message = "No delivery method configured (SMTP credentials missing and Gmail API not set up)"  # type: ignore[assignment]
                    await db.commit()
                    return

            successfully_forwarded_uids: list[str] = []

            if len(emails) != len(new_uids):
                logger.error(
                    f"emails/uids length mismatch ({len(emails)} vs {len(new_uids)}) "
                    f"for account {account.id}; truncating to shorter list"
                )

            # Field length limits matching the DB column definitions
            _MAX_SUBJECT_LEN = 500
            _MAX_FROM_LEN = 255

            for email_data, uid in zip(emails, new_uids):
                # ── Parse email metadata for logging ───────────────────────
                email_subject: str | None = None
                email_from: str | None = None
                try:
                    msg = email_lib.message_from_bytes(email_data)
                    raw_subject = msg.get("Subject", "") or ""
                    email_subject = (
                        raw_subject[:_MAX_SUBJECT_LEN] if raw_subject else None
                    )
                    raw_from = msg.get("From", "") or ""
                    email_from = raw_from[:_MAX_FROM_LEN] if raw_from else None
                except (ValueError, TypeError, UnicodeDecodeError) as exc:
                    logger.debug(
                        "Could not parse email headers for account %s: %s",
                        account.id,
                        exc,
                    )

                email_size_bytes = len(email_data)
                forwarded_ok = False
                error_msg: str | None = None

                try:
                    if use_gmail_api and gmail_service:
                        # Inject via Gmail API (preferred)
                        label_ids = await gmail_service.build_import_label_ids(
                            import_label_templates=gmail_cred.import_label_templates,
                            source_email=account.email_address,  # type: ignore[arg-type]
                        )
                        await gmail_service.inject_email(
                            raw_email=email_data,
                            label_ids=label_ids,
                            source_account_name=account.name,  # type: ignore[arg-type]
                        )
                        forwarded_ok = True
                        emails_forwarded += 1
                        successfully_forwarded_uids.append(uid)
                    else:
                        # Forward via SMTP (fallback)
                        success = await MailProcessor.forward_email(
                            email_data, account.name, account.forward_to, smtp_config  # type: ignore[arg-type]
                        )
                        if success:
                            forwarded_ok = True
                            emails_forwarded += 1
                            successfully_forwarded_uids.append(uid)
                        else:
                            emails_failed += 1

                except Exception as e:
                    error_str = str(e).lower()
                    # If Gmail returns 401/403 the refresh token was revoked –
                    # mark credentials invalid so the user gets notified.
                    if (
                        use_gmail_api
                        and gmail_cred
                        and (
                            "401" in error_str
                            or "403" in error_str
                            or "invalid_grant" in error_str
                        )
                    ):
                        gmail_cred.is_valid = False  # type: ignore[assignment]
                        GMAIL_CREDENTIALS_INVALIDATED_TOTAL.inc()
                        logger.warning(
                            f"Gmail credentials revoked for user {account.user_id}. "
                            "User must re-authorise."
                        )
                        try:
                            await send_user_notification(
                                db=db,
                                user_id=account.user_id,
                                title="InboxRescue: Gmail Authorization Expired",
                                body=f"Your Gmail credentials for account '{account.name}' have been revoked. Please re-authorize Gmail access in Settings.",
                                notify_on_error=True,
                            )
                        except Exception as notify_exc:
                            logger.warning(
                                f"Failed to send revocation notification: {notify_exc}"
                            )
                    logger.error(f"Error delivering email: {e}")
                    error_msg = str(e)
                    emails_failed += 1

                # ── Write per-email ProcessingLog entry ─────────────────────
                db.add(
                    ProcessingLog(
                        user_id=account.user_id,
                        mail_account_id=account.id,
                        processing_run_id=run.id,
                        level="INFO" if forwarded_ok else "ERROR",
                        message=(
                            f"Forwarded: {email_subject or '(no subject)'}"
                            if forwarded_ok
                            else f"Failed: {error_msg or 'delivery error'}"
                        ),
                        email_subject=email_subject,
                        email_from=email_from,
                        email_size_bytes=email_size_bytes,
                        success=forwarded_ok,
                        error_details={"error": error_msg} if error_msg else None,
                    )
                )

            # Persist new message UIDs so they are not processed again
            for uid in successfully_forwarded_uids:
                if uid not in already_seen_uids:
                    db.add(
                        DownloadedMessageId(
                            mail_account_id=account.id,
                            message_uid=uid,
                        )
                    )

            # If Gmail API was used, persist any refreshed access token back to
            # the DB so the next run doesn't need an extra token-refresh call.
            if use_gmail_api and gmail_service and gmail_cred:
                refreshed = gmail_service.get_refreshed_token()
                if refreshed and refreshed["access_token"] != access_token:
                    gmail_cred.encrypted_access_token = encrypt_credential(refreshed["access_token"])  # type: ignore[assignment]
                    if refreshed.get("expiry"):
                        gmail_cred.token_expiry = refreshed["expiry"]  # type: ignore[assignment]
                    gmail_cred.last_verified_at = datetime.now(timezone.utc)  # type: ignore[assignment]
                    logger.info(
                        f"Persisted refreshed Gmail access token for user {account.user_id}"
                    )

            # Update run
            run.emails_forwarded = emails_forwarded  # type: ignore[assignment]
            run.emails_failed = emails_failed  # type: ignore[assignment]
            run.completed_at = datetime.now(timezone.utc)  # type: ignore[assignment]
            run.duration_seconds = (
                run.completed_at - _as_utc(run.started_at)
            ).total_seconds()
            run.status = "completed" if emails_failed == 0 else "partial_failure"  # type: ignore[assignment]

            # Update account
            account.total_emails_processed += emails_forwarded  # type: ignore[assignment]
            account.total_emails_failed += emails_failed  # type: ignore[assignment]
            account.last_check_at = datetime.now(timezone.utc)  # type: ignore[assignment]

            if emails_failed == 0:
                account.last_successful_check_at = datetime.now(timezone.utc)  # type: ignore[assignment]
                account.status = AccountStatus.ACTIVE  # type: ignore[assignment]
            else:
                account.status = AccountStatus.ERROR  # type: ignore[assignment]
                account.last_error_at = datetime.now(timezone.utc)  # type: ignore[assignment]
                account.last_error_message = f"{emails_failed} emails failed to forward"  # type: ignore[assignment]
                try:
                    await send_user_notification(
                        db=db,
                        user_id=account.user_id,
                        title="InboxRescue: Mail Forwarding Failures",
                        body=f"Mail account '{account.name}': {emails_failed} email(s) failed to forward.",
                        notify_on_error=True,
                    )
                except Exception as notify_exc:
                    logger.warning(f"Failed to send notification: {notify_exc}")

            await db.commit()

            # Record Prometheus metrics for this completed run
            _run_status = "completed" if emails_failed == 0 else "partial_failure"
            MAIL_PROCESSING_RUNS_TOTAL.labels(status=_run_status).inc()
            MAIL_PROCESSING_EMAILS_TOTAL.labels(operation="forwarded").inc(
                emails_forwarded
            )
            MAIL_PROCESSING_EMAILS_TOTAL.labels(operation="failed").inc(emails_failed)
            _task_duration = time.monotonic() - _task_start
            MAIL_PROCESSING_DURATION_SECONDS.observe(_task_duration)
            CELERY_TASKS_TOTAL.labels(
                task_name="process_mail_account", status="success"
            ).inc()
            CELERY_TASK_DURATION_SECONDS.labels(
                task_name="process_mail_account"
            ).observe(_task_duration)

            logger.info(
                f"Processed account {account.id}: "
                f"{emails_forwarded} forwarded, {emails_failed} failed"
            )

        except Exception as e:
            logger.error(f"Error processing account {account_id}: {e}")

            # Record failure metric
            _task_duration = time.monotonic() - _task_start
            MAIL_PROCESSING_RUNS_TOTAL.labels(status="failed").inc()
            CELERY_TASKS_TOTAL.labels(
                task_name="process_mail_account", status="failure"
            ).inc()
            CELERY_TASK_DURATION_SECONDS.labels(
                task_name="process_mail_account"
            ).observe(_task_duration)

            # Mark run as failed
            if "run" in locals():
                run.status = "failed"  # type: ignore[assignment]
                run.error_message = str(e)  # type: ignore[assignment]
                run.completed_at = datetime.now(timezone.utc)  # type: ignore[assignment]
                run.duration_seconds = (
                    run.completed_at - _as_utc(run.started_at)
                ).total_seconds()

                # Update account error status
                if "account" in locals() and account is not None:
                    account.status = AccountStatus.ERROR  # type: ignore[assignment]
                    account.last_error_at = datetime.now(timezone.utc)  # type: ignore[assignment]
                    account.last_error_message = str(e)  # type: ignore[assignment]

                    # Notify user about the error
                    try:
                        await send_user_notification(
                            db=db,
                            user_id=account.user_id,
                            title="InboxRescue: Mail Processing Error",
                            body=f"Error processing mail account '{account.name}': {e}",
                            notify_on_error=True,
                        )
                    except Exception as notify_exc:
                        logger.warning(
                            f"Failed to send error notification: {notify_exc}"
                        )

                await db.commit()


@celery_app.task(base=AsyncTask, name="app.workers.tasks.process_all_enabled_accounts")
async def process_all_enabled_accounts():
    """
    Process all enabled mail accounts.
    This task is scheduled to run periodically.
    """
    _task_start = time.monotonic()
    async with async_session_maker() as db:
        try:
            # Fetch all enabled accounts regardless of operational status so
            # that accounts in ERROR state are retried automatically.
            result = await db.execute(
                select(MailAccount).where(
                    MailAccount.is_enabled == True,  # noqa: E712
                )
            )
            accounts = result.scalars().all()

            logger.info(f"Processing {len(accounts)} enabled mail accounts")
            ACTIVE_MAIL_ACCOUNTS.set(len(accounts))

            # Process each account
            for account in accounts:
                # Check if it's time to check this account
                if account.last_check_at:
                    time_since_last_check = (
                        datetime.now(timezone.utc) - account.last_check_at
                    )
                    if time_since_last_check.total_seconds() < (
                        account.check_interval_minutes * 60
                    ):
                        logger.debug(f"Skipping account {account.id} - not time yet")
                        continue

                # Queue processing task
                process_mail_account.delay(account.id)

            _task_duration = time.monotonic() - _task_start
            CELERY_TASKS_TOTAL.labels(
                task_name="process_all_enabled_accounts", status="success"
            ).inc()
            CELERY_TASK_DURATION_SECONDS.labels(
                task_name="process_all_enabled_accounts"
            ).observe(_task_duration)

        except Exception as e:
            logger.error(f"Error processing accounts: {e}")
            _task_duration = time.monotonic() - _task_start
            CELERY_TASKS_TOTAL.labels(
                task_name="process_all_enabled_accounts", status="failure"
            ).inc()
            CELERY_TASK_DURATION_SECONDS.labels(
                task_name="process_all_enabled_accounts"
            ).observe(_task_duration)


@celery_app.task(base=AsyncTask, name="app.workers.tasks.cleanup_old_logs")
async def cleanup_old_logs(days_to_keep: int = 30):
    """
    Clean up old processing logs, runs, and downloaded message ID records.

    Args:
        days_to_keep: Number of days of data to retain
    """
    _task_start = time.monotonic()
    async with async_session_maker() as db:
        try:
            cutoff_date = datetime.now(timezone.utc) - timedelta(days=days_to_keep)

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

            # Delete old downloaded message ID records so the table doesn't
            # grow unboundedly for accounts that never delete messages.
            await db.execute(
                delete(DownloadedMessageId).where(
                    DownloadedMessageId.downloaded_at < cutoff_date
                )
            )

            await db.commit()

            logger.info(
                f"Cleaned up {len(old_runs)} old processing runs and "
                f"{len(old_logs)} old logs"
            )

            _task_duration = time.monotonic() - _task_start
            CELERY_TASKS_TOTAL.labels(
                task_name="cleanup_old_logs", status="success"
            ).inc()
            CELERY_TASK_DURATION_SECONDS.labels(task_name="cleanup_old_logs").observe(
                _task_duration
            )

        except Exception as e:
            logger.error(f"Error cleaning up logs: {e}")
            _task_duration = time.monotonic() - _task_start
            CELERY_TASKS_TOTAL.labels(
                task_name="cleanup_old_logs", status="failure"
            ).inc()
            CELERY_TASK_DURATION_SECONDS.labels(task_name="cleanup_old_logs").observe(
                _task_duration
            )
