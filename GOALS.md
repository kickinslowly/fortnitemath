# GOALS

## ✅ G1 — Cartridge protocol v1 — archived to DEEP_MEMORY.md (2026-10-03)

## G2 — First map in UEFN
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
- [ ] Aaron playtest of the three penalties by walking through wrong doors (debug hook verified only)
- [x] Course layout v2 (2026-10-03): 30 m hallways, real doors, vestibule triggers, per-player barrier passage
  (`AddToIgnoreList`). Verified in play via debug hooks: right door → walk through into the next hallway;
  a closed barrier blocks; penalties on the new course. No `lock_device` needed (doors are plain props).
- [ ] Aaron playtest of v2 by walking the course start to finish
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
- [ ] Aaron playtest of the new penalties (Mud, Dizzy, Blackout) and the tier colours
- [ ] Obstacles / weapons / traps in the hallways (G4 "later")

## Backlog (from 2026-10-02 build audit)
- [x] Order-of-ops 1.1.0: M_BEFORE_D 13, A_BEFORE_S 13 (were 0 / 3)
- [x] Order-of-ops ARITH 53% → 41% via compound misreadings (labelled with first misconception only — playtest whether that feedback reads well)
- [x] integer-ops 1.1.0: T3 ARITH 67% → 34% via MUL_FOR_DIV and ADD_FOR_MUL (review ADD_FOR_MUL's wording: it is
  operation confusion more than a sign rule); T4/T5 drop items with a zero intermediate. Not yet inserted into the map
- [x] Verse root is `<project>/Content/` (verified); `fnm sync starter` works
