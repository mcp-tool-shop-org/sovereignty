#!/usr/bin/env node
/**
 * render.mjs — print a font-inlined RENDER.html to a US-Letter PDF via Chrome.
 *
 * Chrome is resolved from CHROME_PATH, then well-known install paths, then
 * puppeteer-core's channel:'chrome' locator. The HTML URL is built with
 * pathToFileURL so names with spaces encode correctly on every OS.
 *
 *   node render.mjs <html> <out.pdf> [onlyId]
 */
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { pathToFileURL } from "node:url";
import puppeteer from "puppeteer-core";

const HTML_PATH = process.argv[2];
const OUT = process.argv[3];
const ONLY = process.argv[4] || "";

if (!HTML_PATH || !OUT) {
  console.error("usage: node render.mjs <html> <out.pdf> [onlyId]");
  process.exit(2);
}

function candidateChromePaths() {
  const home = os.homedir();
  return [
    process.env.CHROME_PATH,
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    "/usr/bin/google-chrome",
    "/usr/bin/google-chrome-stable",
    "/usr/bin/chromium",
    "/usr/bin/chromium-browser",
    "/snap/bin/chromium",
    "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe",
    "C:\\Program Files (x86)\\Google\\Chrome\\Application\\chrome.exe",
    path.join(home, "AppData", "Local", "Google", "Chrome", "Application", "chrome.exe"),
  ].filter(Boolean);
}

function resolveChrome() {
  if (process.env.CHROME_PATH) {
    if (!fs.existsSync(process.env.CHROME_PATH)) {
      throw new Error(`CHROME_PATH does not exist: ${process.env.CHROME_PATH}`);
    }
    return { executablePath: process.env.CHROME_PATH };
  }
  for (const p of candidateChromePaths()) {
    if (fs.existsSync(p)) return { executablePath: p };
  }
  return { channel: "chrome" };
}

const chrome = resolveChrome();
if (chrome.executablePath && !fs.existsSync(chrome.executablePath)) {
  throw new Error(`Chrome executablePath does not exist: ${chrome.executablePath}`);
}

const htmlAbs = path.resolve(HTML_PATH);
if (!fs.existsSync(htmlAbs)) {
  throw new Error(`HTML does not exist: ${htmlAbs}`);
}
const fileUrl = pathToFileURL(htmlAbs);
if (ONLY) fileUrl.search = `?only=${encodeURIComponent(ONLY)}`;
const url = fileUrl.href;

const browser = await puppeteer.launch({
  ...chrome,
  headless: true,
  args: [
    "--no-sandbox",
    "--allow-file-access-from-files",
    "--font-render-hinting=none",
    "--disable-lcd-text",
  ],
});
const page = await browser.newPage();
await page.setViewport({ width: 1700, height: 2200, deviceScaleFactor: 1 });
await page.emulateMediaType("print");
await page.goto(url, { waitUntil: "load", timeout: 60000 });
await page.waitForFunction(() => document.body.dataset.ready === "true", { timeout: 30000 });
await new Promise((r) => setTimeout(r, 400));
// Design canvas is 1700x2200 px; @ 96dpi that's 17.7x22.9 in. Target page is 8.5x11 in.
// scale = 8.5 / (1700/96) = 8.5*96/1700 = 0.48 exactly
await page.pdf({
  path: OUT,
  width: "8.5in",
  height: "11in",
  scale: 0.48,
  printBackground: true,
  preferCSSPageSize: false,
  displayHeaderFooter: false,
  margin: { top: 0, bottom: 0, left: 0, right: 0 },
});
await browser.close();
console.error(`done${ONLY ? ` only=${ONLY}` : ""}: ${OUT}`);
