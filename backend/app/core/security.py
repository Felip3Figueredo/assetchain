from cryptography.fernet import Fernet, InvalidToken

from app.core.errors import AppError


def _fernet(key: str) -> Fernet:
    try:
        return Fernet(key.encode())
    except (ValueError, TypeError) as exc:
        raise AppError(500, "INVALID_ENCRYPTION_KEY", "FERNET_KEY is missing or invalid") from exc


def encrypt_key(plain: str, fernet_key: str) -> str:
    return _fernet(fernet_key).encrypt(plain.encode()).decode()


def decrypt_key(token: str, fernet_key: str) -> str:
    try:
        return _fernet(fernet_key).decrypt(token.encode()).decode()
    except InvalidToken as exc:
        raise AppError(500, "DECRYPT_FAILED", "Could not decrypt wallet key") from exc
