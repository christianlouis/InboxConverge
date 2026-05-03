"""
Celery application for background email processing tasks.
"""

from celery import Celery
from celery.schedules import crontab
import logging

from app.core.config import settings

logger = logging.getLogger(__name__)

# Suppress noisy INFO-level "ignored untagged response" messages from aioimaplib
logging.getLogger("aioimaplib").setLevel(logging.WARNING)

# Create Celery app
celery_app = Celery(
    "inboxconverge",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=["app.workers.tasks"],
)

# Celery configuration
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=30 * 60,  # 30 minutes
    task_soft_time_limit=25 * 60,  # 25 minutes
    worker_prefetch_multiplier=1,
    worker_max_tasks_per_child=1000,
)

# Periodic tasks schedule
celery_app.conf.beat_schedule = {
    "process-all-mail-accounts": {
        "task": "app.workers.tasks.process_all_enabled_accounts",
        "schedule": crontab(
            minute="*"
        ),  # Every minute (per-account interval gates actual work)
    },
    "refresh-gmail-tokens": {
        "task": "app.workers.tasks.refresh_gmail_tokens",
        "schedule": crontab(minute="*/45"),  # Every 45 minutes
    },
    "cleanup-old-logs": {
        "task": "app.workers.tasks.cleanup_old_logs",
        "schedule": crontab(hour=3, minute=0),  # Daily at 3 AM
    },
}


@celery_app.task(bind=True)
def debug_task(self):
    """Debug task to test Celery"""
    logger.info(f"Request: {self.request!r}")
    return "Celery is working!"
