from __future__ import annotations

import os

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from sshine.exceptions import DecryptionError

_NONCE_SIZE = 12  # bytes, GCM standard


def encrypt(plaintext: bytes, key: bytes) -> tuple[bytes, bytes]:
    """
    Encrypt *plaintext* with AES-256-GCM using *key* (must be 32 bytes).

    Returns ``(nonce, ciphertext_with_tag)`` where the 16-byte GCM tag is
    appended to *ciphertext_with_tag* by the ``cryptography`` library.
    """
    nonce = os.urandom(_NONCE_SIZE)
    aesgcm = AESGCM(key)
    ciphertext_with_tag = aesgcm.encrypt(nonce, plaintext, None)
    return nonce, ciphertext_with_tag


def decrypt(nonce: bytes, ciphertext_with_tag: bytes, key: bytes) -> bytes:
    """
    Decrypt and authenticate *ciphertext_with_tag* produced by :func:`encrypt`.

    Raises :class:`~sshine.exceptions.DecryptionError` on authentication
    failure (wrong key or corrupted data).
    """
    aesgcm = AESGCM(key)
    try:
        return aesgcm.decrypt(nonce, ciphertext_with_tag, None)
    except Exception as exc:
        raise DecryptionError("AES-GCM decryption failed — wrong key or corrupted data") from exc
