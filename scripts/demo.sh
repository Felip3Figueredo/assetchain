#!/usr/bin/env bash
# AssetChain demo: runs the full tokenization scenario against a running stack.
# Usage: ./scripts/demo.sh [API_URL]   (default http://localhost:8000)
set -euo pipefail
API="${1:-http://localhost:8000}"
j() { python3 -c "import sys,json; d=json.load(sys.stdin); print($1)"; }
step() { printf '\n\033[1;36m== %s\033[0m\n' "$1"; }
call() { curl -fsS ${API_KEY:+-H "X-API-Key: $API_KEY"} "$@"; }

step "1. Blockchain status"
call "$API/api/blockchain/status" | python3 -m json.tool

step "2. Seeded asset (ASSET-001)"
ASSET=$(call "$API/api/assets" | j "[a['id'] for a in d if a['asset_code']=='ASSET-001'][0]")
echo "asset id: $ASSET"

step "3. Approve asset (ignored if already approved)"
call -X POST "$API/api/assets/$ASSET/approve" >/dev/null 2>&1 || echo "already approved"

step "4. Deploy ERC-20 + mint 10,000,000 tokens (idempotent)"
call -X POST -H "Idempotency-Key: demo-deploy-$ASSET" "$API/api/tokenization/$ASSET/deploy" | python3 -m json.tool

step "5. Wallets"
A=$(call "$API/api/wallets" | j "[w['address'] for w in d if w['label']=='Tesouraria'][0]")
B=$(call "$API/api/wallets" | j "[w['address'] for w in d if w['label']=='Carteira B'][0]")
echo "A (treasury): $A"; echo "B: $B"

step "6. Transfer 100,000 tokens A -> B"
TX=$(call -X POST -H "Content-Type: application/json" -H "Idempotency-Key: demo-transfer-$(date +%s)" \
  -d "{\"asset_id\": $ASSET, \"from_address\": \"$A\", \"to_address\": \"$B\", \"amount\": \"100000\"}" \
  "$API/api/transactions/transfer")
echo "$TX" | python3 -m json.tool
HASH=$(echo "$TX" | j "d['tx_hash']")

step "7. Updated balances"
echo "A:"; call "$API/api/wallets/$A/balances" | python3 -m json.tool
echo "B:"; call "$API/api/wallets/$B/balances" | python3 -m json.tool

step "8. Transaction hash and block recorded on-chain"
call "$API/api/blockchain/transactions/$HASH" | python3 -m json.tool

step "9. Latest block"
call "$API/api/blockchain/blocks/latest" | python3 -m json.tool
printf '\n\033[1;32mDone. Open the dashboard at http://localhost:5173\033[0m\n'
