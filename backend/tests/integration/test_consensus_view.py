from tests.integration.conftest import create_approved, tokenize


def test_blocks_endpoint_lists_recent_blocks_with_their_proposer(client):
    aid = create_approved(client)
    tokenize(client, aid)
    blocks = client.get("/api/blockchain/blocks?limit=5").json()
    assert 1 <= len(blocks) <= 5
    numbers = [b["number"] for b in blocks]
    assert numbers == sorted(numbers, reverse=True)
    b = blocks[0]
    assert b["hash"].startswith("0x") and b["proposer"].startswith("0x") and "tx_count" in b


def test_blocks_limit_is_validated(client):
    assert client.get("/api/blockchain/blocks?limit=0").status_code == 422
    assert client.get("/api/blockchain/blocks?limit=500").status_code == 422


def test_validators_endpoint_describes_the_consensus(client):
    v = client.get("/api/blockchain/validators").json()
    if client.app_state.settings.poa_chain:  # Besu QBFT network (make test-besu)
        assert v["consensus"] == "QBFT" and v["count"] == 4
        assert v["fault_tolerance"] == 1 and v["quorum"] == 3
        assert len(v["validators"]) == 4 and v["peer_count"] == 3
    else:  # Hardhat: single automining node, no validator set
        assert v["consensus"] == "automine" and v["validators"] == [] and v["count"] == 0
