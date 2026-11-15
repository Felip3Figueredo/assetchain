import os
from pathlib import Path

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


def ensure_fernet_key(settings) -> str:
    """Return the master key: env value wins; otherwise a per-install key is generated once and persisted (0600)."""
    if settings.fernet_key:
        return settings.fernet_key
    path = Path(settings.fernet_key_file)
    if path.exists():
        key = path.read_text().strip()
    else:
        path.parent.mkdir(parents=True, exist_ok=True)
        key = Fernet.generate_key().decode()
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(fd, "w") as fh:
            fh.write(key + "\n")
    settings.fernet_key = key
    return key
