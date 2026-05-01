"""Unit tests for security module"""

import os
import pytest
from unittest.mock import Mock, patch, MagicMock
from cryptography.fernet import Fernet

from core.security import (
    CredentialManager,
    PasswordHasher,
    SecureConfig,
    mask_sensitive_data,
    sanitize_log_data
)


class TestPasswordHasher:
    """Test PasswordHasher class"""

    def test_hash_password(self):
        """Test password hashing"""
        password = "test_password_123"
        hashed, salt = PasswordHasher.hash_password(password)

        assert hashed != password
        assert salt is not None
        assert len(hashed) > 0
        assert len(salt) > 0

    def test_hash_password_with_custom_salt(self):
        """Test password hashing with custom salt"""
        password = "test_password_123"
        custom_salt = "custom_salt_value"
        hashed, salt = PasswordHasher.hash_password(password, salt=custom_salt)

        assert salt == custom_salt

    def test_verify_password_correct(self):
        """Test verifying correct password"""
        password = "test_password_123"
        hashed, salt = PasswordHasher.hash_password(password)

        result = PasswordHasher.verify_password(password, hashed, salt)
        assert result is True

    def test_verify_password_incorrect(self):
        """Test verifying incorrect password"""
        password = "test_password_123"
        wrong_password = "wrong_password"
        hashed, salt = PasswordHasher.hash_password(password)

        result = PasswordHasher.verify_password(wrong_password, hashed, salt)
        assert result is False


class TestMaskSensitiveData:
    """Test mask_sensitive_data function"""

    def test_mask_string(self):
        """Test masking a string"""
        result = mask_sensitive_data("ABCD1234")
        assert result == "AB***1234"

    def test_mask_short_string(self):
        """Test masking a short string"""
        result = mask_sensitive_data("AB")
        assert result == "AB"

    def test_custom_visible_chars(self):
        """Test masking with custom visible chars"""
        result = mask_sensitive_data("ABCD1234", visible_chars=2)
        assert result == "AB***34"

    def test_custom_mask_char(self):
        """Test masking with custom mask char"""
        result = mask_sensitive_data("ABCD1234", mask_char='X')
        assert result == "ABXXX1234"

    def test_mask_empty_string(self):
        """Test masking empty string"""
        result = mask_sensitive_data("")
        assert result == ""

    def test_mask_none(self):
        """Test masking None"""
        result = mask_sensitive_data(None)
        assert result is None


class TestSanitizeLogData:
    """Test sanitize_log_data function"""

    def test_sanitize_dict_with_password(self):
        """Test sanitizing dict with password"""
        data = {
            'username': 'test_user',
            'password': 'secret123',
            'api_key': 'key123'
        }
        result = sanitize_log_data(data)

        assert result['username'] == 'test_user'
        assert result['password'] == '***REDACTED***'
        assert result['api_key'] == '***REDACTED***'

    def test_sanitize_dict_with_pin(self):
        """Test sanitizing dict with pin"""
        data = {'pin': '1234', 'totp_key': 'ABCD'}
        result = sanitize_log_data(data)

        # Short strings are masked with asterisks
        assert result['pin'] == '****'
        assert result['totp_key'] == '****'

    def test_sanitize_dict_with_tokens(self):
        """Test sanitizing dict with tokens"""
        data = {
            'access_token': 'token123',
            'refresh_token': 'refresh123'
        }
        result = sanitize_log_data(data)

        # Longer strings are masked with visible chars
        assert result['access_token'] == 'to***123'
        assert result['refresh_token'] == 're***123'

    def test_sanitize_empty_dict(self):
        """Test sanitizing empty dict"""
        data = {}
        result = sanitize_log_data(data)
        assert result == {}


class TestCredentialManager:
    """Test CredentialManager class"""

    @pytest.fixture
    def temp_env_file(self, tmp_path):
        """Create temporary .env file"""
        env_file = tmp_path / ".env"
        env_file.write_text("""
PYPORTMAN_ZERODHA_TEST_ACCOUNT_USER_ID=TEST123
PYPORTMAN_ZERODHA_TEST_ACCOUNT_PASSWORD=encrypted_password
PYPORTMAN_ZERODHA_TEST_ACCOUNT_API_KEY=test_api_key
PYPORTMAN_ZERODHA_TEST_ACCOUNT_TOTP_KEY=encrypted_totp
PYPORTMAN_ZERODHA_TEST_ACCOUNT_TOTP_ENABLED=true
""")
        return str(env_file)

    def test_encrypt_decrypt(self):
        """Test encryption and decryption"""
        manager = CredentialManager()
        plaintext = "secret_data"

        encrypted = manager.encrypt(plaintext)
        decrypted = manager.decrypt(encrypted)

        assert encrypted != plaintext
        assert decrypted == plaintext

    def test_encrypt_decrypt_different_instances(self):
        """Test encryption/decryption with different instances"""
        # Use same key for both instances
        key = Fernet.generate_key()
        manager1 = CredentialManager()
        manager1._encryption_key = key
        manager1._cipher = Fernet(key)

        manager2 = CredentialManager()
        manager2._encryption_key = key
        manager2._cipher = Fernet(key)

        plaintext = "secret_data"
        encrypted = manager1.encrypt(plaintext)
        decrypted = manager2.decrypt(encrypted)

        assert decrypted == plaintext

    def test_get_credential(self, temp_env_file):
        """Test getting a single credential"""
        with patch.dict(os.environ, {'TEST_KEY': 'test_value'}):
            manager = CredentialManager()
            result = manager.get_credential('TEST_KEY')
            assert result == 'test_value'

    def test_get_credential_encrypted(self, temp_env_file):
        """Test getting encrypted credential"""
        manager = CredentialManager()
        plaintext = "secret_value"
        encrypted = manager.encrypt(plaintext)

        with patch.dict(os.environ, {'TEST_KEY': encrypted}):
            result = manager.get_credential('TEST_KEY', encrypted=True)
            assert result == plaintext

    def test_get_broker_credentials(self, temp_env_file):
        """Test getting broker credentials"""
        manager = CredentialManager()

        with patch.dict(os.environ, {
            'ZERODHA_TEST_ACCOUNT_USER_ID': 'TEST123',
            'ZERODHA_TEST_ACCOUNT_PASSWORD': 'encrypted_pass',
            'ZERODHA_TEST_ACCOUNT_API_KEY': 'test_api',
            'ZERODHA_TEST_ACCOUNT_TOTP_KEY': 'encrypted_totp',
            'ZERODHA_TEST_ACCOUNT_TOTP_ENABLED': 'true'
        }):
            # Mock decrypt to return plaintext
            with patch.object(manager, 'decrypt', side_effect=lambda x: x.replace('encrypted_', '')):
                result = manager.get_broker_credentials('zerodha', 'test_account')

                assert result['user_id'] == 'TEST123'
                assert result['password'] == 'pass'
                assert result['api_key'] == 'test_api'
                assert result['totp_key'] == 'totp'
                assert result['totp_enabled'] is True

    def test_validate_credentials_valid(self):
        """Test validating valid credentials"""
        manager = CredentialManager()
        credentials = {
            'user_id': 'TEST123',
            'password': 'password',
            'api_key': 'api_key'
        }
        result = manager.validate_credentials(credentials)
        assert result is True

    def test_validate_credentials_missing_user_id(self):
        """Test validating credentials without user_id"""
        manager = CredentialManager()
        credentials = {
            'password': 'password',
            'api_key': 'api_key'
        }
        with pytest.raises(Exception):  # ValidationError
            manager.validate_credentials(credentials)

    def test_validate_credentials_missing_password(self):
        """Test validating credentials without password"""
        manager = CredentialManager()
        credentials = {
            'user_id': 'TEST123',
            'api_key': 'api_key'
        }
        with pytest.raises(Exception):  # ValidationError
            manager.validate_credentials(credentials)


class TestSecureConfig:
    """Test SecureConfig class"""

    @pytest.fixture
    def temp_config_file(self, tmp_path):
        """Create temporary config file"""
        config_file = tmp_path / "config.json"
        return str(config_file)

    def test_init_creates_config_dir(self, tmp_path):
        """Test initialization creates config directory"""
        config_dir = tmp_path / "config"
        config_file = config_dir / "config.json"

        config = SecureConfig(config_file=str(config_file))
        assert config_dir.exists()

    def test_get_existing_value(self, temp_config_file):
        """Test getting existing value"""
        import json
        with open(temp_config_file, 'w') as f:
            json.dump({'test': {'key': 'value'}}, f)

        config = SecureConfig(config_file=temp_config_file)
        result = config.get('test.key')
        assert result == 'value'

    def test_get_non_existing_value(self, temp_config_file):
        """Test getting non-existing value"""
        import json
        with open(temp_config_file, 'w') as f:
            json.dump({}, f)

        config = SecureConfig(config_file=temp_config_file)
        result = config.get('non.existing.key', default='default')
        assert result == 'default'

    def test_set_value(self, temp_config_file):
        """Test setting a value"""
        config = SecureConfig(config_file=temp_config_file)
        config.set('test.key', 'value')

        result = config.get('test.key')
        assert result == 'value'

    def test_set_nested_value(self, temp_config_file):
        """Test setting nested value"""
        config = SecureConfig(config_file=temp_config_file)
        config.set('brokers.zerodha.api_key', 'test_key')

        result = config.get('brokers.zerodha.api_key')
        assert result == 'test_key'

    def test_get_broker_config(self, temp_config_file):
        """Test getting broker config"""
        import json
        with open(temp_config_file, 'w') as f:
            json.dump({'brokers': {'zerodha': {'api_key': 'test_key'}}}, f)

        config = SecureConfig(config_file=temp_config_file)
        result = config.get_broker_config('zerodha')
        assert result == {'api_key': 'test_key'}

    def test_set_broker_config(self, temp_config_file):
        """Test setting broker config"""
        config = SecureConfig(config_file=temp_config_file)
        config.set_broker_config('zerodha', {'api_key': 'test_key'})

        result = config.get_broker_config('zerodha')
        assert result == {'api_key': 'test_key'}
