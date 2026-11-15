const nf = new Intl.NumberFormat("pt-BR", { maximumFractionDigits: 6 });

export function formatTokens(v: string | number): string {
  return nf.format(Number(v));
}
export function formatBrl(v: string | number): string {
  return new Intl.NumberFormat("pt-BR", { style: "currency", currency: "BRL" }).format(Number(v));
}
export function shortHash(h: string | null | undefined): string {
  if (!h) return "—";
  return h.length <= 14 ? h : `${h.slice(0, 6)}…${h.slice(-4)}`;
}
export function formatDate(iso: string): string {
  return new Date(iso).toLocaleString("pt-BR", { dateStyle: "short", timeStyle: "short" });
}
