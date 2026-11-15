from sqlalchemy.orm import Session

from app.blockchain.token import TokenGateway
from app.core.logging import get_logger
from app.models import ChainTransaction, IndexedEvent, TxStatus
from app.repositories.repos import AssetRepo, EventRepo, TxRepo

log = get_logger("indexer")
ZERO = "0x0000000000000000000000000000000000000000"


class Indexer:
    """Reconciles PostgreSQL with the chain: indexes Transfer events and settles PENDING txs."""

    def __init__(self, session: Session, gateway: TokenGateway) -> None:
        self.s, self.gateway = session, gateway
        self.events, self.txs, self.assets = EventRepo(session), TxRepo(session), AssetRepo(session)

    def sync(self, asset_id: int) -> int:
        contract = self.assets.contract_of(asset_id)
        if contract is None:
            return 0
        new = 0
        known_hashes = {t.tx_hash for t in self.txs.list(asset_id=asset_id, limit=100000)}
        for ev in self.gateway.transfer_events(contract.address, contract.deployed_block):
            if self.events.exists(ev.tx_hash, ev.log_index):
                continue
            self.events.add(IndexedEvent(
                contract_address=contract.address, tx_hash=ev.tx_hash, log_index=ev.log_index,
                block_number=ev.block_number, from_address=ev.from_address, to_address=ev.to_address,
                amount=ev.amount))
            self.s.flush()
            new += 1
            if ev.tx_hash not in known_hashes:  # activity that did not originate from this API
                self.txs.add(ChainTransaction(
                    tx_hash=ev.tx_hash, asset_id=asset_id, kind="MINT" if ev.from_address == ZERO else "TRANSFER",
                    from_address=ev.from_address, to_address=ev.to_address, amount=ev.amount,
                    status=TxStatus.CONFIRMED, block_number=ev.block_number))
                known_hashes.add(ev.tx_hash)
        self.settle_pending()
        self.s.commit()
        if new:
            log.info("events_indexed", asset_id=asset_id, count=new)
        return new

    def settle_pending(self) -> int:
        fixed = 0
        for tx in self.txs.pending():
            if not tx.tx_hash:
                continue
            receipt = self.gateway.client.get_receipt(tx.tx_hash)
            if receipt is None:
                continue
            tx.status = TxStatus.CONFIRMED if receipt.success else TxStatus.FAILED
            tx.block_number = receipt.block_number
            fixed += 1
        return fixed
