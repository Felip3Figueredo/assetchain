# API

Documentação interativa em `http://localhost:8000/docs`. Quantidades são strings decimais em tokens inteiros (ex.: `"100000"`). Erros: `{"error": {"code", "message"}}`. Com `API_KEY` configurada, envie `X-API-Key` (exceto em `/api/health`). `Idempotency-Key` é opcional nos `POST` de deploy e transferência.

| Método | Rota | Descrição |
| --- | --- | --- |
| POST | `/api/assets` | cadastra ativo (201) |
| GET | `/api/assets` · `/api/assets/{id}` | lista / detalha |
| PUT | `/api/assets/{id}` | edita (bloqueado após tokenizar) |
| POST | `/api/assets/{id}/approve` | aprova para tokenização |
| GET | `/api/assets/{id}/transactions` | movimentações do ativo |
| POST | `/api/tokenization/{asset_id}/deploy` | implanta contrato e emite |
| GET | `/api/tokenization/{asset_id}` | dados do contrato |
| GET | `/api/tokenization/{asset_id}/holders` | detentores (saldos on-chain) |
| GET | `/api/tokenization/{asset_id}/supply` | oferta e `cap` |
| POST | `/api/tokenization/{asset_id}/sync` | força reconciliação |
| POST | `/api/wallets` | cria carteira de teste (financiada com ETH de teste) |
| GET | `/api/wallets` · `/api/wallets/{address}` | lista / detalha |
| GET | `/api/wallets/{address}/balances` | saldos por ativo |
| GET | `/api/wallets/{address}/transactions` | histórico da carteira |
| POST | `/api/transactions/transfer` | transfere tokens |
| GET | `/api/transactions` · `/api/transactions/{hash}` | lista / detalha |
| GET | `/api/blockchain/status` · `/network` | estado da rede |
| GET | `/api/blockchain/blocks/latest` | último bloco |
| GET | `/api/blockchain/blocks?limit=20` | blocos recentes com o validador que propôs cada um |
| GET | `/api/blockchain/validators` | consenso, validadores, quórum, tolerância a falhas e pares |
| GET | `/api/blockchain/transactions/{hash}` | transação direto do nó |
| GET | `/api/blockchain/transactions/{hash}/propagation` | estado da transação em cada nó (recibo, hash do bloco, proponente) |
| GET | `/api/dashboard/stats` | métricas do painel |
| GET | `/api/health` | liveness |

## Códigos de erro principais

`ASSET_NOT_FOUND` 404 · `ASSET_CODE_EXISTS` 409 · `INVALID_STATE` 409 · `NOT_APPROVED` 409 · `ALREADY_TOKENIZED` 409 · `INSUFFICIENT_BALANCE` 422 · `INVALID_AMOUNT` 422 · `VALIDATION_ERROR` 422 · `CONTRACT_REVERT` 409 · `IDEMPOTENCY_KEY_REUSED` 409 · `DEPLOY_IN_PROGRESS` / `MINT_IN_PROGRESS` / `TRANSFER_IN_PROGRESS` 409 · `UNAUTHORIZED` 401 · `RPC_UNAVAILABLE` 503 · `RPC_TIMEOUT` 504.
