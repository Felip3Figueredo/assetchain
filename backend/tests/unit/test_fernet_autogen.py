import os
import stat

from cryptography.fernet import Fernet

from app.core.config import Settings
from app.core.security import ensure_fernet_key


def test_generates_and_persists_a_private_key_when_none_is_configured(tmp_path):
    f = tmp_path / "data" / "fernet.key"
    s = Settings(_env_file=None, fernet_key="", fernet_key_file=str(f))
    key = ensure_fernet_key(s)
    Fernet(key.encode())  # valid
    assert f.read_text().strip() == key and s.fernet_key == key
    assert stat.S_IMODE(os.stat(f).st_mode) == 0o600
    s2 = Settings(_env_file=None, fernet_key="", fernet_key_file=str(f))
    assert ensure_fernet_key(s2) == key  # stable across restarts


def test_environment_key_wins_over_file(tmp_path):
    env_key = Fernet.generate_key().decode()
    s = Settings(_env_file=None, fernet_key=env_key, fernet_key_file=str(tmp_path / "x.key"))
    assert ensure_fernet_key(s) == env_key
    assert not (tmp_path / "x.key").exists()
