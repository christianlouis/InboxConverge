"""
Authentication endpoints (login, register, OAuth).
"""
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime
import logging

from app.core.database import get_db
from app.core.security import verify_password, get_password_hash
from app.models.database_models import User, SubscriptionTier
from app.models.schemas import (
    Token, UserCreate, UserResponse, GoogleAuthRequest
)
from app.services.auth_service import oauth_service

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(
    user_in: UserCreate,
    db: AsyncSession = Depends(get_db)
):
    """Register a new user with email and password"""
    
    # Check if user exists
    result = await db.execute(
        select(User).where(User.email == user_in.email)
    )
    existing_user = result.scalar_one_or_none()
    
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    # Create new user
    user = User(
        email=user_in.email,
        full_name=user_in.full_name,
        hashed_password=get_password_hash(user_in.password) if user_in.password else None,
        subscription_tier=SubscriptionTier.FREE,
        is_active=True
    )
    
    db.add(user)
    await db.commit()
    await db.refresh(user)
    
    logger.info(f"New user registered: {user.email}")
    
    return user


@router.post("/login", response_model=Token)
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db)
):
    """Login with email and password"""
    
    # Get user
    result = await db.execute(
        select(User).where(User.email == form_data.username)
    )
    user = result.scalar_one_or_none()
    
    if not user or not user.hashed_password:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Verify password
    if not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Check if user is active
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is inactive"
        )
    
    # Update last login
    user.last_login_at = datetime.utcnow()
    await db.commit()
    
    # Create tokens
    tokens = oauth_service.create_tokens_for_user(user)
    
    logger.info(f"User logged in: {user.email}")
    
    return tokens


@router.post("/google", response_model=Token)
async def google_oauth(
    auth_request: GoogleAuthRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Authenticate with Google OAuth2.
    Exchange authorization code for access token and user info.
    """
    
    # Get user info from Google
    user_info = await oauth_service.get_google_user_info(
        code=auth_request.code,
        redirect_uri=auth_request.redirect_uri
    )
    
    if not user_info.get('verified_email'):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email not verified with Google"
        )
    
    email = user_info['email']
    google_id = user_info['google_id']
    
    # Check if user exists
    result = await db.execute(
        select(User).where(
            (User.email == email) | (User.google_id == google_id)
        )
    )
    user = result.scalar_one_or_none()
    
    if user:
        # Update Google ID if not set
        if not user.google_id:
            user.google_id = google_id
            user.oauth_provider = "google"
        
        # Update last login
        user.last_login_at = datetime.utcnow()
        
        logger.info(f"Existing user logged in with Google: {user.email}")
    else:
        # Create new user
        user = User(
            email=email,
            full_name=user_info.get('full_name'),
            google_id=google_id,
            oauth_provider="google",
            subscription_tier=SubscriptionTier.FREE,
            is_active=True,
            last_login_at=datetime.utcnow()
        )
        db.add(user)
        
        logger.info(f"New user registered with Google: {user.email}")
    
    await db.commit()
    await db.refresh(user)
    
    # Create tokens
    tokens = oauth_service.create_tokens_for_user(user)
    
    return tokens


@router.get("/google/authorize-url")
async def get_google_authorize_url(redirect_uri: str):
    """Get Google OAuth2 authorization URL"""
    from app.core.config import settings
    
    auth_url = (
        f"https://accounts.google.com/o/oauth2/v2/auth?"
        f"client_id={settings.GOOGLE_CLIENT_ID}&"
        f"response_type=code&"
        f"scope=openid%20email%20profile&"
        f"redirect_uri={redirect_uri}&"
        f"access_type=offline"
    )
    
    return {"authorization_url": auth_url}
