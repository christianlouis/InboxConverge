"""
Configuration service for hybrid env + database settings.

Provides a unified interface for reading application configuration.
Settings are resolved in this order:
  1. Database (app_settings table) — highest priority
  2. Environment variables / .env file — fallback
  3. Hard-coded defaults — last resort

Bootstrap settings (DATABASE_URL, SECRET_KEY, ENCRYPTION_KEY) always
come from environment variables because the database connection itself
depends on them.
"""

import json
import logging
import os
from typing import Any, Dict, List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.database_models import AppSetting, SubscriptionPlan, SubscriptionTier

logger = logging.getLogger(__name__)

# Settings that MUST come from env vars (bootstrap / chicken-and-egg)
BOOTSTRAP_KEYS = frozenset(
    {
        "DATABASE_URL",
        "DATABASE_POOL_SIZE",
        "DATABASE_MAX_OVERFLOW",
        "SECRET_KEY",
        "ENCRYPTION_KEY",
    }
)

# Default settings to seed into the database on first run
DEFAULT_SETTINGS: List[Dict[str, Any]] = [
    # SMTP / Forwarding
    {
        "key": "SMTP_HOST",
        "value": "smtp.gmail.com",
        "value_type": "string",
        "description": "SMTP server hostname for email forwarding",
        "is_secret": False,
        "category": "smtp",
    },
    {
        "key": "SMTP_PORT",
        "value": "587",
        "value_type": "int",
        "description": "SMTP server port",
        "is_secret": False,
        "category": "smtp",
    },
    {
        "key": "SMTP_USER",
        "value": "",
        "value_type": "string",
        "description": "SMTP username for authentication",
        "is_secret": False,
        "category": "smtp",
    },
    {
        "key": "SMTP_PASSWORD",
        "value": "",
        "value_type": "string",
        "description": "SMTP password for authentication",
        "is_secret": True,
        "category": "smtp",
    },
    {
        "key": "SMTP_USE_TLS",
        "value": "true",
        "value_type": "bool",
        "description": "Whether to use STARTTLS for SMTP connections",
        "is_secret": False,
        "category": "smtp",
    },
    # Email Processing
    {
        "key": "MAX_EMAILS_PER_RUN",
        "value": "50",
        "value_type": "int",
        "description": "Maximum emails to process per account per run",
        "is_secret": False,
        "category": "processing",
    },
    {
        "key": "CHECK_INTERVAL_MINUTES",
        "value": "5",
        "value_type": "int",
        "description": "Default interval between mail checks (minutes)",
        "is_secret": False,
        "category": "processing",
    },
    {
        "key": "THROTTLE_EMAILS_PER_MINUTE",
        "value": "10",
        "value_type": "int",
        "description": "Rate limit for email forwarding",
        "is_secret": False,
        "category": "processing",
    },
    # Gmail API
    {
        "key": "GMAIL_API_ENABLED",
        "value": "true",
        "value_type": "bool",
        "description": "Enable Gmail API for direct email injection (preferred over SMTP)",
        "is_secret": False,
        "category": "gmail",
    },
    {
        "key": "GMAIL_INJECT_LABEL_IDS",
        "value": '["INBOX"]',
        "value_type": "json",
        "description": "Gmail label IDs to apply when injecting emails via API",
        "is_secret": False,
        "category": "gmail",
    },
    # Notifications
    {
        "key": "APPRISE_ENABLED",
        "value": "true",
        "value_type": "bool",
        "description": "Enable Apprise multi-channel notifications",
        "is_secret": False,
        "category": "notifications",
    },
    # Logging
    {
        "key": "LOG_LEVEL",
        "value": "INFO",
        "value_type": "string",
        "description": "Application log level (DEBUG, INFO, WARNING, ERROR)",
        "is_secret": False,
        "category": "general",
    },
]


def _cast_value(raw: str, value_type: str) -> Any:
    """Cast a raw string value to its declared type."""
    if raw is None:
        return None
    if value_type == "int":
        return int(raw)
    if value_type == "float":
        return float(raw)
    if value_type == "bool":
        return raw.lower() in ("true", "1", "yes")
    if value_type == "json":
        return json.loads(raw)
    return raw  # string


class ConfigService:
    """
    Hybrid configuration service: database-first with env-var fallback.

    Usage::

        value = await ConfigService.get("SMTP_HOST", db=session)
        smtp_config = await ConfigService.get_smtp_config(db=session)
    """

    @staticmethod
    async def get(
        key: str,
        db: Optional[AsyncSession] = None,
        default: Any = None,
    ) -> Any:
        """
        Retrieve a single setting value.

        Resolution order: database → environment variable → *default*.
        Bootstrap keys (DATABASE_URL, SECRET_KEY, ENCRYPTION_KEY) skip the
        database lookup entirely.
        """
        if key not in BOOTSTRAP_KEYS and db is not None:
            try:
                result = await db.execute(
                    select(AppSetting).where(AppSetting.key == key)
                )
                setting = result.scalar_one_or_none()
                if setting is not None and setting.value is not None:
                    return _cast_value(
                        setting.value,  # type: ignore[arg-type]
                        setting.value_type or "string",  # type: ignore[arg-type]
                    )
            except Exception as exc:
                logger.warning(
                    "DB lookup failed for key=%s, falling back to env: %s",
                    key,
                    exc,
                )

        env_val = os.getenv(key)
        if env_val is not None:
            return env_val

        return default

    @staticmethod
    async def get_many(
        keys: List[str],
        db: Optional[AsyncSession] = None,
    ) -> Dict[str, Any]:
        """Retrieve multiple settings at once."""
        result: Dict[str, Any] = {}
        if db is not None:
            try:
                db_result = await db.execute(
                    select(AppSetting).where(AppSetting.key.in_(keys))
                )
                for setting in db_result.scalars().all():
                    result[setting.key] = _cast_value(  # type: ignore[index]
                        setting.value,  # type: ignore[arg-type]
                        setting.value_type or "string",  # type: ignore[arg-type]
                    )
            except Exception as exc:
                logger.warning("DB bulk lookup failed, falling back to env: %s", exc)

        for key in keys:
            if key not in result:
                env_val = os.getenv(key)
                if env_val is not None:
                    result[key] = env_val

        return result

    @staticmethod
    async def set(
        key: str,
        value: str,
        db: AsyncSession,
        value_type: str = "string",
        description: Optional[str] = None,
        is_secret: bool = False,
        category: Optional[str] = None,
    ) -> AppSetting:
        """Create or update a setting in the database."""
        if key in BOOTSTRAP_KEYS:
            raise ValueError(
                f"'{key}' is a bootstrap setting and cannot be stored in the database. "
                "Set it via environment variables instead."
            )

        result = await db.execute(select(AppSetting).where(AppSetting.key == key))
        existing = result.scalar_one_or_none()

        if existing:
            existing.value = value  # type: ignore[assignment]
            if value_type:
                existing.value_type = value_type  # type: ignore[assignment]
            if description is not None:
                existing.description = description  # type: ignore[assignment]
            existing.is_secret = is_secret  # type: ignore[assignment]
            if category is not None:
                existing.category = category  # type: ignore[assignment]
            await db.commit()
            await db.refresh(existing)
            return existing

        setting = AppSetting(
            key=key,
            value=value,
            value_type=value_type,
            description=description,
            is_secret=is_secret,
            category=category,
        )
        db.add(setting)
        await db.commit()
        await db.refresh(setting)
        return setting

    @staticmethod
    async def delete(key: str, db: AsyncSession) -> bool:
        """Delete a setting from the database."""
        if key in BOOTSTRAP_KEYS:
            raise ValueError(
                f"'{key}' is a bootstrap setting and cannot be deleted from the database."
            )
        result = await db.execute(select(AppSetting).where(AppSetting.key == key))
        existing = result.scalar_one_or_none()
        if existing:
            await db.delete(existing)
            await db.commit()
            return True
        return False

    @staticmethod
    async def list_all(
        db: AsyncSession,
        category: Optional[str] = None,
    ) -> List[AppSetting]:
        """List all settings, optionally filtered by category."""
        query = select(AppSetting).order_by(AppSetting.category, AppSetting.key)
        if category:
            query = query.where(AppSetting.category == category)
        result = await db.execute(query)
        return list(result.scalars().all())

    # ── convenience helpers ─────────────────────────────────────────

    @staticmethod
    async def get_smtp_config(db: Optional[AsyncSession] = None) -> Dict[str, Any]:
        """Return a ready-to-use SMTP configuration dict."""
        keys = ["SMTP_HOST", "SMTP_PORT", "SMTP_USER", "SMTP_PASSWORD", "SMTP_USE_TLS"]
        values = await ConfigService.get_many(keys, db=db)
        return {
            "host": values.get("SMTP_HOST", "smtp.gmail.com"),
            "port": int(values.get("SMTP_PORT", 587)),
            "username": values.get("SMTP_USER", ""),
            "password": values.get("SMTP_PASSWORD", ""),
            "use_tls": str(values.get("SMTP_USE_TLS", "true")).lower()
            in ("true", "1", "yes"),
        }

    @staticmethod
    async def seed_defaults(db: AsyncSession) -> int:
        """
        Populate the database with default settings (skip existing keys).

        Returns the number of settings created.
        """
        created = 0
        for item in DEFAULT_SETTINGS:
            result = await db.execute(
                select(AppSetting).where(AppSetting.key == item["key"])
            )
            if result.scalar_one_or_none() is None:
                db.add(AppSetting(**item))
                created += 1
        if created:
            await db.commit()
        logger.info("Seeded %d default settings into the database", created)

        # Seed default subscription plans
        await ConfigService.seed_default_plans(db)

        return created

    @staticmethod
    async def seed_default_plans(db: AsyncSession) -> int:
        """
        Populate the database with default subscription plans (skip existing tiers).

        Limits mirror the env-var defaults so behaviour is unchanged on first boot
        but can be overridden by admins via the plan management UI.

        Returns the number of plans created.
        """
        from app.core.config import settings  # local import to avoid circular deps

        default_plans = [
            {
                "tier": SubscriptionTier.FREE,
                "name": "Free",
                "description": "Dip your toes in. One old inbox pulled into Gmail, checked every 30 minutes. Free forever, no card needed.",
                "price_monthly": 0.0,
                "price_yearly": 0.0,
                "max_mail_accounts": settings.TIER_FREE_MAX_ACCOUNTS,
                "max_emails_per_day": 100,
                "check_interval_minutes": 30,
                "support_level": "community",
                "is_active": True,
            },
            {
                "tier": SubscriptionTier.BASIC,
                "name": "Good",
                "description": "Got a handful of dusty inboxes you just can't let go of? This one's for you. Less than a coffee per month.",
                "price_monthly": 0.99,
                "price_yearly": 9.90,
                "max_mail_accounts": settings.TIER_BASIC_MAX_ACCOUNTS,
                "max_emails_per_day": 1000,
                "check_interval_minutes": 15,
                "support_level": "email",
                "is_active": True,
            },
            {
                "tier": SubscriptionTier.PRO,
                "name": "Better",
                "description": "You're clearly the type who keeps every email address you've ever had. Respect. Checked every 5 minutes.",
                "price_monthly": 1.99,
                "price_yearly": 19.90,
                "max_mail_accounts": settings.TIER_PRO_MAX_ACCOUNTS,
                "max_emails_per_day": 10000,
                "check_interval_minutes": 5,
                "support_level": "email",
                "is_active": True,
            },
            {
                "tier": SubscriptionTier.ENTERPRISE,
                "name": "Best",
                "description": "Every old inbox you've ever had, all landing neatly in Gmail, checked every minute. The full works.",
                "price_monthly": 2.99,
                "price_yearly": 29.90,
                "max_mail_accounts": settings.TIER_ENTERPRISE_MAX_ACCOUNTS,
                "max_emails_per_day": 100000,
                "check_interval_minutes": 1,
                "support_level": "email",
                "is_active": True,
            },
        ]

        created = 0
        for plan_data in default_plans:
            result = await db.execute(
                select(SubscriptionPlan).where(
                    SubscriptionPlan.tier == plan_data["tier"]
                )
            )
            if result.scalar_one_or_none() is None:
                db.add(SubscriptionPlan(**plan_data))
                created += 1

        if created:
            await db.commit()
        logger.info("Seeded %d default subscription plans into the database", created)
        return created
