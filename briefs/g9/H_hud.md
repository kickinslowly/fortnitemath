# Brief H: HUD builder (G9 "Now" 2, the recap card, HUD copy)

Read `briefs/g9/TEAM.md` first: file ownership, the UEFN write lock, the copy-only-your-files compile rule, the machine
rules and the report format all apply. You are **H**. You own `console/verse/fnm_ui.verse`, `tools/make_hud_art.py`,
the HUD PNGs in `tools/art/`, `tests/test_hud_layout.py`, and the `textures()` function of `tools/import_art.py`.

## Context (checked unless marked belief)
- Spec: `reviews/race-2026-10-13/REVIEW.md` §4 P0 row 2 and §10 Now 2; `sources/ux_critique.md` (tile and slate
  findings, "Target hierarchy", table 3.10, recommendation #5 recap card, #7 copy).
- **The defect, measured 2026-10-13 from a play frame:** the four answer tiles on the slate render B = (0,255,255),
  C = (0,255,246), D = (255,255,0). B and C look the same cyan, and D is yellow while the door/world D is orange. The
  intended colours are `FnmDoorColors` (`fnm_ui.verse` ~line 37): A white, B (0.3,0.55,1.0), C (0.2,0.9,0.3),
  D (1.0,0.55,0.1). The tiles are one white-ring texture (`FNM_Art.T_fnm_tile`, drawn by `tools/make_hud_art.py`)
  tinted with `SetTint`. Why the tint saturates is NOT diagnosed (belief: the UI applies the tint in a space or with a
  gain that clips the channels). Find out, then fix it.
- **Do not change `FnmDoorColors`' values.** `tests/test_hud_layout.py` pins them equal to `tools/build_course.py`
  `LETTER_COLOURS` (the door paint and arena pads, S's file). If the HUD needs different numbers to LOOK like those
  colours, add a HUD-only table (e.g. `FnmTileTints`) or pre-coloured tile textures, and pin whatever you add in the test.
- The tile letter is 20 px today: the smallest text on the slate, and it is the key to the whole game. Make it 40 px.
- D (the director builder) is editing every other Verse file in parallel and will call your new methods.

## Deliverables

1. **Tile colours fixed and SEEN.** Either retuned tints or four pre-coloured tile PNGs (`make_hud_art.py`, deterministic,
   no PIL dependency if the script has none today; imported with `tools/import_art.py` under the lock). Then, under the
   lock: copy `fnm_ui.verse` into the Verse root, `BuildAll`, start a session with `tools/playtest.py` (D keeps
   `DebugAutoPick` at 0 in the director it has synced, so a session should reach a question; if it shows the picker,
   note it in the TEAM log and try again after D's next release), take frames with the four tiles on screen, **sample
   the pixels of each tile's fill and letter, and report the RGB numbers.** Pass: the four tiles are four clearly
   different hues, A white, B blue, C green, D orange, and D's hue matches the orange door paint (S is re-painting the
   doors in parallel; a door may or may not be in frame). Stop the session and release the lock when you have them.
2. **Tile letters at 40 px**, the tile grown to fit, the slate still inside Fortnite's HUD clear zone (the uefn-mcp skill:
   a top-centre panel wider than ~1190 px at 1080p clips the GAME MODE box and the minimap). Seen in the same frames.
3. **The recap card API** (D calls it; land it FIRST, compiled into the Verse root, before items 1-2 if you can, so D is
   not blocked):
   ```
   ShowRecap(Prompt:string, Choices:[]string, RightIndex:int, Steps:string, Verdict:string):int   # returns a generation
   EndRecapIf(Generation:int):void                                                                 # no-op if superseded
   ```
   `ShowRecap` shows the SOLVED item on the slate right away: the prompt, the tiles with the right one lit (the others
   dimmed), a steps line (the explanation), and a verdict line (e.g. "CORRECT!  -1.8 s", in green). It returns a
   generation; `EndRecapIf` clears the recap only if no newer `ShowRecap` / `ShowQuestion` happened since. The director
   then calls `ShowQuestion` for the next item. Keep the slate's height stable between the recap and the question
   (ux_critique P2: the slate jumped between ~225 and ~335 px). Append a line to the TEAM log when it is in the Verse
   root: `H: ShowRecap compiled in the Verse root`.
4. **HUD copy in `fnm_ui.verse`** (ux_critique #7, table 3.10):
   - the picker heading matches its step (today "CHOOSE YOUR SKILL" sits over "Pick a grade");
   - finish-board buttons: "RACE AGAIN" and "NEW SKILL" (were NEW RACE / CHANGE SKILL); D uses the same words;
   - `FnmFeedRecord`: today's record, not the island record ("{Who} set today's record  {Time}");
   - `FnmFeedFinish`: drop the medal word from the public line; KEEP the signature (D and boss mode call it);
   - any player-facing "stage" in this file becomes "station".
   Do not rename the game and do not remove "Fortnite" anywhere (that waits on Aaron).
5. **Tests:** `tests/test_hud_layout.py` pins the new tile tints or textures, the 40 px letter, and the new copy you can
   reach from Python (it already parses the Verse source).

## Verification you must perform
- `BuildAll` clean after your last copy into the Verse root.
- pytest green, or every failure explained as another agent's in-flight work.
- A disproof for the colours: set one tint to the old saturating value, show the frame or test that catches it, restore.
- Frames READ: the four tiles at a station; the recap card if D has wired it by then (if not, say so; the parent will see it).

## Non-goals
- No title-screen picker redesign, no leagues, no logo (waits on Aaron's decisions). No changes to any other Verse file.
  Do not commit.
