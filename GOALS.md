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
- [x] Second topic `integer-ops` (grade 7) — plugged in with zero toolchain changes

## Backlog (from 2026-10-02 build audit)
- [x] Order-of-ops 1.1.0: M_BEFORE_D 13, A_BEFORE_S 13 (were 0 / 3)
- [x] Order-of-ops ARITH 53% → 41% via compound misreadings (labelled with first misconception only — playtest whether that feedback reads well)
- [ ] integer-ops T3 (× ÷) is 67% ARITH: only one ×/÷ misconception exists — add one (e.g. sign of quotient vs. dividend) or make T3 3-choice
- [ ] integer-ops T4/T5 occasionally produce zero intermediates (`(−10 + 10) × (−6)`) — trivial-feeling, filter them
- [ ] Confirm `UEFN_VERSE_SUBPATH` in `fnm/maps.py` against a real UEFN project (sync destination)
