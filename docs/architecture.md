# Arquitetura

## Visão geral

Monorepo com quatro partes independentes: `blockchain/` (contratos + nó local), `backend/` (API Python), `frontend/` (React) e `infrastructure/` (Docker Compose).

```
assetchain/
├── backend/app/
│   ├── api/            rotas REST e injeção de dependências
│   ├── services/       regras de negócio (assets, carteiras, tokenização, transações, indexador)
│   ├── repositories/   acesso a dados (SQLAlchemy)
│   ├── blockchain/     ChainClient e TokenGateway (Web3.py)
│   ├── domain/         máquina de estados do ativo, conversão de unidades
│   ├── models/ schemas/ core/
├── blockchain/         AssetToken.sol, testes Hardhat, export de ABI+bytecode
├── frontend/           SPA React + TypeScript
└── infrastructure/     docker-compose.yml
```

## Decisões

- **Um contrato por ativo.** Isolamento total entre ativos: cada contrato tem seu próprio `cap`, dono e eventos. Um factory economizaria gás, mas acoplaria os ativos.
- **Deploy pelo backend.** O Hardhat compila e exporta `AssetToken.json` (ABI + bytecode); o backend implanta com Web3.py. Assim a aplicação é independente do Hardhat em tempo de execução e pode apontar para outra rede (`RPC_URL`).
- **Blockchain como fonte de verdade.** Saldos e oferta são lidos on-chain. O banco guarda metadados, referências e eventos indexados.
- **Confirmação por recibo.** Transações nascem `PENDING` com o hash e só viram `CONFIRMED`/`FAILED` após o recibo. Se o recibo atrasar, o reconciliador resolve depois.
- **Reconciliação.** `Indexer.sync` lê eventos `Transfer`, grava em `indexed_events` e cria registros para atividade que não passou pela API; também liquida transações `PENDING`.
- **Idempotência.** O cabeçalho `Idempotency-Key` (coluna única) evita duplicar deploy e transferências.
- **Chaves.** Carteiras criadas pela plataforma guardam a chave privada criptografada (Fernet). Veja os limites em [blockchain.md](blockchain.md).
- **Testes sem SQLite escondendo a chain.** Os testes usam SQLite para o banco, mas sempre uma chain Hardhat real. Valores em wei são armazenados como texto (`WeiInt`) para não perder precisão.
- **Agnóstico de rede.** `RPC_URL`, `CHAIN_ID` e `GAS_PRICE_MODE` bastam para trocar de rede.

## Estados do ativo

`DRAFT → APPROVED → TOKENIZED` (transições inválidas retornam 409).

## Erros

Falhas viram JSON `{"error": {"code", "message"}}`. RPC fora do ar → 503 `RPC_UNAVAILABLE`; revert de contrato → 409 `CONTRACT_REVERT`; saldo insuficiente → 422 `INSUFFICIENT_BALANCE`.
