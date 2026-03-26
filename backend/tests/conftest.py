"""
Test configuration and fixtures.
"""

import pytest
from typing import AsyncGenerator
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.pool import NullPool

from app.main import app
from app.core.database import Base, get_db
from app.core.config import settings
from app.models.database_models import User
from app.core.security import get_password_hash, create_access_token

# Test database URL (use different database for tests)
TEST_DATABASE_URL = settings.DATABASE_URL.replace(
    "/inbox_converge", "/inbox_converge_test"
)


# Note: event_loop fixture removed - pytest-asyncio provides this automatically
# when asyncio_mode = auto is set in pytest.ini


@pytest.fixture(scope="function")
async def db_engine():
    """Create test database engine"""
    engine = create_async_engine(
        TEST_DATABASE_URL,
        poolclass=NullPool,
        echo=False,
    )

    # Create tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)

    yield engine

    # Drop tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    await engine.dispose()


@pytest.fixture(scope="function")
async def db_session(db_engine) -> AsyncGenerator[AsyncSession, None]:
    """Create test database session"""
    async_session_maker = async_sessionmaker(
        db_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    async with async_session_maker() as session:
        yield session


@pytest.fixture(scope="function")
async def client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """Create test client with database session override"""

    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    async with AsyncClient(app=app, base_url="http://test") as client:
        yield client

    app.dependency_overrides.clear()


@pytest.fixture
async def test_user(db_session: AsyncSession) -> User:
    """Create a test user"""
    user = User(
        email="test@example.com",
        hashed_password=get_password_hash("testpassword123"),
        is_active=True,
        is_verified=True,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest.fixture
async def test_admin_user(db_session: AsyncSession) -> User:
    """Create a test admin user"""
    user = User(
        email="admin@example.com",
        hashed_password=get_password_hash("adminpassword123"),
        is_active=True,
        is_verified=True,
        is_admin=True,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest.fixture
def auth_headers(test_user: User) -> dict:
    """Generate authentication headers for test user"""
    access_token = create_access_token(data={"sub": test_user.email})
    return {"Authorization": f"Bearer {access_token}"}


@pytest.fixture
def admin_auth_headers(test_admin_user: User) -> dict:
    """Generate authentication headers for admin user"""
    access_token = create_access_token(data={"sub": test_admin_user.email})
    return {"Authorization": f"Bearer {access_token}"}


# Factory fixtures for creating test data


@pytest.fixture
def user_factory(db_session: AsyncSession):
    """Factory for creating test users"""

    async def _create_user(
        email: str = None,
        password: str = "testpassword123",
        is_active: bool = True,
        is_verified: bool = True,
        is_admin: bool = False,
    ) -> User:
        if email is None:
            import uuid

            email = f"test-{uuid.uuid4()}@example.com"

        user = User(
            email=email,
            hashed_password=get_password_hash(password),
            is_active=is_active,
            is_verified=is_verified,
            is_admin=is_admin,
        )
        db_session.add(user)
        await db_session.commit()
        await db_session.refresh(user)
        return user

    return _create_user


@pytest.fixture
def mail_account_factory(db_session: AsyncSession):
    """Factory for creating test mail accounts"""
    from app.models.database_models import MailAccount
    from app.core.security import encrypt_password

    async def _create_mail_account(
        user_id: int,
        host: str = "pop.example.com",
        port: int = 995,
        username: str = None,
        password: str = "mailpassword",
        protocol: str = "pop3",
        use_ssl: bool = True,
    ) -> MailAccount:
        if username is None:
            import uuid

            username = f"test-{uuid.uuid4()}@example.com"

        encrypted_password = encrypt_password(password, user_id)

        account = MailAccount(
            user_id=user_id,
            host=host,
            port=port,
            username=username,
            encrypted_password=encrypted_password,
            protocol=protocol,
            use_ssl=use_ssl,
            is_active=True,
        )
        db_session.add(account)
        await db_session.commit()
        await db_session.refresh(account)
        return account

    return _create_mail_account
