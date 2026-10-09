# Boss battle mode — builder briefs

Spec: `BOSS_MODE.md` at the repo root (read it first; every brief points into it by section). Recipe: global skill
`multi-model-delegation`. Fable (the parent session) wrote these; Opus builds; Fable audits every diff and re-runs the
acceptance checks before anything is committed. **Nobody commits.**

## Order and parallelism

```
B0  tags + cue enum + sync + BuildAll        Opus or Sonnet, ~20 min, SERIAL FIRST (drives UEFN: one BuildAll)
      │
      ├── B1  Verse runtime                   Opus, the big one, no UEFN
      ├── B2  arena builder tool + editor build Opus, drives UEFN (editor only, no play session)
      └── B3  assets: voice lines, textures, cue rows   Sonnet, no UEFN
      │
B4  integration + headless playtest           Opus, SERIAL LAST (drives UEFN: sync, BuildAll, import, sessions)
```

- B0 must land first: `tools/build_bossmode.py` tags actors with `/<module>/_Verse.fnm_bm_*` references, which only
  exist once `fnm_tags.verse` has compiled in the project.
- B1, B2, B3 run in parallel. They are partitioned **by file** (below). Only B2 touches UEFN, and only the editor
  (placing actors, importing materials, viewport captures): no play session, no BuildAll. B1 and B3 never call the MCP.
- B4 runs when all three have reported. It is the only agent that starts play sessions and imports wavs (GUI).
- One agent drives UEFN at a time. UEFN's MCP hung during planning (a modal dialog, most likely): the first agent to
  touch it (B0) screenshots the editor and dismisses any dialog before calling `BuildAll`.

## File ownership (the concurrency contract)

| Agent | Owns (may create / edit) | Must not touch |
|---|---|---|
| B0 | `console/verse/fnm_tags.verse`, `console/verse/fnm_audio.verse` (enum + the three lists only), `tests/test_audio_cues.py` (MEMBERS only) | everything else |
| B1 | `console/verse/fnm_bossmode.verse` (new), `console/verse/fnm_director.verse`, `console/verse/fnm_ui.verse`, `console/verse/fnm_audio.verse` (helper functions only, below the lists), `tests/test_bossmode.py` (new) | `fnm_tags.verse` (B0 done), `tools/**`, `tests/test_hud_layout.py`, `tests/test_audio_cues.py`, `tests/test_arena_layout.py`, `maps/**`, docs |
| B2 | `tools/build_bossmode.py` (new), `tools/build_cannon.py` (additive params only), `tools/import_art.py` (`WALL_COLOURS` keys only), `maps/starter/LAYOUT.md` (one new section), `tests/test_bossmode_layout.py` (new) | `console/**`, `tests/test_arena_layout.py` (must stay green), other tools |
| B3 | `tools/make_announcer.py`, `tools/make_boss_art.py` (new), `tools/art/fnm_banner.png`, `tools/art/fnm_nuke.png`, `tools/audio/announcer/**` (rendered wavs, manifest, QA), `tools/audio/README.md`, `tools/build_audio.py`, `console/AUDIO.md`, `tests/test_hud_layout.py` (PNG size / determinism rows only) | `console/verse/**`, `tools/build_*.py` other than build_audio, `tools/import_art.py` |
| B4 | `BOSS_MODE.md` §14 and `maps/starter/LAYOUT.md` "Still to do" notes; flips and restores debug defaults in `fnm_director.verse` with `tools/patch.py` (ship values at the end) | any other source |

Cross-file facts that two agents must agree on are fixed in `BOSS_MODE.md`: tag names (§3, §8), cue ids and order (§10),
texture names and sizes (§9), level table (§4), log line shapes (§12). A builder who needs to change one of them stops and
reports instead.

Tests that go red while a sibling's half has not landed (say so in the report, do not "fix" the test):
- `tests/test_hud_layout.py::test_every_texture_has_a_png_and_every_png_is_used` is red until B1 (references
  `FNM_Art.T_fnm_banner` / `T_fnm_nuke`) and B3 (the PNGs) both land. Precondition: `ls tools/art/fnm_banner.png`.
- `tests/test_audio_cues.py::test_builder_table_matches_and_is_allowed` is red until B3 adds the 19 CUES rows.
  Precondition: `grep -c bm_boss_l1 tools/build_audio.py`.

## Repo facts every brief shares

- Repo `D:\PyCharm Projects\fortnitemath`, Windows 11, Git Bash available; branch master; tests
  `.venv/Scripts/python -m pytest -q` (8699 passed at planning time, 17 s).
- Verse files are `eol=lf`. Edit them with the Edit tool or `tools/patch.py` (exact-string, needle must match once);
  never `write_text`. `tests/test_hud_layout.py::test_verse_files_are_lf` catches a CRLF.
- Bash heredocs with non-ASCII die on this box: write files with the Write tool; keep shell bodies ASCII.
- `.venv/Scripts/python -m fnm sync starter` copies `console/verse/*.verse` + the slot into the UEFN project
  (`C:/Users/kicki/Documents/Fortnite Projects/FortniteMath/Content`). Compile:
  `.venv/Scripts/python tools/uefn_mcp.py ValkyrieToolset.VerseToolset BuildAll '{}'` → `[]` on success (also on a no-op).
  Errors: `.venv/Scripts/python tools/uefn_mcp.py EditorToolset.LogsToolset GetLogEntries '{"category":"","pattern":"error"}'`.
- A modal dialog in UEFN hangs every MCP call. If a call hangs > 60 s: screenshot the left monitor
  (`~/.claude/skills/uefn-mcp/scripts/gui_act.ps1 -steps "w:0" -name uefn`), read the PNG, dismiss with
  `gui_windows.ps1` + `WM_CLOSE` or a click, retry.
- Checkpoint every deliverable to disk the moment it exists; what is on disk is what survives a session limit.
- Report format (every brief): files created/edited; tests before/after; the verification commands you ran with their
  actual output; what you saw in the PNGs (pixels, not code); things in the docs or the brief that turned out untrue;
  **anything you decided differently from this brief and why**; **your shakiest assumption, stated plainly**.
