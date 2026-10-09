# B4 — Integration and headless playtest (Opus, serial, after B1 + B2 + B3)

You wire the three halves together in UEFN and prove the mode plays. Read first: `briefs/bossmode/README.md`; `BOSS_MODE.md`
§12 (acceptance: commands, expected log lines, what must be SEEN) and §13; the three builder reports the parent hands you
(their `FNM:` log line lists and deviations); `CLAUDE.md` (project: "After any Verse edit", test hooks, `tools/playtest.py`
flags, `tools/click_hud.py`); `console/AUDIO.md` "Announcer" (the GUI wav import procedure, step by step, with the
minimize-the-client rule) and "Rewire a cue"; `tools/playtest.py` docstring; `tools/import_art.py` docstring; the global
skill `~/.claude/skills/uefn-mcp/SKILL.md` ("Play sessions", "Windows GUI automation", the push/cook wait).

You own: nothing in source except flipping debug defaults in `console/verse/fnm_director.verse` with `tools/patch.py` and
restoring the ship values at the end (`DebugAutoBoss : logic = false`, `DebugAutoRightAnswers : logic = false`,
`DebugAutoWrongAnswers : int = 0`, `DebugBossLevel : int = 0`, `DebugAutoPick : int = -1`); `BOSS_MODE.md` §14 ("Shipped —
where it differs") and the "Still to do" list in `maps/starter/LAYOUT.md`. A one-line Verse fix for a compile error is yours
(say exactly what); anything larger goes back to the parent as a finding. Do not commit.

## Steps (in order; every MCP call can hang on a modal dialog — README)

1. `git status` (uncommitted tree from three builders), `.venv/Scripts/python -m pytest -q` → all green (B1 + B3 both landed
   clears the two sibling-gated tests). Fix nothing; report any red.
2. Textures: `python tools/import_art.py` (full run: it imports every `tools/art/fnm_*.png`, the door faces and the
   materials; idempotent). Confirm `T_fnm_banner` and `T_fnm_nuke` in the final `find_assets` print.
3. Sync + compile: `.venv/Scripts/python -m fnm sync starter`; `BuildAll` → `[]`. On an error read
   `LogsToolset.GetLogEntries pattern "error"`; a one-liner you can fix, fix (Edit tool / patch.py, eol=lf) and say so; else stop
   and report the error verbatim with file:line.
4. Wav import (GUI, AUDIO.md procedure; worked 2026-10-07 and 10-08): the 8 new am_michael announcer lines (`bm_start`, `bm_level2..5`, `bm_mega_nuke`, `bm_level_clear`, `bm_victory`) and the 8 am_onyx boss lines (`bm_boss_*`)
   into `/<mount>/FNM_Audio/am_michael` and `/FNM_Audio/am_onyx` (copy only the NEW wavs to `%TEMP%\fnm_vo_*` so the dialog
   selects just them). Minimize the Fortnite client first if a session is running. Then
   `python tools/build_audio.py --announcer am_michael --boss-voice am_onyx` and `--list` (0 mismatches; 65 of 65 devices).
   If the GUI import fails twice, skip it: the mode plays with stock stand-ins and `(not wired)` lines; report it.
5. Flip hooks: `tools/patch.py console/verse/fnm_director.verse "    DebugAutoBoss : logic = false" "    DebugAutoBoss : logic = true"`
   and the same for `DebugAutoRightAnswers`; sync; BuildAll; wait for the push (`playtest.wait_for_push` runs inside
   `playtest.relaunch`).
6. **Acceptance 1** (BOSS_MODE.md §12.1): the `--until ... --frames ...` command verbatim. Save the printed log to
   `%TEMP%\bm_run1.txt`. Read every `pt_frame*.png` and `pt_now.png`. Report what the pixels show, not what the log implies:
   the tag, the slate caption, the banner with its sub line, the mushroom icon and the beams, the VICTORY! board. If the run
   is `stuck`, the log says at which level and after which pad: capture the frame, read it, report (common causes: the boss
   spawner not spawning — look for `boss requested` without `boss spawned`; a pad trigger not firing — look for the hit line).
7. **Acceptance 2** (race untouched): `DebugAutoBoss` back to false, `DebugAutoPick` 0 (keep `DebugAutoRightAnswers` true);
   sync, BuildAll; `tools/playtest.py --until "finished run 2,stuck at stage" --timeout 400`; `finished run 2` and five
   `cannons fired` lines per run; `RACE` strip lines unchanged in shape. Restore `DebugAutoPick -1`.
8. **Acceptance 4** (wrong pad): `DebugAutoBoss` true, `DebugAutoRightAnswers` false, `DebugAutoWrongAnswers 2`; sync,
   BuildAll; `tools/playtest.py --until "debug auto-wrong 2" --timeout 120 --frames "debug auto-wrong 1:1.0"`; expect the
   penalty, the wave line and `cue bm_boss_wrong`; the frame shows the red X with the penalty name over the arena.
9. **Acceptance 3 and 5 need the foreground** (click_hud, keys): ask the parent to confirm Aaron is away from the keyboard
   before running them (`GetLastInputInfo` idle > 10 min is the proxy the skill uses). Picker: `python tools/click_hud.py launch`
   (ship hooks) → read `pick0.png` → click BOSS BATTLE → `FNM: boss mode start`. Perch: `DebugAutoBoss` true, `DebugBossLevel 1`,
   `tools/playtest.py --after "boss level 1 summoned" --keys "<a path from the entry to P1>"`; try `D:1.4,W+SPACE:3` first
   (P1 is front-right: from the entry walk right then run-jump the stones); read the frames. If the climb fails three ways, record
   it as the §3 jump assumption failing with the frame that shows where the player stopped; do not rebuild the arena yourself.
10. Restore every hook to its ship value (list in "You own"), sync, BuildAll → `[]`, `git diff console/verse/fnm_director.verse
    | grep Debug` shows only B1's additions. Write BOSS_MODE.md §14 (what differs from the plan and why, with the probe answers
    from B2's LAYOUT.md section) and the LAYOUT.md "Still to do" notes (what is still unverified: by ear, in a real jump, with
    two players).

## Non-goals
No design changes. No arena rebuild. No new cues or lines. No commit. No private version (Aaron's GUI step).

## Verification is the whole brief; the disproof
Run acceptance 1 once with `DebugAutoRightAnswers` true but `DebugAutoBoss` false and `DebugAutoPick` 0 (step 7 is that):
the boss-mode lines must NOT appear (`grep -c "boss mode" bm_run2.txt` → 0 besides the OnBegin "arena found" line). A mode that
leaks into the race fails here.

## Report
README format, plus: every acceptance item with PASS / FAIL / NOT RUN (why), the frame paths and what each shows in words,
the exact `FNM:` lines around any failure, cook/push timings observed, which wavs were imported and `--list`'s wired count,
things in the docs or the briefs that turned out untrue, anything you decided differently and why, your shakiest assumption
stated plainly.
