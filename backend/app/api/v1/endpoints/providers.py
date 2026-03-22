"""Provider presets and Gmail credential management endpoints"""
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

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
)
from app.services.gmail_service import GmailService

router = APIRouter()

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
    for preset in PROVIDER_PRESETS:
        if preset.id == provider_id:
            return preset
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"Provider '{provider_id}' not found",
    )


@router.post("/gmail-credential", response_model=GmailCredentialResponse, status_code=status.HTTP_201_CREATED)
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
        encrypt_credential(credential_in.refresh_token) if credential_in.refresh_token else None
    )

    if existing:
        # Update existing
        existing.gmail_email = credential_in.gmail_email
        existing.encrypted_access_token = encrypted_access
        existing.encrypted_refresh_token = encrypted_refresh
        existing.is_valid = True
        from datetime import datetime
        existing.last_verified_at = datetime.utcnow()
        await db.commit()
        await db.refresh(existing)
        return existing
    else:
        # Create new
        from datetime import datetime
        credential = GmailCredential(
            user_id=current_user.id,
            gmail_email=credential_in.gmail_email,
            encrypted_access_token=encrypted_access,
            encrypted_refresh_token=encrypted_refresh,
            is_valid=True,
            last_verified_at=datetime.utcnow(),
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
