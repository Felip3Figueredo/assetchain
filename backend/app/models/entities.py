import enum
from datetime import datetime, timezone

from sqlalchemy import JSON, BigInteger, DateTime, Enum, ForeignKey, Integer, Numeric, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base
from app.models.types import WeiInt


def _now() -> datetime:
    return datetime.now(timezone.utc)


class AssetStatus(str, enum.Enum):
    DRAFT = "DRAFT"
    APPROVED = "APPROVED"
    TOKENIZED = "TOKENIZED"


class TxStatus(str, enum.Enum):
    PENDING = "PENDING"
    CONFIRMED = "CONFIRMED"
    FAILED = "FAILED"


class Asset(Base):
    __tablename__ = "assets"
    id: Mapped[int] = mapped_column(primary_key=True)
    asset_code: Mapped[str] = mapped_column(String(40), unique=True)
    name: Mapped[str] = mapped_column(String(120))
    category: Mapped[str] = mapped_column(String(80))
    description: Mapped[str] = mapped_column(String(500), default="")
    estimated_value_brl: Mapped[float] = mapped_column(Numeric(20, 2))
    token_supply: Mapped[int] = mapped_column(BigInteger)  # whole tokens
    token_price_brl: Mapped[float] = mapped_column(Numeric(20, 6))
    status: Mapped[AssetStatus] = mapped_column(Enum(AssetStatus), default=AssetStatus.DRAFT)
    metadata_json: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    contract: Mapped["TokenContract | None"] = relationship(back_populates="asset", uselist=False)


class TokenContract(Base):
    __tablename__ = "token_contracts"
    id: Mapped[int] = mapped_column(primary_key=True)
    asset_id: Mapped[int] = mapped_column(ForeignKey("assets.id"), unique=True)
    address: Mapped[str] = mapped_column(String(42), unique=True)
    deploy_tx_hash: Mapped[str] = mapped_column(String(66))
    deployed_block: Mapped[int] = mapped_column(Integer)
    cap: Mapped[int] = mapped_column(WeiInt)
    symbol: Mapped[str] = mapped_column(String(20))
    asset: Mapped[Asset] = relationship(back_populates="contract")


class Wallet(Base):
    __tablename__ = "wallets"
    id: Mapped[int] = mapped_column(primary_key=True)
    address: Mapped[str] = mapped_column(String(42), unique=True)
    label: Mapped[str] = mapped_column(String(80))
    encrypted_key: Mapped[str | None] = mapped_column(String(300), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    @property
    def can_sign(self) -> bool:
        return self.encrypted_key is not None


class ChainTransaction(Base):
    __tablename__ = "chain_transactions"
    id: Mapped[int] = mapped_column(primary_key=True)
    tx_hash: Mapped[str | None] = mapped_column(String(66), unique=True, nullable=True)
    asset_id: Mapped[int] = mapped_column(ForeignKey("assets.id"))
    kind: Mapped[str] = mapped_column(String(20), default="TRANSFER")  # DEPLOY | MINT | TRANSFER
    from_address: Mapped[str] = mapped_column(String(42))
    to_address: Mapped[str] = mapped_column(String(42))
    amount: Mapped[int] = mapped_column(WeiInt)
    status: Mapped[TxStatus] = mapped_column(Enum(TxStatus), default=TxStatus.PENDING)
    block_number: Mapped[int | None] = mapped_column(Integer, nullable=True)
    error: Mapped[str | None] = mapped_column(String(300), nullable=True)
    idempotency_key: Mapped[str | None] = mapped_column(String(100), unique=True, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


class IndexedEvent(Base):
    __tablename__ = "indexed_events"
    __table_args__ = (UniqueConstraint("tx_hash", "log_index"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    contract_address: Mapped[str] = mapped_column(String(42))
    tx_hash: Mapped[str] = mapped_column(String(66))
    log_index: Mapped[int] = mapped_column(Integer)
    block_number: Mapped[int] = mapped_column(Integer)
    from_address: Mapped[str] = mapped_column(String(42))
    to_address: Mapped[str] = mapped_column(String(42))
    amount: Mapped[int] = mapped_column(WeiInt)
