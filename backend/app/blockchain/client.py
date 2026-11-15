from __future__ import annotations

import functools
from dataclasses import dataclass
from typing import Callable, TypeVar

import requests
from web3 import Web3
from web3.exceptions import ContractLogicError, TimeExhausted, Web3Exception

from app.core.config import Settings
from app.core.errors import AppError
from app.core.logging import get_logger

log = get_logger("chain")
T = TypeVar("T")


@dataclass(frozen=True)
class NetworkInfo:
    chain_id: int
    client_version: str
    block_number: int
    gas_price: int


@dataclass(frozen=True)
class BlockInfo:
    number: int
    hash: str
    parent_hash: str
    timestamp: int
    tx_count: int
    gas_used: int


@dataclass(frozen=True)
class TxInfo:
    hash: str
    from_address: str
    to_address: str | None
    block_number: int | None
    value: int
    input: str


@dataclass(frozen=True)
class Receipt:
    tx_hash: str
    success: bool
    block_number: int
    gas_used: int


def rpc_guard(fn: Callable[..., T]) -> Callable[..., T]:
    """Translate RPC/transport failures and reverts into AppError."""

    @functools.wraps(fn)
    def wrapper(*args, **kwargs):
        try:
            return fn(*args, **kwargs)
        except AppError:
            raise
        except ContractLogicError as exc:
            raise AppError(409, "CONTRACT_REVERT", f"Contract reverted: {exc}") from exc
        except (requests.exceptions.RequestException, ConnectionError, OSError) as exc:
            log.error("rpc_unavailable", error=str(exc))
            raise AppError(503, "RPC_UNAVAILABLE", "Blockchain node is unreachable") from exc
        except TimeExhausted as exc:
            raise AppError(504, "RPC_TIMEOUT", "Timed out waiting for transaction receipt") from exc
        except Web3Exception as exc:
            msg = str(exc)
            if "revert" in msg.lower() or "execution" in msg.lower():
                raise AppError(409, "CONTRACT_REVERT", f"Contract reverted: {msg}") from exc
            log.error("rpc_error", error=msg)
            raise AppError(502, "RPC_ERROR", f"RPC error: {msg}") from exc
        except ValueError as exc:  # web3 raises ValueError for JSON-RPC error payloads in some paths
            msg = str(exc)
            if "revert" in msg.lower():
                raise AppError(409, "CONTRACT_REVERT", f"Contract reverted: {msg}") from exc
            raise AppError(502, "RPC_ERROR", f"RPC error: {msg}") from exc

    return wrapper


class ChainClient:
    """Thin, typed wrapper over Web3.py JSON-RPC access."""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.w3 = Web3(Web3.HTTPProvider(settings.rpc_url, request_kwargs={"timeout": 10}))

    def is_connected(self) -> bool:
        try:
            return bool(self.w3.is_connected())
        except Exception:
            return False

    @rpc_guard
    def network_info(self) -> NetworkInfo:
        return NetworkInfo(
            chain_id=self.w3.eth.chain_id,
            client_version=self.w3.client_version,
            block_number=self.w3.eth.block_number,
            gas_price=self.w3.eth.gas_price,
        )

    @rpc_guard
    def eth_balance(self, address: str) -> int:
        return self.w3.eth.get_balance(address)

    @rpc_guard
    def latest_block(self) -> BlockInfo:
        b = self.w3.eth.get_block("latest")
        return BlockInfo(
            number=b["number"], hash=b["hash"].to_0x_hex(), parent_hash=b["parentHash"].to_0x_hex(),
            timestamp=b["timestamp"], tx_count=len(b["transactions"]), gas_used=b["gasUsed"],
        )

    @rpc_guard
    def get_transaction(self, tx_hash: str) -> TxInfo | None:
        try:
            t = self.w3.eth.get_transaction(tx_hash)
        except Exception as exc:
            if exc.__class__.__name__ == "TransactionNotFound":
                return None
            raise
        return TxInfo(
            hash=t["hash"].to_0x_hex(), from_address=t["from"], to_address=t.get("to"),
            block_number=t.get("blockNumber"), value=t["value"], input=t["input"].to_0x_hex()
            if hasattr(t["input"], "to_0x_hex") else str(t["input"]),
        )

    @rpc_guard
    def wait_receipt(self, tx_hash: str, timeout: int | None = None) -> Receipt:
        r = self.w3.eth.wait_for_transaction_receipt(tx_hash, timeout=timeout or self.settings.receipt_timeout_s)
        return Receipt(tx_hash=tx_hash, success=r["status"] == 1, block_number=r["blockNumber"], gas_used=r["gasUsed"])

    @rpc_guard
    def get_receipt(self, tx_hash: str) -> Receipt | None:
        try:
            r = self.w3.eth.get_transaction_receipt(tx_hash)
        except Exception as exc:
            if exc.__class__.__name__ == "TransactionNotFound":
                return None
            raise
        return Receipt(tx_hash=tx_hash, success=r["status"] == 1, block_number=r["blockNumber"], gas_used=r["gasUsed"])

    @rpc_guard
    def send_signed(self, tx: dict, private_key: str) -> str:
        """Fill nonce/chain/gas, simulate, sign locally and broadcast. Returns tx hash (NOT a confirmation)."""
        acct = self.w3.eth.account.from_key(private_key)
        tx = {**tx, "from": acct.address, "chainId": self.settings.chain_id}
        tx["nonce"] = self.w3.eth.get_transaction_count(acct.address, "pending")
        if self.settings.gas_price_mode == "zero":
            tx["gasPrice"] = 0
        else:
            tx["gasPrice"] = int(self.w3.eth.gas_price * 1.25) or 1
        tx["gas"] = int(self.w3.eth.estimate_gas(tx) * 1.2)  # raises ContractLogicError on revert
        signed = acct.sign_transaction(tx)
        return self.w3.eth.send_raw_transaction(signed.raw_transaction).to_0x_hex()
