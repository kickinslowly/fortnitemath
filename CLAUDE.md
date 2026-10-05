# fortnitemath — custom Fortnite island (UEFN)

Control folder for a UEFN island built with Claude. The UEFN project itself lives in
`%USERPROFILE%\Documents\Fortnite Projects\<ProjectName>` (UEFN creates it); this folder
holds the MCP wiring, notes, and planning docs.

## Architecture
Cartridge (topic) ↔ console (map) contract: **PROTOCOL.md** is the single source of truth.
- `cartridges/<id>/` topic source + committed `baked.json`
- `fnm/` Python toolchain — `.venv/Scripts/python -m fnm insert <id>` plugs a cartridge in
- `console/verse/` shared map runtime (every map uses the same code)
- `maps/<id>/map.json` map profile (doors per station, font profile, UEFN path); `maps/<id>/generated/` is that map's cartridge slot (never hand-edit)
- `emulator/` browser console for testing cartridges without Fortnite
- Goals: GOALS.md

## How Claude drives UEFN
- UEFN 42.00+ (Aug 2026) embeds an official MCP server: http://127.0.0.1:8000/mcp (`.mcp.json` here).
- Per UEFN project, once: Project Settings → enable **Python Editor Scripting** and **UEFN MCP Toolsets**;
  set MCP to auto-start (Editor Preferences, where the port can also be changed).
- UEFN must be open with the project loaded before starting Claude here, or `unreal-mcp` won't connect.
- Toolsets: Verse file read/write + build, Creative device placement and @editable props,
  Scene Graph entities/components, play sessions (Play-in-Client), editor Python.
- Docs: https://dev.epicgames.com/documentation/fortnite/uefn-mcp

## Gotchas
General UEFN/MCP gotchas (setup, argument quirks, Verse tags vs device refs, trigger/billboard/teleporter
settings, launch-once rule, Easy Anti-Cheat, GUI automation) live in the global skill `uefn-mcp`. Read it
before UEFN work. Project-specific:
- Tools: `tools/uefn_mcp.py` (MCP client), `tools/build_course.py` (rebuilds the whole course, idempotent via
  actor tag `fnm_course`), `tools/capture.py` (viewport PNG — look at it), `tools/uefn_status.py`,
  `tools/playtest.py` (relaunch session → screenshot of the game via PrintWindow (`tools/wincap.ps1`, never takes the
  foreground) + the director's `FNM:` log lines; `--watch N`; `--keys` clicks the game forward — ask first if Aaron may
  be in another app),
  `tools/build_rigs.py` (penalty props and effect devices; idempotent via `fnm_rigs`), `tools/build_guards.py`
  (hostile guard spawner per hallway, count rises by station; idempotent via `fnm_guards`; rerun after a course rebuild), `tools/import_art.py`
  (once per UEFN project: verdict textures + wall-colour materials, needed before Verse compiles),
  `tools/build_course.py --paint-only` (recolour walls by tier after a cartridge swap), `--doors-only` (swap the door
  props in place). Guard weapons per station: `WEAPONS` in `tools/build_guards.py`.
  Wrong-door penalty catalog and status: `console/PENALTIES.md`.
- The director finds stations by Verse tags (`console/verse/fnm_tags.verse`: `fnm_station_NN`,
  `fnm_door_a..d`, `fnm_entry`, `fnm_finish`); max 20 stations.
- Every station hallway faces +Y; connectors between them climb, drop, wind and boost (`CONNECTORS`,
  `maps/starter/LAYOUT.md`) and must end facing +Y again: the director's arrival direction is fixed (`ArrivalYaw`).
  Station hallways sit at different X and levels, so never assume x = 0 or z = 0 for a course actor.
  Ice hallways: `ICE_STATIONS` (needs the `ice` material: `python tools/import_art.py ice`).
- Test hooks on the director (ship values 0 / false / -1): `DebugAutoPick` (pick cartridge N on join with no menu;
  every other hook needs it or a real click), `DebugAutoWrongAnswers`, `DebugAutoRightAnswers` (runs
  the whole course through the real triggers and barriers to the finish screen; starts on the FIRST pick only),
  `DebugPassageTest` (drops the player into station 1's right vestibule, then behind a wrong door), `DebugDoorTest`
  (stands them before door N), `DebugStartStage` (start at that station, to try its obstacles). Drive them with
  `tools/playtest.py --after "FNM: debug door" --keys W:0.8,E:0.3,W:2.5` (`W+SPACE:2` runs and jumps).
- HUD buttons (the skill menu, CHANGE SKILL) are clicked with `tools/click_hud.py` (`launch` → read the PNG →
  `click <x> <y> <name> "FNM: grade"` at client-area pixels; it restores a minimized client and takes the
  foreground, so ask first if Aaron may be in another app).
- After any Verse edit: `python -m fnm sync starter` then VerseToolset `BuildAll`.
- Verse files are `eol=lf`; Python `write_text` on Windows rewrites them CRLF, and git then lists them modified with
  no content change. Patch them with the Edit tool or `open(..., newline='')`.
- The penalty pool lives in `maps/<id>/map.json` `penalties` (PROTOCOL §6a), not on the director.
- Content rule (Aaron, 2026-10-04): simple numbers, concept over arithmetic. The bounds are PROTOCOL §4a; every
  procedural cartridge's tests assert them against its `baked.json`. Read §4a before writing or reviewing a generator.
- The slot holds EVERY baked cartridge (`FnmCartridge_<id>()` each + `FnmCartridges()` registry, PROTOCOL §7); the
  player picks grade → skill on a HUD menu at run start (§6b). `fnm insert <id>` re-emits all of them.
