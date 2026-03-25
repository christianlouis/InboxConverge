# ADR 009: Use Gmail API for Email Delivery

**Status:** Accepted  
**Date:** 2026-02-15  
**Deciders:** Development Team

## Context

The core function of the application is forwarding emails fetched from POP3/IMAP accounts into a user's Gmail inbox. There are two primary mechanisms for delivering an email into Gmail:

1. **SMTP**: Send the email as a new message via Gmail's SMTP server (smtp.gmail.com)
2. **Gmail API `messages.insert`**: Inject the raw RFC 2822 email directly into the inbox using the Gmail REST API

Both require user authentication, but they have significantly different characteristics in terms of header preservation, quota, and delivery behavior.

## Decision

We will support **both delivery methods**, with **Gmail API injection as the preferred (default) method** and **SMTP as the fallback**. Each mail account stores a `delivery_method` field (`gmail_api` or `smtp`) chosen at account creation. If `gmail_api` is selected but no valid `GmailCredential` exists, the worker falls back to SMTP automatically.

## Alternatives Considered

### 1. SMTP Only
- **Pros**: Simple, no OAuth2 setup required, works with any email provider
- **Cons**: Counts against sending quota (500/day free), adds forwarding headers (`Received`, `X-Forwarded-To`), may be flagged as spam, rewrites `From` header

### 2. Gmail API Only
- **Pros**: Perfect header preservation, no sending quota, lower spam risk
- **Cons**: Requires OAuth2 setup per user, more complex credential management, tied to Gmail

### 3. IMAP APPEND
- **Pros**: Direct inbox write via standard protocol
- **Cons**: Requires IMAP access to the destination Gmail account, separate credential management, less reliable than API

### 4. PubSub Push (Gmail Push Notifications)
- **Pros**: Real-time delivery notifications
- **Cons**: Unrelated to delivery mechanism, solves a different problem

## Rationale

The dual-method approach was chosen because:

1. **New users benefit from Gmail API**: Perfect header preservation means the email appears exactly as it was sent; no spam risk from forwarding
2. **Legacy users supported via SMTP**: Existing setups using App Passwords continue to work without migration
3. **User Choice**: Different users have different technical comfort levels with OAuth2 setup
4. **Quota Protection**: Gmail API `messages.insert` does not count against the 500/day sending quota
5. **Graceful Degradation**: Automatic fallback to SMTP prevents complete failures when Gmail credentials expire

## Implementation

### GmailService

```python
# backend/app/services/gmail_service.py
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials

class GmailService:
    def inject_email(self, raw_email: bytes, user_id: int) -> dict:
        """Inject a raw RFC 2822 email directly into Gmail inbox."""
        creds = self._get_credentials(user_id)
        service = build("gmail", "v1", credentials=creds)
        message = {"raw": base64.urlsafe_b64encode(raw_email).decode()}
        return service.users().messages().insert(
            userId="me",
            body=message,
        ).execute()
```

### Delivery Decision in Worker

```python
# backend/app/workers/tasks.py
async def _deliver_email(account: MailAccount, raw_email: bytes, db: AsyncSession):
    if account.delivery_method == "gmail_api":
        credential = await db.get(GmailCredential, account.user_id)
        if credential and not credential.is_expired():
            gmail_service = GmailService(credential)
            return gmail_service.inject_email(raw_email, account.user_id)
        # Fall through to SMTP if no valid credential
    await _deliver_via_smtp(account, raw_email)
```

### Per-Account Delivery Method

| Field | Type | Values | Default |
|-------|------|--------|---------|
| `delivery_method` | string | `gmail_api`, `smtp` | `gmail_api` |

### Gmail OAuth2 Credential Storage

Gmail credentials are stored in the `gmail_credentials` table:
- `access_token`: Short-lived OAuth2 access token
- `refresh_token`: Long-lived token for refreshing access
- `token_expiry`: Expiration timestamp
- Tokens are encrypted at rest using Fernet (see ADR-002)

## Comparison Table

| Feature | Gmail API (`gmail_api`) | SMTP Forwarding (`smtp`) |
|---------|------------------------|--------------------------|
| Header preservation | ✅ All original headers intact | ⚠️ Adds `Received`, may rewrite `From` |
| Gmail sending quota | ✅ Does not consume quota | ❌ Counts against 500/day |
| Authentication | OAuth2 tokens per user | App Password (shared per server) |
| Setup complexity | OAuth2 consent flow required | App Password only |
| Spam risk | ✅ Low (email appears native) | ⚠️ Higher (forwarded mail may be flagged) |
| Fallback behavior | Falls back to SMTP automatically | Primary legacy method |

## Consequences

### Positive
- Gmail API delivery produces the cleanest inbox experience for users
- No sending quota concerns for high-volume users
- SMTP fallback ensures continued operation when OAuth tokens expire
- Per-account delivery method supports heterogeneous user setups

### Negative
- OAuth2 setup adds friction for new Gmail API users
- Credential refresh logic must be implemented and maintained
- Gmail API credentials must be encrypted at rest (additional complexity)
- Two code paths to test and maintain

### Token Refresh Strategy

Gmail access tokens expire after 1 hour. The worker automatically refreshes tokens using the stored `refresh_token` before delivery:

```python
from google.auth.transport.requests import Request

if creds.expired and creds.refresh_token:
    creds.refresh(Request())
    # Persist refreshed tokens back to database
    await _update_gmail_credential(user_id, creds, db)
```

## Related Decisions

- See ADR-001 for Celery worker that executes delivery
- See ADR-002 for Fernet encryption of Gmail credentials
- See ADR-005 for retry strategy when delivery fails

## References

- [Gmail API: messages.insert](https://developers.google.com/gmail/api/reference/rest/v1/users.messages/insert)
- [Google OAuth2 for Web Apps](https://developers.google.com/identity/protocols/oauth2/web-server)
- [Gmail Sending Limits](https://support.google.com/mail/answer/22839)
- [RFC 2822: Internet Message Format](https://www.rfc-editor.org/rfc/rfc2822)
