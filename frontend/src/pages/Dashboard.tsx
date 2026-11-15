import { useQuery } from "@tanstack/react-query";
import { Area, AreaChart, CartesianGrid, Cell, Pie, PieChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { api } from "../api";
import { formatTokens } from "../format";
import { Card, Empty, ErrorNote, PageHeader, Stat } from "../ui";
import { TxTable } from "./Transactions";
import type { Asset, Tx } from "../types";

export const PALETTE = ["#0E2A2F", "#F2A71B", "#2E7D8C", "#B97800", "#7FA8AE", "#C2412D"];

function movements(txs: Tx[]) {
  const by = new Map<string, number>();
  txs.filter((t) => t.kind === "TRANSFER" && t.status === "CONFIRMED").forEach((t) => {
    const day = t.created_at.slice(0, 10);
    by.set(day, (by.get(day) ?? 0) + Number(t.amount));
  });
  return [...by.entries()].sort().map(([day, volume]) => ({ day: day.slice(5).replace("-", "/"), volume }));
}

function distribution(assets: Asset[]) {
  return assets.filter((a) => a.status === "TOKENIZED").map((a) => ({ name: a.name, value: a.token_supply }));
}

export default function Dashboard() {
  const stats = useQuery({ queryKey: ["stats"], queryFn: api.stats });
  const txs = useQuery({ queryKey: ["txs"], queryFn: api.txs });
  const assets = useQuery({ queryKey: ["assets"], queryFn: api.assets });
  const s = stats.data;
  const series = movements(txs.data ?? []);
  const dist = distribution(assets.data ?? []);

  return (
    <>
      <PageHeader title="Painel"
        subtitle="Visão geral da plataforma: ativos fictícios tokenizados como ERC-20 em uma blockchain EVM local." />
      <ErrorNote error={stats.error} />
      {s && (
        <p className={`mb-4 inline-flex items-center gap-2 rounded-full px-3 py-1 text-sm ${s.chain.connected ? "bg-emerald-50 text-ok" : "bg-red-50 text-bad"}`}>
          <span className={`h-2 w-2 rounded-full ${s.chain.connected ? "bg-ok" : "bg-bad"}`} />
          {s.chain.connected ? `Rede conectada · chain ${s.chain.chain_id} · bloco ${s.chain.block_number}` : "Rede offline — inicie o nó EVM"}
        </p>
      )}
      <div className="grid grid-cols-2 gap-3 lg:grid-cols-5">
        <Stat label="Ativos cadastrados" value={s?.assets ?? "—"} />
        <Stat label="Ativos tokenizados" value={s?.tokenized_assets ?? "—"} />
        <Stat label="Tokens emitidos" value={s ? formatTokens(s.total_tokens_issued) : "—"} />
        <Stat label="Carteiras" value={s?.wallets ?? "—"} />
        <Stat label="Transações" value={s?.transactions ?? "—"} />
      </div>

      <div className="mt-6 grid gap-4 lg:grid-cols-5">
        <Card title="Movimentação diária (tokens)" className="lg:col-span-3">
          <div className="h-64 p-3">
            {series.length === 0 ? <Empty>Sem transferências confirmadas ainda.</Empty> : (
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={series}>
                  <CartesianGrid stroke="#D8E0E2" vertical={false} />
                  <XAxis dataKey="day" tick={{ fontSize: 12 }} /><YAxis tick={{ fontSize: 12 }} width={70} tickFormatter={(v) => formatTokens(v)} />
                  <Tooltip formatter={(v: number) => formatTokens(v)} />
                  <Area dataKey="volume" name="Tokens movimentados" stroke="#B97800" fill="#F2A71B" fillOpacity={0.35} />
                </AreaChart>
              </ResponsiveContainer>
            )}
          </div>
        </Card>
        <Card title="Tokens por ativo" className="lg:col-span-2">
          <div className="h-64 p-3">
            {dist.length === 0 ? <Empty>Nenhum ativo tokenizado.</Empty> : (
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie data={dist} dataKey="value" nameKey="name" innerRadius={50} outerRadius={85}>
                    {dist.map((_, i) => <Cell key={i} fill={PALETTE[i % PALETTE.length]} />)}
                  </Pie>
                  <Tooltip formatter={(v: number) => formatTokens(v)} />
                </PieChart>
              </ResponsiveContainer>
            )}
          </div>
        </Card>
      </div>

      <Card title="Últimas transações" className="mt-4">
        <TxTable txs={(txs.data ?? []).slice(0, 6)} />
      </Card>
    </>
  );
}
