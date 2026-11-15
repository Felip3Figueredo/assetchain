import type { ReactNode } from "react";
import { shortHash } from "./format";

export function Card({ title, action, children, className = "" }: { title?: string; action?: ReactNode; children: ReactNode; className?: string }) {
  return (
    <section className={`card ${className}`}>
      {(title || action) && (
        <header className="flex items-center justify-between border-b border-paper-line px-4 py-3">
          <h2 className="text-base font-semibold">{title}</h2>
          {action}
        </header>
      )}
      {children}
    </section>
  );
}

export function Stat({ label, value, hint }: { label: string; value: ReactNode; hint?: string }) {
  return (
    <div className="card px-4 py-4">
      <p className="text-sm text-muted">{label}</p>
      <p className="mt-1 font-display text-3xl font-bold leading-none">{value}</p>
      {hint && <p className="mt-2 text-xs text-muted">{hint}</p>}
    </div>
  );
}

const STATUS: Record<string, { label: string; cls: string }> = {
  CONFIRMED: { label: "Confirmada", cls: "bg-emerald-50 text-ok" },
  PENDING: { label: "Pendente", cls: "bg-solar-soft text-solar-deep" },
  FAILED: { label: "Falhou", cls: "bg-red-50 text-bad" },
  DRAFT: { label: "Rascunho", cls: "bg-slate-100 text-muted" },
  APPROVED: { label: "Aprovado", cls: "bg-solar-soft text-solar-deep" },
  TOKENIZED: { label: "Tokenizado", cls: "bg-emerald-50 text-ok" },
};

export function StatusBadge({ status }: { status: string }) {
  const s = STATUS[status] ?? { label: status, cls: "bg-slate-100 text-muted" };
  return <span className={`inline-flex rounded-full px-2.5 py-0.5 text-xs font-medium ${s.cls}`}>{s.label}</span>;
}

export function Hash({ value }: { value: string | null | undefined }) {
  if (!value) return <span className="text-muted">—</span>;
  return <span title={value} className="font-mono text-xs">{shortHash(value)}</span>;
}

export function Empty({ children }: { children: ReactNode }) {
  return <p className="px-4 py-10 text-center text-sm text-muted">{children}</p>;
}

export function ErrorNote({ error }: { error: unknown }) {
  if (!error) return null;
  return <p role="alert" className="rounded-md bg-red-50 px-3 py-2 text-sm text-bad">{(error as Error).message}</p>;
}

export function PageHeader({ title, subtitle, action }: { title: string; subtitle?: string; action?: ReactNode }) {
  return (
    <div className="mb-6 flex flex-wrap items-end justify-between gap-3">
      <div>
        <h1 className="text-3xl font-bold">{title}</h1>
        {subtitle && <p className="mt-1 max-w-2xl text-sm text-muted">{subtitle}</p>}
      </div>
      {action}
    </div>
  );
}
