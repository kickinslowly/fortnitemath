# Brief T1: Titan Peak surfaces and door arches (art bought 2026-10-13 evening; Aaron approved Titan Peak)

Read `briefs/g9/TEAM.md` first (lock, machine rules, report format; test baseline is now **17320 passed**; read the
"Wave 5" note at its end), then `reviews/race-2026-10-13/sources/spectacle.md` §3 (the Titan Peak world: tiers and
biomes), the project `CLAUDE.md` (import_art and paint gotchas: a deleted material nulls every reference; the whole course
lost its paint that way on 2026-10-13) and the `uefn-mcp` skill. You are **T1**, model Opus. The manager (Opus 5.5)
wrote this brief and audits you. **T2** (Sonnet) dresses the scene at the same time with props you import (see below);
V (Verse HUD), A (audio) and P (volcano + trophy) also share the UEFN lock.

## The world, per tier (stations per tier come from the course; `build_course.tier_count()` / `paint_jobs()`)
| tier | place | floor | wall | arch skin |
|---|---|---|---|---|
| 1 green | BASE CAMP (jungle) | `t1_floor` mossy flagstones | `t1_wall` carved green-grey blocks | arch_t1 (grey volcanic stone, moss) |
| 2 blue | WATERFALL GORGE | `t2_floor` river stone | `t2_wall` blue slate strata | arch_t2 river stone |
| 3 purple | FROST RIDGE (the ice station) | `t3_floor` snow + violet ice | `t3_wall` purple rock, snow | arch_t3 frost |
| 4 orange | OBSIDIAN DESCENT | `t4_floor` basalt hex tiles | `t4_wall` obsidian glass | arch_t4 obsidian |
| 5 red | MAGMA CORE | `t5_floor` lava crust | `t5_wall` red rock, lava veins | arch_t5 magma |
| arena | TITAN'S FORGE | `forge_floor` iron plates | (leave) | - |

## You own (may edit)
`tools/import_art.py` (all of it this round; H and S are gone), `tools/build_course.py` (paint code only, plus the
flags you add), new `tools/import_titanpeak.py`, new `tools/build_arches.py`, `maps/starter/LAYOUT.md`,
`tests/test_arena_layout.py`, new `tests/test_titanpeak_surfaces.py`, files under `art/titanpeak/`. No Verse, no commits.

## Inputs (bought; all ids in `art/titanpeak/meshy_tasks.json`)
- Mint PBR materials (tileable, 1024², zip of base colour / normal / roughness / metalness / height + preview): eleven
  asset ids in `mint_materials`. Fetch each with the Mint MCP read tools (`mcp__mint__list_asset_artifacts`, then
  `mcp__mint__get_asset_artifact` for `maps_zip`; load them with ToolSearch), unzip to
  `art/titanpeak/materials/<key>/`. `t1_floor` is already there (checked: tiles seamlessly). Look at each one tiled 2x2
  (Read the PNG); if one is unusable, say which. Do not start any Mint or Meshy generation.
- Door arch: `art/titanpeak/arch/raw/arch_t1.glb` (+ base colour; Meshy 7.1, remeshed ~8k tris, origin bottom; two
  pillars, round top, a blank keystone at the top centre for the lintel letter). Four retextures on the SAME UVs (ids in
  `arch_retexture`): download them with `mcp__meshy__meshy_download_model` (format glb, save_to
  `art/titanpeak/arch/raw/arch_t<N>.glb`); if a call is refused by the permission checker, note it and continue.
- For T2, import these too (T2 places them; you only import): `art/titanpeak/gate/raw/gate.glb`,
  `art/titanpeak/podium/raw/podium.glb`, the six `art/titanpeak/set/raw/*.glb`, and the seven banner PNGs
  `art/titanpeak/banners/*_raw.png` (1376x768 RGBA, text spelled right; crop to alpha bbox like
  `tools/make_medal_art.py` and import as textured quads the way `import_art.py` does its signs).

## Deliverables
1. **`tools/import_titanpeak.py`**: one idempotent import of everything above into `FNM_TitanPeakArt` (statics via the
   `tools/import_cannon.py` route: GLB -> `tools/glb_to_fbx.py` -> `StaticMeshTools.import_file`; `lODBias` 0 on every
   base colour; creates or replaces only its own assets, NEVER deletes or re-imports a material something else uses).
   Flags per group (`--arch`, `--props`, `--banners`, `--materials`) so a rerun can be narrow. **Names** (T2 codes
   against them): meshes `SM_fnm_tp_<name>` (`gate`, `podium`, `arch`, `jungle_pillar`, `river_boulders`, `ice_crystals`,
   `obsidian_spire`, `lava_vent`, `rune_stone`), arch skins `M_fnm_tp_arch_t1..t5`, banner quads
   `SM_fnm_tp_banner_<key>` (keys = the PNG stems without `_raw`), surfaces `M_fnm_tp_<t1_floor ... forge_floor>`. Report triangles and
   texture sizes. **Do the props + banners import FIRST** and post `T1: props imported` to the team log
   (`$LOG`) so T2 can start placing.
2. **Tier surfaces.** Walls and floors of each tier's stations and connectors wear that tier's Mint material instead of
   the flat `WALL_COLOURS` paint; the arena floor wears `forge_floor`. The hard part is **tiling**: course pieces are
   scaled primitives, so a plain imported material stretches. Find a route that tiles at a sensible world scale (about
   2-4 m per repeat): e.g. `MaterialTools` / `MaterialInstanceTools` (both in UEFN's toolset list) for a world-aligned or
   UV-scaled instance, or per-actor UV scale. Probe it on ONE wall first, capture, READ. Keep the old flat paint one
   command away (a flag), and keep `--check-paint` meaningful. Doors and their letter colours must still read against
   the new walls at Hour19 (the HUD tiles are white / blue / green / orange: the doors must match them, CLAUDE.md "HUD
   colours"); if a wall texture fights a door colour, darken or desaturate that material, do not touch the doors.
3. **Door arches** (`tools/build_arches.py`, tag `fnm_arches`, idempotent, `--remove`): an arch framing every answer door
   (4 per station, 10 stations, plus the arena's pads only if it reads well there: optional), the tier's skin, scaled to
   the door opening; the keystone sits behind/around the existing 3D lintel letter (`tools/build_door_marks.py`) without
   hiding it; nothing inside the opening (the doorway, the door trigger, the barrier must work exactly as before); no
   collision on the arch where it could catch a player in the doorway. Reads its geometry from the course actors so it
   survives a course rebuild (say so in its docstring; CLAUDE.md gets a line from the manager).
4. **Seen** (under the lock): editor captures of one station per tier (READ them), then ONE play session (ship hooks;
   you may use `tools/playtest.py --keys W:2` etc. while you hold the lock: Aaron handed over the PC) with frames at
   station 1 and as far along as you get. Doors readable and coloured like the HUD tiles, arches around them, textures
   tiling, not stretched, not blinding at Hour19. Then `tools/build_course.py --check-paint` clean.
5. **Tests**: tier -> material mapping, arch placement maths (inside the wall plane, clear of the opening), flags.

## Disproof (one at least)
E.g. point one tier at another tier's material and see `--check-paint` (or your test) fail; restore.

## Report (TEAM.md format), plus
The tiling route you found (or why none works), per-tier frame paths, the arch scale/offset, triangles/texture sizes,
the exact commands to rebuild everything, and anything that should go into CLAUDE.md's tool list.
