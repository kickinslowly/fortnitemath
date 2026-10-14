# G9 "Now" build team: shared contract (2026-10-13)

Every agent on this build reads this file first, then its own brief in this folder. The parent (Opus 5.5, the
manager) wrote both. The spec for everything is `reviews/race-2026-10-13/REVIEW.md` §4 and §10 "Now", with detail in
`reviews/race-2026-10-13/sources/ux_critique.md` and `sources/race_facts.md` (a code-level inventory of the race).
Read the project `CLAUDE.md` and the global skill `~/.claude/skills/uefn-mcp/SKILL.md` before any UEFN call.

## Roster and file ownership (partition by file; nobody edits a file they do not own)

| Agent | Model | Brief | Owns (may edit) |
|---|---|---|---|
| **D** director builder | Opus | `D_director.md` | `console/verse/*.verse` EXCEPT `fnm_ui.verse`; `console/PENALTIES.md`; `console/AUDIO.md`; `tools/playtest.py`, `tools/burst.py` |
| **H** HUD builder | Sonnet | `H_hud.md` | `console/verse/fnm_ui.verse`; `tools/make_hud_art.py`; `tools/art/` (HUD PNGs only); `tests/test_hud_layout.py`; the `textures()` function in `tools/import_art.py` |
| **S** scene builder | Sonnet | `S_scene.md` | `tools/build_course.py`, `tools/build_guards.py`, `tools/build_decor.py`, `tools/build_island.py`, new `tools/build_door_marks.py`, `WALL_COLOURS` + `materials()` in `tools/import_art.py`, `maps/starter/LAYOUT.md`, `tests/test_arena_layout.py` |
| **C** content lead | Opus (+ Sonnet builders) | `C_content.md` | `cartridges/LIBRARY.md`, new `cartridges/<grade-7 id>/`, new `tests/test_<grade-7 id>.py`, `.claude/skills/cartridge-library/BRIEF.md` |
| parent | Opus 5.5 | - | `GOALS.md`, `CLAUDE.md`, `PROTOCOL.md`, `briefs/`, `reviews/`, `maps/starter/generated/`, git |

- **Nobody commits.** Nobody edits `GOALS.md`, `CLAUDE.md`, `PROTOCOL.md`, or another agent's files. If you find a bug in a
  file you do not own, write it down for your report (file, line, what, why) and carry on. Your report is how it gets fixed.
- `tools/import_art.py` has two owners by region: H may edit only `textures()` (and the PNG list it reads), S only
  `WALL_COLOURS` and `materials()`. Re-read the file right before each edit; the other may have changed it.
- **Nobody runs `fnm insert` or `fnm emit`.** The generated slot is the parent's; C's new cartridges stay out of the map
  until the parent inserts them.

## The UEFN write lock (one editor, many agents)

There is ONE UEFN editor (MCP `http://127.0.0.1:8000/mcp`, client `tools/uefn_mcp.py`). A Verse `BuildAll`, a scene
or device change, or an asset import made while a play session is live pushes and re-cooks for 20 to 60 s. A session
started inside that window starts from a stale snapshot. So every UEFN **mutation** happens under one lock:

```
LOCK="C:/Users/kicki/AppData/Local/Temp/claude/D--PyCharm-Projects-fortnitemath/26b46b63-033f-415b-aac7-f54eb20d33c6/scratchpad/team/uefn.lock"
LOG="C:/Users/kicki/AppData/Local/Temp/claude/D--PyCharm-Projects-fortnitemath/26b46b63-033f-415b-aac7-f54eb20d33c6/scratchpad/team/log.md"
# acquire (atomic: mkdir fails if someone holds it)
mkdir "$LOCK" 2>/dev/null && echo "D BuildAll $(date +%T)" > "$LOCK/owner" && echo "$(date +%T) D acquired: BuildAll" >> "$LOG"
# release
rm -rf "$LOCK" && echo "$(date +%T) D released" >> "$LOG"
```

- **Needs the lock:** `BuildAll`; any `tools/build_*.py` run; `tools/import_art.py`; any `set_properties` /
  `add_to_scene*` / `remove_from_scene` / `PlaceDevice` / `save_assets`; any `StartSession` / `StopSession` /
  `tools/playtest.py` run (a play session holds the lock from launch until you have your frames and logs).
- **Does not need it:** reads (`get_properties`, `find_actors`, `get_actor_bounds`, `GetLogEntries`, `ReadFile`,
  `CaptureViewport`, `GetSessionStatus`), editing files in the repo, pytest.
- **Hold it for one batch** (one compile, one build script, one session test), at most ~20 minutes, then release.
- **If it is held:** `cat "$LOCK/owner"`, then do other work. When you have nothing else to do, wait with a BACKGROUND
  command (`run_in_background: true`), never a foreground sleep:
  `until mkdir "$LOCK" 2>/dev/null; do sleep 2; done; echo "H import $(date +%T)" > "$LOCK/owner"; echo ACQUIRED`
  You are notified when it exits; you then hold the lock. (Poll every 2 s: a 15 s waiter lost the race three times to
  agents re-acquiring at once. TaskStop leaves the bash loop running: kill orphaned waiters by PID, or they take the lock later.)
- If an owner file is older than 40 minutes, note it in `$LOG` and in your report. Do not break the lock.

## Compiling without breaking each other

`python -m fnm sync starter` copies EVERY `console/verse/*.verse` (and the slot) into the UEFN project's Verse root,
`C:/Users/kicki/Documents/Fortnite Projects/FortniteMath/Content/`. With two Verse builders, that would push the other
builder's half-done file. So **D and H copy only their own files** into the Verse root, under the lock, and then `BuildAll`:

```
cp "console/verse/fnm_ui.verse" "C:/Users/kicki/Documents/Fortnite Projects/FortniteMath/Content/fnm_ui.verse"   # H
```

D copies the files it changed the same way. `cp` keeps the bytes (LF). Then
`.venv/Scripts/python tools/uefn_mcp.py ValkyrieToolset.VerseToolset BuildAll '{}'`: `[]` means clean.
- Copy a file into the Verse root only when you believe it compiles. The root always holds each owner's last good copy.
- **Seam rule:** H adds new `fnm_hud` methods and never changes or removes an existing method's signature (D's code calls
  them). New parameters on an existing method only as named optionals with a default (`?Name:type = default`).
- D calls a new H method only after it exists in the VERSE ROOT copy:
  `grep -c "ShowRecap" "C:/Users/kicki/Documents/Fortnite Projects/FortniteMath/Content/fnm_ui.verse"` is 1 or more.
  If not yet, do other work and re-check. Never wait in the foreground.
- If `BuildAll` fails in a file you do not own: release the lock, append the error to `$LOG`, do other work, retry after
  that owner's next release. Mention it in your report if it lasted more than 20 minutes.
- At the very end the parent runs a full `fnm sync starter` + `BuildAll` from the repo.

## The machine

- **Aaron may be at this PC in another app.** Nothing you run may take the foreground: no `--keys`, no
  `tools/click_hud.py`, no `gui_act.ps1`, no `holdkey.ps1`, no `SetCursorPos`. Screenshots of the game only through
  PrintWindow (`tools/wincap.ps1`, `tools/playtest.py`, `tools/burst.py`). If a test truly needs keys, say so in your
  report; the parent schedules it.
- 32 GB RAM. UEFN takes about 13 GB and a play client about 3.4 GB. Do not start a second editor or client.
- Shell: Git Bash. The repo path has a space: quote it. Python: `.venv/Scripts/python`. Paths that start with `/` passed
  to the UEFN MCP from Git Bash need `MSYS_NO_PATHCONV=1`. Bash heredocs with non-ASCII characters break: write files
  with the Write tool. Verse files are `eol=lf`: edit them with the Edit tool or `tools/patch.py`, never Python
  `write_text`.
- Tests: `.venv/Scripts/python -m pytest -q` (baseline 2026-10-13: **8766 passed in 23 s**, clean tree at 583effb).
- Scratch space for frames, logs and throwaway scripts:
  `C:/Users/kicki/AppData/Local/Temp/claude/D--PyCharm-Projects-fortnitemath/26b46b63-033f-415b-aac7-f54eb20d33c6/scratchpad/team/<your letter>/`.

## Working rules

- **Checkpoint to disk the moment each deliverable exists.** What is on disk survives a session limit; what is in your head does not.
- **"Seen" means seen.** For anything visual, capture a frame and READ the PNG. Report what the pixels show, not what the
  code implies. Name anything on the screen that looks wrong, whether or not your brief mentions it.
- **Include one disproof** per deliverable: a check that would fail if the work were wrong (a sabotage you then restore
  by re-applying the original text, never `git checkout`; a read-back; a negative case).
- Finish or kill every background job you started before you report (kill by PID). Release the lock.

## Report format (your final message)

1. Deliverables: done / partial / not started, each with the evidence (log lines, read-backs, frame paths).
2. Files created or edited.
3. Tests: before and after counts; the disproofs you ran and which check went red.
4. Frames you read and what they showed (paths under your scratch folder).
5. **Anything you decided differently from your brief, and why.**
6. **Facts in the briefs or docs that turned out untrue.**
7. **Your shakiest assumption, stated plainly.**
8. Bugs you found in files you do not own.
9. Lock: confirm released; background jobs: confirm none running.

## Wave 4-5 (2026-10-13 evening): roster, and the PC

| Agent | Model | Brief | Owns |
|---|---|---|---|
| **V** Volt reactions | Sonnet | `V_reactions.md` | all `console/verse/*.verse`, `tests/test_hud_layout.py`, `tests/test_volt_reactions.py`, `tools/make_medal_art.py`, `tools/art/fnm_volt_*.png` |
| **A** audio | Sonnet | `A_audio.md` | `tools/build_audio.py`, `console/AUDIO.md`, `tools/make_mint_audio.py`, `tests/test_mint_audio.py`, `art/audio/mint/`, `tools/audio/mint/` |
| **P** volcano + trophy | Sonnet | `P_landmarks.md` | `tools/import_landmarks.py`, `tools/build_landmarks.py`, `tests/test_landmarks.py`, `art/volcano/`, `art/trophy/` |
| **T1** surfaces + arches | Opus | `T1_surfaces_arches.md` | `tools/import_art.py`, `tools/build_course.py` (paint), `tools/import_titanpeak.py`, `tools/build_arches.py`, `maps/starter/LAYOUT.md`, `tests/test_arena_layout.py`, `tests/test_titanpeak_surfaces.py`, `art/titanpeak/` |
| **T2** dressing | Sonnet | `T2_dressing.md` | `tools/build_titanpeak.py`, `tests/test_titanpeak.py` (+ the trophy spot in `build_landmarks.py` after P is done) |

**The PC (Aaron, 2026-10-13 ~18:30 PT: "u have control of pc as long as u need"):** foreground actions (`--keys`,
`click_hud.py`, `gui_act.ps1`, the GUI wav import) are allowed, but ONLY while you hold the UEFN lock, so two agents never
drive the mouse at once. Minimize the Fortnite client before clicking UEFN (AUDIO.md import step 0). Release the
foreground and the lock together. The "Aaron may be at this PC" rule above is suspended until the manager says otherwise.
