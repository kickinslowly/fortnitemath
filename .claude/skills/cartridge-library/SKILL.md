---
name: cartridge-library
description: Build a batch of new fortnitemath cartridges (a grade's library) with parallel Opus builders — plan rows in cartridges/LIBRARY.md, fire one builder per cartridge from BRIEF.md, audit, insert once, compile, commit. Use for "add grade 7/8 topics", "new cartridges", or any multi-cartridge content build.
---

# Building a cartridge library

Rules live in PROTOCOL.md (§4a/§4b bounds, §5 limits) and `cartridges/LIBRARY.md` (the plan). This skill is the
procedure only. First run: grade 6, 2026-10-05, 9 cartridges, ~13 min wall clock, one fix round.

## Steps
1. **Plan in LIBRARY.md**: one row per cartridge (id, title ≤ 32, subtitle ≤ 40, standards, unique seed) and a tier
   plan with starting misconception keys. Also fill the "does not fit" table for the grade: pictures, sentence-long
   choices, heavy-arithmetic standards. Check every example in the plan against §4a/§4b before firing; builders
   found three of mine out of bounds (`$1.50` money ÷, `24 + 36 = 12(...)`, "Add 40 to" data).
2. **Fire one builder per cartridge**, all in one message: `Agent(model: "opus", subagent_type: "general-purpose")`
   with the prompt "Read and follow `.claude/skills/cartridge-library/BRIEF.md` exactly. Your cartridge id: `<id>`."
   Edit BRIEF.md's grade line first. Each builder owns only `cartridges/<id>/` and `tests/test_<id>.py`.
3. **While they run**, own the seams no brief covers: picker capacity (a step with > 5 skills shows two columns,
   `PickerColumnAfter` in `console/verse/fnm_ui.verse`), slot size vs PROTOCOL O4.
4. **Audit each report** as it lands: read its samples as a kid of that grade would. Watch especially for
   - **grade drift**: math from the grade above, e.g. grade-6 `|−6| − |11| = −5` needs grade-7 integer
     subtraction. Send it back with SendMessage to the same agent id.
   - **protocol conflicts** the builder reports, e.g. §4b percents vs §4a quotients. Fix PROTOCOL yourself.
5. **Insert once** at the end: `python -m fnm insert <id>` for each new id. Until then every builder's full-suite run
   shows `test_emit.py::test_generated_slot_file_lints` and `test_carts_js` failing; that is expected.
6. **Verify**:
   - `pytest -q`.
   - `cd emulator && npm run e2e`: plays a full run of every cartridge. Its grade-order test sorts by title.
   - Print 2 random items per tier per cartridge and read them. Use `PYTHONIOENCODING=utf-8`, because `−` crashes cp1252.
   - `fnm sync starter` + VerseToolset `BuildAll`.
   - The picker in play: to see one grade's skill step without clicking, write a single-grade slot straight into
     the UEFN Content folder (`fnm.emit.verse_source` on the filtered carts), BuildAll, playtest, then
     `fnm sync starter` to restore.
7. **Record**: GOALS (G3), LIBRARY.md table, the memory state file. Commit without AI attribution.

## Gotchas
- `tools/playtest.py` prints nothing to a file until it exits (no `-u`). If it hangs, probe
  `SessionToolset GetGameState` and screenshot the client (`tools/click_hud.py shot <name>`). A "logged out" title
  screen means the Epic account signed in elsewhere (Aaron's Xbox): do not click RELAUNCH.
- Pyright flags builders' generators (Optional, Fraction-vs-int). These are annotations only; tests are the gate.
- Standard ids: use `CCSS.MATH.CONTENT.6.SP.B.5.C` form for lettered sub-standards (formats drifted in grade 6).
