# H: HUD for the new race features + two layout bugs (Sonnet)

Read `briefs/g10/TEAM.md` first (ownership, the D <-> H seam, lock, compile rule, report format), then the project
`CLAUDE.md` ("HUD colours" and "HUD buttons" gotchas), the `uefn-mcp` skill, and `console/verse/fnm_ui.verse` in full.
Design background: `reviews/race-2026-10-13/sources/gamification.md` §10 (brag artifacts) and
`reviews/race-2026-10-13/sources/ux_critique.md` (search "slate").

## Hard rules

- Every colour that reaches a widget goes through `FnmUi` (`FnmUiGain` 0.259); textures get `SetTint(FnmUi(White))`.
  `tests/test_hud_layout.py` enforces it; extend that test to every widget you add.
- Never change or remove an existing `fnm_hud` method's signature (D calls them). New parameters only as named optionals.
- You cannot edit the director. To SEE your new widgets before D wires them, add a file-local debug constant in
  `fnm_ui.verse` (e.g. `FnmUiDebugBrag : logic = false`) that makes `ShowResults` call `ShowBragGrid` with sample data;
  flip it true for your test, false (ship) before you report, in the repo AND the Verse root.

## Deliverables, in this order

1. **Stubs first (the seam; checkpoint):** `SetShield(On:logic):void`, `ShowBragGrid(Marks:[]int, BossMark:int,
   Flawless:logic, NextGoal:string, Code:string):void`, `SetCompact(On:logic):void`, exactly as TEAM.md writes them,
   compiling and doing nothing. Copy to the Verse root under the lock, `BuildAll` clean, append "H stubs in root" to the
   team log. D is waiting on this; do it before anything else.
2. **SetShield:** a shield indicator beside the streak line (a small texture or a glyph). Off by default.
3. **ShowBragGrid:** on the finish board, under the medal line, a Wordle-style row of one tile per station in order
   (0 first-try right = check, 1 redeemed = a distinct amber/half state, 2 missed = cross, 3 not reached = dim empty),
   then a boss tile, a FLAWLESS badge when set, the next-goal line, and the code line when `Code` is not "". It must be
   screenshot-ready: readable at 1280x720 and fit with the existing rows and the finish buttons (`ShowFinishButtons`)
   without overlap. Reuse the check / cross / tile HUD textures already imported (`tools/import_art.py` `textures()`);
   new PNGs go through `tools/make_hud_art.py`. `HideResults` hides it.
4. **SetCompact:** a compact slate: question and choices only, smaller and higher. Two uses (D turns it on): the arena,
   where today's slate cuts the titan at the neck, and the wrong-door retry hold, where the slate covers the top half of
   the lintel letters (A B C D over the doors) for the wide camera. Also fix: a two-line prompt or an explanation line
   grows the slate ~60 px over the letters (GOALS G7 1a), and "the slate height jumps around" (review P2): a stable height.
5. **The finish board covers the world ALL-TIME board** at the podium for its 10 s (the player is stood at the podium
   when the titan falls). Move or shrink the HUD board so the world board stays readable from the podium arrival view.

## How to test

You need frames of the real HUD: a hooked run (`DebugAutoPick` + `DebugAutoRightAnswers`, plus `DebugAutoWrongAnswers N`
for misses and a retry hold) via `tools/playtest.py --until "<FNM: line>"` and `tools/burst.py` (PrintWindow, never the
foreground). You may set the director's hooks on the PLACED director device for your session (a property write under the
lock, `set_properties`, one key per call) but never edit `fnm_director.verse`; put the device's hooks back to ship values
after. Read every frame and name anything on screen that looks wrong. Required frames: the brag grid (your debug
constant), the compact slate at a retry hold with the lintel letters visible, the arena with the titan's head visible
(once D calls SetCompact; if D has not landed by your last session, say so), the finish board with the world board
visible behind it.
