import pytest
from cryptography.fernet import Fernet

from app.core.errors import AppError
from app.core.security import decrypt_key, encrypt_key


def test_encrypt_key_roundtrip_and_not_plaintext():
    fk = Fernet.generate_key().decode()
    plain = "0x" + "ab" * 32
    token = encrypt_key(plain, fk)
    assert plain not in token
    assert decrypt_key(token, fk) == plain


def test_invalid_fernet_key_raises_clear_error():
    with pytest.raises(AppError) as exc:
        encrypt_key("0x01", "not-a-valid-key")
    assert exc.value.code == "INVALID_ENCRYPTION_KEY"
