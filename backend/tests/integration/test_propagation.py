from app.blockchain.propagation import parse_nodes
from tests.integration.conftest import create_approved, tokenize


def _transfer(client):
    aid = create_approved(client)
    tokenize(client, aid)
    a = next(w for w in client.get("/api/wallets").json() if w["label"] == "Tesouraria")["address"]
    b = client.post("/api/wallets", json={"label": "B"}).json()["address"]
    return client.post("/api/transactions/transfer", json={
        "asset_id": aid, "from_address": a, "to_address": b, "amount": "10"}).json()


def test_parse_nodes_reads_name_address_and_url():
    nodes = parse_nodes("Validador 1|0xAb|http://a:8545;Validador 2|0xCd|http://b:8545")
    assert [(n.name, n.address, n.url) for n in nodes] == [
        ("Validador 1", "0xAb", "http://a:8545"), ("Validador 2", "0xCd", "http://b:8545")]
    assert parse_nodes("") == []


def test_propagation_reports_every_node_holding_the_same_block(client):
    tx = _transfer(client)
    p = client.get(f"/api/blockchain/transactions/{tx['tx_hash']}/propagation").json()
    assert p["tx_hash"] == tx["tx_hash"] and p["block_number"] == tx["block_number"]
    assert p["proposer"].startswith("0x") and p["block_hash"].startswith("0x")
    assert len(p["nodes"]) >= 1 and p["in_sync"] is True
    n = p["nodes"][0]
    assert n["reachable"] and n["has_tx"] and n["block_hash"] == p["block_hash"] and n["is_entry"] is True


def test_propagation_flags_an_unreachable_node_without_failing(client):
    tx = _transfer(client)
    client.app_state.settings.node_rpc_urls = "Fora do ar|0x0|http://127.0.0.1:1"
    p = client.get(f"/api/blockchain/transactions/{tx['tx_hash']}/propagation").json()
    down = next(n for n in p["nodes"] if n["name"] == "Fora do ar")
    assert down["reachable"] is False and down["has_tx"] is False
    assert p["in_sync"] is False


def test_propagation_unknown_hash_is_404(client):
    assert client.get("/api/blockchain/transactions/0x" + "00" * 32 + "/propagation").status_code == 404
