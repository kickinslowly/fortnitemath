# Brief: build ONE grade-8 cartridge for the fortnitemath library

(Lead: retarget the grade before firing; see SKILL.md. Retargeted to grade 8 on 2026-10-14, G10.)

Repo: `D:\PyCharm Projects\fortnitemath` (Windows, git bash available; the path has a space, quote it). Python venv:
`.venv/Scripts/python`. Test command: `.venv/Scripts/python -m pytest -q`. Baseline on the clean tree, 2026-10-14:
**17493 passed**. Nine other builders and several other agents share this machine and repo, so do NOT run the full
suite at the start: iterate with your own file (`.venv/Scripts/python -m pytest -q tests/test_<id>.py`) and run the
full suite ONCE at the end.

## Read first (they are the spec)
1. `PROTOCOL.md`: §3 (cartridge source), §4 (item shape), §4a + §4b (content bounds: mental math only, concept over
   arithmetic; §4b now has grade-8 rows: Exponents, Scientific notation, Roots, Pythagorean, π volumes, Coordinates and
   lines, Two-way tables, and the grade-8 part of Angles), §5 (validation rules: prompt ≤ 60 chars, each choice ≤ 14,
   explanation ≤ 160, misconception `student` ≤ 80, tier name ≤ 24, title ≤ 32, subtitle ≤ 40; charset = printable
   ASCII plus `× ÷ − ≤ ≥ ≠ √ π`; answer-position balance; determinism), §7 (render profiles: `^7` becomes a
   superscript, `^−3` stays a caret).
2. `cartridges/LIBRARY.md`, section "Grade 8": your cartridge's row and tier plan (id, title, subtitle, standards,
   seed, bounds, tiers, starting misconception keys, the cartridges to "Read"), and the "Rules for every grade-8
   cartridge" list above the tier plans (charset traps, exponent text, high-school drift list, grade-7 ground,
   equal-value traps, one-answer estimates, "which move?" checks, unique prompts). Follow it; improve examples where
   they break a limit or a bound, and report it.
3. The reference cartridge `cartridges/integer-ops/` (manifest + generator) and its test `tests/test_integer_ops.py`:
   the quality bar: golden misconception cases, an independent re-check of every baked answer by a method that does
   NOT use the generator's evaluator, and a bounds test over `baked.json`. Then the cartridges your tier plan says to
   "Read" (manifest, generator, test) for how a `bounds` string is stated and asserted. Read, never edit.

## Deliverables (your cartridge id is given at the bottom)
1. `cartridges/<id>/cartridge.json`: protocol `fnm-cart/1`, version `1.0.0`, grade `"8"`, title and subtitle from
   LIBRARY.md, standards as `CCSS.MATH.CONTENT.8.XX.Y.N` strings, the seed from LIBRARY.md, `items_per_tier` 40,
   5 tiers, a misconception catalog (`student` text is what a kid reads after the wrong door: short, kind, tells the
   right idea; `teacher` text names the wrong rule). Add a `"bounds"` string stating this cartridge's §4a/§4b bounds.
2. `cartridges/<id>/generator.py`: `generate(manifest, rng) -> list[dict]`, stdlib only, deterministic, imports
   nothing from other cartridges. Wrong choices come from modelled misconceptions first, `ARITH` only to fill. 4
   choices per item where possible (2-4 allowed). Balanced answer positions per tier.
3. `tests/test_<id with - replaced by _>.py`, at minimum:
   - golden cases: each misconception key yields its expected wrong value on a hand-worked prompt;
   - an independent re-check of EVERY baked item's answer (parse the prompt text yourself, e.g. with regex, and
     compute with `fractions.Fraction` / plain Python / `math.isqrt`, not by calling the generator's solver);
   - bounds: every item meets this cartridge's `bounds` (walk the correct steps), asserted on `baked.json`;
   - no two choices of any item are equal in VALUE, compared exactly (`2^8` vs `4^4`, `√16` vs `4`, `0.333...` vs
     `1/3`, `20 × 10^6` vs `2 × 10^7`, `y = 2x + 4` vs `y = 4 + 2x`, `(4, −2)` vs `(4, −2)`); the player must never
     face two right doors. For word choices (`Similar`/`Congruent`, `Rational`/`Irrational`, `Yes`/`No`) assert that
     exactly one is true for the item;
   - a bounds-checker self-test with at least one prompt it must reject (a disproof: the checker can fail).
4. Standard ids: lettered sub-standards as `CCSS.MATH.CONTENT.8.EE.C.7.A`. Grade drift: no high-school math.
   Never: simplified radicals (`2√5`), adding or multiplying radicals, rational exponents, function notation `f(x)`,
   domain and range, quadratics, exponential functions as a topic, systems that need an equation multiplied before
   adding, trigonometry, pyramid volume, correlation coefficients, conditional-probability notation.
5. Bake + validate: `.venv/Scripts/python -m fnm bake <id>` then `.venv/Scripts/python -m fnm validate <id>` (must
   print `valid`). Run `bake` twice and confirm `baked.json` is byte-identical (`cmp`).

## Content quality (this is what matters most)
- Math must be doable in the head for an 8th grader, even the topic-specific part (Aaron's words: "make sure math is
  doable in head, even topic related"). Difficulty rises by concept and steps, never number size.
- Each wrong choice must be what a real student holding that misconception would pick. Check a dozen baked items by
  eye per tier and read them as a 13-year-old would (print them with `PYTHONIOENCODING=utf-8`, because `−` crashes
  cp1252): is the prompt unambiguous in ≤ 60 chars? Is exactly one choice right? Would a sharp kid argue a "wrong"
  door is also right (an estimate that is also close, a move that also works, a word that is also true)? Fix the
  generator if so.
- Choices are shuffled by the map at display time (PROTOCOL §4 note), so choice text must never depend on position.
  Units in choices are fine when the unit is part of the concept.
- Explanations show the working in ≤ 160 chars.

## Non-goals / concurrency contract
- Other builders are building the other grade-8 cartridges right now in their own `cartridges/<other-id>/` dirs and
  `tests/test_<other>.py` files. Touch ONLY your own two paths. Do NOT edit PROTOCOL.md, LIBRARY.md, `fnm/`,
  `console/`, `maps/`, `emulator/`, `tools/`, `tests/conftest.py` or any other cartridge or test.
- Do NOT run `fnm insert`, `fnm emit` or `fnm sync` (they rewrite shared generated files; the parent does that once at
  the end). Do NOT commit. No UEFN, no Verse.
- When you run the full suite, a failure in another new cartridge's test file is not yours: note it, carry on. Until
  the parent inserts the new cartridges, `test_emit.py::test_generated_slot_file_lints` and `test_carts_js` fail once
  any new `baked.json` exists; that is expected. Other agents are also editing Verse, HUD and scene tools in this repo:
  a failure in their tests is not yours either.
- Checkpoint every deliverable to disk the moment it exists; what is on disk is what survives a session limit.
- Throwaway scripts go in your own scratch folder,
  `C:/Users/kicki/AppData/Local/Temp/claude/D--PyCharm-Projects-fortnitemath/64261e2b-78b4-449e-905d-de9081377a49/scratchpad/team/C/<id>/`,
  never the shared scratchpad root: in the grade-7 run, builders overwrote each other's `show.py` there.
- If you find a real problem in the protocol, the plan or the toolchain, report it; do not fix it.
- The lead may send you fixes after your report (SendMessage). Apply them, re-bake, re-validate, re-run your test file,
  and report again in the same shape.

## Report (your final message; keep it short)
- Files created; your test count and full-suite result; your `bounds` string.
- Three sample items per tier (prompt / choices / answer) so the lead can eyeball them.
- The disproof you ran (a sabotage of the generator or a planted bad item that your tests caught, then restored).
- Anything you decided differently from this brief or LIBRARY.md and why.
- Any part of your standard that did not fit multiple choice in ≤ 60/14 chars.
- The shakiest assumption in your work, stated plainly.
