"""Observe how a transaction landed on every node of the network (measured via each node's JSON-RPC)."""
from __future__ import annotations

import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass

from web3 import Web3
from web3.middleware import ExtraDataToPOAMiddleware

from app.blockchain.client import ChainClient
from app.core.config import Settings
from app.core.errors import AppError


@dataclass(frozen=True)
class NodeRef:
    name: str
    address: str  # validator address of the node ("" when unknown)
    url: str


def parse_nodes(text: str) -> list[NodeRef]:
    """Format: 'Name|0xValidatorAddress|http://host:8545;Name2|...' (the first node is the API's entry node)."""
    nodes = []
    for chunk in filter(None, (c.strip() for c in text.split(";"))):
        name, address, url = (part.strip() for part in chunk.split("|", 2))
        nodes.append(NodeRef(name, address, url))
    return nodes


def _inspect(settings: Settings, node: NodeRef, tx_hash: str, block_number: int, is_entry: bool) -> dict:
    out = {"name": node.name, "address": node.address, "is_entry": is_entry, "reachable": False,
           "has_tx": False, "block_number": None, "block_hash": None, "latency_ms": None}
    started = time.monotonic()
    try:
        w3 = Web3(Web3.HTTPProvider(node.url, request_kwargs={"timeout": 3}))
        if settings.poa_chain:
            w3.middleware_onion.inject(ExtraDataToPOAMiddleware, layer=0)
        head = w3.eth.block_number
        out["reachable"] = True
        out["head"] = head
        try:
            receipt = w3.eth.get_transaction_receipt(tx_hash)
            out["has_tx"] = True
            out["block_number"] = receipt["blockNumber"]
        except Exception as exc:  # TransactionNotFound: the node has not imported the block yet
            if exc.__class__.__name__ != "TransactionNotFound":
                raise
        if head >= block_number:
            out["block_hash"] = w3.eth.get_block(block_number)["hash"].to_0x_hex()
    except Exception:
        pass  # unreachable (or failed mid-way): the fields gathered so far already describe the problem
    finally:
        out["latency_ms"] = round((time.monotonic() - started) * 1000)
    return out


def trace(settings: Settings, client: ChainClient, tx_hash: str) -> dict:
    info = client.get_transaction(tx_hash)
    receipt = client.get_receipt(tx_hash)
    if info is None:
        raise AppError(404, "TX_NOT_FOUND", "Transaction not found on chain")
    if receipt is None:
        return {"tx_hash": tx_hash, "status": "PENDING", "block_number": None, "block_hash": None,
                "proposer": None, "nodes": [], "in_sync": False}
    block = client.w3.eth.get_block(receipt.block_number)
    ref_hash = block["hash"].to_0x_hex()
    nodes = parse_nodes(settings.node_rpc_urls) or [NodeRef("Nó local", "", settings.rpc_url)]
    with ThreadPoolExecutor(max_workers=len(nodes)) as pool:
        results = list(pool.map(
            lambda t: _inspect(settings, t[1], tx_hash, receipt.block_number, t[0] == 0), enumerate(nodes)))
    for r in results:
        r["in_block"] = r["has_tx"] and r["block_hash"] == ref_hash
    return {
        "tx_hash": tx_hash, "status": "CONFIRMED" if receipt.success else "FAILED",
        "from_address": info.from_address, "to_address": info.to_address,
        "block_number": receipt.block_number, "block_hash": ref_hash,
        "block_timestamp": block["timestamp"], "proposer": Web3.to_checksum_address(block["miner"]),
        "nodes": results, "in_sync": all(r["reachable"] and r["in_block"] for r in results),
    }
