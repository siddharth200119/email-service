"""Tests for encryption utility"""
import pytest
from src.utils.encryption import encrypt, decrypt


class TestEncryption:
    """Test encryption and decryption functions"""

    def test_encrypt_decrypt_roundtrip(self):
        """Test that encrypting then decrypting returns original value"""
        original = "my_secret_password"
        encrypted = encrypt(original)
        decrypted = decrypt(encrypted)
        
        assert decrypted == original
        assert encrypted != original  # Should be different

    def test_encrypt_produces_different_outputs(self):
        """Test that encrypting same value twice produces different ciphertexts"""
        original = "same_password"
        encrypted1 = encrypt(original)
        encrypted2 = encrypt(original)
        
        # Fernet uses random IV, so same plaintext = different ciphertext
        assert encrypted1 != encrypted2
        # But both decrypt to the same value
        assert decrypt(encrypted1) == decrypt(encrypted2) == original

    def test_encrypt_empty_string_returns_empty(self):
        """Test that empty string is handled gracefully"""
        result = encrypt("")
        assert result == ""

    def test_decrypt_empty_string_returns_empty(self):
        """Test that empty string decryption is handled gracefully"""
        result = decrypt("")
        assert result == ""

    def test_encrypt_none_returns_none(self):
        """Test that None is handled gracefully"""
        result = encrypt(None)
        assert result is None

    def test_decrypt_none_returns_none(self):
        """Test that None decryption is handled gracefully"""
        result = decrypt(None)
        assert result is None

    def test_encrypt_special_characters(self):
        """Test encryption with special characters"""
        original = "p@ssw0rd!#$%^&*()_+{}|:<>?"
        encrypted = encrypt(original)
        decrypted = decrypt(encrypted)
        
        assert decrypted == original

    def test_encrypt_unicode(self):
        """Test encryption with unicode characters"""
        original = "пароль密码🔐"
        encrypted = encrypt(original)
        decrypted = decrypt(encrypted)
        
        assert decrypted == original

    def test_decrypt_invalid_ciphertext_raises_error(self):
        """Test that decrypting invalid ciphertext raises an error"""
        with pytest.raises(Exception):
            decrypt("invalid_not_base64_ciphertext")
