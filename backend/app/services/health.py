from sqlalchemy import delete
from sqlalchemy.orm import Session
from web3 import Web3

from app.blockchain.token import TokenGateway
from app.core.logging import get_logger
from app.models import Asset, ChainTransaction, IndexedEvent, TokenContract, Wallet
from app.repositories.repos import AssetRepo

log = get_logger("health")


def stale_contracts(session: Session, gateway: TokenGateway) -> list[str]:
    """Asset codes whose contract has no code on the connected chain (e.g. the dev chain was reset)."""
    repo = AssetRepo(session)
    stale = []
    for c in repo.contracts():
        if len(gateway.w3.eth.get_code(Web3.to_checksum_address(c.address))) == 0:
            stale.append(repo.get(c.asset_id).asset_code)
    return stale


def reconcile_chain_reset(session: Session, gateway: TokenGateway, auto_reset: bool) -> list[str]:
    """Detect a reset dev chain. With auto_reset (dev only) wipe app data so the seed can start clean."""
    stale = stale_contracts(session, gateway)
    if not stale:
        return []
    if auto_reset:
        for model in (IndexedEvent, ChainTransaction, TokenContract, Wallet, Asset):
            session.execute(delete(model))
        session.commit()
        log.warning("chain_reset_detected_app_data_cleared", assets=stale)
    else:
        log.warning("chain_database_mismatch", assets=stale,
                    hint="The chain was reset but PostgreSQL still references old contracts. "
                         "Run `docker compose down -v`, or set AUTO_RESET_ON_CHAIN_MISMATCH=true (dev only).")
    return stale
