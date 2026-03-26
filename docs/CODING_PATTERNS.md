# Coding Patterns and Best Practices

This document outlines the coding patterns, conventions, and best practices for the InboxConverge project.

## Table of Contents
- [General Principles](#general-principles)
- [Python Style](#python-style)
- [API Development](#api-development)
- [Database Patterns](#database-patterns)
- [Error Handling](#error-handling)
- [Security Patterns](#security-patterns)
- [Testing Patterns](#testing-patterns)
- [Async/Await Patterns](#asyncawait-patterns)

---

## General Principles

### 1. Explicit is Better Than Implicit
```python
# Good ✅
async def get_user_by_id(db: AsyncSession, user_id: int) -> Optional[User]:
    result = await db.execute(select(User).where(User.id == user_id))
    return result.scalar_one_or_none()

# Bad ❌
async def get_user(db, id):  # Missing type hints
    return await db.execute(select(User).where(User.id == id)).scalar()  # Chained calls
```

### 2. Dependency Injection
Use FastAPI's dependency injection for shared resources:
```python
# Good ✅
async def create_mail_account(
    account_in: MailAccountCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> MailAccount:
    # Function implementation
    pass

# Bad ❌
# Accessing global db connection or parsing tokens manually
```

---

## Python Style

### Type Hints (Required)
```python
# Good ✅
from typing import Optional, List
from datetime import datetime

def process_emails(
    account_id: int,
    max_count: int = 50,
    since: Optional[datetime] = None
) -> List[Email]:
    pass

# Bad ❌
def process_emails(account_id, max_count=50, since=None):  # No type hints
    pass
```

### Docstrings (Required for Public APIs)
```python
# Good ✅
async def fetch_emails_from_pop3(account: MailAccount) -> List[Email]:
    """
    Fetch emails from a POP3 account.
    
    Args:
        account: The mail account to fetch from
        
    Returns:
        List of Email objects retrieved from the server
        
    Raises:
        ConnectionError: If POP3 connection fails
        AuthenticationError: If credentials are invalid
    """
    pass
```

### Constants
```python
# Good ✅ - In backend/app/core/constants.py
MAX_EMAILS_PER_RUN = 50
DEFAULT_CHECK_INTERVAL_MINUTES = 5
PBKDF2_ITERATIONS = 100_000

# Bad ❌ - Magic numbers in code
if len(emails) > 50:
    pass
```

---

## API Development

### Endpoint Structure
```python
# Good ✅
from fastapi import APIRouter, Depends, HTTPException, status
from app.models.schemas import MailAccountCreate, MailAccountResponse
from app.core.deps import get_current_user, get_db

router = APIRouter(prefix="/mail-accounts", tags=["Mail Accounts"])

@router.post(
    "/",
    response_model=MailAccountResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new mail account"
)
async def create_mail_account(
    account_in: MailAccountCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> MailAccount:
    """Create a new POP3/IMAP mail account for the current user."""
    # Validate subscription limits
    # Create account with encrypted credentials
    # Return response
    pass
```

### Error Responses
```python
# Good ✅
from app.core.errors import ErrorCode, ErrorResponse

if not can_add_account:
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail=ErrorResponse(
            code=ErrorCode.SUBSCRIPTION_LIMIT_REACHED,
            message="Your plan allows maximum 5 mail accounts",
            details={"current": 5, "limit": 5, "upgrade_url": "/pricing"}
        ).dict()
    )

# Bad ❌
if not can_add_account:
    raise HTTPException(status_code=403, detail="Limit reached")  # Not helpful
```

### Validation
```python
# Good ✅ - Use Pydantic validators
from pydantic import BaseModel, validator

class MailAccountCreate(BaseModel):
    host: str
    port: int
    username: str
    password: str
    
    @validator('port')
    def validate_port(cls, v):
        if not 1 <= v <= 65535:
            raise ValueError('Port must be between 1 and 65535')
        return v
    
    @validator('host')
    def validate_host(cls, v):
        if not v or v.strip() == "":
            raise ValueError('Host cannot be empty')
        return v.strip()
```

---

## Database Patterns

### Queries
```python
# Good ✅ - Use SQLAlchemy select statements
from sqlalchemy import select

async def get_user_mail_accounts(db: AsyncSession, user_id: int) -> List[MailAccount]:
    result = await db.execute(
        select(MailAccount)
        .where(MailAccount.user_id == user_id)
        .order_by(MailAccount.created_at.desc())
    )
    return result.scalars().all()

# Bad ❌ - Raw SQL or no await
def get_accounts(db, user_id):
    return db.query(MailAccount).filter_by(user_id=user_id).all()  # Sync, old style
```

### Transactions
```python
# Good ✅ - Explicit transaction management
async def create_user_with_account(
    db: AsyncSession,
    user_data: UserCreate,
    account_data: MailAccountCreate
) -> User:
    try:
        user = User(**user_data.dict())
        db.add(user)
        await db.flush()  # Get user.id
        
        account = MailAccount(**account_data.dict(), user_id=user.id)
        db.add(account)
        
        await db.commit()
        await db.refresh(user)
        return user
    except Exception as e:
        await db.rollback()
        raise

# Bad ❌ - No explicit error handling
async def create_user_with_account(db, user_data, account_data):
    user = User(**user_data.dict())
    db.add(user)
    await db.commit()  # What if this fails?
```

### Relationships
```python
# Good ✅ - Use eager loading when needed
from sqlalchemy.orm import selectinload

async def get_user_with_accounts(db: AsyncSession, user_id: int) -> Optional[User]:
    result = await db.execute(
        select(User)
        .options(selectinload(User.mail_accounts))
        .where(User.id == user_id)
    )
    return result.scalar_one_or_none()

# Bad ❌ - N+1 queries
user = await get_user(db, user_id)
for account in user.mail_accounts:  # Lazy loads each account
    print(account.email)
```

---

## Error Handling

### Specific Exceptions
```python
# Good ✅ - Catch specific exceptions
from smtplib import SMTPAuthenticationError, SMTPException
from poplib import error_proto

try:
    await send_email(message)
except SMTPAuthenticationError as e:
    logger.error(f"SMTP authentication failed: {e}")
    raise HTTPException(status_code=401, detail="Invalid email credentials")
except SMTPException as e:
    logger.error(f"SMTP error: {e}")
    raise HTTPException(status_code=500, detail="Email delivery failed")

# Bad ❌ - Bare except
try:
    await send_email(message)
except Exception as e:  # Too broad
    logger.error(f"Error: {e}")
```

### Logging
```python
# Good ✅ - Structured logging with context
logger.info(
    "Email forwarded successfully",
    extra={
        "user_id": user.id,
        "account_id": account.id,
        "email_size": len(email_data),
        "destination": destination_email
    }
)

# Bad ❌ - String formatting in logs
logger.info(f"Email forwarded for user {user.id}")  # No structure
```

### Resource Cleanup
```python
# Good ✅ - Use context managers
async with aiosmtplib.SMTP(hostname=smtp_host, port=smtp_port) as smtp:
    await smtp.login(username, password)
    await smtp.send_message(message)
# Connection automatically closed

# Bad ❌ - Manual cleanup
smtp = aiosmtplib.SMTP(hostname=smtp_host, port=smtp_port)
try:
    await smtp.connect()
    await smtp.send_message(message)
finally:
    smtp.close()  # Might be forgotten
```

---

## Security Patterns

### Credential Encryption
```python
# Good ✅ - Always encrypt credentials before storage
from app.core.security import encrypt_password

async def create_mail_account(
    db: AsyncSession,
    account_data: MailAccountCreate,
    user_id: int
) -> MailAccount:
    encrypted_password = encrypt_password(account_data.password, user_id)
    account = MailAccount(
        **account_data.dict(exclude={'password'}),
        encrypted_password=encrypted_password,
        user_id=user_id
    )
    db.add(account)
    await db.commit()
    return account

# Bad ❌ - Plain text storage
account = MailAccount(password=account_data.password)  # NEVER DO THIS
```

### Input Validation
```python
# Good ✅ - Validate all external inputs
from urllib.parse import urlparse

@validator('redirect_uri')
def validate_redirect_uri(cls, v):
    allowed_domains = ['localhost', 'app.yourdomain.com']
    parsed = urlparse(v)
    if parsed.netloc not in allowed_domains:
        raise ValueError('Invalid redirect URI')
    return v

# Bad ❌ - Trust user input
redirect_uri = request.args.get('redirect_uri')
return redirect(redirect_uri)  # Open redirect vulnerability
```

### Never Log Secrets
```python
# Good ✅
logger.info(f"Connecting to POP3 server {host} as {username}")

# Bad ❌
logger.debug(f"Connecting with password: {password}")  # NEVER LOG PASSWORDS
```

---

## Testing Patterns

### Test Structure
```python
# Good ✅ - Arrange, Act, Assert
import pytest
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_create_mail_account(
    client: AsyncClient,
    auth_headers: dict,
    db_session: AsyncSession
):
    # Arrange
    account_data = {
        "host": "pop.example.com",
        "port": 995,
        "username": "test@example.com",
        "password": "secure_password"
    }
    
    # Act
    response = await client.post(
        "/api/v1/mail-accounts/",
        json=account_data,
        headers=auth_headers
    )
    
    # Assert
    assert response.status_code == 201
    data = response.json()
    assert data["username"] == account_data["username"]
    assert "password" not in data  # Never return passwords
```

### Fixtures
```python
# Good ✅ - In conftest.py
import pytest
from sqlalchemy.ext.asyncio import AsyncSession

@pytest.fixture
async def test_user(db_session: AsyncSession) -> User:
    """Create a test user."""
    user = User(
        email="test@example.com",
        hashed_password=get_password_hash("testpass")
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user
```

### Mocking
```python
# Good ✅ - Mock external services
from unittest.mock import AsyncMock, patch

@pytest.mark.asyncio
async def test_send_email_success():
    with patch('aiosmtplib.SMTP') as mock_smtp:
        mock_instance = AsyncMock()
        mock_smtp.return_value.__aenter__.return_value = mock_instance
        
        await send_email("test@example.com", "Subject", "Body")
        
        mock_instance.send_message.assert_called_once()
```

---

## Async/Await Patterns

### Always Await Async Functions
```python
# Good ✅
result = await db.execute(query)
await db.commit()

# Bad ❌
result = db.execute(query)  # Returns coroutine, not result!
```

### Use AsyncSession
```python
# Good ✅ - Backend uses AsyncSession
from sqlalchemy.ext.asyncio import AsyncSession

async def get_user(db: AsyncSession, user_id: int) -> Optional[User]:
    result = await db.execute(select(User).where(User.id == user_id))
    return result.scalar_one_or_none()

# Bad ❌ - Mixing sync code with async
from sqlalchemy.orm import Session  # Wrong import

def get_user(db: Session, user_id: int):  # Sync function
    return db.query(User).filter_by(id=user_id).first()
```

### Don't Block the Event Loop
```python
# Good ✅ - Use async libraries
import aiofiles

async def read_large_file(filepath: str) -> str:
    async with aiofiles.open(filepath, 'r') as f:
        return await f.read()

# Bad ❌ - Blocking I/O in async function
async def read_large_file(filepath: str) -> str:
    with open(filepath, 'r') as f:  # Blocks event loop!
        return f.read()
```

---

## Celery Task Patterns

### Task Definition
```python
# Good ✅ - With retry and error handling
from celery import Task
from app.core.celery_app import celery_app

@celery_app.task(
    bind=True,
    autoretry_for=(Exception,),
    retry_kwargs={'max_retries': 3, 'countdown': 60},
    retry_backoff=True
)
def process_mail_account(self: Task, account_id: int) -> dict:
    """Process emails for a mail account."""
    try:
        # Task logic
        return {"status": "success", "count": 10}
    except Exception as exc:
        logger.error(f"Task failed for account {account_id}: {exc}")
        raise self.retry(exc=exc)

# Bad ❌ - No retry logic
@celery_app.task
def process_mail_account(account_id):
    # If this fails, it just fails
    pass
```

---

## Configuration Management

### Use Pydantic Settings
```python
# Good ✅ - In app/core/config.py
from pydantic import BaseSettings, validator

class Settings(BaseSettings):
    SECRET_KEY: str
    DATABASE_URL: str
    
    @validator('SECRET_KEY')
    def validate_secret_key(cls, v):
        if v == "change-this-to-a-secure-random-secret-key-in-production":
            raise ValueError("SECRET_KEY must be changed from default!")
        if len(v) < 32:
            raise ValueError("SECRET_KEY must be at least 32 characters")
        return v
    
    class Config:
        env_file = ".env"

# Bad ❌ - Direct os.getenv without validation
SECRET_KEY = os.getenv('SECRET_KEY', 'default_key')  # Dangerous default
```

---

## Documentation Patterns

### API Endpoint Documentation
```python
# Good ✅
@router.post(
    "/",
    response_model=MailAccountResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new mail account",
    description="Creates a new POP3/IMAP mail account for the authenticated user. "
                "Credentials are encrypted before storage.",
    responses={
        201: {"description": "Mail account created successfully"},
        403: {"description": "Subscription limit reached"},
        422: {"description": "Invalid input data"}
    }
)
async def create_mail_account(...):
    pass
```

---

## Summary Checklist

Before committing code, ensure:
- [ ] Type hints on all functions
- [ ] Docstrings on public APIs
- [ ] Specific exception handling (no bare `except`)
- [ ] Input validation with Pydantic
- [ ] Credentials encrypted, never logged
- [ ] Async/await used correctly
- [ ] Tests added/updated
- [ ] Error codes documented
- [ ] Security considerations checked
- [ ] Code follows these patterns

---

**Last Updated**: 2026-02-06
**Maintainer**: Development Team
