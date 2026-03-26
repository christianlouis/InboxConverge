"""Provider presets and Gmail credential management endpoints"""

from datetime import datetime, timedelta, timezone
from typing import List, Optional
from urllib.parse import quote as urlquote
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import httpx
import logging

from app.core.database import get_db
from app.core.deps import get_current_active_user
from app.core.security import encrypt_credential, decrypt_credential
from app.core.config import settings
from app.models.database_models import User, GmailCredential
from app.models.schemas import (
    ProviderPreset,
    ProviderListResponse,
    GmailCredentialCreate,
    GmailCredentialResponse,
    GmailAuthorizeResponse,
    GmailCallbackRequest,
)
from app.services.gmail_service import GmailService, GmailInjectionError, GMAIL_SCOPES

router = APIRouter()
logger = logging.getLogger(__name__)

# Gmail API scopes requested during the "Connect Gmail" OAuth flow.
# GMAIL_SCOPES (gmail.insert, gmail.labels, gmail.readonly) are imported from
# gmail_service so the scope list stays in sync with what GmailService uses.
GMAIL_API_SCOPES = [
    "openid",
    "email",
    *GMAIL_SCOPES,
]

# Provider presets with server configurations
PROVIDER_PRESETS: List[ProviderPreset] = [
    ProviderPreset(
        id="gmail",
        name="Gmail",
        icon="gmail",
        domains=["gmail.com", "googlemail.com"],
        imap_ssl={"host": "imap.gmail.com", "port": 993},
        pop3_ssl={"host": "pop.gmail.com", "port": 995},
        notes="Enable IMAP/POP3 in Gmail settings. Use an App Password if 2FA is enabled.",
    ),
    ProviderPreset(
        id="gmx",
        name="GMX",
        icon="gmx",
        domains=["gmx.de", "gmx.net", "gmx.at", "gmx.ch", "gmx.com"],
        imap_ssl={"host": "imap.gmx.net", "port": 993},
        pop3_ssl={"host": "pop.gmx.net", "port": 995},
        notes="Enable POP3/IMAP in GMX settings under E-Mail > POP3/IMAP Abruf.",
    ),
    ProviderPreset(
        id="webde",
        name="WEB.DE",
        icon="webde",
        domains=["web.de"],
        imap_ssl={"host": "imap.web.de", "port": 993},
        pop3_ssl={"host": "pop3.web.de", "port": 995},
        notes="Enable POP3/IMAP in WEB.DE settings under E-Mail > POP3/IMAP Abruf.",
    ),
    ProviderPreset(
        id="outlook",
        name="Outlook / Hotmail",
        icon="outlook",
        domains=["outlook.com", "hotmail.com", "live.com", "msn.com", "outlook.de"],
        imap_ssl={"host": "outlook.office365.com", "port": 993},
        pop3_ssl={"host": "outlook.office365.com", "port": 995},
        notes="Use your Microsoft account credentials.",
    ),
    ProviderPreset(
        id="yahoo",
        name="Yahoo Mail",
        icon="yahoo",
        domains=["yahoo.com", "yahoo.de", "yahoo.co.uk", "ymail.com"],
        imap_ssl={"host": "imap.mail.yahoo.com", "port": 993},
        pop3_ssl={"host": "pop.mail.yahoo.com", "port": 995},
        notes="Generate an App Password in Yahoo account security settings.",
    ),
    ProviderPreset(
        id="aol",
        name="AOL Mail",
        icon="aol",
        domains=["aol.com", "aim.com"],
        imap_ssl={"host": "imap.aol.com", "port": 993},
        pop3_ssl={"host": "pop.aol.com", "port": 995},
        notes="Generate an App Password in AOL account security settings.",
    ),
    ProviderPreset(
        id="tonline",
        name="T-Online",
        icon="tonline",
        domains=["t-online.de"],
        imap_ssl={"host": "secureimap.t-online.de", "port": 993},
        pop3_ssl={"host": "securepop.t-online.de", "port": 995},
        notes="Use your T-Online E-Mail-Passwort (not your Telekom login password).",
    ),
    ProviderPreset(
        id="ionos",
        name="1&1 / IONOS",
        icon="ionos",
        domains=["online.de", "onlinehome.de", "1und1.de"],
        imap_ssl={"host": "imap.ionos.de", "port": 993},
        pop3_ssl={"host": "pop.ionos.de", "port": 995},
        notes="Use your IONOS email credentials.",
    ),
    ProviderPreset(
        id="freenet",
        name="Freenet",
        icon="freenet",
        domains=["freenet.de"],
        imap_ssl={"host": "mx.freenet.de", "port": 993},
        pop3_ssl={"host": "mx.freenet.de", "port": 995},
        notes="Use your Freenet email credentials.",
    ),
    ProviderPreset(
        id="posteo",
        name="Posteo",
        icon="posteo",
        domains=["posteo.de", "posteo.net"],
        imap_ssl={"host": "posteo.de", "port": 993},
        pop3_ssl=None,
        notes="Posteo supports IMAP only. Use your Posteo credentials.",
    ),
    ProviderPreset(
        id="mailde",
        name="mail.de",
        icon="mailde",
        domains=["mail.de"],
        imap_ssl={"host": "imap.mail.de", "port": 993},
        pop3_ssl={"host": "pop.mail.de", "port": 995},
        notes="Use your mail.de email credentials.",
    ),
    ProviderPreset(
        id="icloud",
        name="iCloud Mail",
        icon="icloud",
        domains=["icloud.com", "me.com", "mac.com"],
        imap_ssl={"host": "imap.mail.me.com", "port": 993},
        pop3_ssl=None,
        notes="Generate an app-specific password at appleid.apple.com.",
    ),
]

# Create a mapping for O(1) provider lookup
PROVIDER_PRESETS_MAP = {preset.id: preset for preset in PROVIDER_PRESETS}


@router.get("/presets", response_model=ProviderListResponse)
async def list_provider_presets(
    current_user: User = Depends(get_current_active_user),
):
    """List all available mail provider presets for quick setup wizard"""
    return ProviderListResponse(providers=PROVIDER_PRESETS)


@router.get("/presets/{provider_id}", response_model=ProviderPreset)
async def get_provider_preset(
    provider_id: str,
    current_user: User = Depends(get_current_active_user),
):
    """Get a specific provider preset by ID"""
    preset = PROVIDER_PRESETS_MAP.get(provider_id)
    if preset:
        return preset

    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"Provider '{provider_id}' not found",
    )


@router.post(
    "/gmail-credential",
    response_model=GmailCredentialResponse,
    status_code=status.HTTP_201_CREATED,
)
async def save_gmail_credential(
    credential_in: GmailCredentialCreate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Save Gmail API OAuth2 credentials for the current user.
    These are used to inject emails directly into Gmail via the API.
    """
    # Verify the credentials work
    gmail_service = GmailService(
        access_token=credential_in.access_token,
        refresh_token=credential_in.refresh_token,
        client_id=settings.GOOGLE_CLIENT_ID,
        client_secret=settings.GOOGLE_CLIENT_SECRET,
    )

    is_valid = await gmail_service.verify_access()
    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Gmail API credentials are invalid or expired",
        )

    # Check for existing credential
    result = await db.execute(
        select(GmailCredential).where(GmailCredential.user_id == current_user.id)
    )
    existing = result.scalar_one_or_none()

    encrypted_access = encrypt_credential(credential_in.access_token)
    encrypted_refresh = (
        encrypt_credential(credential_in.refresh_token)
        if credential_in.refresh_token
        else None
    )

    if existing:
        # Update existing
        existing.gmail_email = credential_in.gmail_email  # type: ignore[assignment]
        existing.encrypted_access_token = encrypted_access  # type: ignore[assignment]
        existing.encrypted_refresh_token = encrypted_refresh  # type: ignore[assignment]
        existing.is_valid = True  # type: ignore[assignment]
        existing.last_verified_at = datetime.now(timezone.utc)  # type: ignore[assignment]
        await db.commit()
        await db.refresh(existing)
        return existing
    else:
        # Create new
        credential = GmailCredential(
            user_id=current_user.id,
            gmail_email=credential_in.gmail_email,
            encrypted_access_token=encrypted_access,
            encrypted_refresh_token=encrypted_refresh,
            is_valid=True,
            last_verified_at=datetime.now(timezone.utc),
        )
        db.add(credential)
        await db.commit()
        await db.refresh(credential)
        return credential


@router.get("/gmail-credential", response_model=GmailCredentialResponse)
async def get_gmail_credential(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Get the current user's Gmail API credential status"""
    result = await db.execute(
        select(GmailCredential).where(GmailCredential.user_id == current_user.id)
    )
    credential = result.scalar_one_or_none()

    if not credential:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No Gmail credentials configured. Set up Gmail API access first.",
        )

    return credential


@router.delete("/gmail-credential", status_code=status.HTTP_204_NO_CONTENT)
async def delete_gmail_credential(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete the current user's Gmail API credentials"""
    result = await db.execute(
        select(GmailCredential).where(GmailCredential.user_id == current_user.id)
    )
    credential = result.scalar_one_or_none()

    if not credential:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No Gmail credentials found",
        )

    await db.delete(credential)
    await db.commit()


@router.get("/gmail/authorize-url", response_model=GmailAuthorizeResponse)
async def get_gmail_authorize_url(
    redirect_uri: str,
    current_user: User = Depends(get_current_active_user),
):
    """
    Return a Google OAuth2 URL that grants this app Gmail API write permissions.

    The URL requests the gmail.insert + gmail.labels scopes with
    access_type=offline so a long-lived refresh token is issued.
    prompt=consent forces Google to always issue a new refresh token even if
    the user has authorised the app before.
    """
    if not settings.GOOGLE_CLIENT_ID:
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="Google OAuth2 is not configured on this server.",
        )

    scope = urlquote(" ".join(GMAIL_API_SCOPES))
    url = (
        "https://accounts.google.com/o/oauth2/v2/auth"
        f"?client_id={settings.GOOGLE_CLIENT_ID}"
        "&response_type=code"
        f"&scope={scope}"
        f"&redirect_uri={redirect_uri}"
        "&access_type=offline"
        "&prompt=consent"
        "&include_granted_scopes=true"
        "&state=gmail_connect"
    )
    return GmailAuthorizeResponse(authorization_url=url)


@router.post("/gmail/debug-email", status_code=status.HTTP_200_OK)
async def send_gmail_debug_email(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Inject a debug/test email into the current user's Gmail inbox.

    The message appears to have been sent by christian@docuelevate.org,
    carries today's date in the subject, and is tagged with the custom
    labels "test" and "imported" as well as placed in the inbox.

    Useful for verifying that Gmail API delivery is working end-to-end
    without requiring an active mail-account polling cycle.
    """
    result = await db.execute(
        select(GmailCredential).where(
            GmailCredential.user_id == current_user.id,
            GmailCredential.is_valid == True,  # noqa: E712
        )
    )
    credential = result.scalar_one_or_none()

    if not credential:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No valid Gmail credentials found. Connect Gmail first.",
        )

    access_token = decrypt_credential(credential.encrypted_access_token)  # type: ignore[arg-type]
    refresh_token = (
        decrypt_credential(credential.encrypted_refresh_token)  # type: ignore[arg-type]
        if credential.encrypted_refresh_token
        else None
    )

    gmail_service = GmailService(
        access_token=access_token,
        refresh_token=refresh_token,
        client_id=settings.GOOGLE_CLIENT_ID,
        client_secret=settings.GOOGLE_CLIENT_SECRET,
    )

    try:
        inject_result = await gmail_service.inject_debug_email(
            recipient_email=credential.gmail_email,  # type: ignore[arg-type]
        )
    except GmailInjectionError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Gmail injection failed: {exc}",
        )

    # Persist refreshed token if the google-auth library renewed it
    refreshed = gmail_service.get_refreshed_token()
    if refreshed:
        credential.encrypted_access_token = encrypt_credential(  # type: ignore[assignment]
            refreshed["access_token"]
        )
        if refreshed.get("expiry"):
            credential.token_expiry = refreshed["expiry"]  # type: ignore[assignment]
        await db.commit()

    return {
        "message": "Debug email injected successfully",
        "message_id": inject_result.get("message_id"),
        "thread_id": inject_result.get("thread_id"),
        "label_ids": inject_result.get("label_ids", []),
    }


@router.post(
    "/gmail/callback",
    response_model=GmailCredentialResponse,
    status_code=status.HTTP_201_CREATED,
)
async def gmail_oauth_callback(
    callback_in: GmailCallbackRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Exchange a Google authorization code for Gmail API tokens and persist them.

    This is the backend half of the "Connect Gmail" one-click flow.  The
    frontend redirects the user to Google, Google sends a code back to the
    frontend callback page, and the frontend posts that code here.

    Token lifetime
    --------------
    * Access token  : 1 hour.  The google-auth library auto-refreshes it
      during Celery tasks; the new value is written back to this row so the
      next run doesn't need an extra refresh round-trip.
    * Refresh token : does not expire unless the user revokes access or the
      app credentials change.  If revoked, ``is_valid`` is set to False by
      the next Celery run that hits a 401, and the user must re-authorise.
    """
    if not settings.GOOGLE_CLIENT_ID or not settings.GOOGLE_CLIENT_SECRET:
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="Google OAuth2 is not configured on this server.",
        )

    # Exchange code for tokens
    async with httpx.AsyncClient() as client:
        token_resp = await client.post(
            "https://oauth2.googleapis.com/token",
            data={
                "code": callback_in.code,
                "client_id": settings.GOOGLE_CLIENT_ID,
                "client_secret": settings.GOOGLE_CLIENT_SECRET,
                "redirect_uri": callback_in.redirect_uri,
                "grant_type": "authorization_code",
            },
        )

    if token_resp.status_code != 200:
        logger.error(f"Gmail token exchange failed: {token_resp.text}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to exchange authorization code with Google.",
        )

    token_data = token_resp.json()
    access_token: Optional[str] = token_data.get("access_token")
    refresh_token: Optional[str] = token_data.get("refresh_token")

    if not access_token:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Google did not return an access token.",
        )

    # Fetch the Gmail email address to associate with this credential
    async with httpx.AsyncClient() as client:
        profile_resp = await client.get(
            "https://www.googleapis.com/oauth2/v2/userinfo",
            headers={"Authorization": f"Bearer {access_token}"},
        )

    gmail_email = current_user.email  # fallback
    if profile_resp.status_code == 200:
        gmail_email = profile_resp.json().get("email", current_user.email)

    # Calculate token expiry (Google access tokens last 1 hour)
    token_expiry = datetime.now(timezone.utc) + timedelta(
        seconds=int(token_data.get("expires_in", 3600))
    )

    # Verify the credentials actually work with the Gmail API
    gmail_service = GmailService(
        access_token=access_token,
        refresh_token=refresh_token,
        client_id=settings.GOOGLE_CLIENT_ID,
        client_secret=settings.GOOGLE_CLIENT_SECRET,
    )
    is_valid = await gmail_service.verify_access()
    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Obtained tokens but could not verify Gmail API access. "
            "Ensure the gmail.insert scope was granted.",
        )

    # Persist tokens
    result = await db.execute(
        select(GmailCredential).where(GmailCredential.user_id == current_user.id)
    )
    existing = result.scalar_one_or_none()

    encrypted_access = encrypt_credential(access_token)
    encrypted_refresh = encrypt_credential(refresh_token) if refresh_token else None

    if existing:
        existing.gmail_email = gmail_email  # type: ignore[assignment]
        existing.encrypted_access_token = encrypted_access  # type: ignore[assignment]
        if encrypted_refresh:
            existing.encrypted_refresh_token = encrypted_refresh  # type: ignore[assignment]
        existing.token_expiry = token_expiry  # type: ignore[assignment]
        existing.scopes = token_data.get("scope", "").split()  # type: ignore[assignment]
        existing.is_valid = True  # type: ignore[assignment]
        existing.last_verified_at = datetime.now(timezone.utc)  # type: ignore[assignment]
        await db.commit()
        await db.refresh(existing)
        return existing
    else:
        credential = GmailCredential(
            user_id=current_user.id,
            gmail_email=gmail_email,
            encrypted_access_token=encrypted_access,
            encrypted_refresh_token=encrypted_refresh,
            token_expiry=token_expiry,
            scopes=token_data.get("scope", "").split(),
            is_valid=True,
            last_verified_at=datetime.now(timezone.utc),
        )
        db.add(credential)
        await db.commit()
        await db.refresh(credential)
        return credential
