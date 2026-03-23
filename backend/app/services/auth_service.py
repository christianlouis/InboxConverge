"""
OAuth2 authentication service for Google and other providers.
"""

from typing import Dict, Any, Optional
from datetime import datetime
import httpx
from authlib.integrations.starlette_client import OAuth
from fastapi import HTTPException, status
import logging

from app.core.config import settings
from app.core.security import create_access_token, create_refresh_token
from app.models.database_models import User

logger = logging.getLogger(__name__)


class OAuthService:
    """OAuth2 authentication service"""

    def __init__(self):
        self.oauth = OAuth()
        self._register_google()

    def _register_google(self):
        """Register Google OAuth2 provider"""
        if settings.GOOGLE_CLIENT_ID and settings.GOOGLE_CLIENT_SECRET:
            self.oauth.register(
                name="google",
                client_id=settings.GOOGLE_CLIENT_ID,
                client_secret=settings.GOOGLE_CLIENT_SECRET,
                server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
                client_kwargs={"scope": "openid email profile"},
            )

    async def get_google_user_info(
        self, code: str, redirect_uri: str
    ) -> Dict[str, Any]:
        """
        Exchange Google authorization code for user information.

        Args:
            code: Authorization code from Google
            redirect_uri: Redirect URI used in OAuth flow

        Returns:
            Dict with user information (email, name, google_id)
        """
        try:
            # Exchange code for token
            async with httpx.AsyncClient() as client:
                token_response = await client.post(
                    "https://oauth2.googleapis.com/token",
                    data={
                        "code": code,
                        "client_id": settings.GOOGLE_CLIENT_ID,
                        "client_secret": settings.GOOGLE_CLIENT_SECRET,
                        "redirect_uri": redirect_uri,
                        "grant_type": "authorization_code",
                    },
                )

                if token_response.status_code != 200:
                    logger.error(f"Google token exchange failed: {token_response.text}")
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Failed to exchange authorization code",
                    )

                token_data = token_response.json()
                access_token = token_data.get("access_token")

                if not access_token:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="No access token received",
                    )

                # Get user info
                user_info_response = await client.get(
                    "https://www.googleapis.com/oauth2/v2/userinfo",
                    headers={"Authorization": f"Bearer {access_token}"},
                )

                if user_info_response.status_code != 200:
                    logger.error(
                        f"Google user info fetch failed: {user_info_response.text}"
                    )
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Failed to get user information",
                    )

                user_info = user_info_response.json()

                return {
                    "email": user_info.get("email"),
                    "full_name": user_info.get("name"),
                    "google_id": user_info.get("id"),
                    "picture": user_info.get("picture"),
                    "verified_email": user_info.get("verified_email", False),
                }

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"OAuth error: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="OAuth authentication failed",
            )

    @staticmethod
    def create_tokens_for_user(user: User) -> Dict[str, str]:
        """
        Create access and refresh tokens for a user.

        Args:
            user: User database model

        Returns:
            Dict with access_token, refresh_token, and token_type
        """
        access_token = create_access_token(data={"sub": user.id})
        refresh_token = create_refresh_token(data={"sub": user.id})

        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
        }


# Global OAuth service instance
oauth_service = OAuthService()
