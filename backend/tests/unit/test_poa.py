from app.blockchain.client import ChainClient
from app.core.config import Settings


def _n(poa: bool) -> int:
    s = Settings(_env_file=None, database_url="sqlite://", poa_chain=poa)
    return len(list(ChainClient(s).w3.middleware_onion))


def test_poa_flag_adds_extradata_middleware_for_qbft_chains():
    assert _n(True) == _n(False) + 1
