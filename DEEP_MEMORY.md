# DEEP MEMORY

Completed goals, archived from GOALS.md. Append-only.

## ✅ G1 — Cartridge protocol v1 (no UEFN needed) — done 2026-10-02, archived 2026-10-03
Spec in PROTOCOL.md. A topic plugs into any map by one command (`python -m fnm insert <id>`).
- [x] Protocol spec, Verse types, first manifest (order of operations w/ exponents + parentheses)
- [x] Toolchain `fnm/` (validate / bake / emit / insert / new) + order-of-ops generator + tests
- [x] Browser emulator (`emulator/`) — plays any cartridge per §6; inspector for proofreading
- [x] Verse console runtime (`console/verse/`) + UEFN wiring guide — written blind, compile pending G2
Outcome: the runtime compiled in UEFN 42.30 with two Verse fixes (a `Tags` local clashed with the Tags module;
a `<transacts>` call in a `for` header). Cartridges plug in with zero toolchain changes (integer-ops proved it).

## ✅ G2 — First map in UEFN — done 2026-10-04, archived 2026-10-04
- [x] UEFN 42.30 project `FortniteMath` (Blank); Python + MCP Toolsets on; MCP answers on :8000 (`tools/uefn_mcp.py`)
- [x] First Verse compile: 0 errors, 0 warnings; `fnm_director` device registered
- [x] Visual pass v1 (2026-10-04): hallway walls coloured by tier (green, blue, purple, orange, red; finish gold) — `build_course.py --paint-only`. A themed prop kit is still open if Aaron wants more
- [x] O1 font test: ÷ − × and superscripts (², seen 2026-10-04 at stage 7) render in-game → `unicode` profile stays. ✓ ✗ glyphs don't; the verdict uses textures instead
- [x] Starter course built by `tools/build_course.py` (10 stations + finish, tag-discovered); session validates, uploads and cooks
- [x] First live session 2026-10-03: EAC installed, StartSession → match Running, HUD shows title/problem/choices, no FNM errors in client log
- [x] Wrong-door return sank the player into the entry pad (`teleporter_device.Teleport`). Fixed: director `SendTo` uses `TeleportTo` 300 cm past the pad, +100 cm, facing +Y — Aaron confirmed in play 2026-10-03
- [x] Doors playtested by Aaron 2026-10-03: right and wrong doors work, stations 1→4 reached
- [x] Finish reached in play via `DebugAutoRightAnswers` (all 10 real triggers + barriers → "Course complete! 10/10", 2026-10-04); HUD text now sits on a dark panel (contrast fixed)
Outcome: UEFN 42.30 + its MCP server drive the whole loop from Claude (place, tag, compile, play, screenshot).
Held up through ~20 play sessions on 2026-10-04 including Aaron's first full walk; the course, penalties, race layer
and guards that followed (G4) all sit on this map.
