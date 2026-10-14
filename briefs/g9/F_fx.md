# Brief F: right-answer and boost FX: gate burst, pillar of light, boost trail (zero credits; 2026-10-13 night)

Read `briefs/g9/TEAM.md` first (lock, report format, "Wave 4-5": foreground allowed only while you hold the lock), then
`reviews/race-2026-10-13/sources/spectacle.md` §2 rows "Right answer" and "Streak / boost" (the spec, budgets and probes),
`BOSS_MODE.md` §15f-15g (how `tools/build_fx.py` authors Niagara systems over UEFN's Niagara MCP toolsets and how
`console/verse/fnm_fx.verse` spawns them), the project `CLAUDE.md`, and the `uefn-mcp` skill. You are **F**, model Opus; the
manager (Opus 5.5) audits you. Other builders may share the UEFN lock (T1: surfaces; keep holds short). The game is DOORS
OF DOOM on the Titan Peak world; HUD colours and the doors must stay readable.

## You own (may edit)
`tools/build_fx.py`, `console/verse/fnm_fx.verse`, `console/verse/fnm_director.verse` (FX call sites only),
`console/verse/fnm_bossmode.verse` (only if a call fits there), `tests/test_fx*.py` (new or existing), `BOSS_MODE.md` §15f
note lines for the new systems. No commits. Ship debug hooks restored.

## Deliverables (in order; each ships on its own)
1. **`NS_fnm_gate_burst`**: when a right answer opens the barrier, a white-gold flash, a vertical shock ring at the barrier
   plane and ~120 velocity-aligned sparks, ~0.6 s. Spawned at the door the player chose.
2. **`NS_fnm_sky_pillar`**: a ~40 m gold beam rising from the right door's vestibule for ~1.2 s (a `StaticBeam` vertical,
   the `NS_fnm_laser` glow/core layers retuned gold). Visible to everyone (that is the point: a kid sees the class's
   progress ahead). Probe its cull distance first: is it drawn at 50-100 m in play? If not, find the setting (the
   volcano needed far-art settings; Niagara has its own fixed bounds / cull settings) or say what limits it.
3. **Boost trail**: during the speed boost, the director spawns a tiny burst at the player's position every ~0.12 s:
   `NS_fnm_trail_cyan` (streak 1-2), `_gold` (3-5), `_fire` (6+), ~20 particles, 0.6 s life. Budget: 16 players x 8/s.
   Stop the spawns when the boost ends or the player finishes, respawns, or is penalised.
4. Optional if 1-3 are done and seen: `PP_ActionLines` speed lines for the boosting player only (the probe in the
   spectacle doc: does BlendIn honour a strength below 1?). Skip if it fights the HUD.

## Seen (under the lock)
`python tools/build_fx.py <name>` for each new system (a system must exist before the Verse naming it compiles), copy your
Verse files to the root, `BuildAll` `[]`. ONE hooked session: `DebugAutoPick 7` + `DebugAutoRightAnswers true` (boosts
happen on streaks): burst frames (`tools/burst.py`) catching a gate burst, a pillar (also one from far away if a frame
allows: the auto-run gives you the next station's view of the previous pillar? if not, say so), and a trail at each
colour. READ them. Restore hooks, `BuildAll` clean, stop the session. Frame rate: note any hitch the log shows.

## Disproof (one at least)
E.g. a test that fails if a spawn call names a system `build_fx.py` does not build; a frame before/after.

## Report (TEAM.md format), plus
Each system's look (frame paths, best first, at most 8), the cull-distance finding, particle counts, every call site
(file:line, moment), and anything that hurt readability.
