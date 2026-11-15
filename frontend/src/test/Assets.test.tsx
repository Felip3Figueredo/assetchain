import { screen } from "@testing-library/react";
import Assets from "../pages/Assets";
import { mockApi, renderPage } from "./helpers";

const asset = {
  id: 1, asset_code: "ASSET-001", name: "Usina Solar Alpha", category: "Energia renovável", description: "",
  estimated_value_brl: "10000000.00", token_supply: 10000000, token_price_brl: "1.000000", status: "TOKENIZED",
  metadata: {}, contract_address: "0x" + "cd".repeat(20), created_at: "2026-11-15T12:00:00Z",
};

test("assets list shows value, supply, contract and status", async () => {
  mockApi({ "/api/assets": [asset] });
  renderPage(<Assets />);
  expect(await screen.findByText("Usina Solar Alpha")).toBeInTheDocument();
  expect(screen.getByText(/10\.000\.000,00/)).toBeInTheDocument();
  expect(screen.getByText("Tokenizado")).toBeInTheDocument();
  expect(screen.getByText("0xcdcd…cdcd")).toBeInTheDocument();
});
