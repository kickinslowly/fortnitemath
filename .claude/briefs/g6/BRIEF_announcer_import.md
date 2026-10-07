# Brief E — Announcer pack into UEFN (G6 item 1c)

You are putting the announcer voice lines (`tools/audio/announcer/<voice>/*.wav`, 31 files) into the open UEFN
project and swapping them onto the matching sound-cue devices. Read first, in order: `CLAUDE.md`,
`~/.claude/skills/uefn-mcp/SKILL.md` (whole; especially "Windows GUI automation" and the Verse-tags / device-options
notes), `console/AUDIO.md`, `tools/build_audio.py`, `tools/audio/README.md`, `tools/audio/announcer/manifest.json`,
`tools/import_art.py` (how the project's own assets are referenced: `/<mount>/<Folder>/<Asset>.<Asset>`, mount from
`VerseToolset.ListFiles("")`), `tools/playtest.py`, `tools/audio_meter.py`, `tools/hear.py`.

## Repo facts (checked 2026-10-07)
- `D:\PyCharm Projects\fortnitemath`, Windows 11, Git Bash, branch `master`, tree clean at the commit named in your
  prompt. Python `.venv/Scripts/python`; tests `.venv/Scripts/python -m pytest -q` (read the count first; keep green).
- UEFN 42.30 is open with the project. MCP via `tools/uefn_mcp.py` (`MSYS_NO_PATHCONV=1` for `/` args). Set paths
  explicitly (`%TEMP%` = `C:\Users\kicki\AppData\Local\Temp`; the TEMP variable was empty in one Git Bash call today).
- **No headless import exists** (tested today): a wav dropped into `Content/` is never picked up, `AssetTools` has no
  import, the scripting toolset only exposes `execute_tool`. The route is the UEFN **Import** button in the Content
  Browser, driven with `~/.claude/skills/uefn-mcp/scripts/gui_act.ps1` (`c:x,y` click, `d:` double-click, `k:` SendKeys,
  `w:` wait; saves a full-screen PNG to `%TEMP%\<name>.png`) and `gui_windows.ps1` (which process owns a window).
  Coordinates are physical pixels; screenshots may come back scaled: read the skill's note and measure once.
- The Fortnite client window may be in front of UEFN. Bring UEFN forward by clicking ITS taskbar icon (the skill:
  `SetForegroundWindow` is blocked; clicking the taskbar icon of a window that is already in front minimizes it, so
  check `gui_windows.ps1` first). Take a screenshot and READ it before every click; never click blind. A modal dialog
  left open in UEFN hangs every MCP call: close what you open. `PostMessage(hwnd, WM_CLOSE)` closes a stray dialog
  without focus (AUDIO.md).
- The voice is `am_michael` unless your prompt names another.

## Deliverables
1. **Imported assets**: every wav of the chosen voice as a SoundWave under `/<mount>/FNM_Audio/<voice>/<cue_id>`
   (create the folder with `AssetTools.create_folder` or in the dialog; `EditorAppToolset.SetContentBrowserPath` points
   the browser at it). Windows file dialogs take a multi-select in the filename box as a quoted list
   (`"a.wav" "b.wav" ...`): one Import for all 31. If UEFN shows an import-options dialog, read it and accept the
   defaults. Prove it with `AssetTools.find_assets` (class `/Script/Engine.SoundWave`, folder `/<mount>/FNM_Audio`):
   31 assets, names = the cue ids. Save them (`save_assets`).
2. **`tools/build_audio.py --announcer <voice>`**: an `ANNOUNCER_CUES` list at the top (fixed set:
   `go, streak2, streak3, streak4, streak5, streak6, streak7, perfect, new_best, new_record, medal_gold, medal_silver,
   medal_bronze, penalty_freeze, penalty_spike, penalty_mud, penalty_dizzy, penalty_blackout, penalty_yeet, no_skip,
   guards_up, welcome, choose`; the countdown ticks, correct/retry chimes, wrong buzzer, door, boost, finish and music
   stay stock). With the flag, those devices' `audio` property is set to the imported SoundWave path instead of the
   stock cue (same one-write-per-call + read-back + save discipline; `CUES` keeps the stock path as the fallback and
   `--list` prints which source each device carries). Without the flag nothing changes. If an imported asset is missing
   the device keeps the stock sound and the run says so.
3. **Docs**: `console/AUDIO.md` gets an "Announcer" section (the import procedure with the exact clicks that worked,
   the asset path shape, the `--announcer` flag, which cues carry the voice); `tools/audio/README.md` gets the
   import verdict (what UEFN made of 48 kHz mono 16-bit: sample rate kept? compression?). One line in `CLAUDE.md`'s
   `tools/build_audio.py` entry for the flag.

## Verification
- `find_assets` shows the 31 SoundWaves; `get_asset_class` on one says SoundWave; `--list` shows the announcer paths on
  exactly the `ANNOUNCER_CUES` devices and stock elsewhere.
- Island validation: a play session must START with the swapped sounds (a failed start leaves "Unable to Play" and the
  editor log names the illegal reference). Flip `DebugAutoPick 0` + `DebugAutoRightAnswers true` with `tools/patch.py`,
  sync, BuildAll, then in the background `tools/audio_meter.py 230 <TEMP>/meter.csv unmute` and
  `tools/hear.py --seconds 225 --out <TEMP>/hear3.wav`, then `tools/playtest.py --until "finished run 1,stuck at stage"
  --timeout 200 > <TEMP>/run3.txt`; then `tools/hear.py --analyze --out <TEMP>/hear3.wav --log <TEMP>/run3.txt`.
  Expect `audio: 37 of 37 cues wired`, the streak lines with onsets, a session peak in the meter. Report the
  alignment count against the earlier 44 of 59. Then RESTORE the hooks to ship values, sync, BuildAll, and re-mute the
  client session (`SimpleAudioVolume.SetMute(1)` via pycaw, as `tools/audio_meter.py` shows) — Aaron keeps it muted.
- Look at one `pt_*.png`: HUD unchanged.
- Leave the UEFN window as you found it (no dialogs open, content browser path harmless).

## Non-goals / do NOT
- Do NOT commit. Do NOT edit any `.verse` file, any other `tools/build_*.py`, `GOALS.md`, `cartridges/**`,
  `emulator/**`, `fnm/**`. Do NOT regenerate the wavs. Do NOT click anything in UEFN beyond the import flow and
  bringing the window forward; do NOT change Editor Preferences or Project Settings.
- Do NOT play audio through the speakers except the verification run at the meter's 0.25 session volume.
- Checkpoint to disk as you go; if the GUI route fails after three careful attempts, stop, leave UEFN clean, and
  report exactly what each attempt showed (screenshots named).

## Report
What the import flow was (clicks and keys that worked, with screenshot names); the 31 asset paths (or the shortfall);
UEFN's import verdict on the wav format; `--list` excerpt; the session-start result; the alignment count; pytest
before/after. Then **"Anything I decided differently from this brief and why"** and **"Shakiest assumption, stated
plainly"**, and anything in the docs that turned out untrue.
