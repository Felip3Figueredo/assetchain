import re

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

    def deploy(self, asset_id: int, idempotency_key: str | None) -> TokenContract:
        asset = self._asset(asset_id)
        contract = self.assets.contract_of(asset_id)

        if asset.status == AssetStatus.TOKENIZED and contract:
            prior = self.txs.by_idem(idempotency_key) if idempotency_key else None
            if prior and prior.asset_id == asset_id:
                return contract  # idempotent replay
            raise AppError(409, "ALREADY_TOKENIZED", "Asset is already tokenized")
        if asset.status == AssetStatus.DRAFT:
            raise AppError(409, "NOT_APPROVED", "Asset must be approved before tokenization")

        treasury = self.wallets.ensure_treasury()
        if contract is None:
            cap = asset.token_supply * WEI
            res = self.gateway.deploy(asset.name, symbol_for(asset), asset.asset_code, cap)
            contract = TokenContract(asset_id=asset.id, address=res.address, deploy_tx_hash=res.tx_hash,
                                     deployed_block=res.block, cap=cap, symbol=symbol_for(asset))
            self.s.add(contract)
            self.txs.add(ChainTransaction(
                tx_hash=res.tx_hash, asset_id=asset.id, kind="DEPLOY", from_address=self.gateway.deployer_address,
                to_address=res.address, amount=0, status=TxStatus.CONFIRMED, block_number=res.block,
                idempotency_key=idempotency_key))
            self.s.commit()
            log.info("contract_deployed", asset=asset.asset_code, address=res.address, block=res.block)

        # Resume-safe mint: only mint when nothing has been issued yet.
        if self.gateway.total_supply(contract.address) == 0:
            h = self.gateway.mint(contract.address, treasury.address, asset.token_supply * WEI)
            tx = self.txs.add(ChainTransaction(
                tx_hash=h, asset_id=asset.id, kind="MINT", from_address=ZERO, to_address=treasury.address,
                amount=asset.token_supply * WEI, status=TxStatus.PENDING))
            self.s.commit()
            receipt = self.gateway.client.wait_receipt(h)
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
