from app.models import ChainTransaction, IndexedEvent, TxStatus
from app.services.indexer import Indexer
from tests.conftest import KEYS
from tests.integration.conftest import create_approved, tokenize
from eth_account import Account


def _session(client):
    return client.app_state.session_factory()


def test_sync_indexes_onchain_transfer_made_outside_the_api(client):
    aid = create_approved(client)
    contract = tokenize(client, aid).json()["contract_address"]
    gw = client.app_state.gateway
    outsider = Account.from_key(KEYS[2]).address
    h = gw.transfer(contract, KEYS[0], outsider, 5 * 10**18)  # bypasses the API entirely
    gw.client.wait_receipt(h)

    s = _session(client)
    assert s.query(ChainTransaction).filter_by(tx_hash=h).count() == 0
    assert Indexer(s, gw).sync(aid) >= 1
    row = s.query(ChainTransaction).filter_by(tx_hash=h).one()
    assert row.status == TxStatus.CONFIRMED and row.block_number is not None
    assert s.query(IndexedEvent).filter_by(tx_hash=h).count() == 1
    assert Indexer(s, gw).sync(aid) == 0  # idempotent


def test_sync_settles_pending_transaction_with_receipt(client):
    aid = create_approved(client)
    contract = tokenize(client, aid).json()["contract_address"]
    gw = client.app_state.gateway
    h = gw.transfer(contract, KEYS[0], Account.from_key(KEYS[1]).address, 10**18)
    gw.client.wait_receipt(h)
    s = _session(client)
    s.add(ChainTransaction(tx_hash=h, asset_id=aid, from_address="0x1", to_address="0x2",
                           amount=10**18, status=TxStatus.PENDING))
    s.commit()
    Indexer(s, gw).sync(aid)
    assert s.query(ChainTransaction).filter_by(tx_hash=h).one().status == TxStatus.CONFIRMED
