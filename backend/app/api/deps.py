from collections.abc import Iterator

from fastapi import Depends, Request
from sqlalchemy.orm import Session

from app.blockchain.token import TokenGateway
from app.core.config import Settings
from app.services.asset_service import AssetService
from app.services.indexer import Indexer
from app.services.tokenization_service import TokenizationService
from app.services.transaction_service import TransactionService
from app.services.wallet_service import WalletService


def get_settings_dep(request: Request) -> Settings:
    return request.app.state.settings


def get_db(request: Request) -> Iterator[Session]:
    session = request.app.state.session_factory()
    try:
        yield session
    finally:
        session.close()


def get_gateway(request: Request) -> TokenGateway:
    return request.app.state.gateway


def asset_service(s: Session = Depends(get_db)) -> AssetService:
    return AssetService(s)


def wallet_service(s: Session = Depends(get_db), g: TokenGateway = Depends(get_gateway),
                   cfg: Settings = Depends(get_settings_dep)) -> WalletService:
    return WalletService(s, g, cfg)


def tokenization_service(s: Session = Depends(get_db), g: TokenGateway = Depends(get_gateway),
                         w: WalletService = Depends(wallet_service)) -> TokenizationService:
    return TokenizationService(s, g, w)


def transaction_service(s: Session = Depends(get_db), g: TokenGateway = Depends(get_gateway),
                        w: WalletService = Depends(wallet_service)) -> TransactionService:
    return TransactionService(s, g, w)


def indexer(s: Session = Depends(get_db), g: TokenGateway = Depends(get_gateway)) -> Indexer:
    return Indexer(s, g)
