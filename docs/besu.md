# Fase 2 — Hyperledger Besu (rede permissionada)

A mesma aplicação roda sobre uma rede **permissionada** Hyperledger Besu, sem alterar código de negócio: só configuração de rede.

## Topologia

- 4 validadores Besu com consenso **QBFT** (finalidade imediata, tolera 1 nó com falha), blocos a cada 2 s.
- **Permissionamento de nós**: apenas os 4 enodes listados em `infrastructure/besu/permissions_config.toml` entram na rede.
- Chain ID `1337`, gás gratuito (`zeroBaseFee` + `--min-gas-price=0`), típico de redes corporativas.
- `besu-1` expõe o JSON-RPC em `localhost:8545` e responde ao hostname `chain` dentro do Docker.
- Chaves dos nós e contas pré-financiadas são **de teste**, versionadas de propósito (as contas são as públicas do Hardhat).

## Executar

```bash
make up-besu          # docker compose -f docker-compose.yml -f infrastructure/docker-compose.besu.yml up --build
./scripts/demo.sh     # mesmo cenário da Fase 1: deploy, emissão, transferência, saldos, hash e bloco
make test-besu        # suíte do backend (inclusive o fluxo completo) contra o Besu
```

Verificações úteis:

```bash
curl -s -X POST localhost:8545 -H 'content-type: application/json' \
  --data '{"jsonrpc":"2.0","id":1,"method":"qbft_getValidatorsByBlockNumber","params":["latest"]}'
curl -s -X POST localhost:8545 -H 'content-type: application/json' \
  --data '{"jsonrpc":"2.0","id":1,"method":"net_peerCount","params":[]}'   # 0x3
```

## O que muda em relação ao Hardhat

| Configuração | Hardhat (Fase 1) | Besu (Fase 2) |
| --- | --- | --- |
| `CHAIN_ID` | 31337 | 1337 |
| `POA_CHAIN` | `false` | `true` — blocos QBFT têm `extraData` longo; o Web3.py precisa do middleware PoA |
| `GAS_PRICE_MODE` | `auto` | `zero` — rede sem taxa de gás |
| Consenso | automine, nó único | QBFT, 4 validadores |
| Acesso | qualquer nó | nós permissionados |

## Limites

- O permissionamento é por **nó**. Permissionamento por **conta** (allowlist de endereços) não foi habilitado porque a plataforma cria carteiras dinamicamente; seria necessário registrar cada nova conta na allowlist.
- Sem privacidade de transações (Tessera) e sem governança de validadores via contrato.
- Os dados do Besu são efêmeros no compose (`down -v` reinicia a rede e o banco juntos).
