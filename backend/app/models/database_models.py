"""
Database models for the multi-tenant POP3 forwarder application.
"""

from datetime import datetime, timezone
from sqlalchemy import (
    Column,
    Integer,
    String,
    Boolean,
    DateTime,
    ForeignKey,
    Text,
    Enum as SQLEnum,
    JSON,
    Float,
    Index,
)
from sqlalchemy.orm import relationship

from app.utils.gmail_labels import (
    DEFAULT_IMPORT_LABEL_TEMPLATES,
    extract_granted_scopes,
    extract_import_label_templates,
)
import enum

from app.core.database import Base


class SubscriptionTier(str, enum.Enum):
    """Subscription tier levels"""

    FREE = "free"
    BASIC = "basic"
    PRO = "pro"
    ENTERPRISE = "enterprise"


class MailProtocol(str, enum.Enum):
    """Supported mail protocols"""

    POP3 = "pop3"
    POP3_SSL = "pop3_ssl"
    IMAP = "imap"
    IMAP_SSL = "imap_ssl"


class DeliveryMethod(str, enum.Enum):
    """How emails are delivered to Gmail"""

    SMTP = "smtp"  # Forward via SMTP (legacy)
    GMAIL_API = "gmail_api"  # Inject via Gmail API (preferred)


class AccountStatus(str, enum.Enum):
    """Mail account status"""

    ACTIVE = "active"
    INACTIVE = "inactive"
    ERROR = "error"
    TESTING = "testing"


class NotificationChannel(str, enum.Enum):
    """Notification channel types"""

    EMAIL = "email"
    TELEGRAM = "telegram"
    WEBHOOK = "webhook"
    SLACK = "slack"
    DISCORD = "discord"


class User(Base):
    """User model - represents a user account"""

    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    hashed_password = Column(
        String(255), nullable=True
    )  # Nullable for OAuth-only users
    full_name = Column(String(255))
    is_active = Column(Boolean, default=True)
    is_superuser = Column(Boolean, default=False)

    # OAuth
    google_id = Column(String(255), unique=True, index=True, nullable=True)
    oauth_provider = Column(String(50), nullable=True)

    # Subscription
    subscription_tier: Column[str] = Column(
        SQLEnum(SubscriptionTier), default=SubscriptionTier.FREE
    )
    subscription_status = Column(
        String(50), default="active"
    )  # active, canceled, past_due
    stripe_customer_id = Column(String(255), unique=True, nullable=True)
    stripe_subscription_id = Column(String(255), unique=True, nullable=True)
    subscription_expires_at = Column(DateTime(timezone=True), nullable=True)

    # Timestamps
    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    last_login_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    mail_accounts = relationship(
        "MailAccount", back_populates="user", cascade="all, delete-orphan"
    )
    notifications = relationship(
        "NotificationConfig", back_populates="user", cascade="all, delete-orphan"
    )
    logs = relationship(
        "ProcessingLog", back_populates="user", cascade="all, delete-orphan"
    )


class MailAccount(Base):
    """Mail account configuration (POP3/IMAP)"""

    __tablename__ = "mail_accounts"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )

    # Account details
    name = Column(String(255), nullable=False)  # User-friendly name
    email_address = Column(String(255), nullable=False)

    # Server configuration
    protocol: Column[str] = Column(SQLEnum(MailProtocol), default=MailProtocol.POP3_SSL)
    host = Column(String(255), nullable=False)
    port = Column(Integer, nullable=False)
    use_ssl = Column(Boolean, default=True)
    use_tls = Column(Boolean, default=False)

    # Credentials (encrypted)
    username = Column(String(255), nullable=False)
    encrypted_password = Column(Text, nullable=False)

    # Forwarding destination
    forward_to = Column(String(255), nullable=False)

    # Delivery method
    delivery_method: Column[str] = Column(
        SQLEnum(DeliveryMethod), default=DeliveryMethod.GMAIL_API
    )

    # Status and settings
    status: Column[str] = Column(SQLEnum(AccountStatus), default=AccountStatus.ACTIVE)
    is_enabled = Column(Boolean, default=True)
    check_interval_minutes = Column(Integer, default=5)
    max_emails_per_check = Column(Integer, default=50)
    delete_after_forward = Column(Boolean, default=True)

    # Auto-detection metadata
    provider_name = Column(String(100), nullable=True)  # e.g., "Gmail", "GMX"
    auto_detected = Column(Boolean, default=False)

    # Debug logging
    debug_logging = Column(Boolean, default=False)
    # Number of completed/partial_failure runs since debug_logging was last
    # enabled.  Resets to 0 when debug_logging is toggled True via the API.
    # debug_logging is auto-disabled once this reaches 5.
    debug_logging_run_count = Column(Integer, default=0)

    # Notification backoff: True once an error notification has been sent for
    # the current consecutive failure streak.  Cleared (with a recovery notice)
    # when a run succeeds so the next new failure streak triggers a fresh alert.
    error_notification_sent = Column(Boolean, default=False)

    # Statistics
    total_emails_processed = Column(Integer, default=0)
    total_emails_failed = Column(Integer, default=0)
    last_check_at = Column(DateTime(timezone=True), nullable=True)
    last_successful_check_at = Column(DateTime(timezone=True), nullable=True)
    last_error_at = Column(DateTime(timezone=True), nullable=True)
    last_error_message = Column(Text, nullable=True)

    # Timestamps
    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # Relationships
    user = relationship("User", back_populates="mail_accounts")
    processing_runs = relationship(
        "ProcessingRun", back_populates="mail_account", cascade="all, delete-orphan"
    )

    # Indexes
    __table_args__ = (
        Index("idx_user_email", "user_id", "email_address"),
        Index("idx_status_enabled", "status", "is_enabled"),
    )


class ProcessingRun(Base):
    """Records of email processing runs for each mail account"""

    __tablename__ = "processing_runs"

    id = Column(Integer, primary_key=True, index=True)
    mail_account_id = Column(
        Integer, ForeignKey("mail_accounts.id", ondelete="CASCADE"), nullable=False
    )

    # Run details
    started_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    completed_at = Column(DateTime(timezone=True), nullable=True)
    duration_seconds = Column(Float, nullable=True)

    # Results
    emails_fetched = Column(Integer, default=0)
    emails_forwarded = Column(Integer, default=0)
    emails_failed = Column(Integer, default=0)

    # Status
    status = Column(String(50), default="running")  # running, completed, failed
    error_message = Column(Text, nullable=True)

    # Relationships
    mail_account = relationship("MailAccount", back_populates="processing_runs")

    # Indexes
    __table_args__ = (Index("idx_account_started", "mail_account_id", "started_at"),)


class ProcessingLog(Base):
    """Detailed logs of individual email processing attempts"""

    __tablename__ = "processing_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    mail_account_id = Column(
        Integer, ForeignKey("mail_accounts.id", ondelete="CASCADE"), nullable=False
    )
    processing_run_id = Column(
        Integer, ForeignKey("processing_runs.id", ondelete="CASCADE"), nullable=True
    )

    # Log details
    timestamp = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
        index=True,
    )
    level = Column(String(20), nullable=False)  # INFO, WARNING, ERROR
    message = Column(Text, nullable=False)

    # Email metadata (if applicable)
    email_subject = Column(String(500), nullable=True)
    email_from = Column(String(255), nullable=True)
    email_size_bytes = Column(Integer, nullable=True)

    # Status
    success = Column(Boolean, default=True)
    error_details = Column(JSON, nullable=True)

    # Relationships
    user = relationship("User", back_populates="logs")

    # Indexes
    __table_args__ = (
        Index("idx_user_timestamp", "user_id", "timestamp"),
        Index("idx_account_timestamp", "mail_account_id", "timestamp"),
    )


class NotificationConfig(Base):
    """User notification channel configurations"""

    __tablename__ = "notification_configs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )

    name = Column(String(255), nullable=False, default="My Notification")
    apprise_url = Column(
        Text, nullable=True
    )  # The Apprise URL e.g. tgram://token/chatid

    # Channel details
    channel: Column[str] = Column(SQLEnum(NotificationChannel), nullable=False)
    is_enabled = Column(Boolean, default=True)

    # Channel-specific configuration (stored as JSON)
    config = Column(JSON, nullable=False)
    # Examples:
    # EMAIL: {"address": "user@example.com"}
    # TELEGRAM: {"bot_token": "xxx", "chat_id": "yyy"}
    # WEBHOOK: {"url": "https://example.com/webhook", "headers": {...}}

    # Notification preferences
    notify_on_errors = Column(Boolean, default=True)
    notify_on_success = Column(Boolean, default=False)
    notify_threshold = Column(Integer, default=3)  # Notify after N consecutive errors

    # Timestamps
    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # Relationships
    user = relationship("User", back_populates="notifications")

    # Indexes
    __table_args__ = (Index("idx_user_channel", "user_id", "channel"),)


class MailServerPreset(Base):
    """Predefined mail server configurations for common providers"""

    __tablename__ = "mail_server_presets"

    id = Column(Integer, primary_key=True, index=True)

    # Provider info
    provider_name = Column(String(100), unique=True, nullable=False, index=True)
    provider_domain = Column(String(255), nullable=False)  # e.g., "gmail.com"

    # Server configurations (can have multiple protocols)
    configs = Column(JSON, nullable=False)
    # Example:
    # {
    #   "pop3_ssl": {"host": "pop.gmail.com", "port": 995, "ssl": true},
    #   "imap_ssl": {"host": "imap.gmail.com", "port": 993, "ssl": true}
    # }

    # Metadata
    is_verified = Column(Boolean, default=False)
    popularity_score = Column(Integer, default=0)  # For sorting recommendations

    # Timestamps
    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )


class SubscriptionPlan(Base):
    """Available subscription plans and their features"""

    __tablename__ = "subscription_plans"

    id = Column(Integer, primary_key=True, index=True)

    # Plan details
    tier: Column[str] = Column(SQLEnum(SubscriptionTier), unique=True, nullable=False)
    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)

    # Pricing
    price_monthly = Column(Float, nullable=False)
    price_yearly = Column(Float, nullable=True)

    # Stripe integration
    stripe_price_id_monthly = Column(String(255), nullable=True)
    stripe_price_id_yearly = Column(String(255), nullable=True)

    # Features/Limits
    max_mail_accounts = Column(Integer, nullable=False)
    max_emails_per_day = Column(Integer, nullable=False)
    check_interval_minutes = Column(Integer, nullable=False)
    support_level = Column(
        String(50), default="community"
    )  # community, email, priority
    features = Column(JSON, nullable=True)  # Additional features as JSON

    # Status
    is_active = Column(Boolean, default=True)

    # Timestamps
    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )


class AuditLog(Base):
    """Audit trail for security and compliance"""

    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)

    # Who
    user_id = Column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    user_email = Column(String(255), nullable=True)  # Cached for deleted users
    ip_address = Column(String(45), nullable=True)  # IPv4 or IPv6

    # What
    action = Column(String(100), nullable=False, index=True)
    resource_type = Column(String(50), nullable=True)
    resource_id = Column(Integer, nullable=True)

    # Details
    details = Column(JSON, nullable=True)
    status = Column(String(20), default="success")  # success, failure

    # When
    timestamp = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
        index=True,
    )

    # Indexes
    __table_args__ = (
        Index("idx_user_action", "user_id", "action"),
        Index("idx_timestamp_action", "timestamp", "action"),
    )


class UserSmtpConfig(Base):
    """Per-user SMTP relay configuration for email forwarding fallback."""

    __tablename__ = "user_smtp_configs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True
    )

    host = Column(String(255), nullable=False, default="smtp.gmail.com")
    port = Column(Integer, nullable=False, default=587)
    username = Column(String(255), nullable=False, default="")
    encrypted_password = Column(Text, nullable=False, default="")
    use_tls = Column(Boolean, default=True)

    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # Relationships
    user = relationship("User", backref="smtp_config")


class DownloadedMessageId(Base):
    """
    Tracks unique message IDs that have already been downloaded and forwarded.

    - For POP3: stores the UIDL string returned by the server.
    - For IMAP: stores the IMAP UID (numeric string) of the message.

    This prevents re-processing the same message when delete_after_forward=False.
    """

    __tablename__ = "downloaded_message_ids"

    id = Column(Integer, primary_key=True, index=True)
    mail_account_id = Column(
        Integer, ForeignKey("mail_accounts.id", ondelete="CASCADE"), nullable=False
    )

    # Unique message identifier (UIDL for POP3, UID for IMAP)
    message_uid = Column(String(512), nullable=False)

    downloaded_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # Indexes — unique constraint prevents duplicates
    __table_args__ = (
        Index(
            "idx_account_message_uid",
            "mail_account_id",
            "message_uid",
            unique=True,
        ),
        Index("idx_downloaded_at", "downloaded_at"),
    )


class GmailCredential(Base):
    """Stores OAuth2 credentials for Gmail API access (per-user)"""

    __tablename__ = "gmail_credentials"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True
    )

    # Gmail account email
    gmail_email = Column(String(255), nullable=False)

    # OAuth2 tokens (encrypted)
    encrypted_access_token = Column(Text, nullable=False)
    encrypted_refresh_token = Column(Text, nullable=True)

    # Token metadata
    token_expiry = Column(DateTime(timezone=True), nullable=True)
    scopes = Column(JSON, nullable=True)

    # Status
    is_valid = Column(Boolean, default=True)
    last_verified_at = Column(DateTime(timezone=True), nullable=True)

    # Timestamps
    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # Relationships
    user = relationship("User", backref="gmail_credential")

    @property
    def granted_scopes(self) -> list[str]:
        return extract_granted_scopes(self.scopes)

    @property
    def import_label_templates(self) -> list[str]:
        return extract_import_label_templates(self.scopes)

    @property
    def default_import_label_templates(self) -> list[str]:
        return DEFAULT_IMPORT_LABEL_TEMPLATES.copy()


class AppSetting(Base):
    """
    Application settings stored in the database.

    Provides database-backed configuration that supplements or overrides
    environment variable settings. Bootstrap settings (DATABASE_URL,
    SECRET_KEY, ENCRYPTION_KEY) must still come from environment variables,
    but all other settings can be managed via the database.
    """

    __tablename__ = "app_settings"

    id = Column(Integer, primary_key=True, index=True)
    key = Column(String(255), unique=True, nullable=False, index=True)
    value = Column(Text, nullable=True)
    value_type = Column(String(50), default="string")  # string, int, float, bool, json
    description = Column(Text, nullable=True)
    is_secret = Column(Boolean, default=False)
    category = Column(String(100), nullable=True, index=True)

    # Timestamps
    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )


class AdminNotificationConfig(Base):
    """System-wide admin notification channels"""

    __tablename__ = "admin_notification_configs"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    apprise_url = Column(Text, nullable=False)
    is_enabled = Column(Boolean, default=True)
    notify_on_errors = Column(Boolean, default=True)
    notify_on_system_events = Column(Boolean, default=True)
    description = Column(Text, nullable=True)

    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
