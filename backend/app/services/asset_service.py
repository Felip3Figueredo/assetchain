from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.domain.states import ensure_transition
from app.models import Asset, AssetStatus
from app.repositories.repos import AssetRepo
from app.schemas.api import AssetIn


class AssetService:
    def __init__(self, session: Session) -> None:
        self.s = session
        self.repo = AssetRepo(session)

    def get(self, asset_id: int) -> Asset:
        asset = self.repo.get(asset_id)
        if asset is None:
            raise AppError(404, "ASSET_NOT_FOUND", f"Asset {asset_id} not found")
        return asset

    def create(self, data: AssetIn) -> Asset:
        if self.repo.by_code(data.asset_code):
            raise AppError(409, "ASSET_CODE_EXISTS", f"Asset code {data.asset_code} already exists")
        asset = Asset(
            asset_code=data.asset_code, name=data.name, category=data.category, description=data.description,
            estimated_value_brl=data.estimated_value_brl, token_supply=data.token_supply,
            token_price_brl=data.token_price_brl, metadata_json=data.metadata,
        )
        self.repo.add(asset)
        self.s.commit()
        return asset

    def update(self, asset_id: int, data: AssetIn) -> Asset:
        asset = self.get(asset_id)
        if asset.status == AssetStatus.TOKENIZED:
            raise AppError(409, "ASSET_LOCKED", "Tokenized assets cannot be edited")
        other = self.repo.by_code(data.asset_code)
        if other and other.id != asset.id:
            raise AppError(409, "ASSET_CODE_EXISTS", f"Asset code {data.asset_code} already exists")
        for f in ("asset_code", "name", "category", "description", "estimated_value_brl",
                  "token_supply", "token_price_brl"):
            setattr(asset, f, getattr(data, f))
        asset.metadata_json = data.metadata
        self.s.commit()
        return asset

    def approve(self, asset_id: int) -> Asset:
        asset = self.get(asset_id)
        ensure_transition(asset.status, AssetStatus.APPROVED)
        asset.status = AssetStatus.APPROVED
        self.s.commit()
        return asset
