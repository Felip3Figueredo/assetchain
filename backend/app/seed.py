"""Seed fictional assets and TEST wallets. Idempotent. Usage: python -m app.seed [--demo]"""
import sys
from decimal import Decimal

from sqlalchemy.orm import Session

from app.blockchain.client import ChainClient
from app.blockchain.token import TokenGateway
from app.core.config import Settings, get_settings
from app.core.logging import configure_logging, get_logger
from app.domain.units import to_wei
from app.models import Asset, AssetStatus
from app.repositories.repos import AssetRepo
from app.schemas.api import AssetIn
from app.services.asset_service import AssetService
from app.services.tokenization_service import TokenizationService
from app.services.transaction_service import TransactionService
from app.services.wallet_service import WalletService

log = get_logger("seed")

# Public Hardhat test accounts #1 and #2 (worthless; never use on a real network).
TEST_WALLETS = [
    ("Carteira B", "0x59c6995e998f97a5a0044966f0945389dc9e86dae88c7a8412f4603b6b78690d"),
    ("Carteira C", "0x5de4111afa1a4b94908f83103eb1f1706367c2e68ca870fc3fb9a804cdab365a"),
]

ASSETS = [
    AssetIn(asset_code="ASSET-001", name="Usina Solar Alpha", category="Energia renovável",
            description="Usina fotovoltaica fictícia de 12 MWp (ativo educacional).",
            estimated_value_brl=Decimal("10000000"), token_supply=10_000_000, token_price_brl=Decimal("1.00"),
            metadata={"location": "Petrolina, PE (fictício)", "capacity_mwp": 12}),
    AssetIn(asset_code="ASSET-002", name="Galpão Logístico Beta", category="Imóveis comerciais",
            description="Galpão logístico fictício de 8.000 m² (ativo educacional).",
            estimated_value_brl=Decimal("4000000"), token_supply=4_000_000, token_price_brl=Decimal("1.00"),
            metadata={"location": "Cajamar, SP (fictício)", "area_m2": 8000}),
]


def run_seed(session: Session, gateway: TokenGateway, settings: Settings, demo: bool = False) -> None:
    wallets = WalletService(session, gateway, settings)
    treasury = wallets.ensure_treasury()
    for label, key in TEST_WALLETS:
        wallets.register(label, key)

    assets = AssetService(session)
    repo = AssetRepo(session)
    for data in ASSETS:
        if repo.by_code(data.asset_code) is None:
            assets.create(data)
            log.info("asset_seeded", code=data.asset_code)

    if demo:
        alpha = repo.by_code("ASSET-001")
        assert alpha is not None
        if alpha.status == AssetStatus.DRAFT:
            assets.approve(alpha.id)
        tok = TokenizationService(session, gateway, wallets)
        if alpha.status != AssetStatus.TOKENIZED:
            tok.deploy(alpha.id, "seed-deploy-asset-001")
        if len(TransactionService(session, gateway, wallets).txs.list(asset_id=alpha.id)) < 3:
            b = wallets.repo.by_address(wallets.register(*TEST_WALLETS[0]).address)
            TransactionService(session, gateway, wallets).transfer(
                alpha.id, treasury.address, b.address, to_wei(Decimal("100000")), "seed-transfer-1")
    log.info("seed_done", demo=demo)


def main() -> None:
    settings = get_settings()
    configure_logging(settings.log_level)
    from app.core.db import make_engine
    from sqlalchemy.orm import sessionmaker

    gateway = TokenGateway(ChainClient(settings))
    with sessionmaker(bind=make_engine(settings.database_url))() as s:
        run_seed(s, gateway, settings, demo="--demo" in sys.argv)


if __name__ == "__main__":
    main()
