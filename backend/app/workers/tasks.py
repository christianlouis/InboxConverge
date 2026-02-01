"""
Celery tasks for background email processing.
"""
import asyncio
from datetime import datetime, timedelta
from typing import List
from celery import Task
import logging

from app.workers.celery_app import celery_app
from app.core.database import async_session_maker
from app.core.security import decrypt_credential
from app.models.database_models import MailAccount, ProcessingRun, ProcessingLog, AccountStatus
from app.services.mail_processor import MailProcessor
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


class AsyncTask(Task):
    """Base task class that handles async operations"""
    
    def __call__(self, *args, **kwargs):
        """Run async task in event loop"""
        loop = asyncio.get_event_loop()
        return loop.run_until_complete(self.run(*args, **kwargs))


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
                status="running"
            )
            db.add(run)
            await db.commit()
            await db.refresh(run)
            
            # Decrypt password
            password = decrypt_credential(account.encrypted_password)
            
            # Create processor
            processor = MailProcessor(account, password)
            
            # Fetch emails
            emails = await processor.fetch_emails(account.max_emails_per_check)
            
            run.emails_fetched = len(emails)
            
            # Forward emails
            emails_forwarded = 0
            emails_failed = 0
            
            # TODO: Get SMTP config from user settings or environment
            smtp_config = {
                "host": "smtp.gmail.com",
                "port": 587,
                "username": "smtp_user@gmail.com",  # Should come from config
                "password": "smtp_password",  # Should come from config
                "use_tls": True
            }
            
            for email_data in emails:
                try:
                    success = await MailProcessor.forward_email(
                        email_data,
                        account.name,
                        account.forward_to,
                        smtp_config
                    )
                    
                    if success:
                        emails_forwarded += 1
                    else:
                        emails_failed += 1
                        
                except Exception as e:
                    logger.error(f"Error forwarding email: {e}")
                    emails_failed += 1
            
            # Update run
            run.emails_forwarded = emails_forwarded
            run.emails_failed = emails_failed
            run.completed_at = datetime.utcnow()
            run.duration_seconds = (run.completed_at - run.started_at).total_seconds()
            run.status = "completed" if emails_failed == 0 else "partial_failure"
            
            # Update account
            account.total_emails_processed += emails_forwarded
            account.total_emails_failed += emails_failed
            account.last_check_at = datetime.utcnow()
            
            if emails_failed == 0:
                account.last_successful_check_at = datetime.utcnow()
                account.status = AccountStatus.ACTIVE
            else:
                account.status = AccountStatus.ERROR
                account.last_error_at = datetime.utcnow()
                account.last_error_message = f"{emails_failed} emails failed to forward"
            
            await db.commit()
            
            logger.info(
                f"Processed account {account.id}: "
                f"{emails_forwarded} forwarded, {emails_failed} failed"
            )
            
        except Exception as e:
            logger.error(f"Error processing account {account_id}: {e}")
            
            # Mark run as failed
            if 'run' in locals():
                run.status = "failed"
                run.error_message = str(e)
                run.completed_at = datetime.utcnow()
                run.duration_seconds = (run.completed_at - run.started_at).total_seconds()
                
                # Update account error status
                if 'account' in locals():
                    account.status = AccountStatus.ERROR
                    account.last_error_at = datetime.utcnow()
                    account.last_error_message = str(e)
                
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
                        MailAccount.is_enabled == True,
                        MailAccount.status.in_([AccountStatus.ACTIVE, AccountStatus.TESTING])
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
                    if time_since_last_check.total_seconds() < (account.check_interval_minutes * 60):
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
