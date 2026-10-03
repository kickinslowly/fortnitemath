# GOALS

## ✅ G1 — Cartridge protocol v1 — archived to DEEP_MEMORY.md (2026-10-03)

## G2 — First map in UEFN
- [x] UEFN 42.30 project `FortniteMath` (Blank); Python + MCP Toolsets on; MCP answers on :8000 (`tools/uefn_mcp.py`)
- [x] First Verse compile: 0 errors, 0 warnings; `fnm_director` device registered
- [ ] Visual pass: rooms are plain white engine cubes — colour per tier or a themed kit
- [ ] O1 font test (×, ÷, −, superscripts) — ÷ − × render in-game (2026-10-03); ✓ ✗ do NOT (missing-glyph diamond); superscripts unchecked → pick Verse render profile
- [x] Starter course built by `tools/build_course.py` (10 stations + finish, tag-discovered); session validates, uploads and cooks
- [x] First live session 2026-10-03: EAC installed, StartSession → match Running, HUD shows title/problem/choices, no FNM errors in client log
- [x] Wrong-door return sank the player into the entry pad (`teleporter_device.Teleport`). Fixed: director `SendTo` uses `TeleportTo` 300 cm past the pad, +100 cm, facing +Y — Aaron confirmed in play 2026-10-03
- [x] Doors playtested by Aaron 2026-10-03: right and wrong doors work, stations 1→4 reached
- [ ] Reach the finish in play; stage subtitle (blue on pale wall) is hard to read — fix contrast

## G3 — More cartridges
- [x] Second topic `integer-ops` (grade 7) — plugged in with zero toolchain changes

## G4 — Race course (Aaron, 2026-10-03)
Replace the room-and-teleport loop with a race: long hallways ending in walls of real doors the player opens.
The right door opens onto the next hallway with no stall. A wrong door triggers a surprise penalty from the
map's pool. Big red X / green CORRECT! flash. Later: obstacles, weapons, traps. Penalty catalog: `console/PENALTIES.md`.
- [x] Penalty runtime: random pick from the map's pool; Freeze and Spike live; big verdict flash; right answer moves on at once
- [x] Players start at station 1 facing the doors (Play-From-Here ignores the requested spawn point)
- [ ] Yeet via a launcher device moved under the player (SetLinearVelocity is a no-op on players)
- [ ] Penalty visuals: ice block around a frozen player, spike prop or real damage trap
- [ ] Spike once logged "respawn after 0 polls" in live play (IsActive still true 1 s after Damage?) — make the wait key off the elimination, not a fixed 1 s
- [ ] Course layout v2: hallways + real doors (prop with a door + `lock_device`), per-player passage via `barrier_device.AddToIgnoreList`
- [ ] Map profile chooses its penalty pool (map.json → director `Penalties`)
- [ ] More penalties from the catalog
- [ ] Verdict check-mark/X as textures (the HUD font has no ✓/✗ glyphs)

## Backlog (from 2026-10-02 build audit)
- [x] Order-of-ops 1.1.0: M_BEFORE_D 13, A_BEFORE_S 13 (were 0 / 3)
- [x] Order-of-ops ARITH 53% → 41% via compound misreadings (labelled with first misconception only — playtest whether that feedback reads well)
- [ ] integer-ops T3 (× ÷) is 67% ARITH: only one ×/÷ misconception exists — add one (e.g. sign of quotient vs. dividend) or make T3 3-choice
- [ ] integer-ops T4/T5 occasionally produce zero intermediates (`(−10 + 10) × (−6)`) — trivial-feeling, filter them
- [x] Verse root is `<project>/Content/` (verified); `fnm sync starter` works
