"""
Application configuration using Pydantic settings.

Supports a hybrid configuration model:
  • **Bootstrap settings** (DATABASE_URL, SECRET_KEY, ENCRYPTION_KEY)
    are always loaded from environment variables or ``.env`` files.
  • **Application settings** (SMTP, processing, Gmail API, etc.)
    can be managed in the database via the ``AppSetting`` model and
    the ``/api/v1/settings`` admin endpoints.  When a setting exists
    in the database it takes precedence over environment variables.

See ``app.services.config_service.ConfigService`` for the runtime
lookup logic and ``app.models.database_models.AppSetting`` for the
database model.
"""

from typing import Optional, List
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import field_validator


class Settings(BaseSettings):
    """Application settings loaded from environment variables"""

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", case_sensitive=False, extra="ignore"
    )

    # Application
    APP_NAME: str = "InboxRescue"
    APP_VERSION: str = "2.0.0"
    DEBUG: bool = False
    API_V1_PREFIX: str = "/api/v1"

    # Server
    HOST: str = "0.0.0.0"
    PORT: int = 8000

    # Database
    DATABASE_URL: str = (
        "postgresql+asyncpg://user:password@localhost:5432/pop3_forwarder"
    )
    DATABASE_POOL_SIZE: int = 20
    DATABASE_MAX_OVERFLOW: int = 10

    # Security
    SECRET_KEY: str = "change-this-to-a-secure-random-secret-key-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # Encryption (for storing POP3/IMAP credentials)
    ENCRYPTION_KEY: str = "change-this-to-a-secure-encryption-key"

    # OAuth2 - Google
    GOOGLE_CLIENT_ID: Optional[str] = None
    GOOGLE_CLIENT_SECRET: Optional[str] = None
    GOOGLE_REDIRECT_URI: str = "http://localhost:3000/auth/callback/google"

    # Gmail API (for direct email injection)
    GMAIL_API_ENABLED: bool = True
    GMAIL_INJECT_LABEL_IDS: List[str] = ["INBOX"]

    # CORS
    CORS_ORIGINS: List[str] = ["http://localhost:3000", "http://localhost:8000"]

    # Stripe Payment
    STRIPE_API_KEY: Optional[str] = None
    STRIPE_WEBHOOK_SECRET: Optional[str] = None
    STRIPE_PUBLISHABLE_KEY: Optional[str] = None

    # Subscription Tiers
    TIER_FREE_MAX_ACCOUNTS: int = 1
    TIER_BASIC_MAX_ACCOUNTS: int = 5
    TIER_PRO_MAX_ACCOUNTS: int = 20
    TIER_ENTERPRISE_MAX_ACCOUNTS: int = 100

    # Email Processing
    MAX_EMAILS_PER_RUN: int = 50
    CHECK_INTERVAL_MINUTES: int = 5
    THROTTLE_EMAILS_PER_MINUTE: int = 10

    # Redis (for Celery and caching)
    REDIS_URL: str = "redis://localhost:6379/0"

    # Celery
    CELERY_BROKER_URL: str = "redis://localhost:6379/0"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/0"

    # Apprise (notifications)
    APPRISE_ENABLED: bool = True

    # Logging
    LOG_LEVEL: str = "INFO"

    # Admin
    ADMIN_EMAIL: Optional[str] = "christianlouis@gmail.com"
    ADMIN_PASSWORD: Optional[str] = None

    # Mail Server Presets
    MAIL_SERVER_PRESETS_FILE: str = "app/data/mail_server_presets.json"

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: str | List[str]) -> List[str]:
        """Parse CORS origins from environment variable"""
        if isinstance(v, str):
            return [i.strip() for i in v.split(",")]
        return v

    @field_validator("SECRET_KEY")
    @classmethod
    def validate_secret_key(cls, v: str) -> str:
        """Validate that SECRET_KEY is changed from default and is secure"""
        default_keys = [
            "change-this-to-a-secure-random-secret-key-in-production",
            "secret",
            "secret-key",
            "secretkey",
        ]
        if v.lower() in default_keys:
            raise ValueError(
                "SECRET_KEY must be changed from default value! "
                "Generate a secure key with: python -c 'import secrets; print(secrets.token_urlsafe(32))'"
            )
        if len(v) < 32:
            raise ValueError(
                f"SECRET_KEY must be at least 32 characters long (current: {len(v)}). "
                "Generate a secure key with: python -c 'import secrets; print(secrets.token_urlsafe(32))'"
            )
        return v

    @field_validator("ENCRYPTION_KEY")
    @classmethod
    def validate_encryption_key(cls, v: str) -> str:
        """Validate that ENCRYPTION_KEY is changed from default and is secure"""
        default_keys = [
            "change-this-to-a-secure-encryption-key",
            "encryption",
            "encryption-key",
            "encryptionkey",
        ]
        if v.lower() in default_keys:
            raise ValueError(
                "ENCRYPTION_KEY must be changed from default value! "
                "Generate a secure key with: python -c 'import secrets; print(secrets.token_urlsafe(32))'"
            )
        if len(v) < 32:
            raise ValueError(
                f"ENCRYPTION_KEY must be at least 32 characters long (current: {len(v)}). "
                "Generate a secure key with: python -c 'import secrets; print(secrets.token_urlsafe(32))'"
            )
        return v


# Global settings instance
settings = Settings()
