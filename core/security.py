"""
Security Module
Handles credentials encryption, .env management, and security utilities
"""

import os
import json
import base64
from pathlib import Path
from typing import Dict, Optional, Any
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import hashlib
from dotenv import load_dotenv

from .error_handler import ConfigurationError, ValidationError
from .logging_config import get_logger

logger = get_logger('pyportman.security')


class CredentialManager:
    """
    Manages secure credential storage and retrieval
    """

    def __init__(self, env_file: Optional[str] = None):
        """
        Initialize credential manager

        Args:
            env_file: Path to .env file (default: .env in project root)
        """
        if env_file:
            load_dotenv(env_file)
        else:
            # Try to load from common locations
            project_root = Path(__file__).parent.parent
            env_paths = [
                project_root / '.env',
                project_root / '.env.local',
                Path.home() / '.pyportman' / '.env'
            ]
            for env_path in env_paths:
                if env_path.exists():
                    load_dotenv(env_path)
                    logger.info(f"Loaded credentials from {env_path}")
                    break

        self._encryption_key = self._get_or_create_encryption_key()
        self._cipher = Fernet(self._encryption_key)

    def _get_or_create_encryption_key(self) -> bytes:
        """Get or create encryption key from environment"""
        key = os.getenv('PYPORTMAN_ENCRYPTION_KEY')

        if key:
            try:
                return base64.urlsafe_b64decode(key.encode())
            except Exception as e:
                logger.warning(f"Invalid encryption key in env, creating new one: {e}")

        # Generate new key
        new_key = Fernet.generate_key()
        logger.warning("Generated new encryption key. Set PYPORTMAN_ENCRYPTION_KEY in .env to persist.")
        return new_key

    def encrypt(self, data: str) -> str:
        """
        Encrypt sensitive data

        Args:
            data: Plain text data to encrypt

        Returns:
            Encrypted data (base64 encoded)
        """
        encrypted = self._cipher.encrypt(data.encode())
        return base64.urlsafe_b64encode(encrypted).decode()

    def decrypt(self, encrypted_data: str) -> str:
        """
        Decrypt sensitive data

        Args:
            encrypted_data: Encrypted data (base64 encoded)

        Returns:
            Decrypted plain text
        """
        try:
            encrypted_bytes = base64.urlsafe_b64decode(encrypted_data.encode())
            decrypted = self._cipher.decrypt(encrypted_bytes)
            return decrypted.decode()
        except Exception as e:
            raise ConfigurationError(f"Failed to decrypt data: {e}")

    def get_credential(self, key: str, encrypted: bool = False) -> Optional[str]:
        """
        Get credential from environment

        Args:
            key: Environment variable key
            encrypted: Whether the value is encrypted

        Returns:
            Credential value or None if not found
        """
        value = os.getenv(key)
        if not value:
            return None

        if encrypted:
            try:
                return self.decrypt(value)
            except Exception as e:
                logger.error(f"Failed to decrypt {key}: {e}")
                return None

        return value

    def get_broker_credentials(self, broker: str, account_name: str) -> Dict[str, str]:
        """
        Get credentials for a specific broker account

        Args:
            broker: Broker name (zerodha, angel, etc.)
            account_name: Account name/identifier

        Returns:
            Dictionary of credentials
        """
        prefix = f"{broker.upper()}_{account_name.upper()}_"

        credentials = {
            'user_id': self.get_credential(f'{prefix}USER_ID'),
            'password': self.get_credential(f'{prefix}PASSWORD', encrypted=True),
            'api_key': self.get_credential(f'{prefix}API_KEY'),
            'totp_key': self.get_credential(f'{prefix}TOTP_KEY', encrypted=True),
            'totp_enabled': self.get_credential(f'{prefix}TOTP_ENABLED') == 'true',
        }

        # Remove None values
        return {k: v for k, v in credentials.items() if v is not None}

    def validate_credentials(self, credentials: Dict[str, Any]) -> bool:
        """
        Validate that required credentials are present

        Args:
            credentials: Dictionary of credentials

        Returns:
            True if valid, raises ValidationError otherwise
        """
        required_fields = ['user_id', 'password']
        missing = [field for field in required_fields if not credentials.get(field)]

        if missing:
            raise ValidationError(f"Missing required credentials: {', '.join(missing)}")

        return True


class PasswordHasher:
    """Utility for hashing passwords"""

    @staticmethod
    def hash_password(password: str, salt: Optional[str] = None) -> tuple[str, str]:
        """
        Hash a password using PBKDF2

        Args:
            password: Plain text password
            salt: Optional salt (will generate if not provided)

        Returns:
            Tuple of (hashed_password, salt)
        """
        if salt is None:
            salt = os.urandom(16).hex()

        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt.encode(),
            iterations=100000,
        )
        hashed = base64.urlsafe_b64encode(kdf.derive(password.encode())).decode()
        return hashed, salt

    @staticmethod
    def verify_password(password: str, hashed_password: str, salt: str) -> bool:
        """
        Verify a password against its hash

        Args:
            password: Plain text password to verify
            hashed_password: Stored hash
            salt: Salt used for hashing

        Returns:
            True if password matches
        """
        new_hash, _ = PasswordHasher.hash_password(password, salt)
        return new_hash == hashed_password


class SecureConfig:
    """
    Secure configuration manager
    """

    def __init__(self, config_file: Optional[str] = None):
        """
        Initialize secure config manager

        Args:
            config_file: Path to config file (JSON format)
        """
        self.config_file = config_file or self._get_default_config_path()
        self.config = self._load_config()

    def _get_default_config_path(self) -> str:
        """Get default config file path"""
        config_dir = Path.home() / '.pyportman'
        config_dir.mkdir(exist_ok=True)
        return str(config_dir / 'config.json')

    def _load_config(self) -> Dict:
        """Load configuration from file"""
        if not os.path.exists(self.config_file):
            return {}

        try:
            with open(self.config_file, 'r') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Failed to load config: {e}")
            return {}

    def save_config(self) -> None:
        """Save configuration to file"""
        try:
            config_dir = Path(self.config_file).parent
            config_dir.mkdir(exist_ok=True)

            with open(self.config_file, 'w') as f:
                json.dump(self.config, f, indent=2)

            # Set restrictive permissions
            os.chmod(self.config_file, 0o600)
            logger.info(f"Configuration saved to {self.config_file}")
        except Exception as e:
            raise ConfigurationError(f"Failed to save config: {e}")

    def get(self, key: str, default: Any = None) -> Any:
        """Get configuration value"""
        keys = key.split('.')
        value = self.config
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default
        return value

    def set(self, key: str, value: Any) -> None:
        """Set configuration value"""
        keys = key.split('.')
        config = self.config
        for k in keys[:-1]:
            if k not in config:
                config[k] = {}
            config = config[k]
        config[keys[-1]] = value

    def get_broker_config(self, broker: str) -> Dict:
        """Get broker-specific configuration"""
        return self.get(f'brokers.{broker}', {})

    def set_broker_config(self, broker: str, config: Dict) -> None:
        """Set broker-specific configuration"""
        self.set(f'brokers.{broker}', config)


# Security utilities
def mask_sensitive_data(data: str, mask_char: str = '*', visible_chars: int = 4) -> str:
    """
    Mask sensitive data for logging

    Args:
        data: Data to mask
        mask_char: Character to use for masking
        visible_chars: Number of characters to show at start and end

    Returns:
        Masked string
    """
    if not data or len(data) <= visible_chars * 2:
        return mask_char * len(data) if data else ''

    return data[:visible_chars] + mask_char * (len(data) - visible_chars * 2) + data[-visible_chars:]


def sanitize_log_data(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Sanitize dictionary for logging by masking sensitive fields

    Args:
        data: Dictionary to sanitize

    Returns:
        Sanitized dictionary
    """
    sensitive_keys = [
        'password', 'pin', 'api_key', 'api_secret', 'totp_key',
        'access_token', 'refresh_token', 'auth_token'
    ]

    sanitized = {}
    for key, value in data.items():
        key_lower = key.lower()
        if any(sensitive in key_lower for sensitive in sensitive_keys):
            if isinstance(value, str):
                sanitized[key] = mask_sensitive_data(value)
            else:
                sanitized[key] = '***REDACTED***'
        else:
            sanitized[key] = value

    return sanitized
