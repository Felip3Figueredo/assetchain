from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from eth_account import Account
from web3 import Web3

from app.blockchain.client import ChainClient, rpc_guard
from app.core.errors import AppError


@dataclass(frozen=True)
class DeployResult:
    address: str
    tx_hash: str
    block: int


@dataclass(frozen=True)
class TransferEvent:
    tx_hash: str
    log_index: int
    block_number: int
    from_address: str
    to_address: str
    amount: int


class TokenGateway:
    """Web3.py access to AssetToken contracts (one contract per asset)."""

    def __init__(self, client: ChainClient) -> None:
        self.client = client
        self.w3 = client.w3
        path = Path(client.settings.artifact_path)
        if not path.exists():
            raise AppError(500, "ARTIFACT_MISSING", f"Contract artifact not found: {path}")
        artifact = json.loads(path.read_text())
        self.abi = artifact["abi"]
        self.bytecode = artifact["bytecode"]
        self._deployer_key = client.settings.deployer_private_key
        self.deployer_address = Account.from_key(self._deployer_key).address

    def _contract(self, address: str):
        return self.w3.eth.contract(address=Web3.to_checksum_address(address), abi=self.abi)

    @rpc_guard
    def deploy_send(self, name: str, symbol: str, asset_id: str, cap_wei: int) -> str:
        """Broadcast the deployment and return its hash (NOT a confirmation)."""
        factory = self.w3.eth.contract(abi=self.abi, bytecode=self.bytecode)
        tx = factory.constructor(name, symbol, asset_id, cap_wei, self.deployer_address).build_transaction(
            {"from": self.deployer_address, "gas": 1, "gasPrice": 1, "nonce": 0,
             "chainId": self.client.settings.chain_id})
        for k in ("nonce", "gas", "gasPrice"):
            tx.pop(k, None)
        return self.client.send_signed(tx, self._deployer_key)

    def deploy(self, name: str, symbol: str, asset_id: str, cap_wei: int) -> DeployResult:
        tx_hash = self.deploy_send(name, symbol, asset_id, cap_wei)
        receipt = self.client.wait_receipt(tx_hash)
        if not receipt.success or not receipt.contract_address:
            raise AppError(409, "DEPLOY_FAILED", "Contract deployment reverted")
        return DeployResult(address=receipt.contract_address, tx_hash=tx_hash, block=receipt.block_number)

    @rpc_guard
    def mint(self, contract_address: str, to: str, amount_wei: int) -> str:
        data = self._contract(contract_address).functions.mint(Web3.to_checksum_address(to), amount_wei)
        tx = data.build_transaction({"from": self.deployer_address, "gas": 1, "gasPrice": 1, "nonce": 0,
                                     "chainId": self.client.settings.chain_id})
        for k in ("nonce", "gas", "gasPrice"):
            tx.pop(k, None)
        return self.client.send_signed(tx, self._deployer_key)

    @rpc_guard
    def transfer(self, contract_address: str, from_key: str, to: str, amount_wei: int) -> str:
        sender = Account.from_key(from_key).address
        fn = self._contract(contract_address).functions.transfer(Web3.to_checksum_address(to), amount_wei)
        tx = fn.build_transaction({"from": sender, "gas": 1, "gasPrice": 1, "nonce": 0,
                                   "chainId": self.client.settings.chain_id})
        for k in ("nonce", "gas", "gasPrice"):
            tx.pop(k, None)
        return self.client.send_signed(tx, from_key)

    @rpc_guard
    def balance_of(self, contract_address: str, holder: str) -> int:
        return self._contract(contract_address).functions.balanceOf(Web3.to_checksum_address(holder)).call()

    @rpc_guard
    def total_supply(self, contract_address: str) -> int:
        return self._contract(contract_address).functions.totalSupply().call()

    @rpc_guard
    def transfer_events(self, contract_address: str, from_block: int) -> list[TransferEvent]:
        logs = self._contract(contract_address).events.Transfer().get_logs(from_block=from_block)
        return [
            TransferEvent(
                tx_hash=e["transactionHash"].to_0x_hex(), log_index=e["logIndex"], block_number=e["blockNumber"],
                from_address=e["args"]["from"], to_address=e["args"]["to"], amount=e["args"]["value"],
            )
            for e in logs
        ]
