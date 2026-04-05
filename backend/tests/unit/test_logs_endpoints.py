"""
Unit tests for processing logs / runs endpoints (api/v1/endpoints/logs.py).

All database interactions and auth dependencies are mocked.
"""

import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

from httpx import AsyncClient, ASGITransport

from app.main import create_application
from app.core.database import get_db
from app.core.deps import get_current_active_user
from app.models.database_models import (
    User,
    ProcessingRun,
    ProcessingLog,
    SubscriptionTier,
)

# ── helpers ──────────────────────────────────────────────────────────────────


def _make_user(**overrides) -> MagicMock:
    defaults = dict(
        id=1,
        email="user@example.com",
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
    u = MagicMock(spec=User)
    for k, v in defaults.items():
        setattr(u, k, v)
    return u


def _make_run(**overrides) -> MagicMock:
    defaults = dict(
        id=1,
        mail_account_id=10,
        started_at=datetime.now(timezone.utc),
        completed_at=datetime.now(timezone.utc),
        duration_seconds=1.5,
        emails_fetched=3,
        emails_forwarded=3,
        emails_failed=0,
        status="completed",
        error_message=None,
    )
    defaults.update(overrides)
    run = MagicMock(spec=ProcessingRun)
    for k, v in defaults.items():
        setattr(run, k, v)
    return run


def _make_log(**overrides) -> MagicMock:
    defaults = dict(
        id=1,
        timestamp=datetime.now(timezone.utc),
        level="INFO",
        message="processed",
        email_subject="Hello",
        email_from="sender@example.com",
        success=True,
        mail_account_id=10,
        processing_run_id=1,
        email_size_bytes=1024,
        error_details=None,
    )
    defaults.update(overrides)
    log = MagicMock(spec=ProcessingLog)
    for k, v in defaults.items():
        setattr(log, k, v)
    return log


def _scalar_one(value):
    r = MagicMock()
    r.scalar_one.return_value = value
    return r


def _scalar_one_or_none(value):
    r = MagicMock()
    r.scalar_one_or_none.return_value = value
    return r


def _rows_all(rows):
    r = MagicMock()
    r.all.return_value = rows
    return r


def _scalars_all(values):
    r = MagicMock()
    scalars = MagicMock()
    scalars.all.return_value = values
    r.scalars.return_value = scalars
    return r


@pytest.fixture
def app():
    return create_application()


@pytest.fixture
def mock_db():
    db = AsyncMock()
    return db


@pytest.fixture
def current_user():
    return _make_user()


@pytest.fixture
async def auth_client(app, current_user, mock_db):
    async def _override_user():
        return current_user

    async def _override_db():
        yield mock_db

    app.dependency_overrides[get_current_active_user] = _override_user
    app.dependency_overrides[get_db] = _override_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client

    app.dependency_overrides.clear()


# ── GET /logs ─────────────────────────────────────────────────────────────────


class TestListProcessingRuns:
    async def test_returns_paginated_list(self, auth_client, mock_db):
        run = _make_run()
        # The endpoint queries total count then rows
        # First execute → count, second execute → rows with joined columns
        row = MagicMock()
        row.ProcessingRun = run
        row.name = "My Account"
        row.email_address = "me@example.com"

        mock_db.execute = AsyncMock(
            side_effect=[
                _scalar_one(1),  # count query
                _rows_all([row]),  # data query
            ]
        )
        response = await auth_client.get("/api/v1/processing-runs")
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "total" in data
        assert data["total"] == 1
        assert len(data["items"]) == 1

    async def test_empty_result(self, auth_client, mock_db):
        mock_db.execute = AsyncMock(
            side_effect=[
                _scalar_one(0),
                _rows_all([]),
            ]
        )
        response = await auth_client.get("/api/v1/processing-runs")
        assert response.status_code == 200
        data = response.json()
        assert data["items"] == []
        assert data["total"] == 0

    async def test_unauthenticated_401(self, app):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/api/v1/processing-runs")
        assert response.status_code == 401

    async def test_pagination_params(self, auth_client, mock_db):
        mock_db.execute = AsyncMock(
            side_effect=[
                _scalar_one(0),
                _rows_all([]),
            ]
        )
        response = await auth_client.get("/api/v1/processing-runs?page=2&page_size=5")
        assert response.status_code == 200
        data = response.json()
        assert data["page"] == 2
        assert data["page_size"] == 5

    async def test_filter_by_account_id(self, auth_client, mock_db):
        mock_db.execute = AsyncMock(
            side_effect=[
                _scalar_one(0),
                _rows_all([]),
            ]
        )
        response = await auth_client.get("/api/v1/processing-runs?account_id=5")
        assert response.status_code == 200

    async def test_filter_by_status(self, auth_client, mock_db):
        mock_db.execute = AsyncMock(
            side_effect=[
                _scalar_one(0),
                _rows_all([]),
            ]
        )
        response = await auth_client.get("/api/v1/processing-runs?status=completed")
        assert response.status_code == 200

    async def test_filter_has_emails(self, auth_client, mock_db):
        mock_db.execute = AsyncMock(
            side_effect=[
                _scalar_one(0),
                _rows_all([]),
            ]
        )
        response = await auth_client.get("/api/v1/processing-runs?has_emails=true")
        assert response.status_code == 200


# ── GET /logs/{run_id} ────────────────────────────────────────────────────────


class TestGetProcessingRun:
    async def test_returns_run(self, auth_client, mock_db):
        run = _make_run(id=42)
        row = MagicMock()
        row.ProcessingRun = run
        row.name = "Account"
        row.email_address = "me@example.com"

        result = MagicMock()
        result.one_or_none.return_value = row
        mock_db.execute = AsyncMock(return_value=result)

        response = await auth_client.get("/api/v1/processing-runs/42")
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == 42

    async def test_404_when_not_found(self, auth_client, mock_db):
        result = MagicMock()
        result.one_or_none.return_value = None
        mock_db.execute = AsyncMock(return_value=result)

        response = await auth_client.get("/api/v1/processing-runs/999")
        assert response.status_code == 404


# ── GET /logs/{run_id}/logs ───────────────────────────────────────────────────


class TestGetRunLogs:
    async def test_returns_log_entries(self, auth_client, mock_db):
        run = _make_run(id=1)
        log_entry = _make_log(processing_run_id=1)

        mock_db.execute = AsyncMock(
            side_effect=[
                _scalar_one_or_none(run),  # ownership check
                _scalar_one(1),  # count
                _scalars_all([log_entry]),  # log entries
            ]
        )
        response = await auth_client.get("/api/v1/processing-runs/1/logs")
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert len(data["items"]) == 1

    async def test_404_when_run_not_found(self, auth_client, mock_db):
        mock_db.execute = AsyncMock(return_value=_scalar_one_or_none(None))
        response = await auth_client.get("/api/v1/processing-runs/999/logs")
        assert response.status_code == 404

    async def test_empty_log_entries(self, auth_client, mock_db):
        run = _make_run(id=1)
        mock_db.execute = AsyncMock(
            side_effect=[
                _scalar_one_or_none(run),
                _scalar_one(0),
                _scalars_all([]),
            ]
        )
        response = await auth_client.get("/api/v1/processing-runs/1/logs")
        assert response.status_code == 200
        data = response.json()
        assert data["items"] == []
        assert data["total"] == 0


# ── helper: _paginate ─────────────────────────────────────────────────────────


class TestPaginateHelper:
    def test_single_page(self):
        from app.api.v1.endpoints.logs import _paginate

        result = _paginate(total=10, page=1, page_size=20)
        assert result["total"] == 10
        assert result["pages"] == 1

    def test_multiple_pages(self):
        from app.api.v1.endpoints.logs import _paginate

        result = _paginate(total=25, page=2, page_size=10)
        assert result["pages"] == 3

    def test_zero_total(self):
        from app.api.v1.endpoints.logs import _paginate

        result = _paginate(total=0, page=1, page_size=20)
        assert result["pages"] == 1
        assert result["total"] == 0
