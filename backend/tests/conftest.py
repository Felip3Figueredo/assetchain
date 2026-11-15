import os
import shutil
import socket
import subprocess
import time
from pathlib import Path

import pytest
from web3 import Web3

ROOT = Path(__file__).resolve().parents[2]
ARTIFACT = ROOT / "blockchain" / "artifacts-export" / "AssetToken.json"
PORT = int(os.environ.get("TEST_CHAIN_PORT", "8546"))

# Hardhat default test accounts (public, worthless)
KEYS = [
    "0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80",
    "0x59c6995e998f97a5a0044966f0945389dc9e86dae88c7a8412f4603b6b78690d",
    "0x5de4111afa1a4b94908f83103eb1f1706367c2e68ca870fc3fb9a804cdab365a",
]


def _port_open(port: int) -> bool:
    with socket.socket() as s:
        s.settimeout(0.3)
        return s.connect_ex(("127.0.0.1", port)) == 0


@pytest.fixture(scope="session")
def chain_url():
    """Local Hardhat EVM node (real JSON-RPC) shared by the whole test session."""
    url = f"http://127.0.0.1:{PORT}"
    proc = None
    if not _port_open(PORT):
        npx = shutil.which("npx")
        proc = subprocess.Popen(
            [npx, "hardhat", "node", "--port", str(PORT)],
            cwd=ROOT / "blockchain", stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )
        for _ in range(100):
            if _port_open(PORT):
                break
            time.sleep(0.3)
        else:
            proc.kill()
            pytest.fail("hardhat node did not start")
        time.sleep(0.5)
    yield url
    if proc:
        proc.terminate()


@pytest.fixture()
def settings(chain_url, monkeypatch):
    from app.core.config import Settings

    return Settings(
        _env_file=None, rpc_url=chain_url, chain_id=31337, database_url="sqlite://",
        deployer_private_key=KEYS[0], artifact_path=str(ARTIFACT),
        fernet_key="", receipt_timeout_s=20,
    )


@pytest.fixture()
def w3(chain_url):
    return Web3(Web3.HTTPProvider(chain_url))
