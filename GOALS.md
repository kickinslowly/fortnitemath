# GOALS

## G1 — Cartridge protocol v1 (no UEFN needed)
Spec in PROTOCOL.md. A topic plugs into any map by one command (`python -m fnm insert <id>`).
- [x] Protocol spec, Verse types, first manifest (order of operations w/ exponents + parentheses)
- [x] Toolchain `fnm/` (validate / bake / emit / insert / new) + order-of-ops generator + tests
- [x] Browser emulator (`emulator/`) — plays any cartridge per §6; inspector for proofreading
- [x] Verse console runtime (`console/verse/`) + UEFN wiring guide — written blind, compile pending G2

## G2 — First map in UEFN
- [x] UEFN 42.30 project `FortniteMath` (Blank); Python + MCP Toolsets on; MCP answers on :8000 (`tools/uefn_mcp.py`)
- [x] First Verse compile: 0 errors, 0 warnings; `fnm_director` device registered
- [ ] Visual pass: rooms are plain white engine cubes — colour per tier or a themed kit
- [ ] O1 font test (×, ÷, −, superscripts) — ÷ and − render in-game (2026-10-03); × and superscripts unchecked → pick Verse render profile
- [x] Starter course built by `tools/build_course.py` (10 stations + finish, tag-discovered); session validates, uploads and cooks
- [x] First live session 2026-10-03: EAC installed, StartSession → match Running, HUD shows title/problem/choices, no FNM errors in client log
- [x] Wrong-door return sank the player into the entry pad (`teleporter_device.Teleport`). Fixed: director `SendTo` uses `TeleportTo` 300 cm past the pad, +100 cm, facing +Y — Aaron confirmed in play 2026-10-03
- [ ] Playtest pass: walk a correct and a wrong door, reach finish; stage subtitle (blue on pale wall) is hard to read — fix contrast

## G3 — More cartridges
- [x] Second topic `integer-ops` (grade 7) — plugged in with zero toolchain changes

## Backlog (from 2026-10-02 build audit)
- [x] Order-of-ops 1.1.0: M_BEFORE_D 13, A_BEFORE_S 13 (were 0 / 3)
- [x] Order-of-ops ARITH 53% → 41% via compound misreadings (labelled with first misconception only — playtest whether that feedback reads well)
- [ ] integer-ops T3 (× ÷) is 67% ARITH: only one ×/÷ misconception exists — add one (e.g. sign of quotient vs. dividend) or make T3 3-choice
- [ ] integer-ops T4/T5 occasionally produce zero intermediates (`(−10 + 10) × (−6)`) — trivial-feeling, filter them
- [x] Verse root is `<project>/Content/` (verified); `fnm sync starter` works
