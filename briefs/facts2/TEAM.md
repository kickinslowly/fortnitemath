# Facts by range (2026-10-16)

Aaron: the first Facts build climbed one cartridge from within 10 to within 100 across a run. He wants one cartridge
per range, the whole run in it, easy to hard within it: addition and subtraction to 10, 20, 50, 100; then the same
pattern for the other operations. His calls (2026-10-16 picker): multiplication = times tables to 5, 10, 12, 15
(division backwards); levels 7-10 get hard with missing numbers; combo becomes Mixed per range. 20 cartridges replace
the 5 of 2026-10-15.

Lead: Opus main session (spec `pools.py` + `BRIEF.md`, LIBRARY/PROTOCOL, HUD grid, boss-mode draw, emulator e2e,
audit, insert, sync, BuildAll, play check, commit). Builders: one Sonnet agent per operation (add, sub, mul, div in
parallel), then mix after those four pass audit.

## Decisions
1. Same picker grade `Facts`; 20 skills, `picker_order` 1-20 (add, sub, mul, div, mix; ranges ascending).
2. HUD: a skill step with more than 10 buttons shows them 4 to a row, read row by row (`PickerGridColumns`), so Facts
   is a 5 x 4 grid: one operation per row, ranges left to right. 4 columns, not 5: five ~18-character titles at the
   stock button size would run past a 1080p screen's width; 5 rows match the grade-6 step's height (870 px, fits).
3. 24 items per tier (PROTOCOL §5 floor; 2 drawn per tier per run): 2,400 items, up from 840; slot size and island
   memory get measured after insert.
4. Boss mode draws a grade first, then a skill in it: 20 Facts skills would otherwise be 41% of its questions (5 of 34
   was 15%); grade-first keeps Facts at one grade's share (25%).
5. One generator per operation, byte-identical in its four dirs, range from the id (no new manifest field).
6. Old `facts-addition`, `-subtraction`, `-multiplication`, `-division`, `-combo` and their tests are deleted after
   the new set passes audit.

## Ownership
| Who | Owns |
|---|---|
| Builder add / sub / mul / div / mix (Sonnet) | `cartridges/facts-<op>-*/`, `tests/test_facts_<op>.py` |
| Lead | everything else: `briefs/facts2/`, PROTOCOL, LIBRARY, `fnm/`, `console/verse/`, `emulator/`, `tests/test_emit.py`, `tests/test_hud_layout.py`, old facts removal, insert/sync/BuildAll, GOALS, memory, commit |

## Verify (lead, before commit)
- Each builder report audited: items read per tier per range as a kid would; an independent re-check of every item
  by the lead's own script (answer, pools, near/far, ranks, ones digits).
- `fnm insert`; `pytest -q` green; `cd emulator && npm run e2e` green.
- `fnm sync starter` + VerseToolset `BuildAll` clean.
- In play: a frame of the Facts skill step (20 buttons, 4 to a row, inside a 1080p screen); a run on a range cartridge
  (`DebugAutoPick` = a Facts index) showing a missing-number door question at stations 7-10; hooks back to ship values.
