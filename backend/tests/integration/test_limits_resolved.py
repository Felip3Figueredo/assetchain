import threading

import pytest
from eth_account import Account

from app.core.errors import AppError
from app.models import ChainTransaction, TokenContract, TxStatus, Wallet
from tests.conftest import KEYS
from tests.integration.conftest import create_approved, tokenize


def test_concurrent_sends_from_one_account_do_not_collide_on_nonce(client):
    gw = client.app_state.gateway
    errors: list[Exception] = []
    hashes: list[str] = []
    dest = Account.from_key(KEYS[1]).address

    def send():
        try:
            hashes.append(gw.client.send_signed({"to": dest, "value": 1}, KEYS[2]))
        except Exception as exc:  # noqa: BLE001
            errors.append(exc)

    threads = [threading.Thread(target=send) for _ in range(8)]
    [t.start() for t in threads]
    [t.join() for t in threads]
    assert errors == [] and len(set(hashes)) == 8


def test_wallet_creation_with_rpc_down_leaves_no_unfunded_wallet(client):
    client.app_state.gateway.client.w3.provider.endpoint_uri = "http://127.0.0.1:1"
    assert client.post("/api/wallets", json={"label": "X"}).status_code == 503
    s = client.app_state.session_factory()
    assert s.query(Wallet).filter_by(label="X").count() == 0


def _fail_nth_receipt(client, monkeypatch, nth: int):
    real = client.app_state.gateway.client.wait_receipt
    calls = {"n": 0}

    def flaky(tx_hash, timeout=None):
        calls["n"] += 1
        if calls["n"] == nth:
            raise AppError(504, "RPC_TIMEOUT", "Timed out waiting for transaction receipt")
        return real(tx_hash, timeout)

    monkeypatch.setattr(client.app_state.gateway.client, "wait_receipt", flaky)


def _wait_until_mined(client, kind: str):
    """A simulated timeout returns instantly; real chains (e.g. 2s QBFT blocks) need a moment to mine."""
    import time

    s = client.app_state.session_factory()
    row = s.query(ChainTransaction).filter_by(kind=kind, status=TxStatus.PENDING).one()
    for _ in range(40):
        if client.app_state.gateway.client.get_receipt(row.tx_hash):
            return
        time.sleep(0.5)
    raise AssertionError("transaction was never mined")


def test_deploy_receipt_timeout_then_retry_yields_exactly_one_contract(client, monkeypatch):
    aid = create_approved(client)
    _fail_nth_receipt(client, monkeypatch, 1)  # first receipt wait = the deploy
    assert tokenize(client, aid, "t1").status_code == 504
    _wait_until_mined(client, "DEPLOY")
    r = tokenize(client, aid, "t1")
    assert r.status_code == 200 and r.json()["status"] == "TOKENIZED"
    s = client.app_state.session_factory()
    assert s.query(TokenContract).filter_by(asset_id=aid).count() == 1
    assert client.get(f"/api/tokenization/{aid}/supply").json()["total_supply"] == "10000000"


def test_mint_receipt_timeout_then_retry_does_not_report_failure(client, monkeypatch):
    aid = create_approved(client)
    _fail_nth_receipt(client, monkeypatch, 2)  # 1st = deploy, 2nd = mint
    assert tokenize(client, aid, "m1").status_code == 504
    _wait_until_mined(client, "MINT")
    r = tokenize(client, aid, "m1")
    assert r.status_code == 200, r.text
    s = client.app_state.session_factory()
    mints = s.query(ChainTransaction).filter_by(asset_id=aid, kind="MINT").all()
    assert len(mints) == 1 and mints[0].status == TxStatus.CONFIRMED
    assert client.get(f"/api/tokenization/{aid}/supply").json()["total_supply"] == "10000000"
