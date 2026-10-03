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
