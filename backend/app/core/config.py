from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict

# Well-known Hardhat test account #0 (public, worthless). Never use real keys.
HARDHAT_ACCOUNT_0 = "0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+psycopg://assetchain:assetchain@localhost:5432/assetchain"
    rpc_url: str = "http://127.0.0.1:8545"
    chain_id: int = 31337
    deployer_private_key: str = HARDHAT_ACCOUNT_0
    fernet_key: str = ""
    artifact_path: str = "../blockchain/artifacts-export/AssetToken.json"
    gas_price_mode: str = "auto"  # "auto" | "zero" (permissioned chains with free gas)
    receipt_timeout_s: int = 60
    log_level: str = "INFO"


@lru_cache
def get_settings() -> Settings:
    return Settings()
