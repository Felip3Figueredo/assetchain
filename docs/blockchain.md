# Blockchain e segurança

## Contrato `AssetToken`

`blockchain/contracts/AssetToken.sol` combina `ERC20`, `ERC20Capped` e `Ownable` do OpenZeppelin 5.

- Nome, símbolo, `assetId` e `cap` definidos no deploy; o `cap` é imutável (não existe emissão ilimitada).
- `mint(to, amount)` é restrito ao dono e reverte acima do `cap` (`ERC20ExceededCap`).
- Eventos: `Transfer` (padrão ERC-20) e `AssetMinted(assetId, to, amount)`.
- 18 casas decimais. A API usa quantidades em tokens inteiros/decimais e converte para a menor unidade.

## Integração Python ↔ Solidity

1. `npx hardhat compile` gera artefatos; `scripts/export-artifact.ts` grava `artifacts-export/AssetToken.json`.
2. `TokenGateway` carrega ABI e bytecode e implanta/chama o contrato com Web3.py.
3. `ChainClient.send_signed` preenche nonce, simula com `estimate_gas` (detecta reverts antes do envio), assina localmente e envia a transação crua.

## Limites de segurança do ambiente experimental

- **Chave da tesouraria pública.** O padrão usa a conta nº 0 do Hardhat; qualquer pessoa conhece essa chave. Use somente em rede local descartável.
- **Chave mestra Fernet** vem do `.env`. O valor padrão do compose é de demonstração; gere a sua.
- **Sem autenticação.** Qualquer cliente que alcance a API pode operar. Seria o primeiro requisito em uma versão real.
- **Sem KYC/AML, custódia ou conformidade legal.** Tokens são participações econômicas fictícias, sem efeito jurídico.
- **Sem dados pessoais** on-chain.

## Rede pública × permissionada

A aplicação roda sobre Hardhat (efêmera, nó único). A Fase 2 leva a mesma aplicação para Hyperledger Besu, uma rede permissionada com consenso QBFT, mudando apenas a configuração de rede.
