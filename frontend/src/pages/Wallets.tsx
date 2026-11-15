import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "../api";
import { formatTokens } from "../format";
import { Card, Empty, ErrorNote, Hash, PageHeader } from "../ui";
import { TxTable } from "./Transactions";

function WalletRow({ address, label, selected, onSelect }: { address: string; label: string; selected: boolean; onSelect: () => void }) {
  const bal = useQuery({ queryKey: ["balances", address], queryFn: () => api.balances(address) });
  return (
    <tr className={`cursor-pointer border-b border-paper-line last:border-0 ${selected ? "bg-solar-soft/60" : "hover:bg-paper/60"}`} onClick={onSelect}>
      <td className="td"><button className="font-medium underline-offset-2 hover:underline" onClick={onSelect}>{label}</button></td>
      <td className="td"><span className="break-all font-mono text-xs">{address}</span></td>
      <td className="td">
        {(bal.data ?? []).filter((b) => Number(b.balance) > 0).map((b) => (
          <div key={b.asset_id}>{formatTokens(b.balance)} <span className="text-muted">{b.symbol}</span></div>
        ))}
        {bal.data && bal.data.every((b) => Number(b.balance) === 0) && <span className="text-muted">Sem tokens</span>}
      </td>
    </tr>
  );
}

export default function Wallets() {
  const qc = useQueryClient();
  const wallets = useQuery({ queryKey: ["wallets"], queryFn: api.wallets });
  const [selected, setSelected] = useState<string | null>(null);
  const [label, setLabel] = useState("");
  const create = useMutation({ mutationFn: () => api.createWallet(label), onSuccess: () => { setLabel(""); qc.invalidateQueries(); } });
  const sel = selected ?? wallets.data?.[0]?.address ?? null;
  const history = useQuery({ queryKey: ["wallet-txs", sel], queryFn: () => api.walletTxs(sel!), enabled: !!sel });

  return (
    <>
      <PageHeader title="Carteiras" subtitle="Carteiras de teste. As chaves privadas ficam criptografadas no servidor e nunca saem da API." />
      <Card title="Nova carteira de teste" className="mb-4">
        <form className="flex flex-wrap items-end gap-3 p-4" onSubmit={(e) => { e.preventDefault(); create.mutate(); }}>
          <label className="min-w-[220px] flex-1 text-sm"><span className="text-muted">Nome</span>
            <input className="input mt-1" required value={label} onChange={(e) => setLabel(e.target.value)} placeholder="Ex.: Investidora Maria" /></label>
          <button className="btn-solar" disabled={create.isPending}>Criar carteira</button>
          <div className="w-full"><ErrorNote error={create.error} /></div>
        </form>
      </Card>
      <Card>
        {!wallets.data ? <Empty>Carregando…</Empty> : wallets.data.length === 0 ? <Empty>Nenhuma carteira. Crie a primeira acima.</Empty> : (
          <div className="overflow-x-auto"><table className="w-full min-w-[640px]">
            <thead><tr className="border-b border-paper-line"><th className="th">Nome</th><th className="th">Endereço</th><th className="th">Saldo de tokens</th></tr></thead>
            <tbody>{wallets.data.map((w) => <WalletRow key={w.address} address={w.address} label={w.label} selected={w.address === sel} onSelect={() => setSelected(w.address)} />)}</tbody>
          </table></div>)}
      </Card>
      {sel && (
        <Card title="Histórico da carteira selecionada" className="mt-4" action={<Hash value={sel} />}>
          {history.data ? <TxTable txs={history.data} /> : <Empty>Carregando…</Empty>}
        </Card>)}
    </>
  );
}
