from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import Asset, ChainTransaction, IndexedEvent, TokenContract, Wallet


class AssetRepo:
    def __init__(self, s: Session) -> None:
        self.s = s

    def get(self, asset_id: int) -> Asset | None:
        return self.s.get(Asset, asset_id)

    def by_code(self, code: str) -> Asset | None:
        return self.s.scalar(select(Asset).where(Asset.asset_code == code))

    def list(self) -> list[Asset]:
        return list(self.s.scalars(select(Asset).order_by(Asset.id)))

    def add(self, asset: Asset) -> Asset:
        self.s.add(asset)
        self.s.flush()
        return asset

    def count(self, status=None) -> int:
        q = select(func.count(Asset.id))
        if status is not None:
            q = q.where(Asset.status == status)
        return self.s.scalar(q) or 0

    def contract_of(self, asset_id: int) -> TokenContract | None:
        return self.s.scalar(select(TokenContract).where(TokenContract.asset_id == asset_id))

    def contracts(self) -> list[TokenContract]:
        return list(self.s.scalars(select(TokenContract)))


class WalletRepo:
    def __init__(self, s: Session) -> None:
        self.s = s

    def by_address(self, address: str) -> Wallet | None:
        return self.s.scalar(select(Wallet).where(Wallet.address == address))

    def list(self) -> list[Wallet]:
        return list(self.s.scalars(select(Wallet).order_by(Wallet.id)))

    def add(self, w: Wallet) -> Wallet:
        self.s.add(w)
        self.s.flush()
        return w

    def count(self) -> int:
        return self.s.scalar(select(func.count(Wallet.id))) or 0


class TxRepo:
    def __init__(self, s: Session) -> None:
        self.s = s

    def by_hash(self, h: str) -> ChainTransaction | None:
        return self.s.scalar(select(ChainTransaction).where(ChainTransaction.tx_hash == h))

    def by_idem(self, key: str) -> ChainTransaction | None:
        return self.s.scalar(select(ChainTransaction).where(ChainTransaction.idempotency_key == key))

    def list(self, asset_id: int | None = None, address: str | None = None, limit: int = 200) -> list[ChainTransaction]:
        q = select(ChainTransaction).order_by(ChainTransaction.id.desc()).limit(limit)
        if asset_id is not None:
            q = q.where(ChainTransaction.asset_id == asset_id)
        if address:
            q = q.where((ChainTransaction.from_address == address) | (ChainTransaction.to_address == address))
        return list(self.s.scalars(q))

    def pending(self) -> list[ChainTransaction]:
        return list(self.s.scalars(select(ChainTransaction).where(ChainTransaction.status == "PENDING")))

    def pending_deploy(self, asset_id: int) -> ChainTransaction | None:
        return self.s.scalar(select(ChainTransaction).where(
            ChainTransaction.asset_id == asset_id, ChainTransaction.kind == "DEPLOY",
            ChainTransaction.status == "PENDING"))

    def add(self, t: ChainTransaction) -> ChainTransaction:
        self.s.add(t)
        self.s.flush()
        return t

    def count(self) -> int:
        return self.s.scalar(select(func.count(ChainTransaction.id))) or 0


class EventRepo:
    def __init__(self, s: Session) -> None:
        self.s = s

    def exists(self, tx_hash: str, log_index: int) -> bool:
        return self.s.scalar(select(IndexedEvent.id).where(
            IndexedEvent.tx_hash == tx_hash, IndexedEvent.log_index == log_index)) is not None

    def add(self, e: IndexedEvent) -> None:
        self.s.add(e)

    def for_contract(self, address: str) -> list[IndexedEvent]:
        return list(self.s.scalars(select(IndexedEvent).where(IndexedEvent.contract_address == address)
                                   .order_by(IndexedEvent.block_number, IndexedEvent.log_index)))
