from fastapi.testclient import TestClient
from cryptography.fernet import Fernet

from app.core.db import Base
from app.main import create_app
from app.models import Asset, ChainTransaction, TokenContract, Wallet
from app.services.health import reconcile_chain_reset
from tests.integration.conftest import create_approved, tokenize


def _make_stale(client):
    aid = create_approved(client)
    tokenize(client, aid)
    s = client.app_state.session_factory()
    s.query(TokenContract).one().address = "0x000000000000000000000000000000000000dEaD"
    s.commit()
    return s


def test_chain_reset_is_detected_and_left_alone_by_default(client):
    s = _make_stale(client)
    assert reconcile_chain_reset(s, client.app_state.gateway, auto_reset=False) == ["ASSET-001"]
    assert s.query(Asset).count() == 1


def test_chain_reset_can_self_heal_in_dev_by_clearing_stale_app_data(client):
    s = _make_stale(client)
    assert reconcile_chain_reset(s, client.app_state.gateway, auto_reset=True) == ["ASSET-001"]
    for model in (Asset, TokenContract, ChainTransaction, Wallet):
        assert s.query(model).count() == 0


def _app(settings, key):
    settings.fernet_key = Fernet.generate_key().decode()
    settings.api_key = key
    app = create_app(settings)
    Base.metadata.create_all(app.state.engine)
    return TestClient(app)


def test_api_key_protects_the_api_when_configured(settings):
    with _app(settings, "s3cret") as c:
        assert c.get("/api/assets").status_code == 401
        assert c.get("/api/assets", headers={"X-API-Key": "wrong"}).status_code == 401
        assert c.get("/api/assets", headers={"X-API-Key": "s3cret"}).status_code == 200
        assert c.get("/api/health").status_code == 200  # liveness stays open


def test_api_is_open_when_no_key_is_configured(settings):
    with _app(settings, "") as c:
        assert c.get("/api/assets").status_code == 200
