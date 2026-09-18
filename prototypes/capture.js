/* Captura screenshots e vídeo dos protótipos NEMO IDE.
   Uso: node prototypes/capture.js [--video] */
const { chromium } = require("playwright");
const path = require("path");

const PROTOTYPES = [
  { file: "layout_a_chat.html", out: "layout_a_chat" },
  { file: "layout_b_ide.html", out: "layout_b_ide" },
  { file: "layout_c_command_center.html", out: "layout_c_command_center" },
  { file: "layout_d_ai_workspace.html", out: "layout_d_ai_workspace" },
];

const withVideo = process.argv.includes("--video");
const root = __dirname;
const mediaDir = path.join(root, "media");
const fs = require("fs");
if (!fs.existsSync(mediaDir)) fs.mkdirSync(mediaDir);

(async () => {
  const browser = await chromium.launch();
  for (const p of PROTOTYPES) {
    const ctx = await browser.newContext({
      viewport: { width: 1280, height: 760 },
      recordVideo: withVideo ? { dir: mediaDir, size: { width: 1280, height: 760 } } : undefined,
    });
    const page = await ctx.newPage();
    const url = "file://" + path.join(root, p.file).replace(/\\/g, "/");
    await page.goto(url);
    await page.waitForTimeout(1200); // abertura
    await page.screenshot({ path: path.join(mediaDir, p.out + "_open.png") });
    await page.waitForTimeout(7000); // pensando/investigando
    await page.screenshot({ path: path.join(mediaDir, p.out + "_working.png") });
    await page.waitForTimeout(9000); // conclusão
    await page.screenshot({ path: path.join(mediaDir, p.out + "_done.png") });
    await ctx.close();
    console.log("capturado:", p.out);
  }
  await browser.close();
  console.log("OK");
})();