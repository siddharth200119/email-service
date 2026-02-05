"""
Encryption utilities for sensitive data using Fernet symmetric encryption.
"""
import os
from cryptography.fernet import Fernet
from src.utils import logger

_fernet = None


def _get_fernet() -> Fernet:
    """Get or initialize the Fernet instance."""
    global _fernet
    if _fernet is None:
        # Load key lazily to ensure dotenv has been called
        encryption_key = os.getenv("ENCRYPTION_SECRET")
        if not encryption_key:
            raise ValueError("ENCRYPTION_SECRET environment variable is not set")
        _fernet = Fernet(encryption_key.encode())
    return _fernet


def encrypt(plaintext: str) -> str:
    """
    Encrypt a plaintext string.
    Returns the encrypted value as a base64-encoded string.
    """
    if not plaintext:
        return plaintext
    try:
        fernet = _get_fernet()
        encrypted = fernet.encrypt(plaintext.encode())
        return encrypted.decode()
    except Exception as e:
        logger.error(f"Encryption error: {e}")
        raise


def decrypt(ciphertext: str) -> str:
    """
    Decrypt an encrypted string.
    Returns the original plaintext.
    """
    if not ciphertext:
        return ciphertext
    try:
        fernet = _get_fernet()
        decrypted = fernet.decrypt(ciphertext.encode())
        return decrypted.decode()
    except Exception as e:
        logger.error(f"Decryption error: {e}")
        raise
