"""
Unit tests for Pydantic schema validation.
"""

import pytest
from pydantic import ValidationError
from app.models.schemas import (
    UserCreate,
    UserUpdate,
    MailAccountCreate,
    MailAccountUpdate,
    MailAccountTestRequest,
    MailAccountAutoDetectRequest,
    MailProtocol,
    DeliveryMethod,
    SubscriptionTier,
    AccountStatus,
    NotificationChannel,
    Token,
    TokenPayload,
    GoogleAuthRequest,
    NotificationConfigCreate,
    SubscriptionCheckoutRequest,
    ProviderPreset,
)


class TestEnums:
    """Test enum values"""

    def test_subscription_tiers(self):
        """Test all subscription tier values"""
        assert SubscriptionTier.FREE == "free"
        assert SubscriptionTier.BASIC == "basic"
        assert SubscriptionTier.PRO == "pro"
        assert SubscriptionTier.ENTERPRISE == "enterprise"

    def test_mail_protocols(self):
        """Test all mail protocol values"""
        assert MailProtocol.POP3 == "pop3"
        assert MailProtocol.POP3_SSL == "pop3_ssl"
        assert MailProtocol.IMAP == "imap"
        assert MailProtocol.IMAP_SSL == "imap_ssl"

    def test_account_status(self):
        """Test all account status values"""
        assert AccountStatus.ACTIVE == "active"
        assert AccountStatus.INACTIVE == "inactive"
        assert AccountStatus.ERROR == "error"
        assert AccountStatus.TESTING == "testing"

    def test_delivery_method(self):
        """Test all delivery method values"""
        assert DeliveryMethod.SMTP == "smtp"
        assert DeliveryMethod.GMAIL_API == "gmail_api"

    def test_notification_channels(self):
        """Test all notification channel values"""
        assert NotificationChannel.EMAIL == "email"
        assert NotificationChannel.TELEGRAM == "telegram"
        assert NotificationChannel.WEBHOOK == "webhook"
        assert NotificationChannel.SLACK == "slack"
        assert NotificationChannel.DISCORD == "discord"


class TestUserSchemas:
    """Test user-related schemas"""

    def test_user_create_with_email(self):
        """Test UserCreate with valid email"""
        user = UserCreate(email="test@example.com", password="password123")
        assert user.email == "test@example.com"
        assert user.password == "password123"

    def test_user_create_without_password(self):
        """Test UserCreate without password (OAuth users)"""
        user = UserCreate(email="test@example.com")
        assert user.password is None

    def test_user_create_with_full_name(self):
        """Test UserCreate with full name"""
        user = UserCreate(
            email="test@example.com", full_name="Test User", password="pass"
        )
        assert user.full_name == "Test User"

    def test_user_create_invalid_email(self):
        """Test UserCreate rejects invalid email"""
        with pytest.raises(ValidationError):
            UserCreate(email="not-an-email", password="pass")

    def test_user_update_partial(self):
        """Test UserUpdate with partial data"""
        update = UserUpdate(full_name="New Name")
        assert update.full_name == "New Name"
        assert update.email is None


class TestTokenSchemas:
    """Test token schemas"""

    def test_token_schema(self):
        """Test Token schema"""
        token = Token(
            access_token="abc123", refresh_token="def456", token_type="bearer"
        )
        assert token.access_token == "abc123"
        assert token.token_type == "bearer"

    def test_token_payload_schema(self):
        """Test TokenPayload schema"""
        payload = TokenPayload(sub=42, type="access")
        assert payload.sub == 42
        assert payload.type == "access"

    def test_google_auth_request(self):
        """Test GoogleAuthRequest schema"""
        req = GoogleAuthRequest(
            code="auth-code-123", redirect_uri="http://localhost:3000/callback"
        )
        assert req.code == "auth-code-123"


class TestMailAccountSchemas:
    """Test mail account schemas"""

    def test_mail_account_create_valid(self):
        """Test creating a valid mail account"""
        account = MailAccountCreate(
            name="Test Account",
            email_address="user@example.com",
            host="imap.example.com",
            port=993,
            username="user@example.com",
            password="secret",
            forward_to="me@gmail.com",
        )
        assert account.name == "Test Account"
        assert account.protocol == MailProtocol.POP3_SSL  # default
        assert account.use_ssl is True

    def test_mail_account_create_invalid_port(self):
        """Test that invalid port is rejected"""
        with pytest.raises(ValidationError):
            MailAccountCreate(
                name="Test",
                email_address="user@example.com",
                host="imap.example.com",
                port=0,  # invalid
                username="user@example.com",
                password="secret",
                forward_to="me@gmail.com",
            )

    def test_mail_account_create_port_too_high(self):
        """Test that port above 65535 is rejected"""
        with pytest.raises(ValidationError):
            MailAccountCreate(
                name="Test",
                email_address="user@example.com",
                host="imap.example.com",
                port=70000,  # invalid
                username="user@example.com",
                password="secret",
                forward_to="me@gmail.com",
            )

    def test_mail_account_update_partial(self):
        """Test partial mail account update"""
        update = MailAccountUpdate(is_enabled=False)
        assert update.is_enabled is False
        assert update.name is None
        assert update.password is None

    def test_mail_account_test_request(self):
        """Test mail account test connection schema"""
        req = MailAccountTestRequest(
            host="imap.gmail.com",
            port=993,
            protocol=MailProtocol.IMAP_SSL,
            username="user@gmail.com",
            password="app-password",
        )
        assert req.host == "imap.gmail.com"

    def test_auto_detect_request(self):
        """Test auto-detect request schema"""
        req = MailAccountAutoDetectRequest(email_address="user@gmail.com")
        assert req.email_address == "user@gmail.com"

    def test_auto_detect_invalid_email(self):
        """Test auto-detect rejects invalid email"""
        with pytest.raises(ValidationError):
            MailAccountAutoDetectRequest(email_address="not-email")


class TestNotificationSchemas:
    """Test notification schemas"""

    def test_notification_config_create(self):
        """Test creating notification config"""
        config = NotificationConfigCreate(
            channel=NotificationChannel.TELEGRAM,
            config={"bot_token": "123:abc", "chat_id": "456"},
        )
        assert config.channel == NotificationChannel.TELEGRAM
        assert config.notify_on_errors is True  # default
        assert config.notify_on_success is False  # default

    def test_notification_config_threshold_validation(self):
        """Test notification threshold validation"""
        with pytest.raises(ValidationError):
            NotificationConfigCreate(
                channel=NotificationChannel.EMAIL,
                config={},
                notify_threshold=0,  # must be > 0
            )


class TestSubscriptionSchemas:
    """Test subscription schemas"""

    def test_subscription_checkout_request_monthly(self):
        """Test subscription checkout with monthly billing"""
        req = SubscriptionCheckoutRequest(
            tier=SubscriptionTier.PRO,
            billing_period="monthly",
            success_url="https://example.com/success",
            cancel_url="https://example.com/cancel",
        )
        assert req.tier == SubscriptionTier.PRO
        assert req.billing_period == "monthly"

    def test_subscription_checkout_request_yearly(self):
        """Test subscription checkout with yearly billing"""
        req = SubscriptionCheckoutRequest(
            tier=SubscriptionTier.BASIC,
            billing_period="yearly",
            success_url="https://example.com/success",
            cancel_url="https://example.com/cancel",
        )
        assert req.billing_period == "yearly"

    def test_subscription_checkout_invalid_period(self):
        """Test that invalid billing period is rejected"""
        with pytest.raises(ValidationError):
            SubscriptionCheckoutRequest(
                tier=SubscriptionTier.BASIC,
                billing_period="quarterly",  # invalid
                success_url="https://example.com/success",
                cancel_url="https://example.com/cancel",
            )


class TestProviderPresetSchema:
    """Test provider preset schema"""

    def test_provider_preset_with_imap(self):
        """Test provider preset with IMAP config"""
        preset = ProviderPreset(
            id="gmail",
            name="Gmail",
            domains=["gmail.com", "googlemail.com"],
            imap_ssl={"host": "imap.gmail.com", "port": 993},
        )
        assert preset.id == "gmail"
        assert "gmail.com" in preset.domains

    def test_provider_preset_without_pop3(self):
        """Test provider preset without POP3 (IMAP only)"""
        preset = ProviderPreset(
            id="posteo",
            name="Posteo",
            domains=["posteo.de"],
            imap_ssl={"host": "posteo.de", "port": 993},
        )
        assert preset.pop3_ssl is None
