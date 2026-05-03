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
    GmailImportLabelsUpdate,
)
from app.services.gmail_service import GmailService, GmailInjectionError, GMAIL_SCOPES
from app.utils.gmail_labels import (
    MAX_IMPORT_LABELS,
    build_gmail_credential_scopes,
    extract_granted_scopes,
    normalize_import_label_templates,
)

router = APIRouter()
logger = logging.getLogger(__name__)


def _validated_import_label_templates(label_templates: List[str]) -> List[str]:
    normalized = normalize_import_label_templates(label_templates)
    if len(normalized) > MAX_IMPORT_LABELS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"You can configure up to {MAX_IMPORT_LABELS} Gmail import labels.",
        )
    return normalized


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
        id="protonmail",
        name="Proton Mail",
        icon="protonmail",
        domains=["proton.me", "protonmail.com", "protonmail.ch", "pm.me"],
        imap_ssl={"host": "127.0.0.1", "port": 1143},
        pop3_ssl={"host": "127.0.0.1", "port": 1144},
        notes="Requires Proton Mail Bridge running locally. Use your Bridge password (not your Proton account password). Default Bridge ports: IMAP 127.0.0.1:1143, POP3 127.0.0.1:1144.",
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
    logger.debug(
        "OAuth [Gmail credential]: verifying credentials for user_id=%s "
        "(gmail=%s, has_refresh_token=%s)",
        current_user.id,
        credential_in.gmail_email,
        bool(credential_in.refresh_token),
    )
    # Verify the credentials work
    gmail_service = GmailService(
        access_token=credential_in.access_token,
        refresh_token=credential_in.refresh_token,
        client_id=settings.GOOGLE_CLIENT_ID,
        client_secret=settings.GOOGLE_CLIENT_SECRET,
    )

    is_valid = await gmail_service.verify_access()
    if not is_valid:
        logger.warning(
            "OAuth [Gmail credential]: credential verification failed for user_id=%s "
            "(gmail=%s)",
            current_user.id,
            credential_in.gmail_email,
        )
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
        existing.scopes = build_gmail_credential_scopes(
            existing.granted_scopes,
            existing.import_label_templates,
        )  # type: ignore[assignment]
        existing.is_valid = True  # type: ignore[assignment]
        existing.last_verified_at = datetime.now(timezone.utc)  # type: ignore[assignment]
        await db.commit()
        await db.refresh(existing)
        logger.info(
            "OAuth [Gmail credential]: updated credential for user_id=%s (gmail=%s)",
            current_user.id,
            credential_in.gmail_email,
        )
        return existing
    else:
        # Create new
        credential = GmailCredential(
            user_id=current_user.id,
            gmail_email=credential_in.gmail_email,
            encrypted_access_token=encrypted_access,
            encrypted_refresh_token=encrypted_refresh,
            scopes=build_gmail_credential_scopes(granted_scopes=[]),
            is_valid=True,
            last_verified_at=datetime.now(timezone.utc),
        )
        db.add(credential)
        await db.commit()
        await db.refresh(credential)
        logger.info(
            "OAuth [Gmail credential]: created new credential for user_id=%s (gmail=%s)",
            current_user.id,
            credential_in.gmail_email,
        )
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

    logger.info(
        "OAuth [Gmail credential]: deleting credential for user_id=%s (gmail=%s)",
        current_user.id,
        credential.gmail_email,
    )
    await db.delete(credential)
    await db.commit()


@router.put("/gmail-credential/labels", response_model=GmailCredentialResponse)
async def update_gmail_import_labels(
    labels_in: GmailImportLabelsUpdate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Update the Gmail labels applied to imported messages."""
    result = await db.execute(
        select(GmailCredential).where(GmailCredential.user_id == current_user.id)
    )
    credential = result.scalar_one_or_none()

    if not credential:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No Gmail credentials found. Connect Gmail first.",
        )

    validated = _validated_import_label_templates(labels_in.import_label_templates)
    logger.info(
        "OAuth [Gmail credential]: updating import labels for user_id=%s "
        "(gmail=%s, labels=%s)",
        current_user.id,
        credential.gmail_email,
        validated,
    )
    credential.scopes = build_gmail_credential_scopes(  # type: ignore[assignment]
        extract_granted_scopes(credential.scopes),
        validated,
    )
    await db.commit()
    await db.refresh(credential)
    return credential


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

    logger.info(
        "OAuth [Gmail connect]: authorization URL requested for user_id=%s "
        "(redirect_uri=%s, scopes=%s)",
        current_user.id,
        redirect_uri,
        GMAIL_API_SCOPES,
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
    logger.info(
        "OAuth [Gmail debug-email]: debug injection requested by user_id=%s",
        current_user.id,
    )
    result = await db.execute(
        select(GmailCredential).where(
            GmailCredential.user_id == current_user.id,
            GmailCredential.is_valid == True,  # noqa: E712
        )
    )
    credential = result.scalar_one_or_none()

    if not credential:
        logger.warning(
            "OAuth [Gmail debug-email]: no valid credential found for user_id=%s",
            current_user.id,
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No valid Gmail credentials found. Connect Gmail first.",
        )

    logger.debug(
        "OAuth [Gmail debug-email]: using credential for user_id=%s (gmail=%s, "
        "token_expiry=%s, has_refresh_token=%s)",
        current_user.id,
        credential.gmail_email,
        credential.token_expiry,
        bool(credential.encrypted_refresh_token),
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
            import_label_templates=credential.import_label_templates,
        )
    except GmailInjectionError as exc:
        logger.error(
            "OAuth [Gmail debug-email]: injection failed for user_id=%s (gmail=%s): %s",
            current_user.id,
            credential.gmail_email,
            exc,
        )
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Gmail injection failed: {exc}",
        )

    # Persist refreshed token if the google-auth library renewed it
    refreshed = gmail_service.get_refreshed_token()
    if refreshed:
        logger.debug(
            "OAuth [Gmail debug-email]: access token was auto-refreshed for "
            "user_id=%s; persisting new expiry=%s",
            current_user.id,
            refreshed.get("expiry"),
        )
        credential.encrypted_access_token = encrypt_credential(  # type: ignore[assignment]
            refreshed["access_token"]
        )
        if refreshed.get("expiry"):
            credential.token_expiry = refreshed["expiry"]  # type: ignore[assignment]
        await db.commit()

    logger.info(
        "OAuth [Gmail debug-email]: injection succeeded for user_id=%s (gmail=%s, "
        "message_id=%s)",
        current_user.id,
        credential.gmail_email,
        inject_result.get("message_id"),
    )
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

    logger.info(
        "OAuth [Gmail connect]: callback received for user_id=%s (redirect_uri=%s)",
        current_user.id,
        callback_in.redirect_uri,
    )

    # Exchange code for tokens
    logger.debug(
        "OAuth [Gmail connect]: exchanging authorization code for tokens "
        "(user_id=%s)",
        current_user.id,
    )
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
        logger.error(
            "OAuth [Gmail connect]: token exchange failed for user_id=%s "
            "(status=%s, body=%s)",
            current_user.id,
            token_resp.status_code,
            token_resp.text,
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to exchange authorization code with Google.",
        )

    token_data = token_resp.json()
    access_token: Optional[str] = token_data.get("access_token")
    refresh_token: Optional[str] = token_data.get("refresh_token")

    logger.debug(
        "OAuth [Gmail connect]: token exchange succeeded for user_id=%s — "
        "scopes=%s, has_refresh_token=%s, expires_in=%s",
        current_user.id,
        token_data.get("scope", ""),
        bool(refresh_token),
        token_data.get("expires_in"),
    )

    if not access_token:
        logger.error(
            "OAuth [Gmail connect]: Google response contained no access_token "
            "for user_id=%s (keys_present=%s)",
            current_user.id,
            list(token_data.keys()),
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Google did not return an access token.",
        )

    if not refresh_token:
        logger.warning(
            "OAuth [Gmail connect]: Google did not return a refresh_token for "
            "user_id=%s — token refresh may fail after 1 hour. "
            "This can happen if the user has previously authorised the app and "
            "access_type=offline was not honoured.",
            current_user.id,
        )

    # Fetch the Gmail email address to associate with this credential
    logger.debug(
        "OAuth [Gmail connect]: fetching Google profile for user_id=%s",
        current_user.id,
    )
    async with httpx.AsyncClient() as client:
        profile_resp = await client.get(
            "https://www.googleapis.com/oauth2/v2/userinfo",
            headers={"Authorization": f"Bearer {access_token}"},
        )

    gmail_email = current_user.email  # fallback
    if profile_resp.status_code == 200:
        gmail_email = profile_resp.json().get("email", current_user.email)
        logger.debug(
            "OAuth [Gmail connect]: Google profile retrieved for user_id=%s "
            "(gmail=%s)",
            current_user.id,
            gmail_email,
        )
    else:
        logger.warning(
            "OAuth [Gmail connect]: could not fetch Google profile for user_id=%s "
            "(status=%s); falling back to account email=%s",
            current_user.id,
            profile_resp.status_code,
            current_user.email,
        )

    # Calculate token expiry (Google access tokens last 1 hour)
    token_expiry = datetime.now(timezone.utc) + timedelta(
        seconds=int(token_data.get("expires_in", 3600))
    )

    # Verify the credentials actually work with the Gmail API
    logger.debug(
        "OAuth [Gmail connect]: verifying Gmail API access for user_id=%s (gmail=%s)",
        current_user.id,
        gmail_email,
    )
    gmail_service = GmailService(
        access_token=access_token,
        refresh_token=refresh_token,
        client_id=settings.GOOGLE_CLIENT_ID,
        client_secret=settings.GOOGLE_CLIENT_SECRET,
    )
    is_valid = await gmail_service.verify_access()
    if not is_valid:
        logger.error(
            "OAuth [Gmail connect]: Gmail API access verification failed for "
            "user_id=%s (gmail=%s) — ensure gmail.insert scope was granted",
            current_user.id,
            gmail_email,
        )
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
        existing.scopes = build_gmail_credential_scopes(  # type: ignore[assignment]
            token_data.get("scope", "").split(),
            existing.import_label_templates,
        )
        existing.is_valid = True  # type: ignore[assignment]
        existing.last_verified_at = datetime.now(timezone.utc)  # type: ignore[assignment]
        await db.commit()
        await db.refresh(existing)
        logger.info(
            "OAuth [Gmail connect]: updated credential for user_id=%s "
            "(gmail=%s, token_expiry=%s, has_refresh_token=%s, scopes=%s)",
            current_user.id,
            gmail_email,
            token_expiry,
            bool(encrypted_refresh),
            token_data.get("scope", ""),
        )
        return existing
    else:
        credential = GmailCredential(
            user_id=current_user.id,
            gmail_email=gmail_email,
            encrypted_access_token=encrypted_access,
            encrypted_refresh_token=encrypted_refresh,
            token_expiry=token_expiry,
            scopes=build_gmail_credential_scopes(token_data.get("scope", "").split()),
            is_valid=True,
            last_verified_at=datetime.now(timezone.utc),
        )
        db.add(credential)
        await db.commit()
        await db.refresh(credential)
        logger.info(
            "OAuth [Gmail connect]: created new credential for user_id=%s "
            "(gmail=%s, token_expiry=%s, has_refresh_token=%s, scopes=%s)",
            current_user.id,
            gmail_email,
            token_expiry,
            bool(encrypted_refresh),
            token_data.get("scope", ""),
        )
        return credential
