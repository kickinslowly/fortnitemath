# Brief Q: QA session runner (after D, H, S finished)

Read `briefs/g9/TEAM.md` first (lock, machine rules, report format). You are **Q**. The build agents are done; you are
the only agent using UEFN now, but still take the lock (the parent may compile between your tests). You change only:
the debug hook defaults in `console/verse/fnm_director.verse` (with `tools/patch.py`, one-line flips, always restored),
the Island Settings `timeOfDayOverride` (with `tools/build_island.py --time`), and files under your scratch folder
`.../scratchpad/team/Q/`. No other edits, no commits, no `--keys`, nothing that takes the foreground.

## Setup (once)
- `.venv/Scripts/python -m fnm sync starter` (the full sync: the slot now holds 19 cartridges, 1.7 MB, never compiled
  in UEFN before), then `BuildAll`. Record the compile time and the result. If it fails, stop and report the error.
- Every session: flip the hooks you need, copy `fnm_director.verse` into the Verse root
  (`C:/Users/kicki/Documents/Fortnite Projects/FortniteMath/Content/`), `BuildAll`, wait for the push (the gotcha in
  `CLAUDE.md`: a relaunch within 20-60 s of a build starts stale; `tools/playtest.py` has `wait_for_push`), then
  `tools/playtest.py` with `--until` / `--frames`, plus `tools/burst.py` for timed bursts.
- Picker order (index for `DebugAutoPick`) is `maps/starter/generated/SLOT.txt` order, from 0.

## Tests, in order
1. **Lighting comparison** (G9 Now 3). For each of `Hour10`, `Hour14`, `Hour17`, `Hour19`: set it, then one
   `DebugAutoPick 7` (Order of Operations) + `DebugAutoRightAnswers` session. Frames: station 1 door wall from the start
   (the doors, the lintel letters, the slate), a mid-course hallway with a connector (station 4 or 5), station 6 (ice),
   the arena during the cannon volley, the finish/podium. Name them `hNN_<what>.png`. Make one contact sheet per subject
   across the four hours (`sheet_<what>.png`, 2x2, labelled) so the parent can compare at a glance. Note, per hour:
   readability of the four door colours and letters, floor glare, how the titan reads, sky. Leave the island on the
   hour you think is best and say which and why; the parent decides.
2. **A grade-7 cartridge in play** (proves the 19-cartridge slot cooks and runs; G3): `DebugAutoPick` = the index of
   `circles` + `DebugAutoRightAnswers`, to the finish. Frames of at least three questions whose prompt or doors carry
   `π` (does the HUD font draw it, or a `?` diamond?), and of `r^2`/`²` if any appears. Report the log's cartridge count
   line.
3. **A grade-6 skill other than Order of Operations** (G3 "one run on a new grade-6 skill in play"): `DebugAutoPick 0`
   (area-volume) + `DebugAutoRightAnswers` to the finish board. Frames of two questions and the finish.
4. **Ice poll** (G4 open item): `DebugAutoPick 0` + `DebugStartStage 6`, no auto-run, let it sit ~30 s. Pass: the log
   has one "on ice" and no "off ice" while the player stands in the ice hallway. Report the lines.
5. **Wrong doors at the new retry spot** (D's G9 Now 7, independent look): `DebugAutoPick 7` +
   `DebugAutoWrongAnswers` through at least four wrong doors at stations 1-3. Bursts from the verdict to the retry spot.
   Per wrong door: the penalty, seconds from verdict to "back at the retry spot" (log), what the frames show (player
   facing the doors? letters reshuffled? "+3 s" visible?). Also one frame of the recap card after a right door
   (any auto-right session above: 0.5 s and 3.5 s after a right door).

## Finally
- Restore every hook to its ship value (the list at the top of `fnm_director.verse`); `git diff
  console/verse/fnm_director.verse` must show no hook changes from what D left; copy, `BuildAll` clean; stop the session.
- Report in TEAM.md's format; list every frame path you want the parent to look at, best first (no more than 12).
