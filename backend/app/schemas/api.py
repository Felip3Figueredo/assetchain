from datetime import datetime
from decimal import Decimal
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, field_validator
from web3 import Web3

Address = Annotated[str, StringConstraints(strip_whitespace=True)]


def _checksum(v: str) -> str:
    if not isinstance(v, str) or not Web3.is_address(v):
        raise ValueError("invalid Ethereum address")
    return Web3.to_checksum_address(v)


class AssetIn(BaseModel):
    asset_code: str = Field(min_length=3, max_length=40, pattern=r"^[A-Za-z0-9_-]+$")
    name: str = Field(min_length=2, max_length=120)
    category: str = Field(min_length=2, max_length=80)
    description: str = Field(default="", max_length=500)
    estimated_value_brl: Decimal = Field(gt=0, max_digits=20, decimal_places=2)
    token_supply: int = Field(gt=0, le=10**12)
    token_price_brl: Decimal = Field(gt=0, max_digits=20, decimal_places=6)
    metadata: dict = Field(default_factory=dict)


class AssetOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    asset_code: str
    name: str
    category: str
    description: str
    estimated_value_brl: Decimal
    token_supply: int
    token_price_brl: Decimal
    status: str
    metadata: dict = Field(validation_alias="metadata_json")
    contract_address: str | None = None
    created_at: datetime


class WalletIn(BaseModel):
    label: str = Field(min_length=1, max_length=80)


class WalletOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    address: str
    label: str
    can_sign: bool
    created_at: datetime


class BalanceOut(BaseModel):
    asset_id: int
    asset_code: str
    symbol: str
    contract_address: str
    balance: str


class TransferIn(BaseModel):
    asset_id: int = Field(gt=0)
    from_address: str
    to_address: str
    amount: Decimal = Field(gt=0, max_digits=40, decimal_places=18)

    @field_validator("from_address", "to_address")
    @classmethod
    def _addr(cls, v: str) -> str:
        return _checksum(v)


class TxOut(BaseModel):
    id: int
    tx_hash: str | None
    asset_id: int
    asset_code: str
    kind: str
    from_address: str
    to_address: str
    amount: str
    status: str
    block_number: int | None
    error: str | None
    created_at: datetime
