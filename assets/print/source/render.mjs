import puppeteer from 'puppeteer-core';
const HTML_PATH = process.argv[2], OUT = process.argv[3], ONLY = process.argv[4] || '';
const url = `file://${HTML_PATH}` + (ONLY ? `?only=${encodeURIComponent(ONLY)}` : '');
const browser = await puppeteer.launch({
  executablePath: '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',
  headless: 'new', args: ['--no-sandbox', '--allow-file-access-from-files']
});
const page = await browser.newPage();
await page.setViewport({width: 1700, height: 2200, deviceScaleFactor: 1});
await page.goto(url, {waitUntil: 'networkidle0', timeout: 60000});
await page.waitForFunction(() => document.body.dataset.ready === 'true', {timeout: 30000});
await new Promise(r => setTimeout(r, 500));
// Design canvas is 1700x2200 px; @ 96dpi that's 17.7x22.9 in. Target page is 8.5x11 in.
// scale = 8.5 / (1700/96) = 8.5*96/1700 = 0.48 exactly
await page.pdf({
  path: OUT,
  width: '8.5in',
  height: '11in',
  scale: 0.48,
  printBackground: true,
  preferCSSPageSize: false,   // override @page; we want exact 8.5x11 in
  displayHeaderFooter: false,
  margin: {top: 0, bottom: 0, left: 0, right: 0}
});
await browser.close();
console.error(`done${ONLY ? ` only=${ONLY}` : ''}: ${OUT}`);
