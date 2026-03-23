"""
Unit tests for extended security module functionality.
"""

from datetime import timedelta
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    generate_random_token,
    encrypt_credential,
    decrypt_credential,
    CredentialEncryption,
)


class TestAccessToken:
    """Test JWT access token creation and decoding"""

    def test_create_access_token_with_custom_expiry(self):
        """Test creating an access token with custom expiry"""
        data = {"sub": "test@example.com"}
        token = create_access_token(data, expires_delta=timedelta(hours=1))

        assert isinstance(token, str)
        assert token.count(".") == 2

    def test_decode_valid_access_token(self):
        """Test decoding a valid access token"""
        data = {"sub": "user123"}
        token = create_access_token(data)

        payload = decode_token(token)
        assert payload is not None
        assert payload["sub"] == "user123"
        assert payload["type"] == "access"

    def test_decode_invalid_token_returns_none(self):
        """Test that decoding an invalid token returns None"""
        result = decode_token("invalid.token.string")
        assert result is None

    def test_decode_empty_token_returns_none(self):
        """Test that decoding an empty string returns None"""
        result = decode_token("")
        assert result is None

    def test_access_token_contains_type(self):
        """Test that access token payload contains type 'access'"""
        data = {"sub": "user@example.com"}
        token = create_access_token(data)
        payload = decode_token(token)

        assert payload is not None
        assert payload["type"] == "access"

    def test_access_token_contains_expiry(self):
        """Test that access token payload contains expiry"""
        data = {"sub": "user@example.com"}
        token = create_access_token(data)
        payload = decode_token(token)

        assert payload is not None
        assert "exp" in payload


class TestRefreshToken:
    """Test JWT refresh token creation and decoding"""

    def test_create_refresh_token(self):
        """Test refresh token creation"""
        data = {"sub": "test@example.com"}
        token = create_refresh_token(data)

        assert isinstance(token, str)
        assert token.count(".") == 2

    def test_decode_refresh_token(self):
        """Test decoding a valid refresh token"""
        data = {"sub": "user456"}
        token = create_refresh_token(data)

        payload = decode_token(token)
        assert payload is not None
        assert payload["sub"] == "user456"
        assert payload["type"] == "refresh"

    def test_refresh_token_different_from_access(self):
        """Test that refresh and access tokens are different"""
        data = {"sub": "test@example.com"}
        access = create_access_token(data)
        refresh = create_refresh_token(data)

        assert access != refresh


class TestRandomToken:
    """Test random token generation"""

    def test_generate_random_token_default_length(self):
        """Test generating a random token with default length"""
        token = generate_random_token()
        assert isinstance(token, str)
        assert len(token) > 0

    def test_generate_random_token_custom_length(self):
        """Test generating a random token with custom length"""
        token = generate_random_token(64)
        assert isinstance(token, str)
        assert len(token) > 0

    def test_random_tokens_are_unique(self):
        """Test that generated tokens are unique"""
        tokens = {generate_random_token() for _ in range(10)}
        assert len(tokens) == 10


class TestGlobalEncryptionFunctions:
    """Test global encryption convenience functions"""

    def test_encrypt_credential_returns_string(self):
        """Test that encrypt_credential returns a non-empty string"""
        encrypted = encrypt_credential("my-password")
        assert isinstance(encrypted, str)
        assert len(encrypted) > 0

    def test_decrypt_credential_roundtrip(self):
        """Test encrypt/decrypt roundtrip with global functions"""
        original = "super-secret-password-123"
        encrypted = encrypt_credential(original)
        decrypted = decrypt_credential(encrypted)
        assert decrypted == original

    def test_encrypt_credential_is_not_plaintext(self):
        """Test that encrypted credential differs from plaintext"""
        password = "my-password"
        encrypted = encrypt_credential(password)
        assert encrypted != password


class TestCredentialEncryptionEdgeCases:
    """Test edge cases in credential encryption"""

    def test_encrypt_empty_string(self):
        """Test encrypting an empty string"""
        encryptor = CredentialEncryption(user_id=1)
        encrypted = encryptor.encrypt("")
        decrypted = encryptor.decrypt(encrypted)
        assert decrypted == ""

    def test_encrypt_long_string(self):
        """Test encrypting a very long string"""
        long_password = "a" * 10000
        encryptor = CredentialEncryption(user_id=1)
        encrypted = encryptor.encrypt(long_password)
        decrypted = encryptor.decrypt(encrypted)
        assert decrypted == long_password

    def test_encrypt_special_characters(self):
        """Test encrypting a string with special characters"""
        special = "p@$$w0rd!#%^&*()_+-=[]{}|;':\",./<>?"
        encryptor = CredentialEncryption(user_id=1)
        encrypted = encryptor.encrypt(special)
        decrypted = encryptor.decrypt(encrypted)
        assert decrypted == special

    def test_encrypt_unicode(self):
        """Test encrypting unicode characters"""
        unicode_str = "密码テスト🔒"
        encryptor = CredentialEncryption(user_id=1)
        encrypted = encryptor.encrypt(unicode_str)
        decrypted = encryptor.decrypt(encrypted)
        assert decrypted == unicode_str

    def test_custom_key(self):
        """Test encryption with a custom key"""
        key = "custom-encryption-key-that-is-at-least-32-chars-long"
        encryptor = CredentialEncryption(key=key, user_id=1)
        encrypted = encryptor.encrypt("test-data")
        decrypted = encryptor.decrypt(encrypted)
        assert decrypted == "test-data"

    def test_system_salt_without_user_id(self):
        """Test encryption with system salt (no user_id)"""
        encryptor = CredentialEncryption()
        encrypted = encryptor.encrypt("system-data")
        decrypted = encryptor.decrypt(encrypted)
        assert decrypted == "system-data"
