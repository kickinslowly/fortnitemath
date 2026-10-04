# GOALS

## ✅ G1 — Cartridge protocol v1 — archived to DEEP_MEMORY.md (2026-10-03)

## ✅ G2 — First map in UEFN — done 2026-10-04 (archive to DEEP_MEMORY once stable a session)
- [x] UEFN 42.30 project `FortniteMath` (Blank); Python + MCP Toolsets on; MCP answers on :8000 (`tools/uefn_mcp.py`)
- [x] First Verse compile: 0 errors, 0 warnings; `fnm_director` device registered
- [x] Visual pass v1 (2026-10-04): hallway walls coloured by tier (green, blue, purple, orange, red; finish gold) — `build_course.py --paint-only`. A themed prop kit is still open if Aaron wants more
- [x] O1 font test: ÷ − × and superscripts (², seen 2026-10-04 at stage 7) render in-game → `unicode` profile stays. ✓ ✗ glyphs don't; the verdict uses textures instead
- [x] Starter course built by `tools/build_course.py` (10 stations + finish, tag-discovered); session validates, uploads and cooks
- [x] First live session 2026-10-03: EAC installed, StartSession → match Running, HUD shows title/problem/choices, no FNM errors in client log
- [x] Wrong-door return sank the player into the entry pad (`teleporter_device.Teleport`). Fixed: director `SendTo` uses `TeleportTo` 300 cm past the pad, +100 cm, facing +Y — Aaron confirmed in play 2026-10-03
- [x] Doors playtested by Aaron 2026-10-03: right and wrong doors work, stations 1→4 reached
- [x] Finish reached in play via `DebugAutoRightAnswers` (all 10 real triggers + barriers → "Course complete! 10/10", 2026-10-04); HUD text now sits on a dark panel (contrast fixed)

## G3 — More cartridges
- [x] Second topic `integer-ops` (grade 7) — plugged in with zero toolchain changes

## G4 — Race course (Aaron, 2026-10-03)
Replace the room-and-teleport loop with a race: long hallways ending in walls of real doors the player opens.
The right door opens onto the next hallway with no stall. A wrong door triggers a surprise penalty from the
map's pool. Big red X / green CORRECT! flash. Later: obstacles, weapons, traps. Penalty catalog: `console/PENALTIES.md`.
- [x] Penalty runtime: random pick from the map's pool; Freeze and Spike live; big verdict flash; right answer moves on at once
- [x] Players start at station 1 facing the doors (Play-From-Here ignores the requested spawn point)
- [x] Penalty visuals (2026-10-03, seen in play): ice block around a frozen player, a spear ring bursting up for Spike, an air-vent launch for Yeet (rigs: `tools/build_rigs.py`)
- [x] Yeet launches for real (air vent moved under the player, ~75 m skydive); back at the station entry on landing
- [x] Spike respawn wait no longer races the elimination (polls start after the damage; "after 8 polls" in play)
- [x] Aaron playtest of the penalties by walking through wrong doors (2026-10-04): all work (Mud not drawn that run)
- [x] Course layout v2 (2026-10-03): 30 m hallways, real doors, vestibule triggers, per-player barrier passage
  (`AddToIgnoreList`). Verified in play via debug hooks: right door → walk through into the next hallway;
  a closed barrier blocks; penalties on the new course. No `lock_device` needed (doors are plain props).
- [x] Aaron playtest of v2 start to finish (2026-10-04): completed once; door C's whole wall stood out, so all doors
  now share one look and the coloured letters tell them apart (`build_course.py --doors-only`, 2026-10-04; letters seen in play)
- [x] Door C is now a dark stone bank wall with a wooden door (oil-rig "Green" rendered blue like B)
- [x] Every door type opens with E in play and its trigger fires on the way through (A, C, D tested 2026-10-03)
- [ ] One test session showed "Performance Warning: See editor" on the HUD (nothing in the editor log; seen once
  in four runs). Not seen again in ~12 sessions on 2026-10-04 and not in any log; watch item. UEFN's memory panel
  is GUI-only
- [x] Map profile chooses its penalty pool (map.json `penalties` → generated `FnmMapPenalties`, PROTOCOL §6a)
- [x] More penalties (2026-10-04, all seen in play): Mud (slowed + sepia), Dizzy (colour swirl), Blackout (black
  screen, wake at entry); Freeze also frosts the screen. Catalog: `console/PENALTIES.md`
- [x] Verdict check mark / cross as textures (`tools/import_art.py`), seen in play; verdict moved to the lower third so
  it no longer covers the player
- [x] Aaron playtest of the new penalties (2026-10-04): Dizzy was confusing, not dizzying. Wanted: blurred vision
  coming in and out, spinning/wobble. Built 2026-10-04: two spins on the spot (character `TeleportTo` yaw steps) then
  `PP_RadialBlur` pulsed in/out for 6 s; seen in frames from a background-throttled client (~10 fps), so whether the
  spin is smooth at full fps is unverified (`DizzySpinStepSeconds` 0.033 if it strobes). A real camera wobble is not
  exposed to Verse as far as we know
- [x] Obstacles (2026-10-04, seen in play): gold 70 cm hurdles (walking stops at one, run+jump clears it), baffle
  walls, shipping containers sliding across the hallway (Verse `Slide`, `fnm_slider`); harder per station
  (`OBSTACLES` in `tools/build_course.py`). Not checked: what a sliding container does to a player it hits
- [x] Race layer (2026-10-04, seen in play via debug hooks): 3-2-1-GO countdown, race clock (left, under GAME MODE),
  streak ("4 IN A ROW!") + speed boost on first-try right answers, FINISH + GOLD/SILVER/BRONZE medal + time +
  personal best + island record, then an automatic new run 12 s later. Boost speed (1.6x) not yet felt in play
- [x] Aaron playtest of the race layer and obstacles (2026-10-04): obstacles feel good, harder with multi-step problems
  and guards but achievable; hurdles great. Couldn't notice the streak (one finish). Time vs personal best vs island
  record not obvious; wants top scores on the big finish screen. Building: big streak line, streak survives guard
  deaths, boost 2.0x, a centre finish board with your time / best / island record (holder's name) / top 5 session
  times / next-run countdown. Built and seen in play 2026-10-04 (two auto-right runs: NEW BEST!, NEW RECORD!, one
  row per player). Board is per session only
- [ ] Hurdle variation as we polish (Aaron 2026-10-04: "would recommend additional variation")
- [ ] Leaderboard that persists across sessions (today's board is per session; per-player best could use
  `persistable`, an island-wide board needs a different store)
- [ ] Weapons / traps in the hallways (G4 "later"; guard drops now supply weapons, traps still open)
- [ ] Aaron playtest of the 2026-10-04 evening build: Dizzy spin smoothness, the 2.0x boost, the finish board, guard
  weapons at stations 3/5/7/9, identical doors. Claude's own composed play pass is also pending (held while Aaron
  was in Dota: play sessions take the foreground)
- [x] Hostile guards (Aaron, 2026-10-04; seen in play at station 5): a guard spawner per hallway, 1,1,2,2,3,3,4,4,5,5
  guards by station (`tools/build_guards.py`), Wildlife team, low accuracy, health bars, drop their gun. Up only while a
  player is on that station. Any elimination respawns the player at their station's entry with the pistol
- [x] Spike death now lands with the spears (~0.4 s, was ~1.3 s), seen in play
- [x] Aaron playtest of guards (2026-10-04): good. Dropped guns fill the player's slots, fine by him. Wanted:
  progressively better weapons from the guards as stations rise, so the player ends up with them. Built 2026-10-04:
  `WEAPONS` ladder in `tools/build_guards.py` (pistol → suppressed SMG → tactical shotgun → AR UC/R/VR → heavy AR VR)
  through the spawner's `itemList`; seen in play 2026-10-04 (station 7: four guards with rifles, feed "eliminated
  … with a rifle"). Four AR guards killed a standing player in ~6 s from first hit: balance is Aaron's call.
  Stations 1–2 keep the loadout's rare pistol

## Backlog (from 2026-10-02 build audit)
- [x] Order-of-ops 1.1.0: M_BEFORE_D 13, A_BEFORE_S 13 (were 0 / 3)
- [x] Order-of-ops ARITH 53% → 41% via compound misreadings (labelled with first misconception only — playtest whether that feedback reads well)
- [x] integer-ops 1.1.0: T3 ARITH 67% → 34% via MUL_FOR_DIV and ADD_FOR_MUL (review ADD_FOR_MUL's wording: it is
  operation confusion more than a sign rule); T4/T5 drop items with a zero intermediate. Not yet inserted into the map
- [x] Verse root is `<project>/Content/` (verified); `fnm sync starter` works
