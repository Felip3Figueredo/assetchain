import { screen, within } from "@testing-library/react";
import { Route, Routes } from "react-router-dom";
import TxFlow from "../pages/TxFlow";
import { mockApi, renderPage } from "./helpers";

const H = "0x" + "ab".repeat(32);
const BH = "0x" + "cd".repeat(32);
const A = ["0x" + "11".repeat(20), "0x" + "22".repeat(20), "0x" + "33".repeat(20), "0x" + "44".repeat(20)];
const node = (i: number, over = {}) => ({
  name: `Validador ${i + 1}`, address: A[i], is_entry: i === 0, reachable: true, has_tx: true, block_number: 7,
  block_hash: BH, latency_ms: 12, in_block: true, ...over,
});
const base = { tx_hash: H, status: "CONFIRMED", from_address: A[0], to_address: A[1], block_number: 7, block_hash: BH,
  block_timestamp: 1790000000, proposer: A[2] };

function show(p: object) {
  mockApi({ [`/api/blockchain/transactions/${H}/propagation`]: p });
  renderPage(<Routes><Route path="/transactions/:hash" element={<TxFlow />} /></Routes>, `/transactions/${H}`);
}

test("shows entry node, proposer, and that every node holds the same block", async () => {
  show({ ...base, in_sync: true, nodes: [0, 1, 2, 3].map((i) => node(i)) });
  expect(await screen.findByText("Proposto pelo Validador 3")).toBeInTheDocument();
  expect(screen.getByText(/Recebida pelo Validador 1/)).toBeInTheDocument();
  expect(screen.getByText(/4 de 4 nós/)).toBeInTheDocument();
  const table = screen.getByRole("table");
  expect(within(table).getAllByText("Mesmo bloco")).toHaveLength(4);
});

test("flags a node that is down or missing the block", async () => {
  show({ ...base, in_sync: false, nodes: [node(0), node(1), node(2), node(3, { reachable: false, has_tx: false, block_hash: null, in_block: false, latency_ms: 3001 })] });
  expect(await screen.findByText(/3 de 4 nós/)).toBeInTheDocument();
  expect(screen.getByText("Sem resposta")).toBeInTheDocument();
});

test("explains that a pending transaction has not been mined yet", async () => {
  show({ tx_hash: H, status: "PENDING", block_number: null, block_hash: null, proposer: null, nodes: [], in_sync: false });
  expect(await screen.findByText(/ainda não foi incluída em um bloco/)).toBeInTheDocument();
});
