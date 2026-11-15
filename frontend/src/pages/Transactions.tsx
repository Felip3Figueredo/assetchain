import { useQuery } from "@tanstack/react-query";
import { api } from "../api";
import { formatDate, formatTokens } from "../format";
import { Card, Empty, ErrorNote, Hash, PageHeader, StatusBadge } from "../ui";
import type { Tx } from "../types";

export function TxTable({ txs }: { txs: Tx[] }) {
  if (txs.length === 0) return <Empty>Nenhuma transação ainda. Tokenize um ativo e transfira tokens para ver o histórico aqui.</Empty>;
  return (
    <div className="overflow-x-auto">
      <table className="w-full min-w-[760px]">
        <thead><tr className="border-b border-paper-line">
          {["Hash", "Tipo", "Origem", "Destino", "Quantidade", "Data", "Status", "Bloco"].map((h) => <th key={h} className="th">{h}</th>)}
        </tr></thead>
        <tbody>
          {txs.map((t) => (
            <tr key={t.id} className="border-b border-paper-line last:border-0">
              <td className="td"><Hash value={t.tx_hash} /></td>
              <td className="td">{t.kind === "MINT" ? "Emissão" : t.kind === "DEPLOY" ? "Implantação" : "Transferência"}</td>
              <td className="td"><Hash value={t.from_address} /></td>
              <td className="td"><Hash value={t.to_address} /></td>
              <td className="td text-right">{t.kind === "DEPLOY" ? "—" : formatTokens(t.amount)}</td>
              <td className="td whitespace-nowrap">{formatDate(t.created_at)}</td>
              <td className="td"><StatusBadge status={t.status} /></td>
              <td className="td">{t.block_number ?? "—"}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export default function Transactions() {
  const { data, error } = useQuery({ queryKey: ["txs"], queryFn: api.txs });
  return (
    <>
      <PageHeader title="Transações" subtitle="Cada linha é uma operação registrada na blockchain local. O status só vira Confirmada após o recibo do bloco." />
      <ErrorNote error={error} />
      <Card>{data ? <TxTable txs={data} /> : <Empty>Carregando…</Empty>}</Card>
    </>
  );
}
