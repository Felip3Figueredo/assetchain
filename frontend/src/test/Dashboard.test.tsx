import { screen } from "@testing-library/react";
import Dashboard from "../pages/Dashboard";
import { mockApi, renderPage } from "./helpers";

const stats = {
  assets: 2, tokenized_assets: 1, total_tokens_issued: "10000000", wallets: 3, transactions: 3,
  chain: { connected: true, chain_id: 31337, block_number: 7, client_version: "HardhatNetwork/2" },
};

test("dashboard shows the headline numbers and chain status", async () => {
  mockApi({ "/api/dashboard/stats": stats, "/api/transactions": [], "/api/assets": [] });
  renderPage(<Dashboard />);
  expect(await screen.findByText("10.000.000")).toBeInTheDocument();
  expect(screen.getByText("Tokens emitidos")).toBeInTheDocument();
  expect(screen.getByText(/Rede conectada/)).toBeInTheDocument();
  expect(screen.getByText(/31337/)).toBeInTheDocument();
});

test("dashboard tells the user when the chain is offline", async () => {
  mockApi({ "/api/dashboard/stats": { ...stats, chain: { connected: false, chain_id: null, block_number: null, client_version: null } },
    "/api/transactions": [], "/api/assets": [] });
  renderPage(<Dashboard />);
  expect(await screen.findByText(/Rede offline/)).toBeInTheDocument();
});
