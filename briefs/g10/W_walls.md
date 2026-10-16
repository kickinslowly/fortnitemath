# W: the walls stop reading like wallpaper (Opus)

Read `briefs/g10/TEAM.md` first (ownership, lock, machine rules, report format), then the project `CLAUDE.md`, the
`uefn-mcp` skill, `briefs/g9/T1_surfaces_arches.md` (what the last surface pass was asked to do), the docstring and knob
block of `tools/import_titanpeak.py` (lines 1-160), and `maps/starter/LAYOUT.md` "Titan Peak".

## Why

Aaron, after playing (2026-10-13): "some of it feels repetitive and tiled too monotonously like wallpaper". Today
(2026-10-14), asked to leave it to us: "i thought some of those textured walls we created were a bit repetitive and wall
papery, so consider doing something about that."

The shader side has already been pushed hard (T1, waves 5-6): world-aligned box projection, a turned second sample on a
macro mask, colour jitter, per-actor offset, grime at the foot, a light band at the top, and a second organic Mint layer
in noise patches. That is 13 texture samples / 408 instructions, and the Xbox cost is unmeasured. The parent's read of
`<old scratch>/team/T1/v2/pairs4_A.png` (old scratch = `C:/Users/kicki/AppData/Local/Temp/claude/D--PyCharm-Projects-fortnitemath/26b46b63-033f-415b-aac7-f54eb20d33c6/scratchpad`,
read it): **the problem is now geometry, not texture.** Each hallway wall is a perfectly flat, 6 m tall engine box with
a hard straight top edge. The textures paint depth the geometry does not have (station 3's cliff ledges and ferns), so
the same painted ledge recurs every 4 m on a dead-flat plane. More shader layers will not fix a flat plane. This is the
parent's belief from one frame sheet: test it with your own frames before you build on it.

## Deliverables

1. **Diagnosis frames (checkpoint first).** Editor captures (`tools/capture.py`, no lock) at player eye height (floor +
   170 cm) for stations 1, 3, 5, 6 (ice), 7, 9, and two connectors (one stair, one winding): one looking down the hallway,
   one at ~35 degrees onto a side wall from 4 m. Build a contact sheet, read it, and write in `notes.md` what makes each
   tier read as wallpaper (repeat distance, the flat plane, the straight top edge, colour, scale). Station geometry comes
   from the course actors (`find_actors`; never assume x = 0 or z = 0; tools/build_decor.py shows how to read it).

2. **Break up the walls (the parent's recommended direction; deviate if your frames say otherwise, and say why):**
   - **Bays.** Pilasters / buttresses / ribs along every station hallway side wall and connector wall, at varied spacing
     (~5-9 m, not a metronome), 30-80 cm proud of the wall, in a contrasting stone per tier. They turn one 30 m plane into
     panels, so the texture repeat stops reading.
   - **The top edge.** Break the straight top silhouette: coping stones, crenellation, broken rock, or irregular heights,
     per tier (jungle ruin, gorge rock, frost ridge, obsidian, magma).
   - **The foot.** A plinth / rubble line where wall meets floor.
   - **More than one wall material per tier,** e.g. alternate bay panels between today's material and a second Mint wall
     material, or put the trim in its own stone. You may buy Mint materials (the `mint-gg` skill; T1's ids in
     `art/titanpeak/meshy_tasks.json`) and Meshy props (the `meshy-3d` skill), within the budget below.
   - Only if repetition still shows after the geometry: shader anti-tiling (per-bay random rotation/offset is nearly free;
     hex/stochastic tiling costs samples). Keep the master within +25% of today's instructions or justify it in the report.
   - Free assets first: UEFN's Fortnite galleries (rock, cliff, ruin, pillar props; `build_colosseum.py` shows how this
     project placed a playset kit) and scaled engine cubes painted with a tier material cost no credits. A Meshy mesh
     must pass UEFN's 30,000 LOD0 vertex cap (`tools/simplify_glb.py`, `tools/replace_mesh.py --audit`).

3. **A tool for it:** `tools/build_wall_trim.py`, idempotent via actor tag `fnm_wall_trim`, reading geometry from the
   course actors at run time (like `build_decor.py`), with `--remove` and a read-only `--check`. The parent will add
   "rerun after a course rebuild" to CLAUDE.md from your report. Imports stay in `tools/import_titanpeak.py`
   (new flags as needed; keep its "keeps existing assets" rule: deleting a material nulls it on every actor that uses it).

4. **Tests:** a geometric clearance test with a sabotage: no trim piece intersects a door wall, an arch, a vestibule or
   door trigger, a pickup pad or its row trigger, a guard spawner, a slider's travel path (station 5 containers), the
   finish area, the arena, or another decoration (torches, chalkboards, banners, set pieces, the BASE CAMP gate, station
   signs); nothing sits above the invisible lids (`build_lids.py`). Pure Python against the placement plan your tool
   computes (make the planner importable and testable without UEFN).

5. **After frames** at the same poses as deliverable 1 (before/after sheet), then ONE play session at the end (hooked
   `DebugAutoRightAnswers` run + PrintWindow frames, `tools/burst.py` / `tools/playtest.py`) to see it at Hour19 in game.
   Read every frame. The bar: a kid running a hallway should see stone architecture with panels, not a printed backdrop.

## Constraints

- **Play space is sacred.** Doors, door walls and the arches round them are not yours: side walls and connector walls
  only. Stay out of `FNM_Arena_*` actors (S is moving the arena pads this wave). Pickup pads run along the walls at
  every even station and Slap Splash pads at odd stations from 3 (`tools/build_pickups.py`): read their bounds, do not
  cover them. Guards must still path. The ice station keeps its ice.
- **Collision.** Anything a player can touch must not make a ledge that lets them climb over a wall (the skip guard sends
  wall-hoppers back, but do not invite it). Trim above head height: collision off. Proud pilasters at foot level: keep
  them shallow, collision on, and make sure no lane narrows below ~3 m.
- **Budget.** Island memory was 35,635 / 100,000 at 19 cartridges and grade 8 is about to land; it can only be measured by
  Aaron's GUI click, so estimate: report actors added, unique meshes added (with LOD0 vertices), new textures and their
  sizes. Reuse a few meshes many times rather than many unique ones. Credits: up to **2,000 Mint** and **300 Meshy**
  (monthly pool first). Record every task id in `art/titanpeak/meshy_tasks.json` (or a sibling json you name).
- UEFN writes under the lock, one batch at a time (TEAM.md). Others need sessions too: do your one play session at the end.

## Done means

Before/after sheet read by you, the session frames read, clearance test green with its sabotage shown red, `--check`
clean, `pytest -q` green, and in the report: what each tier looked like before and after in one line each, the actor and
mesh counts, credits spent, and anything that still reads as wallpaper.
