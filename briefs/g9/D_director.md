# Brief D: director builder (G9 "Now" 4-9, the race runtime)

Read `briefs/g9/TEAM.md` first: file ownership, the UEFN write lock, the copy-only-your-files compile rule, the machine
rules and the report format all apply. You are **D**. You own every `console/verse/*.verse` file except `fnm_ui.verse`
(that is H's), plus `console/PENALTIES.md`, `console/AUDIO.md`, `tools/playtest.py`, `tools/burst.py`.
You are the main play-session user in this build.

## Context (checked unless marked belief)
- Spec: `reviews/race-2026-10-13/REVIEW.md` §4 (P1 table) and §10 "Now" items 4-9. Detail and line refs:
  `reviews/race-2026-10-13/sources/ux_critique.md`, recommendations table rows **#2 (tutorial), #5 (recap), #6 (feed),
  #7 (copy, with table 3.10), #8 (retry spot), #10 (podium)**, and its B8 section. Code inventory:
  `sources/race_facts.md` (B8b, 7b.x). Line numbers there are `D:<line>` in `fnm_director.verse` as of 583effb.
- The race runtime is `console/verse/fnm_director.verse` (2918 lines, one `fnm_director` class). Wrong door:
  `HandleDoor` -> `Punish` (line ~1670) -> `PullOut` / `SendTo` entry pad. Right door: `HandleDoor` -> `AdvancePlayer`.
  Feed: `Broadcast` (~2788) pushes to every HUD; `fnm_hud.PushFeed(Line)` pushes to one. Strip rows: `RaceRowsFor`
  (~2850) -> `Hud.SetRivals`. Finish: `FinishPlayer` (~1905), victory area `SetUpVictoryArea` (~1984), boss down `BossDown` (~2497).
- Test hooks and how to drive them: the project `CLAUDE.md` "Test hooks" paragraph. Flip a default with
  `tools/patch.py`. Run sessions with `tools/playtest.py` (`--until`, `--frames`, `--watch`) and `tools/burst.py`
  (PrintWindow bursts; the editor log lags ~10 s, so start a burst on an early line and match frames by file time).
  Never `--keys` (TEAM.md: no foreground).
- H is adding to `fnm_ui.verse` in parallel (tile colours, 40 px tile letters, a recap card method, picker copy,
  "RACE AGAIN" on the finish buttons, today's-record feed copy). See "Seam with H" below.
- S is changing the scene in parallel: door paint, lintel letters, arch lights, **station 1's guard spawner removed**
  (`tools/build_guards.py`), darker floors. Your code must tolerate station 1 having no guard spawner (check
  `FindGuards`, `CountGuardStations`, `WarnAboutDoorCounts`, `GuardLoop`; a missing spawner must log nothing scary and
  break nothing). S runs no play sessions.

## Deliverables, in this order (checkpoint each before starting the next)

1. **Retry spot and the five-second wrong door** (Now 7; ux_critique #8). After a wrong door's gag the player comes back
   to a **retry spot 3 m in front of their station's door wall, facing the doors** (+Y), not the 4.5 m landing. Compute
   it from the station's own door triggers (`ZoneCentre`, `TriggerHalf`) at runtime; hallways sit at different X and
   levels, so never assume x = 0 or z = 0. The retry spot must be clear of the vestibule triggers (standing on it must
   not answer a door) and of the barrier.
   - Holds about 2.5 s for every penalty (today Freeze is ~9.3 s, Yeet ~5.8 s; `race_facts` has the table). Keep the
     gags' look, cut the dead time. Yeet: the throw still plays, then the retry spot (not a 75 m skydive to the entry).
     Blackout and Dizzy: shortened to the same budget.
   - **+3 s on the race clock** per wrong door, shown once on the HUD (e.g. the verdict or delta line: "+3 s").
   - **Spike without the kill:** no `Damage(1000)`, no elimination, no loss of the player's guns; the spear ring still
     bursts, then a hold, then the retry spot.
   - **Letters reshuffle on every retry:** same question, new letter order (the anti-memorization shuffle in PROTOCOL
     §3's note already exists for a new showing; call it again on a retry and redraw the slate).
   - Update `console/PENALTIES.md` to the new costs.
   - Proof: a headless session with `DebugAutoWrongAnswers` (read how it picks doors first) logging, per wrong door, the
     penalty, the hold length, the +3 s, the retry spot coordinates, and the new letter order; frames showing the
     player at the retry spot facing the doors, and a Spike that leaves them standing. Time each wrong door from the
     verdict to "back at the retry spot" in the log: target 5 s or less.
2. **Teleport to the podium when the titan falls** (Now 8; ux_critique #10, B8). About 3 s after the boss falls for a
   player who just finished, `TeleportTo` them into the victory area within 3 m of the podium buttons, facing them.
   Rename the action "RACE AGAIN" everywhere the director writes it (`SetCountdown` lines, hints; the podium button's
   interaction text through `SetInteractionText` if `button_device` exposes it; check the digest), and "NEW SKILL"
   for CHANGE SKILL (H renames the board buttons the same way).
   Proof: `DebugAutoRightAnswers` run to the finish; the log line for the teleport; a frame of the podium in front.
3. **Feed and strip** (Now 5; ux_critique #6). Wrong-door feed lines go to the victim's HUD only (`PushFeed` on their
   own HUD), EXCEPT the current leader's misses, which may stay public. (H drops the medal word from the public
   finish line inside `FnmFeedFinish`; you change nothing for that.) Strip (`RaceRowsFor`): top 3 + the one rival just ahead + you, no full ranking that shows who is last; the
   arena shows "BOSS" not "station 10" (ux_critique 3.10). Proof: log lines; a frame of the strip. Two real players
   are not available: reason the multi-player branches from the code and say so.
4. **Recap card** (Now 6; ux_critique #5). Delete "Correct!  <explanation>" under the next question (D:1389). On a
   right door: show the recap (solved question, right tile lit, steps, "CORRECT!  -1.8 s" or "CORRECT!" when there is
   no pace) for about 3 s, then the next question. The race arena uses the same card instead of "Last one:"; boss
   mode's `FnmLastOne` path may stay as it is. Needs H's `ShowRecap` (seam below). A newer door answer or the arena
   must never be overwritten by a late recap flip (use a generation counter, like `ShowFeedback` does).
   Proof: frames at 0.5 s and 3.5 s after a right door showing recap then question.
5. **Station 1 as the tutorial** (Now 9; ux_critique #2). On a player's first run of the session (or first ever, if
   persistence makes that easy), station 1 shows short captions: what the doors are (each door is an answer; A is
   on the left), how to answer (run through the door with your answer; E opens it), what a wrong door costs. Keep each
   caption under ~50 characters and on screen long enough to read while walking 30 m. No guard at station 1 (S
   removes the spawner; you make sure the director is happy with that).
6. **Copy pass** (Now 4; ux_critique #7 and table 3.10), for the director's own strings: "Station" everywhere a
   player sees "Stage"; one arena instruction that fires on arena ENTRY and is not overwritten in the same tick; one
   hit counter (the boss bar), not two; "Today's record" for the per-session record (the board, the record line, the
   NEW RECORD tail); show the medal rule on the finish (read the medal logic first and write the rule it really
   applies); "Only A, B, C this time" as a caption when an item has fewer than four choices; the `choose` voice line
   2.0 s after `welcome`. Do not rename the game or remove "Fortnite" from anything: that waits on Aaron (Now 11).

## Seam with H (`fnm_ui.verse`)
H adds, without changing existing signatures:
```
ShowRecap(Prompt:string, Choices:[]string, RightIndex:int, Steps:string, Verdict:string):int   # returns a generation
EndRecapIf(Generation:int):void                                                                 # no-op if superseded
```
`ShowRecap` puts the solved item on the slate (the prompt, the tiles with the right one lit, the steps line, the verdict
line) and returns at once; the director waits ~3 s, then calls `EndRecapIf(Gen)` and `ShowCurrent`. Check that both exist in
the Verse ROOT copy before you sync a director that calls them (TEAM.md seam rule); until then build items 1-3 and 5.
If H's version differs from this, adapt and say so in your report.

**Keep `DebugAutoPick` at 0 in the copy you sync to the Verse root while you build**, so that H's capture sessions
reach a question. Restore every hook to its ship value (the list at the top of `fnm_director.verse`) at the end,
sync your files, `BuildAll` clean, and say so.

## Verification you must perform
- `BuildAll` clean (`[]`) after your last sync, with ship values. Prove it once with a planted unknown identifier
  (expect error 3506), then remove it.
- pytest: the full suite green, or every failure explained as another agent's in-flight work.
- One full `DebugAutoRightAnswers` run to the finish with all your changes in, plus one `DebugAutoWrongAnswers`
  session through at least three wrong doors, both with frames you READ.
- A disproof: e.g. set the retry offset to 0 so the retry spot lands inside the vestibule, and show the log
  answering a door by position (proof the clear-of-triggers check matters), then restore.

## Non-goals
- No new penalties, no hint baking (ux_critique #9), no guard weapon changes, no HEAT/party mode, no rename.
- Do not touch `fnm_ui.verse`, scene builders, cartridges, GOALS, CLAUDE.md. Do not commit.
