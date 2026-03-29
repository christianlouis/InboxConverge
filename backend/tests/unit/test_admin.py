"""
Unit tests for admin endpoints (backend/app/api/v1/endpoints/admin.py).

All tests mock the database session and auth dependencies so no real
PostgreSQL instance is required.
"""

import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

from httpx import AsyncClient, ASGITransport

from app.main import create_application
from app.core.database import get_db
from app.core.deps import get_current_superuser, get_current_user
from app.models.database_models import (
    User,
    ProcessingRun,
    ProcessingLog,
    SubscriptionPlan,
    SubscriptionTier,
    AdminNotificationConfig,
)

# ── helpers ──────────────────────────────────────────────────────────────


def _make_user(**overrides) -> MagicMock:
    """Return a MagicMock that behaves like a User ORM instance."""
    defaults = dict(
        id=1,
        email="admin@example.com",
        hashed_password="hashed",
        full_name="Admin User",
        is_active=True,
        is_superuser=True,
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


def _make_admin_user(**overrides) -> MagicMock:
    return _make_user(**overrides)


def _make_regular_user(**overrides) -> MagicMock:
    return _make_user(id=2, email="user@example.com", is_superuser=False, **overrides)


def _scalar_one_or_none(value):
    """Create a mock result whose .scalar_one_or_none() returns *value*."""
    result = MagicMock()
    result.scalar_one_or_none.return_value = value
    return result


def _scalar_one(value):
    result = MagicMock()
    result.scalar_one.return_value = value
    return result


def _scalar(value):
    result = MagicMock()
    result.scalar.return_value = value
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
def admin_user():
    return _make_admin_user()


@pytest.fixture
def regular_user():
    return _make_regular_user()


@pytest.fixture
def mock_db():
    db = AsyncMock()
    db.commit = AsyncMock()
    db.refresh = AsyncMock()
    db.delete = AsyncMock()
    db.add = MagicMock()
    return db


@pytest.fixture
async def admin_client(app, admin_user, mock_db):
    """AsyncClient where the caller is a superuser and db is mocked."""

    async def _override_superuser():
        return admin_user

    async def _override_db():
        yield mock_db

    app.dependency_overrides[get_current_superuser] = _override_superuser
    app.dependency_overrides[get_current_user] = _override_superuser
    app.dependency_overrides[get_db] = _override_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client

    app.dependency_overrides.clear()


@pytest.fixture
async def noauth_client(app, regular_user, mock_db):
    """AsyncClient where the caller is a regular (non-admin) user."""

    async def _override_user():
        return regular_user

    async def _override_db():
        yield mock_db

    app.dependency_overrides[get_current_user] = _override_user
    app.dependency_overrides[get_db] = _override_db
    # deliberately do NOT override get_current_superuser – it will call
    # get_current_user (which returns a non-superuser) and raise 403.

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client

    app.dependency_overrides.clear()


# ═══════════════════════════════════════════════════════════════════════════
# Auth guard – every admin endpoint must reject non-superusers
# ═══════════════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
class TestAdminAuthGuard:
    """Non-superusers must receive 403 on every admin endpoint."""

    ADMIN_ENDPOINTS = [
        ("GET", "/api/v1/admin/stats"),
        ("GET", "/api/v1/admin/users"),
        ("GET", "/api/v1/admin/users/1"),
        ("PUT", "/api/v1/admin/users/1"),
        ("DELETE", "/api/v1/admin/users/1"),
        ("GET", "/api/v1/admin/plans"),
        ("POST", "/api/v1/admin/plans"),
        ("PUT", "/api/v1/admin/plans/1"),
        ("DELETE", "/api/v1/admin/plans/1"),
        ("GET", "/api/v1/admin/notifications"),
        ("POST", "/api/v1/admin/notifications"),
        ("GET", "/api/v1/admin/notifications/1"),
        ("PUT", "/api/v1/admin/notifications/1"),
        ("DELETE", "/api/v1/admin/notifications/1"),
        ("POST", "/api/v1/admin/notifications/test"),
        ("GET", "/api/v1/admin/processing-runs"),
        ("GET", "/api/v1/admin/processing-logs"),
    ]

    @pytest.mark.parametrize("method,url", ADMIN_ENDPOINTS)
    async def test_non_admin_gets_403(self, noauth_client, method, url):
        json_body = None
        if method == "POST" and "test" in url:
            json_body = {"apprise_url": "json://localhost"}
        elif method == "POST" and "plans" in url:
            json_body = {"tier": "free", "name": "Free", "price_monthly": 0}
        elif method == "POST" and "notifications" in url:
            json_body = {"name": "Test", "apprise_url": "json://localhost"}
        elif method == "PUT" and "users" in url:
            json_body = {"full_name": "x"}
        elif method == "PUT" and "plans" in url:
            json_body = {"name": "x"}
        elif method == "PUT" and "notifications" in url:
            json_body = {"name": "x"}

        kwargs = {}
        if json_body is not None:
            kwargs["json"] = json_body

        response = await getattr(noauth_client, method.lower())(url, **kwargs)
        assert response.status_code == 403, f"{method} {url} should return 403"


# ═══════════════════════════════════════════════════════════════════════════
# GET /admin/stats
# ═══════════════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
class TestAdminStats:
    async def test_returns_stats(self, admin_client, mock_db):
        mock_db.execute = AsyncMock(
            side_effect=[
                _scalar(5),  # user_count
                _scalar(10),  # account_count
                _scalar(20),  # run_count
            ]
        )

        response = await admin_client.get("/api/v1/admin/stats")
        assert response.status_code == 200
        data = response.json()
        assert data["total_users"] == 5
        assert data["total_mail_accounts"] == 10
        assert data["total_processing_runs"] == 20

    async def test_returns_zero_when_empty(self, admin_client, mock_db):
        mock_db.execute = AsyncMock(side_effect=[_scalar(0), _scalar(0), _scalar(0)])
        response = await admin_client.get("/api/v1/admin/stats")
        assert response.status_code == 200
        data = response.json()
        assert data["total_users"] == 0
        assert data["total_mail_accounts"] == 0
        assert data["total_processing_runs"] == 0


# ═══════════════════════════════════════════════════════════════════════════
# GET /admin/users
# ═══════════════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
class TestListUsers:
    async def test_returns_users(self, admin_client, mock_db, admin_user):
        user2 = _make_regular_user()

        # First call: select(User) → users list
        # Second call: select(MailAccount.user_id, count) → counts
        mock_db.execute = AsyncMock(
            side_effect=[
                _scalars_all([admin_user, user2]),
                MagicMock(__iter__=lambda s: iter([])),  # no mail accounts
            ]
        )

        response = await admin_client.get("/api/v1/admin/users")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        assert data[0]["email"] == "admin@example.com"
        assert data[1]["email"] == "user@example.com"

    async def test_empty_list(self, admin_client, mock_db):
        mock_db.execute = AsyncMock(
            side_effect=[
                _scalars_all([]),
                MagicMock(__iter__=lambda s: iter([])),
            ]
        )
        response = await admin_client.get("/api/v1/admin/users")
        assert response.status_code == 200
        assert response.json() == []

    async def test_mail_account_count_populated(
        self, admin_client, mock_db, admin_user
    ):
        count_row = MagicMock(user_id=1, cnt=3)
        mock_db.execute = AsyncMock(
            side_effect=[
                _scalars_all([admin_user]),
                MagicMock(__iter__=lambda s: iter([count_row])),
            ]
        )
        response = await admin_client.get("/api/v1/admin/users")
        assert response.status_code == 200
        data = response.json()
        assert data[0]["mail_account_count"] == 3

    async def test_skip_and_limit(self, admin_client, mock_db):
        mock_db.execute = AsyncMock(
            side_effect=[
                _scalars_all([]),
                MagicMock(__iter__=lambda s: iter([])),
            ]
        )
        response = await admin_client.get(
            "/api/v1/admin/users", params={"skip": 10, "limit": 5}
        )
        assert response.status_code == 200


# ═══════════════════════════════════════════════════════════════════════════
# GET /admin/users/{user_id}
# ═══════════════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
class TestGetUser:
    async def test_returns_user(self, admin_client, mock_db):
        user = _make_regular_user()
        mock_db.execute = AsyncMock(return_value=_scalar_one_or_none(user))

        response = await admin_client.get("/api/v1/admin/users/2")
        assert response.status_code == 200
        data = response.json()
        assert data["email"] == "user@example.com"

    async def test_user_not_found(self, admin_client, mock_db):
        mock_db.execute = AsyncMock(return_value=_scalar_one_or_none(None))

        response = await admin_client.get("/api/v1/admin/users/999")
        assert response.status_code == 404
        assert "User not found" in response.json()["detail"]


# ═══════════════════════════════════════════════════════════════════════════
# PUT /admin/users/{user_id}
# ═══════════════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
class TestUpdateUser:
    async def test_update_full_name(self, admin_client, mock_db):
        user = _make_regular_user()
        mock_db.execute = AsyncMock(return_value=_scalar_one_or_none(user))

        response = await admin_client.put(
            "/api/v1/admin/users/2", json={"full_name": "New Name"}
        )
        assert response.status_code == 200
        assert user.full_name == "New Name"

    async def test_update_email(self, admin_client, mock_db):
        user = _make_regular_user()
        mock_db.execute = AsyncMock(return_value=_scalar_one_or_none(user))

        response = await admin_client.put(
            "/api/v1/admin/users/2", json={"email": "new@example.com"}
        )
        assert response.status_code == 200
        assert user.email == "new@example.com"

    async def test_update_is_active(self, admin_client, mock_db):
        user = _make_regular_user()
        mock_db.execute = AsyncMock(return_value=_scalar_one_or_none(user))

        response = await admin_client.put(
            "/api/v1/admin/users/2", json={"is_active": False}
        )
        assert response.status_code == 200
        assert user.is_active is False

    async def test_update_is_superuser(self, admin_client, mock_db):
        user = _make_regular_user()
        mock_db.execute = AsyncMock(return_value=_scalar_one_or_none(user))

        response = await admin_client.put(
            "/api/v1/admin/users/2", json={"is_superuser": True}
        )
        assert response.status_code == 200
        assert user.is_superuser is True

    async def test_update_subscription_tier(self, admin_client, mock_db):
        user = _make_regular_user()
        mock_db.execute = AsyncMock(return_value=_scalar_one_or_none(user))

        response = await admin_client.put(
            "/api/v1/admin/users/2", json={"subscription_tier": "pro"}
        )
        assert response.status_code == 200
        assert user.subscription_tier == SubscriptionTier.PRO

    async def test_update_subscription_status(self, admin_client, mock_db):
        user = _make_regular_user()
        mock_db.execute = AsyncMock(return_value=_scalar_one_or_none(user))

        response = await admin_client.put(
            "/api/v1/admin/users/2", json={"subscription_status": "canceled"}
        )
        assert response.status_code == 200
        assert user.subscription_status == "canceled"

    async def test_update_multiple_fields(self, admin_client, mock_db):
        user = _make_regular_user()
        mock_db.execute = AsyncMock(return_value=_scalar_one_or_none(user))

        response = await admin_client.put(
            "/api/v1/admin/users/2",
            json={"full_name": "Updated", "is_active": False},
        )
        assert response.status_code == 200
        assert user.full_name == "Updated"
        assert user.is_active is False

    async def test_update_user_not_found(self, admin_client, mock_db):
        mock_db.execute = AsyncMock(return_value=_scalar_one_or_none(None))

        response = await admin_client.put(
            "/api/v1/admin/users/999", json={"full_name": "x"}
        )
        assert response.status_code == 404

    async def test_update_no_changes(self, admin_client, mock_db):
        """Sending an empty body should still succeed (no fields updated)."""
        user = _make_regular_user(full_name="Original")
        mock_db.execute = AsyncMock(return_value=_scalar_one_or_none(user))

        response = await admin_client.put("/api/v1/admin/users/2", json={})
        assert response.status_code == 200
        assert user.full_name == "Original"


# ═══════════════════════════════════════════════════════════════════════════
# DELETE /admin/users/{user_id}
# ═══════════════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
class TestDeleteUser:
    async def test_delete_user(self, admin_client, mock_db):
        user = _make_regular_user()
        mock_db.execute = AsyncMock(return_value=_scalar_one_or_none(user))

        response = await admin_client.delete("/api/v1/admin/users/2")
        assert response.status_code == 204
        mock_db.delete.assert_called_once_with(user)
        mock_db.commit.assert_called()

    async def test_cannot_delete_self(self, admin_client, mock_db, admin_user):
        mock_db.execute = AsyncMock(return_value=_scalar_one_or_none(admin_user))

        response = await admin_client.delete("/api/v1/admin/users/1")
        assert response.status_code == 400
        assert "Cannot delete your own account" in response.json()["detail"]

    async def test_delete_user_not_found(self, admin_client, mock_db):
        mock_db.execute = AsyncMock(return_value=_scalar_one_or_none(None))

        response = await admin_client.delete("/api/v1/admin/users/999")
        assert response.status_code == 404


# ═══════════════════════════════════════════════════════════════════════════
# GET /admin/plans
# ═══════════════════════════════════════════════════════════════════════════


def _make_plan(**overrides):
    defaults = dict(
        id=1,
        tier=SubscriptionTier.FREE,
        name="Free Plan",
        description="Basic access",
        price_monthly=0.0,
        price_yearly=None,
        max_mail_accounts=1,
        max_emails_per_day=100,
        check_interval_minutes=15,
        support_level="community",
        features=None,
        is_active=True,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    defaults.update(overrides)
    plan = MagicMock(spec=SubscriptionPlan)
    for k, v in defaults.items():
        setattr(plan, k, v)
    return plan


@pytest.mark.asyncio
class TestListPlans:
    async def test_returns_plans(self, admin_client, mock_db):
        plan = _make_plan()
        mock_db.execute = AsyncMock(return_value=_scalars_all([plan]))

        response = await admin_client.get("/api/v1/admin/plans")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["name"] == "Free Plan"

    async def test_empty_plans(self, admin_client, mock_db):
        mock_db.execute = AsyncMock(return_value=_scalars_all([]))

        response = await admin_client.get("/api/v1/admin/plans")
        assert response.status_code == 200
        assert response.json() == []


# ═══════════════════════════════════════════════════════════════════════════
# POST /admin/plans
# ═══════════════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
class TestCreatePlan:
    async def test_create_plan(self, admin_client, mock_db):
        # First execute: check existing → None
        mock_db.execute = AsyncMock(return_value=_scalar_one_or_none(None))

        # After add & commit, refresh must populate server-side defaults
        async def _refresh(obj):
            obj.id = 99
            obj.created_at = datetime.now(timezone.utc)
            obj.updated_at = datetime.now(timezone.utc)

        mock_db.refresh = AsyncMock(side_effect=_refresh)

        response = await admin_client.post(
            "/api/v1/admin/plans",
            json={
                "tier": "basic",
                "name": "Basic Plan",
                "price_monthly": 9.99,
                "max_mail_accounts": 5,
                "max_emails_per_day": 1000,
                "check_interval_minutes": 5,
            },
        )
        assert response.status_code == 201
        mock_db.add.assert_called_once()
        mock_db.commit.assert_called()
        data = response.json()
        assert data["name"] == "Basic Plan"
        assert data["tier"] == "basic"

    async def test_duplicate_tier_rejected(self, admin_client, mock_db):
        existing = _make_plan()
        mock_db.execute = AsyncMock(return_value=_scalar_one_or_none(existing))

        response = await admin_client.post(
            "/api/v1/admin/plans",
            json={
                "tier": "free",
                "name": "Another Free",
                "price_monthly": 0,
                "max_mail_accounts": 1,
                "max_emails_per_day": 100,
                "check_interval_minutes": 15,
            },
        )
        assert response.status_code == 400
        assert "already exists" in response.json()["detail"]


# ═══════════════════════════════════════════════════════════════════════════
# PUT /admin/plans/{plan_id}
# ═══════════════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
class TestUpdatePlan:
    async def test_update_plan_name(self, admin_client, mock_db):
        plan = _make_plan()
        mock_db.execute = AsyncMock(return_value=_scalar_one_or_none(plan))

        response = await admin_client.put(
            "/api/v1/admin/plans/1", json={"name": "Updated Free"}
        )
        assert response.status_code == 200
        assert plan.name == "Updated Free"

    async def test_update_plan_pricing(self, admin_client, mock_db):
        plan = _make_plan()
        mock_db.execute = AsyncMock(return_value=_scalar_one_or_none(plan))

        response = await admin_client.put(
            "/api/v1/admin/plans/1",
            json={"price_monthly": 4.99, "price_yearly": 49.99},
        )
        assert response.status_code == 200
        assert plan.price_monthly == 4.99
        assert plan.price_yearly == 49.99

    async def test_update_plan_limits(self, admin_client, mock_db):
        plan = _make_plan()
        mock_db.execute = AsyncMock(return_value=_scalar_one_or_none(plan))

        response = await admin_client.put(
            "/api/v1/admin/plans/1",
            json={
                "max_mail_accounts": 10,
                "max_emails_per_day": 5000,
                "check_interval_minutes": 1,
            },
        )
        assert response.status_code == 200
        assert plan.max_mail_accounts == 10
        assert plan.max_emails_per_day == 5000
        assert plan.check_interval_minutes == 1

    async def test_update_plan_support_and_features(self, admin_client, mock_db):
        plan = _make_plan()
        mock_db.execute = AsyncMock(return_value=_scalar_one_or_none(plan))

        response = await admin_client.put(
            "/api/v1/admin/plans/1",
            json={
                "support_level": "priority",
                "features": {"custom_domains": True},
            },
        )
        assert response.status_code == 200
        assert plan.support_level == "priority"
        assert plan.features == {"custom_domains": True}

    async def test_update_plan_is_active(self, admin_client, mock_db):
        plan = _make_plan()
        mock_db.execute = AsyncMock(return_value=_scalar_one_or_none(plan))

        response = await admin_client.put(
            "/api/v1/admin/plans/1", json={"is_active": False}
        )
        assert response.status_code == 200
        assert plan.is_active is False

    async def test_update_plan_description(self, admin_client, mock_db):
        plan = _make_plan()
        mock_db.execute = AsyncMock(return_value=_scalar_one_or_none(plan))

        response = await admin_client.put(
            "/api/v1/admin/plans/1", json={"description": "New description"}
        )
        assert response.status_code == 200
        assert plan.description == "New description"

    async def test_update_plan_not_found(self, admin_client, mock_db):
        mock_db.execute = AsyncMock(return_value=_scalar_one_or_none(None))

        response = await admin_client.put("/api/v1/admin/plans/999", json={"name": "x"})
        assert response.status_code == 404
        assert "Plan not found" in response.json()["detail"]


# ═══════════════════════════════════════════════════════════════════════════
# DELETE /admin/plans/{plan_id}
# ═══════════════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
class TestDeletePlan:
    async def test_delete_plan(self, admin_client, mock_db):
        plan = _make_plan()
        mock_db.execute = AsyncMock(return_value=_scalar_one_or_none(plan))

        response = await admin_client.delete("/api/v1/admin/plans/1")
        assert response.status_code == 204
        mock_db.delete.assert_called_once_with(plan)

    async def test_delete_plan_not_found(self, admin_client, mock_db):
        mock_db.execute = AsyncMock(return_value=_scalar_one_or_none(None))

        response = await admin_client.delete("/api/v1/admin/plans/999")
        assert response.status_code == 404


# ═══════════════════════════════════════════════════════════════════════════
# Admin notification config CRUD
# ═══════════════════════════════════════════════════════════════════════════


def _make_notification_config(**overrides):
    defaults = dict(
        id=1,
        name="Slack Alert",
        apprise_url="slack://token-a/token-b/token-c",
        is_enabled=True,
        notify_on_errors=True,
        notify_on_system_events=True,
        description="Main alert channel",
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    defaults.update(overrides)
    cfg = MagicMock(spec=AdminNotificationConfig)
    for k, v in defaults.items():
        setattr(cfg, k, v)
    return cfg


@pytest.mark.asyncio
class TestListNotificationConfigs:
    async def test_returns_configs(self, admin_client, mock_db):
        cfg = _make_notification_config()
        mock_db.execute = AsyncMock(return_value=_scalars_all([cfg]))

        response = await admin_client.get("/api/v1/admin/notifications")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["name"] == "Slack Alert"

    async def test_empty_configs(self, admin_client, mock_db):
        mock_db.execute = AsyncMock(return_value=_scalars_all([]))

        response = await admin_client.get("/api/v1/admin/notifications")
        assert response.status_code == 200
        assert response.json() == []


@pytest.mark.asyncio
class TestCreateNotificationConfig:
    async def test_create_config(self, admin_client, mock_db):
        async def _refresh(obj):
            obj.id = 42
            obj.created_at = datetime.now(timezone.utc)
            obj.updated_at = datetime.now(timezone.utc)

        mock_db.refresh = AsyncMock(side_effect=_refresh)
        response = await admin_client.post(
            "/api/v1/admin/notifications",
            json={
                "name": "Discord Alerts",
                "apprise_url": "discord://webhook_id/webhook_token",
                "is_enabled": True,
                "notify_on_errors": True,
                "notify_on_system_events": False,
                "description": "Errors only",
            },
        )
        assert response.status_code == 201
        mock_db.add.assert_called_once()
        mock_db.commit.assert_called()
        data = response.json()
        assert data["name"] == "Discord Alerts"
        assert data["id"] == 42


@pytest.mark.asyncio
class TestGetNotificationConfig:
    async def test_get_config(self, admin_client, mock_db):
        cfg = _make_notification_config()
        mock_db.execute = AsyncMock(return_value=_scalar_one_or_none(cfg))

        response = await admin_client.get("/api/v1/admin/notifications/1")
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Slack Alert"

    async def test_config_not_found(self, admin_client, mock_db):
        mock_db.execute = AsyncMock(return_value=_scalar_one_or_none(None))

        response = await admin_client.get("/api/v1/admin/notifications/999")
        assert response.status_code == 404
        assert "not found" in response.json()["detail"]


@pytest.mark.asyncio
class TestUpdateNotificationConfig:
    async def test_update_name(self, admin_client, mock_db):
        cfg = _make_notification_config()
        mock_db.execute = AsyncMock(return_value=_scalar_one_or_none(cfg))

        response = await admin_client.put(
            "/api/v1/admin/notifications/1", json={"name": "Updated Channel"}
        )
        assert response.status_code == 200
        assert cfg.name == "Updated Channel"

    async def test_update_apprise_url(self, admin_client, mock_db):
        cfg = _make_notification_config()
        mock_db.execute = AsyncMock(return_value=_scalar_one_or_none(cfg))

        response = await admin_client.put(
            "/api/v1/admin/notifications/1",
            json={"apprise_url": "telegram://bot_token/chat_id"},
        )
        assert response.status_code == 200
        assert cfg.apprise_url == "telegram://bot_token/chat_id"

    async def test_update_flags(self, admin_client, mock_db):
        cfg = _make_notification_config()
        mock_db.execute = AsyncMock(return_value=_scalar_one_or_none(cfg))

        response = await admin_client.put(
            "/api/v1/admin/notifications/1",
            json={
                "is_enabled": False,
                "notify_on_errors": False,
                "notify_on_system_events": False,
            },
        )
        assert response.status_code == 200
        assert cfg.is_enabled is False
        assert cfg.notify_on_errors is False
        assert cfg.notify_on_system_events is False

    async def test_update_description(self, admin_client, mock_db):
        cfg = _make_notification_config()
        mock_db.execute = AsyncMock(return_value=_scalar_one_or_none(cfg))

        response = await admin_client.put(
            "/api/v1/admin/notifications/1",
            json={"description": "New description"},
        )
        assert response.status_code == 200
        assert cfg.description == "New description"

    async def test_update_config_not_found(self, admin_client, mock_db):
        mock_db.execute = AsyncMock(return_value=_scalar_one_or_none(None))

        response = await admin_client.put(
            "/api/v1/admin/notifications/999", json={"name": "x"}
        )
        assert response.status_code == 404


@pytest.mark.asyncio
class TestDeleteNotificationConfig:
    async def test_delete_config(self, admin_client, mock_db):
        cfg = _make_notification_config()
        mock_db.execute = AsyncMock(return_value=_scalar_one_or_none(cfg))

        response = await admin_client.delete("/api/v1/admin/notifications/1")
        assert response.status_code == 204
        mock_db.delete.assert_called_once_with(cfg)

    async def test_delete_config_not_found(self, admin_client, mock_db):
        mock_db.execute = AsyncMock(return_value=_scalar_one_or_none(None))

        response = await admin_client.delete("/api/v1/admin/notifications/999")
        assert response.status_code == 404


# ═══════════════════════════════════════════════════════════════════════════
# POST /admin/notifications/test
# ═══════════════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
class TestNotificationTest:
    @patch("app.api.v1.endpoints.admin.test_notification", new_callable=AsyncMock)
    async def test_notification_success(self, mock_test_notif, admin_client):
        mock_test_notif.return_value = (True, "Notification sent successfully")

        response = await admin_client.post(
            "/api/v1/admin/notifications/test",
            json={"apprise_url": "json://localhost"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["message"] == "Notification sent successfully"
        mock_test_notif.assert_called_once_with("json://localhost")

    @patch("app.api.v1.endpoints.admin.test_notification", new_callable=AsyncMock)
    async def test_notification_failure(self, mock_test_notif, admin_client):
        mock_test_notif.return_value = (False, "Connection refused")

        response = await admin_client.post(
            "/api/v1/admin/notifications/test",
            json={"apprise_url": "json://invalid"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is False
        assert data["message"] == "Connection refused"


# ═══════════════════════════════════════════════════════════════════════════
# GET /admin/processing-runs
# ═══════════════════════════════════════════════════════════════════════════


def _make_processing_run_row(**overrides):
    """Simulates a joined query row with ProcessingRun + extras."""
    now = datetime.now(timezone.utc)
    run = MagicMock(spec=ProcessingRun)
    run_defaults = dict(
        id=1,
        mail_account_id=10,
        started_at=now,
        completed_at=now,
        duration_seconds=5.2,
        emails_fetched=10,
        emails_forwarded=8,
        emails_failed=2,
        status="completed",
        error_message=None,
    )
    for k, v in run_defaults.items():
        setattr(run, k, v)

    row = MagicMock()
    row.ProcessingRun = run
    row.account_name = overrides.get("account_name", "Work Email")
    row.account_email = overrides.get("account_email", "john@work.com")
    row.uid = overrides.get("uid", 2)
    row.user_email = overrides.get("user_email", "john@example.com")
    return row


@pytest.mark.asyncio
class TestAdminProcessingRuns:
    async def test_returns_paginated_runs(self, admin_client, mock_db):
        row = _make_processing_run_row()
        # First execute: count
        # Second execute: rows
        mock_db.execute = AsyncMock(
            side_effect=[_scalar_one(1), MagicMock(all=MagicMock(return_value=[row]))]
        )

        response = await admin_client.get("/api/v1/admin/processing-runs")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert data["page"] == 1
        assert data["pages"] == 1
        assert len(data["items"]) == 1
        item = data["items"][0]
        assert item["status"] == "completed"
        assert item["emails_fetched"] == 10
        assert item["user_id"] == 2

    async def test_emails_are_gdpr_masked(self, admin_client, mock_db):
        row = _make_processing_run_row(
            account_email="john.doe@work.com",
            user_email="john.doe@example.com",
        )
        mock_db.execute = AsyncMock(
            side_effect=[_scalar_one(1), MagicMock(all=MagicMock(return_value=[row]))]
        )

        response = await admin_client.get("/api/v1/admin/processing-runs")
        data = response.json()
        item = data["items"][0]
        # GDPR-masked: first 2 chars of local part + ***, first char of domain + ***
        assert "john.doe" not in item["account_email"]
        assert "***" in item["account_email"]
        assert "john.doe" not in item["user_email"]
        assert "***" in item["user_email"]

    async def test_null_emails_handled(self, admin_client, mock_db):
        row = _make_processing_run_row(account_email=None, user_email=None)
        mock_db.execute = AsyncMock(
            side_effect=[_scalar_one(1), MagicMock(all=MagicMock(return_value=[row]))]
        )

        response = await admin_client.get("/api/v1/admin/processing-runs")
        data = response.json()
        item = data["items"][0]
        assert item["account_email"] is None
        assert item["user_email"] is None

    async def test_empty_runs(self, admin_client, mock_db):
        mock_db.execute = AsyncMock(
            side_effect=[_scalar_one(0), MagicMock(all=MagicMock(return_value=[]))]
        )
        response = await admin_client.get("/api/v1/admin/processing-runs")
        data = response.json()
        assert data["total"] == 0
        assert data["items"] == []
        assert data["pages"] == 1

    async def test_filter_by_user_id(self, admin_client, mock_db):
        mock_db.execute = AsyncMock(
            side_effect=[_scalar_one(0), MagicMock(all=MagicMock(return_value=[]))]
        )
        response = await admin_client.get(
            "/api/v1/admin/processing-runs", params={"user_id": 5}
        )
        assert response.status_code == 200

    async def test_filter_by_account_id(self, admin_client, mock_db):
        mock_db.execute = AsyncMock(
            side_effect=[_scalar_one(0), MagicMock(all=MagicMock(return_value=[]))]
        )
        response = await admin_client.get(
            "/api/v1/admin/processing-runs", params={"account_id": 10}
        )
        assert response.status_code == 200

    async def test_filter_by_status(self, admin_client, mock_db):
        mock_db.execute = AsyncMock(
            side_effect=[_scalar_one(0), MagicMock(all=MagicMock(return_value=[]))]
        )
        response = await admin_client.get(
            "/api/v1/admin/processing-runs", params={"status": "failed"}
        )
        assert response.status_code == 200

    async def test_pagination_params(self, admin_client, mock_db):
        mock_db.execute = AsyncMock(
            side_effect=[_scalar_one(50), MagicMock(all=MagicMock(return_value=[]))]
        )
        response = await admin_client.get(
            "/api/v1/admin/processing-runs", params={"page": 3, "page_size": 10}
        )
        data = response.json()
        assert data["page"] == 3
        assert data["page_size"] == 10
        assert data["pages"] == 5  # ceil(50/10)


# ═══════════════════════════════════════════════════════════════════════════
# GET /admin/processing-logs
# ═══════════════════════════════════════════════════════════════════════════


def _make_processing_log_row(**overrides):
    """Simulates a joined query row with ProcessingLog + user_email."""
    now = datetime.now(timezone.utc)
    log = MagicMock(spec=ProcessingLog)
    log_defaults = dict(
        id=1,
        user_id=2,
        mail_account_id=10,
        processing_run_id=100,
        timestamp=now,
        level="INFO",
        message="Email forwarded successfully",
        email_subject="Hello World",
        email_from="Jane Doe <jane@sender.com>",
        email_size_bytes=4096,
        success=True,
        error_details=None,
    )
    for k, v in log_defaults.items():
        setattr(log, k, v)

    row = MagicMock()
    row.ProcessingLog = log
    row.user_email = overrides.get("user_email", "john@example.com")
    return row


@pytest.mark.asyncio
class TestAdminProcessingLogs:
    async def test_returns_paginated_logs(self, admin_client, mock_db):
        row = _make_processing_log_row()
        mock_db.execute = AsyncMock(
            side_effect=[_scalar_one(1), MagicMock(all=MagicMock(return_value=[row]))]
        )

        response = await admin_client.get("/api/v1/admin/processing-logs")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert data["page"] == 1
        assert len(data["items"]) == 1
        item = data["items"][0]
        assert item["level"] == "INFO"
        assert item["success"] is True
        assert item["email_subject"] == "Hello World"

    async def test_sender_is_gdpr_masked(self, admin_client, mock_db):
        row = _make_processing_log_row(user_email="secret.user@example.com")
        mock_db.execute = AsyncMock(
            side_effect=[_scalar_one(1), MagicMock(all=MagicMock(return_value=[row]))]
        )

        response = await admin_client.get("/api/v1/admin/processing-logs")
        data = response.json()
        item = data["items"][0]
        # email_from should be masked by mask_from_header
        assert "jane@sender.com" not in item["email_from"]
        assert "***" in item["email_from"]
        # user_email should be masked too
        assert "secret.user" not in item["user_email"]

    async def test_null_email_from_handled(self, admin_client, mock_db):
        log_row = _make_processing_log_row()
        # Set email_from to None
        log_row.ProcessingLog.email_from = None
        mock_db.execute = AsyncMock(
            side_effect=[
                _scalar_one(1),
                MagicMock(all=MagicMock(return_value=[log_row])),
            ]
        )

        response = await admin_client.get("/api/v1/admin/processing-logs")
        data = response.json()
        assert data["items"][0]["email_from"] is None

    async def test_null_user_email_handled(self, admin_client, mock_db):
        row = _make_processing_log_row(user_email=None)
        mock_db.execute = AsyncMock(
            side_effect=[_scalar_one(1), MagicMock(all=MagicMock(return_value=[row]))]
        )

        response = await admin_client.get("/api/v1/admin/processing-logs")
        data = response.json()
        assert data["items"][0]["user_email"] is None

    async def test_empty_logs(self, admin_client, mock_db):
        mock_db.execute = AsyncMock(
            side_effect=[_scalar_one(0), MagicMock(all=MagicMock(return_value=[]))]
        )
        response = await admin_client.get("/api/v1/admin/processing-logs")
        data = response.json()
        assert data["total"] == 0
        assert data["items"] == []

    async def test_filter_by_user_id(self, admin_client, mock_db):
        mock_db.execute = AsyncMock(
            side_effect=[_scalar_one(0), MagicMock(all=MagicMock(return_value=[]))]
        )
        response = await admin_client.get(
            "/api/v1/admin/processing-logs", params={"user_id": 2}
        )
        assert response.status_code == 200

    async def test_filter_by_account_id(self, admin_client, mock_db):
        mock_db.execute = AsyncMock(
            side_effect=[_scalar_one(0), MagicMock(all=MagicMock(return_value=[]))]
        )
        response = await admin_client.get(
            "/api/v1/admin/processing-logs", params={"account_id": 10}
        )
        assert response.status_code == 200

    async def test_filter_by_run_id(self, admin_client, mock_db):
        mock_db.execute = AsyncMock(
            side_effect=[_scalar_one(0), MagicMock(all=MagicMock(return_value=[]))]
        )
        response = await admin_client.get(
            "/api/v1/admin/processing-logs", params={"run_id": 100}
        )
        assert response.status_code == 200

    async def test_filter_by_level(self, admin_client, mock_db):
        mock_db.execute = AsyncMock(
            side_effect=[_scalar_one(0), MagicMock(all=MagicMock(return_value=[]))]
        )
        response = await admin_client.get(
            "/api/v1/admin/processing-logs", params={"level": "ERROR"}
        )
        assert response.status_code == 200

    async def test_pagination_params(self, admin_client, mock_db):
        mock_db.execute = AsyncMock(
            side_effect=[_scalar_one(200), MagicMock(all=MagicMock(return_value=[]))]
        )
        response = await admin_client.get(
            "/api/v1/admin/processing-logs", params={"page": 2, "page_size": 50}
        )
        data = response.json()
        assert data["page"] == 2
        assert data["page_size"] == 50
        assert data["pages"] == 4  # ceil(200/50)


# ═══════════════════════════════════════════════════════════════════════════
# _admin_paginate helper
# ═══════════════════════════════════════════════════════════════════════════


class TestAdminPaginate:
    """Direct unit tests for the _admin_paginate helper."""

    def test_basic_pagination(self):
        from app.api.v1.endpoints.admin import _admin_paginate

        result = _admin_paginate(total=50, page=1, page_size=20)
        assert result == {"total": 50, "page": 1, "page_size": 20, "pages": 3}

    def test_exact_division(self):
        from app.api.v1.endpoints.admin import _admin_paginate

        result = _admin_paginate(total=40, page=2, page_size=20)
        assert result["pages"] == 2

    def test_zero_total(self):
        from app.api.v1.endpoints.admin import _admin_paginate

        result = _admin_paginate(total=0, page=1, page_size=20)
        assert result["pages"] == 1

    def test_single_item(self):
        from app.api.v1.endpoints.admin import _admin_paginate

        result = _admin_paginate(total=1, page=1, page_size=20)
        assert result["pages"] == 1

    def test_large_page_size(self):
        from app.api.v1.endpoints.admin import _admin_paginate

        result = _admin_paginate(total=5, page=1, page_size=100)
        assert result["pages"] == 1
