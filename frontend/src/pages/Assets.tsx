import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { api } from "../api";
import { formatBrl, formatTokens } from "../format";
import { Card, Empty, ErrorNote, Hash, PageHeader, StatusBadge } from "../ui";

const EMPTY = { asset_code: "", name: "", category: "", description: "", estimated_value_brl: "", token_supply: "", token_price_brl: "1.00" };

function NewAssetForm({ onDone }: { onDone: () => void }) {
  const qc = useQueryClient();
  const [f, setF] = useState(EMPTY);
  const m = useMutation({
    mutationFn: () => api.createAsset({ ...f, estimated_value_brl: Number(f.estimated_value_brl), token_supply: Number(f.token_supply), token_price_brl: Number(f.token_price_brl) }),
    onSuccess: () => { qc.invalidateQueries(); setF(EMPTY); onDone(); },
  });
  const field = (k: keyof typeof EMPTY, label: string, type = "text") => (
    <label className="block text-sm">
      <span className="text-muted">{label}</span>
      <input className="input mt-1" type={type} required value={f[k]} onChange={(e) => setF({ ...f, [k]: e.target.value })} />
    </label>
  );
  return (
    <form className="grid gap-3 p-4 sm:grid-cols-2" onSubmit={(e) => { e.preventDefault(); m.mutate(); }}>
      {field("asset_code", "Identificador (ex.: ASSET-003)")}
      {field("name", "Nome do ativo")}
      {field("category", "Categoria")}
      {field("description", "Descrição")}
      {field("estimated_value_brl", "Valor estimado (R$)", "number")}
      {field("token_supply", "Quantidade de tokens", "number")}
      {field("token_price_brl", "Valor por token (R$)", "number")}
      <div className="flex items-end gap-3">
        <button className="btn-primary" disabled={m.isPending}>Cadastrar ativo</button>
      </div>
      <div className="sm:col-span-2"><ErrorNote error={m.error} /></div>
    </form>
  );
}

export default function Assets() {
  const { data, error } = useQuery({ queryKey: ["assets"], queryFn: api.assets });
  const [open, setOpen] = useState(false);
  return (
    <>
      <PageHeader title="Ativos" subtitle="Ativos fictícios do mundo real. Cada ativo tokenizado tem seu próprio contrato ERC-20."
        action={<button className="btn-solar" onClick={() => setOpen(!open)}>{open ? "Fechar" : "Cadastrar ativo"}</button>} />
      {open && <Card title="Novo ativo" className="mb-4"><NewAssetForm onDone={() => setOpen(false)} /></Card>}
      <ErrorNote error={error} />
      <Card>
        {!data ? <Empty>Carregando…</Empty> : data.length === 0 ? <Empty>Nenhum ativo cadastrado. Use “Cadastrar ativo” para começar.</Empty> : (
          <div className="overflow-x-auto">
            <table className="w-full min-w-[720px]">
              <thead><tr className="border-b border-paper-line">
                {["Ativo", "Categoria", "Valor estimado", "Tokens", "Contrato", "Status"].map((h) => <th key={h} className="th">{h}</th>)}
              </tr></thead>
              <tbody>
                {data.map((a) => (
                  <tr key={a.id} className="border-b border-paper-line last:border-0 hover:bg-paper/60">
                    <td className="td"><Link to={`/assets/${a.id}`} className="font-medium underline-offset-2 hover:underline">{a.name}</Link>
                      <div className="font-mono text-xs text-muted">{a.asset_code}</div></td>
                    <td className="td">{a.category}</td>
                    <td className="td whitespace-nowrap">{formatBrl(a.estimated_value_brl)}</td>
                    <td className="td">{formatTokens(a.token_supply)}</td>
                    <td className="td"><Hash value={a.contract_address} /></td>
                    <td className="td"><StatusBadge status={a.status} /></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>
    </>
  );
}
