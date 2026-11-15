import { screen } from "@testing-library/react";
import Transactions from "../pages/Transactions";
import { mockApi, renderPage } from "./helpers";

const tx = {
  id: 1, tx_hash: "0x" + "ab".repeat(32), asset_id: 1, asset_code: "ASSET-001", kind: "TRANSFER",
  from_address: "0x" + "11".repeat(20), to_address: "0x" + "22".repeat(20), amount: "100000",
  status: "CONFIRMED", block_number: 12, error: null, created_at: "2026-11-15T12:00:00Z",
};

test("transactions table shows hash, amount, status and block", async () => {
  mockApi({ "/api/transactions": [tx] });
  renderPage(<Transactions />);
  expect(await screen.findByText("0xabab…abab")).toBeInTheDocument();
  expect(screen.getByText("100.000")).toBeInTheDocument();
  expect(screen.getByText("Confirmada")).toBeInTheDocument();
  expect(screen.getByText("12")).toBeInTheDocument();
});

test("transactions page has an empty state", async () => {
  mockApi({ "/api/transactions": [] });
  renderPage(<Transactions />);
  expect(await screen.findByText(/Nenhuma transação ainda/)).toBeInTheDocument();
});
