import { useRef, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Cell, Pie, PieChart, ResponsiveContainer, Tooltip } from "recharts";
import { useParams } from "react-router-dom";
import { api, newIdempotencyKey } from "../api";
import { formatBrl, formatTokens } from "../format";
import { Card, Empty, ErrorNote, Hash, PageHeader, StatusBadge } from "../ui";
import { TxTable } from "./Transactions";
import { PALETTE } from "./Dashboard";

function TransferForm({ assetId }: { assetId: number }) {
  const qc = useQueryClient();
  const wallets = useQuery({ queryKey: ["wallets"], queryFn: api.wallets });
  const [from, setFrom] = useState("");
  const [to, setTo] = useState("");
  const [amount, setAmount] = useState("100000");
  // One key per distinct transfer: retries after a timeout reuse it, editing the form or succeeding rotates it.
  const key = useRef(newIdempotencyKey());
  const rotate = () => { key.current = newIdempotencyKey(); };
  const m = useMutation({
    mutationFn: () => api.transfer({ asset_id: assetId, from_address: from, to_address: to, amount }, key.current),
    onSuccess: () => { rotate(); qc.invalidateQueries(); },
  });
  const list = wallets.data ?? [];
  const opts = list.map((w) => <option key={w.address} value={w.address}>{w.label} — {w.address.slice(0, 8)}…</option>);
  return (
    <form className="grid gap-3 p-4 sm:grid-cols-4" onSubmit={(e) => { e.preventDefault(); m.mutate(); }}>
      <label className="text-sm"><span className="text-muted">De</span>
        <select className="input mt-1" required value={from} onChange={(e) => { rotate(); setFrom(e.target.value); }}><option value="">Selecione</option>{opts}</select></label>
      <label className="text-sm"><span className="text-muted">Para</span>
        <select className="input mt-1" required value={to} onChange={(e) => { rotate(); setTo(e.target.value); }}><option value="">Selecione</option>{opts}</select></label>
      <label className="text-sm"><span className="text-muted">Quantidade</span>
        <input className="input mt-1" required inputMode="decimal" value={amount} onChange={(e) => { rotate(); setAmount(e.target.value); }} /></label>
      <div className="flex items-end"><button className="btn-primary w-full" disabled={m.isPending}>{m.isPending ? "Aguardando bloco…" : "Transferir tokens"}</button></div>
      <div className="sm:col-span-4">
        <ErrorNote error={m.error} />
        {m.data && m.data.status === "FAILED" && <p role="alert" className="rounded-md bg-red-50 px-3 py-2 text-sm text-bad">A transação foi revertida na blockchain. Hash: <Hash value={m.data.tx_hash} /></p>}
        {m.data && m.data.status !== "FAILED" && <p className="rounded-md bg-emerald-50 px-3 py-2 text-sm text-ok">Transferência {m.data.status === "CONFIRMED" ? "confirmada" : "enviada (aguardando bloco)"}{m.data.block_number != null ? ` no bloco ${m.data.block_number}` : ""}. Hash: <Hash value={m.data.tx_hash} /></p>}
      </div>
    </form>
  );
}

function TokenSection({ id }: { id: number }) {
  const info = useQuery({ queryKey: ["token", id], queryFn: () => api.tokenInfo(id) });
  const supply = useQuery({ queryKey: ["supply", id], queryFn: () => api.supply(id) });
  const holders = useQuery({ queryKey: ["holders", id], queryFn: () => api.holders(id) });
  const h = holders.data ?? [];
  return (
    <>
      <div className="mt-4 grid gap-4 lg:grid-cols-5">
        <Card title="Distribuição de tokens" className="lg:col-span-2">
          <div className="h-56 p-3">
            {h.length === 0 ? <Empty>Sem detentores.</Empty> : (
              <ResponsiveContainer width="100%" height="100%"><PieChart>
                <Pie isAnimationActive={false} data={h.map((x) => ({ name: x.label ?? x.address.slice(0, 8), value: Number(x.balance) }))} dataKey="value" innerRadius={45} outerRadius={80}>
                  {h.map((_, i) => <Cell key={i} fill={PALETTE[i % PALETTE.length]} />)}
                </Pie><Tooltip formatter={(v: number) => formatTokens(v)} /></PieChart></ResponsiveContainer>)}
          </div>
        </Card>
        <Card title="Carteiras participantes" className="lg:col-span-3">
          {h.length === 0 ? <Empty>Nenhum detentor ainda.</Empty> : (
            <table className="w-full"><thead><tr className="border-b border-paper-line"><th className="th">Carteira</th><th className="th">Saldo</th><th className="th">%</th></tr></thead>
              <tbody>{h.map((x) => (
                <tr key={x.address} className="border-b border-paper-line last:border-0">
                  <td className="td">{x.label ?? "Externa"} <Hash value={x.address} /></td>
                  <td className="td">{formatTokens(x.balance)}</td><td className="td">{x.share_pct.toFixed(2)}%</td></tr>))}</tbody></table>)}
        </Card>
      </div>
      <Card title="Contrato inteligente" className="mt-4">
        {info.data && supply.data && (
          <dl className="grid gap-x-6 gap-y-3 p-4 text-sm sm:grid-cols-2">
            {([
              ["Endereço", <span className="break-all font-mono text-xs">{info.data.contract_address}</span>],
              ["Símbolo", info.data.symbol], ["Rede", `chain ${info.data.chain_id}`],
              ["Implantado no bloco", info.data.deployed_block],
              ["Hash da implantação", <Hash value={info.data.deploy_tx_hash} />],
              ["Oferta atual (on-chain)", `${formatTokens(supply.data.total_supply)} ${supply.data.symbol}`],
              ["Limite máximo (cap)", formatTokens(supply.data.cap)],
            ] as [string, React.ReactNode][]).map(([k, v]) => (
              <div key={k}><dt className="text-muted">{k}</dt><dd className="mt-0.5">{v}</dd></div>))}
          </dl>)}
      </Card>
    </>
  );
}

export default function AssetDetail() {
  const id = Number(useParams().id);
  const qc = useQueryClient();
  const asset = useQuery({ queryKey: ["asset", id], queryFn: () => api.asset(id) });
  const txs = useQuery({ queryKey: ["asset-txs", id], queryFn: () => api.assetTxs(id) });
  const approve = useMutation({ mutationFn: () => api.approve(id), onSuccess: () => qc.invalidateQueries() });
  const deployKey = useRef(newIdempotencyKey());
  const deploy = useMutation({
    mutationFn: () => api.deploy(id, deployKey.current),
    onSuccess: () => { deployKey.current = newIdempotencyKey(); qc.invalidateQueries(); },
  });
  const a = asset.data;
  if (asset.error) return <ErrorNote error={asset.error} />;
  if (!a) return <Empty>Carregando…</Empty>;

  return (
    <>
      <PageHeader title={a.name} subtitle={`${a.asset_code} · ${a.category}`} action={<StatusBadge status={a.status} />} />
      <Card title="Informações do empreendimento">
        <dl className="grid gap-x-6 gap-y-3 p-4 text-sm sm:grid-cols-3">
          <div><dt className="text-muted">Valor estimado</dt><dd className="mt-0.5 font-medium">{formatBrl(a.estimated_value_brl)}</dd></div>
          <div><dt className="text-muted">Tokens</dt><dd className="mt-0.5 font-medium">{formatTokens(a.token_supply)}</dd></div>
          <div><dt className="text-muted">Valor representativo por token</dt><dd className="mt-0.5 font-medium">{formatBrl(a.token_price_brl)}</dd></div>
          {a.description && <div className="sm:col-span-3"><dt className="text-muted">Descrição</dt><dd className="mt-0.5">{a.description}</dd></div>}
        </dl>
        <div className="flex flex-wrap items-center gap-3 border-t border-paper-line p-4">
          {a.status === "DRAFT" && <button className="btn-solar" disabled={approve.isPending} onClick={() => approve.mutate()}>Aprovar para tokenização</button>}
          {a.status === "APPROVED" && <button className="btn-solar" disabled={deploy.isPending} onClick={() => deploy.mutate()}>
            {deploy.isPending ? "Implantando…" : "Implantar contrato e emitir tokens"}</button>}
          <ErrorNote error={approve.error ?? deploy.error} />
          <p className="text-xs text-muted">Os tokens representam participações econômicas fictícias e não representam propriedade jurídica sobre o ativo.</p>
        </div>
      </Card>

      {a.status === "TOKENIZED" && (
        <>
          <TokenSection id={id} />
          <Card title="Transferir tokens" className="mt-4"><TransferForm assetId={id} /></Card>
        </>
      )}
      <Card title="Histórico de movimentações" className="mt-4">
        {txs.data ? <TxTable txs={txs.data} /> : <Empty>Carregando…</Empty>}
      </Card>
    </>
  );
}
