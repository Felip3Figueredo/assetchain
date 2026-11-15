import { formatTokens, shortHash, formatBrl } from "../format";

test("formats whole-token strings in pt-BR", () => {
  expect(formatTokens("10000000")).toBe("10.000.000");
  expect(formatTokens("1.5")).toBe("1,5");
});
test("shortens hashes and addresses", () => {
  expect(shortHash("0x" + "ab".repeat(32))).toBe("0xabab…abab");
});
test("formats BRL", () => {
  expect(formatBrl(10000000)).toContain("10.000.000,00");
});
