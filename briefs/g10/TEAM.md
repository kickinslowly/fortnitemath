# G10 build team: shared contract (2026-10-14)

Every agent on this build reads this file first, then its own brief in this folder. The parent (Opus 5.5, the manager)
wrote both. Aaron is away ("take care of anything you can do without me"); the parent is the only one who talks to him.
Read the project `CLAUDE.md` first. Before ANY UEFN call, read the global skill `~/.claude/skills/uefn-mcp/SKILL.md`.
Background for the race features: `reviews/race-2026-10-13/REVIEW.md` and `reviews/race-2026-10-13/sources/`
(`gamification.md`, `ux_critique.md`, `race_facts.md` = a code-level inventory of the race, line numbers may have drifted).

## Roster and file ownership (partition by file; nobody edits a file they do not own)

| Agent | Model | Brief | Owns (may edit) |
|---|---|---|---|
| **C** content lead | Opus (+ Sonnet builders it fires) | `C_grade8.md` | `cartridges/LIBRARY.md`, new `cartridges/<grade-8 id>/`, new `tests/test_<grade-8 id>.py`, `.claude/skills/cartridge-library/BRIEF.md`, `PROTOCOL.md` §4b only (new grade-8 bounds) |
| **W** walls | Opus | `W_walls.md` | `tools/import_titanpeak.py`, new `tools/build_wall_trim.py` (or another new tool it names in its report), `art/titanpeak/`, `tests/test_titanpeak_surfaces.py`, new `tests/test_wall_*.py`, the "Titan Peak" sections of `maps/starter/LAYOUT.md` |
| **D** director | Opus | `D_director.md` | `console/verse/*.verse` EXCEPT `fnm_ui.verse`; `console/PENALTIES.md`; `console/AUDIO.md`; `tools/build_audio.py`; `tools/playtest.py`, `tools/burst.py`; new `tests/test_g10_*.py` for its features |
| **H** HUD | Sonnet | `H_hud.md` | `console/verse/fnm_ui.verse`; `tools/make_hud_art.py`; `tools/art/` (HUD PNGs only); `tests/test_hud_layout.py`; the `textures()` function in `tools/import_art.py` |
| **S** arena + analytics | Sonnet | `S_arena.md` | `tools/build_course.py`, `tools/build_race_boss.py`, `tools/build_fx.py`, new `tools/build_analytics.py`, `tests/test_arena_layout.py`, the "Boss arena" section of `maps/starter/LAYOUT.md`, `BOSS_MODE.md` §16 |
| **X** voice lines | Haiku | `X_voice.md` | `tools/audio/announcer/am_onyx/`, `tools/audio/announcer/bm_george/`, `tools/audio/announcer/manifest.json`, `tools/audio/announcer/QA.md` |
| parent | Opus 5.5 | - | `GOALS.md`, `CLAUDE.md`, `PROTOCOL.md` (except C's §4b), `briefs/`, `reviews/`, `maps/starter/generated/`, `maps/starter/map.json`, git, memory |

- **Nobody commits.** Nobody edits `GOALS.md`, `CLAUDE.md`, or another agent's files. A bug in a file you do not own: write
  it down for your report (file, line, what, why) and carry on. Your report is how it gets fixed.
- `maps/starter/LAYOUT.md` has two owners by section (W: Titan Peak; S: Boss arena). Re-read the file right before each edit.
- `tools/import_art.py` belongs only to H (`textures()`); nobody else edits it this wave. Running it is fine for anyone
  who needs an import it already supports, under the lock.
- **Nobody runs `fnm insert` or `fnm emit`.** The generated slot is the parent's; C's cartridges stay out of the map until
  the parent inserts them at the end.
- **Nobody runs a full `tools/build_course.py`** (it rebuilds the whole course and every tool listed under "rerun after a
  course rebuild" would have to follow). In-place modes only.

## The seams (contracts between agents; build to these exactly)

**D <-> H (Verse).** H adds these `fnm_hud` methods; D calls them. Names and parameter lists are fixed:

```verse
# Shield charge indicator next to the streak line. On = the player holds a shield.
SetShield(On:logic):void
# Brag grid on the finish board, under the medal line (shown by ShowResults' caller right after ShowResults; HideResults
# hides it too). Marks: one per station in order: 0 = first-try right, 1 = redeemed at the boss, 2 = missed, 3 = not
# reached. BossMark: 0 = boss down, 2 = not down. Flawless: draw a FLAWLESS badge. NextGoal: one line such as
# "GOLD needs 9/10 - you: 8/10" ("" = no line). Code: the island code text ("" = no code line; never a QR).
ShowBragGrid(Marks:[]int, BossMark:int, Flawless:logic, NextGoal:string, Code:string):void
# Compact slate: question + choices only, smaller and higher, so the world behind reads (the titan in the arena, the
# lintel letters at the retry spot). D turns it on at arena entry and for the retry hold, off when they end.
SetCompact(On:logic):void
```

H lands both as compiling stubs FIRST (copy to the Verse root, BuildAll clean), then fills them in. D calls a new method
only after it exists in the VERSE ROOT copy:
`grep -c "ShowBragGrid" "C:/Users/kicki/Documents/Fortnite Projects/FortniteMath/Content/fnm_ui.verse"` is 1 or more.
If not yet, do other work and re-check. Never wait in the foreground. H never changes or removes an existing method's
signature (D's code calls them); new parameters on an existing method only as named optionals with a default.

**D <-> S (tags).** S places one `analytics_device` per station (10) plus one at the finish and one at the boss kill,
with Verse tags `fnm_analytics` + the station tag that already exists for that station (`fnm_station_NN`), or
`fnm_analytics` + `fnm_finish` / `fnm_analytics` + `fnm_boss`. D declares `fnm_analytics` in `fnm_tags.verse` (if it is
missing, S's devices are simply not found: harmless) and calls `Submit(Agent)` on a station's device when that player
clears it, on the finish device at the finish, on the boss device at the kill. S's arena pads keep their tags
(`fnm_boss` + `fnm_door_a..d`); the director finds them by tag and needs no change for a new row layout. If S rescales
the titan and a director constant depends on its size (leash, hit radius, `FaceLetter`), S names it in the report; the
parent routes it to D.

**D's `build_audio.py` cues.** New sounds for D's features use stock sounds from `/Game/Sounds/Creative` (see
`console/AUDIO.md`; zero credits). No new Mint audio this wave.

## The UEFN write lock (one editor, many agents)

There is ONE UEFN editor (MCP `http://127.0.0.1:8000/mcp`, client `tools/uefn_mcp.py`). A Verse `BuildAll`, a scene or
device change, or an asset import made while a play session is live pushes and re-cooks for 20 to 60 s. A session started
inside that window starts from a stale snapshot. So every UEFN **mutation** happens under one lock:

```
LOCK="C:/Users/kicki/AppData/Local/Temp/claude/D--PyCharm-Projects-fortnitemath/64261e2b-78b4-449e-905d-de9081377a49/scratchpad/team/uefn.lock"
LOG="C:/Users/kicki/AppData/Local/Temp/claude/D--PyCharm-Projects-fortnitemath/64261e2b-78b4-449e-905d-de9081377a49/scratchpad/team/log.md"
# acquire (atomic: mkdir fails if someone holds it)
mkdir "$LOCK" 2>/dev/null && echo "D BuildAll $(date +%T)" > "$LOCK/owner" && echo "$(date +%T) D acquired: BuildAll" >> "$LOG"
# release
rm -rf "$LOCK" && echo "$(date +%T) D released" >> "$LOG"
```

- **Needs the lock:** `BuildAll`; any `tools/build_*.py` run that writes; `tools/import_*.py`; any `set_properties` /
  `add_to_scene*` / `remove_from_scene` / `PlaceDevice` / `save_assets` / material edits; any `StartSession` /
  `StopSession` / `tools/playtest.py` run (a play session holds the lock from launch until you have your frames and logs).
- **Does not need it:** reads (`get_properties`, `find_actors`, `get_actor_bounds`, `GetLogEntries`, `ReadFile`,
  `CaptureViewport` / `tools/capture.py`, `GetSessionStatus`), editing files in the repo, pytest. Exception: do not
  `CaptureViewport` while a play session is running (the editor viewport is not the game); check `GetSessionStatus` first.
- **Hold it for one batch** (one compile, one build script, one session test), at most ~20 minutes, then release.
- **If it is held:** `cat "$LOCK/owner"`, then do other work. When you have nothing else to do, wait with a BACKGROUND
  command (`run_in_background: true`), never a foreground sleep:
  `until mkdir "$LOCK" 2>/dev/null; do sleep 2; done; echo "H import $(date +%T)" > "$LOCK/owner"; echo ACQUIRED`
  You are notified when it exits; you then hold the lock. TaskStop leaves the bash loop running: kill orphaned waiters by
  PID, or they take the lock later.
- If an owner file is older than 40 minutes, note it in `$LOG` and in your report. Do not break the lock.

## Compiling without breaking each other

`python -m fnm sync starter` copies EVERY `console/verse/*.verse` (and the slot) into the UEFN project's Verse root,
`C:/Users/kicki/Documents/Fortnite Projects/FortniteMath/Content/`. With two Verse builders that would push the other
builder's half-done file, so **nobody runs `fnm sync` this wave**. D and H copy only their own files into the Verse
root, under the lock, then `BuildAll`:

```
cp "console/verse/fnm_ui.verse" "C:/Users/kicki/Documents/Fortnite Projects/FortniteMath/Content/fnm_ui.verse"   # H
```

D copies the files it changed the same way. `cp` keeps the bytes (LF). Then
`.venv/Scripts/python tools/uefn_mcp.py ValkyrieToolset.VerseToolset BuildAll '{}'`: `[]` means clean.
- Copy a file into the Verse root only when you believe it compiles. The root always holds each owner's last good copy.
- If `BuildAll` fails in a file you do not own: release the lock, append the error to `$LOG`, do other work, retry after
  that owner's next release. Mention it in your report if it lasted more than 20 minutes.
- Debug hooks on the director: flip them for a test, and put the SHIP values back in the repo file AND the Verse root
  before you report (ship values: CLAUDE.md "Test hooks"). The parent checks.
- At the very end the parent runs a full `fnm sync starter` + `BuildAll` from the repo.

## The machine

- **Aaron may be at this PC in another app.** Nothing you run may take the foreground: no `--keys`, no
  `tools/click_hud.py`, no `gui_act.ps1`, no `holdkey.ps1`, no `SetCursorPos`. Screenshots of the game only through
  PrintWindow (`tools/wincap.ps1`, `tools/playtest.py`, `tools/burst.py`). Drive runs with the director's debug hooks.
  If a test truly needs keys, say so in your report; the parent schedules it.
- 32 GB RAM. UEFN takes about 13 GB and a play client about 3.4 GB. Do not start a second editor or client. The harness
  reaps background shells when RAM runs out (uefn-mcp skill).
- Shell: Git Bash. The repo path has a space: quote it. Python: `.venv/Scripts/python`. Paths that start with `/` passed
  to the UEFN MCP from Git Bash need `MSYS_NO_PATHCONV=1`. Bash heredocs with non-ASCII characters break: write files
  with the Write tool. Verse files are `eol=lf`: edit them with the Edit tool or `tools/patch.py`, never Python
  `write_text`.
- Tests: `.venv/Scripts/python -m pytest -q` (baseline 2026-10-14: **17493 passed in 40 s**, clean tree at 682acc4).
  C's new cartridges make `test_emit.py::test_generated_slot_file_lints` and the carts.js test fail until the parent
  inserts them: expected, not yours to fix.
- Scratch space for frames, logs and throwaway scripts:
  `C:/Users/kicki/AppData/Local/Temp/claude/D--PyCharm-Projects-fortnitemath/64261e2b-78b4-449e-905d-de9081377a49/scratchpad/team/<your letter>/`.
- Credits (prepaid; Aaron 2026-10-13: spend what is already paid for without asking; never buy more): Mint ~5,723
  (expires 2026-10-21), Meshy 844 permanent + 1,000 monthly (expires 2026-11-14). Only W has a credit budget this wave.

## Working rules

- **Checkpoint to disk the moment each deliverable exists.** What is on disk survives a session limit; what is in your
  head does not. Keep a running `notes.md` in your scratch folder.
- **"Seen" means seen.** For anything visual, capture a frame and READ the PNG. Report what the pixels show, not what the
  code implies. Name anything on the screen that looks wrong, whether or not your brief mentions it.
- **Include one disproof** per deliverable: a check that would fail if the work were wrong (a sabotage you then restore
  by re-applying the original text, never `git checkout`; a read-back; a negative case). Say which check went red.
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
9. Lock: confirm released; background jobs: confirm none running; debug hooks: confirm ship values.
