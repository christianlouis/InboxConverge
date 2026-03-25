# ADR 006: Key Management in Production

**Status:** Accepted  
**Date:** 2026-02-05  
**Deciders:** Security Team, Development Team

## Context

The application requires several cryptographic secrets for secure operation:

1. `SECRET_KEY` — signs and verifies JWT tokens (HMAC-SHA256)
2. `ENCRYPTION_KEY` — Fernet master key for encrypting POP3/IMAP passwords at rest (see ADR-002)
3. `GOOGLE_CLIENT_SECRET` — OAuth2 client secret for Google Sign-In
4. `STRIPE_API_KEY` — Stripe payment processing API key

These secrets must be:
- **Available at startup** (bootstrap dependency before database is ready)
- **Never committed to source control**
- **Rotatable** without application downtime
- **Auditable** (who accessed what, when)

## Decision

For the initial production deployment we will manage secrets via **environment variables injected at container runtime**, loaded from a **secrets management backend** (Docker secrets, Kubernetes Secrets, or HashiCorp Vault depending on deployment target). Local development uses `.env` files that are `.gitignore`d.

Startup validation rejects the application launch if any required secret is missing or too short.

## Alternatives Considered

### 1. Hardcoded / In-Code Defaults
- **Pros**: Simple, no external dependency
- **Cons**: Catastrophic security failure, impossible to rotate without code deployment

### 2. Plain `.env` Files in Production
- **Pros**: Simple, portable
- **Cons**: Files on disk are a security risk, not auditable, hard to rotate across multiple instances

### 3. HashiCorp Vault
- **Pros**: Industry-standard secret management, dynamic secrets, full audit trail, automatic rotation
- **Cons**: Significant operational overhead for initial deployment, requires dedicated Vault cluster

### 4. AWS Secrets Manager / Azure Key Vault
- **Pros**: Managed service, automatic rotation, IAM integration
- **Cons**: Cloud vendor lock-in, adds latency on secret retrieval, requires cloud SDK

### 5. Docker Swarm Secrets / Kubernetes Secrets
- **Pros**: Native to container orchestration platform, mounted as files, not in env
- **Cons**: Still requires base64 encoding, secrets accessible to anyone with cluster access unless using encrypted etcd

## Rationale

Environment variable injection was chosen as the **pragmatic starting point** because:

1. **Universally Supported**: Works identically in Docker Compose, Kubernetes, and bare-metal
2. **No Additional Infrastructure**: No Vault cluster to operate initially
3. **Startup Validation**: FastAPI lifespan validates all required secrets before accepting requests
4. **Platform Agnostic**: Easy to migrate to Vault or cloud KMS later without code changes
5. **12-Factor App Compliance**: Follows 12-factor app principle for configuration

HashiCorp Vault is documented as the **target architecture** for enterprise deployments (see Future Roadmap).

## Implementation

### Startup Validation
```python
# backend/app/core/config.py
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    SECRET_KEY: str
    ENCRYPTION_KEY: str

    @validator("SECRET_KEY")
    def secret_key_min_length(cls, v: str) -> str:
        if len(v) < 32:
            raise ValueError("SECRET_KEY must be at least 32 characters")
        return v

    @validator("ENCRYPTION_KEY")
    def encryption_key_must_be_valid_fernet(cls, v: str) -> str:
        try:
            Fernet(v.encode())
        except Exception:
            raise ValueError("ENCRYPTION_KEY must be a valid Fernet key")
        return v
```

### Docker Compose (Development / Staging)
```yaml
# docker-compose.new.yml
services:
  backend:
    env_file:
      - backend/.env  # Never committed to git
    environment:
      - SECRET_KEY=${SECRET_KEY}
      - ENCRYPTION_KEY=${ENCRYPTION_KEY}
```

### Kubernetes (Production)
```yaml
# Create secret from secure source (not echo/printf)
kubectl create secret generic app-secrets \
  --from-literal=SECRET_KEY="$(vault kv get -field=SECRET_KEY secret/app)" \
  --from-literal=ENCRYPTION_KEY="$(vault kv get -field=ENCRYPTION_KEY secret/app)"

# Reference in Deployment
envFrom:
  - secretRef:
      name: app-secrets
```

### Generating Secure Keys
```bash
# Generate SECRET_KEY (min 32 chars, cryptographically random)
python -c "import secrets; print(secrets.token_hex(32))"

# Generate ENCRYPTION_KEY (valid Fernet key)
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

## Key Rotation Procedure

### JWT Secret Key Rotation
1. Generate new `SECRET_KEY`
2. Deploy with both old and new key (dual-key verification)
3. All existing tokens expire within TTL (default: 30 minutes access, 7 days refresh)
4. Remove old key from config after max TTL has elapsed

### Encryption Key Rotation (Fernet)
1. Generate new `ENCRYPTION_KEY`
2. Run migration script to re-encrypt all stored credentials with new key
3. Deploy new key in production
4. Verify decryption works on all accounts
5. Delete old key from secrets store

```python
# Key rotation migration (run as one-off script)
async def rotate_encryption_key(old_key: str, new_key: str, db: AsyncSession):
    old_fernet = Fernet(old_key.encode())
    new_fernet = Fernet(new_key.encode())
    accounts = await db.execute(select(MailAccount).where(MailAccount.password.is_not(None)))
    for account in accounts.scalars():
        plaintext = old_fernet.decrypt(account.password.encode())
        account.password = new_fernet.encrypt(plaintext).decode()
    await db.commit()
```

## Consequences

### Positive
- Startup validation prevents misconfigured deployments
- Secrets never touch the filesystem in container (env-var injection)
- Rotation procedure documented and tested
- Clear migration path to Vault for enterprise use

### Negative
- Environment variables are visible to all processes in the container
- Docker inspect can reveal env vars if host is compromised
- No automatic rotation — manual procedure required

### Mitigation
- Use Docker secrets or Kubernetes secrets (mounted as files) to avoid env-var exposure
- Regularly audit secret access patterns
- Rotate keys on any suspected compromise

## Future Roadmap

1. **Phase 2**: Migrate to HashiCorp Vault for dynamic secrets and automatic rotation
2. **Phase 3**: Implement per-user encryption key derivation (separate Fernet keys per user)
3. **Phase 4**: Add HSM support for root key protection

## Related Decisions

- See ADR-002 for Fernet encryption implementation
- See ADR-007 for JWT token management

## References

- [12-Factor App: Config](https://12factor.net/config)
- [HashiCorp Vault](https://www.vaultproject.io/)
- [Kubernetes Secrets](https://kubernetes.io/docs/concepts/configuration/secret/)
- [OWASP Secrets Management Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Secrets_Management_Cheat_Sheet.html)
