# Brief: build ONE Facts operation (four range cartridges) for the fortnitemath library

Repo: `D:\PyCharm Projects\fortnitemath` (Windows, git bash; the path has a space, quote it). Python venv:
`.venv/Scripts/python`. Print baked text with `PYTHONIOENCODING=utf-8` (`−` crashes cp1252). Other builders share this
repo right now: iterate with your own test file only; run the full suite (`.venv/Scripts/python -m pytest -q`) ONCE at
the end.

## What this is
A Fortnite race: a kid runs through 10 stations; each asks one multiple-choice question, answered by running through
one of four lettered doors. A cartridge is one skill with 5 tiers climbed station by station (stations 1-2 tier 1 ...
9-10 tier 5; the HUD shows the tier name: "STATION 3/10 - Sums to 10"). Aaron (the teacher) rejected the first Facts
build (one addition cartridge climbing from sums within 10 to within 100 across a run). He wants **one cartridge per
number range**, the whole run inside that range, **easy to hard within it**:

- Addition and subtraction: to 10, to 20, to 50, to 100.
- Multiplication: times tables to 5, 10, 12, 15 (factors 0-N). Division: those tables read backwards.
- Mixed: + − at 10/20/50/100 with × ÷ at 5/10/12/15 (built last, by a separate builder).
- Levels 7-10 (tiers 4-5) get hard with **missing numbers**: `7 + ? = 15`, `? − 6 = 9`, `6 × ? = 42`, `? ÷ 6 = 7`.

## The spec
1. `briefs/facts2/pools.py` IS the prompt spec: for each range, each tier's prompt forms (R result unknown, C second
   number unknown, S first number unknown), the pairs each form draws from, and the per-part floors. Its docstring
   defines the forms, the reading-backwards rule for subtraction and division, and the floor semantics. Copy the parts
   for your operation into your generator (cartridges import nothing outside themselves). Tier names are there too.
   Run it to see the pool counts. Do not edit it; if it is wrong, report it.
2. `cartridges/LIBRARY.md` "Facts" (the lead is rewriting it now; pools.py wins any conflict) and `PROTOCOL.md` §3,
   §4, §4c, §5: item shape and validation (prompt ≤ 60 chars, choice ≤ 14, explanation ≤ 160, student text ≤ 80,
   tier name ≤ 24, title ≤ 32, subtitle ≤ 40; charset printable ASCII plus `× ÷ − ≤ ≥ ≠ √ π`; answer-position balance
   per tier; determinism).
3. The first build is your reference for distractors, explanations, student text and tests, NOT for prompt pools:
   `cartridges/facts-<addition|subtraction|multiplication|division|combo>/generator.py` and
   `tests/test_facts_<op>.py`. Read them; they will be deleted by the lead once the new set is in. Keep their R-form
   misconception keys and student text unless something is wrong.

## Deliverables (your operation is named at the bottom)
1. Four cartridges `cartridges/facts-<op>-<range>/` (ids at the bottom), each with:
   - `cartridge.json`: protocol `fnm-cart/1`, version `1.0.0`, `"grade": "Facts"`, `picker_order`, title, subtitle,
     seed (table at the bottom), `"items_per_tier": 24`, standards as `CCSS.MATH.CONTENT.<grade>.<domain>.<cluster>.<n>`
     (table at the bottom), 5 tiers named as in pools.py with a one-line `description` each, the misconception catalog
     (`student`: what a kid reads after the wrong door, ≤ 80, kind, names the right idea; `teacher`: names the wrong
     rule), and a `"bounds"` string stating the range, each tier's forms and pools in words, and the distractor rules.
   - `generator.py`: `generate(manifest, rng) -> list[dict]`, stdlib only, deterministic (only the `rng` passed in;
     never iterate a `set`). **One generator file for all four ranges, byte-identical in the four directories**; it
     takes the range from the id (`int(manifest["id"].rsplit("-", 1)[1])`). Exactly 24 items per tier, prompts unique
     per tier, each part's floor met, 4 choices, balanced answer positions per tier (round-robin positions, then shuffle
     the order with `rng`).
2. One test file `tests/test_facts_<op>.py` covering all four, parametrized by id. At minimum:
   - the four `generator.py` files are byte-identical;
   - golden cases: every misconception key yields its expected wrong value on a hand-worked prompt of each form;
   - an independent re-check of EVERY baked item: parse the prompt with
     `^(\d+|\?) ([+−×÷]) (\d+|\?) = (\d+|\?)$` (exactly one `?`), solve with plain Python, never the generator;
   - pools: every item's form + pair is in its tier's pools (rebuild the pools in the test from the words of pools.py,
     independently, not by importing the generator), every part's floor holds, no ÷ 0, no ambiguous missing number;
   - distractors on `baked.json`: 4 distinct values, wrong values non-negative integers ≤ 999, ≥ 2 near, ≤ 1 far;
     each answer rank (smallest .. largest of the four values) holds the answer in 15-35% of a tier's items; the
     ones-digit rule (below);
   - a checker self-test: planted bad items the checker must reject (wrong answer, a pair outside the tier's pools, a
     too-far distractor set): a disproof that the checker can fail.
3. Bake + validate each id: `.venv/Scripts/python -m fnm bake <id>`, then `.venv/Scripts/python -m fnm validate <id>`
   (must print `valid`). Bake twice and `cmp` the `baked.json` (byte-identical).

## Distractors (the old rules, extended to the missing-number forms)
Wrong values from modelled misconceptions first, `ARITH` only to fill; first key listed wins a value collision; a
key that yields the answer is dropped. **At least two near wrong values, at most one far.** Near:
- addition, subtraction (every form): within ±1, ±2 or ±10 of the answer;
- multiplication R and division S (the answer is a product): within the larger factor of the answer (one group off);
- multiplication C/S, division R and C (the answer is a factor): within ±2.

Keys (rename only with a reason in your report; student text ≤ 80):
- Addition R (`a + b = ?`): `ONE_OFF` s ± 1, `SUBTRACTED` |a − b|, `NO_CARRY` s − 10 when the ones make a ten,
  `TENS_SLIP` s ± 10 otherwise. C/S (`a + ? = s`, `? + b = s`; the answer m is the missing part, k the shown one):
  `MISSING_ADDED` k + s (added the two numbers you can see; far), `MISSING_ONE_OFF` m ± 1, `MISSING_TENS` m ± 10
  (two-digit ranges: the trade forgotten when you count up across a ten, or a tens slip).
- Subtraction R (`s − a = ?`): `ONE_OFF`, `ADDED` s + a, `SMALLER_FROM_LARGER`, `FORGOT_TRADE`, `TENS_SLIP` as in the
  old cartridge. C (`s − ? = b`, answer a): `MISSING_ADDED` s + b, `MISSING_ONE_OFF` a ± 1, `MISSING_TENS` a ± 10.
  S (`? − a = b`, answer s): `START_SUBTRACTED` |b − a| (took away instead of adding back), `MISSING_ONE_OFF` s ± 1,
  `START_NO_CARRY` s − 10 when a + b regroups, `MISSING_TENS` s ± 10 otherwise.
- Multiplication R: `GROUP_OFF`, `ADDED`, `DROPPED_CARRY`, `TENS_SLIP`, `PARTIAL_PRODUCTS` as in the old cartridge
  (the last three only where a factor is ≥ 11). C/S (`a × ? = p`, `? × b = p`; answer m, shown factor k):
  `MISSING_ONE_OFF` m ± 1, `MISSING_SUBTRACTED` p − k (far), `MISSING_PRODUCT` p itself (wrote the product; far).
- Division R (`p ÷ a = ?`): `GROUP_OFF` q ± 1, `SUBTRACTED` p − a, `MULTIPLIED` p × a (≤ 999), `TENS_SLIP` where the
  quotient is ≥ 11. C (`p ÷ ? = b`, answer the divisor a): `MISSING_ONE_OFF` a ± 1, `MISSING_SUBTRACTED` p − b,
  `MISSING_MULTIPLIED` p × b (≤ 999). S (`? ÷ a = b`, answer p): `START_GROUP_OFF` a × (b ± 1) (one group off),
  `START_ADDED` a + b (far), `START_TENS` p ± 10 where a factor is ≥ 11 (`DROPPED_CARRY`'s value when the ones
  product carries).

**No middle tell**: each of the four ranks holds the answer in 15-35% of a tier's items (assign a target rank
round-robin per tier, take the least-used feasible rank: an answer of 0 is always the smallest).
**No ones-digit tell**: where the ones digit is not the whole fact, a kid must not answer from the ones digit alone.
Applies per tier to the items whose answer is ≥ 20 in addition and subtraction, and to multiplication R and division S
items with a factor ≥ 11 and answer ≥ 20: among those items (when a tier has ≥ 8 of them), the answer is the only
choice with its ones digit in at most 25%. The ±10 keys exist for this.

## Explanations (≤ 160): the fact and one reusable strategy
R forms as in the old cartridges (counting on, doubles, near doubles, make ten, tens then ones, think addition, ×2
doubles, ×5 half of ×10, ×9 is ×10 minus a group, 11-15 split as 10 and the rest, a neighbour fact, the fact family).
Missing forms say the whole fact, the missing number, and how to find it:
`7 + ? = 15: 7 + 8 = 15, so ? = 8. Count up: 7 + 3 = 10, then 5 more.` /
`? − 6 = 9: add back, 9 + 6 = 15, so ? = 15.` / `6 × ? = 42: 6 × 7 = 42, so ? = 7.` /
`42 ÷ ? = 7: 7 × 6 = 42, so ? = 6.` / `? ÷ 6 = 7: 6 × 7 = 42, so ? = 42.`

## Content quality (what matters most)
Read a dozen baked items per tier of each range as the kid would. Exactly one right choice? Could a kid win by a
pattern (always the middle value, the only even one, the only one-digit one, the only one ending in the right digit)?
Do the levels feel easy to hard within the range? Is a missing-number prompt unambiguous? Fix the generator if not.
Choices are shuffled by the map at display time, so choice text never depends on position.

## Non-goals / concurrency contract
- Touch ONLY your four `cartridges/facts-<op>-*/` dirs and `tests/test_facts_<op>.py`. Do NOT edit PROTOCOL.md,
  LIBRARY.md, `briefs/`, `fnm/`, `console/`, `maps/`, `emulator/`, `tools/`, `tests/conftest.py`, the old facts
  cartridges, or any other cartridge or test.
- Do NOT run `fnm insert`, `fnm emit` or `fnm sync` (shared generated files; the lead does that once). Do NOT commit.
  No UEFN, no Verse.
- In the full suite, failures in other builders' new files, in the old facts tests, and in `test_emit.py` /
  `test_carts_js` / the slot lint (they fail once a new `baked.json` exists until the lead inserts) are not yours: list
  them, carry on.
- Checkpoint every deliverable to disk the moment it exists. Throwaway scripts go in
  `C:/Users/kicki/AppData/Local/Temp/claude/D--PyCharm-Projects-fortnitemath/7584642b-64be-4cc8-9fb5-f30d94f12b6c/scratchpad/facts2/<op>/`.
- The lead may send fixes after your report: apply, re-bake, re-validate, re-run your test file, report again.

## Report (your final message; short)
- Files created; your test count; the full-suite result (which failures are not yours).
- Per cartridge, per tier: 3 sample items (prompt / choices / answer / each wrong choice's key), the answer-rank
  distribution, and the ones-digit-twin share where the rule applies.
- The disproof you ran (a sabotage or planted item your tests caught, then restored).
- Anything decided differently from this brief or pools.py, and why.
- The shakiest assumption in your work, stated plainly.

## Ids, titles, seeds, standards
`picker_order` runs 1-20 across the whole Facts grade so the HUD's 4-wide grid reads one operation per row, ranges
left to right. Standards are CCSS ids written `CCSS.MATH.CONTENT.<id>`.

| Op | id | Title | Subtitle | Seed | picker_order | Standards |
|---|---|---|---|---|---|---|
| add | `facts-add-10` | Addition to 10 | Sums up to 10 | 20261051 | 1 | K.OA.A.4, K.OA.A.5, 1.OA.C.6, 1.OA.D.8 |
| add | `facts-add-20` | Addition to 20 | Sums 11 to 20 | 20261052 | 2 | 1.OA.C.6, 1.OA.D.8, 2.OA.B.2 |
| add | `facts-add-50` | Addition to 50 | Sums 21 to 50 | 20261053 | 3 | 1.NBT.C.4, 1.OA.D.8, 2.NBT.B.5 |
| add | `facts-add-100` | Addition to 100 | Sums 51 to 100 | 20261054 | 4 | 1.NBT.C.4, 1.OA.D.8, 2.NBT.B.5 |
| sub | `facts-sub-10` | Subtraction to 10 | Take away from 10 or less | 20261055 | 5 | K.OA.A.5, 1.OA.B.4, 1.OA.C.6, 1.OA.D.8 |
| sub | `facts-sub-20` | Subtraction to 20 | Take away from 11 to 20 | 20261056 | 6 | 1.OA.B.4, 1.OA.C.6, 1.OA.D.8, 2.OA.B.2 |
| sub | `facts-sub-50` | Subtraction to 50 | Take away from 21 to 50 | 20261057 | 7 | 1.OA.D.8, 2.NBT.B.5 |
| sub | `facts-sub-100` | Subtraction to 100 | Take away from 51 to 100 | 20261058 | 8 | 1.OA.D.8, 2.NBT.B.5 |
| mul | `facts-mul-5` | Times Tables to 5 | Factors 0 to 5 | 20261059 | 9 | 2.OA.C.4, 3.OA.A.4, 3.OA.C.7 |
| mul | `facts-mul-10` | Times Tables to 10 | Factors 0 to 10 | 20261060 | 10 | 3.OA.A.4, 3.OA.B.5, 3.OA.C.7 |
| mul | `facts-mul-12` | Times Tables to 12 | Factors 0 to 12 | 20261061 | 11 | 3.OA.A.4, 3.OA.C.7, 4.NBT.B.5 |
| mul | `facts-mul-15` | Times Tables to 15 | Factors 0 to 15 | 20261062 | 12 | 3.OA.A.4, 3.OA.C.7, 4.NBT.B.5 |
| div | `facts-div-5` | Divide by 1 to 5 | Times tables to 5, backwards | 20261063 | 13 | 3.OA.A.4, 3.OA.B.6, 3.OA.C.7 |
| div | `facts-div-10` | Divide by 1 to 10 | Times tables to 10, backwards | 20261064 | 14 | 3.OA.A.4, 3.OA.B.6, 3.OA.C.7 |
| div | `facts-div-12` | Divide by 1 to 12 | Times tables to 12, backwards | 20261065 | 15 | 3.OA.A.4, 3.OA.C.7, 4.NBT.B.6 |
| div | `facts-div-15` | Divide by 1 to 15 | Times tables to 15, backwards | 20261066 | 16 | 3.OA.A.4, 3.OA.C.7, 4.NBT.B.6 |
| mix | `facts-mix-10` | Mixed to 10 | + − to 10, × ÷ to 5 | 20261067 | 17 | union of add-10, sub-10, mul-5, div-5 |
| mix | `facts-mix-20` | Mixed to 20 | + − to 20, × ÷ to 10 | 20261068 | 18 | union of add-20, sub-20, mul-10, div-10 |
| mix | `facts-mix-50` | Mixed to 50 | + − to 50, × ÷ to 12 | 20261069 | 19 | union of add-50, sub-50, mul-12, div-12 |
| mix | `facts-mix-100` | Mixed to 100 | + − to 100, × ÷ to 15 | 20261070 | 20 | union of add-100, sub-100, mul-15, div-15 |

## If your operation is `mix`
The other four operations are finished and audited: `cartridges/facts-{add,sub,mul,div}-*/` and their tests. Each mix
tier is 6 items from each operation's own cartridge at the paired range and the SAME tier (same pools, same floors
scaled to 6: a part's floor `n` becomes `ceil(n / 4)`), the same forms, distractors, explanations and student text.
Copy each generator's rules into one generator (never import them); prefix every misconception key with its operation
(`ADD_ONE_OFF`, `SUB_MISSING_ADDED`, `MUL_GROUP_OFF`, `DIV_START_ADDED`, ...). Tier names say both operations' tier
in ≤ 24 chars where they can (`Easy facts`, ..., `Missing numbers`, `Missing first numbers`). Your test re-checks every
item independently, asserts the 6/6/6/6 split per tier, and asserts that every mix prompt that also appears in its
operation's own `baked.json` at the same tier has the same answer.
