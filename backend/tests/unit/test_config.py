"""
Unit tests for configuration module.
"""
import pytest
from pydantic import ValidationError
from app.core.config import Settings


class TestConfigValidation:
    """Test configuration validation"""
    
    def test_default_secret_key_rejected(self):
        """Test that default SECRET_KEY is rejected"""
        with pytest.raises(ValidationError) as exc_info:
            Settings(
                SECRET_KEY="change-this-to-a-secure-random-secret-key-in-production",
                ENCRYPTION_KEY="this-is-a-secure-32-character-key-for-testing",
            )
        
        assert "SECRET_KEY must be changed from default" in str(exc_info.value)
    
    def test_short_secret_key_rejected(self):
        """Test that short SECRET_KEY is rejected"""
        with pytest.raises(ValidationError) as exc_info:
            Settings(
                SECRET_KEY="short",
                ENCRYPTION_KEY="this-is-a-secure-32-character-key-for-testing",
            )
        
        assert "at least 32 characters" in str(exc_info.value)
    
    def test_default_encryption_key_rejected(self):
        """Test that default ENCRYPTION_KEY is rejected"""
        with pytest.raises(ValidationError) as exc_info:
            Settings(
                SECRET_KEY="this-is-a-secure-32-character-key-for-testing",
                ENCRYPTION_KEY="change-this-to-a-secure-encryption-key",
            )
        
        assert "ENCRYPTION_KEY must be changed from default" in str(exc_info.value)
    
    def test_short_encryption_key_rejected(self):
        """Test that short ENCRYPTION_KEY is rejected"""
        with pytest.raises(ValidationError) as exc_info:
            Settings(
                SECRET_KEY="this-is-a-secure-32-character-key-for-testing",
                ENCRYPTION_KEY="short",
            )
        
        assert "at least 32 characters" in str(exc_info.value)
    
    def test_valid_keys_accepted(self):
        """Test that valid keys are accepted"""
        settings = Settings(
            SECRET_KEY="this-is-a-secure-32-character-key-for-testing-secret",
            ENCRYPTION_KEY="this-is-a-secure-32-character-key-for-encryption",
        )
        
        assert settings.SECRET_KEY == "this-is-a-secure-32-character-key-for-testing-secret"
        assert settings.ENCRYPTION_KEY == "this-is-a-secure-32-character-key-for-encryption"
