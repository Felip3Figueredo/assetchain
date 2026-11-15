export interface Asset {
  id: number; asset_code: string; name: string; category: string; description: string;
  estimated_value_brl: string | number; token_supply: number; token_price_brl: string | number;
  status: "DRAFT" | "APPROVED" | "TOKENIZED"; metadata: Record<string, unknown>;
  contract_address: string | null; created_at: string;
}
export interface Wallet { address: string; label: string; can_sign: boolean; created_at: string }
export interface Balance { asset_id: number; asset_code: string; symbol: string; contract_address: string; balance: string }
export interface Tx {
  id: number; tx_hash: string | null; asset_id: number; asset_code: string; kind: string;
  from_address: string; to_address: string; amount: string;
  status: "PENDING" | "CONFIRMED" | "FAILED"; block_number: number | null; error: string | null; created_at: string;
}
export interface ChainStatus { connected: boolean; chain_id: number | null; block_number: number | null; client_version: string | null }
export interface Stats {
  assets: number; tokenized_assets: number; total_tokens_issued: string; wallets: number; transactions: number; chain: ChainStatus;
}
export interface TokenInfo {
  asset_id: number; asset_code: string; status: string; contract_address: string; symbol: string; name: string;
  deploy_tx_hash: string; deployed_block: number; cap: string; chain_id: number;
}
export interface Holder { address: string; label: string | null; balance: string; share_pct: number }
export interface Supply { total_supply: string; cap: string; symbol: string; contract_address: string }
export interface Block { number: number; hash: string; parent_hash: string; timestamp: number; tx_count: number; gas_used: number }
export interface Consensus { consensus: "QBFT" | "automine"; validators: string[]; count: number; fault_tolerance: number; quorum: number; peer_count: number }
export interface ChainBlock { number: number; hash: string; timestamp: number; tx_count: number; gas_used: number; proposer: string }
export interface NodeView { name: string; address: string; is_entry: boolean; reachable: boolean; has_tx: boolean; block_number: number | null; block_hash: string | null; latency_ms: number | null; in_block: boolean }
export interface Propagation {
  tx_hash: string; status: "PENDING" | "CONFIRMED" | "FAILED"; from_address?: string; to_address?: string | null;
  block_number: number | null; block_hash: string | null; block_timestamp?: number; proposer: string | null;
  nodes: NodeView[]; in_sync: boolean;
}
