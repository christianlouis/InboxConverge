"""
OAuth2 authentication service for Google and other providers.
"""

from typing import Dict, Any
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
            scope = "openid email profile"
            self.oauth.register(
                name="google",
                client_id=settings.GOOGLE_CLIENT_ID,
                client_secret=settings.GOOGLE_CLIENT_SECRET,
                server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
                client_kwargs={"scope": scope},
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
            logger.debug(
                "OAuth [Google sign-in]: exchanging authorization code for tokens "
                "(redirect_uri=%s)",
                redirect_uri,
            )
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
                    logger.error(
                        "OAuth [Google sign-in]: token exchange failed "
                        "(status=%s, body=%s)",
                        token_response.status_code,
                        token_response.text,
                    )
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Failed to exchange authorization code",
                    )

                token_data = token_response.json()
                access_token = token_data.get("access_token")

                if not access_token:
                    logger.error(
                        "OAuth [Google sign-in]: token exchange response contained "
                        "no access_token (keys_present=%s)",
                        list(token_data.keys()),
                    )
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="No access token received",
                    )

                logger.debug(
                    "OAuth [Google sign-in]: token exchange succeeded — "
                    "scopes=%s, has_refresh_token=%s, expires_in=%s",
                    token_data.get("scope", ""),
                    bool(token_data.get("refresh_token")),
                    token_data.get("expires_in"),
                )

                # Get user info
                logger.debug("OAuth [Google sign-in]: fetching Google user profile")
                user_info_response = await client.get(
                    "https://www.googleapis.com/oauth2/v2/userinfo",
                    headers={"Authorization": f"Bearer {access_token}"},
                )

                if user_info_response.status_code != 200:
                    logger.error(
                        "OAuth [Google sign-in]: user-info fetch failed "
                        "(status=%s, body=%s)",
                        user_info_response.status_code,
                        user_info_response.text,
                    )
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Failed to get user information",
                    )

                user_info = user_info_response.json()
                logger.debug(
                    "OAuth [Google sign-in]: user profile retrieved — "
                    "email=%s, verified=%s",
                    user_info.get("email"),
                    user_info.get("verified_email"),
                )

                return {
                    "email": user_info.get("email"),
                    "full_name": user_info.get("name"),
                    "google_id": user_info.get("id"),
                    "picture": user_info.get("picture"),
                    "verified_email": user_info.get("verified_email", False),
                    "access_token": access_token,
                    "refresh_token": token_data.get("refresh_token"),
                    "expires_in": token_data.get("expires_in"),
                    "scope": token_data.get("scope", ""),
                }

        except HTTPException:
            raise
        except Exception as e:
            logger.error("OAuth [Google sign-in]: unexpected error: %s", e)
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
        logger.debug("OAuth: issuing application JWT tokens for user_id=%s", user.id)
        access_token = create_access_token(data={"sub": str(user.id)})
        refresh_token = create_refresh_token(data={"sub": str(user.id)})

        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
        }


# Global OAuth service instance
oauth_service = OAuthService()
