# fortnitemath — custom Fortnite island (UEFN)

Control folder for a UEFN island built with Claude. The UEFN project itself lives in
`%USERPROFILE%\Documents\Fortnite Projects\<ProjectName>` (UEFN creates it); this folder
holds the MCP wiring, notes, and planning docs.

## How Claude drives UEFN
- UEFN 42.00+ (Aug 2026) embeds an official MCP server: http://127.0.0.1:8000/mcp (`.mcp.json` here).
- Per UEFN project, once: Project Settings → enable **Python Editor Scripting** and **UEFN MCP Toolsets**;
  set MCP to auto-start (Editor Preferences, where the port can also be changed).
- UEFN must be open with the project loaded before starting Claude here, or `unreal-mcp` won't connect.
- Toolsets: Verse file read/write + build, Creative device placement and @editable props,
  Scene Graph entities/components, play sessions (Play-in-Client), editor Python.
- Docs: https://dev.epicgames.com/documentation/fortnite/uefn-mcp

## Gotchas
- MCP uses XYZ coordinates, not UEFN's LUF — convert carefully for spatial math. Units are cm.
- MCP calls can hitch/hang the editor; batch work, don't spam calls.
- Verify by screenshot/playtest, not by a successful tool return.
