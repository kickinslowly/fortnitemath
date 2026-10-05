// E2E for the FNM emulator. Runs against file:// — no server.
//   cd emulator && npm run e2e
import { test, expect } from '@playwright/test';
import { pathToFileURL, fileURLToPath } from 'node:url';
import path from 'node:path';
import fs from 'node:fs';

const EMU = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const pageUrl = (q = '') => pathToFileURL(path.join(EMU, 'index.html')).href + q;
const FIXTURE = '?carts=test-fixture/carts.js';
const ARITH = 'Check your arithmetic.';

// Independent copy of the §6 formula — the app's own function is NOT used for expectations.
const expectedTier = (s, S, T) => (S <= 1 ? 1 : 1 + Math.floor((2 * (s - 1) * (T - 1) + (S - 1)) / (2 * (S - 1))));

// Independent copy of the §6a reduction, used to check what the emulator presents.
function expectedReduce(item, max) {
  const n = item.choices.length;
  if (n <= max) return { choices: item.choices, answer: item.answer, misconceptions: item.misconceptions };
  const idx = [...Array(n).keys()].filter((i) => i !== item.answer).reverse();
  const drop = [...idx.filter((i) => item.misconceptions[i] === 'ARITH'), ...idx.filter((i) => item.misconceptions[i] !== 'ARITH')].slice(0, n - max);
  const keep = [...Array(n).keys()].filter((i) => !drop.includes(i));
  return { choices: keep.map((i) => item.choices[i]), answer: keep.indexOf(item.answer), misconceptions: keep.map((i) => item.misconceptions[i]) };
}

async function setStages(page, S) {
  for (let i = 0; i < 25; i++) {
    const v = Number(await page.getByTestId('stages-val').textContent());
    if (v === S) return;
    await page.getByRole('button', { name: v < S ? 'More stages' : 'Fewer stages' }).click();
  }
  throw new Error('could not set stages');
}

// Play one full run. Wrong-first policy: odd stages miss once, every 3rd stage (3+ choices) misses twice.
// Mixes mouse and keyboard input. Returns the expectations the end screen must match.
async function playRun(page, cartKey, S, maxDoors = 4) {
  const cart = await page.evaluate((k) => {
    const c = window.FNM_CARTRIDGES[k];
    return { tiers: c.tiers, misconceptions: c.misconceptions || {}, title: c.title };
  }, cartKey);
  const T = cart.tiers.length;
  await setStages(page, S);
  await page.getByTestId(`doors-${maxDoors}`).click();
  await page.locator(`[data-testid=cart-card][data-cart="${cartKey}"] [data-testid=play]`).click();
  await expect(page.locator('.rt')).toHaveText(cart.title);

  let firstTry = 0, misses = 0;
  const hit = {};
  const seen = new Set();
  const tiersSeen = [];
  for (let s = 1; s <= S; s++) {
    const cur = await page.evaluate(() => window.FNM_EMU.current());
    const tExp = expectedTier(s, S, T);
    tiersSeen.push(cur.item.tier);
    expect(cur.stage).toBe(s);
    expect(cur.item.tier, `stage ${s} item tier`).toBe(tExp);
    const tname = cart.tiers.find((t) => t.tier === tExp).name;
    await expect(page.getByTestId('stage-label')).toHaveText(`Stage ${s} / ${S} · Tier ${tExp}: ${tname}`);
    expect(seen.has(cur.item.id), `repeat item ${cur.item.id}`).toBe(false);
    seen.add(cur.item.id);
    const baked = await page.evaluate(([k, id]) => window.FNM_CARTRIDGES[k].items.find((x) => x.id === id), [cartKey, cur.item.id]);
    const want = expectedReduce(baked, maxDoors);
    expect(cur.item.choices).toEqual(want.choices);
    expect(cur.item.answer).toBe(want.answer);
    expect(cur.item.misconceptions).toEqual(want.misconceptions);
    const doors = page.getByTestId('door');
    await expect(doors).toHaveCount(Math.min(baked.choices.length, maxDoors));
    await expect(doors.locator('.door-text')).toHaveText(want.choices);

    const wrongIdx = cur.item.choices.map((_, i) => i).filter((i) => i !== cur.item.answer);
    let nWrong = s % 2 === 1 ? 1 : 0;
    if (s % 3 === 0 && wrongIdx.length >= 2) nWrong = 2;
    for (let w = 0; w < nWrong; w++) {
      const i = wrongIdx[w];
      if (w === 0 && s % 4 === 1) await page.keyboard.press(String(i + 1));
      else if (w === 0 && s % 4 === 3) await page.keyboard.press('ABCD'[i]);
      else await doors.nth(i).click();
      const key = cur.item.misconceptions[i];
      const want = key === 'ARITH' ? ARITH : cart.misconceptions[key].student;
      await expect(page.getByTestId('feedback')).toHaveAttribute('data-kind', 'wrong');
      await expect(page.locator('.feedback .fb-text')).toHaveText(want);
      await expect(doors.nth(i)).toBeDisabled();
      // re-picking a dead door (key or click) must not count again
      await page.keyboard.press(String(i + 1));
      await doors.nth(i).click({ force: true });
      misses++;
      hit[key] = (hit[key] || 0) + 1;
    }
    if (nWrong === 0) firstTry++;
    if (s % 2 === 0) await page.keyboard.press(String(cur.item.answer + 1));
    else await doors.nth(cur.item.answer).click();
    await expect(page.getByTestId('feedback')).toHaveAttribute('data-kind', 'correct');
    await expect(page.locator('.feedback .fb-text')).toHaveText(cur.item.explanation);
    if (s % 2 === 0) await page.keyboard.press('Enter');
    else await page.getByTestId('continue').click();
  }
  return { firstTry, misses, hit, tiersSeen, T };
}

async function checkEnd(page, S, exp) {
  await expect(page.getByTestId('end')).toBeVisible();
  await expect(page.getByTestId('accuracy')).toHaveText(`${Math.round((100 * exp.firstTry) / S)}%`);
  await expect(page.getByTestId('accuracy')).toHaveAttribute('data-first', String(exp.firstTry));
  await expect(page.getByTestId('misses')).toHaveText(String(exp.misses));
  const rows = await page.getByTestId('mc-row').evaluateAll((els) =>
    els.map((e) => [e.dataset.key, Number(e.dataset.count)]));
  expect(Object.fromEntries(rows)).toEqual(exp.hit);
  for (let i = 1; i < rows.length; i++) expect(rows[i - 1][1]).toBeGreaterThanOrEqual(rows[i][1]);
  // the run's tier sequence is exactly the §6 formula
  expect(exp.tiersSeen).toEqual(Array.from({ length: S }, (_, i) => expectedTier(i + 1, S, exp.T)));
}

const RUNS = [
  { key: 'fixture-signed-numbers', S: 7, D: 4 },  // T=3 over 7 stages: 1,1,2,2,2,3,3
  { key: 'fixture-even-odd', S: 5, D: 4 },        // T=2 over 5 stages: 1,1,2,2,2
  { key: 'fixture-signed-numbers', S: 20, D: 4 },
  { key: 'fixture-signed-numbers', S: 10, D: 3 }, // 3-door map: 4-choice items reduced
  { key: 'fixture-signed-numbers', S: 10, D: 2 }, // 2-door map: 4-choice items reduced
];
for (const { key, S, D } of RUNS) {
  test(`full run: ${key} S=${S} doors=${D}`, async ({ page }) => {
    const errors = [];
    page.on('pageerror', (e) => errors.push(String(e)));
    await page.goto(pageUrl(FIXTURE + '&seed=42'));
    const exp = await playRun(page, key, S, D);
    await checkEnd(page, S, exp);
    expect(exp.misses).toBeGreaterThan(0);
    expect(errors).toEqual([]);
  });
}

test('stage→tier formula (§6) matches the protocol examples', async ({ page }) => {
  await page.goto(pageUrl(FIXTURE));
  const seq = (S, T) => page.evaluate(([S, T]) => Array.from({ length: S }, (_, i) => window.FNM_EMU.tierForStage(i + 1, S, T)), [S, T]);
  expect(await seq(3, 5)).toEqual([1, 3, 5]);
  expect(await seq(5, 5)).toEqual([1, 2, 3, 4, 5]);
  expect(await seq(10, 5)).toEqual([1, 1, 2, 2, 3, 3, 4, 4, 5, 5]);
  expect(await seq(1, 5)).toEqual([1]);
  // every run starts at tier 1 and ends at tier T
  for (let T = 1; T <= 5; T++) for (let S = 3; S <= 20; S++) {
    const q = await seq(S, T);
    expect(q[0]).toBe(1); expect(q[S - 1]).toBe(T);
    expect(q).toEqual(Array.from({ length: S }, (_, i) => expectedTier(i + 1, S, T)));
  }
});

test('door reduction (§6a): ARITH dropped first, last first, order kept', async ({ page }) => {
  await page.goto(pageUrl(FIXTURE));
  const red = (item, max) => page.evaluate(([it, m]) => {
    const r = window.FNM_EMU.reduceItem(it, m);
    return { choices: r.choices, answer: r.answer, misconceptions: r.misconceptions };
  }, [item, max]);
  const it = (mcs, answer) => ({ id: 'x', tier: 1, prompt: 'p', explanation: 'e', choices: mcs.map((_, i) => 'c' + i), answer, misconceptions: mcs });
  expect(await red(it(['LTR', null, 'ARITH', 'ARITH'], 1), 2)).toEqual({ choices: ['c0', 'c1'], answer: 1, misconceptions: ['LTR', null] });
  expect(await red(it(['LTR', null, 'ARITH', 'ARITH'], 1), 3)).toEqual({ choices: ['c0', 'c1', 'c2'], answer: 1, misconceptions: ['LTR', null, 'ARITH'] });
  expect(await red(it([null, 'ARITH', 'X', 'ARITH'], 0), 2)).toEqual({ choices: ['c0', 'c2'], answer: 0, misconceptions: [null, 'X'] });
  expect(await red(it(['X', 'Y', null, 'Z'], 2), 2)).toEqual({ choices: ['c0', 'c2'], answer: 1, misconceptions: ['X', null] });
  expect(await red(it(['X', 'Y', null, 'Z'], 2), 3)).toEqual({ choices: ['c0', 'c1', 'c2'], answer: 2, misconceptions: ['X', 'Y', null] });
  expect(await red(it(['X', null], 1), 2)).toEqual({ choices: ['c0', 'c1'], answer: 1, misconceptions: ['X', null] });
});

test('inspector shows items unreduced even on a 2-door map', async ({ page }) => {
  await page.goto(pageUrl(FIXTURE));
  await page.getByTestId('doors-2').click();
  await page.getByTestId('tab-inspect').click();
  await page.locator('.pill', { hasText: 'Signed Numbers' }).click();
  await expect(page.getByTestId('inspect-item').first().locator('.ich')).toHaveCount(4);
});

test('select screen lists every fixture cartridge', async ({ page }) => {
  await page.goto(pageUrl(FIXTURE));
  await expect(page.getByTestId('cart-card')).toHaveCount(2);
  await expect(page.getByTestId('stages-val')).toHaveText('10');
  await expect(page.locator('[data-cart="fixture-even-odd"] .tierlist li')).toHaveCount(2);
  await expect(page.locator('[data-cart="fixture-signed-numbers"] .tierlist li')).toHaveCount(3);
});

test('inspector shows every item with correct choice and misconception tags', async ({ page }) => {
  await page.goto(pageUrl(FIXTURE));
  await page.getByTestId('tab-inspect').click();
  const keys = await page.evaluate(() => Object.keys(window.FNM_CARTRIDGES));
  for (const k of keys) {
    const c = await page.evaluate((k) => window.FNM_CARTRIDGES[k], k);
    await page.locator('.pill', { hasText: c.title }).click();
    await expect(page.getByTestId('inspect-item')).toHaveCount(c.items.length);
    await expect(page.locator('.ich.ok')).toHaveCount(c.items.length);
    const wrongs = c.items.reduce((n, it) => n + it.choices.length - 1, 0);
    await expect(page.locator('.ichoices .tag.mc')).toHaveCount(wrongs);
    await expect(page.locator('.igroup')).toHaveCount(c.tiers.length);
  }
});

test('missing cartridge file shows the insert instruction, no crash', async ({ page }) => {
  const errors = [];
  page.on('pageerror', (e) => errors.push(String(e)));
  await page.goto(pageUrl('?carts=test-fixture/nope.js'));
  await expect(page.getByTestId('empty')).toContainText('python -m fnm insert <id>');
  expect(errors).toEqual([]);
});

test('draw without replacement reshuffles when a tier runs dry', async ({ page }) => {
  await page.goto(pageUrl(FIXTURE));
  const draws = await page.evaluate(() => {
    const items = [1, 2, 3].map((i) => ({ id: 'x' + i, tier: 1 }));
    const d = window.FNM_EMU.makeDrawer(items, window.FNM_EMU.makeRng(7));
    return Array.from({ length: 9 }, () => d.draw(1).id);
  });
  for (let k = 0; k < 9; k += 3) expect(new Set(draws.slice(k, k + 3)).size).toBe(3);
});

// The real generated cartridge file, once the toolchain has produced it.
const REAL = path.join(EMU, 'carts.js');
test('real carts.js: one full run of each cartridge', async ({ page }) => {
  test.skip(!fs.existsSync(REAL), 'emulator/carts.js not generated yet');
  const errors = [];
  page.on('pageerror', (e) => errors.push(String(e)));
  await page.goto(pageUrl('?seed=7'));
  const keys = await page.evaluate(() => Object.keys(window.FNM_CARTRIDGES || {}));
  expect(keys.length).toBeGreaterThan(0);
  for (const k of keys) for (const D of [4, 2]) {
    await page.goto(pageUrl('?seed=7'));
    const exp = await playRun(page, k, 10, D);
    await checkEnd(page, 10, exp);
  }
  expect(errors).toEqual([]);
});

// §6b picker order on the home screen: the DOM sequence of headings and cards, in document order.
const homeSequence = (page) => page.evaluate(() =>
  [...document.querySelectorAll('[data-testid=grade-heading], [data-testid=cart-card]')].map((e) =>
    e.dataset.testid === 'grade-heading' ? `H:${e.textContent}|${e.dataset.grade}` : `C:${e.dataset.cart}`));

test('home groups cartridges by grade: real carts.js gives Grade 6 then Grade 7', async ({ page }) => {
  test.skip(!fs.existsSync(REAL), 'emulator/carts.js not generated yet');
  await page.goto(pageUrl());
  // within a grade the home sorts cards by title (PROTOCOL 6b), not by id
  const carts = await page.evaluate(() => Object.entries(window.FNM_CARTRIDGES)
    .sort(([, x], [, y]) => (x.title < y.title ? -1 : x.title > y.title ? 1 : 0)).map(([k, c]) => [k, String(c.grade)]));
  const g6 = carts.filter(([, g]) => g === '6').map(([k]) => `C:${k}`);
  const g7 = carts.filter(([, g]) => g === '7').map(([k]) => `C:${k}`);
  expect(g6.length + g7.length, 'real carts.js holds only grade 6 and 7 cartridges').toBe(carts.length);
  expect(await homeSequence(page), 'home sequence: Grade 6 heading, its cards, Grade 7 heading, its cards')
    .toEqual(['H:Grade 6|6', ...g6, 'H:Grade 7|7', ...g7]);
});

test('home grade order: numeric when all grades are numbers, string otherwise, no grade last as Other', async ({ page }) => {
  const mk = (id, title, grade) => {
    const c = { protocol: 'fnm-cart/1', id, version: '0.0.0', title, subtitle: 's', standards: [],
      tiers: [{ tier: 1, name: 't', description: '' }], misconceptions: {},
      items: [{ id: `${id}/t1/001`, tier: 1, prompt: 'p', choices: ['a', 'b'], answer: 0, misconceptions: [null, 'ARITH'], explanation: 'e' }] };
    if (grade !== undefined) c.grade = grade;
    return c;
  };
  const load = async (carts) => {
    await page.addInitScript((cs) => { window.FNM_CARTRIDGES = cs; }, carts);
    await page.goto(pageUrl('?carts=nope.js'));
  };
  // all numeric: 10 sorts after 8 (numeric, not string); title order within a grade; no grade -> Other, last
  await load({ a: mk('a', 'Zeta', '10'), b: mk('b', 'Beta', '8'), c: mk('c', 'Alpha', '8'), d: mk('d', 'Nada'), e: mk('e', 'Mid', '9') });
  expect(await homeSequence(page), 'numeric grade order').toEqual(
    ['H:Grade 8|8', 'C:c', 'C:b', 'H:Grade 9|9', 'C:e', 'H:Grade 10|10', 'C:a', 'H:Other|', 'C:d']);
  // one unnumbered grade switches every grade to string order; Other still last
  const p2 = await page.context().newPage();
  await p2.addInitScript((cs) => { window.FNM_CARTRIDGES = cs; },
    { a: mk('a', 'A', '10'), b: mk('b', 'B', '8'), k: mk('k', 'K', 'K'), n: mk('n', 'N', '') });
  await p2.goto(pageUrl('?carts=nope.js'));
  expect(await homeSequence(p2), 'string grade order with an unnumbered grade').toEqual(
    ['H:Grade 10|10', 'C:a', 'H:Grade 8|8', 'C:b', 'H:Grade K|K', 'C:k', 'H:Other|', 'C:n']);
  await expect(p2.getByTestId('cart-card')).toHaveCount(4);
});

test('finish screen: Play again starts a new run of the same cartridge at stage 1, same settings', async ({ page }) => {
  await page.goto(pageUrl(FIXTURE + '&seed=42'));
  const exp = await playRun(page, 'fixture-signed-numbers', 5, 3);
  await checkEnd(page, 5, exp);
  await expect(page.getByTestId('again')).toBeVisible();
  await expect(page.getByTestId('home')).toHaveText('Choose cartridge');
  await page.getByTestId('again').click();
  await expect(page.locator('#app')).toHaveAttribute('data-screen', 'run');
  await expect(page.locator('.rt')).toHaveText('Signed Numbers');
  await expect(page.getByTestId('stage-label')).toHaveAttribute('data-stage', '1');
  await expect(page.getByTestId('stage-label')).toContainText('Stage 1 / 5');
  const cur = await page.evaluate(() => window.FNM_EMU.current());
  expect(cur).toMatchObject({ stage: 1, S: 5, maxDoors: 3, seed: 42, wrong: [], solved: false });
  await expect(page.getByTestId('door')).toHaveCount(3);
});

test('Play again without ?seed draws a fresh seed', async ({ page }) => {
  await page.goto(pageUrl(FIXTURE));
  const exp = await playRun(page, 'fixture-even-odd', 3, 4);
  await checkEnd(page, 3, exp);
  const seed1 = (await page.evaluate(() => window.FNM_EMU.current())).seed;
  await page.getByTestId('again').click();
  const cur = await page.evaluate(() => window.FNM_EMU.current());
  expect(cur).toMatchObject({ stage: 1, S: 3, maxDoors: 4 });
  expect(cur.seed, 'again-run seed differs from the finished run').not.toBe(seed1);
  await expect(page.locator('.rt')).toHaveText('Even or Odd');
});
