import re

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.blockchain.token import TokenGateway
from app.core.errors import AppError
from app.core.logging import get_logger
from app.domain.states import ensure_transition
from app.domain.units import fmt
from app.models import Asset, AssetStatus, ChainTransaction, TokenContract, TxStatus
from app.repositories.repos import AssetRepo, TxRepo, WalletRepo
from app.services.wallet_service import WalletService

log = get_logger("tokenization")
ZERO = "0x0000000000000000000000000000000000000000"
WEI = 10**18


def symbol_for(asset: Asset) -> str:
    return re.sub(r"[^A-Z0-9]", "", asset.asset_code.upper())[:10] or "ASSET"


class TokenizationService:
    def __init__(self, session: Session, gateway: TokenGateway, wallets: WalletService) -> None:
        self.s, self.gateway, self.wallets = session, gateway, wallets
        self.assets, self.txs = AssetRepo(session), TxRepo(session)

    def _asset(self, asset_id: int) -> Asset:
        a = self.assets.get(asset_id)
        if a is None:
            raise AppError(404, "ASSET_NOT_FOUND", f"Asset {asset_id} not found")
        return a

    def contract(self, asset_id: int) -> TokenContract:
        self._asset(asset_id)
        c = self.assets.contract_of(asset_id)
        if c is None:
            raise AppError(404, "NOT_TOKENIZED", f"Asset {asset_id} has no token contract")
        return c

    # ---- deploy helpers -------------------------------------------------
    def _finalize_deploy(self, asset: Asset, res: ChainTransaction, receipt) -> TokenContract:
        contract = TokenContract(asset_id=asset.id, address=receipt.contract_address, deploy_tx_hash=receipt.tx_hash,
                                 deployed_block=receipt.block_number, cap=asset.token_supply * WEI,
                                 symbol=symbol_for(asset))
        self.s.add(contract)
        res.to_address, res.block_number, res.status = receipt.contract_address, receipt.block_number, TxStatus.CONFIRMED
        self.s.commit()
        log.info("contract_deployed", asset=asset.asset_code, address=receipt.contract_address,
                 block=receipt.block_number)
        return contract

    def _resume_pending_deploy(self, asset: Asset, pending: ChainTransaction) -> TokenContract | None:
        """A previous attempt broadcast the deployment but never saw the receipt: settle it from the chain."""
        if pending.tx_hash is None:
            raise AppError(409, "DEPLOY_IN_PROGRESS", "A deployment for this asset is already in progress")
        receipt = self.gateway.client.get_receipt(pending.tx_hash)
        if receipt is None:
            raise AppError(409, "DEPLOY_IN_PROGRESS", "Deployment is still waiting to be mined")
        if receipt.success and receipt.contract_address:
            return self._finalize_deploy(asset, pending, receipt)
        pending.status = TxStatus.FAILED
        self.s.commit()
        return None

    def _reserve_deploy(self, asset: Asset, idem: str | None, prior: ChainTransaction | None) -> ChainTransaction:
        """Record intent BEFORE touching the chain so retries/concurrent calls cannot deploy twice."""
        if prior is not None:
            res = prior  # FAILED earlier: reuse the row so the same key can be retried
            res.status, res.tx_hash = TxStatus.PENDING, None
        else:
            res = self.txs.add(ChainTransaction(
                asset_id=asset.id, kind="DEPLOY", from_address=self.gateway.deployer_address,
                to_address="", amount=0, status=TxStatus.PENDING, idempotency_key=idem))
        try:
            self.s.commit()
        except IntegrityError as exc:
            self.s.rollback()
            raise AppError(409, "DEPLOY_IN_PROGRESS", "A deployment with this key is already in progress") from exc
        return res

    def _settle_pending_mint(self, asset: Asset) -> None:
        """Resolve a MINT whose receipt was never observed, instead of blindly minting again."""
        pending = self.txs.pending_of(asset.id, "MINT")
        if pending is None:
            return
        if pending.tx_hash is None:
            raise AppError(409, "MINT_IN_PROGRESS", "An initial mint is already in progress")
        receipt = self.gateway.client.get_receipt(pending.tx_hash)
        if receipt is None:
            raise AppError(409, "MINT_IN_PROGRESS", "Initial mint is still waiting to be mined")
        pending.status = TxStatus.CONFIRMED if receipt.success else TxStatus.FAILED
        pending.block_number = receipt.block_number
        self.s.commit()

    def deploy(self, asset_id: int, idempotency_key: str | None) -> TokenContract:
        asset = self._asset(asset_id)
        prior = self.txs.by_idem(idempotency_key) if idempotency_key else None
        if prior is not None and (prior.kind != "DEPLOY" or prior.asset_id != asset_id):
            raise AppError(409, "IDEMPOTENCY_KEY_REUSED", "This Idempotency-Key was used for a different operation")
        contract = self.assets.contract_of(asset_id)

        if asset.status == AssetStatus.TOKENIZED and contract:
            if prior is not None and prior.status == TxStatus.CONFIRMED:
                return contract  # idempotent replay
            raise AppError(409, "ALREADY_TOKENIZED", "Asset is already tokenized")
        if asset.status == AssetStatus.DRAFT:
            raise AppError(409, "NOT_APPROVED", "Asset must be approved before tokenization")

        treasury = self.wallets.ensure_treasury()
        if contract is None:
            pending = self.txs.pending_of(asset_id, "DEPLOY")
            if pending is not None:
                contract = self._resume_pending_deploy(asset, pending)
                if contract is not None:
                    prior = pending if prior is None else prior
        if contract is None:
            res = self._reserve_deploy(asset, idempotency_key, prior if prior and prior.status == TxStatus.FAILED else None)
            cap = asset.token_supply * WEI
            try:
                tx_hash = self.gateway.deploy_send(asset.name, symbol_for(asset), asset.asset_code, cap)
            except Exception:
                res.status = TxStatus.FAILED
                self.s.commit()
                raise
            res.tx_hash = tx_hash  # persisted before waiting: a timeout can be resumed from the hash
            self.s.commit()
            receipt = self.gateway.client.wait_receipt(tx_hash)  # RPC_TIMEOUT leaves the row PENDING
            if not receipt.success or not receipt.contract_address:
                res.status = TxStatus.FAILED
                self.s.commit()
                raise AppError(409, "DEPLOY_FAILED", "Contract deployment reverted")
            contract = self._finalize_deploy(asset, res, receipt)

        # Resume-safe mint: settle any in-flight mint first, then mint only when nothing was issued yet.
        self._settle_pending_mint(asset)
        if self.gateway.total_supply(contract.address) == 0:
            h = self.gateway.mint(contract.address, treasury.address, asset.token_supply * WEI)
            tx = self.txs.add(ChainTransaction(
                tx_hash=h, asset_id=asset.id, kind="MINT", from_address=ZERO, to_address=treasury.address,
                amount=asset.token_supply * WEI, status=TxStatus.PENDING))
            self.s.commit()
            receipt = self.gateway.client.wait_receipt(h)  # RPC_TIMEOUT leaves the row PENDING
            tx.status = TxStatus.CONFIRMED if receipt.success else TxStatus.FAILED
            tx.block_number = receipt.block_number
            self.s.commit()
            if not receipt.success:
                raise AppError(409, "MINT_FAILED", "Initial mint failed on-chain")
            log.info("tokens_minted", asset=asset.asset_code, tx=h, block=receipt.block_number)

        ensure_transition(asset.status, AssetStatus.TOKENIZED)
        asset.status = AssetStatus.TOKENIZED
        self.s.commit()
        return contract

    def supply(self, asset_id: int) -> dict:
        c = self.contract(asset_id)
        return {"asset_id": asset_id, "symbol": c.symbol, "contract_address": c.address,
                "total_supply": fmt(self.gateway.total_supply(c.address)), "cap": fmt(c.cap)}
