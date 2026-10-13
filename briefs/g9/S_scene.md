# Brief S: scene builder (G9 "Now" 1, 3 and 9's guard: doors, letters, lights, floors, island time)

Read `briefs/g9/TEAM.md` first: file ownership, the UEFN write lock, the machine rules and the report format all apply.
You are **S**. You own `tools/build_course.py`, `tools/build_guards.py`, `tools/build_decor.py`, `tools/build_island.py`,
a new `tools/build_door_marks.py`, `WALL_COLOURS` + `materials()` in `tools/import_art.py`, `maps/starter/LAYOUT.md`,
`tests/test_arena_layout.py`. **You run no play sessions and edit no Verse.** You verify by property read-back and
editor viewport captures (`tools/capture.py`), which you READ. The parent sees your work in play afterwards.

## Context (checked unless marked belief)
- Spec: `reviews/race-2026-10-13/REVIEW.md` §4 P0 rows 1 and 3, §7 item 1-2, §10 Now 1, 3, 9; detail in
  `sources/spectacle.md` and `sources/ux_critique.md`. Read the project `CLAUDE.md` Gotchas (every builder script, its
  tag, its rerun rules) and the global `uefn-mcp` skill (door dressing, Alphabet props, Customizable Light, island
  settings, `MSYS_NO_PATHCONV`).
- **P0 regression, read back 2026-10-13:** every door is identical in play and in the editor. `FNM_S01_DoorB` reads
  `doorAnimatingMaterial: null` and `DoorComponent.overrideMaterials: [null]`, while the materials `M_door_face_a..d`
  exist. `door_dress` (`build_course.py` ~309) sets both; it was seen working in the editor on 2026-10-09. Which later
  rebuild dropped it is NOT diagnosed (belief: a later `build_course.py` path re-placed or reset the doors without
  `door_dress`, or the paint never persisted through a save/reload).
- Door colours: `LETTER_COLOURS` in `build_course.py` (A white, B blue, C green, D orange), pinned equal to the HUD's
  `FnmDoorColors` by `tests/test_hud_layout.py`. Do not change the values.
- The course: 10 stations, every station hallway faces +Y, a wall of four doors at its end; hallways sit at different
  X and levels (never assume x = 0 or z = 0). `build_decor.py` already reads geometry from the course actors; copy
  that approach.

## Deliverables (checkpoint each)

1. **Doors painted again, and the cause found.** Diagnose why the paint was lost (git log/blame on `build_course.py`
   and the other builders since fb38d7d; which code path places or resets door props without `door_dress`). Fix the
   cause in code so a rerun cannot lose it again, then re-apply the paint to all 40 doors (`--doors-only` or a new
   narrower flag) and **read back all 40** (`doorAnimatingMaterial` and the `DoorComponent` override, each pointing at
   its own letter's material). `save_assets` / save the level so it persists, then read back again. Editor captures of
   two stations' door walls: report what the pixels show (each panel in its colour with its letter tile).
2. **3D lintel letters + letter-colour arch lights**, a new idempotent builder `tools/build_door_marks.py`
   (actor tag `fnm_door_marks`, removes its own actors on rerun, reads door positions from the course actors).
   - Letters: the CRG_Props Alphabet PPIDs (uefn-mcp skill: ~206 x 201 x 50 cm, readable face +Y at yaw 0, a `color`
     option, `bNoCollision` settable). One over each door's lintel, facing the runner (the runner faces +Y, so the
     readable face must point -Y toward them: work out the yaw and confirm it in a capture), in the closest
     `color` enum value to each letter's colour. `bNoCollision` true and `bCanBeDamaged` false, read back.
     Mind the existing decor on the door wall (station numbers, chalkboards, torches from `build_decor.py`): nothing may
     overlap.
   - Lights: one Customizable Light (`PID_Device_PointLight`) per door arch in the letter colour, a glow, not a flood
     (`lightSizePercentage` ~50, intensity 60-100; the skill notes `lightSize` refuses writes). Read back.
   - Seen: editor captures from a runner's eye at the hallway's start and from 8 m, two stations.
3. **Station 1 without a guard.** `build_guards.py`: station 1 gets no guard spawner (count 0); stations 2-10 unchanged.
   Rerun it, read back: no spawner tagged for station 1, the others as before. D makes the director tolerate it.
4. **Darker tier floors** (today engine-cube floors stay white and glare by day). Add a dark mid-tone floor material per
   tier (`WALL_COLOURS` keys like `floor_tier1..5`, imported with `tools/import_art.py <keys>`), and have `paint()` /
   `--paint-only` paint each hallway's floor by its tier; the ice station's floor stays ice; connectors may stay as they
   are or take the next station's floor (your call, say which). Gotcha: flat Kd materials render much lighter than their
   numbers (boss mode's stone needed 0.09). Editor captures; the final look is judged in play under a locked time of day.
5. **Island time of day:** `build_island.py --time <value>` sets Island Settings `timeOfDayOverride` (read its enum
   values with `list_properties` first; today it reads `NoOverride`) and reads it back; `--check` reports it. **Do not
   change the live value**; list the enum values in your report. The parent compares Hour10/14/17/19 in play.
6. `maps/starter/LAYOUT.md`: door paint (the cause and the fix), the door marks, floors, station 1's guard.

## Verification you must perform
- Every builder you change or add reruns idempotently: run it twice, count tagged actors after each (same number).
- pytest green, or every failure explained as another agent's in-flight work (`tests/test_arena_layout.py` and
  `tests/test_hud_layout.py` read `build_course.py`).
- A disproof for the door fix: show that the code path you blamed really drops the paint (or explain why a reproduction
  was not safe), then that the fixed path keeps it.
- Frames READ for every visual claim.

## Non-goals
- No course rebuild (`build_course.py` with no flags) unless the door fix truly needs it: a full rebuild means rerunning
  decor, finish, guards, pickups, lids, race boss, door marks (`CLAUDE.md` lists them) and takes a long time. If you
  conclude it is needed, stop and report instead.
- No Verse, no play sessions, no Meshy or Mint, no new decor beyond the letters and lights. Do not commit.
