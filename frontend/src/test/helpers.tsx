import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import type { ReactElement } from "react";

export function mockApi(routes: Record<string, unknown>) {
  globalThis.fetch = vi.fn(async (url: string) => {
    const key = Object.keys(routes).find((k) => String(url).startsWith(k));
    if (!key) return new Response(JSON.stringify({ error: { code: "NOT_FOUND", message: "nf" } }), { status: 404 });
    return new Response(JSON.stringify(routes[key]), { status: 200 });
  }) as unknown as typeof fetch;
}

export function renderPage(ui: ReactElement, path = "/") {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(<QueryClientProvider client={qc}><MemoryRouter initialEntries={[path]}>{ui}</MemoryRouter></QueryClientProvider>);
}
