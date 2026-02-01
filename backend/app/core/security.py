"""
Security utilities for encryption, hashing, and token generation.
"""
import secrets
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from jose import JWTError, jwt
from passlib.context import CryptContext
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2
import base64

from app.core.config import settings


# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash"""
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """Generate password hash"""
    return pwd_context.hash(password)


def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    """Create JWT access token"""
    to_encode = data.copy()
    
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({"exp": expire, "type": "access"})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt


def create_refresh_token(data: Dict[str, Any]) -> str:
    """Create JWT refresh token"""
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode.update({"exp": expire, "type": "refresh"})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt


def decode_token(token: str) -> Optional[Dict[str, Any]]:
    """Decode and validate JWT token"""
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        return payload
    except JWTError:
        return None


def generate_random_token(length: int = 32) -> str:
    """Generate a secure random token"""
    return secrets.token_urlsafe(length)


class CredentialEncryption:
    """Handles encryption/decryption of sensitive credentials (POP3/IMAP passwords)"""
    
    def __init__(self, key: Optional[str] = None, user_id: Optional[int] = None):
        """
        Initialize encryption with a key.
        If no key provided, uses the one from settings.
        In production, use a unique salt per user for enhanced security.
        
        Args:
            key: Encryption key (defaults to settings.ENCRYPTION_KEY)
            user_id: Optional user ID for per-user salt generation
        """
        if key is None:
            key = settings.ENCRYPTION_KEY
        
        # Generate salt - in production, this should be unique per user
        if user_id is not None:
            # Per-user salt for production
            salt = f'pop3_forwarder_user_{user_id}'.encode('utf-8')[:16].ljust(16, b'0')
        else:
            # Default salt for system-wide operations (use with caution)
            salt = b'pop3_forwarder_0'
        
        # Derive a proper Fernet key from the provided key
        kdf = PBKDF2(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
        )
        key_bytes = key.encode('utf-8')
        derived_key = base64.urlsafe_b64encode(kdf.derive(key_bytes))
        self.fernet = Fernet(derived_key)
    
    def encrypt(self, plain_text: str) -> str:
        """Encrypt a string and return base64-encoded ciphertext"""
        encrypted = self.fernet.encrypt(plain_text.encode('utf-8'))
        return base64.b64encode(encrypted).decode('utf-8')
    
    def decrypt(self, encrypted_text: str) -> str:
        """Decrypt a base64-encoded ciphertext"""
        encrypted_bytes = base64.b64decode(encrypted_text.encode('utf-8'))
        decrypted = self.fernet.decrypt(encrypted_bytes)
        return decrypted.decode('utf-8')


# Global encryption instance
credential_encryptor = CredentialEncryption()


def encrypt_credential(credential: str) -> str:
    """Convenience function to encrypt a credential"""
    return credential_encryptor.encrypt(credential)


def decrypt_credential(encrypted_credential: str) -> str:
    """Convenience function to decrypt a credential"""
    return credential_encryptor.decrypt(encrypted_credential)
