"""
crypto_utils.py

Encrypts the message before it ever gets hidden in the image, so even if
someone extracts the raw bits, they've still got nothing readable without
the password.

Uses Fernet (from the `cryptography` library) for the actual encryption,
this is deliberately not hand-rolled. "Never roll your own crypto" is a
real, widely repeated principle, the correct move as a developer is using
a vetted library correctly, not writing cipher math from scratch.

The password itself is never used directly as the key. It's run through
PBKDF2 first, a function designed specifically to make brute-forcing a
password much slower. A random salt is generated per message and stored
alongside the ciphertext, so the same password never produces the same
key twice, which defends against precomputed rainbow-table style attacks.
"""

import os
import base64
from cryptography.fernet import Fernet, InvalidToken
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

SALT_SIZE = 16
PBKDF2_ITERATIONS = 390_000  # OWASP's current recommended minimum for PBKDF2-SHA256


def _derive_key(password: str, salt: bytes) -> bytes:
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=PBKDF2_ITERATIONS,
    )
    return base64.urlsafe_b64encode(kdf.derive(password.encode()))


def encrypt_message(message: str, password: str) -> bytes:
    """Returns salt + ciphertext as one blob, ready to be embedded."""
    salt = os.urandom(SALT_SIZE)
    key = _derive_key(password, salt)
    token = Fernet(key).encrypt(message.encode())
    return salt + token


def decrypt_message(blob: bytes, password: str) -> str:
    """Reverses encrypt_message. Raises ValueError on a wrong password."""
    salt, token = blob[:SALT_SIZE], blob[SALT_SIZE:]
    key = _derive_key(password, salt)
    try:
        return Fernet(key).decrypt(token).decode()
    except InvalidToken:
        raise ValueError("Wrong password, or this isn't a message this tool encrypted.")
