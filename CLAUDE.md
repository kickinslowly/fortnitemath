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
  `tools/playtest.py` (relaunch session → game screenshot + the director's `FNM:` log lines; `--watch N`),
  `tools/build_rigs.py` (penalty props the director moves onto a punished player; idempotent via `fnm_rigs`).
- To test penalties without walking: director `DebugAutoWrongAnswers` (Verse default; ship value 0).
  Wrong-door penalty catalog and status: `console/PENALTIES.md`.
- The director finds stations by Verse tags (`console/verse/fnm_tags.verse`: `fnm_station_NN`,
  `fnm_door_a..d`, `fnm_entry`, `fnm_finish`); max 20 stations.
- Course grid stays tight (`SPACING`/`COLS` in build_course.py) — the template floor ends near x≈13000.
- After any Verse edit: `python -m fnm sync starter` then VerseToolset `BuildAll`.
