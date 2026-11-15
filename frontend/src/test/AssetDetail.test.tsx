import { screen } from "@testing-library/react";
import { Route, Routes } from "react-router-dom";
import AssetDetail from "../pages/AssetDetail";
import { mockApi, renderPage } from "./helpers";

const asset = {
  id: 1, asset_code: "ASSET-001", name: "Usina Solar Alpha", category: "Energia renovável", description: "Usina fictícia",
  estimated_value_brl: "10000000.00", token_supply: 10000000, token_price_brl: "1.000000", status: "APPROVED",
  metadata: {}, contract_address: null, created_at: "2026-11-15T12:00:00Z",
};

test("approved asset offers the deploy action and explains it is not legal ownership", async () => {
  mockApi({ "/api/assets/1/transactions": [], "/api/assets/1": asset, "/api/wallets": [] });
  renderPage(<Routes><Route path="/assets/:id" element={<AssetDetail />} /></Routes>, "/assets/1");
  expect(await screen.findByRole("button", { name: "Implantar contrato e emitir tokens" })).toBeInTheDocument();
  expect(screen.getByText(/não representam propriedade jurídica/)).toBeInTheDocument();
});

import userEvent from "@testing-library/user-event";

test("retrying a failed deploy reuses the same Idempotency-Key", async () => {
  const keys: string[] = [];
  globalThis.fetch = vi.fn(async (url: string, init?: RequestInit) => {
    const u = String(url);
    if (u.includes("/deploy")) {
      keys.push((init!.headers as Record<string, string>)["Idempotency-Key"]);
      return new Response(JSON.stringify({ error: { code: "RPC_UNAVAILABLE", message: "down" } }), { status: 503 });
    }
    if (u.startsWith("/api/assets/1/transactions")) return new Response("[]");
    if (u.startsWith("/api/assets/1")) return new Response(JSON.stringify(asset));
    return new Response("[]");
  }) as unknown as typeof fetch;
  renderPage(<Routes><Route path="/assets/:id" element={<AssetDetail />} /></Routes>, "/assets/1");
  const btn = await screen.findByRole("button", { name: "Implantar contrato e emitir tokens" });
  await userEvent.click(btn);
  await screen.findByText("down");
  await userEvent.click(await screen.findByRole("button", { name: "Implantar contrato e emitir tokens" }));
  await vi.waitFor(() => expect(keys.length).toBe(2));
  expect(keys[0]).toBe(keys[1]);
});
