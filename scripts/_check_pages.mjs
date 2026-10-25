import { chromium } from 'playwright';

const PORT = process.env.GWV_PORT || 8090;
const pages = [
  ['present', `http://localhost:${PORT}/present`],
  ['screenshot', `http://localhost:${PORT}/screenshot`],
  ['debug-bookmarks', `http://localhost:${PORT}/debug-bookmarks`],
];

const browser = await chromium.launch();
const page = await browser.newPage();
for (const [name, url] of pages) {
  const errors = [];
  const msgs = [];
  page.removeAllListeners('console');
  page.removeAllListeners('pageerror');
  page.on('console', m => { if (m.type() === 'error') msgs.push(m.text().slice(0, 300)); });
  page.on('pageerror', e => errors.push(String(e).slice(0, 300)));
  try {
    const resp = await page.goto(url, { waitUntil: 'load', timeout: 20000 });
    await page.waitForTimeout(8000);
    console.log(`\n=== ${name}: HTTP ${resp ? resp.status() : '?'} ===`);
    errors.forEach(e => console.log('  PAGEERR:', e));
    msgs.slice(0, 8).forEach(m => console.log('  CONSOLE:', m));
  } catch (e) {
    console.log(`\n=== ${name}: FAIL ${e.message.slice(0, 200)}`);
  }
}
await browser.close();
