"""
Unit tests for mail account endpoints (backend/app/api/v1/endpoints/mail_accounts.py).

All tests mock the database session and auth dependencies so no real
PostgreSQL instance is required.
"""

import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

from httpx import AsyncClient, ASGITransport

from app.main import create_application
from app.core.database import get_db
from app.core.deps import get_current_active_user
from app.models.database_models import (
    User,
    MailAccount,
    ProcessingRun,
    ProcessingLog,
    SubscriptionPlan,
    SubscriptionTier,
    AccountStatus,
)

BASE = "/api/v1/mail-accounts"

# ── helpers ──────────────────────────────────────────────────────────────


def _make_user(**overrides) -> MagicMock:
    """Return a MagicMock that behaves like a User ORM instance."""
    defaults = dict(
        id=1,
        email="user@example.com",
        hashed_password="hashed",
        full_name="Test User",
        is_active=True,
        is_superuser=False,
        subscription_tier=SubscriptionTier.FREE,
        subscription_status="active",
        google_id=None,
        oauth_provider=None,
        last_login_at=None,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
        stripe_customer_id=None,
        stripe_subscription_id=None,
        subscription_expires_at=None,
    )
    defaults.update(overrides)
    user = MagicMock(spec=User)
    for k, v in defaults.items():
        setattr(user, k, v)
    return user


def _make_superuser(**overrides) -> MagicMock:
    return _make_user(is_superuser=True, **overrides)


def _make_account(**overrides) -> MagicMock:
    """Return a MagicMock that behaves like a MailAccount ORM instance."""
    defaults = dict(
        id=10,
        user_id=1,
        name="Test Account",
        email_address="test@example.com",
        protocol="pop3_ssl",
        host="pop.example.com",
        port=995,
        use_ssl=True,
        use_tls=False,
        username="test@example.com",
        encrypted_password="encrypted_pass",
        forward_to="me@gmail.com",
        delivery_method="gmail_api",
        status="active",
        is_enabled=True,
        check_interval_minutes=5,
        max_emails_per_check=50,
        delete_after_forward=True,
        debug_logging=False,
        provider_name="Gmail",
        auto_detected=False,
        total_emails_processed=100,
        total_emails_failed=2,
        last_check_at=datetime.now(timezone.utc),
        last_successful_check_at=datetime.now(timezone.utc),
        last_error_at=None,
        last_error_message=None,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    defaults.update(overrides)
    account = MagicMock(spec=MailAccount)
    for k, v in defaults.items():
        setattr(account, k, v)
    return account


def _make_run(**overrides) -> MagicMock:
    """Return a MagicMock that behaves like a ProcessingRun ORM instance."""
    defaults = dict(
        id=100,
        mail_account_id=10,
        started_at=datetime.now(timezone.utc),
        completed_at=datetime.now(timezone.utc),
        duration_seconds=1.5,
        emails_fetched=5,
        emails_forwarded=4,
        emails_failed=1,
        status="completed",
        error_message=None,
    )
    defaults.update(overrides)
    run = MagicMock(spec=ProcessingRun)
    for k, v in defaults.items():
        setattr(run, k, v)
    return run


def _make_log(**overrides) -> MagicMock:
    """Return a MagicMock that behaves like a ProcessingLog ORM instance."""
    defaults = dict(
        id=200,
        user_id=1,
        mail_account_id=10,
        processing_run_id=100,
        timestamp=datetime.now(timezone.utc),
        level="INFO",
        message="Processed email",
        email_subject="Hello",
        email_from="sender@example.com",
        email_size_bytes=1024,
        success=True,
        error_details=None,
    )
    defaults.update(overrides)
    log = MagicMock(spec=ProcessingLog)
    for k, v in defaults.items():
        setattr(log, k, v)
    return log


def _scalar_one_or_none(value):
    """Create a mock result whose .scalar_one_or_none() returns *value*."""
    result = MagicMock()
    result.scalar_one_or_none.return_value = value
    return result


def _scalar_one(value):
    result = MagicMock()
    result.scalar_one.return_value = value
    return result


def _scalars_all(values):
    result = MagicMock()
    scalars = MagicMock()
    scalars.all.return_value = values
    result.scalars.return_value = scalars
    return result


# ── fixtures ─────────────────────────────────────────────────────────────


@pytest.fixture
def app():
    return create_application()


@pytest.fixture
def regular_user():
    return _make_user()


@pytest.fixture
def superuser():
    return _make_superuser()


@pytest.fixture
def mock_db():
    db = AsyncMock()
    db.commit = AsyncMock()
    db.refresh = AsyncMock()
    db.delete = AsyncMock()
    db.add = MagicMock()
    return db


@pytest.fixture
async def client(app, regular_user, mock_db):
    """AsyncClient where the caller is a regular user and db is mocked."""

    async def _override_user():
        return regular_user

    async def _override_db():
        yield mock_db

    app.dependency_overrides[get_current_active_user] = _override_user
    app.dependency_overrides[get_db] = _override_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c

    app.dependency_overrides.clear()


@pytest.fixture
async def superuser_client(app, superuser, mock_db):
    """AsyncClient where the caller is a superuser and db is mocked."""

    async def _override_user():
        return superuser

    async def _override_db():
        yield mock_db

    app.dependency_overrides[get_current_active_user] = _override_user
    app.dependency_overrides[get_db] = _override_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c

    app.dependency_overrides.clear()


# ── account payload helper ───────────────────────────────────────────────

VALID_ACCOUNT_PAYLOAD = dict(
    name="My Account",
    email_address="inbox@example.com",
    protocol="pop3_ssl",
    host="pop.example.com",
    port=995,
    use_ssl=True,
    use_tls=False,
    username="inbox@example.com",
    password="secret",
    forward_to="me@gmail.com",
    delivery_method="gmail_api",
    is_enabled=True,
    check_interval_minutes=5,
    max_emails_per_check=50,
    delete_after_forward=True,
    provider_name="Gmail",
)


# ── tests: create mail account ──────────────────────────────────────────


class TestCreateMailAccount:
    """POST /api/v1/mail-accounts"""

    @patch("app.api.v1.endpoints.mail_accounts.encrypt_credential", return_value="enc")
    async def test_create_superuser_bypasses_limit(
        self, mock_encrypt, superuser_client, mock_db
    ):
        """Superusers skip the subscription-limit check entirely."""
        mock_db.refresh = AsyncMock(side_effect=lambda obj: None)
        created = {}

        def capture_add(obj):
            created["obj"] = obj
            # Give the added object all the response fields
            for k, v in {
                "id": 10,
                "user_id": 1,
                "status": "active",
                "auto_detected": False,
                "total_emails_processed": 0,
                "total_emails_failed": 0,
                "last_check_at": None,
                "last_successful_check_at": None,
                "last_error_at": None,
                "last_error_message": None,
                "created_at": datetime.now(timezone.utc),
                "updated_at": datetime.now(timezone.utc),
            }.items():
                setattr(obj, k, v)

        mock_db.add = MagicMock(side_effect=capture_add)

        resp = await superuser_client.post(BASE, json=VALID_ACCOUNT_PAYLOAD)
        assert resp.status_code == 201
        data = resp.json()
        assert data["name"] == "My Account"
        assert data["email_address"] == "inbox@example.com"
        mock_encrypt.assert_called_once_with("secret")
        mock_db.commit.assert_called_once()

    @patch("app.api.v1.endpoints.mail_accounts.encrypt_credential", return_value="enc")
    async def test_create_regular_user_within_limit(
        self, mock_encrypt, client, mock_db
    ):
        """Regular user under their plan limit can create an account."""
        # 1st execute: count existing accounts (returns 0 accounts)
        # 2nd execute: fetch subscription plan
        plan = MagicMock(spec=SubscriptionPlan)
        plan.max_mail_accounts = 5

        mock_db.execute = AsyncMock(
            side_effect=[
                _scalars_all([]),  # existing accounts
                _scalar_one_or_none(plan),  # subscription plan
            ]
        )

        def capture_add(obj):
            for k, v in {
                "id": 10,
                "user_id": 1,
                "status": "active",
                "auto_detected": False,
                "total_emails_processed": 0,
                "total_emails_failed": 0,
                "last_check_at": None,
                "last_successful_check_at": None,
                "last_error_at": None,
                "last_error_message": None,
                "created_at": datetime.now(timezone.utc),
                "updated_at": datetime.now(timezone.utc),
            }.items():
                setattr(obj, k, v)

        mock_db.add = MagicMock(side_effect=capture_add)

        resp = await client.post(BASE, json=VALID_ACCOUNT_PAYLOAD)
        assert resp.status_code == 201
        mock_encrypt.assert_called_once_with("secret")

    @patch("app.api.v1.endpoints.mail_accounts.encrypt_credential", return_value="enc")
    async def test_create_subscription_limit_reached(
        self, mock_encrypt, client, mock_db
    ):
        """402 when account limit is reached."""
        existing = [_make_account(id=i) for i in range(1)]
        plan = MagicMock(spec=SubscriptionPlan)
        plan.max_mail_accounts = 1

        mock_db.execute = AsyncMock(
            side_effect=[
                _scalars_all(existing),  # existing accounts (1 already)
                _scalar_one_or_none(plan),  # plan says max=1
            ]
        )

        resp = await client.post(BASE, json=VALID_ACCOUNT_PAYLOAD)
        assert resp.status_code == 402
        assert "limit" in resp.json()["detail"].lower()

    @patch("app.api.v1.endpoints.mail_accounts.encrypt_credential", return_value="enc")
    async def test_create_uses_db_plan_limit(self, mock_encrypt, client, mock_db):
        """When a SubscriptionPlan exists in the DB, use its max_mail_accounts."""
        plan = MagicMock(spec=SubscriptionPlan)
        plan.max_mail_accounts = 3

        existing = [_make_account(id=i) for i in range(3)]
        mock_db.execute = AsyncMock(
            side_effect=[
                _scalars_all(existing),  # 3 existing
                _scalar_one_or_none(plan),  # plan limit = 3
            ]
        )

        resp = await client.post(BASE, json=VALID_ACCOUNT_PAYLOAD)
        assert resp.status_code == 402

    @patch("app.api.v1.endpoints.mail_accounts.encrypt_credential", return_value="enc")
    async def test_create_fallback_tier_limit_when_no_plan(
        self, mock_encrypt, client, mock_db
    ):
        """When no SubscriptionPlan row exists, falls back to settings tier limits."""
        mock_db.execute = AsyncMock(
            side_effect=[
                _scalars_all([]),  # 0 existing accounts
                _scalar_one_or_none(None),  # no plan in DB → fallback
            ]
        )

        def capture_add(obj):
            for k, v in {
                "id": 10,
                "user_id": 1,
                "status": "active",
                "auto_detected": False,
                "total_emails_processed": 0,
                "total_emails_failed": 0,
                "last_check_at": None,
                "last_successful_check_at": None,
                "last_error_at": None,
                "last_error_message": None,
                "created_at": datetime.now(timezone.utc),
                "updated_at": datetime.now(timezone.utc),
            }.items():
                setattr(obj, k, v)

        mock_db.add = MagicMock(side_effect=capture_add)

        resp = await client.post(BASE, json=VALID_ACCOUNT_PAYLOAD)
        # free tier default is 1, and 0 existing → should succeed
        assert resp.status_code == 201


# ── tests: list mail accounts ───────────────────────────────────────────


class TestListMailAccounts:
    """GET /api/v1/mail-accounts"""

    async def test_list_accounts(self, client, mock_db):
        accounts = [_make_account(id=1), _make_account(id=2)]
        mock_db.execute = AsyncMock(return_value=_scalars_all(accounts))

        resp = await client.get(BASE)
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 2


# ── tests: get mail account ─────────────────────────────────────────────


class TestGetMailAccount:
    """GET /api/v1/mail-accounts/{account_id}"""

    async def test_get_account_success(self, client, mock_db):
        account = _make_account()
        mock_db.execute = AsyncMock(return_value=_scalar_one_or_none(account))

        resp = await client.get(f"{BASE}/10")
        assert resp.status_code == 200
        assert resp.json()["id"] == 10

    async def test_get_account_not_found(self, client, mock_db):
        mock_db.execute = AsyncMock(return_value=_scalar_one_or_none(None))

        resp = await client.get(f"{BASE}/999")
        assert resp.status_code == 404


# ── tests: update mail account ──────────────────────────────────────────


class TestUpdateMailAccount:
    """PUT /api/v1/mail-accounts/{account_id}"""

    async def test_update_account_success(self, client, mock_db):
        account = _make_account()
        mock_db.execute = AsyncMock(return_value=_scalar_one_or_none(account))

        resp = await client.put(f"{BASE}/10", json={"name": "Updated Name"})
        assert resp.status_code == 200
        mock_db.commit.assert_called()

    @patch(
        "app.api.v1.endpoints.mail_accounts.encrypt_credential", return_value="new_enc"
    )
    async def test_update_account_with_password(self, mock_encrypt, client, mock_db):
        account = _make_account()
        mock_db.execute = AsyncMock(return_value=_scalar_one_or_none(account))

        resp = await client.put(f"{BASE}/10", json={"password": "newpass"})
        assert resp.status_code == 200
        mock_encrypt.assert_called_once_with("newpass")
        # Verify encrypted_password was set on the account
        assert account.encrypted_password == "new_enc"

    async def test_update_account_not_found(self, client, mock_db):
        mock_db.execute = AsyncMock(return_value=_scalar_one_or_none(None))

        resp = await client.put(f"{BASE}/999", json={"name": "X"})
        assert resp.status_code == 404


# ── tests: delete mail account ──────────────────────────────────────────


class TestDeleteMailAccount:
    """DELETE /api/v1/mail-accounts/{account_id}"""

    async def test_delete_account_success(self, client, mock_db):
        account = _make_account()
        mock_db.execute = AsyncMock(return_value=_scalar_one_or_none(account))

        resp = await client.delete(f"{BASE}/10")
        assert resp.status_code == 204
        mock_db.delete.assert_called_once_with(account)
        mock_db.commit.assert_called()

    async def test_delete_account_not_found(self, client, mock_db):
        mock_db.execute = AsyncMock(return_value=_scalar_one_or_none(None))

        resp = await client.delete(f"{BASE}/999")
        assert resp.status_code == 404


# ── tests: toggle mail account ──────────────────────────────────────────


class TestToggleMailAccount:
    """PATCH /api/v1/mail-accounts/{account_id}/toggle"""

    async def test_toggle_enable_resets_error(self, client, mock_db):
        """Toggling an ERROR account to enabled resets status to ACTIVE."""
        account = _make_account(is_enabled=False, status=AccountStatus.ERROR)
        mock_db.execute = AsyncMock(return_value=_scalar_one_or_none(account))

        resp = await client.patch(f"{BASE}/10/toggle")
        assert resp.status_code == 200
        # After toggle: is_enabled=True and status reset from ERROR → ACTIVE
        assert account.is_enabled is True
        assert account.status == AccountStatus.ACTIVE
        mock_db.commit.assert_called()

    async def test_toggle_disable(self, client, mock_db):
        """Toggling an enabled account disables it."""
        account = _make_account(is_enabled=True, status=AccountStatus.ACTIVE)
        mock_db.execute = AsyncMock(return_value=_scalar_one_or_none(account))

        resp = await client.patch(f"{BASE}/10/toggle")
        assert resp.status_code == 200
        assert account.is_enabled is False

    async def test_toggle_not_found(self, client, mock_db):
        mock_db.execute = AsyncMock(return_value=_scalar_one_or_none(None))

        resp = await client.patch(f"{BASE}/999/toggle")
        assert resp.status_code == 404


# ── tests: pull now ─────────────────────────────────────────────────────


class TestPullNow:
    """POST /api/v1/mail-accounts/{account_id}/pull-now"""

    @patch("app.api.v1.endpoints.mail_accounts.process_mail_account_task")
    async def test_pull_now_success(self, mock_task, client, mock_db):
        account = _make_account(is_enabled=True)
        mock_db.execute = AsyncMock(return_value=_scalar_one_or_none(account))

        resp = await client.post(f"{BASE}/10/pull-now")
        assert resp.status_code == 202
        assert "queued" in resp.json()["message"].lower()
        mock_task.delay.assert_called_once_with(10)

    @patch("app.api.v1.endpoints.mail_accounts.process_mail_account_task")
    async def test_pull_now_disabled_account(self, mock_task, client, mock_db):
        account = _make_account(is_enabled=False)
        mock_db.execute = AsyncMock(return_value=_scalar_one_or_none(account))

        resp = await client.post(f"{BASE}/10/pull-now")
        assert resp.status_code == 409
        assert "disabled" in resp.json()["detail"].lower()
        mock_task.delay.assert_not_called()

    @patch("app.api.v1.endpoints.mail_accounts.process_mail_account_task")
    async def test_pull_now_not_found(self, mock_task, client, mock_db):
        mock_db.execute = AsyncMock(return_value=_scalar_one_or_none(None))

        resp = await client.post(f"{BASE}/999/pull-now")
        assert resp.status_code == 404


# ── tests: test connection (new) ────────────────────────────────────────


class TestTestConnection:
    """POST /api/v1/mail-accounts/test"""

    @patch("app.api.v1.endpoints.mail_accounts.MailProcessor")
    async def test_connection_success(self, mock_processor_cls, client):
        instance = mock_processor_cls.return_value
        instance.test_connection = AsyncMock(
            return_value=(True, "Connection successful")
        )

        payload = dict(
            host="pop.example.com",
            port=995,
            protocol="pop3_ssl",
            username="user@example.com",
            password="pass",
            use_ssl=True,
            use_tls=False,
        )
        resp = await client.post(f"{BASE}/test", json=payload)
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        assert data["message"] == "Connection successful"

    @patch("app.api.v1.endpoints.mail_accounts.MailProcessor")
    async def test_connection_failure(self, mock_processor_cls, client):
        instance = mock_processor_cls.return_value
        instance.test_connection = AsyncMock(return_value=(False, "Connection refused"))

        payload = dict(
            host="pop.example.com",
            port=995,
            protocol="pop3_ssl",
            username="user@example.com",
            password="pass",
            use_ssl=True,
            use_tls=False,
        )
        resp = await client.post(f"{BASE}/test", json=payload)
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is False
        assert data["message"] == "Connection refused"


# ── tests: test existing connection ─────────────────────────────────────


class TestTestExistingConnection:
    """POST /api/v1/mail-accounts/{account_id}/test"""

    @patch("app.api.v1.endpoints.mail_accounts.MailProcessor")
    @patch(
        "app.api.v1.endpoints.mail_accounts.decrypt_credential",
        return_value="decrypted_pass",
    )
    async def test_existing_connection_success(
        self, mock_decrypt, mock_processor_cls, client, mock_db
    ):
        account = _make_account()
        mock_db.execute = AsyncMock(return_value=_scalar_one_or_none(account))

        instance = mock_processor_cls.return_value
        instance.test_connection = AsyncMock(return_value=(True, "Connected"))

        resp = await client.post(f"{BASE}/10/test")
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        mock_decrypt.assert_called_once_with("encrypted_pass")
        mock_processor_cls.assert_called_once_with(account, "decrypted_pass")

    async def test_existing_connection_not_found(self, client, mock_db):
        mock_db.execute = AsyncMock(return_value=_scalar_one_or_none(None))

        resp = await client.post(f"{BASE}/999/test")
        assert resp.status_code == 404

    @patch("app.api.v1.endpoints.mail_accounts.MailProcessor")
    @patch(
        "app.api.v1.endpoints.mail_accounts.decrypt_credential",
        side_effect=Exception("Decryption failed"),
    )
    async def test_existing_connection_decrypt_failure(
        self, mock_decrypt, mock_processor_cls, client, mock_db
    ):
        account = _make_account()
        mock_db.execute = AsyncMock(return_value=_scalar_one_or_none(account))

        resp = await client.post(f"{BASE}/10/test")
        assert resp.status_code == 500
        assert "decrypt" in resp.json()["detail"].lower()


# ── tests: auto-detect ──────────────────────────────────────────────────


class TestAutoDetect:
    """POST /api/v1/mail-accounts/auto-detect"""

    @patch("app.api.v1.endpoints.mail_accounts.MailServerAutoDetect")
    async def test_auto_detect_success(self, mock_auto_cls, client):
        mock_auto_cls.detect.return_value = [
            {"host": "pop.gmail.com", "port": 995, "protocol": "pop3_ssl"}
        ]

        resp = await client.post(
            f"{BASE}/auto-detect",
            json={"email_address": "user@gmail.com"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        assert len(data["suggestions"]) == 1
        mock_auto_cls.detect.assert_called_once_with("user@gmail.com")

    @patch("app.api.v1.endpoints.mail_accounts.MailServerAutoDetect")
    async def test_auto_detect_no_suggestions(self, mock_auto_cls, client):
        mock_auto_cls.detect.return_value = []

        resp = await client.post(
            f"{BASE}/auto-detect",
            json={"email_address": "user@unknown-domain.xyz"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is False
        assert data["suggestions"] == []


# ── tests: processing runs ──────────────────────────────────────────────


class TestListProcessingRuns:
    """GET /api/v1/mail-accounts/{account_id}/processing-runs"""

    async def test_list_runs_success(self, client, mock_db):
        account = _make_account()
        run = _make_run()

        mock_db.execute = AsyncMock(
            side_effect=[
                _scalar_one_or_none(account),  # ownership check
                _scalar_one(1),  # count
                _scalars_all([run]),  # run data
            ]
        )

        resp = await client.get(f"{BASE}/10/processing-runs")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 1
        assert data["page"] == 1
        assert len(data["items"]) == 1
        assert data["items"][0]["id"] == 100
        assert data["items"][0]["account_name"] == "Test Account"
        assert data["items"][0]["account_email"] == "test@example.com"

    async def test_list_runs_account_not_found(self, client, mock_db):
        mock_db.execute = AsyncMock(return_value=_scalar_one_or_none(None))

        resp = await client.get(f"{BASE}/999/processing-runs")
        assert resp.status_code == 404


# ── tests: processing logs ──────────────────────────────────────────────


class TestListProcessingLogs:
    """GET /api/v1/mail-accounts/{account_id}/logs"""

    async def test_list_logs_success(self, client, mock_db):
        account = _make_account()
        log = _make_log()

        mock_db.execute = AsyncMock(
            side_effect=[
                _scalar_one_or_none(account),  # ownership check
                _scalar_one(1),  # count
                _scalars_all([log]),  # log data
            ]
        )

        resp = await client.get(f"{BASE}/10/logs")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 1
        assert len(data["items"]) == 1
        assert data["items"][0]["id"] == 200
        assert data["items"][0]["level"] == "INFO"
        assert data["items"][0]["message"] == "Processed email"

    async def test_list_logs_account_not_found(self, client, mock_db):
        mock_db.execute = AsyncMock(return_value=_scalar_one_or_none(None))

        resp = await client.get(f"{BASE}/999/logs")
        assert resp.status_code == 404
