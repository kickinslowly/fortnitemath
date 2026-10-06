# Brief: build ONE grade-6 cartridge for the fortnitemath library

(Parent: change "grade-6"/"grade \"6\""/"6th grader" to the target grade before firing; see SKILL.md.)

Repo: `D:\PyCharm Projects\fortnitemath` (Windows, git bash available). Python venv: `.venv/Scripts/python`.
Test command: `.venv/Scripts/python -m pytest -q` (run it once first and note the count).

## Read first (they are the spec)
1. `PROTOCOL.md` — all of it, especially §3 (cartridge source), §4 (item shape), §4a + §4b (content bounds:
   mental math only, concept over arithmetic), §5 (validation rules: prompt ≤ 60 chars, each choice ≤ 14,
   explanation ≤ 160, misconception `student` ≤ 80, tier name ≤ 24, title ≤ 32, subtitle ≤ 40; charset =
   printable ASCII plus `× ÷ − ≤ ≥ ≠ √ π`; answer-position balance; determinism).
2. `cartridges/LIBRARY.md` — your cartridge's row and tier plan (id, title, subtitle, standards, seed, tiers,
   starting misconception keys). Follow it; improve examples where they break a limit, and report it.
3. The reference cartridge `cartridges/integer-ops/` (manifest + generator) and its test
   `tests/test_integer_ops.py` — the quality bar: golden misconception cases, an independent re-check of every
   baked answer by a method that does NOT use the generator's evaluator, and a bounds test over `baked.json`.

## Deliverables (your cartridge id is given at the bottom)
1. `cartridges/<id>/cartridge.json` — protocol `fnm-cart/1`, version `1.0.0`, grade `"6"`, standards as
   `CCSS.MATH.CONTENT.6.XX.Y.N` strings, the seed from LIBRARY.md, `items_per_tier` 40, 5 tiers, a
   misconception catalog (`student` text is what a kid reads after the wrong door: short, kind, tells the right
   idea; `teacher` text names the wrong rule). Add a `"bounds"` string stating this cartridge's §4a/§4b bounds.
2. `cartridges/<id>/generator.py` — `generate(manifest, rng) -> list[dict]`, stdlib only, deterministic,
   imports nothing from other cartridges. Wrong choices come from modelled misconceptions first, `ARITH` only
   to fill. 4 choices per item where possible (2–4 allowed). Balanced answer positions per tier.
3. `tests/test_<id with - replaced by _>.py` — at minimum:
   - golden cases: each misconception key yields its expected wrong value on a hand-worked prompt;
   - an independent re-check of EVERY baked item's answer (parse the prompt text yourself, e.g. with regex,
     and compute with `fractions.Fraction` / plain Python — not by calling the generator's solver);
   - bounds: every item meets this cartridge's `bounds` (walk the correct steps), asserted on `baked.json`;
   - no two choices of any item are equal in VALUE (e.g. `1/2` vs `2/4`, `0.5` vs `.50`, `3x + 6` vs `6 + 3x`);
     the player must never face two right doors;
   - a bounds-checker self-test with at least one prompt it must reject (a disproof: the checker can fail).
4. Standard ids: lettered sub-standards as `CCSS.MATH.CONTENT.6.SP.B.5.C`. Grade drift: no math from the grade above (grade 6 has no subtracting into negatives).
5. Bake + validate: `.venv/Scripts/python -m fnm bake <id>` then `.venv/Scripts/python -m fnm validate <id>`
   (must print `valid`). Run `bake` twice and confirm `baked.json` is byte-identical (`cmp`).

## Content quality (this is what matters most)
- Math must be doable in the head for a 6th grader, even the topic-specific part (Aaron's words: "make sure
  math is doable in head, even topic related"). Difficulty rises by concept and steps, never number size.
- Each wrong choice must be what a real student holding that misconception would pick. Check a dozen baked
  items by eye per tier and read them as a 12-year-old would: is the prompt unambiguous in ≤ 60 chars? Is
  exactly one choice right? Would a sharp kid argue a "wrong" door is also right? Fix the generator if so.
- Choices are shuffled by the map at display time (PROTOCOL §4 note), so choice text must never depend on
  position. Units in choices are fine when the unit is part of the concept.
- Explanations show the working in ≤ 160 chars.

## Non-goals / concurrency contract
- Other agents are building the other LIBRARY.md cartridges right now in their own `cartridges/<other-id>/`
  dirs and `tests/test_<other>.py` files. Touch ONLY your own two paths. Do NOT edit PROTOCOL.md, LIBRARY.md,
  `fnm/`, `console/`, `maps/`, `emulator/`, `tests/conftest.py` or any other cartridge.
- Do NOT run `fnm insert`, `fnm emit` or `fnm sync` (they rewrite shared generated files; the parent does that
  once at the end). Do NOT commit.
- When you run the full suite, a failure in another new cartridge's test file is not yours: note it, carry on.
- Checkpoint every deliverable to disk the moment it exists; what is on disk is what survives a session limit.
- If you find a real problem in the protocol or toolchain, report it; do not fix it.

## Report (keep it short)
- Files created; your test count and full-suite result.
- Three sample items per tier (prompt / choices / answer) so the parent can eyeball them.
- Anything you decided differently from this brief or LIBRARY.md and why.
- Any part of your standard that did not fit multiple choice in ≤ 60/14 chars.
- The shakiest assumption in your work, stated plainly.
