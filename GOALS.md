# GOALS

## G1 — Cartridge protocol v1 (no UEFN needed)
Spec in PROTOCOL.md. A topic plugs into any map by one command (`python -m fnm insert <id>`).
- [x] Protocol spec, Verse types, first manifest (order of operations w/ exponents + parentheses)
- [x] Toolchain `fnm/` (validate / bake / emit / insert / new) + order-of-ops generator + tests
- [x] Browser emulator (`emulator/`) — plays any cartridge per §6; inspector for proofreading
- [x] Verse console runtime (`console/verse/`) + UEFN wiring guide — written blind, compile pending G2

## G2 — First map in UEFN (blocked on install)
- [ ] Create UEFN project; enable Python Editor Scripting + UEFN MCP Toolsets; confirm `unreal-mcp` connects
- [ ] First Verse compile of console + generated cartridge; fix
- [ ] O1 font test (×, ÷, −, superscripts) → pick Verse render profile
- [ ] Build the starter course (stations + A–D doors), playtest with the order-of-ops cartridge

## G3 — More cartridges
- [ ] Second topic via `fnm new`, proving plug-and-play end to end (candidate: Aaron picks)

## Backlog (from 2026-10-02 build audit)
- [ ] Order-of-ops content: M_BEFORE_D never appears and A_BEFORE_S only 3×; add `a ÷ b × c` / `a − b + c` patterns (T1/T2), bump to 1.1.0
- [ ] ARITH is 320 of 600 distractors — look for more misconception-driven wrong answers
- [ ] Confirm `UEFN_VERSE_SUBPATH` in `fnm/maps.py` against a real UEFN project (sync destination)
