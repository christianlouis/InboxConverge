# ADR 007: Use JWT for API Authentication

**Status:** Accepted  
**Date:** 2026-02-08  
**Deciders:** Security Team, Development Team

## Context

The multi-tenant SaaS API needs a stateless authentication mechanism that:

1. Works with both browser-based frontends and programmatic API clients
2. Supports short-lived access tokens to limit exposure on compromise
3. Allows session refresh without re-entering credentials
4. Integrates with Google OAuth2 (users who sign in via Google)
5. Requires no server-side session store

## Decision

We will use **JWT (JSON Web Tokens)** with **HMAC-SHA256 (HS256)** signing for both access tokens and refresh tokens, implemented via the `python-jose` library.

- **Access tokens**: 30-minute TTL, sent in `Authorization: Bearer <token>` header
- **Refresh tokens**: 7-day TTL, exchanged for a new access token
- **Token subject**: User ID (stored as `str` in `sub` claim, decoded to `int` in deps)

## Alternatives Considered

### 1. Session Cookies (server-side sessions)
- **Pros**: Easy revocation, browser-native, CSRF protectable with SameSite
- **Cons**: Requires server-side session store (Redis), doesn't work well for API-first architecture, harder to use from mobile/CLI clients

### 2. OAuth2 Opaque Tokens
- **Pros**: Easy revocation, no token content leakage
- **Cons**: Every request requires a database lookup to validate the token (not stateless)

### 3. JWT with RS256 (RSA asymmetric signing)
- **Pros**: Public key verification allows third-party validation without sharing secret
- **Cons**: Additional key management complexity, slower to sign/verify, not required at current scale

### 4. API Keys (long-lived static tokens)
- **Pros**: Simple for machine-to-machine, easy to understand
- **Cons**: Long-lived tokens increase risk on compromise, no user-session semantics

### 5. Paseto (Platform-Agnostic Security Tokens)
- **Pros**: Better defaults than JWT (no algorithm confusion attacks), cleaner spec
- **Cons**: Less widespread adoption, fewer library options in Python, migration cost from JWT

## Rationale

JWT with HS256 was chosen because:

1. **Stateless**: No database lookup required to validate a token — the signature is self-authenticating
2. **Short TTL**: 30-minute access tokens limit the window of opportunity if a token is stolen
3. **Refresh Token Pattern**: 7-day refresh tokens allow long sessions without exposing long-lived access tokens
4. **Standard**: JWT is the de-facto standard for REST API authentication
5. **OAuth2 Compatibility**: Google OAuth2 tokens can be exchanged for our own JWTs, giving unified auth handling
6. **`python-jose`**: Well-maintained library with HS256/RS256 support and JWKS endpoint capability

## Implementation

```python
# backend/app/core/security.py
from datetime import datetime, timedelta, timezone
from jose import jwt, JWTError

ACCESS_TOKEN_EXPIRE_MINUTES = 30
REFRESH_TOKEN_EXPIRE_DAYS = 7

def create_access_token(subject: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    payload = {"sub": subject, "exp": expire, "type": "access"}
    return jwt.encode(payload, settings.SECRET_KEY, algorithm="HS256")

def create_refresh_token(subject: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    payload = {"sub": subject, "exp": expire, "type": "refresh"}
    return jwt.encode(payload, settings.SECRET_KEY, algorithm="HS256")

def decode_token(token: str) -> dict:
    return jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
```

```python
# backend/app/core/deps.py
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")

async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    try:
        payload = decode_token(token)
        user_id = int(payload["sub"])   # sub is str (jose requirement), decode to int
    except (JWTError, KeyError, ValueError):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)
    user = await db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)
    return user
```

### Token Subject Encoding

The `sub` claim uses `str(user.id)` when creating tokens and `int(payload["sub"])` when decoding. This is required because `python-jose` mandates string subjects per the JWT spec.

## Consequences

### Positive
- No database query per request for authentication (stateless validation)
- Short access token TTL limits blast radius of token theft
- Works identically for browser, mobile, and CLI clients
- Google OAuth flow exchanges Google's token for our own JWT (unified handling)

### Negative
- No instant token revocation (must wait for TTL to expire)
- Refresh token theft allows extended session hijacking
- `SECRET_KEY` compromise invalidates all tokens and requires rotation

### Token Revocation Strategy

For logout and forced revocation, a **token blocklist** stored in Redis can be used:
```python
# Add jti (JWT ID) claim to tokens
# On logout: store jti in Redis with TTL = token TTL
# On each request: check if jti is blocklisted
```

This is planned but not yet implemented; current logout deletes the token client-side only.

## Security Considerations

1. **HTTPS Only**: JWTs must only be transmitted over TLS in production
2. **No Sensitive Data in Payload**: JWT payload is base64-encoded, not encrypted — never put passwords or PII in claims
3. **Algorithm Pinning**: Always specify `algorithms=["HS256"]` in `jwt.decode()` to prevent algorithm confusion attacks
4. **Secret Key Length**: `SECRET_KEY` must be ≥ 32 characters (validated at startup)
5. **Token Storage**: Frontend stores tokens in `localStorage` (XSS risk); consider `httpOnly` cookies for hardened deployments

## Related Decisions

- See ADR-006 for SECRET_KEY management
- See ADR-003 for FastAPI dependency injection (`Depends(get_current_user)`)

## References

- [RFC 7519: JSON Web Token](https://www.rfc-editor.org/rfc/rfc7519)
- [python-jose Documentation](https://python-jose.readthedocs.io/)
- [JWT Best Practices (RFC 8725)](https://www.rfc-editor.org/rfc/rfc8725)
- [OWASP Authentication Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Authentication_Cheat_Sheet.html)
