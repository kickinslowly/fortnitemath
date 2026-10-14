# Brief T2: Titan Peak dressing: start gate, champions' podium, tier set pieces, place banners (2026-10-13 evening)

Read `briefs/g9/TEAM.md` first (lock, machine rules, report format; test baseline now **17320 passed**; read the
"Wave 5" note at its end), then `reviews/race-2026-10-13/sources/spectacle.md` §3 (the Titan Peak world), the project
`CLAUDE.md` and the `uefn-mcp` skill. You are **T2**, model Sonnet. The manager (Opus 5.5) audits you. **T1** imports
every asset you place (`tools/import_titanpeak.py` into `FNM_TitanPeakArt`) and re-surfaces the course; it posts
`T1: props imported` to the team log when your assets exist. Until then, work out placements from the course actors.

## You own (may edit)
New `tools/build_titanpeak.py`, new `tests/test_titanpeak.py`. After **P** reports done (watch the team log for
`P released` with its final note, or ask the manager), you may also edit the trophy placement in `tools/build_landmarks.py`
(see 2). No Verse, no other files, no commits.

## Deliverables: `tools/build_titanpeak.py` (tags per part under `fnm_titanpeak`, idempotent, `--remove`, `--part X`)
Every placement reads its geometry from the course actors (like `tools/build_finish.py`) so it survives a course
rebuild; none blocks a running line, a doorway, a trigger, a pickup pad, or the camera's view of the doors; set pieces
and banners have no collision unless they stand where nobody can reach.
1. **Start gate** ("Base Camp" log gate with braziers, `SM_fnm_tp_gate`): frames the start of the run at station 1, so
   the player sees the course through it from the spawn. Volt waves at (-500, -10870) (`tools/build_mascot.py`): keep him
   in view. Put the BASE CAMP banner on the gate's blank sign board.
2. **Champions' podium** (`SM_fnm_tp_podium`, 3 steps, obsidian + gold): in the victory area built by
   `tools/build_finish.py`, where the podium wide camera sees it (the director teleports the player before the two
   lecterns). It must not cover the RACE AGAIN / NEW SKILL labels, the lecterns, the ALL-TIME billboard, or Volt
   (2387, 66701). P is putting a Titan Cup trophy nearby; once P is done, move the trophy onto the podium's top step
   (edit `build_landmarks.py`'s trophy spot only) if it looks right; say what you did. HALL OF CHAMPIONS banner above.
3. **Tier set pieces**, 2-4 per station hallway or connector, chosen by tier: t1 `jungle_pillar`, t2 `river_boulders`,
   t3 `ice_crystals`, t4 `obsidian_spire`, t5 `lava_vent`, and `rune_stone` sprinkled anywhere. Against the walls,
   varied scale/yaw (seeded, deterministic), never on the running line. Keep the total under ~60 actors (memory/draw).
4. **Place banners**: each tier's name banner over the entrance of its first station (WATERFALL GORGE at the first
   tier-2 station, etc.), readable from the approach; TITAN'S FORGE over the arena entrance.
5. **Seen** (under the lock): editor captures of each part (READ them), then ONE play session at ship hooks; you may use
   `tools/playtest.py --keys` (Aaron handed over the PC) while you hold the lock: frames at the spawn (gate + Volt),
   one banner, set pieces in one hallway. Podium: if you cannot reach it without hooks, say so; the manager runs a hooked
   session at the end.
6. **Tests**: placement maths (no overlap with doorways, running line, finish rig labels; counts per tier), tags.

## Disproof (one at least)
E.g. place a set piece on the running line and see your test fail; restore.

## Report (TEAM.md format), plus
Positions/scales per part, actor count, frame paths (best first, at most 8), and the trophy decision.
