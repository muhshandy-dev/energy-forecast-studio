// Uji ujung ke ujung dengan Playwright: CSP, galat konsol, responsif, aksesibilitas, paritas angka.
import AxeBuilder from "@axe-core/playwright";
import { mkdirSync, readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { chromium } from "playwright";
import { startServer } from "./serve.mjs";

const here = dirname(fileURLToPath(import.meta.url));
const OUT = process.env.SHOT_DIR || join(here, "..", "..", "screenshots");
mkdirSync(OUT, { recursive: true });
const WIDTHS = process.env.WIDTHS ? process.env.WIDTHS.split(",").map(Number) : [360, 768, 1440];
const SCHEMES = ["light", "dark"];
const VIEWS = ["studio", "uji-mundur", "kinerja", "kesalahan", "metode"];
const metrics = JSON.parse(readFileSync(join(here, "..", "public", "data", "metrics.json"), "utf8"));
const failures = [];
let checks = 0;
const ok = (cond, msg) => {
  checks += 1;
  if (!cond) {
    failures.push(msg);
    console.error("GAGAL:", msg);
  }
};

const server = await startServer();
const base = `http://127.0.0.1:${server.address().port}`;
const browser = await chromium.launch(
  process.env.PW_CHROMIUM ? { executablePath: process.env.PW_CHROMIUM } : {},
);

function watch(page, problems) {
  page.on("console", (m) => {
    if (["error", "warning"].includes(m.type())) problems.push(`${m.type()}: ${m.text()}`);
  });
  page.on("pageerror", (e) => problems.push(`pageerror: ${e.message}`));
  page.on("requestfailed", (r) => problems.push(`requestfailed: ${r.url()}`));
  page.on("request", (r) => {
    if (!r.url().startsWith(base)) problems.push(`permintaan luar: ${r.url()}`);
  });
}

async function waitView(page) {
  await page.waitForSelector("main h1");
  await page.waitForFunction(() => {
    const plots = [...document.querySelectorAll(".plot > div")];
    return !document.querySelector(".loading") && plots.every((p) => p.dataset.plot === "ready");
  });
}

for (const scheme of SCHEMES) {
  for (const width of WIDTHS) {
    const ctx = await browser.newContext({ viewport: { width, height: 900 }, colorScheme: scheme, reducedMotion: "reduce" });
    const page = await ctx.newPage();
    const problems = [];
    watch(page, problems);
    for (const view of VIEWS) {
      await page.goto(`${base}/#${view}`);
      await waitView(page);
      const overflow = await page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth);
      ok(overflow <= 0, `${view} ${width}px ${scheme}: gulir horizontal ${overflow}px`);
      if (width !== 768) {
        await page.screenshot({ path: join(OUT, `${view}-${width}-${scheme === "dark" ? "gelap" : "terang"}.png`), fullPage: true });
      }
      if (width === 1440 || width === 360) {
        const axe = await new AxeBuilder({ page }).withTags(["wcag2a", "wcag2aa"]).analyze();
        const serious = axe.violations.filter((v) => ["serious", "critical"].includes(v.impact));
        ok(
          serious.length === 0,
          `${view} ${width}px ${scheme}: axe ${serious.map((v) => `${v.id} (${v.nodes.length})`).join(", ")}`,
        );
      }
    }
    ok(problems.length === 0, `${width}px ${scheme}: ${problems.slice(0, 5).join(" | ")}`);
    await ctx.close();
  }
}

// Paritas angka: tabel kinerja menampilkan MAE dari metrics.json.
{
  const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });
  await page.goto(`${base}/#kinerja`);
  await waitView(page);
  const fmt = new Intl.NumberFormat("id-ID", { maximumFractionDigits: 0 });
  const rows = [
    ["lightgbm", "LightGBM"],
    ["mstl_ets", "MSTL + ETS"],
    ["snaive168", "Naive mingguan"],
  ];
  if ("ensemble" in metrics.metrics.test) rows.unshift(["ensemble", "Gabungan"]);
  for (const [model, label] of rows) {
    const row = page.locator("table.metrics tbody tr", { hasText: label });
    const cell = await row.locator("td").nth(1).innerText();
    const want = fmt.format(metrics.metrics.test[model].week_ahead.mae);
    ok(cell.startsWith(want), `MAE ${model}: tampil "${cell}", seharusnya ${want}`);
  }
  // Interaksi studio: geser skenario mengubah puncak secara proporsional.
  await page.goto(`${base}/#studio`);
  await waitView(page);
  const peak = async () => (await page.locator(".stat").first().locator(".stat-value").innerText()).trim();
  const before = await peak();
  await page.locator("#shift").fill("10");
  await waitView(page);
  const after = await peak();
  const val = (s) => Number(s.replace(/[^\d,]/g, "").replace(",", "."));
  ok(Math.abs(val(after) / val(before) - 1.1) < 0.02, `skenario +10%: puncak ${before} -> ${after}`);
  await page.getByRole("radio", { name: /^MSTL/ }).check();
  await waitView(page);
  ok((await page.locator(".provenance").innerText()).includes("MSTL + ETS"), "pilihan model tidak tercermin di keterangan");
  // Navigasi keyboard: tautan lompat lalu navigasi bisa dicapai dari awal halaman.
  await page.close();
}
{
  const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });
  await page.goto(`${base}/#kinerja`);
  await waitView(page);
  await page.keyboard.press("Tab");
  ok(await page.evaluate(() => document.activeElement?.classList.contains("skip")), "tab pertama bukan tautan lompat");
  await page.keyboard.press("Tab");
  ok(await page.evaluate(() => document.activeElement?.tagName === "A"), "fokus keyboard tidak mencapai navigasi");
  await page.close();
}

await browser.close();
server.close();
console.log(`${checks} pemeriksaan, ${failures.length} gagal`);
process.exit(failures.length ? 1 : 0);
