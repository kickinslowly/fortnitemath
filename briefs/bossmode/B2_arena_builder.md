# B2 — Boss battle arena: builder tool + editor build (Opus, parallel with B1 and B3, after B0)

You place the new arena in the open UEFN project. Read first: `briefs/bossmode/README.md`; `BOSS_MODE.md` §3 (the arena:
diagram, piece table, settings, UNVERIFIED list), §4 (weapon table), §5, §11; `CLAUDE.md` (project; tools list, "never
assume x = 0", tag conventions); `maps/starter/LAYOUT.md` ("Boss arena", "Laser cannons", "Glass lids", "Pickups");
`tools/build_course.py` (helpers `box`, `ybox`, `device`, `prop`, `props`, `verse_tags`, `tag`, `clear`, `board`, `spawner`,
`arena`; constants `PAD_SIZE`, `PAD_H`, `LETTER_COLOURS`, `SIGN_COLOUR`, `BOARD`, `TRIGGER`, `TELEPORTER`, `BILLBOARD`,
`WALL_T`, `SLAB_T`), `tools/build_cannon.py` (all of it), `tools/build_guards.py` (SPAWNER, SETTINGS, WEAPONS, the accepted
list in its docstring), `tools/build_rigs.py` (GRANTER, TRIGGER_CLASS, the loadout granter binding), `tools/build_pickups.py`
(`GRANT_SETTINGS`, `granters()`), `tools/build_lids.py` (`lid()`, the hidden-sheet recipe), `tools/import_art.py`
(`WALL_COLOURS`, `materials()`), `tools/capture.py`, `tests/test_arena_layout.py` (must stay green), the global skill
`~/.claude/skills/uefn-mcp/SKILL.md` ("Devices", "Course building", "Assets", "Windows GUI automation" paragraphs).

Precondition (B0 landed and compiled): `grep -c fnm_bm_slot_5 console/verse/fnm_tags.verse` → 2, and in the project
`.venv/Scripts/python tools/uefn_mcp.py ValkyrieToolset.VerseToolset Grep '{"pattern":"fnm_bm_slot_5","pathGlob":"*.verse"}'`
finds it. If not, write the tool and its tests first (no MCP), then re-check before building.

You own: `tools/build_bossmode.py` (new), `tools/build_cannon.py` (additive: a `prefix` / `fx_tag` parameter on `cannon()`
and `label`-prefix on `shape()` / `device()`; existing calls unchanged), `tools/import_art.py` (`WALL_COLOURS` keys
`bm_wall`, `bm_floor`, `bm_perch` only), `maps/starter/LAYOUT.md` (one new section "Boss battle arena"),
`tests/test_bossmode_layout.py` (new). Nothing in `console/`, no other tools, no other tests. You drive the UEFN **editor**
only (place / set / capture / import materials): no `BuildAll`, no play session, no wav import. Do not commit.

## Repo facts
See README. MCP client: `tools/uefn_mcp.py` (`u.call(toolset, tool, args)`); toolset names in `build_course.py`
(`SCENE`, `ACTOR`, `OBJ`, `DEV`, `ASSETS`). One property per `set_properties` call, read back, then `save_assets` (the
course builders do this; a combined write silently kept an old value). Tag an actor (`verse_tags`) BEFORE setting its
sub-object settings (the tag component rebuilds them). Device bounds carry an editor margin; take heights from engine cubes.
Captures: `.venv/Scripts/python tools/capture.py out.png x y z pitch yaw` then Read the PNG. The island's spawn pads and the
whole course live at x within ±2000 of 0 and y from -12000 on; parked rigs at x -4000, y -8000..-17000 underground. The
arena goes at x 12000..16000, y -14000..-10000, floor top z 2 (nothing is there: confirm with one overhead capture before
building, `capture.py probe.png 14000 -12000 6000 -89 0`).

## Deliverables

1. **`tools/build_bossmode.py`** — docstring in the house style (what, why, idempotency, commands), `TAG = "fnm_bossmode"`,
   every constant from BOSS_MODE.md §3 as module constants (ORIGIN, ARENA_W, ARENA_L, WALL_H 800, PAD_SPOTS, PLATFORM_*,
   GATES, GATE_W/H, ALCOVE_D, PERCHES, PERCH_TOP, STONE, STONE_RISE 60, STONE_GAP 150, CANNON_Y 2200, BOSS_WEAPONS,
   GATE_WEAPONS, GATE_SETTINGS, BOSS_SETTINGS (import from build_course), GRANT_WEAPONS, ANGER_RADIUS 650, ANGER_ANGLES,
   PARK_DROP 600), and:
   - `build()`: clear(TAG); floor slab, four walls with the gate openings (each side wall as three segments + a lintel over
     each opening), the four alcoves, the lid (hidden sheet, build_lids recipe), the sign, the entry teleporter (`fnm_bm` +
     `fnm_entry`, both group knobs `Group_None`, yaw 90), the four pads (tile in `M_fnm_wall_pad_x`, trigger with the race
     pads' trigger props, letter billboard; tags `fnm_bm` + `fnm_door_x`), the platform, five boss spawners
     (`build_course.spawner(...)` with `BOSS_SETTINGS`, health asked 100000, weapon per level; tags `fnm_bm_boss` +
     `fnm_bm_slot_L`), four gate spawners (`GATE_SETTINGS`; tags `fnm_bm_gate` + `fnm_bm_slot_G`; read the weapon list back,
     exit on refusal like `build_guards`), four gate VFX (`fnm_bm_gate_fx` + slot), four perches with stones + a hidden
     trigger on each top (`fnm_bm_perch` + `fnm_bm_slot_P`, trigger props as the pads) + a beacon VFX (`fnm_bm_perch_fx` +
     slot), five granters + five grant triggers parked under the floor (`fnm_bm_grant` + `fnm_bm_slot_L`; the binding is
     the `grantItem` eventSubscriptions shape from `build_pickups.granters()`, with `TRIGGER_CLASS`; `GRANT_SETTINGS` +
     `equipItemOnGrant` 1; read item list and settings back, exit on refusal), two cannons (`build_cannon.cannon()` with
     prefix `FNM_BM_Cannon` and fx tag `fnm_bm_cannon_fx`, aimed at the platform), the parked strike (`fnm_bm_strike`),
     two blasts (`fnm_bm_blast`), the nuke VFX (`fnm_bm_nuke_fx`), five anger VFX (`fnm_bm_anger_fx` + slot). Every actor
     labelled `FNM_BM_*` and tagged TAG. `save_assets` at the end. Print one line per piece group and a final summary with
     the boss health the device kept and the probe answers.
   - `check()` (`--check`): list placed actors by label with the devices' read-back options (the shape of `build_cannon.check`).
   - `probe()` (`--probe`, no build): answers to BOSS_MODE.md §3 UNVERIFIED items that can be read from the editor:
     `ListDeviceAssets` with nameFilter `Creature`, `Wildlife`, `Sentry` (print displayName + assetPath, or "none");
     `list_properties` on a placed VFX spawner → the `visual_Effect` enum values (print them all) and `effectType` values;
     `list_properties` on an explosive device → `knockback` values; one granter's item list after setting each of the five
     weapons (accepted / refused). Record the answers in the LAYOUT.md section.
   - Fallbacks in code, not in prose: if `knockback` refuses "Large" use "Medium"; if the VFX enum has an entry whose name
     contains `Explosion`, `Smoke`, `Fire` or `Blast`, use the first such for the nuke, else `LightningBolt_01`; a refused
     weapon stops the build with the WID named (the parent decides the swap).
2. **`tools/build_cannon.py`**: `cannon(side, face, oy, ztop, boss, project, steel, glow, prefix="FNM_Cannon", fx_tag="fnm_cannon_fx")`
   and whatever label parameter `shape()` / `device()` need; the default call path (`build()`) produces byte-identical labels
   and tags to today (prove: `python -c "import ast,..."` is overkill — just run `python tools/build_cannon.py --check` before
   and after your edit with the race rig in place and diff the two outputs).
3. **`tools/import_art.py`**: `WALL_COLOURS` gains `"bm_wall": (0.12, 0.10, 0.14)`, `"bm_floor": (0.22, 0.20, 0.24)`,
   `"bm_perch": (1.0, 0.8, 0.1)`; run `python tools/import_art.py bm_wall bm_floor bm_perch` (materials only) before `build()`.
   Do not run the full `import_art.py` (B3's PNGs may be half-written; B4 imports textures).
4. **Editor build**: `python tools/import_art.py bm_wall bm_floor bm_perch`, then `python tools/build_bossmode.py`, then
   `--check`, then `--probe`. Captures (Read every PNG): overhead `capture.py bm_over.png 14000 -12000 5500 -89 0`; from the
   entry toward the boss `capture.py bm_entry.png 14000 -13700 220 -5 90`; a perch close-up showing the stones
   `capture.py bm_perch.png 12800 -13900 300 -15 60`; a gate `capture.py bm_gate.png 13000 -12800 250 0 180`; the platform
   with its five spawners and the anger ring `capture.py bm_boss.png 14000 -11500 400 -20 90`. Report what the pixels show:
   are the pads A B / C D in the letter colours with A on the LEFT as seen from the entry; do the stones step up toward the
   perch; are the gate openings real holes with a dark alcove; are the cannons aimed at the platform; is anything floating
   or sunk. Re-run `python tools/build_bossmode.py` once more and confirm the actor count is unchanged (idempotency).
5. **`maps/starter/LAYOUT.md`** section "Boss battle arena (2026-10-09, BOSS_MODE.md)": the §3 diagram, where it sits, the
   piece/tag table, the probe answers (UNVERIFIED items resolved or still open), and "rerun after": nothing (it reads no
   course geometry) — it is independent of a course rebuild.
6. **`tests/test_bossmode_layout.py`**: pads inside the walls, apart, and not over the platform, the stones or the perches;
   perches inside the walls and off the gates; stone rises ≤ 70 (the proven jump) and gaps ≤ 200; gates on the side walls
   between y 0 and ARENA_L; cannons on the walls short of the platform (as `test_arena_layout` does for the race); the boss
   weapons are in `build_guards.WEAPONS` and are neither snipers nor launchers; GATE_SETTINGS has `spawnOnTimer False`,
   `despawnGuardsWhenDisabled True`, `spawnCount 2`; BOSS_MODE §4's weapon WIDs appear in GRANT_WEAPONS in level order;
   every tag string the tool writes is declared in `fnm_tags.verse`; `build_cannon.cannon` defaults still spell
   `FNM_Cannon` / `fnm_cannon_fx` (the race rig). `tests/test_arena_layout.py` must stay green.

## Non-goals
No Verse (B1). No play session, no `BuildAll`, no wav or PNG import (B4). Do not move or re-place anything tagged
`fnm_course`, `fnm_cannon_rig`, `fnm_rigs`, `fnm_audio`, `fnm_pickups`, `fnm_guards`, `fnm_decor`, `fnm_finish_rig`,
`fnm_lids`, `fnm_island`. Do not change `build_course.py`, `build_guards.py`, `build_rigs.py`, `build_pickups.py`,
`build_lids.py` — import from them. No creature spawner placement this round even if the probe finds one: report it.

## Concurrency
B1 edits `console/verse/*` (no effect on you). B3 edits `tools/make_announcer.py`, `tools/build_audio.py`, `tools/art/*`,
`tests/test_hud_layout.py`, `console/AUDIO.md` (no effect on you; do not run `import_art.py` without keys). You are the only
agent on the MCP until B4; if a call hangs > 60 s, screenshot the editor (README) and dismiss the dialog. UEFN hung during
planning — expect that once.

## Verification
- `.venv/Scripts/python -m pytest -q tests/test_bossmode_layout.py tests/test_arena_layout.py` green; the whole suite as in
  README (sibling-gated reds only).
- One disproof by hand: set `STONE_RISE = 90` in a scratch copy → `test_bossmode_layout` red (name the test); restore.
- Idempotency: two consecutive builds → same `--check` actor count; `find_actors(tag "fnm_bossmode")` count printed.
- `build_cannon.py --check` output before and after your edit is identical for the race rig.
- `git diff --stat`: only your five files.

## Report
README format, plus: the probe answers verbatim (device paths, enum values, accepted/refused weapons), the boss health the
spawners kept, the actor count, the five PNG paths with what each shows, anything you decided differently and why, your
shakiest assumption stated plainly (the jump chain is the planner's).
