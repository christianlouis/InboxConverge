"""
Pydantic schemas for API request/response validation.
"""
from datetime import datetime
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, EmailStr, Field, validator
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
    
    class Config:
        from_attributes = True


class UserDetailResponse(UserResponse):
    google_id: Optional[str] = None
    oauth_provider: Optional[str] = None
    stripe_customer_id: Optional[str] = None
    subscription_expires_at: Optional[datetime] = None
    last_login_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True


# Authentication Schemas
class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class TokenPayload(BaseModel):
    sub: Optional[int] = None
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
    is_enabled: bool = True
    check_interval_minutes: int = Field(default=5, gt=0, le=1440)
    max_emails_per_check: int = Field(default=50, gt=0, le=1000)
    delete_after_forward: bool = True


class MailAccountCreate(MailAccountBase):
    password: str  # Will be encrypted before storage


class MailAccountUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=255)
    password: Optional[str] = None
    forward_to: Optional[EmailStr] = None
    is_enabled: Optional[bool] = None
    check_interval_minutes: Optional[int] = Field(None, gt=0, le=1440)
    max_emails_per_check: Optional[int] = Field(None, gt=0, le=1000)
    delete_after_forward: Optional[bool] = None


class MailAccountResponse(MailAccountBase):
    id: int
    user_id: int
    status: AccountStatus
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
    
    # Don't expose password or username in responses
    password: str = Field(exclude=True, default="")
    username: str = Field(exclude=True, default="")
    
    class Config:
        from_attributes = True


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
    
    class Config:
        from_attributes = True


# Processing Log Schemas
class ProcessingLogResponse(BaseModel):
    id: int
    timestamp: datetime
    level: str
    message: str
    email_subject: Optional[str] = None
    email_from: Optional[str] = None
    success: bool
    
    class Config:
        from_attributes = True


# Notification Config Schemas
class NotificationConfigBase(BaseModel):
    channel: NotificationChannel
    is_enabled: bool = True
    config: Dict[str, Any]
    notify_on_errors: bool = True
    notify_on_success: bool = False
    notify_threshold: int = Field(default=3, gt=0, le=100)


class NotificationConfigCreate(NotificationConfigBase):
    pass


class NotificationConfigUpdate(BaseModel):
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
    
    class Config:
        from_attributes = True


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
    
    class Config:
        from_attributes = True


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
    
    class Config:
        from_attributes = True
