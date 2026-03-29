"""
Unit tests for Celery tasks in app.workers.tasks.

All database and external-service interactions are mocked so these tests
run without a database or message broker.
"""

from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.models.database_models import DeliveryMethod, DownloadedMessageId
from app.workers.tasks import _as_utc

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

MODULE = "app.workers.tasks"


def _make_account(**overrides) -> MagicMock:
    """Return a MagicMock that behaves like a MailAccount ORM object."""
    defaults = {
        "id": 1,
        "user_id": 10,
        "name": "Test Account",
        "email_address": "src@example.com",
        "host": "imap.example.com",
        "port": 993,
        "use_ssl": True,
        "username": "src@example.com",
        "encrypted_password": "enc-pw",
        "forward_to": "dest@gmail.com",
        "delivery_method": MagicMock(value="gmail_api"),
        "status": MagicMock(value="active"),
        "is_enabled": True,
        "check_interval_minutes": 5,
        "max_emails_per_check": 50,
        "delete_after_forward": True,
        "total_emails_processed": 0,
        "total_emails_failed": 0,
        "last_check_at": None,
        "last_successful_check_at": None,
        "last_error_at": None,
        "last_error_message": None,
    }
    defaults.update(overrides)
    account = MagicMock(**defaults)
    return account


def _build_raw_email(
    subject: str = "Hello",
    sender: str = "alice@example.com",
    body: str = "Test body",
) -> bytes:
    """Build a minimal RFC-822 email as raw bytes."""
    return (
        f"From: {sender}\r\n"
        f"To: dest@example.com\r\n"
        f"Subject: {subject}\r\n"
        f"\r\n"
        f"{body}\r\n"
    ).encode()


def _build_empty_email() -> bytes:
    """Build an RFC-822 email with no subject, sender, or body."""
    return b"\r\n\r\n"


def _mock_session_maker():
    """
    Return (session_maker_mock, session_mock) where session_maker_mock()
    is usable as ``async with session_maker_mock() as db:``.
    """
    session = AsyncMock()

    # Make the session usable as an async context manager
    ctx = AsyncMock()
    ctx.__aenter__ = AsyncMock(return_value=session)
    ctx.__aexit__ = AsyncMock(return_value=False)

    maker = MagicMock(return_value=ctx)
    return maker, session


def _make_gmail_cred(**overrides) -> MagicMock:
    """Return a MagicMock that behaves like a GmailCredential ORM object."""
    defaults = {
        "id": 1,
        "user_id": 10,
        "gmail_email": "dest@gmail.com",
        "encrypted_access_token": "enc-at",
        "encrypted_refresh_token": "enc-rt",
        "token_expiry": datetime.now(timezone.utc) + timedelta(hours=1),
        "is_valid": True,
        "import_label_templates": ["INBOX", "InboxRescue/{source_email}"],
    }
    defaults.update(overrides)
    return MagicMock(**defaults)


def _make_gmail_service(**overrides) -> MagicMock:
    """
    Return a MagicMock that behaves like a GmailService instance.

    ``inject_email`` and ``build_import_label_ids`` are async, while
    ``get_refreshed_token`` is synchronous – mixing AsyncMock/MagicMock
    accordingly avoids "coroutine was never awaited" errors.
    """
    svc = MagicMock()
    svc.build_import_label_ids = AsyncMock(
        return_value=overrides.pop("label_ids", ["INBOX"])
    )
    svc.inject_email = AsyncMock(
        return_value=overrides.pop(
            "inject_result",
            {"message_id": "m1", "thread_id": "t1", "label_ids": ["INBOX"]},
        )
    )
    svc.get_refreshed_token = MagicMock(
        return_value=overrides.pop("refreshed_token", None)
    )
    for k, v in overrides.items():
        setattr(svc, k, v)
    return svc


# ---------------------------------------------------------------------------
# _as_utc tests
# ---------------------------------------------------------------------------


class TestAsUtc:
    """Test the _as_utc() helper."""

    def test_naive_datetime_gets_utc(self):
        dt = datetime(2025, 1, 1, 12, 0, 0)
        result = _as_utc(dt)
        assert result.tzinfo is timezone.utc
        assert result.year == 2025

    def test_aware_datetime_unchanged(self):
        dt = datetime(2025, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        result = _as_utc(dt)
        assert result is dt

    def test_non_utc_aware_datetime_kept(self):
        """A non-UTC aware datetime is returned as-is (tzinfo preserved)."""
        from datetime import timezone as tz

        offset = tz(timedelta(hours=5))
        dt = datetime(2025, 6, 15, 10, 0, 0, tzinfo=offset)
        result = _as_utc(dt)
        assert result is dt
        assert result.tzinfo is offset


# ---------------------------------------------------------------------------
# process_mail_account tests
# ---------------------------------------------------------------------------


class TestProcessMailAccount:
    """Tests for the process_mail_account() async task body."""

    @pytest.mark.asyncio
    async def test_account_not_found(self):
        """Task returns early when the account doesn't exist."""
        maker, session = _mock_session_maker()

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        session.execute.return_value = mock_result

        with (
            patch(f"{MODULE}.async_session_maker", maker),
            patch(f"{MODULE}.engine", AsyncMock()),
        ):
            from app.workers.tasks import process_mail_account

            await process_mail_account.run(999)

        # No commit should happen beyond the initial query
        session.add.assert_not_called()

    @pytest.mark.asyncio
    async def test_account_disabled(self):
        """Task returns early when the account is disabled."""
        account = _make_account(is_enabled=False)
        maker, session = _mock_session_maker()

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = account
        session.execute.return_value = mock_result

        with (
            patch(f"{MODULE}.async_session_maker", maker),
            patch(f"{MODULE}.engine", AsyncMock()),
        ):
            from app.workers.tasks import process_mail_account

            await process_mail_account.run(1)

        session.add.assert_not_called()

    @pytest.mark.asyncio
    async def test_gmail_api_forwarding_success(self):
        """Successful Gmail API forwarding updates run status and account."""

        raw_email = _build_raw_email()
        account = _make_account(
            delivery_method=DeliveryMethod.GMAIL_API,
        )

        maker, session = _mock_session_maker()

        gmail_cred = _make_gmail_cred(user_id=account.user_id)

        # Configure sequential execute() calls
        account_result = MagicMock()
        account_result.scalar_one_or_none.return_value = account

        seen_result = MagicMock()
        seen_result.scalars.return_value.all.return_value = []

        gmail_cred_result = MagicMock()
        gmail_cred_result.scalar_one_or_none.return_value = gmail_cred

        session.execute = AsyncMock(
            side_effect=[account_result, seen_result, gmail_cred_result]
        )
        session.commit = AsyncMock()
        session.refresh = AsyncMock()

        mock_processor = AsyncMock()
        mock_processor.fetch_emails.return_value = ([raw_email], ["uid-1"])

        mock_gmail_svc = _make_gmail_service()
        mock_gmail_svc.build_import_label_ids = AsyncMock(return_value=["INBOX"])
        mock_gmail_svc.inject_email = AsyncMock(
            return_value={
                "message_id": "msg1",
                "thread_id": "t1",
                "label_ids": ["INBOX"],
            }
        )
        mock_gmail_svc.get_refreshed_token = MagicMock(return_value=None)

        with (
            patch(f"{MODULE}.async_session_maker", maker),
            patch(f"{MODULE}.engine", AsyncMock()),
            patch(f"{MODULE}.decrypt_credential", return_value="password123"),
            patch(f"{MODULE}.encrypt_credential", return_value="enc-new"),
            patch(f"{MODULE}.MailProcessor", return_value=mock_processor),
            patch(f"{MODULE}.GmailService", return_value=mock_gmail_svc),
            patch(f"{MODULE}.send_user_notification", new_callable=AsyncMock),
        ):
            from app.workers.tasks import process_mail_account

            await process_mail_account.run(1)

        # Should have committed (ProcessingRun creation + final update)
        assert session.commit.await_count >= 2
        mock_gmail_svc.inject_email.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_smtp_forwarding_user_config(self):
        """SMTP forwarding uses per-user SMTP config when available."""

        raw_email = _build_raw_email()
        account = _make_account(
            delivery_method=DeliveryMethod.SMTP,
        )

        maker, session = _mock_session_maker()

        user_smtp = MagicMock()
        user_smtp.host = "smtp.user.com"
        user_smtp.port = 587
        user_smtp.username = "user@user.com"
        user_smtp.encrypted_password = "enc-smtp-pw"
        user_smtp.use_tls = True

        account_result = MagicMock()
        account_result.scalar_one_or_none.return_value = account

        seen_result = MagicMock()
        seen_result.scalars.return_value.all.return_value = []

        smtp_result = MagicMock()
        smtp_result.scalar_one_or_none.return_value = user_smtp

        session.execute = AsyncMock(
            side_effect=[account_result, seen_result, smtp_result]
        )
        session.commit = AsyncMock()
        session.refresh = AsyncMock()

        mock_processor = AsyncMock()
        mock_processor.fetch_emails.return_value = ([raw_email], ["uid-1"])

        with (
            patch(f"{MODULE}.async_session_maker", maker),
            patch(f"{MODULE}.engine", AsyncMock()),
            patch(f"{MODULE}.decrypt_credential", return_value="password123"),
            patch(f"{MODULE}.MailProcessor", return_value=mock_processor),
            patch(
                f"{MODULE}.MailProcessor.forward_email",
                new_callable=AsyncMock,
                return_value=True,
            ),
            patch(f"{MODULE}.send_user_notification", new_callable=AsyncMock),
        ):
            from app.workers.tasks import process_mail_account

            await process_mail_account.run(1)

        assert session.commit.await_count >= 2

    @pytest.mark.asyncio
    async def test_smtp_forwarding_global_config(self):
        """SMTP forwarding falls back to global config when user has none."""

        raw_email = _build_raw_email()
        account = _make_account(delivery_method=DeliveryMethod.SMTP)

        maker, session = _mock_session_maker()

        # User has no SMTP config
        user_smtp = MagicMock()
        user_smtp.username = None
        user_smtp.encrypted_password = None

        account_result = MagicMock()
        account_result.scalar_one_or_none.return_value = account

        seen_result = MagicMock()
        seen_result.scalars.return_value.all.return_value = []

        smtp_result = MagicMock()
        smtp_result.scalar_one_or_none.return_value = user_smtp

        session.execute = AsyncMock(
            side_effect=[account_result, seen_result, smtp_result]
        )
        session.commit = AsyncMock()
        session.refresh = AsyncMock()

        mock_processor = AsyncMock()
        mock_processor.fetch_emails.return_value = ([raw_email], ["uid-1"])

        global_smtp = {
            "host": "smtp.global.com",
            "port": 587,
            "username": "global@example.com",
            "password": "globalpw",
            "use_tls": True,
        }

        with (
            patch(f"{MODULE}.async_session_maker", maker),
            patch(f"{MODULE}.engine", AsyncMock()),
            patch(f"{MODULE}.decrypt_credential", return_value="password123"),
            patch(f"{MODULE}.MailProcessor", return_value=mock_processor),
            patch(
                f"{MODULE}.MailProcessor.forward_email",
                new_callable=AsyncMock,
                return_value=True,
            ),
            patch(
                f"{MODULE}.ConfigService.get_smtp_config",
                new_callable=AsyncMock,
                return_value=global_smtp,
            ),
            patch(f"{MODULE}.send_user_notification", new_callable=AsyncMock),
        ):
            from app.workers.tasks import process_mail_account

            await process_mail_account.run(1)

        assert session.commit.await_count >= 2

    @pytest.mark.asyncio
    async def test_smtp_missing_credentials_fails_run(self):
        """Run is marked 'failed' when SMTP credentials are missing."""

        raw_email = _build_raw_email()
        account = _make_account(delivery_method=DeliveryMethod.SMTP)

        maker, session = _mock_session_maker()

        user_smtp = MagicMock()
        user_smtp.username = None
        user_smtp.encrypted_password = None

        account_result = MagicMock()
        account_result.scalar_one_or_none.return_value = account

        seen_result = MagicMock()
        seen_result.scalars.return_value.all.return_value = []

        smtp_result = MagicMock()
        smtp_result.scalar_one_or_none.return_value = user_smtp

        session.execute = AsyncMock(
            side_effect=[account_result, seen_result, smtp_result]
        )
        session.commit = AsyncMock()
        session.refresh = AsyncMock()

        mock_processor = AsyncMock()
        mock_processor.fetch_emails.return_value = ([raw_email], ["uid-1"])

        # Global SMTP also has no credentials
        global_smtp = {
            "host": "smtp.global.com",
            "port": 587,
            "username": "",
            "password": "",
            "use_tls": True,
        }

        with (
            patch(f"{MODULE}.async_session_maker", maker),
            patch(f"{MODULE}.engine", AsyncMock()),
            patch(f"{MODULE}.decrypt_credential", return_value="password123"),
            patch(f"{MODULE}.MailProcessor", return_value=mock_processor),
            patch(
                f"{MODULE}.ConfigService.get_smtp_config",
                new_callable=AsyncMock,
                return_value=global_smtp,
            ),
            patch(f"{MODULE}.send_user_notification", new_callable=AsyncMock),
        ):
            from app.workers.tasks import process_mail_account

            await process_mail_account.run(1)

        # The run should have been committed with status "failed"
        assert session.commit.await_count >= 1

    @pytest.mark.asyncio
    async def test_gmail_cred_missing_falls_back_to_smtp(self):
        """Falls back to SMTP when Gmail creds are not found."""

        raw_email = _build_raw_email()
        account = _make_account(delivery_method=DeliveryMethod.GMAIL_API)

        maker, session = _mock_session_maker()

        account_result = MagicMock()
        account_result.scalar_one_or_none.return_value = account

        seen_result = MagicMock()
        seen_result.scalars.return_value.all.return_value = []

        # No gmail creds
        gmail_cred_result = MagicMock()
        gmail_cred_result.scalar_one_or_none.return_value = None

        # User SMTP config
        user_smtp = MagicMock()
        user_smtp.host = "smtp.user.com"
        user_smtp.port = 587
        user_smtp.username = "user@user.com"
        user_smtp.encrypted_password = "enc-smtp-pw"
        user_smtp.use_tls = True

        smtp_result = MagicMock()
        smtp_result.scalar_one_or_none.return_value = user_smtp

        session.execute = AsyncMock(
            side_effect=[
                account_result,
                seen_result,
                gmail_cred_result,
                smtp_result,
            ]
        )
        session.commit = AsyncMock()
        session.refresh = AsyncMock()

        mock_processor = AsyncMock()
        mock_processor.fetch_emails.return_value = ([raw_email], ["uid-1"])

        with (
            patch(f"{MODULE}.async_session_maker", maker),
            patch(f"{MODULE}.engine", AsyncMock()),
            patch(f"{MODULE}.decrypt_credential", return_value="password123"),
            patch(f"{MODULE}.MailProcessor", return_value=mock_processor),
            patch(
                f"{MODULE}.MailProcessor.forward_email",
                new_callable=AsyncMock,
                return_value=True,
            ),
            patch(f"{MODULE}.send_user_notification", new_callable=AsyncMock),
        ):
            from app.workers.tasks import process_mail_account

            await process_mail_account.run(1)

        assert session.commit.await_count >= 2

    @pytest.mark.asyncio
    async def test_empty_email_skipped(self):
        """Empty emails are logged as warnings and their UIDs persisted."""

        empty_email = _build_empty_email()
        account = _make_account(delivery_method=DeliveryMethod.GMAIL_API)

        maker, session = _mock_session_maker()

        gmail_cred = _make_gmail_cred(user_id=account.user_id)

        account_result = MagicMock()
        account_result.scalar_one_or_none.return_value = account

        seen_result = MagicMock()
        seen_result.scalars.return_value.all.return_value = []

        gmail_cred_result = MagicMock()
        gmail_cred_result.scalar_one_or_none.return_value = gmail_cred

        session.execute = AsyncMock(
            side_effect=[account_result, seen_result, gmail_cred_result]
        )
        session.commit = AsyncMock()
        session.refresh = AsyncMock()

        mock_processor = AsyncMock()
        mock_processor.fetch_emails.return_value = ([empty_email], ["uid-empty"])

        mock_gmail_svc = _make_gmail_service()
        mock_gmail_svc.get_refreshed_token = MagicMock(return_value=None)

        with (
            patch(f"{MODULE}.async_session_maker", maker),
            patch(f"{MODULE}.engine", AsyncMock()),
            patch(f"{MODULE}.decrypt_credential", return_value="password123"),
            patch(f"{MODULE}.MailProcessor", return_value=mock_processor),
            patch(f"{MODULE}.GmailService", return_value=mock_gmail_svc),
            patch(f"{MODULE}.send_user_notification", new_callable=AsyncMock),
        ):
            from app.workers.tasks import process_mail_account

            await process_mail_account.run(1)

        # inject_email should NOT be called for empty emails
        mock_gmail_svc.inject_email.assert_not_awaited()

        # session.add should be called for the ProcessingLog (warning) and
        # the DownloadedMessageId (to record the empty UID)
        add_calls = session.add.call_args_list
        assert len(add_calls) >= 2  # ProcessingRun + at least the log entries

    @pytest.mark.asyncio
    async def test_email_forwarding_failure_partial(self):
        """Partial failures are recorded in run status and account."""

        raw_email = _build_raw_email()
        account = _make_account(delivery_method=DeliveryMethod.SMTP)

        maker, session = _mock_session_maker()

        user_smtp = MagicMock()
        user_smtp.host = "smtp.user.com"
        user_smtp.port = 587
        user_smtp.username = "user@user.com"
        user_smtp.encrypted_password = "enc-pw"
        user_smtp.use_tls = True

        account_result = MagicMock()
        account_result.scalar_one_or_none.return_value = account

        seen_result = MagicMock()
        seen_result.scalars.return_value.all.return_value = []

        smtp_result = MagicMock()
        smtp_result.scalar_one_or_none.return_value = user_smtp

        session.execute = AsyncMock(
            side_effect=[account_result, seen_result, smtp_result]
        )
        session.commit = AsyncMock()
        session.refresh = AsyncMock()

        mock_processor = AsyncMock()
        # Two emails: first succeeds, second fails
        mock_processor.fetch_emails.return_value = (
            [raw_email, raw_email],
            ["uid-1", "uid-2"],
        )

        with (
            patch(f"{MODULE}.async_session_maker", maker),
            patch(f"{MODULE}.engine", AsyncMock()),
            patch(f"{MODULE}.decrypt_credential", return_value="password123"),
            patch(f"{MODULE}.MailProcessor", return_value=mock_processor),
            patch(
                f"{MODULE}.MailProcessor.forward_email",
                new_callable=AsyncMock,
                side_effect=[True, False],
            ),
            patch(f"{MODULE}.send_user_notification", new_callable=AsyncMock),
        ):
            from app.workers.tasks import process_mail_account

            await process_mail_account.run(1)

        assert session.commit.await_count >= 2

    @pytest.mark.asyncio
    async def test_gmail_credential_revocation_on_401(self):
        """Gmail 401 error invalidates credentials and sends notification."""

        raw_email = _build_raw_email()
        account = _make_account(delivery_method=DeliveryMethod.GMAIL_API)

        maker, session = _mock_session_maker()

        gmail_cred = _make_gmail_cred(user_id=account.user_id)

        account_result = MagicMock()
        account_result.scalar_one_or_none.return_value = account

        seen_result = MagicMock()
        seen_result.scalars.return_value.all.return_value = []

        gmail_cred_result = MagicMock()
        gmail_cred_result.scalar_one_or_none.return_value = gmail_cred

        session.execute = AsyncMock(
            side_effect=[account_result, seen_result, gmail_cred_result]
        )
        session.commit = AsyncMock()
        session.refresh = AsyncMock()

        mock_processor = AsyncMock()
        mock_processor.fetch_emails.return_value = ([raw_email], ["uid-1"])

        mock_gmail_svc = _make_gmail_service()
        mock_gmail_svc.build_import_label_ids = AsyncMock(return_value=["INBOX"])
        mock_gmail_svc.inject_email = AsyncMock(
            side_effect=Exception("HTTP 401 Unauthorized")
        )
        mock_gmail_svc.get_refreshed_token = MagicMock(return_value=None)

        mock_send_notification = AsyncMock()

        with (
            patch(f"{MODULE}.async_session_maker", maker),
            patch(f"{MODULE}.engine", AsyncMock()),
            patch(f"{MODULE}.decrypt_credential", return_value="password123"),
            patch(f"{MODULE}.MailProcessor", return_value=mock_processor),
            patch(f"{MODULE}.GmailService", return_value=mock_gmail_svc),
            patch(f"{MODULE}.send_user_notification", mock_send_notification),
        ):
            from app.workers.tasks import process_mail_account

            await process_mail_account.run(1)

        # Gmail cred should be marked invalid
        assert gmail_cred.is_valid is False

    @pytest.mark.asyncio
    async def test_gmail_credential_revocation_on_403(self):
        """Gmail 403 error also invalidates credentials."""

        raw_email = _build_raw_email()
        account = _make_account(delivery_method=DeliveryMethod.GMAIL_API)

        maker, session = _mock_session_maker()

        gmail_cred = _make_gmail_cred(user_id=account.user_id)

        account_result = MagicMock()
        account_result.scalar_one_or_none.return_value = account

        seen_result = MagicMock()
        seen_result.scalars.return_value.all.return_value = []

        gmail_cred_result = MagicMock()
        gmail_cred_result.scalar_one_or_none.return_value = gmail_cred

        session.execute = AsyncMock(
            side_effect=[account_result, seen_result, gmail_cred_result]
        )
        session.commit = AsyncMock()
        session.refresh = AsyncMock()

        mock_processor = AsyncMock()
        mock_processor.fetch_emails.return_value = ([raw_email], ["uid-1"])

        mock_gmail_svc = _make_gmail_service()
        mock_gmail_svc.build_import_label_ids = AsyncMock(return_value=["INBOX"])
        mock_gmail_svc.inject_email = AsyncMock(
            side_effect=Exception("HTTP 403 Forbidden")
        )
        mock_gmail_svc.get_refreshed_token = MagicMock(return_value=None)

        with (
            patch(f"{MODULE}.async_session_maker", maker),
            patch(f"{MODULE}.engine", AsyncMock()),
            patch(f"{MODULE}.decrypt_credential", return_value="password123"),
            patch(f"{MODULE}.MailProcessor", return_value=mock_processor),
            patch(f"{MODULE}.GmailService", return_value=mock_gmail_svc),
            patch(f"{MODULE}.send_user_notification", new_callable=AsyncMock),
        ):
            from app.workers.tasks import process_mail_account

            await process_mail_account.run(1)

        assert gmail_cred.is_valid is False

    @pytest.mark.asyncio
    async def test_gmail_credential_revocation_on_invalid_grant(self):
        """Gmail invalid_grant error also invalidates credentials."""

        raw_email = _build_raw_email()
        account = _make_account(delivery_method=DeliveryMethod.GMAIL_API)

        maker, session = _mock_session_maker()

        gmail_cred = _make_gmail_cred(user_id=account.user_id)

        account_result = MagicMock()
        account_result.scalar_one_or_none.return_value = account

        seen_result = MagicMock()
        seen_result.scalars.return_value.all.return_value = []

        gmail_cred_result = MagicMock()
        gmail_cred_result.scalar_one_or_none.return_value = gmail_cred

        session.execute = AsyncMock(
            side_effect=[account_result, seen_result, gmail_cred_result]
        )
        session.commit = AsyncMock()
        session.refresh = AsyncMock()

        mock_processor = AsyncMock()
        mock_processor.fetch_emails.return_value = ([raw_email], ["uid-1"])

        mock_gmail_svc = _make_gmail_service()
        mock_gmail_svc.build_import_label_ids = AsyncMock(return_value=["INBOX"])
        mock_gmail_svc.inject_email = AsyncMock(side_effect=Exception("invalid_grant"))
        mock_gmail_svc.get_refreshed_token = MagicMock(return_value=None)

        with (
            patch(f"{MODULE}.async_session_maker", maker),
            patch(f"{MODULE}.engine", AsyncMock()),
            patch(f"{MODULE}.decrypt_credential", return_value="password123"),
            patch(f"{MODULE}.MailProcessor", return_value=mock_processor),
            patch(f"{MODULE}.GmailService", return_value=mock_gmail_svc),
            patch(f"{MODULE}.send_user_notification", new_callable=AsyncMock),
        ):
            from app.workers.tasks import process_mail_account

            await process_mail_account.run(1)

        assert gmail_cred.is_valid is False

    @pytest.mark.asyncio
    async def test_refreshed_gmail_token_persisted(self):
        """A refreshed Gmail access token is written back to the DB."""

        raw_email = _build_raw_email()
        account = _make_account(delivery_method=DeliveryMethod.GMAIL_API)

        maker, session = _mock_session_maker()

        gmail_cred = _make_gmail_cred(user_id=account.user_id)

        account_result = MagicMock()
        account_result.scalar_one_or_none.return_value = account

        seen_result = MagicMock()
        seen_result.scalars.return_value.all.return_value = []

        gmail_cred_result = MagicMock()
        gmail_cred_result.scalar_one_or_none.return_value = gmail_cred

        session.execute = AsyncMock(
            side_effect=[account_result, seen_result, gmail_cred_result]
        )
        session.commit = AsyncMock()
        session.refresh = AsyncMock()

        mock_processor = AsyncMock()
        mock_processor.fetch_emails.return_value = ([raw_email], ["uid-1"])

        new_expiry = datetime.now(timezone.utc) + timedelta(hours=1)
        mock_gmail_svc = _make_gmail_service()
        mock_gmail_svc.build_import_label_ids = AsyncMock(return_value=["INBOX"])
        mock_gmail_svc.inject_email = AsyncMock(
            return_value={
                "message_id": "m1",
                "thread_id": "t1",
                "label_ids": ["INBOX"],
            }
        )
        mock_gmail_svc.get_refreshed_token = MagicMock(
            return_value={
                "access_token": "new-access-token",
                "expiry": new_expiry,
            }
        )

        with (
            patch(f"{MODULE}.async_session_maker", maker),
            patch(f"{MODULE}.engine", AsyncMock()),
            patch(f"{MODULE}.decrypt_credential", return_value="password123"),
            patch(f"{MODULE}.encrypt_credential", return_value="enc-new-token"),
            patch(f"{MODULE}.MailProcessor", return_value=mock_processor),
            patch(f"{MODULE}.GmailService", return_value=mock_gmail_svc),
            patch(f"{MODULE}.send_user_notification", new_callable=AsyncMock),
        ):
            from app.workers.tasks import process_mail_account

            await process_mail_account.run(1)

        # Verify the refreshed token was persisted
        assert gmail_cred.encrypted_access_token == "enc-new-token"
        assert gmail_cred.token_expiry == new_expiry

    @pytest.mark.asyncio
    async def test_outer_exception_marks_run_failed(self):
        """An unexpected exception triggers rollback and marks the run failed."""

        account = _make_account(delivery_method=DeliveryMethod.GMAIL_API)

        maker, session = _mock_session_maker()

        account_result = MagicMock()
        account_result.scalar_one_or_none.return_value = account

        session.execute = AsyncMock(side_effect=[account_result])
        # commit succeeds for the ProcessingRun creation but we make the
        # second execute blow up
        commit_count = 0

        async def commit_side_effect():
            nonlocal commit_count
            commit_count += 1
            if commit_count >= 2:
                raise RuntimeError("Simulated DB crash")

        session.commit = AsyncMock(side_effect=commit_side_effect)
        session.refresh = AsyncMock()
        session.rollback = AsyncMock()

        with (
            patch(f"{MODULE}.async_session_maker", maker),
            patch(f"{MODULE}.engine", AsyncMock()),
            patch(f"{MODULE}.decrypt_credential", return_value="password123"),
            patch(f"{MODULE}.send_user_notification", new_callable=AsyncMock),
        ):
            from app.workers.tasks import process_mail_account

            # Should not raise
            await process_mail_account.run(1)

        session.rollback.assert_awaited()

    @pytest.mark.asyncio
    async def test_no_new_emails(self):
        """When fetch_emails returns empty, run completes cleanly."""

        account = _make_account(delivery_method=DeliveryMethod.GMAIL_API)

        maker, session = _mock_session_maker()

        gmail_cred = _make_gmail_cred(user_id=account.user_id)

        account_result = MagicMock()
        account_result.scalar_one_or_none.return_value = account

        seen_result = MagicMock()
        seen_result.scalars.return_value.all.return_value = []

        gmail_cred_result = MagicMock()
        gmail_cred_result.scalar_one_or_none.return_value = gmail_cred

        session.execute = AsyncMock(
            side_effect=[account_result, seen_result, gmail_cred_result]
        )
        session.commit = AsyncMock()
        session.refresh = AsyncMock()

        mock_processor = AsyncMock()
        mock_processor.fetch_emails.return_value = ([], [])

        mock_gmail_svc = _make_gmail_service()
        mock_gmail_svc.get_refreshed_token = MagicMock(return_value=None)

        with (
            patch(f"{MODULE}.async_session_maker", maker),
            patch(f"{MODULE}.engine", AsyncMock()),
            patch(f"{MODULE}.decrypt_credential", return_value="password123"),
            patch(f"{MODULE}.MailProcessor", return_value=mock_processor),
            patch(f"{MODULE}.GmailService", return_value=mock_gmail_svc),
            patch(f"{MODULE}.send_user_notification", new_callable=AsyncMock),
        ):
            from app.workers.tasks import process_mail_account

            await process_mail_account.run(1)

        assert session.commit.await_count >= 2

    @pytest.mark.asyncio
    async def test_notification_failure_does_not_break_task(self):
        """A failing notification does not crash the task."""

        raw_email = _build_raw_email()
        account = _make_account(delivery_method=DeliveryMethod.SMTP)

        maker, session = _mock_session_maker()

        user_smtp = MagicMock()
        user_smtp.host = "smtp.user.com"
        user_smtp.port = 587
        user_smtp.username = "user@user.com"
        user_smtp.encrypted_password = "enc-pw"
        user_smtp.use_tls = True

        account_result = MagicMock()
        account_result.scalar_one_or_none.return_value = account

        seen_result = MagicMock()
        seen_result.scalars.return_value.all.return_value = []

        smtp_result = MagicMock()
        smtp_result.scalar_one_or_none.return_value = user_smtp

        session.execute = AsyncMock(
            side_effect=[account_result, seen_result, smtp_result]
        )
        session.commit = AsyncMock()
        session.refresh = AsyncMock()

        mock_processor = AsyncMock()
        mock_processor.fetch_emails.return_value = ([raw_email], ["uid-1"])

        mock_send_notification = AsyncMock(side_effect=Exception("Notification failed"))

        with (
            patch(f"{MODULE}.async_session_maker", maker),
            patch(f"{MODULE}.engine", AsyncMock()),
            patch(f"{MODULE}.decrypt_credential", return_value="password123"),
            patch(f"{MODULE}.MailProcessor", return_value=mock_processor),
            patch(
                f"{MODULE}.MailProcessor.forward_email",
                new_callable=AsyncMock,
                return_value=False,
            ),
            patch(f"{MODULE}.send_user_notification", mock_send_notification),
        ):
            from app.workers.tasks import process_mail_account

            # Should not raise despite notification failure
            await process_mail_account.run(1)

    @pytest.mark.asyncio
    async def test_already_seen_uids_skipped(self):
        """Previously downloaded UIDs should not be re-persisted."""

        raw_email = _build_raw_email()
        account = _make_account(delivery_method=DeliveryMethod.GMAIL_API)

        maker, session = _mock_session_maker()

        gmail_cred = _make_gmail_cred(user_id=account.user_id)

        account_result = MagicMock()
        account_result.scalar_one_or_none.return_value = account

        # uid-1 was already seen
        seen_result = MagicMock()
        seen_result.scalars.return_value.all.return_value = ["uid-1"]

        gmail_cred_result = MagicMock()
        gmail_cred_result.scalar_one_or_none.return_value = gmail_cred

        session.execute = AsyncMock(
            side_effect=[account_result, seen_result, gmail_cred_result]
        )
        session.commit = AsyncMock()
        session.refresh = AsyncMock()

        mock_processor = AsyncMock()
        # fetch_emails still returns uid-1 (MailProcessor may not filter)
        mock_processor.fetch_emails.return_value = ([raw_email], ["uid-1"])

        mock_gmail_svc = _make_gmail_service()
        mock_gmail_svc.build_import_label_ids = AsyncMock(return_value=["INBOX"])
        mock_gmail_svc.inject_email = AsyncMock(
            return_value={
                "message_id": "m1",
                "thread_id": "t1",
                "label_ids": ["INBOX"],
            }
        )
        mock_gmail_svc.get_refreshed_token = MagicMock(return_value=None)

        with (
            patch(f"{MODULE}.async_session_maker", maker),
            patch(f"{MODULE}.engine", AsyncMock()),
            patch(f"{MODULE}.decrypt_credential", return_value="password123"),
            patch(f"{MODULE}.MailProcessor", return_value=mock_processor),
            patch(f"{MODULE}.GmailService", return_value=mock_gmail_svc),
            patch(f"{MODULE}.send_user_notification", new_callable=AsyncMock),
        ):
            from app.workers.tasks import process_mail_account

            await process_mail_account.run(1)

        # Count DownloadedMessageId objects added — uid-1 is already seen
        # so should NOT create a new DownloadedMessageId for it

        added_downloaded = [
            c
            for c in session.add.call_args_list
            if isinstance(c[0][0], DownloadedMessageId)
        ]
        assert len(added_downloaded) == 0

    @pytest.mark.asyncio
    async def test_gmail_no_refresh_token(self):
        """Gmail credential without refresh_token works (refresh_token=None)."""

        raw_email = _build_raw_email()
        account = _make_account(delivery_method=DeliveryMethod.GMAIL_API)

        maker, session = _mock_session_maker()

        gmail_cred = _make_gmail_cred(
            user_id=account.user_id,
            encrypted_refresh_token=None,
        )

        account_result = MagicMock()
        account_result.scalar_one_or_none.return_value = account

        seen_result = MagicMock()
        seen_result.scalars.return_value.all.return_value = []

        gmail_cred_result = MagicMock()
        gmail_cred_result.scalar_one_or_none.return_value = gmail_cred

        session.execute = AsyncMock(
            side_effect=[account_result, seen_result, gmail_cred_result]
        )
        session.commit = AsyncMock()
        session.refresh = AsyncMock()

        mock_processor = AsyncMock()
        mock_processor.fetch_emails.return_value = ([raw_email], ["uid-1"])

        mock_gmail_svc = _make_gmail_service()
        mock_gmail_svc.build_import_label_ids = AsyncMock(return_value=["INBOX"])
        mock_gmail_svc.inject_email = AsyncMock(
            return_value={
                "message_id": "m1",
                "thread_id": "t1",
                "label_ids": ["INBOX"],
            }
        )
        mock_gmail_svc.get_refreshed_token = MagicMock(return_value=None)

        with (
            patch(f"{MODULE}.async_session_maker", maker),
            patch(f"{MODULE}.engine", AsyncMock()),
            patch(f"{MODULE}.decrypt_credential", return_value="password123"),
            patch(f"{MODULE}.MailProcessor", return_value=mock_processor),
            patch(f"{MODULE}.GmailService", return_value=mock_gmail_svc),
            patch(f"{MODULE}.send_user_notification", new_callable=AsyncMock),
        ):
            from app.workers.tasks import process_mail_account

            await process_mail_account.run(1)

        mock_gmail_svc.inject_email.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_emails_uids_length_mismatch(self):
        """When emails and UIDs lists differ in length, truncation occurs."""

        raw_email = _build_raw_email()
        account = _make_account(delivery_method=DeliveryMethod.GMAIL_API)

        maker, session = _mock_session_maker()

        gmail_cred = _make_gmail_cred(user_id=account.user_id)

        account_result = MagicMock()
        account_result.scalar_one_or_none.return_value = account

        seen_result = MagicMock()
        seen_result.scalars.return_value.all.return_value = []

        gmail_cred_result = MagicMock()
        gmail_cred_result.scalar_one_or_none.return_value = gmail_cred

        session.execute = AsyncMock(
            side_effect=[account_result, seen_result, gmail_cred_result]
        )
        session.commit = AsyncMock()
        session.refresh = AsyncMock()

        mock_processor = AsyncMock()
        # 2 emails but 3 UIDs → mismatch logged
        mock_processor.fetch_emails.return_value = (
            [raw_email, raw_email],
            ["uid-1", "uid-2", "uid-3"],
        )

        mock_gmail_svc = _make_gmail_service()

        with (
            patch(f"{MODULE}.async_session_maker", maker),
            patch(f"{MODULE}.engine", AsyncMock()),
            patch(f"{MODULE}.decrypt_credential", return_value="password123"),
            patch(f"{MODULE}.MailProcessor", return_value=mock_processor),
            patch(f"{MODULE}.GmailService", return_value=mock_gmail_svc),
            patch(f"{MODULE}.send_user_notification", new_callable=AsyncMock),
        ):
            from app.workers.tasks import process_mail_account

            await process_mail_account.run(1)

        # inject_email should be called twice (zip truncates)
        assert mock_gmail_svc.inject_email.await_count == 2

    @pytest.mark.asyncio
    async def test_email_header_parse_error(self):
        """Malformed email headers don't crash the processing loop."""

        # Produce bytes that email_lib.message_from_bytes can technically
        # parse but where header extraction will return empty strings.
        malformed_email = b"\xff\xfe invalid bytes"
        account = _make_account(delivery_method=DeliveryMethod.GMAIL_API)

        maker, session = _mock_session_maker()

        gmail_cred = _make_gmail_cred(user_id=account.user_id)

        account_result = MagicMock()
        account_result.scalar_one_or_none.return_value = account

        seen_result = MagicMock()
        seen_result.scalars.return_value.all.return_value = []

        gmail_cred_result = MagicMock()
        gmail_cred_result.scalar_one_or_none.return_value = gmail_cred

        session.execute = AsyncMock(
            side_effect=[account_result, seen_result, gmail_cred_result]
        )
        session.commit = AsyncMock()
        session.refresh = AsyncMock()

        mock_processor = AsyncMock()
        mock_processor.fetch_emails.return_value = (
            [malformed_email],
            ["uid-malformed"],
        )

        mock_gmail_svc = _make_gmail_service()

        with (
            patch(f"{MODULE}.async_session_maker", maker),
            patch(f"{MODULE}.engine", AsyncMock()),
            patch(f"{MODULE}.decrypt_credential", return_value="password123"),
            patch(f"{MODULE}.MailProcessor", return_value=mock_processor),
            patch(f"{MODULE}.GmailService", return_value=mock_gmail_svc),
            patch(f"{MODULE}.send_user_notification", new_callable=AsyncMock),
        ):
            from app.workers.tasks import process_mail_account

            # Should not raise
            await process_mail_account.run(1)

    @pytest.mark.asyncio
    async def test_multipart_empty_email_detected(self):
        """A multipart email with no real content is detected as empty."""

        # Build a multipart email with no subject/from and empty parts
        multipart_empty = (
            b"MIME-Version: 1.0\r\n"
            b'Content-Type: multipart/mixed; boundary="boundary123"\r\n'
            b"\r\n"
            b"--boundary123\r\n"
            b"Content-Type: text/plain\r\n"
            b"\r\n"
            b"   \r\n"
            b"--boundary123--\r\n"
        )
        account = _make_account(delivery_method=DeliveryMethod.GMAIL_API)

        maker, session = _mock_session_maker()

        gmail_cred = _make_gmail_cred(user_id=account.user_id)

        account_result = MagicMock()
        account_result.scalar_one_or_none.return_value = account

        seen_result = MagicMock()
        seen_result.scalars.return_value.all.return_value = []

        gmail_cred_result = MagicMock()
        gmail_cred_result.scalar_one_or_none.return_value = gmail_cred

        session.execute = AsyncMock(
            side_effect=[account_result, seen_result, gmail_cred_result]
        )
        session.commit = AsyncMock()
        session.refresh = AsyncMock()

        mock_processor = AsyncMock()
        mock_processor.fetch_emails.return_value = (
            [multipart_empty],
            ["uid-mp-empty"],
        )

        mock_gmail_svc = _make_gmail_service()

        with (
            patch(f"{MODULE}.async_session_maker", maker),
            patch(f"{MODULE}.engine", AsyncMock()),
            patch(f"{MODULE}.decrypt_credential", return_value="password123"),
            patch(f"{MODULE}.MailProcessor", return_value=mock_processor),
            patch(f"{MODULE}.GmailService", return_value=mock_gmail_svc),
            patch(f"{MODULE}.send_user_notification", new_callable=AsyncMock),
        ):
            from app.workers.tasks import process_mail_account

            await process_mail_account.run(1)

        # Empty email should be skipped — inject_email NOT called
        mock_gmail_svc.inject_email.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_non_multipart_empty_email_detected(self):
        """A non-multipart email with only whitespace body is detected as empty."""

        # Non-multipart, no subject, no from, whitespace body
        non_multipart_empty = b"Content-Type: text/plain\r\n" b"\r\n" b"   \r\n"
        account = _make_account(delivery_method=DeliveryMethod.GMAIL_API)

        maker, session = _mock_session_maker()

        gmail_cred = _make_gmail_cred(user_id=account.user_id)

        account_result = MagicMock()
        account_result.scalar_one_or_none.return_value = account

        seen_result = MagicMock()
        seen_result.scalars.return_value.all.return_value = []

        gmail_cred_result = MagicMock()
        gmail_cred_result.scalar_one_or_none.return_value = gmail_cred

        session.execute = AsyncMock(
            side_effect=[account_result, seen_result, gmail_cred_result]
        )
        session.commit = AsyncMock()
        session.refresh = AsyncMock()

        mock_processor = AsyncMock()
        mock_processor.fetch_emails.return_value = (
            [non_multipart_empty],
            ["uid-np-empty"],
        )

        mock_gmail_svc = _make_gmail_service()

        with (
            patch(f"{MODULE}.async_session_maker", maker),
            patch(f"{MODULE}.engine", AsyncMock()),
            patch(f"{MODULE}.decrypt_credential", return_value="password123"),
            patch(f"{MODULE}.MailProcessor", return_value=mock_processor),
            patch(f"{MODULE}.GmailService", return_value=mock_gmail_svc),
            patch(f"{MODULE}.send_user_notification", new_callable=AsyncMock),
        ):
            from app.workers.tasks import process_mail_account

            await process_mail_account.run(1)

        mock_gmail_svc.inject_email.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_revocation_notification_failure_swallowed(self):
        """Notification failure during credential revocation is swallowed."""

        raw_email = _build_raw_email()
        account = _make_account(delivery_method=DeliveryMethod.GMAIL_API)

        maker, session = _mock_session_maker()

        gmail_cred = _make_gmail_cred(user_id=account.user_id)

        account_result = MagicMock()
        account_result.scalar_one_or_none.return_value = account

        seen_result = MagicMock()
        seen_result.scalars.return_value.all.return_value = []

        gmail_cred_result = MagicMock()
        gmail_cred_result.scalar_one_or_none.return_value = gmail_cred

        session.execute = AsyncMock(
            side_effect=[account_result, seen_result, gmail_cred_result]
        )
        session.commit = AsyncMock()
        session.refresh = AsyncMock()

        mock_processor = AsyncMock()
        mock_processor.fetch_emails.return_value = ([raw_email], ["uid-1"])

        mock_gmail_svc = _make_gmail_service()
        mock_gmail_svc.build_import_label_ids = AsyncMock(return_value=["INBOX"])
        mock_gmail_svc.inject_email = AsyncMock(
            side_effect=Exception("401 Unauthorized")
        )

        # The notification service raises inside the credential-revocation block
        mock_send = AsyncMock(side_effect=Exception("Notification channel down"))

        with (
            patch(f"{MODULE}.async_session_maker", maker),
            patch(f"{MODULE}.engine", AsyncMock()),
            patch(f"{MODULE}.decrypt_credential", return_value="password123"),
            patch(f"{MODULE}.MailProcessor", return_value=mock_processor),
            patch(f"{MODULE}.GmailService", return_value=mock_gmail_svc),
            patch(f"{MODULE}.send_user_notification", mock_send),
        ):
            from app.workers.tasks import process_mail_account

            # Should not raise
            await process_mail_account.run(1)

        assert gmail_cred.is_valid is False

    @pytest.mark.asyncio
    async def test_outer_error_commit_failure(self):
        """When error handler's commit fails, it's caught and logged."""

        account = _make_account(delivery_method=DeliveryMethod.GMAIL_API)

        maker, session = _mock_session_maker()

        account_result = MagicMock()
        account_result.scalar_one_or_none.return_value = account

        # 1st execute returns account, then 2nd call for ProcessingRun commit,
        # we make the password decrypt blow up to trigger the outer handler.
        session.execute = AsyncMock(side_effect=[account_result])
        session.refresh = AsyncMock()
        session.rollback = AsyncMock()
        # Commit always fails
        session.commit = AsyncMock(side_effect=RuntimeError("DB crashed"))

        with (
            patch(f"{MODULE}.async_session_maker", maker),
            patch(f"{MODULE}.engine", AsyncMock()),
            patch(
                f"{MODULE}.decrypt_credential",
                side_effect=RuntimeError("decrypt failed"),
            ),
            patch(f"{MODULE}.send_user_notification", new_callable=AsyncMock),
        ):
            from app.workers.tasks import process_mail_account

            # Should not raise
            await process_mail_account.run(1)

    @pytest.mark.asyncio
    async def test_outer_error_notification_failure(self):
        """When notification fails during outer error handler, it's swallowed."""

        account = _make_account(delivery_method=DeliveryMethod.GMAIL_API)

        maker, session = _mock_session_maker()

        account_result = MagicMock()
        account_result.scalar_one_or_none.return_value = account

        session.execute = AsyncMock(side_effect=[account_result])
        session.commit = AsyncMock()
        session.refresh = AsyncMock()
        session.rollback = AsyncMock()

        mock_send = AsyncMock(side_effect=Exception("Notification service exploded"))

        with (
            patch(f"{MODULE}.async_session_maker", maker),
            patch(f"{MODULE}.engine", AsyncMock()),
            patch(
                f"{MODULE}.decrypt_credential",
                side_effect=RuntimeError("decrypt failed"),
            ),
            patch(f"{MODULE}.send_user_notification", mock_send),
        ):
            from app.workers.tasks import process_mail_account

            # Should not raise
            await process_mail_account.run(1)

    @pytest.mark.asyncio
    async def test_rollback_failure_swallowed(self):
        """When rollback itself fails during error handling, it's caught."""

        account = _make_account(delivery_method=DeliveryMethod.GMAIL_API)

        maker, session = _mock_session_maker()

        account_result = MagicMock()
        account_result.scalar_one_or_none.return_value = account

        session.execute = AsyncMock(side_effect=[account_result])
        session.commit = AsyncMock()
        session.refresh = AsyncMock()
        # Rollback itself raises
        session.rollback = AsyncMock(
            side_effect=RuntimeError("Rollback connection lost")
        )

        with (
            patch(f"{MODULE}.async_session_maker", maker),
            patch(f"{MODULE}.engine", AsyncMock()),
            patch(
                f"{MODULE}.decrypt_credential",
                side_effect=RuntimeError("decrypt failed"),
            ),
            patch(f"{MODULE}.send_user_notification", new_callable=AsyncMock),
        ):
            from app.workers.tasks import process_mail_account

            # Should not raise despite rollback failure
            await process_mail_account.run(1)

    @pytest.mark.asyncio
    async def test_email_header_parse_raises_exception(self):
        """ValueError/TypeError during header parsing is caught gracefully."""

        raw_email = _build_raw_email()
        account = _make_account(delivery_method=DeliveryMethod.GMAIL_API)

        maker, session = _mock_session_maker()

        gmail_cred = _make_gmail_cred(user_id=account.user_id)

        account_result = MagicMock()
        account_result.scalar_one_or_none.return_value = account

        seen_result = MagicMock()
        seen_result.scalars.return_value.all.return_value = []

        gmail_cred_result = MagicMock()
        gmail_cred_result.scalar_one_or_none.return_value = gmail_cred

        session.execute = AsyncMock(
            side_effect=[account_result, seen_result, gmail_cred_result]
        )
        session.commit = AsyncMock()
        session.refresh = AsyncMock()

        mock_processor = AsyncMock()
        mock_processor.fetch_emails.return_value = ([raw_email], ["uid-1"])

        mock_gmail_svc = _make_gmail_service()

        with (
            patch(f"{MODULE}.async_session_maker", maker),
            patch(f"{MODULE}.engine", AsyncMock()),
            patch(f"{MODULE}.decrypt_credential", return_value="password123"),
            patch(f"{MODULE}.MailProcessor", return_value=mock_processor),
            patch(f"{MODULE}.GmailService", return_value=mock_gmail_svc),
            patch(f"{MODULE}.send_user_notification", new_callable=AsyncMock),
            patch(
                f"{MODULE}.email_lib.message_from_bytes",
                side_effect=ValueError("Bad encoding"),
            ),
        ):
            from app.workers.tasks import process_mail_account

            await process_mail_account.run(1)


class TestProcessAllEnabledAccounts:
    """Tests for the process_all_enabled_accounts() async task body."""

    @pytest.mark.asyncio
    async def test_no_enabled_accounts(self):
        """No tasks are queued when there are no enabled accounts."""
        maker, session = _mock_session_maker()

        # First query: stale runs
        stale_result = MagicMock()
        stale_result.scalars.return_value.all.return_value = []

        # Second query: enabled accounts
        accounts_result = MagicMock()
        accounts_result.scalars.return_value.all.return_value = []

        session.execute = AsyncMock(side_effect=[stale_result, accounts_result])
        session.commit = AsyncMock()

        with (
            patch(f"{MODULE}.async_session_maker", maker),
            patch(f"{MODULE}.engine", AsyncMock()),
            patch(f"{MODULE}.process_mail_account") as mock_task,
        ):
            from app.workers.tasks import process_all_enabled_accounts

            await process_all_enabled_accounts.run()

        mock_task.delay.assert_not_called()

    @pytest.mark.asyncio
    async def test_accounts_queued(self):
        """Enabled accounts without recent checks are queued."""
        maker, session = _mock_session_maker()

        account1 = _make_account(id=1, last_check_at=None, check_interval_minutes=5)
        account2 = _make_account(
            id=2,
            last_check_at=datetime.now(timezone.utc) - timedelta(minutes=10),
            check_interval_minutes=5,
        )

        stale_result = MagicMock()
        stale_result.scalars.return_value.all.return_value = []

        accounts_result = MagicMock()
        accounts_result.scalars.return_value.all.return_value = [
            account1,
            account2,
        ]

        session.execute = AsyncMock(side_effect=[stale_result, accounts_result])
        session.commit = AsyncMock()

        with (
            patch(f"{MODULE}.async_session_maker", maker),
            patch(f"{MODULE}.engine", AsyncMock()),
            patch(f"{MODULE}.process_mail_account") as mock_task,
        ):
            from app.workers.tasks import process_all_enabled_accounts

            await process_all_enabled_accounts.run()

        assert mock_task.delay.call_count == 2

    @pytest.mark.asyncio
    async def test_account_skipped_if_checked_recently(self):
        """Accounts checked recently (within interval) are skipped."""
        maker, session = _mock_session_maker()

        # Checked 1 minute ago but interval is 5 minutes
        account = _make_account(
            id=1,
            last_check_at=datetime.now(timezone.utc) - timedelta(minutes=1),
            check_interval_minutes=5,
        )

        stale_result = MagicMock()
        stale_result.scalars.return_value.all.return_value = []

        accounts_result = MagicMock()
        accounts_result.scalars.return_value.all.return_value = [account]

        session.execute = AsyncMock(side_effect=[stale_result, accounts_result])
        session.commit = AsyncMock()

        with (
            patch(f"{MODULE}.async_session_maker", maker),
            patch(f"{MODULE}.engine", AsyncMock()),
            patch(f"{MODULE}.process_mail_account") as mock_task,
        ):
            from app.workers.tasks import process_all_enabled_accounts

            await process_all_enabled_accounts.run()

        mock_task.delay.assert_not_called()

    @pytest.mark.asyncio
    async def test_stale_runs_marked_failed(self):
        """Stale 'running' runs are marked as failed."""
        maker, session = _mock_session_maker()

        stale_run = MagicMock()
        stale_run.started_at = datetime.now(timezone.utc) - timedelta(minutes=60)

        stale_result = MagicMock()
        stale_result.scalars.return_value.all.return_value = [stale_run]

        accounts_result = MagicMock()
        accounts_result.scalars.return_value.all.return_value = []

        session.execute = AsyncMock(side_effect=[stale_result, accounts_result])
        session.commit = AsyncMock()

        with (
            patch(f"{MODULE}.async_session_maker", maker),
            patch(f"{MODULE}.engine", AsyncMock()),
            patch(f"{MODULE}.process_mail_account"),
        ):
            from app.workers.tasks import process_all_enabled_accounts

            await process_all_enabled_accounts.run()

        assert stale_run.status == "failed"
        assert "timed out" in stale_run.error_message
        session.commit.assert_awaited()

    @pytest.mark.asyncio
    async def test_exception_does_not_propagate(self):
        """An exception is logged but doesn't crash the task."""
        maker, session = _mock_session_maker()

        session.execute = AsyncMock(side_effect=RuntimeError("DB connection lost"))

        with (
            patch(f"{MODULE}.async_session_maker", maker),
            patch(f"{MODULE}.engine", AsyncMock()),
        ):
            from app.workers.tasks import process_all_enabled_accounts

            # Should not raise
            await process_all_enabled_accounts.run()


# ---------------------------------------------------------------------------
# cleanup_old_logs tests
# ---------------------------------------------------------------------------


class TestCleanupOldLogs:
    """Tests for the cleanup_old_logs() async task body."""

    @pytest.mark.asyncio
    async def test_deletes_old_runs_and_logs(self):
        """Old processing runs and logs are deleted."""
        maker, session = _mock_session_maker()

        stale_result = MagicMock()
        stale_result.scalars.return_value.all.return_value = []

        old_run = MagicMock()
        old_runs_result = MagicMock()
        old_runs_result.scalars.return_value.all.return_value = [old_run]

        old_log = MagicMock()
        old_logs_result = MagicMock()
        old_logs_result.scalars.return_value.all.return_value = [old_log]

        # For the bulk delete of DownloadedMessageId
        delete_result = MagicMock()

        session.execute = AsyncMock(
            side_effect=[
                stale_result,
                old_runs_result,
                old_logs_result,
                delete_result,
            ]
        )
        session.commit = AsyncMock()
        session.delete = AsyncMock()

        with (
            patch(f"{MODULE}.async_session_maker", maker),
            patch(f"{MODULE}.engine", AsyncMock()),
        ):
            from app.workers.tasks import cleanup_old_logs

            await cleanup_old_logs.run(days_to_keep=30)

        # Both old run and old log should have been deleted
        assert session.delete.await_count == 2
        session.commit.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_stale_runs_marked_failed(self):
        """Stale 'running' runs are marked as failed during cleanup."""
        maker, session = _mock_session_maker()

        stale_run = MagicMock()
        stale_run.started_at = datetime.now(timezone.utc) - timedelta(minutes=60)

        stale_result = MagicMock()
        stale_result.scalars.return_value.all.return_value = [stale_run]

        old_runs_result = MagicMock()
        old_runs_result.scalars.return_value.all.return_value = []

        old_logs_result = MagicMock()
        old_logs_result.scalars.return_value.all.return_value = []

        delete_result = MagicMock()

        session.execute = AsyncMock(
            side_effect=[
                stale_result,
                old_runs_result,
                old_logs_result,
                delete_result,
            ]
        )
        session.commit = AsyncMock()
        session.delete = AsyncMock()

        with (
            patch(f"{MODULE}.async_session_maker", maker),
            patch(f"{MODULE}.engine", AsyncMock()),
        ):
            from app.workers.tasks import cleanup_old_logs

            await cleanup_old_logs.run(days_to_keep=30)

        assert stale_run.status == "failed"
        assert "timed out" in stale_run.error_message
        assert stale_run.completed_at is not None

    @pytest.mark.asyncio
    async def test_custom_days_to_keep(self):
        """The days_to_keep parameter is respected."""
        maker, session = _mock_session_maker()

        stale_result = MagicMock()
        stale_result.scalars.return_value.all.return_value = []

        old_runs_result = MagicMock()
        old_runs_result.scalars.return_value.all.return_value = []

        old_logs_result = MagicMock()
        old_logs_result.scalars.return_value.all.return_value = []

        delete_result = MagicMock()

        session.execute = AsyncMock(
            side_effect=[
                stale_result,
                old_runs_result,
                old_logs_result,
                delete_result,
            ]
        )
        session.commit = AsyncMock()
        session.delete = AsyncMock()

        with (
            patch(f"{MODULE}.async_session_maker", maker),
            patch(f"{MODULE}.engine", AsyncMock()),
        ):
            from app.workers.tasks import cleanup_old_logs

            await cleanup_old_logs.run(days_to_keep=7)

        session.commit.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_nothing_to_clean(self):
        """When there's nothing old, task completes without deleting."""
        maker, session = _mock_session_maker()

        stale_result = MagicMock()
        stale_result.scalars.return_value.all.return_value = []

        old_runs_result = MagicMock()
        old_runs_result.scalars.return_value.all.return_value = []

        old_logs_result = MagicMock()
        old_logs_result.scalars.return_value.all.return_value = []

        delete_result = MagicMock()

        session.execute = AsyncMock(
            side_effect=[
                stale_result,
                old_runs_result,
                old_logs_result,
                delete_result,
            ]
        )
        session.commit = AsyncMock()
        session.delete = AsyncMock()

        with (
            patch(f"{MODULE}.async_session_maker", maker),
            patch(f"{MODULE}.engine", AsyncMock()),
        ):
            from app.workers.tasks import cleanup_old_logs

            await cleanup_old_logs.run(days_to_keep=30)

        session.delete.assert_not_awaited()
        session.commit.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_exception_does_not_propagate(self):
        """An exception is logged but doesn't crash the cleanup task."""
        maker, session = _mock_session_maker()

        session.execute = AsyncMock(side_effect=RuntimeError("DB connection lost"))

        with (
            patch(f"{MODULE}.async_session_maker", maker),
            patch(f"{MODULE}.engine", AsyncMock()),
        ):
            from app.workers.tasks import cleanup_old_logs

            # Should not raise
            await cleanup_old_logs.run(days_to_keep=30)
