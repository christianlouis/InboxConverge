"""
Unit tests for security module.
"""

import pytest
from app.core.security import (
    get_password_hash,
    verify_password,
    create_access_token,
    CredentialEncryption,
)


class TestPasswordHashing:
    """Test password hashing and verification"""

    def test_hash_password(self):
        """Test password hashing"""
        password = "securepassword123"
        hashed = get_password_hash(password)

        assert hashed != password
        assert len(hashed) > 50
        assert hashed.startswith("$2b$")

    def test_verify_password_success(self):
        """Test password verification with correct password"""
        password = "securepassword123"
        hashed = get_password_hash(password)

        assert verify_password(password, hashed) is True

    def test_verify_password_failure(self):
        """Test password verification with wrong password"""
        password = "securepassword123"
        wrong_password = "wrongpassword"
        hashed = get_password_hash(password)

        assert verify_password(wrong_password, hashed) is False


class TestJWT:
    """Test JWT token creation and validation"""

    def test_create_access_token(self):
        """Test access token creation"""
        data = {"sub": "test@example.com"}
        token = create_access_token(data)

        assert isinstance(token, str)
        assert len(token) > 50
        assert token.count(".") == 2  # JWT has 3 parts


class TestEncryption:
    """Test credential encryption/decryption"""

    def test_encrypt_password(self):
        """Test password encryption"""
        password = "mailpassword123"
        user_id = 1

        encryptor = CredentialEncryption(user_id=user_id)
        encrypted = encryptor.encrypt(password)

        assert encrypted != password
        assert len(encrypted) > 50

    def test_decrypt_password(self):
        """Test password decryption"""
        password = "mailpassword123"
        user_id = 1

        encryptor = CredentialEncryption(user_id=user_id)
        encrypted = encryptor.encrypt(password)
        decrypted = encryptor.decrypt(encrypted)

        assert decrypted == password

    def test_encryption_with_different_user_ids(self):
        """Test that encryption produces different results for different users"""
        password = "mailpassword123"
        user_id_1 = 1
        user_id_2 = 2

        encryptor_1 = CredentialEncryption(user_id=user_id_1)
        encryptor_2 = CredentialEncryption(user_id=user_id_2)

        encrypted_1 = encryptor_1.encrypt(password)
        encrypted_2 = encryptor_2.encrypt(password)

        # Different users should produce different encrypted values
        assert encrypted_1 != encrypted_2

        # But decryption should work correctly for each
        assert encryptor_1.decrypt(encrypted_1) == password
        assert encryptor_2.decrypt(encrypted_2) == password

    def test_decrypt_with_wrong_user_id_fails(self):
        """Test that decryption fails with wrong user ID"""
        password = "mailpassword123"
        user_id = 1
        wrong_user_id = 2

        encryptor = CredentialEncryption(user_id=user_id)
        wrong_encryptor = CredentialEncryption(user_id=wrong_user_id)

        encrypted = encryptor.encrypt(password)

        with pytest.raises(Exception):
            wrong_encryptor.decrypt(encrypted)
