import { screen, within } from "@testing-library/react";
import Network from "../pages/Network";
import { mockApi, renderPage } from "./helpers";

const V = ["0x" + "11".repeat(20), "0x" + "22".repeat(20), "0x" + "33".repeat(20), "0x" + "44".repeat(20)];
const block = (n: number, p: string) => ({ number: n, hash: "0x" + String(n).padStart(2, "0").repeat(32), timestamp: 1790000000 + n * 2, tx_count: 0, gas_used: 0, proposer: p });

test("shows the QBFT validator set, quorum, fault tolerance and who proposed each block", async () => {
  mockApi({
    "/api/blockchain/validators": { consensus: "QBFT", validators: V, count: 4, fault_tolerance: 1, quorum: 3, peer_count: 3 },
    "/api/blockchain/blocks": [block(8, V[0]), block(7, V[3]), block(6, V[2]), block(5, V[1])],
  });
  renderPage(<Network />);
  expect(await screen.findByText("QBFT")).toBeInTheDocument();
  expect(screen.getByText("Quórum de votos")).toBeInTheDocument();
  expect(screen.getByText(/tolera 1 validador com falha/)).toBeInTheDocument();
  const table = screen.getByText(/Validadores \(últimos/).closest("section")!;
  expect(within(table).getAllByText(/^Validador \d$/)).toHaveLength(4);
  expect(screen.getByText("#8")).toBeInTheDocument();
});

test("flags a validator that stopped proposing blocks", async () => {
  mockApi({
    "/api/blockchain/validators": { consensus: "QBFT", validators: V, count: 4, fault_tolerance: 1, quorum: 3, peer_count: 2 },
    "/api/blockchain/blocks": [block(8, V[0]), block(7, V[1]), block(6, V[2]), block(5, V[0]), block(4, V[1]), block(3, V[2])],
  });
  renderPage(<Network />);
  expect(await screen.findByText(/Sem propor nos últimos blocos/)).toBeInTheDocument();
});

test("explains single-node automine networks instead of showing validators", async () => {
  mockApi({
    "/api/blockchain/validators": { consensus: "automine", validators: [], count: 0, fault_tolerance: 0, quorum: 0, peer_count: 0 },
    "/api/blockchain/blocks": [block(2, V[0])],
  });
  renderPage(<Network />);
  expect(await screen.findByText(/nó único/)).toBeInTheDocument();
});
