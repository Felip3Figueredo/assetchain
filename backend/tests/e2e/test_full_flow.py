"""End-to-end: the 13-step demo scenario against a real local EVM chain."""
import pytest
from cryptography.fernet import Fernet
from fastapi.testclient import TestClient

from app.core.db import Base
from app.main import create_app
from app.seed import run_seed


@pytest.fixture()
def api(settings):
    settings.fernet_key = Fernet.generate_key().decode()
    app = create_app(settings)
    Base.metadata.create_all(app.state.engine)
    with app.state.session_factory() as s:
        run_seed(s, app.state.gateway, settings)
    with TestClient(app) as c:
        yield c


def test_usina_solar_alpha_end_to_end(api):
    # 1-3: chain is up and the backend is connected to it
    status = api.get("/api/blockchain/status").json()
    assert status["connected"] and status["chain_id"] == api.app.state.settings.chain_id
    # 4-5: seeded asset -> approve
    asset = next(a for a in api.get("/api/assets").json() if a["asset_code"] == "ASSET-001")
    assert asset["status"] == "DRAFT" and asset["token_supply"] == 10_000_000
    assert api.post(f"/api/assets/{asset['id']}/approve").json()["status"] == "APPROVED"
    # 6-7: deploy ERC-20 and mint 10M tokens
    dep = api.post(f"/api/tokenization/{asset['id']}/deploy", headers={"Idempotency-Key": "e2e"}).json()
    assert dep["status"] == "TOKENIZED"
    assert api.get(f"/api/tokenization/{asset['id']}/supply").json()["total_supply"] == "10000000"
    # 8-9: wallets A (treasury) -> B, 100k tokens
    wallets = {w["label"]: w["address"] for w in api.get("/api/wallets").json()}
    a, b = wallets["Tesouraria"], wallets["Carteira B"]
    tx = api.post("/api/transactions/transfer", headers={"Idempotency-Key": "e2e-t"}, json={
        "asset_id": asset["id"], "from_address": a, "to_address": b, "amount": "100000"}).json()
    assert tx["status"] == "CONFIRMED"
    # 10: balances
    bal = lambda addr: api.get(f"/api/wallets/{addr}/balances").json()[0]["balance"]
    assert bal(a) == "9900000" and bal(b) == "100000"
    # 11-12: hash and block
    chain_tx = api.get(f"/api/blockchain/transactions/{tx['tx_hash']}").json()
    assert chain_tx["block_number"] == tx["block_number"] and chain_tx["success"] is True
    assert api.get("/api/blockchain/blocks/latest").json()["number"] >= tx["block_number"]
    # 13: everything the dashboard needs is queryable
    stats = api.get("/api/dashboard/stats").json()
    assert stats["tokenized_assets"] == 1 and stats["total_tokens_issued"] == "10000000"
    assert stats["wallets"] == 3 and stats["transactions"] >= 3
    holders = api.get(f"/api/tokenization/{asset['id']}/holders").json()
    assert [h["balance"] for h in holders] == ["9900000", "100000"]
