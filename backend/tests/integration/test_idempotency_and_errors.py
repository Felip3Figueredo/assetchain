from sqlalchemy import BigInteger

from app.models import Asset, TokenContract
from app.services.transaction_service import TransactionService
from tests.integration.conftest import create_approved, tokenize


def _treasury_and_b(client):
    t = next(w for w in client.get("/api/wallets").json() if w["label"] == "Tesouraria")
    b = client.post("/api/wallets", json={"label": "B"}).json()
    return t["address"], b["address"]


def test_deploy_key_reused_for_another_asset_is_rejected_without_deploying(client):
    a1, a2 = create_approved(client, "ASSET-001"), create_approved(client, "ASSET-002")
    assert tokenize(client, a1, "k").status_code == 200
    r = tokenize(client, a2, "k")
    assert r.status_code == 409 and r.json()["error"]["code"] == "IDEMPOTENCY_KEY_REUSED"
    assert client.get(f"/api/assets/{a2}").json()["status"] == "APPROVED"
    s = client.app_state.session_factory()
    assert s.query(TokenContract).filter_by(asset_id=a2).count() == 0


def test_key_cannot_be_reused_for_a_different_operation_or_payload(client):
    aid = create_approved(client)
    tokenize(client, aid, "deploy-key")
    a, b = _treasury_and_b(client)
    base = {"asset_id": aid, "from_address": a, "to_address": b, "amount": "1"}
    r = client.post("/api/transactions/transfer", headers={"Idempotency-Key": "deploy-key"}, json=base)
    assert r.status_code == 409 and r.json()["error"]["code"] == "IDEMPOTENCY_KEY_REUSED"
    assert client.post("/api/transactions/transfer", headers={"Idempotency-Key": "x2"}, json=base).status_code == 201
    r = client.post("/api/transactions/transfer", headers={"Idempotency-Key": "x2"}, json={**base, "amount": "999"})
    assert r.status_code == 409 and r.json()["error"]["code"] == "IDEMPOTENCY_KEY_REUSED"


def test_deploy_can_be_retried_with_same_key_after_rpc_failure(client):
    aid = create_approved(client)
    gw = client.app_state.gateway
    good = gw.client.w3.provider.endpoint_uri
    gw.client.w3.provider.endpoint_uri = "http://127.0.0.1:1"
    assert tokenize(client, aid, "retry").status_code == 503
    gw.client.w3.provider.endpoint_uri = good
    r = tokenize(client, aid, "retry")
    assert r.status_code == 200 and r.json()["status"] == "TOKENIZED"


def test_pending_deploy_blocks_a_concurrent_deploy(client):
    aid = create_approved(client)
    from app.models import ChainTransaction, TxStatus
    s = client.app_state.session_factory()
    s.add(ChainTransaction(asset_id=aid, kind="DEPLOY", from_address="0x1", to_address="0x2", amount=0,
                           status=TxStatus.PENDING))
    s.commit()
    r = tokenize(client, aid, "other")
    assert r.status_code == 409 and r.json()["error"]["code"] == "DEPLOY_IN_PROGRESS"


def test_more_than_18_decimals_is_422(client):
    aid = create_approved(client)
    tokenize(client, aid)
    a, b = _treasury_and_b(client)
    r = client.post("/api/transactions/transfer", json={
        "asset_id": aid, "from_address": a, "to_address": b, "amount": "0.0000000000000000001"})
    assert r.status_code == 422


def test_transfer_with_rpc_down_is_503_and_leaves_no_record(client):
    aid = create_approved(client)
    tokenize(client, aid)
    a, b = _treasury_and_b(client)
    before = len(client.get("/api/transactions").json())
    client.app_state.gateway.client.w3.provider.endpoint_uri = "http://127.0.0.1:1"
    r = client.post("/api/transactions/transfer", headers={"Idempotency-Key": "down"}, json={
        "asset_id": aid, "from_address": a, "to_address": b, "amount": "1"})
    assert r.status_code == 503
    s = client.app_state.session_factory()
    from app.models import ChainTransaction
    assert s.query(ChainTransaction).filter_by(idempotency_key="down").count() == 0
    del before


def test_wallet_detail_with_rpc_down_is_503(client):
    a, _ = _treasury_and_b(client)
    client.app_state.gateway.client.w3.provider.endpoint_uri = "http://127.0.0.1:1"
    assert client.get(f"/api/wallets/{a}").status_code == 503


def test_successful_transfer_is_not_reported_as_failure_when_post_sync_fails(client, monkeypatch):
    from app.core.errors import AppError
    aid = create_approved(client)
    tokenize(client, aid)
    a, b = _treasury_and_b(client)

    def boom(self, asset_id):
        raise AppError(503, "RPC_UNAVAILABLE", "down")

    monkeypatch.setattr("app.services.transaction_service.Indexer.sync", boom)
    r = client.post("/api/transactions/transfer", json={"asset_id": aid, "from_address": a, "to_address": b, "amount": "2"})
    assert r.status_code == 201 and r.json()["status"] == "CONFIRMED"


def test_token_supply_column_fits_values_above_int32():
    assert isinstance(Asset.__table__.c.token_supply.type, BigInteger)
