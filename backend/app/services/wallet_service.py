from eth_account import Account
from sqlalchemy.orm import Session

from app.blockchain.token import TokenGateway
from app.core.config import Settings
from app.core.errors import AppError
from app.core.logging import get_logger
from app.core.security import decrypt_key, encrypt_key
from app.domain.units import fmt
from app.models import Wallet
from app.repositories.repos import AssetRepo, WalletRepo
from app.schemas.api import BalanceOut

log = get_logger("wallets")
TREASURY_LABEL = "Tesouraria"
GAS_FUNDING_WEI = 10**18  # 1 test ETH (worthless local currency)


class WalletService:
    def __init__(self, session: Session, gateway: TokenGateway, settings: Settings) -> None:
        self.s, self.gateway, self.settings = session, gateway, settings
        self.repo = WalletRepo(session)

    def register(self, label: str, private_key: str, fund: bool = False) -> Wallet:
        """Register a TEST wallet. The key is stored encrypted (Fernet); never in plain text."""
        address = Account.from_key(private_key).address
        existing = self.repo.by_address(address)
        if existing:
            return existing
        wallet = self.repo.add(Wallet(address=address, label=label,
                                      encrypted_key=encrypt_key(private_key, self.settings.fernet_key)))
        self.s.commit()
        if fund:
            self._fund(address)
        log.info("wallet_registered", address=address, label=label)
        return wallet

    def create(self, label: str) -> Wallet:
        account = Account.create()
        return self.register(label, "0x" + account.key.hex().removeprefix("0x"), fund=True)

    def ensure_treasury(self) -> Wallet:
        return self.register(TREASURY_LABEL, self.settings.deployer_private_key)

    def _fund(self, address: str) -> None:
        client = self.gateway.client
        h = client.send_signed({"to": address, "value": GAS_FUNDING_WEI}, self.settings.deployer_private_key)
        if not client.wait_receipt(h).success:
            raise AppError(502, "FUNDING_FAILED", "Could not fund wallet with test ETH")

    def get(self, address: str) -> Wallet:
        w = self.repo.by_address(address)
        if w is None:
            raise AppError(404, "WALLET_NOT_FOUND", f"Wallet {address} not found")
        return w

    def private_key_of(self, wallet: Wallet) -> str:
        if not wallet.encrypted_key:
            raise AppError(422, "WALLET_NO_SIGNER", "This wallet has no signing key in the platform")
        return decrypt_key(wallet.encrypted_key, self.settings.fernet_key)

    def balances(self, address: str) -> list[BalanceOut]:
        self.get(address)
        out = []
        for c in AssetRepo(self.s).contracts():
            bal = self.gateway.balance_of(c.address, address)
            asset = AssetRepo(self.s).get(c.asset_id)
            out.append(BalanceOut(asset_id=c.asset_id, asset_code=asset.asset_code, symbol=c.symbol,
                                  contract_address=c.address, balance=fmt(bal)))
        return out
