#!/usr/bin/env python3
"""
Security utilities for OpenStack Toolbox.

This module provides encryption/decryption for sensitive configuration data
like SMTP passwords using the cryptography library with Fernet symmetric encryption.
"""

import base64
import os
from pathlib import Path
from typing import Optional

from cryptography.fernet import Fernet, InvalidToken
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2

from .exceptions import ConfigurationError


class SecureConfig:
    """Handle encryption and decryption of sensitive configuration data."""

    def __init__(self, config_dir: Optional[Path] = None):
        """
        Initialize secure configuration handler.

        Args:
            config_dir: Directory to store encryption key
                       (default: ~/.config/openstack-toolbox)
        """
        if config_dir is None:
            config_dir = Path.home() / ".config" / "openstack-toolbox"

        self.config_dir = Path(config_dir)
        self.config_dir.mkdir(parents=True, exist_ok=True)
        self.key_file = self.config_dir / ".encryption_key"
        self._cipher = None

    def _get_or_create_key(self) -> bytes:
        """
        Get existing encryption key or create a new one.

        Returns:
            Encryption key as bytes

        Raises:
            ConfigurationError: If key file operations fail
        """
        try:
            if self.key_file.exists():
                with open(self.key_file, "rb") as f:
                    return f.read()
            else:
                # Generate new key
                key = Fernet.generate_key()
                # Save with restricted permissions
                with open(self.key_file, "wb") as f:
                    f.write(key)
                # Set file permissions to 600 (read/write for owner only)
                self.key_file.chmod(0o600)
                return key
        except (OSError, IOError) as e:
            raise ConfigurationError(
                f"Failed to access encryption key file: {e}"
            ) from e

    def _get_cipher(self) -> Fernet:
        """
        Get or create Fernet cipher instance.

        Returns:
            Fernet cipher instance
        """
        if self._cipher is None:
            key = self._get_or_create_key()
            self._cipher = Fernet(key)
        return self._cipher

    def encrypt(self, plaintext: str) -> str:
        """
        Encrypt a string.

        Args:
            plaintext: String to encrypt

        Returns:
            Base64-encoded encrypted string

        Examples:
            >>> secure = SecureConfig()
            >>> encrypted = secure.encrypt("my_password")
            >>> isinstance(encrypted, str)
            True
        """
        cipher = self._get_cipher()
        encrypted_bytes = cipher.encrypt(plaintext.encode())
        return base64.b64encode(encrypted_bytes).decode()

    def decrypt(self, encrypted: str) -> str:
        """
        Decrypt an encrypted string.

        Args:
            encrypted: Base64-encoded encrypted string

        Returns:
            Decrypted plaintext string

        Raises:
            ConfigurationError: If decryption fails

        Examples:
            >>> secure = SecureConfig()
            >>> encrypted = secure.encrypt("my_password")
            >>> decrypted = secure.decrypt(encrypted)
            >>> decrypted == "my_password"
            True
        """
        try:
            cipher = self._get_cipher()
            encrypted_bytes = base64.b64decode(encrypted.encode())
            decrypted_bytes = cipher.decrypt(encrypted_bytes)
            return decrypted_bytes.decode()
        except (InvalidToken, ValueError) as e:
            raise ConfigurationError(
                "Failed to decrypt data. The encryption key may have changed."
            ) from e

    def is_encrypted(self, value: str) -> bool:
        """
        Check if a value appears to be encrypted.

        Args:
            value: String to check

        Returns:
            True if value looks encrypted, False otherwise

        Examples:
            >>> secure = SecureConfig()
            >>> secure.is_encrypted("plaintext")
            False
            >>> encrypted = secure.encrypt("password")
            >>> secure.is_encrypted(encrypted)
            True
        """
        try:
            # Try to decode as base64 and decrypt
            base64.b64decode(value.encode())
            # If it's valid base64, try to decrypt
            self.decrypt(value)
            return True
        except Exception:
            return False


def generate_salt() -> bytes:
    """
    Generate a random salt for key derivation.

    Returns:
        Random 16-byte salt

    Examples:
        >>> salt = generate_salt()
        >>> len(salt)
        16
    """
    return os.urandom(16)


def derive_key_from_password(password: str, salt: bytes) -> bytes:
    """
    Derive an encryption key from a password using PBKDF2.

    Args:
        password: User password
        salt: Random salt bytes

    Returns:
        Derived 32-byte key

    Examples:
        >>> salt = generate_salt()
        >>> key = derive_key_from_password("my_password", salt)
        >>> len(key)
        32
    """
    kdf = PBKDF2(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=100000,
    )
    return kdf.derive(password.encode())
