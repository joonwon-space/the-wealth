"""AES-256-GCM 기반 암호화/복호화 유틸.

마스터 키: `ENCRYPTION_MASTER_KEY` 환경변수 (32바이트 hex 문자열).
암호문 포맷: base64(nonce[12] + ciphertext + tag[16])
"""
from __future__ import annotations

import base64
import os

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from app.core.config import settings


def _get_key() -> bytes:
    key_hex = settings.ENCRYPTION_MASTER_KEY
    key_bytes = bytes.fromhex(key_hex) if len(key_hex) == 64 else key_hex.encode()[:32].ljust(32, b"\x00")
    return key_bytes


def encrypt(plaintext: str) -> str:
    """평문 문자열을 AES-256-GCM으로 암호화하여 base64 문자열 반환."""
    aesgcm = AESGCM(_get_key())
    nonce = os.urandom(12)
    ciphertext = aesgcm.encrypt(nonce, plaintext.encode(), None)
    return base64.b64encode(nonce + ciphertext).decode()


def decrypt(token: str) -> str:
    """base64 암호문을 복호화하여 평문 반환."""
    raw = base64.b64decode(token.encode())
    nonce, ciphertext = raw[:12], raw[12:]
    aesgcm = AESGCM(_get_key())
    return aesgcm.decrypt(nonce, ciphertext, None).decode()
