from sqlalchemy.orm import Session
from web3 import Web3

from app.blockchain.token import TokenGateway
from app.repositories.repos import AssetRepo


def stale_contracts(session: Session, gateway: TokenGateway) -> list[str]:
    """Asset codes whose contract has no code on the connected chain (e.g. the dev chain was reset)."""
    repo = AssetRepo(session)
    stale = []
    for c in repo.contracts():
        if len(gateway.w3.eth.get_code(Web3.to_checksum_address(c.address))) == 0:
            stale.append(repo.get(c.asset_id).asset_code)
    return stale
