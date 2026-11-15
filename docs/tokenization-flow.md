# Fluxo de tokenização

| # | Passo | Endpoint | Resultado |
| --- | --- | --- | --- |
| 1 | Cadastrar ativo | `POST /api/assets` | `DRAFT` |
| 2 | Aprovar | `POST /api/assets/{id}/approve` | `APPROVED` |
| 3 | Implantar ERC-20 | `POST /api/tokenization/{id}/deploy` | contrato + mint inicial |
| 4 | Consultar oferta | `GET /api/tokenization/{id}/supply` | oferta lida on-chain |
| 5 | Transferir | `POST /api/transactions/transfer` | `PENDING` → `CONFIRMED` |
| 6 | Saldos | `GET /api/wallets/{address}/balances` | saldo lido on-chain |
| 7 | Hash e bloco | `GET /api/blockchain/transactions/{hash}` | dados do nó |

## Regras

- Deploy só para ativos `APPROVED`; repetir o deploy retorna 409 (ou o mesmo resultado, com a mesma `Idempotency-Key`).
- O deploy é retomável: se o contrato foi implantado mas o mint falhou, uma nova chamada emite sem reimplantar.
- A transferência valida saldo antes de enviar e nunca marca `CONFIRMED` sem recibo `status == 1`.
- Falhas de RPC não deixam estado inconsistente: o ativo permanece `APPROVED` se o deploy não concluiu.
- Se o recibo do deploy ou da emissão não chegar a tempo (504), a transação fica `PENDING` com o hash; repetir a chamada (mesma chave) consulta a chain e conclui sem reimplantar nem emitir de novo. Se ainda não foi minerada, retorna 409 `DEPLOY_IN_PROGRESS` / `MINT_IN_PROGRESS`.
