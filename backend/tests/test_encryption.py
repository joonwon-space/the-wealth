"""encryption 서비스 단위 테스트 — encrypt/decrypt 라운드트립."""
from __future__ import annotations

import pytest

from app.core.encryption import decrypt, encrypt


@pytest.mark.unit
class TestEncryption:
    def test_roundtrip(self) -> None:
        """encrypt → decrypt 라운드트립이 원본을 복원해야 한다."""
        plaintext = "PS7yzJfa3MLSuDcoKAPAjpsOIEY1P14pKeYp"
        encrypted = encrypt(plaintext)
        decrypted = decrypt(encrypted)
        assert decrypted == plaintext

    def test_different_ciphertexts(self) -> None:
        """같은 평문이라도 매번 다른 암호문이 생성되어야 한다 (random nonce)."""
        plaintext = "test-secret-key"
        enc1 = encrypt(plaintext)
        enc2 = encrypt(plaintext)
        assert enc1 != enc2
        assert decrypt(enc1) == plaintext
        assert decrypt(enc2) == plaintext

    def test_empty_string(self) -> None:
        """빈 문자열도 암호화/복호화 가능."""
        encrypted = encrypt("")
        assert decrypt(encrypted) == ""

    def test_unicode(self) -> None:
        """유니코드 문자열 암호화/복호화."""
        plaintext = "한국투자증권 앱키 테스트 🔑"
        encrypted = encrypt(plaintext)
        assert decrypt(encrypted) == plaintext

    def test_invalid_token_raises(self) -> None:
        """잘못된 토큰은 예외 발생."""
        with pytest.raises(Exception):
            decrypt("invalid-base64-token!!!")
