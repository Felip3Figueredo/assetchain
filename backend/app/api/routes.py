from decimal import Decimal

from fastapi import APIRouter, Depends, Header, Query
from sqlalchemy.orm import Session
from web3 import Web3

from app.api.deps import (asset_service, get_db, get_gateway, indexer, tokenization_service,
                          transaction_service, wallet_service)
from app.blockchain.token import TokenGateway
from app.core.errors import AppError
from app.domain.units import fmt, to_wei
from app.models import Asset, AssetStatus, ChainTransaction
from app.repositories.repos import AssetRepo, EventRepo, TxRepo, WalletRepo
from app.schemas.api import AssetIn, AssetOut, BalanceOut, TransferIn, TxOut, WalletIn, WalletOut
from app.services.asset_service import AssetService
from app.services.indexer import Indexer
from app.services.tokenization_service import ZERO, TokenizationService
from app.services.transaction_service import TransactionService
from app.services.wallet_service import WalletService

router = APIRouter(prefix="/api")


def _asset_out(a: Asset) -> AssetOut:
    out = AssetOut.model_validate(a)
    out.contract_address = a.contract.address if a.contract else None
    return out


def _tx_out(tx: ChainTransaction, s: Session) -> TxOut:
    asset = AssetRepo(s).get(tx.asset_id)
    return TxOut(id=tx.id, tx_hash=tx.tx_hash, asset_id=tx.asset_id, asset_code=asset.asset_code if asset else "",
                 kind=tx.kind, from_address=tx.from_address, to_address=tx.to_address, amount=fmt(tx.amount),
                 status=tx.status.value, block_number=tx.block_number, error=tx.error, created_at=tx.created_at)


def _norm_address(address: str) -> str:
    if not Web3.is_address(address):
        raise AppError(422, "INVALID_ADDRESS", "Invalid Ethereum address")
    return Web3.to_checksum_address(address)


# ---------------- Assets ----------------
@router.post("/assets", response_model=AssetOut, status_code=201, tags=["assets"])
def create_asset(body: AssetIn, svc: AssetService = Depends(asset_service)):
    return _asset_out(svc.create(body))


@router.get("/assets", response_model=list[AssetOut], tags=["assets"])
def list_assets(svc: AssetService = Depends(asset_service)):
    return [_asset_out(a) for a in svc.repo.list()]


@router.get("/assets/{asset_id}", response_model=AssetOut, tags=["assets"])
def get_asset(asset_id: int, svc: AssetService = Depends(asset_service)):
    return _asset_out(svc.get(asset_id))


@router.put("/assets/{asset_id}", response_model=AssetOut, tags=["assets"])
def update_asset(asset_id: int, body: AssetIn, svc: AssetService = Depends(asset_service)):
    return _asset_out(svc.update(asset_id, body))


@router.post("/assets/{asset_id}/approve", response_model=AssetOut, tags=["assets"])
def approve_asset(asset_id: int, svc: AssetService = Depends(asset_service)):
    return _asset_out(svc.approve(asset_id))


@router.get("/assets/{asset_id}/transactions", response_model=list[TxOut], tags=["assets"])
def asset_transactions(asset_id: int, s: Session = Depends(get_db), svc: AssetService = Depends(asset_service)):
    svc.get(asset_id)
    return [_tx_out(t, s) for t in TxRepo(s).list(asset_id=asset_id)]


# ---------------- Tokenization ----------------
def _token_info(c, asset: Asset, chain_id: int) -> dict:
    return {"asset_id": asset.id, "asset_code": asset.asset_code, "status": asset.status.value,
            "contract_address": c.address, "symbol": c.symbol, "name": asset.name,
            "deploy_tx_hash": c.deploy_tx_hash, "deployed_block": c.deployed_block, "cap": fmt(c.cap),
            "chain_id": chain_id}


@router.post("/tokenization/{asset_id}/deploy", tags=["tokenization"])
def deploy_token(asset_id: int, idempotency_key: str | None = Header(default=None, max_length=100),
                 svc: TokenizationService = Depends(tokenization_service),
                 g: TokenGateway = Depends(get_gateway), s: Session = Depends(get_db)):
    c = svc.deploy(asset_id, idempotency_key)
    return _token_info(c, AssetRepo(s).get(asset_id), g.client.settings.chain_id)


@router.get("/tokenization/{asset_id}", tags=["tokenization"])
def tokenization_info(asset_id: int, svc: TokenizationService = Depends(tokenization_service),
                      g: TokenGateway = Depends(get_gateway), s: Session = Depends(get_db)):
    c = svc.contract(asset_id)
    return _token_info(c, AssetRepo(s).get(asset_id), g.client.settings.chain_id)


@router.get("/tokenization/{asset_id}/supply", tags=["tokenization"])
def token_supply(asset_id: int, svc: TokenizationService = Depends(tokenization_service)):
    return svc.supply(asset_id)


@router.get("/tokenization/{asset_id}/holders", tags=["tokenization"])
def token_holders(asset_id: int, svc: TokenizationService = Depends(tokenization_service),
                  idx: Indexer = Depends(indexer), g: TokenGateway = Depends(get_gateway),
                  s: Session = Depends(get_db)):
    c = svc.contract(asset_id)
    idx.sync(asset_id)
    labels = {w.address: w.label for w in WalletRepo(s).list()}
    addresses = {e.to_address for e in EventRepo(s).for_contract(c.address)} - {ZERO}
    holders = []
    for addr in addresses:
        bal = g.balance_of(c.address, addr)  # chain is the source of truth for balances
        if bal > 0:
            holders.append({"address": addr, "label": labels.get(addr), "balance": fmt(bal), "_w": bal})
    holders.sort(key=lambda h: -h["_w"])
    total = sum(h["_w"] for h in holders) or 1
    for h in holders:
        h["share_pct"] = round(h.pop("_w") * 100 / total, 4)
    return holders


@router.post("/tokenization/{asset_id}/sync", tags=["tokenization"])
def sync_events(asset_id: int, svc: TokenizationService = Depends(tokenization_service),
                idx: Indexer = Depends(indexer)):
    svc.contract(asset_id)
    return {"indexed_events": idx.sync(asset_id)}


# ---------------- Wallets ----------------
@router.post("/wallets", response_model=WalletOut, status_code=201, tags=["wallets"])
def create_wallet(body: WalletIn, svc: WalletService = Depends(wallet_service)):
    return svc.create(body.label)


@router.get("/wallets", response_model=list[WalletOut], tags=["wallets"])
def list_wallets(svc: WalletService = Depends(wallet_service)):
    return svc.repo.list()


@router.get("/wallets/{address}", tags=["wallets"])
def get_wallet(address: str, svc: WalletService = Depends(wallet_service), g: TokenGateway = Depends(get_gateway)):
    w = svc.get(_norm_address(address))
    eth = g.w3.eth.get_balance(w.address)
    return {**WalletOut.model_validate(w).model_dump(), "eth_balance": str(Decimal(eth) / 10**18)}


@router.get("/wallets/{address}/balances", response_model=list[BalanceOut], tags=["wallets"])
def wallet_balances(address: str, svc: WalletService = Depends(wallet_service)):
    return svc.balances(_norm_address(address))


@router.get("/wallets/{address}/transactions", response_model=list[TxOut], tags=["wallets"])
def wallet_transactions(address: str, s: Session = Depends(get_db)):
    return [_tx_out(t, s) for t in TxRepo(s).list(address=_norm_address(address))]


# ---------------- Transactions ----------------
@router.post("/transactions/transfer", response_model=TxOut, status_code=201, tags=["transactions"])
def transfer(body: TransferIn, idempotency_key: str | None = Header(default=None, max_length=100),
             svc: TransactionService = Depends(transaction_service), s: Session = Depends(get_db)):
    tx = svc.transfer(body.asset_id, body.from_address, body.to_address, to_wei(body.amount), idempotency_key)
    return _tx_out(tx, s)


@router.get("/transactions", response_model=list[TxOut], tags=["transactions"])
def list_transactions(asset_id: int | None = None, limit: int = Query(200, ge=1, le=1000),
                      s: Session = Depends(get_db)):
    return [_tx_out(t, s) for t in TxRepo(s).list(asset_id=asset_id, limit=limit)]


@router.get("/transactions/{tx_hash}", tags=["transactions"])
def transaction_detail(tx_hash: str, s: Session = Depends(get_db), g: TokenGateway = Depends(get_gateway)):
    tx = TxRepo(s).by_hash(tx_hash)
    if tx is None:
        raise AppError(404, "TX_NOT_FOUND", "Transaction not found")
    out = _tx_out(tx, s).model_dump(mode="json")
    info = g.client.get_transaction(tx_hash)
    receipt = g.client.get_receipt(tx_hash)
    out["chain"] = {
        "block_number": info.block_number if info else None,
        "from": info.from_address if info else None, "to": info.to_address if info else None,
        "gas_used": receipt.gas_used if receipt else None, "success": receipt.success if receipt else None,
    }
    return out


# ---------------- Blockchain ----------------
@router.get("/blockchain/status", tags=["blockchain"])
def chain_status(g: TokenGateway = Depends(get_gateway)):
    return _status(g)


def _status(g: TokenGateway) -> dict:
    if not g.client.is_connected():
        return {"connected": False, "chain_id": None, "block_number": None, "client_version": None}
    info = g.client.network_info()
    return {"connected": True, "chain_id": info.chain_id, "block_number": info.block_number,
            "client_version": info.client_version}


@router.get("/blockchain/network", tags=["blockchain"])
def chain_network(g: TokenGateway = Depends(get_gateway)):
    info = g.client.network_info()
    return {"chain_id": info.chain_id, "client_version": info.client_version, "gas_price": str(info.gas_price),
            "block_number": info.block_number, "rpc_url": g.client.settings.rpc_url}


@router.get("/blockchain/blocks/latest", tags=["blockchain"])
def latest_block(g: TokenGateway = Depends(get_gateway)):
    return g.client.latest_block().__dict__


@router.get("/blockchain/transactions/{tx_hash}", tags=["blockchain"])
def chain_transaction(tx_hash: str, g: TokenGateway = Depends(get_gateway)):
    info = g.client.get_transaction(tx_hash)
    if info is None:
        raise AppError(404, "TX_NOT_FOUND", "Transaction not found on chain")
    receipt = g.client.get_receipt(tx_hash)
    return {**info.__dict__, "value": str(info.value), "success": receipt.success if receipt else None,
            "gas_used": receipt.gas_used if receipt else None}


# ---------------- Dashboard ----------------
@router.get("/dashboard/stats", tags=["dashboard"])
def dashboard_stats(s: Session = Depends(get_db), g: TokenGateway = Depends(get_gateway)):
    assets = AssetRepo(s)
    issued = 0
    if g.client.is_connected():
        issued = sum(g.total_supply(c.address) for c in assets.contracts())
    return {"assets": assets.count(), "tokenized_assets": assets.count(AssetStatus.TOKENIZED),
            "total_tokens_issued": fmt(issued), "wallets": WalletRepo(s).count(),
            "transactions": TxRepo(s).count(), "chain": _status(g)}
