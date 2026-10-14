# Brief P: the volcano on the horizon and the Titan Cup trophy (Meshy art bought 2026-10-13 evening)

Read `briefs/g9/TEAM.md` first (the UEFN lock, the machine rules, the report format; the test baseline there is old:
it is now **17320 passed**), then `BOSS_MODE.md` §15b and §15d (the titan and cannon Meshy-to-UEFN paths and their
pitfalls), `reviews/race-2026-10-13/sources/spectacle.md` §3 (the volcano idea: why +Y, the Only Up principle) and the
`uefn-mcp` skill. You are **P**, model Sonnet. The manager (Opus 5.5) wrote this brief and audits your work. Two other
builders share the UEFN lock with you: **V** (Verse HUD) and **A** (audio). You touch no Verse.

This is a **reversible probe** for the "Titan Peak" world, which Aaron has not chosen yet: everything you place carries
one tag and comes out with one command.

## You own (may edit)
New `tools/import_landmarks.py`, new `tools/build_landmarks.py`, new `tests/test_landmarks.py`, files under
`art/volcano/` and `art/trophy/`. You may run (not edit) `tools/glb_to_fbx.py`, `tools/capture.py`, `tools/playtest.py`,
`tools/burst.py`, `tools/build_mascot.py`. **Do not flip debug hooks** (V owns the director this round): for play frames
use the ship values and the session's natural start (the player spawns at station 1's start). No commits.

## Inputs (bought, in the repo, untracked)
- `art/volcano/concept.png`, `art/volcano/raw/volcano.{glb,fbx}` + `volcano_base_color.png`: Meshy 7.1, textured 2K,
  remeshed to ~20k triangles, origin at the bottom. A squat cartoon volcano: dark basalt cone, glowing orange crater rim,
  lava rivers in cracks, rocks and jungle plants at the base.
- `art/trophy/concept.png`, `art/trophy/raw/trophy.{glb,fbx}` + `trophy_base_color.png`: ~15k triangles, a gold cup with
  lightning-bolt handles and a fiery-fist emblem on an obsidian base with cyan trim and a blank plaque.
- Task ids: write `art/volcano/meshy_tasks.json` = `{"concept": "01a137da-0a0f-73ed-b183-676ba0498ab6", "image_to_3d":
  "01a137db-0fa3-7191-bde0-075430a34273"}` and `art/trophy/meshy_tasks.json` = `{"concept":
  "01a137da-0a51-71cc-9454-f7e5c6e7fde6", "image_to_3d": "01a137db-126d-774b-832b-e3e666858d76"}`.

## Deliverables
1. **`tools/import_landmarks.py`** modelled on `tools/import_cannon.py` (read its docstring: Meshy's own FBX welded UV
   seams and blotched; it re-exports the GLB through Blender with `tools/glb_to_fbx.py`). Folder `FNM_LandmarkArt`,
   meshes `SM_fnm_volcano`, `SM_fnm_trophy`, `lODBias` 0 on both base colours, idempotent, saves. Report triangles and
   texture sizes. The volcano's lava should glow at dusk: if the imported material has no emissive, try the simplest
   route (a material instance or the texture as emissive at low strength) for 20 minutes at most; else leave it and say so.
2. **`tools/build_landmarks.py`**, idempotent (tag `fnm_landmarks`; removes its own actors, then places; `--remove`
   removes only), reads its geometry from the course actors the way `tools/build_finish.py` does (docstring says it
   survives a course rebuild):
   - **Volcano** far beyond the race arena along +Y, centred on the course's X, 1.5-2.5 km past the arena, big enough
     to stand above the door wall from station 1's start (work out the angle from the course's heights and the
     distance; non-uniform scale is fine if the squat cone reads better taller). Not spatially loaded (always present:
     `bIsSpatiallyLoaded` false, and check cull/draw distances on the static mesh component), no collision.
   - **The titan on its rim:** the race titan's skeletal mesh on ONE Animated Mesh device (idle clip, `loop` true,
     `initialState` "Playing"; the asset paths and props are in `tools/build_race_boss.py` /
     `build_bossmode.titan_clip_props`), scaled to look like a giant standing on the crater rim, facing the course
     (-Y). This reuses an imported mesh: no new memory. If it misplays at that scale (tilted, invisible, frozen), drop
     it and say so.
   - **Trophy** in the victory area (`tools/build_finish.py` builds it: podium, two lecterns, the ALL-TIME billboard;
     `tools/build_mascot.py` puts Volt dancing at (2387, 66701), scale 2.0), about 2 m tall on a simple plinth (a gallery
     pedestal prop or a primitive), inside the podium's wide arrival shot (the director's podium camera; see M's
     report in `GOALS.md` G9 "Meshy art in the game"), covering none of: the RACE AGAIN / NEW SKILL labels, the
     lecterns, the billboard, Volt. No collision on the trophy itself if it stands where players walk; otherwise keep
     it out of the walking line and say where.
3. **Seen** (under the lock):
   - Editor: `tools/capture.py` shots of the volcano from station 1's start looking +Y, and of the trophy beside the
     podium (READ them; streaming blotches on a fresh texture are expected in editor frames, see the skill).
   - Play: ONE session at ship values (no hook flips). Frames (`tools/playtest.py` or `tools/burst.py`, PrintWindow
     only) in the first seconds at station 1: is the volcano visible above the door wall at Hour19, how big, any
     pop-in? If fog or culling hides it, find the cause (fog settings on the island, the component's draw distance)
     before reporting it as impossible. The trophy in play: if you cannot get a podium frame without hooks, say so; the
     manager runs a hooked session after V finishes.
4. **`tests/test_landmarks.py`**: placement maths (the volcano clears the door wall's top edge from the start position
   at the chosen scale and distance; the trophy's footprint overlaps none of the finish rig's labels or Volt's spot),
   device props, tag.

## Disproof (one at least)
E.g. move the volcano to a distance or scale where your test says it hides behind the door wall and see the test fail;
or a frame before placement without it.

## Report (TEAM.md format), plus
Positions, scales and why; triangles/texture sizes; whether the volcano is visible from station 1 in play (frame
path); the titan-on-rim result; the trophy spot; `build_landmarks.py --remove` tried and re-placed; anything the
director could later drive (e.g. the rim titan roaring when a player reaches the arena).
