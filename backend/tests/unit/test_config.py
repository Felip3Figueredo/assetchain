from app.core.config import Settings


def test_settings_read_env(monkeypatch):
    monkeypatch.setenv("RPC_URL", "http://chain:8545")
    monkeypatch.setenv("CHAIN_ID", "31337")
    monkeypatch.setenv("DATABASE_URL", "sqlite://")
    s = Settings(_env_file=None)
    assert s.rpc_url == "http://chain:8545"
    assert s.chain_id == 31337
    assert s.database_url == "sqlite://"
