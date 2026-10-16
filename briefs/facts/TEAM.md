# Facts wave (2026-10-15)

Aaron: a **Facts** selection beside the grade levels; categories addition, subtraction, multiplication, division,
combo; each with levels that scale (addition within 10 up to 100, multiplication factors up to 5 up to 15; subtraction
and division mirror). Content spec: `cartridges/LIBRARY.md` "Facts". Lead: Opus main session (plan, seams, audit,
insert, play check, commit). Builders: one Sonnet agent per cartridge from `BRIEF.md`; addition, subtraction,
multiplication and division in parallel, combo after those four pass audit (it copies their rules).

Plan audited 2026-10-15 by a fresh Opus agent before any build; folded in: the ones-digit tell at levels 3-5, combo
built last with operation-prefixed keys, each answer rank 15-35%, misconception collisions and examples, the grade
grid instead of a wide row, grade and `picker_order` validation, the rewritten order tests.

## Decisions
1. Facts is a picker **grade** (`"grade": "Facts"`), not a new mode: no director, save or boss-mode change. Levels =
   the cartridge's 5 tiers, climbed station by station (LIBRARY.md says why; selectable levels = a third picker step,
   left for Aaron).
2. Order: numeric grades ascending, then word grades A-Z, then no grade; so the step reads Grade 6, 7, 8, Facts and the
   29 existing cartridges keep their registry indices 0-28 (`DebugAutoPick` values, tools, notes stay right). Within a
   grade: the optional manifest field `picker_order` (int, default 0), then title, then id. PROTOCOL §3, §6b; additive,
   no protocol bump (§9).
3. Labels: a numeric grade shows as `Grade 7`, a word grade as itself (`Facts`): HUD grade buttons, the skill step's
   line, the emulator's headings and card badges.
4. HUD: four grade buttons in one column push the grade step (logo + BOSS BATTLE + buttons) past the top of a 1080p
   screen (2026-10-13 measure: 503 px with two grades, 797 with the logo; ~85 px per grade). Past `GradeColumnAfter`
   (3) grades the step shows them two to a row in the skill step's two-column frame, read row by row (Grade 6 | Grade
   7, Grade 8 | Facts): two rows, the height measured in play. One row of four was rejected: the BOSS BATTLE cell
   fills the panel's width and would stretch to four buttons.
5. Boss mode draws from every cartridge, so Facts items join its pool (5 of 34 cartridges). Left as is; flagged to Aaron.
6. PROTOCOL §4c records Aaron's bounds for grade-Facts cartridges (number size is the scaling axis there only).
7. `fnm validate` checks the grade (≤ 12 chars, §5 charset: it is now button text) and that `picker_order` is an int.

## Ownership
| Who | Owns |
|---|---|
| Builder `<id>` (x5, Sonnet) | `cartridges/<id>/`, `tests/test_<id_underscored>.py` only |
| Lead | `PROTOCOL.md`, `cartridges/LIBRARY.md`, `fnm/emit.py`, `fnm/validate.py`, `console/verse/fnm_ui.verse`, `emulator/app.js`, `emulator/e2e/`, `tests/test_emit.py`, `tests/test_validate.py`, `tests/test_hud_layout.py`, insert/sync/BuildAll, GOALS, memory, commit |

## Verify (lead, before commit)
- Every builder report audited: 3+ items per tier read as a kid would; independent re-check of 2 random items per tier.
- `fnm insert` each id; `pytest -q` green; `cd emulator && npm run e2e` green (plays every cartridge).
- `fnm sync starter` + VerseToolset `BuildAll` clean.
- In play: a frame of the grade step showing Grade 6 / 7 / 8 / Facts inside the screen, and a Facts run's first
  question (`DebugAutoPick` = a Facts index). Hooks back to ship values after.
