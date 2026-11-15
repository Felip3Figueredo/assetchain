BESU = -f docker-compose.yml -f infrastructure/docker-compose.besu.yml

.PHONY: up up-demo up-besu down test test-besu demo

up:            ## Hardhat stack (Phase 1)
	docker compose up --build

up-demo:       ## Same, with ASSET-001 already tokenized
	SEED_DEMO=true docker compose up --build

up-besu:       ## Permissioned Hyperledger Besu stack (Phase 2)
	docker compose $(BESU) up --build

down:
	docker compose $(BESU) down -v

test:          ## Contracts, backend (local Hardhat node) and frontend
	cd blockchain && npx hardhat test
	cd backend && .venv/bin/pytest -p no:warnings
	cd frontend && npm test

test-besu:     ## Backend suite against a running Besu network (make up-besu first)
	cd backend && TEST_RPC_URL=http://localhost:8545 TEST_CHAIN_ID=1337 .venv/bin/pytest -p no:warnings

demo:
	./scripts/demo.sh
