import pytest
from eth_account import Account

from app.blockchain.client import ChainClient
from app.blockchain.token import TokenGateway
from app.core.config import Settings
from app.core.errors import AppError
from tests.conftest import KEYS

CAP = 10_000_000 * 10**18


@pytest.fixture()
def gateway(settings):
    return TokenGateway(ChainClient(settings))


def _addr(i: int) -> str:
    return Account.from_key(KEYS[i]).address


def test_client_reports_network_and_latest_block(settings):
    client = ChainClient(settings)
    assert client.is_connected()
    assert client.network_info().chain_id == settings.chain_id
    assert client.latest_block().number >= 0


def test_deploy_mint_transfer_and_balances(gateway):
    deployed = gateway.deploy("Usina Solar Alpha", "SOLA", "ASSET-001", CAP)
    assert deployed.address.startswith("0x") and deployed.block >= 0
    mint_hash = gateway.mint(deployed.address, _addr(0), CAP)
    assert gateway.client.wait_receipt(mint_hash).success
    assert gateway.total_supply(deployed.address) == CAP

    amount = 100_000 * 10**18
    tx_hash = gateway.transfer(deployed.address, KEYS[0], _addr(1), amount)
    receipt = gateway.client.wait_receipt(tx_hash)
    assert receipt.success and receipt.block_number > deployed.block
    assert gateway.balance_of(deployed.address, _addr(1)) == amount
    assert gateway.balance_of(deployed.address, _addr(0)) == CAP - amount

    events = gateway.transfer_events(deployed.address, deployed.block)
    assert any(e.to_address == _addr(1) and e.amount == amount for e in events)

    info = gateway.client.get_transaction(tx_hash)
    assert info is not None and info.block_number == receipt.block_number


def test_transfer_without_balance_is_contract_revert(gateway):
    deployed = gateway.deploy("T", "T", "ASSET-X", CAP)
    with pytest.raises(AppError) as exc:
        gateway.transfer(deployed.address, KEYS[2], _addr(1), 1)
    assert exc.value.code == "CONTRACT_REVERT"


def test_rpc_unreachable_maps_to_503():
    s = Settings(_env_file=None, rpc_url="http://127.0.0.1:1", database_url="sqlite://", fernet_key="")
    with pytest.raises(AppError) as exc:
        ChainClient(s).latest_block()
    assert exc.value.status_code == 503 and exc.value.code == "RPC_UNAVAILABLE"
