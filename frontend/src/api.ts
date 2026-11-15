import type { Asset, Balance, Block, Holder, Stats, Supply, TokenInfo, Tx, Wallet } from "./types";

export class ApiError extends Error {
  constructor(public status: number, public code: string, message: string) { super(message); }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(path, { headers: { "Content-Type": "application/json" }, ...init });
  if (!res.ok) {
    let body: any = {};
    try { body = await res.json(); } catch { /* non-JSON error */ }
    throw new ApiError(res.status, body?.error?.code ?? "HTTP_ERROR", body?.error?.message ?? `Erro ${res.status}`);
  }
  return res.json() as Promise<T>;
}

const idem = () => `ui-${crypto.randomUUID()}`;

export const api = {
  stats: () => request<Stats>("/api/dashboard/stats"),
  assets: () => request<Asset[]>("/api/assets"),
  asset: (id: number) => request<Asset>(`/api/assets/${id}`),
  createAsset: (body: unknown) => request<Asset>("/api/assets", { method: "POST", body: JSON.stringify(body) }),
  approve: (id: number) => request<Asset>(`/api/assets/${id}/approve`, { method: "POST" }),
  deploy: (id: number) =>
    request<TokenInfo>(`/api/tokenization/${id}/deploy`, { method: "POST", headers: { "Content-Type": "application/json", "Idempotency-Key": idem() } }),
  tokenInfo: (id: number) => request<TokenInfo>(`/api/tokenization/${id}`),
  supply: (id: number) => request<Supply>(`/api/tokenization/${id}/supply`),
  holders: (id: number) => request<Holder[]>(`/api/tokenization/${id}/holders`),
  assetTxs: (id: number) => request<Tx[]>(`/api/assets/${id}/transactions`),
  wallets: () => request<Wallet[]>("/api/wallets"),
  createWallet: (label: string) => request<Wallet>("/api/wallets", { method: "POST", body: JSON.stringify({ label }) }),
  balances: (address: string) => request<Balance[]>(`/api/wallets/${address}/balances`),
  walletTxs: (address: string) => request<Tx[]>(`/api/wallets/${address}/transactions`),
  txs: () => request<Tx[]>("/api/transactions?limit=500"),
  transfer: (body: { asset_id: number; from_address: string; to_address: string; amount: string }) =>
    request<Tx>("/api/transactions/transfer", {
      method: "POST", headers: { "Content-Type": "application/json", "Idempotency-Key": idem() }, body: JSON.stringify(body),
    }),
  latestBlock: () => request<Block>("/api/blockchain/blocks/latest"),
};
