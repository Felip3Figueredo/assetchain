import * as fs from "fs";
import * as path from "path";

const src = path.join(__dirname, "../artifacts/contracts/AssetToken.sol/AssetToken.json");
const outDir = path.join(__dirname, "../artifacts-export");
const artifact = JSON.parse(fs.readFileSync(src, "utf8"));

fs.mkdirSync(outDir, { recursive: true });
fs.writeFileSync(
  path.join(outDir, "AssetToken.json"),
  JSON.stringify({ contractName: artifact.contractName, abi: artifact.abi, bytecode: artifact.bytecode }, null, 2)
);
console.log("exported AssetToken artifact");
