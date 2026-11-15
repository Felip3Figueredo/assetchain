from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.blockchain.token import TokenGateway
from app.core.errors import AppError
from app.core.logging import get_logger
from app.domain.units import fmt
from app.models import AssetStatus, ChainTransaction, TxStatus
from app.repositories.repos import AssetRepo, TxRepo
from app.services.indexer import Indexer
from app.services.wallet_service import WalletService

log = get_logger("transactions")


class TransactionService:
    def __init__(self, session: Session, gateway: TokenGateway, wallets: WalletService) -> None:
        self.s, self.gateway, self.wallets = session, gateway, wallets
        self.txs, self.assets = TxRepo(session), AssetRepo(session)

    def _check_replay(self, tx: ChainTransaction, asset_id: int, frm: str, to: str, amount: int) -> ChainTransaction:
        same = (tx.kind == "TRANSFER" and tx.asset_id == asset_id and tx.from_address == frm
                and tx.to_address == to and tx.amount == amount)
        if not same:
            raise AppError(409, "IDEMPOTENCY_KEY_REUSED",
                           "This Idempotency-Key was already used for a different operation or payload")
        if tx.status == TxStatus.PENDING and tx.tx_hash is None:
            raise AppError(409, "TRANSFER_IN_PROGRESS", "A transfer with this key is already being submitted")
        return tx

    def transfer(self, asset_id: int, from_address: str, to_address: str, amount_wei: int,
                 idempotency_key: str | None) -> ChainTransaction:
        if idempotency_key:
            prior = self.txs.by_idem(idempotency_key)
            if prior:
                return self._check_replay(prior, asset_id, from_address, to_address, amount_wei)
        asset = self.assets.get(asset_id)
        if asset is None:
            raise AppError(404, "ASSET_NOT_FOUND", f"Asset {asset_id} not found")
        contract = self.assets.contract_of(asset_id)
        if asset.status != AssetStatus.TOKENIZED or contract is None:
            raise AppError(409, "NOT_TOKENIZED", "Asset is not tokenized")
        if from_address == to_address:
            raise AppError(422, "SAME_WALLET", "Origin and destination must differ")

        sender = self.wallets.get(from_address)
        key = self.wallets.private_key_of(sender)
        balance = self.gateway.balance_of(contract.address, from_address)
        if balance < amount_wei:
            raise AppError(422, "INSUFFICIENT_BALANCE",
                           f"Balance {fmt(balance)} {contract.symbol} is lower than requested {fmt(amount_wei)}")

        # Reserve the idempotency key BEFORE broadcasting, so a concurrent duplicate cannot send a second tx.
        tx = self.txs.add(ChainTransaction(
            tx_hash=None, asset_id=asset_id, kind="TRANSFER", from_address=from_address, to_address=to_address,
            amount=amount_wei, status=TxStatus.PENDING, idempotency_key=idempotency_key))
        try:
            self.s.commit()
        except IntegrityError as exc:
            self.s.rollback()
            raise AppError(409, "TRANSFER_IN_PROGRESS", "A transfer with this key is already being submitted") from exc

        try:
            tx_hash = self.gateway.transfer(contract.address, key, to_address, amount_wei)
        except Exception:
            self.s.delete(tx)  # nothing reached the chain: leave no trace
            self.s.commit()
            raise
        tx.tx_hash = tx_hash
        try:
            self.s.commit()
        except IntegrityError:  # the reconciler already indexed this hash: keep a single record
            self.s.rollback()
            self.s.delete(self.s.get(ChainTransaction, tx.id))
            self.s.commit()
            return self.txs.by_hash(tx_hash)  # type: ignore[return-value]
        log.info("transfer_submitted", tx=tx_hash, asset_id=asset_id)

        try:
            receipt = self.gateway.client.wait_receipt(tx_hash)
        except AppError as exc:
            if exc.code == "RPC_TIMEOUT":
                return tx  # stays PENDING; the reconciler settles it later
            raise
        tx.status = TxStatus.CONFIRMED if receipt.success else TxStatus.FAILED
        tx.block_number = receipt.block_number
        if not receipt.success:
            tx.error = "Transaction reverted on-chain"
        self.s.commit()
        log.info("transfer_settled", tx=tx_hash, status=tx.status.value, block=receipt.block_number)
        try:
            Indexer(self.s, self.gateway).sync(asset_id)
        except AppError as exc:  # the transfer already succeeded; reconciliation can run later
            log.warning("post_transfer_sync_failed", error=exc.message)
        return tx
