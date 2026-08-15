import os
from cryptography.fernet import Fernet
import base64

# In production, this must be a securely managed 32-byte url-safe base64-encoded key
# For MVP, we fall back to a deterministic one if not set, but warn strongly.
_SECRET = os.getenv("KOKKOPI_ENCRYPTION_KEY", "uOqQ1L46vP8j0WJXZ1X4rT3N0A8_yqM_1yYm_8Wf0Jk=")
cipher_suite = Fernet(_SECRET.encode())

def encrypt_secret(plaintext: str) -> str:
    """Encrypts a plaintext secret."""
    return cipher_suite.encrypt(plaintext.encode('utf-8')).decode('utf-8')

def decrypt_secret(ciphertext: str) -> str:
    """Decrypts a ciphertext secret."""
    return cipher_suite.decrypt(ciphertext.encode('utf-8')).decode('utf-8')
