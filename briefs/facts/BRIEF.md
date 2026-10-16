# Brief: build ONE Facts cartridge for the fortnitemath library

Repo: `D:\PyCharm Projects\fortnitemath` (Windows, git bash available; the path has a space, quote it). Python venv:
`.venv/Scripts/python`. Test command: `.venv/Scripts/python -m pytest -q`. Baseline on the clean tree, 2026-10-15:
**24155 passed**. Other builders share this repo right
now, so do NOT run the full suite at the start: iterate with your own file
(`.venv/Scripts/python -m pytest -q tests/test_<id_underscored>.py`) and run the full suite ONCE at the end.

## What this is
A Fortnite race: a kid runs through 10 stations; each station asks one multiple-choice question and the kid answers by
running through one of four lettered doors. A cartridge is one skill, 5 tiers, climbed station by station (stations
1-2 tier 1 ... 9-10 tier 5). Aaron (the teacher) asked for a **Facts** group beside the grade levels: addition,
subtraction, multiplication, division and combo, each with levels that scale (addition within 10 up to within 100;
multiplication factors up to 5 up to 15; subtraction and division mirror them). The tiers ARE those levels.

## Read first (they are the spec)
1. `cartridges/LIBRARY.md`, section **"Facts"** (the last section): your row (id, title, subtitle, standards, seed,
   items per tier), the bounds table (your tier bands), and "Rules for every Facts cartridge" (prompt shape, near
   distractors, the no-middle-tell rule, misconception keys, explanation strategies). Follow it exactly; where an
   example breaks a limit or a bound, improve it and report it.
2. `PROTOCOL.md`: §3 (cartridge source), §4 (item shape), §4c (Facts bounds: these replace §4a for your cartridge),
   §5 (validation: prompt ≤ 60 chars, each choice ≤ 14, explanation ≤ 160, misconception `student` ≤ 80, tier name
   ≤ 24, title ≤ 32, subtitle ≤ 40; charset printable ASCII plus `× ÷ − ≤ ≥ ≠ √ π`; answer-position balance per
   tier; determinism).
3. The reference cartridge `cartridges/integer-ops/` (manifest + generator) and `tests/test_integer_ops.py`: the
   quality bar (golden misconception cases, an independent re-check of every baked answer, a bounds test over
   `baked.json`). Read, never edit.

## Deliverables (your cartridge id is given at the bottom)
1. `cartridges/<id>/cartridge.json`: protocol `fnm-cart/1`, version `1.0.0`, `"grade": "Facts"`, `"picker_order"`
   (addition 1, subtraction 2, multiplication 3, division 4, combo 5), title and subtitle from LIBRARY.md, standards as
   `CCSS.MATH.CONTENT.<grade>.<domain>.<cluster>.<n>` strings (`CCSS.MATH.CONTENT.K.OA.A.5`,
   `CCSS.MATH.CONTENT.2.NBT.B.5`), the seed and `items_per_tier` from LIBRARY.md, 5 tiers named as in the bounds table
   (combo: "Within 10 & 5 × 5" ... "Within 100 & 15 × 15"), each with a one-line `description`, a misconception catalog
   (`student` text is what a kid reads after the wrong door: short, kind, tells the right idea; `teacher` text names
   the wrong rule), and a `"bounds"` string stating your tier bands and the wrong-choice range.
2. `cartridges/<id>/generator.py`: `generate(manifest, rng) -> list[dict]`, stdlib only, deterministic (only the
   `rng` passed in; never iterate a `set`), imports nothing from other cartridges. Exactly `items_per_tier` items per
   tier, prompts unique per tier, 4 choices each, balanced answer positions per tier (§5 rule 8: assign the answer
   position round-robin, then shuffle the order of positions with `rng`). Wrong choices from the modelled
   misconceptions first, `ARITH` only to fill.
3. `tests/test_<id with - replaced by _>.py`, at minimum:
   - golden cases: each misconception key yields its expected wrong value on a hand-worked prompt;
   - an independent re-check of EVERY baked item: parse the prompt with a regex (`^(\d+) ([+−×÷]) (\d+) = \?$`) and
     compute with plain Python, never by calling the generator;
   - bounds: every item's numbers sit in its tier's band (LIBRARY.md table), the tier 2-5 mix rules hold (crossing
     ten, regroup share, two-digit-with-one-digit share, multiples of 10), wrong choices are distinct non-negative
     integers ≤ 999, asserted on `baked.json`;
   - the near-distractor rule (≥ 2 near wrong values per item), the no-middle-tell rule (each rank 15-35% per tier)
     and the no-ones-digit-tell rule (on the tiers LIBRARY.md names: the answer is the only choice with its ones digit
     in at most 25% of the tier's items);
   - a checker self-test with at least one planted item it must reject (a disproof: the checker can fail).
4. Bake + validate: `.venv/Scripts/python -m fnm bake <id>` then `.venv/Scripts/python -m fnm validate <id>` (must
   print `valid`). Bake twice and confirm `baked.json` is byte-identical (`cmp`).

## Content quality (what matters most)
- Read a dozen baked items per tier as the kid would (print them with `PYTHONIOENCODING=utf-8`; `−` crashes cp1252).
  Is exactly one choice right? Could a kid win by a pattern instead of the fact (always the middle value, always the
  even one, always the only two-digit one, the only one ending in the right digit)? Fix the generator if so.
- Near distractors are the point: 7 × 8 should sit beside 48, 63 or 54, not beside 15, 1 and 99.
- Choices are shuffled by the map at display time, so choice text must never depend on position.
- Explanations show the fact and one reusable strategy in ≤ 160 chars (LIBRARY.md lists them).

## Non-goals / concurrency contract
- Other builders are building the other Facts cartridges in their own `cartridges/<other-id>/` dirs and
  `tests/test_<other>.py` files. Touch ONLY your own two paths. Do NOT edit PROTOCOL.md, LIBRARY.md, `fnm/`,
  `console/`, `maps/`, `emulator/`, `tools/`, `tests/conftest.py` or any other cartridge or test.
- Do NOT run `fnm insert`, `fnm emit` or `fnm sync` (they rewrite shared generated files; the lead does that once at
  the end). Do NOT commit. No UEFN, no Verse.
- When you run the full suite, a failure in another new cartridge's test file is not yours: note it, carry on. Until
  the lead inserts the new cartridges, `test_emit.py::test_generated_slot_file_lints` and `test_carts_js` fail once
  any new `baked.json` exists; that is expected. The lead is also editing `fnm/emit.py`, `tests/test_emit.py`, the
  HUD and the emulator: a failure there is not yours either.
- Checkpoint every deliverable to disk the moment it exists.
- Throwaway scripts go in your own scratch folder,
  `C:/Users/kicki/AppData/Local/Temp/claude/D--PyCharm-Projects-fortnitemath/78214c3f-bf61-447e-8b46-80d4fc4fcce7/scratchpad/facts/<id>/`,
  never the shared scratchpad root.
- If you find a real problem in the protocol, the plan or the toolchain, report it; do not fix it.
- The lead may send you fixes after your report (SendMessage). Apply them, re-bake, re-validate, re-run your test file,
  and report again in the same shape.

## If your id is `facts-combo`
The other four Facts cartridges are finished and audited: `cartridges/facts-addition/`, `facts-subtraction/`,
`facts-multiplication/`, `facts-division/` and their tests. Read their generators and copy each operation's rules
(bands, distractor choice, explanations, student text) into your own generator: never import them. Prefix every
misconception key with its operation (`ADD_ONE_OFF`, `SUB_ADDED`, `MUL_GROUP_OFF`, `DIV_SUBTRACTED`, ...). Your test
re-checks every item independently and also asserts that each combo prompt that appears in an operation's own
`baked.json` at the same tier has the same answer.

## Report (your final message; keep it short)
- Files created; your test count and full-suite result; your `bounds` string.
- Four sample items per tier (prompt / choices / answer / the misconception key of each wrong choice).
- Per tier: the answer's rank distribution (how often smallest / 2nd / 3rd / largest), and the share of items where
  the answer is the only choice with its ones digit.
- The disproof you ran (a sabotage of the generator or a planted bad item that your tests caught, then restored).
- Anything you decided differently from this brief or LIBRARY.md and why.
- The shakiest assumption in your work, stated plainly.
