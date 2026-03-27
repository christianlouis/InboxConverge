"""
Authentication endpoints (login, register, OAuth).
"""

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime, timezone
from urllib.parse import quote as urlquote
import logging

from app.core.config import settings
from app.core.database import get_db
from app.core.security import verify_password, get_password_hash
from app.core.metrics import (
    AUTH_LOGINS_TOTAL,
    AUTH_REGISTRATIONS_TOTAL,
    OAUTH_CALLBACKS_TOTAL,
)
from app.models.database_models import User, SubscriptionTier
from app.models.schemas import Token, UserCreate, UserResponse, GoogleAuthRequest
from app.services.auth_service import oauth_service

router = APIRouter()
logger = logging.getLogger(__name__)

# Scopes requested during Google Sign-In – only basic profile information.
# Gmail API access is granted separately via the "Connect Gmail" flow in
# Settings (/providers/gmail/authorize-url).
GOOGLE_LOGIN_SCOPES = [
    "openid",
    "email",
    "profile",
]


def _domain_of(email: str) -> str:
    """Return the lowercased domain part of an email address."""
    return email.split("@")[-1].lower()


def _check_domain_allowed(email: str) -> None:
    """
    Raise 403 if ALLOWED_DOMAINS is configured and the email's domain is not
    in the list.  Always passes when ALLOWED_DOMAINS is empty (no restriction).
    """
    if not settings.ALLOWED_DOMAINS:
        return
    domain = _domain_of(email)
    if domain not in settings.ALLOWED_DOMAINS:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=(
                f"Registrations are restricted to approved domains. "
                f"'{domain}' is not authorised."
            ),
        )


def _default_tier() -> SubscriptionTier:
    """Return the SubscriptionTier that should be assigned to every new user."""
    try:
        return SubscriptionTier(settings.DEFAULT_USER_TIER)
    except ValueError:
        logger.warning(
            "DEFAULT_USER_TIER '%s' is not a valid tier; falling back to FREE.",
            settings.DEFAULT_USER_TIER,
        )
        return SubscriptionTier.FREE


def _is_admin_email(email: str) -> bool:
    return (
        settings.ADMIN_EMAIL is not None
        and email.lower() == settings.ADMIN_EMAIL.lower()
    )


@router.post(
    "/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED
)
async def register(user_in: UserCreate, db: AsyncSession = Depends(get_db)):
    """Register a new user with email and password"""

    # Check if user exists
    result = await db.execute(select(User).where(User.email == user_in.email))
    existing_user = result.scalar_one_or_none()

    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered"
        )

    # Domain restriction check (before creating the account)
    _check_domain_allowed(user_in.email)

    # Create new user
    user = User(
        email=user_in.email,
        full_name=user_in.full_name,
        hashed_password=(
            get_password_hash(user_in.password) if user_in.password else None
        ),
        subscription_tier=_default_tier(),
        is_active=True,
        is_superuser=_is_admin_email(user_in.email),
    )

    db.add(user)
    await db.commit()
    await db.refresh(user)

    AUTH_REGISTRATIONS_TOTAL.labels(method="password", status="success").inc()
    logger.info(f"New user registered: {user.email}")

    return user


@router.post("/login", response_model=Token)
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(), db: AsyncSession = Depends(get_db)
):
    """Login with email and password"""

    # Get user
    result = await db.execute(select(User).where(User.email == form_data.username))
    user = result.scalar_one_or_none()

    if not user or not user.hashed_password:
        AUTH_LOGINS_TOTAL.labels(method="password", status="failure").inc()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Verify password
    if not verify_password(form_data.password, user.hashed_password):  # type: ignore[arg-type]
        AUTH_LOGINS_TOTAL.labels(method="password", status="failure").inc()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Check if user is active
    if not user.is_active:
        AUTH_LOGINS_TOTAL.labels(method="password", status="failure").inc()
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="User account is inactive"
        )

    # Domain restriction — superusers always bypass
    if not user.is_superuser:
        _check_domain_allowed(user.email)

    # Update last login
    user.last_login_at = datetime.now(timezone.utc)  # type: ignore[assignment]

    # Auto-promote to superuser if this is the configured admin email
    if not user.is_superuser and _is_admin_email(user.email):
        user.is_superuser = True  # type: ignore[assignment]
        logger.info(f"Auto-promoted admin user: {user.email}")

    await db.commit()

    # Create tokens
    tokens = oauth_service.create_tokens_for_user(user)

    AUTH_LOGINS_TOTAL.labels(method="password", status="success").inc()
    logger.info(f"User logged in: {user.email}")

    return tokens


@router.post("/google", response_model=Token)
async def google_oauth(
    auth_request: GoogleAuthRequest, db: AsyncSession = Depends(get_db)
):
    """
    Authenticate with Google OAuth2.
    Exchange authorization code for access token and user info.
    """

    # Get user info from Google
    user_info = await oauth_service.get_google_user_info(
        code=auth_request.code, redirect_uri=auth_request.redirect_uri
    )

    if not user_info.get("verified_email"):
        OAUTH_CALLBACKS_TOTAL.labels(provider="google", status="error").inc()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email not verified with Google",
        )

    email = user_info["email"]
    google_id = user_info["google_id"]

    # Check if user exists
    result = await db.execute(
        select(User).where((User.email == email) | (User.google_id == google_id))
    )
    user = result.scalar_one_or_none()

    if user:
        # Update Google ID if not set
        if not user.google_id:
            user.google_id = google_id  # type: ignore[assignment]
            user.oauth_provider = "google"  # type: ignore[assignment]

        # Update last login
        user.last_login_at = datetime.now(timezone.utc)  # type: ignore[assignment]

        # Domain restriction — superusers always bypass
        if not user.is_superuser:
            _check_domain_allowed(email)

        # Auto-promote to superuser if this is the configured admin email
        if not user.is_superuser and _is_admin_email(email):
            user.is_superuser = True  # type: ignore[assignment]
            logger.info(f"Auto-promoted admin user via Google OAuth: {user.email}")

        logger.info(f"Existing user logged in with Google: {user.email}")
        AUTH_LOGINS_TOTAL.labels(method="google", status="success").inc()
    else:
        # Domain restriction check before creating the account
        _check_domain_allowed(email)

        # Create new user
        user = User(
            email=email,
            full_name=user_info.get("full_name"),
            google_id=google_id,
            oauth_provider="google",
            subscription_tier=_default_tier(),
            is_active=True,
            last_login_at=datetime.now(timezone.utc),
            is_superuser=_is_admin_email(email),
        )
        db.add(user)

        logger.info(f"New user registered with Google: {user.email}")
        AUTH_REGISTRATIONS_TOTAL.labels(method="google", status="success").inc()

    await db.commit()
    await db.refresh(user)

    # Create tokens
    tokens = oauth_service.create_tokens_for_user(user)

    OAUTH_CALLBACKS_TOTAL.labels(provider="google", status="success").inc()
    return tokens


@router.get("/google/authorize-url")
async def get_google_authorize_url(redirect_uri: str):
    """Get Google OAuth2 authorization URL for sign-in (profile scopes only)."""
    scope = urlquote(" ".join(GOOGLE_LOGIN_SCOPES))
    auth_url = (
        "https://accounts.google.com/o/oauth2/v2/auth"
        f"?client_id={settings.GOOGLE_CLIENT_ID}"
        "&response_type=code"
        f"&scope={scope}"
        f"&redirect_uri={redirect_uri}"
        "&prompt=select_account"
    )

    return {"authorization_url": auth_url}
