# Brief M: import Volt, the robot host, and place him at the start and the podium (Meshy art bought 2026-10-13)

Read `briefs/g9/TEAM.md` first (the UEFN lock, the machine rules, the report format), then `BOSS_MODE.md` §15b (the
Magma Titan: the proven Meshy-to-Animated-Mesh path and its pitfalls) and the `uefn-mcp` skill. You are **M**, model
Sonnet. The manager (Opus 5.5) wrote this brief and audits your work. A second builder, **H2**, works on the HUD at the
same time; you share the UEFN lock with H2.

## You own (may edit)
New `tools/import_mascot.py`, new `tools/build_mascot.py`, new `tests/test_mascot.py` (pure-Python geometry/props
checks, no UEFN), files under `art/mascot/`. You may flip debug hook defaults in `console/verse/fnm_director.verse` with
`tools/patch.py` for your test session only (restored; `git diff console/verse/fnm_director.verse` empty when you
report). No Verse changes, no other files, no commits.

## Inputs (bought, in the repo, untracked)
`art/mascot/`: `concept.png`, `meshy_tasks.json` (task ids), `hud_portrait_raw.png` (H2's), and `raw/`:
- `rig.fbx`: Meshy's rigged character (height given as 1.5 m), ~20k triangles, 2K texture.
- One FBX per clip, each with its own skin (the titan's format): `idle_0`, `wave_28` (Big Wave Hello), `ymca_596`
  (YMCA Dance), `dance_22` (Funny Dancing 1), `victory_59` (Victory Cheer), `cheer_298` (Cheer with Both Hands Up),
  `wag_409` (Finger Wag No). The number is Meshy's action id.
- `volt_tpose.glb`: the unrigged textured model.
Volt is a chibi cyan-and-white robot with a dark visor face, glowing cyan eyes, a gold bow tie, an orange tool belt.

## Deliverables
1. **`tools/import_mascot.py`** modelled on `tools/import_boss.py`: folder `FNM_MascotArt` (not a Verse-style name; the
   skill explains why), idempotent, `lODBias` 0 on the base colour (the titan and cannon notes say why), saves.
   - **Memory probe first** (spectacle §4a: every clip as its own skeletal mesh is a full mesh copy). Import `idle_0`
     with its mesh; then try importing the other clips as **animation only** against idle's skeleton (one mesh, N
     animations). Prove it in play with frames (below). If a shared-skeleton clip plays upright and correct, ship that
     way. If any misplays (the titan's chest pound tipped flat and its knockdown spun on the spot this way), import THAT
     clip with its own mesh, the titan way, and say which.
   - Report each imported asset (skeletal mesh triangle count, texture size).
2. **`tools/build_mascot.py`**, tag `fnm_mascot`, idempotent (removes its own actors by tag, then places), reads its
   geometry from the course actors the way `tools/build_finish.py` does (so it survives a course rebuild; say so in its
   docstring). Animated Mesh devices (`/CRD_AnimatedMesh/Device_AnimatedMesh.Device_AnimatedMesh_C`; props like
   `build_bossmode.titan_clip_props`: mesh, animation, `loop` true, `initialState` "Playing"):
   - **Start:** Volt waving (`wave_28`) beside station 1's start, in view of a player standing at the spawn and while
     they pick a skill, facing that player. Not on the running line, not between the spawn and station 1's door wall,
     not hiding the door wall. About 2.5-3 m tall (measure the imported mesh's bounds and pick the scale).
   - **Podium (victory area):** Volt dancing (`ymca_596`, or `dance_22` if YMCA misplays) beside the podium area built by
     `tools/build_finish.py`, inside the frame a player sees when the run's end stands them at the podium (the director
     teleports them centred before the two lecterns under a wide camera for `PodiumWideSeconds`). He must not cover the
     RACE AGAIN / NEW SKILL labels, the lecterns or the all-time billboard. About 3 m tall.
   - Check whether the device blocks players (collision). If it does, keep him where nobody needs to walk and say so.
3. **Seen** (under the lock):
   - Editor: `tools/capture.py` viewport shots of both spots after placing (READ them).
   - Play: ONE session, `DebugAutoPick 7` + `DebugAutoRightAnswers true`. Frames in the first seconds (Volt waving at the
     start, upright, the right size, facing the player) and after "FNM: finished run 1" at the podium (Volt dancing, in
     the arrival frame, labels readable). Sample each clip over several frames (`tools/burst.py`) to prove it animates
     and stays upright. If you used the shared skeleton, these frames are the proof. Restore the hooks, copy the
     director into the Verse root, `BuildAll` clean, stop the session.
4. **`tests/test_mascot.py`**: the placement maths and device props (clip names, loop, Playing, tag), no UEFN.

## Disproof (one at least)
E.g. point the start device at a clip that does not exist and show the build script or a read-back fail, or show a
frame from before placement with no Volt; restore.

## Report (TEAM.md format), plus
The scale and positions you chose and why, shared skeleton yes/no per clip, which raw FBX files are actually imported
(the manager commits only those, the rest get git-ignored like `art/cannon/raw`), the frame paths to look at (best
first, at most 8), and anything the director could later drive (e.g. `wag_409` on a wrong door) with what it would need.
