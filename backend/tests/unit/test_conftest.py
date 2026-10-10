import pytest
from sqlalchemy.engine import make_url

from conftest import _test_database_url


def test_test_database_url_preserves_explicit_test_database():
    url = "postgresql+asyncpg://test_user:test_password@localhost/inbox_converge_test"

    assert _test_database_url(url) == url


def test_test_database_url_maps_base_database_and_preserves_query():
    url = "postgresql+asyncpg://test_user:test_password@localhost/inbox_converge?sslmode=require"

    result = make_url(_test_database_url(url))

    assert result.database == "inbox_converge_test"
    assert result.username == "test_user"
    assert result.password == "test_password"
    assert result.query == {"sslmode": "require"}


def test_test_database_url_preserves_explicit_test_query():
    url = "postgresql+asyncpg://test_user:test_password@localhost/inbox_converge_test?sslmode=require"

    result = make_url(_test_database_url(url))

    assert result.database == "inbox_converge_test"
    assert result.password == "test_password"
    assert result.query == {"sslmode": "require"}


def test_test_database_url_rejects_arbitrary_database():
    url = "postgresql+asyncpg://test_user:test_password@localhost/customer_data"

    with pytest.raises(ValueError, match="inbox_converge"):
        _test_database_url(url)
