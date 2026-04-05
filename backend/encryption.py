"""
Encryption utilities for pyPortMan Backend
Secure credential storage using Fernet symmetric encryption
"""

import os
import base64
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import uuid


class EncryptionManager:
    """Manager for encrypting/decrypting sensitive data"""

    def __init__(self, machine_id: str = None):
        """
        Initialize encryption manager

        Args:
            machine_id: Unique machine identifier. If None, uses system UUID.
        """
        self.machine_id = machine_id or str(uuid.getnode())
        self._fernet = None

    def _get_key(self) -> bytes:
        """
        Generate encryption key from machine ID
        Key is derived using PBKDF2 for better security
        """
        # Use machine ID as password
        password = self.machine_id.encode()
        salt = b'pyportman_salt'  # Fixed salt for consistency across restarts

        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
        )
        key = base64.urlsafe_b64encode(kdf.derive(password))
        return key

    @property
    def fernet(self) -> Fernet:
        """Get or create Fernet instance"""
        if self._fernet is None:
            key = self._get_key()
            self._fernet = Fernet(key)
        return self._fernet

    def encrypt(self, plaintext: str) -> str:
        """
        Encrypt plaintext string

        Args:
            plaintext: String to encrypt

        Returns:
            Encrypted string (base64 encoded)
        """
        if not plaintext:
            return ""

        encrypted = self.fernet.encrypt(plaintext.encode())
        return base64.urlsafe_b64encode(encrypted).decode()

    def decrypt(self, encrypted_text: str) -> str:
        """
        Decrypt encrypted string

        Args:
            encrypted_text: Encrypted string (base64 encoded)

        Returns:
            Decrypted plaintext string
        """
        if not encrypted_text:
            return ""

        try:
            encrypted_bytes = base64.urlsafe_b64decode(encrypted_text.encode())
            decrypted = self.fernet.decrypt(encrypted_bytes)
            return decrypted.decode()
        except Exception as e:
            raise ValueError(f"Decryption failed: {e}")

    def encrypt_dict(self, data: dict, keys: list) -> dict:
        """
        Encrypt specific keys in a dictionary

        Args:
            data: Dictionary to encrypt
            keys: List of keys to encrypt

        Returns:
            Dictionary with encrypted values
        """
        result = data.copy()
        for key in keys:
            if key in result and result[key]:
                result[key] = self.encrypt(str(result[key]))
        return result

    def decrypt_dict(self, data: dict, keys: list) -> dict:
        """
        Decrypt specific keys in a dictionary

        Args:
            data: Dictionary to decrypt
            keys: List of keys to decrypt

        Returns:
            Dictionary with decrypted values
        """
        result = data.copy()
        for key in keys:
            if key in result and result[key]:
                try:
                    result[key] = self.decrypt(result[key])
                except Exception:
                    # Keep original if decryption fails
                    pass
        return result


# Global encryption manager instance
_encryption_manager = None


def get_encryption_manager() -> EncryptionManager:
    """Get the global encryption manager instance"""
    global _encryption_manager
    if _encryption_manager is None:
        _encryption_manager = EncryptionManager()
    return _encryption_manager


def encrypt(text: str) -> str:
    """Convenience function to encrypt text"""
    return get_encryption_manager().encrypt(text)


def decrypt(encrypted_text: str) -> str:
    """Convenience function to decrypt text"""
    return get_encryption_manager().decrypt(encrypted_text)


if __name__ == "__main__":
    # Test encryption/decryption
    manager = EncryptionManager()

    test_data = "my_secret_password_123"
    print(f"Original: {test_data}")

    encrypted = manager.encrypt(test_data)
    print(f"Encrypted: {encrypted}")

    decrypted = manager.decrypt(encrypted)
    print(f"Decrypted: {decrypted}")

    assert decrypted == test_data, "Decryption failed!"
    print("Encryption test passed!")
