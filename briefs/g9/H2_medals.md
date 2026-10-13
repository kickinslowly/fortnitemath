# Brief H2: medal art and Volt on the finish board (Meshy art bought 2026-10-13)

Read `briefs/g9/TEAM.md` first (the UEFN lock, the machine rules, the report format). You are **H2**, model Sonnet. The
manager (Opus 5.5) wrote this brief and audits your diff. A second builder, **M**, imports and places the 3D mascot at
the same time; you share the UEFN lock with M.

## You own (may edit)
`console/verse/fnm_ui.verse`; `tests/test_hud_layout.py`; new `tools/make_medal_art.py`; new PNGs
`tools/art/fnm_medal_gold.png`, `fnm_medal_silver.png`, `fnm_medal_bronze.png`, `fnm_volt.png`. You may flip debug hook
defaults in `console/verse/fnm_director.verse` with `tools/patch.py` for your test sessions only (one-line flips, always
restored to ship values; `git diff console/verse/fnm_director.verse` must be empty when you report). Nothing else. No
commits.

## Inputs (already bought, in the repo, untracked)
- `art/medals/gold_raw.png`, `silver_raw.png`, `bronze_raw.png`: 1024x1024 RGBA, transparent background, one medal each
  (same design, star + laurel, cyan/blue ribbon), medal roughly x 250-780, y 115-890. Silver and bronze have a stray
  near-transparent pixel at the image edge (their bbox starts at 0,0).
- `art/mascot/hud_portrait_raw.png`: 1024x1024 RGBA, Volt (the cyan robot host) cheering, fist raised, transparent.

## Deliverables
1. **`tools/make_medal_art.py`** (stdlib + Pillow, no UEFN): reads the four raw PNGs, zeroes alpha below ~16, crops
   to the alpha bbox, pads to square (centred), resizes to 256x256 (LANCZOS), writes the four `tools/art/fnm_*.png`.
   Re-runnable, prints what it wrote. Look at each output on a dark background (composite + Read the PNG).
2. **Import** (under the lock): `.venv/Scripts/python tools/import_art.py medal_gold medal_silver medal_bronze volt`.
   `HUD_KEYS` comes from the `tools/art/fnm_*.png` glob, so the keys exist once the PNGs do. Read `import_art.py`'s
   docstring first: never `--force` (it would replace other assets); a plain run keeps existing assets and imports
   only the missing ones. Confirm `FNM_Art/T_fnm_medal_gold` etc. exist afterwards (`find_assets`).
3. **Finish board** (`fnm_ui.verse`, `ShowResults`, around line 1026, and wherever the board's widgets are built):
   - A medal image (`texture_block`, about 150-180 px square) on the medal row: the GOLD / SILVER / BRONZE texture
     picked from the `Medal` string; `Medal = ""` (boss mode can pass it) collapses it. Keep the "GOLD MEDAL" text
     beside it (the word still matters for a kid who cannot tell silver from gold).
   - Volt's portrait (`fnm_volt`, about 180-220 px) cheering on the board, placed so it overlaps no text at the 920 px
     wrap width and does not cover the board's top-times rows. Shown on every finish.
   - **Colour rule (CLAUDE.md "HUD colours"):** every new texture gets `SetTint(FnmUi(NamedColors.White))` in the same
     place the other textures get theirs; `tests/test_hud_layout.py` enforces it. Add tests for the new widgets the same
     way the file tests the existing ones (layout fits, tint rule).
   - Do not change any existing method signature (`ShowResults` keeps its parameters: the director and boss mode call
     it). New behaviour lives inside `fnm_ui.verse`.
4. **Compile:** copy only `fnm_ui.verse` into the Verse root (TEAM.md "Compiling"), `BuildAll` must return `[]`.
5. **Seen in play** (under the lock): ONE session with `DebugAutoPick 7` + `DebugAutoRightAnswers true` +
   `DebugAutoWrongAnswers 8`. The auto-run plays two runs: run 1 takes two wrong doors at each of stations 1-4 (first
   try 6/10, BRONZE: under 70%), run 2 takes none (GOLD). Confirm both from the log's "FNM: finished run N ... MEDAL,
   first try N/10" lines. Frames of the finish board after each finish (`tools/burst.py` started on the "FNM: finished
   run" line; the board shows for `ResultsSeconds`, and the podium wide camera follows). READ each frame: the medal art is the right metal, the
   portrait and medal overlap no text, colours look like the PNGs (not washed out 3.9x, not dark). Restore the hooks,
   copy, `BuildAll` clean.

## Disproof (one at least)
Point `ShowResults` at the wrong texture for one medal (e.g. SILVER shows the bronze PNG) or drop one `SetTint`, run the
test file, see it go red (or see the wrong medal in a frame), restore by re-applying the original text.

## Report (TEAM.md format), plus
The four output PNG paths, the two finish-board frame paths you want the manager to look at, and the exact widget sizes
and positions you chose.
