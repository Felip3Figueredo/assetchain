// Records the full AssetChain demo through the real UI (Playwright + system Chrome).
// Usage: node record.mjs [BASE_URL] [OUT_DIR]   (stack must be running; defaults: http://localhost:5173, ./out)
import { chromium } from "playwright-core";
import { execSync } from "node:child_process";
import fs from "node:fs";

const BASE = process.argv[2] ?? "http://localhost:5173";
const OUT = process.argv[3] ?? "./out";
const SIMULATE_NODE_FAILURE = process.env.NODE_FAILURE !== "0";
const BESU_NODE4 = process.env.BESU_NODE4 ?? "assetchain-besu-4-1";
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

fs.rmSync(OUT, { recursive: true, force: true });
const browser = await chromium.launch({ executablePath: process.env.CHROME ?? "/usr/bin/google-chrome", headless: true, args: ["--no-sandbox"] });
const ctx = await browser.newContext({ viewport: { width: 1366, height: 768 }, recordVideo: { dir: OUT, size: { width: 1366, height: 768 } }, locale: "pt-BR" });
const page = await ctx.newPage();

// Overlay: caption bar + visible cursor + click ripple (video captures the page, not the OS pointer).
await page.addInitScript(() => {
  const init = () => {
    if (document.getElementById("demo-cap")) return;
    const st = document.createElement("style");
    st.textContent = `#demo-cap{position:fixed;left:50%;bottom:22px;transform:translateX(-50%);max-width:86%;z-index:99999;background:rgba(10,31,35,.94);color:#fff;font:500 18px/1.35 'IBM Plex Sans',system-ui,sans-serif;padding:12px 22px;border-radius:10px;border-left:5px solid #F2A71B;box-shadow:0 6px 24px rgba(0,0,0,.3);transition:opacity .25s;pointer-events:none}
    #demo-cur{position:fixed;width:20px;height:20px;border-radius:50%;background:rgba(242,167,27,.55);border:2px solid #B97800;z-index:100000;pointer-events:none;transform:translate(-50%,-50%);left:-50px;top:-50px}
    .demo-rip{position:fixed;width:20px;height:20px;border-radius:50%;border:3px solid #F2A71B;z-index:99998;pointer-events:none;transform:translate(-50%,-50%);animation:rip .6s ease-out forwards}
    @keyframes rip{to{width:70px;height:70px;opacity:0}}`;
    document.head.appendChild(st);
    const cap = document.createElement("div"); cap.id = "demo-cap"; cap.style.opacity = "0"; document.body.appendChild(cap);
    const cur = document.createElement("div"); cur.id = "demo-cur"; document.body.appendChild(cur);
    addEventListener("mousemove", (e) => { cur.style.left = e.clientX + "px"; cur.style.top = e.clientY + "px"; }, true);
    addEventListener("mousedown", (e) => { const r = document.createElement("div"); r.className = "demo-rip"; r.style.left = e.clientX + "px"; r.style.top = e.clientY + "px"; document.body.appendChild(r); setTimeout(() => r.remove(), 700); }, true);
  };
  if (document.body) init(); else addEventListener("DOMContentLoaded", init);
});

const caption = async (text) => page.evaluate((t) => { const c = document.getElementById("demo-cap"); if (c) { c.textContent = t; c.style.opacity = t ? "1" : "0"; } }, text);
const say = async (text, ms = 3500) => { await caption(text); await sleep(ms); };
let mx = 683, my = 384;
async function glide(x, y) { await page.mouse.move(x, y, { steps: 28 }); mx = x; my = y; }
async function click(locator, { pause = 450 } = {}) {
  await locator.first().scrollIntoViewIfNeeded();
  const b = await locator.first().boundingBox();
  await glide(b.x + b.width / 2, b.y + b.height / 2);
  await sleep(pause);
  await page.mouse.click(b.x + b.width / 2, b.y + b.height / 2);
}
const nav = (name) => click(page.getByRole("navigation", { name: "Principal" }).getByRole("link", { name }));
const scrollBy = async (dy) => { await page.mouse.wheel(0, dy); await sleep(900); };

// ---------------- Script ----------------
await page.goto(BASE + "/");
await page.waitForSelector("text=Painel");
await say("AssetChain: tokenização de ativos do mundo real (projeto educacional, ativos fictícios)", 4200);
await say("Ambiente recém-criado: 2 ativos em rascunho e 3 carteiras de teste, sem nenhuma transação de tokens", 4500);

await nav("Rede");
await page.waitForSelector("text=QBFT");
await say("Rede permissionada Hyperledger Besu: 4 validadores com consenso QBFT. O quórum é de 3 votos e a rede tolera 1 validador com falha", 5500);
await scrollBy(420);
await say("Cada bloco é proposto por um validador diferente, em rodízio", 3500);

await nav("Ativos");
await page.waitForSelector("text=Usina Solar Alpha");
await say("Ativos fictícios cadastrados. Vamos tokenizar a Usina Solar Alpha: R$ 10.000.000 em 10.000.000 tokens", 4500);
await click(page.getByRole("link", { name: "Usina Solar Alpha" }));
await page.waitForSelector("text=Informações do empreendimento");
await say("Detalhe do ativo. Os tokens são participações econômicas fictícias, sem propriedade jurídica", 4200);

await click(page.getByRole("button", { name: "Aprovar para tokenização" }));
await page.waitForSelector("text=Implantar contrato e emitir tokens");
await say("1. Ativo aprovado para tokenização", 2800);

await caption("2. O backend implanta um contrato ERC-20 só para este ativo e emite 10.000.000 tokens na blockchain (aguardando o bloco)…");
await click(page.getByRole("button", { name: "Implantar contrato e emitir tokens" }));
await page.waitForSelector("text=Contrato inteligente", { timeout: 90000 });
await sleep(1500);
await say("Contrato implantado: endereço, bloco da implantação e oferta máxima fixa de 10.000.000 tokens", 4500);
await scrollBy(450);
await say("Toda a emissão está na Tesouraria (100%). A oferta é lida do contrato, não do banco de dados", 4500);

// ---- transfer 100.000 Tesouraria -> Carteira B
await scrollBy(500);
const form = page.locator("form").filter({ has: page.getByRole("button", { name: "Transferir tokens" }) });
await say("3. Transferência de 100.000 tokens da Tesouraria (carteira A) para a Carteira B", 3500);
await click(form.locator("select").nth(0)); await form.locator("select").nth(0).selectOption({ index: 1 }); // Tesouraria is first wallet
await sleep(600);
await click(form.locator("select").nth(1));
const opts = await form.locator("select").nth(1).locator("option").allTextContents();
const idxB = opts.findIndex((t) => t.startsWith("Carteira B"));
await form.locator("select").nth(1).selectOption({ index: idxB });
await sleep(600);
const amount = form.locator("input");
await click(amount); await amount.fill(""); await amount.pressSequentially("100000", { delay: 120 });
await sleep(700);
await caption("Assinada com a chave da carteira e enviada ao nó; só vira CONFIRMADA depois do recibo do bloco…");
await click(form.getByRole("button", { name: "Transferir tokens" }));
await page.waitForSelector("text=Transferência confirmada", { timeout: 90000 });
await say("Transferência confirmada na blockchain: o bloco e o hash aparecem na tela", 4000);

// ---- node flow
await click(page.getByRole("link", { name: "Ver fluxo entre os nós" }));
await page.waitForSelector("text=Caminho da transação");
await say("Fluxo da transação entre os nós: recebida por um validador, proposta no bloco e conferida em cada nó", 4500);
await scrollBy(450);
await page.waitForSelector("text=Presente em 4 de 4 nós", { timeout: 30000 });
await say("Consulta direta ao JSON-RPC de cada nó: os 4 têm a transação e o mesmo hash de bloco", 5000);

// ---- balances
await nav("Carteiras");
await page.waitForSelector("text=Carteira B");
await sleep(2500);
await say("Saldos lidos on-chain: Tesouraria 9.900.000 e Carteira B 100.000 tokens", 5000);

await nav("Transações");
await page.waitForSelector("text=Transferência");
await say("Histórico: implantação, emissão e transferência, todas confirmadas com hash e número do bloco", 5000);

// ---- optional: validator failure
if (SIMULATE_NODE_FAILURE) {
  await caption("Teste de resiliência: derrubando o Validador 4 (1 de 4)…");
  execSync(`docker stop ${BESU_NODE4}`, { stdio: "ignore" });
  await sleep(4000);
  await nav("Ativos");
  await click(page.getByRole("link", { name: "Usina Solar Alpha" }));
  await page.waitForSelector("text=Transferir tokens");
  await scrollBy(1100);
  const f2 = page.locator("form").filter({ has: page.getByRole("button", { name: "Transferir tokens" }) });
  await say("Com um validador fora do ar, a rede ainda atinge o quórum e continua confirmando transferências", 4200);
  await click(f2.locator("select").nth(0)); await f2.locator("select").nth(0).selectOption({ index: 1 });
  const opts2 = await f2.locator("select").nth(1).locator("option").allTextContents();
  await click(f2.locator("select").nth(1)); await f2.locator("select").nth(1).selectOption({ index: opts2.findIndex((t) => t.startsWith("Carteira C")) });
  await click(f2.locator("input")); await f2.locator("input").fill(""); await f2.locator("input").pressSequentially("500", { delay: 120 });
  await click(f2.getByRole("button", { name: "Transferir tokens" }));
  await page.waitForSelector("text=Transferência confirmada", { timeout: 90000 });
  await click(page.getByRole("link", { name: "Ver fluxo entre os nós" }));
  await page.waitForSelector("text=Presente em 3 de 4 nós", { timeout: 40000 });
  await scrollBy(500);
  await say("Confirmada por 3 de 4 nós: o Validador 4 aparece como \"Sem resposta\" até voltar e se sincronizar sozinho", 6000);
  execSync(`docker start ${BESU_NODE4}`, { stdio: "ignore" });
}

await nav("Painel");
await sleep(2500);
await say("Resumo: ativos, tokens emitidos, carteiras, transações e status da blockchain. Fim da demonstração", 5000);
await caption("");
await sleep(600);

const videoPath = await page.video().path();
await ctx.close();
await browser.close();
fs.renameSync(videoPath, `${OUT}/assetchain-demo.webm`);
console.log("video:", `${OUT}/assetchain-demo.webm`);
