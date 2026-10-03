// Screenshot sweep for visual review: node e2e/screens.mjs [carts-query]
// Writes PNGs to e2e/screens/ at 1280x800 and 390x844. Default source: the test fixture.
import { chromium } from '@playwright/test';
import { pathToFileURL, fileURLToPath } from 'node:url';
import path from 'node:path';
import fs from 'node:fs';

const EMU = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const OUT = path.join(EMU, 'e2e', 'screens');
fs.mkdirSync(OUT, { recursive: true });
const query = process.argv[2] ?? '?carts=test-fixture/carts.js';
const tag = process.argv[3] ?? 'fixture';
const url = pathToFileURL(path.join(EMU, 'index.html')).href + query + (query ? '&' : '?') + 'seed=3';

const browser = await chromium.launch();
for (const [vw, vh, name] of [[1280, 800, 'desk'], [390, 844, 'phone']]) {
  const page = await browser.newPage({ viewport: { width: vw, height: vh } });
  const shot = (s, full = false) => page.screenshot({ path: path.join(OUT, `${tag}-${name}-${s}.png`), fullPage: full });
  await page.goto(url);
  await shot('1-select', true);
  const keys = await page.evaluate(() => Object.keys(window.FNM_CARTRIDGES));
  await page.locator(`[data-testid=cart-card][data-cart="${keys[0]}"] [data-testid=play]`).click();
  await shot('2-question');
  let cur = await page.evaluate(() => window.FNM_EMU.current());
  const wrong = cur.item.choices.findIndex((_, i) => i !== cur.item.answer);
  await page.getByTestId('door').nth(wrong).click();
  await page.waitForTimeout(400); // let the shake finish
  await shot('3-wrong');
  await page.getByTestId('door').nth(cur.item.answer).click();
  await shot('4-correct');
  // finish the run, missing once on every other stage
  for (;;) {
    await page.getByTestId('continue').click();
    if (await page.getByTestId('end').count()) break;
    cur = await page.evaluate(() => window.FNM_EMU.current());
    if (cur.stage % 2) await page.getByTestId('door').nth((cur.item.answer + 1) % cur.item.choices.length).click();
    await page.getByTestId('door').nth(cur.item.answer).click();
  }
  await shot('5-end', true);
  await page.getByTestId('home').click();
  await page.getByTestId('tab-inspect').click();
  await shot('6-inspector');
  await page.goto(pathToFileURL(path.join(EMU, 'index.html')).href + '?carts=nope.js');
  await shot('7-empty');
  // 2-door map: same cartridge, reduced
  await page.goto(url + '&doors=2');
  await page.locator(`[data-testid=cart-card][data-cart="${keys[0]}"] [data-testid=play]`).click();
  await shot('8-doors2');
  // §5 rule-6 maximum lengths must display without truncation (§6)
  const mx = await browser.newPage({ viewport: { width: vw, height: vh } });
  await mx.addInitScript(() => {
    const P = '(12 + 8)^2 ÷ 4 − 3 × (6 − 2)^2 + 18 ÷ (9 − 6) × 2 − 10';
    window.FNM_CARTRIDGES = { 'zz-maxlen': {
      protocol: 'fnm-cart/1', id: 'zz-maxlen', version: '0.0.0',
      title: 'W'.repeat(32), subtitle: 'M'.repeat(40), grade: '8', standards: [],
      tiers: [{ tier: 1, name: 'W'.repeat(24), description: '' }],
      misconceptions: { LONG: { student: 'W'.repeat(20) + ' ' + 'm'.repeat(59), teacher: '' } },
      items: [{ id: 'zz-maxlen/t1/001', tier: 1, prompt: P.padEnd(60, '0'),
        choices: ['−12345678.9012', '−98765432.1098', '-1234567890123', 'WWWWWWWWWWWWWW'], answer: 3,
        misconceptions: ['LONG', 'LONG', 'ARITH', null], explanation: ('Wide words ').repeat(14).slice(0, 160) }],
    } };
  });
  await mx.goto(pathToFileURL(path.join(EMU, 'index.html')).href + '?carts=nope.js');
  await mx.getByTestId('play').click();
  await mx.getByTestId('door').nth(0).click();
  await mx.screenshot({ path: path.join(OUT, `maxlen-${name}-wrong.png`), fullPage: true });
  await mx.getByTestId('door').nth(3).click();
  await mx.screenshot({ path: path.join(OUT, `maxlen-${name}-correct.png`), fullPage: true });
  const over = await mx.evaluate(() => [...document.querySelectorAll('.prompt, .door-text, .fb-text, .rt, .rs, .run-stage')]
    .filter((e) => e.scrollWidth > e.clientWidth + 1).map((e) => e.className));
  const pageOver = await mx.evaluate(() => document.documentElement.scrollWidth > window.innerWidth);
  console.log(name, 'maxlen overflow:', JSON.stringify(over), 'page h-scroll:', pageOver);
  await mx.close();
  await page.close();
}
await browser.close();
console.log('screens written to', OUT);
