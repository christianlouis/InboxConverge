# ADR 002: Use Fernet Encryption for Mail Credentials

**Status:** Accepted  
**Date:** 2026-01-20  
**Deciders:** Security Team, Development Team

## Context

The application stores POP3/IMAP credentials for user mail accounts. These credentials must be:

1. Encrypted at rest in the database
2. Decryptable when needed for mail operations
3. Protected with industry-standard encryption
4. Simple to implement and maintain

Security requirements:
- Symmetric encryption (need to decrypt for use)
- At least AES-128 bit encryption
- Per-user salt for additional security
- Key rotation capability

## Decision

We will use **Fernet (symmetric encryption)** from the Python `cryptography` library for encrypting mail credentials.

## Alternatives Considered

### 1. AES Directly (PyCrypto/cryptography)
- **Pros**: Full control, widely supported
- **Cons**: Easy to implement incorrectly, need to handle padding, IV, etc.

### 2. Database-Level Encryption (PostgreSQL)
- **Pros**: Transparent to application, secure
- **Cons**: All-or-nothing encryption, harder key rotation, requires DB support

### 3. HashiCorp Vault
- **Pros**: Enterprise-grade secret management, audit logs, key rotation
- **Cons**: Additional infrastructure, complexity, operational overhead

### 4. AWS KMS / Cloud KMS
- **Pros**: Managed service, automatic key rotation
- **Cons**: Cloud vendor lock-in, network latency for each decrypt, cost

## Rationale

Fernet was chosen because:

1. **High-Level API**: Implements encryption best practices by default
2. **Proven Security**: Based on AES-128 in CBC mode with HMAC for authentication
3. **Python Native**: Part of `cryptography` library (PyCA)
4. **Timestamp Validation**: Built-in support for expiring encrypted data
5. **No Complexity**: Handles padding, IV, authentication tag automatically
6. **Battle-Tested**: Used in production by many Python applications

## Implementation Details

### Key Derivation
```python
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2

# Generate key from master secret + per-user salt
kdf = PBKDF2(
    algorithm=hashes.SHA256(),
    length=32,
    salt=salt,
    iterations=100_000,
)
key = base64.urlsafe_b64encode(kdf.derive(ENCRYPTION_KEY.encode()))
```

### Encryption/Decryption
```python
def encrypt_password(password: str, user_id: int) -> str:
    """Encrypt password with user-specific salt."""
    salt = get_user_salt(user_id)
    key = derive_key(ENCRYPTION_KEY, salt)
    fernet = Fernet(key)
    return fernet.encrypt(password.encode()).decode()

def decrypt_password(encrypted_password: str, user_id: int) -> str:
    """Decrypt password with user-specific salt."""
    salt = get_user_salt(user_id)
    key = derive_key(ENCRYPTION_KEY, salt)
    fernet = Fernet(key)
    return fernet.decrypt(encrypted_password.encode()).decode()
```

## Consequences

### Positive
- Simple, secure implementation
- No risk of implementing encryption incorrectly
- Built-in authentication (prevents tampering)
- Can add TTL expiration if needed
- Easy to test and validate

### Negative
- Slower than AES-GCM (includes HMAC overhead)
- Fixed to AES-128 (no AES-256 option without manual implementation)
- All encrypted values become invalid if master key changes (no key rotation)

### Mitigation Strategies

#### For Key Rotation
```python
# Support multiple encryption keys with versioning
ENCRYPTION_KEY_V1 = os.getenv('ENCRYPTION_KEY_V1')
ENCRYPTION_KEY_V2 = os.getenv('ENCRYPTION_KEY_V2')  # New key

# Store key version with encrypted data
encrypted_data = f"v2:{fernet_v2.encrypt(data)}"

# Decrypt with appropriate key
version, encrypted = encrypted_data.split(':', 1)
if version == 'v1':
    return fernet_v1.decrypt(encrypted)
elif version == 'v2':
    return fernet_v2.decrypt(encrypted)
```

#### For Per-User Salt
```python
# Generate unique salt per user (stored in users table)
def get_or_create_user_salt(user_id: int) -> bytes:
    # Use deterministic salt based on user_id + global salt
    # OR store random salt in database per user
    return hashlib.sha256(f'pop3_forwarder_user_{user_id}'.encode()).digest()
```

## Security Best Practices

1. **Never log encryption keys**: Keys only in environment variables
2. **Rotate keys regularly**: Plan for annual key rotation
3. **Secure key storage**: Use secrets manager in production
4. **Strong master key**: Minimum 32 characters, random
5. **Audit access**: Log when credentials are decrypted
6. **Principle of least privilege**: Only workers need decryption

## Monitoring

- Track decryption failures (wrong key indicator)
- Monitor performance impact of encryption
- Alert on unusual decryption volume
- Log credential access for audit

## Future Improvements

1. Migrate to HashiCorp Vault for enterprise deployments
2. Implement automatic key rotation
3. Add encryption key versioning
4. Consider AWS KMS for AWS deployments
5. Add audit trail for credential access

## Related Decisions

- See ADR-006 for key management in production
- See SECURITY_REPORT.md for security analysis

## References

- [Fernet Specification](https://github.com/fernet/spec/blob/master/Spec.md)
- [Python cryptography library](https://cryptography.io/)
- [OWASP Cryptographic Storage Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Cryptographic_Storage_Cheat_Sheet.html)
