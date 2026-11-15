from tests.integration.conftest import SOLAR, create_approved, tokenize

TOTAL = 10_000_000


def test_asset_crud_and_state_machine(client):
    r = client.post("/api/assets", json=SOLAR)
    assert r.status_code == 201 and r.json()["status"] == "DRAFT"
    aid = r.json()["id"]
    assert client.post("/api/assets", json=SOLAR).status_code == 409  # duplicate code
    assert client.get("/api/assets").json()[0]["asset_code"] == "ASSET-001"
    r = client.put(f"/api/assets/{aid}", json={**SOLAR, "name": "Usina Solar Alpha II"})
    assert r.json()["name"] == "Usina Solar Alpha II"
    assert tokenize(client, aid).status_code == 409  # not approved yet
    assert client.post(f"/api/assets/{aid}/approve").json()["status"] == "APPROVED"
    assert client.post(f"/api/assets/{aid}/approve").status_code == 409
    assert client.get("/api/assets/999").status_code == 404


def test_invalid_input_is_422(client):
    assert client.post("/api/assets", json={**SOLAR, "token_supply": 0}).status_code == 422
    assert client.post("/api/wallets", json={"label": ""}).status_code == 422


def test_full_tokenization_and_transfer_flow(client):
    aid = create_approved(client)
    r = tokenize(client, aid)
    assert r.status_code == 200, r.text
    info = r.json()
    assert info["contract_address"].startswith("0x") and info["status"] == "TOKENIZED"
    assert client.get(f"/api/assets/{aid}").json()["status"] == "TOKENIZED"

    supply = client.get(f"/api/tokenization/{aid}/supply").json()
    assert supply["total_supply"] == str(TOTAL) and supply["cap"] == str(TOTAL)

    wallets = client.get("/api/wallets").json()
    treasury = next(w for w in wallets if w["label"] == "Tesouraria")
    b = client.post("/api/wallets", json={"label": "Carteira B"}).json()
    assert "private_key" not in b and "encrypted_key" not in b

    r = client.post("/api/transactions/transfer", headers={"Idempotency-Key": "t-1"},
                    json={"asset_id": aid, "from_address": treasury["address"], "to_address": b["address"],
                          "amount": "100000"})
    assert r.status_code == 201, r.text
    tx = r.json()
    assert tx["status"] == "CONFIRMED" and tx["block_number"] is not None
    assert tx["tx_hash"].startswith("0x")

    bal_b = client.get(f"/api/wallets/{b['address']}/balances").json()
    assert bal_b[0]["balance"] == "100000" and bal_b[0]["asset_code"] == "ASSET-001"
    bal_a = client.get(f"/api/wallets/{treasury['address']}/balances").json()
    assert bal_a[0]["balance"] == str(TOTAL - 100_000)

    detail = client.get(f"/api/transactions/{tx['tx_hash']}").json()
    assert detail["status"] == "CONFIRMED" and detail["chain"]["block_number"] == tx["block_number"]
    blk = client.get("/api/blockchain/blocks/latest").json()
    assert blk["number"] >= tx["block_number"]
    assert client.get(f"/api/blockchain/transactions/{tx['tx_hash']}").json()["block_number"] == tx["block_number"]
    assert len(client.get(f"/api/assets/{aid}/transactions").json()) >= 2  # mint + transfer
    holders = client.get(f"/api/tokenization/{aid}/holders").json()
    assert {h["address"]: h["balance"] for h in holders}[b["address"]] == "100000"
    assert client.get("/api/tokenization/{}".format(aid)).json()["contract_address"] == info["contract_address"]


def test_transfer_with_insufficient_balance_is_rejected(client):
    aid = create_approved(client)
    tokenize(client, aid)
    a = client.post("/api/wallets", json={"label": "Sem saldo"}).json()
    b = client.post("/api/wallets", json={"label": "Destino"}).json()
    before = len(client.get("/api/transactions").json())
    r = client.post("/api/transactions/transfer", json={
        "asset_id": aid, "from_address": a["address"], "to_address": b["address"], "amount": "5"})
    assert r.status_code == 422 and r.json()["error"]["code"] == "INSUFFICIENT_BALANCE"
    txs = client.get("/api/transactions").json()
    assert len(txs) == before and all(t["status"] == "CONFIRMED" for t in txs)


def test_transfer_idempotency_key_sends_only_one_transaction(client):
    aid = create_approved(client)
    tokenize(client, aid)
    t = next(w for w in client.get("/api/wallets").json() if w["label"] == "Tesouraria")
    b = client.post("/api/wallets", json={"label": "B"}).json()
    body = {"asset_id": aid, "from_address": t["address"], "to_address": b["address"], "amount": "10"}
    r1 = client.post("/api/transactions/transfer", headers={"Idempotency-Key": "same"}, json=body)
    r2 = client.post("/api/transactions/transfer", headers={"Idempotency-Key": "same"}, json=body)
    assert r1.json()["tx_hash"] == r2.json()["tx_hash"]
    assert client.get(f"/api/wallets/{b['address']}/balances").json()[0]["balance"] == "10"


def test_deploy_idempotency_and_double_deploy(client):
    aid = create_approved(client)
    r1 = tokenize(client, aid, "k")
    r2 = tokenize(client, aid, "k")
    assert r1.json()["contract_address"] == r2.json()["contract_address"]
    assert tokenize(client, aid, "other-key").status_code == 409


def test_invalid_addresses_and_amounts_are_422(client):
    aid = create_approved(client)
    tokenize(client, aid)
    base = {"asset_id": aid, "from_address": "0x123", "to_address": "nope", "amount": "1"}
    assert client.post("/api/transactions/transfer", json=base).status_code == 422
    t = next(w for w in client.get("/api/wallets").json() if w["label"] == "Tesouraria")
    ok = {**base, "from_address": t["address"], "to_address": t["address"]}
    assert client.post("/api/transactions/transfer", json={**ok, "amount": "0"}).status_code == 422
    assert client.post("/api/transactions/transfer", json={**ok, "amount": "-3"}).status_code == 422


def test_rpc_down_returns_503(client):
    aid = create_approved(client)
    client.app.state.gateway.client.w3.provider.endpoint_uri = "http://127.0.0.1:1"
    r = tokenize(client, aid)
    assert r.status_code == 503 and r.json()["error"]["code"] == "RPC_UNAVAILABLE"
    assert client.get(f"/api/assets/{aid}").json()["status"] == "APPROVED"
    s = client.get("/api/blockchain/status")
    assert s.status_code == 200 and s.json()["connected"] is False


def test_dashboard_stats(client):
    aid = create_approved(client)
    tokenize(client, aid)
    s = client.get("/api/dashboard/stats").json()
    assert s["assets"] == 1 and s["tokenized_assets"] == 1
    assert s["total_tokens_issued"] == str(TOTAL) and s["wallets"] >= 1
    assert s["chain"]["connected"] is True
