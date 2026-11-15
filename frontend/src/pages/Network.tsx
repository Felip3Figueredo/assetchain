import { useQuery } from "@tanstack/react-query";
import { api } from "../api";
import { formatDate, shortHash } from "../format";
import { Card, Empty, ErrorNote, Hash, PageHeader, Stat } from "../ui";

const LIVE = { refetchInterval: 3000 };
const WINDOW = 20;

export default function Network() {
  const cons = useQuery({ queryKey: ["consensus"], queryFn: api.validators, ...LIVE });
  const blocks = useQuery({ queryKey: ["blocks"], queryFn: () => api.blocks(WINDOW), ...LIVE });
  const c = cons.data;
  const bl = blocks.data ?? [];
  const proposed = (addr: string) => bl.filter((b) => b.proposer === addr).length;
  const indexOf = (addr: string) => (c?.validators ?? []).indexOf(addr);
  // After a full rotation plus margin, a validator with zero proposals is probably down.
  const judgeable = !!c && bl.length >= c.count + 2;

  return (
    <>
      <PageHeader title="Rede"
        subtitle="Consenso da blockchain: quem valida os blocos e quem propôs cada um. Atualiza a cada 3 segundos." />
      <ErrorNote error={cons.error ?? blocks.error} />
      {c && (
        <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
          <Stat label="Consenso" value={c.consensus} hint={c.consensus === "QBFT" ? "Votação entre validadores autorizados" : "Rede de nó único: um nó gera todos os blocos"} />
          <Stat label="Validadores" value={c.count || "—"} hint={c.count ? `tolera ${c.fault_tolerance} validador com falha` : undefined} />
          <Stat label="Quórum de votos" value={c.quorum || "—"} hint={c.count ? `Mais de 2/3 dos ${c.count} validadores` : undefined} />
          <Stat label="Pares conectados" value={c.peer_count} hint={c.count ? `Esperado: ${c.count - 1}` : undefined} />
        </div>
      )}

      {c && c.count > 0 && (
        <Card title={`Validadores (últimos ${bl.length} blocos)`} className="mt-4">
          <table className="w-full">
            <thead><tr className="border-b border-paper-line"><th className="th">Validador</th><th className="th">Endereço</th><th className="th">Blocos propostos</th><th className="th">Situação</th></tr></thead>
            <tbody>
              {c.validators.map((v, i) => {
                const n = proposed(v);
                const down = judgeable && n === 0;
                return (
                  <tr key={v} className="border-b border-paper-line last:border-0">
                    <td className="td font-medium">Validador {i + 1}</td>
                    <td className="td"><Hash value={v} /></td>
                    <td className="td">
                      <div className="flex items-center gap-2">
                        <div className="h-2 w-32 rounded bg-paper"><div className={`h-2 rounded ${down ? "bg-bad" : "bg-solar"}`} style={{ width: `${bl.length ? (n / bl.length) * 100 : 0}%` }} /></div>
                        <span className="text-sm">{n}</span>
                      </div>
                    </td>
                    <td className="td">{down
                      ? <span className="rounded-full bg-red-50 px-2.5 py-0.5 text-xs font-medium text-bad">Sem propor nos últimos blocos</span>
                      : <span className="rounded-full bg-emerald-50 px-2.5 py-0.5 text-xs font-medium text-ok">Ativo</span>}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
          {c.peer_count < c.count - 1 && <p className="border-t border-paper-line px-4 py-3 text-sm text-bad">Este nó enxerga {c.peer_count} de {c.count - 1} pares: algum validador está desconectado.</p>}
        </Card>
      )}

      <Card title="Blocos recentes" className="mt-4">
        {bl.length === 0 ? <Empty>Carregando blocos…</Empty> : (
          <div className="overflow-x-auto">
            <table className="w-full min-w-[640px]">
              <thead><tr className="border-b border-paper-line">{["Bloco", "Hash", "Proposto por", "Transações", "Data"].map((h) => <th key={h} className="th">{h}</th>)}</tr></thead>
              <tbody>
                {bl.map((b) => {
                  const i = indexOf(b.proposer);
                  return (
                    <tr key={b.number} className="border-b border-paper-line last:border-0">
                      <td className="td font-medium">#{b.number}</td>
                      <td className="td"><Hash value={b.hash} /></td>
                      <td className="td">{i >= 0 ? `Validador ${i + 1}` : <span title={b.proposer} className="font-mono text-xs">{shortHash(b.proposer)}</span>}</td>
                      <td className="td">{b.tx_count}</td>
                      <td className="td whitespace-nowrap">{formatDate(new Date(b.timestamp * 1000).toISOString())}</td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </Card>
    </>
  );
}
