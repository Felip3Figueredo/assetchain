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

## Ver o consenso na tela

Abra **Rede** no dashboard (http://localhost:5173/network). A página mostra o consenso (QBFT), os 4 validadores, o quórum (3 votos), quantos blocos cada validador propôs nos últimos 20 e quem propôs cada bloco, atualizando a cada 3 segundos. Endpoints: `GET /api/blockchain/validators` e `GET /api/blockchain/blocks?limit=20`.

Teste de tolerância a falhas:

```bash
docker stop assetchain-besu-4-1     # 1 de 4 validadores cai: a rede continua produzindo blocos
docker stop assetchain-besu-3-1     # 2 de 4 caem: sem quórum (3), os blocos param
docker start assetchain-besu-3-1 assetchain-besu-4-1
```

Com um validador fora, a tela mostra "Sem propor nos últimos blocos" para ele (após cerca de 40 s, quando a janela de 20 blocos já passou por todo o rodízio) e o aviso de pares desconectados. Em rede Hardhat a página explica que é um nó único.

## Ver o fluxo de uma transação entre os nós

Em **Transações**, clique no hash (ou em "Ver fluxo entre os nós" depois de transferir). A tela `/transactions/{hash}` mostra:

1. qual nó recebeu a transação da API (o nó de entrada, `besu-1`);
2. qual validador **propôs** o bloco que a contém;
3. o estado em **cada um dos 4 nós**, consultado agora pelo JSON-RPC de cada um: tem o recibo? o hash do bloco é o mesmo?

Os passos marcados "Lido nos nós" são medidos; os marcados "Como funciona" (propagação P2P e votos PREPARE/COMMIT) são explicação, porque a rede não expõe a hora de cada repasse nem os votos individuais. Para ver a diferença entre nós: derrube o `assetchain-besu-4-1`, faça uma transferência e abra o fluxo (mostra "3 de 4 nós" e o nó 4 "Sem resposta"). Ao religar, o nó se sincroniza sozinho em cerca de 45 s e a tela volta a "4 de 4".

A API sabe quais nós consultar pela variável `NODE_RPC_URLS` (`Nome|endereço do validador|url;...`, já configurada em `docker-compose.besu.yml`). Sem ela, consulta só o nó do `RPC_URL`.

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
