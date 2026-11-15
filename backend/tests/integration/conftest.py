import pytest
from cryptography.fernet import Fernet
from fastapi.testclient import TestClient

from app.core.db import Base
from app.main import create_app


@pytest.fixture()
def client(settings):
    settings.fernet_key = Fernet.generate_key().decode()
    app = create_app(settings)
    Base.metadata.create_all(app.state.engine)
    with TestClient(app) as c:
        c.app_state = app.state
        yield c


SOLAR = {
    "asset_code": "ASSET-001", "name": "Usina Solar Alpha", "category": "Energia renovável",
    "description": "Usina fotovoltaica fictícia", "estimated_value_brl": 10_000_000,
    "token_supply": 10_000_000, "token_price_brl": 1.0,
}


def create_approved(client, code="ASSET-001"):
    r = client.post("/api/assets", json={**SOLAR, "asset_code": code})
    assert r.status_code == 201, r.text
    aid = r.json()["id"]
    assert client.post(f"/api/assets/{aid}/approve").status_code == 200
    return aid


def tokenize(client, aid, key="deploy-1"):
    return client.post(f"/api/tokenization/{aid}/deploy", headers={"Idempotency-Key": key})
