from app.models import TokenContract
from app.services.health import stale_contracts
from tests.integration.conftest import create_approved, tokenize


def test_detects_db_contracts_that_no_longer_exist_on_chain(client):
    gw = client.app_state.gateway
    aid = create_approved(client)
    tokenize(client, aid)
    s = client.app_state.session_factory()
    assert stale_contracts(s, gw) == []
    # simulate a chain reset: DB still points at an address with no code
    c = s.query(TokenContract).one()
    c.address = "0x000000000000000000000000000000000000dEaD"
    s.commit()
    assert stale_contracts(s, gw) == ["ASSET-001"]
