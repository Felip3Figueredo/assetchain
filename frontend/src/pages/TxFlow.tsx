import type { ReactNode } from "react";
import { useQuery } from "@tanstack/react-query";
import { Link, useParams } from "react-router-dom";
import { api } from "../api";
import { Card, Empty, ErrorNote, Hash, PageHeader, StatusBadge } from "../ui";
import type { NodeView } from "../types";

function Step({ n, title, kind, children, last }: { n: number; title: string; kind: "medido" | "explicação"; children: ReactNode; last?: boolean }) {
  return (
    <li className="flex gap-4">
      <div className="flex flex-col items-center">
        <span className={`flex h-8 w-8 items-center justify-center rounded-full text-sm font-semibold ${kind === "medido" ? "bg-ink-900 text-solar" : "border border-paper-line bg-white text-muted"}`}>{n}</span>
        {!last && <span className="mt-1 w-px flex-1 bg-paper-line" />}
      </div>
      <div className="pb-6">
        <div className="flex flex-wrap items-center gap-2">
          <h3 className="text-base font-semibold">{title}</h3>
          <span className={`rounded-full px-2 py-0.5 text-[11px] ${kind === "medido" ? "bg-emerald-50 text-ok" : "bg-slate-100 text-muted"}`}>{kind === "medido" ? "Lido nos nós" : "Como funciona"}</span>
        </div>
        <div className="mt-1 text-sm text-ink-700">{children}</div>
      </div>
    </li>
  );
}

function nodeState(n: NodeView) {
  if (!n.reachable) return <span className="rounded-full bg-red-50 px-2.5 py-0.5 text-xs font-medium text-bad">Sem resposta</span>;
  if (n.in_block) return <span className="rounded-full bg-emerald-50 px-2.5 py-0.5 text-xs font-medium text-ok">Mesmo bloco</span>;
  if (n.has_tx) return <span className="rounded-full bg-red-50 px-2.5 py-0.5 text-xs font-medium text-bad">Bloco divergente</span>;
  return <span className="rounded-full bg-solar-soft px-2.5 py-0.5 text-xs font-medium text-solar-deep">Ainda sem o bloco</span>;
}

export default function TxFlow() {
  const hash = useParams().hash ?? "";
  const q = useQuery({ queryKey: ["propagation", hash], queryFn: () => api.propagation(hash), refetchInterval: 3000 });
  const p = q.data;
  const nodes = p?.nodes ?? [];
  const entry = nodes.find((n) => n.is_entry);
  const proposer = nodes.find((n) => n.address && n.address === p?.proposer);
  const have = nodes.filter((n) => n.in_block).length;

  return (
    <>
      <PageHeader title="Fluxo da transação" subtitle="Como a transação saiu da API, foi proposta por um validador e chegou a cada nó da rede."
        action={<Link to="/transactions" className="btn-ghost">Voltar às transações</Link>} />
      <ErrorNote error={q.error} />
      {!p ? <Empty>Consultando os nós…</Empty> : p.status === "PENDING" ? (
        <Card title="Aguardando bloco"><Empty>Esta transação ainda não foi incluída em um bloco. A página atualiza sozinha.</Empty></Card>
      ) : (
        <>
          <Card className="mb-4">
            <div className="flex flex-wrap items-center gap-x-6 gap-y-2 px-4 py-3 text-sm">
              <span className="text-muted">Hash</span><span className="break-all font-mono text-xs">{p.tx_hash}</span>
              <StatusBadge status={p.status} />
              <span className="text-muted">Bloco</span><span className="font-medium">#{p.block_number}</span>
            </div>
          </Card>

          <Card title="Caminho da transação">
            <ol className="p-5">
              <Step n={1} title={`Recebida pelo ${entry?.name ?? "nó de entrada"}`} kind="medido">
                A API assinou a transferência com a chave da carteira e a enviou por JSON-RPC ao nó de entrada.
                <div className="mt-1 text-xs text-muted">De <Hash value={p.from_address} /> para o contrato <Hash value={p.to_address} /></div>
              </Step>
              <Step n={2} title="Propagada aos pares" kind="explicação">
                O nó de entrada guarda a transação no pool e a repassa aos outros nós pela rede P2P. A rede não registra a hora exata de cada repasse; o que dá para confirmar é o resultado nos nós, no passo 5.
              </Step>
              <Step n={3} title={proposer ? `Proposto pelo ${proposer.name}` : "Bloco proposto"} kind="medido">
                O validador da vez montou o bloco #{p.block_number} com esta transação.
                <div className="mt-1 text-xs text-muted">Endereço do proponente: <Hash value={p.proposer} /> · hash do bloco <Hash value={p.block_hash} /></div>
              </Step>
              <Step n={4} title="Votação QBFT" kind="explicação">
                Os validadores trocam votos (PREPARE e COMMIT). Com mais de 2/3 de concordância (3 de 4) o bloco é finalizado: não existe reorganização depois disso.
              </Step>
              <Step n={5} title={`Presente em ${have} de ${nodes.length} nós`} kind="medido" last>
                Cada nó foi consultado agora pelo seu próprio JSON-RPC: tem o recibo da transação e o mesmo hash para o bloco #{p.block_number}?
              </Step>
            </ol>
          </Card>

          <Card title="Estado em cada nó" className="mt-4">
            <div className="overflow-x-auto">
              <table className="w-full min-w-[620px]">
                <thead><tr className="border-b border-paper-line">{["Nó", "Endereço", "Papel", "Resposta", "Situação"].map((h) => <th key={h} className="th">{h}</th>)}</tr></thead>
                <tbody>
                  {nodes.map((n) => (
                    <tr key={n.name} className="border-b border-paper-line last:border-0">
                      <td className="td font-medium">{n.name}</td>
                      <td className="td"><Hash value={n.address || null} /></td>
                      <td className="td text-sm">{[n.is_entry && "Entrada da API", n.address === p.proposer && "Proponente"].filter(Boolean).join(" · ") || "—"}</td>
                      <td className="td text-sm">{n.reachable ? `${n.latency_ms} ms` : "—"}</td>
                      <td className="td">{nodeState(n)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            {!p.in_sync && <p className="border-t border-paper-line px-4 py-3 text-sm text-bad">Nem todos os nós têm o bloco. Um nó parado alcança os demais sozinho quando volta (sincronização).</p>}
          </Card>
        </>
      )}
    </>
  );
}
