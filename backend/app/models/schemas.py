"""
Pydantic schemas for API request/response validation.
"""

from datetime import datetime
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, ConfigDict, EmailStr, Field
from enum import Enum


# Enums matching database models
class SubscriptionTier(str, Enum):
    FREE = "free"
    BASIC = "basic"
    PRO = "pro"
    ENTERPRISE = "enterprise"


class MailProtocol(str, Enum):
    POP3 = "pop3"
    POP3_SSL = "pop3_ssl"
    IMAP = "imap"
    IMAP_SSL = "imap_ssl"


class AccountStatus(str, Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    ERROR = "error"
    TESTING = "testing"


class DeliveryMethod(str, Enum):
    SMTP = "smtp"
    GMAIL_API = "gmail_api"


class NotificationChannel(str, Enum):
    EMAIL = "email"
    TELEGRAM = "telegram"
    WEBHOOK = "webhook"
    SLACK = "slack"
    DISCORD = "discord"


# User Schemas
class UserBase(BaseModel):
    email: EmailStr
    full_name: Optional[str] = None


class UserCreate(UserBase):
    password: Optional[str] = None


class UserUpdate(BaseModel):
    full_name: Optional[str] = None
    email: Optional[EmailStr] = None


class UserResponse(UserBase):
    id: int
    is_active: bool
    subscription_tier: SubscriptionTier
    subscription_status: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class UserDetailResponse(UserResponse):
    google_id: Optional[str] = None
    oauth_provider: Optional[str] = None
    stripe_customer_id: Optional[str] = None
    subscription_expires_at: Optional[datetime] = None
    last_login_at: Optional[datetime] = None
    is_superuser: bool = False

    model_config = ConfigDict(from_attributes=True)


# Authentication Schemas
class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class TokenPayload(BaseModel):
    sub: Optional[str] = None
    exp: Optional[int] = None
    type: Optional[str] = None


class GoogleAuthRequest(BaseModel):
    code: str
    redirect_uri: str


# Mail Account Schemas
class MailAccountBase(BaseModel):
    name: str = Field(..., max_length=255)
    email_address: EmailStr
    protocol: MailProtocol = MailProtocol.POP3_SSL
    host: str = Field(..., max_length=255)
    port: int = Field(..., gt=0, lt=65536)
    use_ssl: bool = True
    use_tls: bool = False
    username: str = Field(..., max_length=255)
    forward_to: EmailStr
    delivery_method: DeliveryMethod = DeliveryMethod.GMAIL_API
    is_enabled: bool = True
    check_interval_minutes: int = Field(default=5, gt=0, le=1440)
    max_emails_per_check: int = Field(default=50, gt=0, le=1000)
    delete_after_forward: bool = True
    provider_name: Optional[str] = Field(None, max_length=100)
    debug_logging: bool = False


class MailAccountCreate(MailAccountBase):
    password: str  # Will be encrypted before storage


class MailAccountUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=255)
    email_address: Optional[EmailStr] = None
    protocol: Optional[MailProtocol] = None
    host: Optional[str] = Field(None, max_length=255)
    port: Optional[int] = Field(None, gt=0, lt=65536)
    use_ssl: Optional[bool] = None
    use_tls: Optional[bool] = None
    username: Optional[str] = Field(None, max_length=255)
    password: Optional[str] = None
    forward_to: Optional[EmailStr] = None
    delivery_method: Optional[DeliveryMethod] = None
    is_enabled: Optional[bool] = None
    check_interval_minutes: Optional[int] = Field(None, gt=0, le=1440)
    max_emails_per_check: Optional[int] = Field(None, gt=0, le=1000)
    delete_after_forward: Optional[bool] = None
    provider_name: Optional[str] = Field(None, max_length=100)
    debug_logging: Optional[bool] = None


class MailAccountResponse(MailAccountBase):
    id: int
    user_id: int
    status: AccountStatus
    delivery_method: DeliveryMethod
    provider_name: Optional[str] = None
    auto_detected: bool
    total_emails_processed: int
    total_emails_failed: int
    last_check_at: Optional[datetime] = None
    last_successful_check_at: Optional[datetime] = None
    last_error_at: Optional[datetime] = None
    last_error_message: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    # Don't expose password in responses; username is safe to return
    password: str = Field(exclude=True, default="")

    model_config = ConfigDict(from_attributes=True)


class MailAccountTestRequest(BaseModel):
    """Test connection to mail server"""

    host: str
    port: int
    protocol: MailProtocol
    username: str
    password: str
    use_ssl: bool = True
    use_tls: bool = False


class MailAccountTestResponse(BaseModel):
    success: bool
    message: str
    details: Optional[Dict[str, Any]] = None


class MailAccountAutoDetectRequest(BaseModel):
    """Auto-detect mail server settings"""

    email_address: EmailStr


class MailAccountAutoDetectResponse(BaseModel):
    success: bool
    suggestions: List[Dict[str, Any]]


# Processing Run Schemas
class ProcessingRunResponse(BaseModel):
    id: int
    mail_account_id: int
    started_at: datetime
    completed_at: Optional[datetime] = None
    duration_seconds: Optional[float] = None
    emails_fetched: int
    emails_forwarded: int
    emails_failed: int
    status: str
    error_message: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class ProcessingRunDetailResponse(ProcessingRunResponse):
    """ProcessingRunResponse with optional account metadata."""

    account_name: Optional[str] = None
    account_email: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


# Processing Log Schemas
class ProcessingLogResponse(BaseModel):
    id: int
    timestamp: datetime
    level: str
    message: str
    email_subject: Optional[str] = None
    email_from: Optional[str] = None
    success: bool

    model_config = ConfigDict(from_attributes=True)


class ProcessingLogDetailResponse(ProcessingLogResponse):
    """ProcessingLogResponse with additional fields."""

    mail_account_id: int
    processing_run_id: Optional[int] = None
    email_size_bytes: Optional[int] = None
    error_details: Optional[Dict[str, Any]] = None

    model_config = ConfigDict(from_attributes=True)


class PaginatedProcessingRunsResponse(BaseModel):
    items: List[ProcessingRunDetailResponse]
    total: int
    page: int
    page_size: int
    pages: int


class PaginatedProcessingLogsResponse(BaseModel):
    items: List[ProcessingLogDetailResponse]
    total: int
    page: int
    page_size: int
    pages: int


class AdminProcessingRunResponse(ProcessingRunDetailResponse):
    """ProcessingRunDetailResponse with user info for admin views."""

    user_id: Optional[int] = None
    user_email: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class PaginatedAdminRunsResponse(BaseModel):
    items: List[AdminProcessingRunResponse]
    total: int
    page: int
    page_size: int
    pages: int


class AdminProcessingLogResponse(ProcessingLogDetailResponse):
    """ProcessingLogDetailResponse with user info for admin views."""

    user_id: int
    user_email: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class PaginatedAdminLogsResponse(BaseModel):
    items: List[AdminProcessingLogResponse]
    total: int
    page: int
    page_size: int
    pages: int


# Notification Config Schemas
class NotificationConfigBase(BaseModel):
    name: str = Field(
        default="My Notification",
        max_length=255,
        description="Friendly name for this notification channel",
    )
    channel: NotificationChannel
    apprise_url: Optional[str] = Field(None, description="Apprise notification URL")
    is_enabled: bool = True
    config: Dict[str, Any] = Field(
        default_factory=dict,
        description="Legacy channel-specific configuration (deprecated in favour of apprise_url)",
    )
    notify_on_errors: bool = True
    notify_on_success: bool = False
    notify_threshold: int = Field(default=3, gt=0, le=100)


class NotificationConfigCreate(NotificationConfigBase):
    pass


class NotificationConfigUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=255)
    channel: Optional[NotificationChannel] = None
    apprise_url: Optional[str] = None
    is_enabled: Optional[bool] = None
    config: Optional[Dict[str, Any]] = None
    notify_on_errors: Optional[bool] = None
    notify_on_success: Optional[bool] = None
    notify_threshold: Optional[int] = Field(None, gt=0, le=100)


class NotificationConfigResponse(NotificationConfigBase):
    id: int
    user_id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class NotificationTestRequest(BaseModel):
    apprise_url: str = Field(..., description="Apprise URL to test")


class NotificationTestResponse(BaseModel):
    success: bool
    message: str


# Admin Notification Config Schemas
class AdminNotificationConfigBase(BaseModel):
    name: str = Field(..., max_length=255)
    apprise_url: str = Field(..., description="Apprise notification URL")
    is_enabled: bool = True
    notify_on_errors: bool = True
    notify_on_system_events: bool = True
    description: Optional[str] = None


class AdminNotificationConfigCreate(AdminNotificationConfigBase):
    pass


class AdminNotificationConfigUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=255)
    apprise_url: Optional[str] = None
    is_enabled: Optional[bool] = None
    notify_on_errors: Optional[bool] = None
    notify_on_system_events: Optional[bool] = None
    description: Optional[str] = None


class AdminNotificationConfigResponse(AdminNotificationConfigBase):
    id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# Subscription Schemas
class SubscriptionPlanResponse(BaseModel):
    id: int
    tier: SubscriptionTier
    name: str
    description: Optional[str] = None
    price_monthly: float
    price_yearly: Optional[float] = None
    max_mail_accounts: int
    max_emails_per_day: int
    check_interval_minutes: int
    support_level: str
    features: Optional[Dict[str, Any]] = None
    is_active: bool

    model_config = ConfigDict(from_attributes=True)


class SubscriptionCheckoutRequest(BaseModel):
    tier: SubscriptionTier
    billing_period: str = Field(..., pattern="^(monthly|yearly)$")
    success_url: str
    cancel_url: str


class SubscriptionCheckoutResponse(BaseModel):
    checkout_url: str
    session_id: str


# Statistics Schemas
class AccountStatistics(BaseModel):
    total_accounts: int
    active_accounts: int
    inactive_accounts: int
    error_accounts: int
    total_emails_processed: int
    total_emails_failed: int


class ProcessingStatistics(BaseModel):
    last_24h_processed: int
    last_24h_failed: int
    last_7d_processed: int
    last_7d_failed: int
    success_rate: float


class DashboardStatistics(BaseModel):
    account_stats: AccountStatistics
    processing_stats: ProcessingStatistics
    recent_runs: List[ProcessingRunResponse]
    recent_errors: List[ProcessingLogResponse]


# Mail Server Preset Schemas
class MailServerPresetResponse(BaseModel):
    id: int
    provider_name: str
    provider_domain: str
    configs: Dict[str, Any]
    is_verified: bool

    model_config = ConfigDict(from_attributes=True)


# Gmail Credential Schemas
class GmailCredentialCreate(BaseModel):
    access_token: str
    refresh_token: Optional[str] = None
    gmail_email: EmailStr


class GmailCredentialResponse(BaseModel):
    id: int
    user_id: int
    gmail_email: str
    is_valid: bool
    import_label_templates: List[str] = Field(default_factory=list)
    default_import_label_templates: List[str] = Field(default_factory=list)
    last_verified_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# Provider Wizard Schemas
class ProviderPreset(BaseModel):
    id: str
    name: str
    icon: Optional[str] = None
    domains: List[str]
    imap_ssl: Optional[Dict[str, Any]] = None
    pop3_ssl: Optional[Dict[str, Any]] = None
    notes: Optional[str] = None


class ProviderListResponse(BaseModel):
    providers: List[ProviderPreset]


# User SMTP Config Schemas
class UserSmtpConfigBase(BaseModel):
    host: str = "smtp.gmail.com"
    port: int = Field(587, gt=0, lt=65536)
    username: str = ""
    use_tls: bool = True


class UserSmtpConfigUpdate(UserSmtpConfigBase):
    password: Optional[str] = None  # Only provided when changing the password


class UserSmtpConfigResponse(UserSmtpConfigBase):
    id: int
    user_id: int
    has_password: bool  # True if a password is stored (value is never returned)
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# Gmail OAuth Schemas
class GmailAuthorizeResponse(BaseModel):
    authorization_url: str


class GmailCallbackRequest(BaseModel):
    code: str
    redirect_uri: str


class GmailImportLabelsUpdate(BaseModel):
    import_label_templates: List[str] = Field(default_factory=list)


# Admin Schemas


class AdminUserListResponse(BaseModel):
    id: int
    email: str
    full_name: Optional[str] = None
    is_active: bool
    is_superuser: bool
    subscription_tier: SubscriptionTier
    subscription_status: str
    google_id: Optional[str] = None
    oauth_provider: Optional[str] = None
    last_login_at: Optional[datetime] = None
    created_at: datetime
    mail_account_count: int = 0

    model_config = ConfigDict(from_attributes=True)


class AdminUserUpdate(BaseModel):
    full_name: Optional[str] = None
    email: Optional[EmailStr] = None
    is_active: Optional[bool] = None
    is_superuser: Optional[bool] = None
    subscription_tier: Optional[SubscriptionTier] = None
    subscription_status: Optional[str] = None


class SubscriptionPlanCreate(BaseModel):
    tier: SubscriptionTier
    name: str
    description: Optional[str] = None
    price_monthly: float = 0.0
    price_yearly: Optional[float] = None
    max_mail_accounts: int = 1
    max_emails_per_day: int = 1000
    check_interval_minutes: int = 5
    support_level: str = "community"
    features: Optional[Dict[str, Any]] = None
    is_active: bool = True


class SubscriptionPlanUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    price_monthly: Optional[float] = None
    price_yearly: Optional[float] = None
    max_mail_accounts: Optional[int] = None
    max_emails_per_day: Optional[int] = None
    check_interval_minutes: Optional[int] = None
    support_level: Optional[str] = None
    features: Optional[Dict[str, Any]] = None
    is_active: Optional[bool] = None
