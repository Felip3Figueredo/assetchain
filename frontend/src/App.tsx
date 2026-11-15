import { NavLink, Route, Routes } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { api } from "./api";
import Dashboard from "./pages/Dashboard";
import Assets from "./pages/Assets";
import AssetDetail from "./pages/AssetDetail";
import Wallets from "./pages/Wallets";
import Transactions from "./pages/Transactions";

const NAV = [
  { to: "/", label: "Painel", end: true },
  { to: "/assets", label: "Ativos" },
  { to: "/wallets", label: "Carteiras" },
  { to: "/transactions", label: "Transações" },
];

function Sidebar() {
  const { data } = useQuery({ queryKey: ["chain-status"], queryFn: api.stats });
  const c = data?.chain;
  return (
    <aside className="bg-ink-900 text-white md:fixed md:inset-y-0 md:w-60">
      <div className="flex items-center gap-3 px-5 py-5">
        <svg width="28" height="28" viewBox="0 0 32 32" aria-hidden><rect width="32" height="32" rx="7" fill="#173B41" /><path d="M8 20l8-12 8 12-8 4z" fill="#F2A71B" /></svg>
        <span className="font-display text-xl font-bold">AssetChain</span>
      </div>
      <nav className="flex gap-1 overflow-x-auto px-3 pb-3 md:flex-col md:pb-0" aria-label="Principal">
        {NAV.map((n) => (
          <NavLink key={n.to} to={n.to} end={n.end}
            className={({ isActive }) => `whitespace-nowrap rounded-md px-3 py-2 text-sm ${isActive ? "bg-ink-700 font-medium text-solar" : "text-slate-300 hover:bg-ink-800"}`}>
            {n.label}
          </NavLink>
        ))}
      </nav>
      <div className="hidden px-5 md:absolute md:inset-x-0 md:bottom-0 md:block md:pb-5">
        <p className="flex items-center gap-2 text-xs text-slate-300">
          <span className={`inline-block h-2 w-2 rounded-full ${c?.connected ? "bg-emerald-400" : "bg-red-400"}`} />
          {c?.connected ? `Chain ${c.chain_id} · bloco ${c.block_number}` : "Rede offline"}
        </p>
        <p className="mt-3 text-[11px] leading-snug text-slate-400">
          Projeto educacional. Ativos fictícios e moedas de teste, sem valor financeiro.
        </p>
      </div>
    </aside>
  );
}

export default function App() {
  return (
    <div className="min-h-screen">
      <Sidebar />
      <main className="mx-auto max-w-6xl px-4 py-6 md:ml-60 md:px-8 md:py-8">
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/assets" element={<Assets />} />
          <Route path="/assets/:id" element={<AssetDetail />} />
          <Route path="/wallets" element={<Wallets />} />
          <Route path="/transactions" element={<Transactions />} />
        </Routes>
      </main>
    </div>
  );
}
