"""
Unit tests for the database-backed configuration service.
"""

import os
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.services.config_service import (
    ConfigService,
    BOOTSTRAP_KEYS,
    DEFAULT_SETTINGS,
    _cast_value,
)

# ── _cast_value tests ─────────────────────────────────────────────


class TestCastValue:
    """Test low-level value casting."""

    def test_cast_string(self):
        assert _cast_value("hello", "string") == "hello"

    def test_cast_int(self):
        assert _cast_value("42", "int") == 42

    def test_cast_float(self):
        assert _cast_value("3.14", "float") == 3.14

    def test_cast_bool_true(self):
        for val in ("true", "True", "1", "yes"):
            assert _cast_value(val, "bool") is True

    def test_cast_bool_false(self):
        for val in ("false", "False", "0", "no"):
            assert _cast_value(val, "bool") is False

    def test_cast_json(self):
        assert _cast_value('["INBOX"]', "json") == ["INBOX"]
        assert _cast_value('{"a": 1}', "json") == {"a": 1}

    def test_cast_none(self):
        assert _cast_value(None, "string") is None
        assert _cast_value(None, "int") is None


# ── ConfigService.get tests ────────────────────────────────────────


class TestConfigServiceGet:
    """Test ConfigService.get() resolution order."""

    @pytest.mark.asyncio
    async def test_returns_default_when_no_source(self):
        """When neither DB nor env has the key, return the default."""
        with patch.dict(os.environ, {}, clear=False):
            # Make sure the key is not in env
            os.environ.pop("MY_TEST_KEY_XYZ", None)
            result = await ConfigService.get("MY_TEST_KEY_XYZ", default="fallback")
        assert result == "fallback"

    @pytest.mark.asyncio
    async def test_env_overrides_default(self):
        """Env var should override the default."""
        with patch.dict(os.environ, {"MY_TEST_KEY_XYZ": "from_env"}):
            result = await ConfigService.get("MY_TEST_KEY_XYZ", default="fallback")
        assert result == "from_env"

    @pytest.mark.asyncio
    async def test_db_overrides_env(self):
        """Database value should take precedence over env var."""
        mock_setting = MagicMock()
        mock_setting.value = "from_db"
        mock_setting.value_type = "string"

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_setting

        mock_db = AsyncMock()
        mock_db.execute.return_value = mock_result

        with patch.dict(os.environ, {"SMTP_HOST": "from_env"}):
            result = await ConfigService.get("SMTP_HOST", db=mock_db, default="default")

        assert result == "from_db"

    @pytest.mark.asyncio
    async def test_bootstrap_key_skips_db(self):
        """Bootstrap keys must never read from the database."""
        mock_db = AsyncMock()

        with patch.dict(os.environ, {"SECRET_KEY": "env_secret_value"}):
            result = await ConfigService.get("SECRET_KEY", db=mock_db)

        # DB should not have been called
        mock_db.execute.assert_not_called()
        assert result == "env_secret_value"

    @pytest.mark.asyncio
    async def test_db_exception_falls_back_to_env(self):
        """If DB lookup fails, fall back to env var gracefully."""
        mock_db = AsyncMock()
        mock_db.execute.side_effect = Exception("DB down")

        with patch.dict(os.environ, {"SMTP_HOST": "env_value"}):
            result = await ConfigService.get("SMTP_HOST", db=mock_db)

        assert result == "env_value"


# ── ConfigService.get_many tests ───────────────────────────────────


class TestConfigServiceGetMany:
    """Test ConfigService.get_many() bulk retrieval."""

    @pytest.mark.asyncio
    async def test_get_many_from_env(self):
        """When no DB, all values come from env."""
        with patch.dict(
            os.environ, {"SMTP_HOST": "host", "SMTP_PORT": "587"}, clear=False
        ):
            result = await ConfigService.get_many(["SMTP_HOST", "SMTP_PORT"])
        assert result["SMTP_HOST"] == "host"
        assert result["SMTP_PORT"] == "587"

    @pytest.mark.asyncio
    async def test_get_many_with_db(self):
        """DB values should be included in results."""
        mock_setting = MagicMock()
        mock_setting.key = "SMTP_HOST"
        mock_setting.value = "db_host"
        mock_setting.value_type = "string"

        mock_scalars = MagicMock()
        mock_scalars.all.return_value = [mock_setting]

        mock_result = MagicMock()
        mock_result.scalars.return_value = mock_scalars

        mock_db = AsyncMock()
        mock_db.execute.return_value = mock_result

        with patch.dict(os.environ, {"SMTP_PORT": "465"}, clear=False):
            os.environ.pop("SMTP_HOST", None)
            result = await ConfigService.get_many(
                ["SMTP_HOST", "SMTP_PORT"], db=mock_db
            )

        assert result["SMTP_HOST"] == "db_host"
        assert result["SMTP_PORT"] == "465"


# ── ConfigService.set tests ────────────────────────────────────────


class TestConfigServiceSet:
    """Test ConfigService.set() create and update."""

    @pytest.mark.asyncio
    async def test_set_rejects_bootstrap_key(self):
        """Setting a bootstrap key must raise ValueError."""
        mock_db = AsyncMock()
        with pytest.raises(ValueError, match="bootstrap setting"):
            await ConfigService.set("SECRET_KEY", "value", db=mock_db)

    @pytest.mark.asyncio
    async def test_set_creates_new_setting(self):
        """set() should create a new record when key does not exist."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None

        mock_db = AsyncMock()
        mock_db.execute.return_value = mock_result

        # The method will call db.add() and db.commit()
        await ConfigService.set(
            "SMTP_HOST", "new.host.com", db=mock_db, category="smtp"
        )

        mock_db.add.assert_called_once()
        mock_db.commit.assert_called()

    @pytest.mark.asyncio
    async def test_set_updates_existing_setting(self):
        """set() should update an existing record."""
        existing = MagicMock()
        existing.value = "old_value"

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = existing

        mock_db = AsyncMock()
        mock_db.execute.return_value = mock_result

        await ConfigService.set("SMTP_HOST", "updated.host.com", db=mock_db)

        assert existing.value == "updated.host.com"
        mock_db.commit.assert_called()


# ── ConfigService.delete tests ─────────────────────────────────────


class TestConfigServiceDelete:
    """Test ConfigService.delete()."""

    @pytest.mark.asyncio
    async def test_delete_rejects_bootstrap_key(self):
        mock_db = AsyncMock()
        with pytest.raises(ValueError, match="bootstrap setting"):
            await ConfigService.delete("DATABASE_URL", db=mock_db)

    @pytest.mark.asyncio
    async def test_delete_returns_false_when_missing(self):
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None

        mock_db = AsyncMock()
        mock_db.execute.return_value = mock_result

        assert await ConfigService.delete("NONEXISTENT", db=mock_db) is False

    @pytest.mark.asyncio
    async def test_delete_removes_existing(self):
        existing = MagicMock()

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = existing

        mock_db = AsyncMock()
        mock_db.execute.return_value = mock_result

        assert await ConfigService.delete("SMTP_HOST", db=mock_db) is True
        mock_db.delete.assert_called_once_with(existing)


# ── ConfigService.get_smtp_config tests ────────────────────────────


class TestConfigServiceSmtpConfig:
    """Test the SMTP convenience helper."""

    @pytest.mark.asyncio
    async def test_smtp_config_defaults(self):
        """When nothing is configured, sensible defaults are returned."""
        with patch.dict(os.environ, {}, clear=False):
            for key in (
                "SMTP_HOST",
                "SMTP_PORT",
                "SMTP_USER",
                "SMTP_PASSWORD",
                "SMTP_USE_TLS",
            ):
                os.environ.pop(key, None)
            config = await ConfigService.get_smtp_config()

        assert config["host"] == "smtp.gmail.com"
        assert config["port"] == 587
        assert config["username"] == ""
        assert config["password"] == ""
        assert config["use_tls"] is True

    @pytest.mark.asyncio
    async def test_smtp_config_from_env(self):
        """Env vars should populate the SMTP config."""
        env = {
            "SMTP_HOST": "mail.example.com",
            "SMTP_PORT": "465",
            "SMTP_USER": "user",
            "SMTP_PASSWORD": "pass",
            "SMTP_USE_TLS": "false",
        }
        with patch.dict(os.environ, env, clear=False):
            config = await ConfigService.get_smtp_config()

        assert config["host"] == "mail.example.com"
        assert config["port"] == 465
        assert config["username"] == "user"
        assert config["password"] == "pass"
        assert config["use_tls"] is False


# ── DEFAULT_SETTINGS sanity check ──────────────────────────────────


class TestDefaultSettings:
    """Verify the built-in defaults are well-formed."""

    def test_all_defaults_have_required_fields(self):
        for item in DEFAULT_SETTINGS:
            assert "key" in item
            assert "value" in item
            assert "value_type" in item

    def test_no_default_is_a_bootstrap_key(self):
        for item in DEFAULT_SETTINGS:
            assert item["key"] not in BOOTSTRAP_KEYS
