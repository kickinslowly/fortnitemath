# D round 2: audit fixes (Fable audit of the G9 diff, 2026-10-13)

Same rules as `TEAM.md` and your first brief. You own the director files again; Q (the QA runner) has finished and
restored the ship hooks. The parent set `RetryStandOff` to 600.0 after your report (at 3 m only doors B and C were on
screen); keep 600 unless Q's frames say otherwise (the parent will tell you).

1. **MAJOR: `ChargeWrongDoor` corrupts the clock's "no clock" sentinel.** `set State.StartTime -= WrongDoorSeconds`
   (fnm_director.verse ~1653). `StartTime < 0.0` means "no clock" everywhere (clock loop break ~2435, `RecordSplit`
   ~3056, `FinishPlayer` Time = 0.0 ~2115, `RaceEntry` ~3135, `Racing` ~3143, `ChargeWrongDoor` itself). On a fresh
   session GO happens at sim time T of tens of seconds, so after N wrong doors with 3N > T the clock freezes, splits
   stop, and the finish records 0:00.0 as a persisted personal best and today's record. Fix: a per-player
   `ClockPenalty` reset where `StartTime` is reset, added by `ChargeWrongDoor`, and added to every
   `elapsed = now - StartTime` read (clock loop, RecordSplit, FinishPlayer, RaceEntry, and any other you find). Never
   move `StartTime`. Proof: a FIRST-run-of-session `DebugAutoWrongAnswers` session with enough wrong doors that 3N
   exceeds the GO time (log the GO sim time; 8 to 10 wrong doors), the clock keeps ticking, every wrong door logs its
   +3 s, the finish time equals real elapsed + 3N (log both).
2. **Boss mode through the shared `Punish`:** Mud now holds the player in stasis on the pad for 2 s and Dizzy spins
   them in place, where both used to move them to the entry first; `Wave()` has just released monsters next to them
   and stasis does not block damage. In boss mode, move the player to the retry point (the arena entry) FIRST, then
   hold, as before. Race behaviour unchanged. Also remove boss mode's now-dead "not for a Spike penalty's own death"
   exclusion only if it is truly dead (Spike no longer kills); say what you did. Proof: one `DebugAutoBoss` +
   `DebugAutoWrongAnswers` session through Mud and Dizzy (or reason it from the code if the pick is random and they
   do not come up in two tries; say so).
3. **Race arena recap vs live pads:** during the 3 s recap the next item is drawn and the pads are live, but the
   question is not on the slate; a player teleported to the arena entry can reach a pad in ~2 s and answer an unseen
   question (`TooSoon` covers only 1.5 s). Fix: in the race arena the recap lasts no longer than the answer cooldown
   (or the cooldown covers the recap there). Stations are unaffected (the next wall is 30 m away).
4. **Private miss copy:** the victim's own HUD reads "<their own name> got frozen at station 3" (`MissFeed` pushes
   `FnmFeedPenalty(State.Player, ...)`). Private lines say "You got frozen at station 3" (build the message in the
   director, e.g. with `FnmText`; `fnm_ui.verse` is H's).
5. **Comments:** the file header (~14), `RetrySpotFor` (~1597) and the field comment say 3 m; it is 6 m. Fix the
   words. Your report's disproof "offset 0 lands inside the vestibule" cannot happen: `RetrySpotFor` puts Y in front of
   every zone for any offset >= 0, so the OnBegin clear check is true by construction. Say how your disproof actually
   placed the spot inside door B's zone, or redo it so it really does (a negative offset, or a test-only hook).

Verification: pytest green (17279+), `BuildAll` clean with ship values (planted-identifier disproof once), the two
sessions above with frames you READ. Restore every hook. Report in TEAM.md format, only what moved.

## Added after the QA pass (Q, 2026-10-13; frames under scratchpad/team/Q/frames/)
6. **All four doors on screen at the retry spot.** At RetryStandOff 600 (in effect: station 1's spot moved to y -9625)
   the third-person camera still frames only doors B and C (`Q/frames/wrong/w2_retry_spot_st2.png`); the camera sees
   about 2.6 door pitches at that distance, so all four need ~11 m, which lands among the obstacles (the last ones sit at
   1950-2000 cm of the 3000 cm hall, sliders 246 cm deep). Keep the stand-off at 600 and use the existing wide camera
   (`WideCamera`, the orbit device, distance 900) from arrival on the retry spot until the player has moved ~1.5 m or
   ~4 s pass, whichever comes first (or a better idea; say what and why). Proof: a frame from the retry spot with all
   four doors and their lintel letters on screen, and one after the camera returns. Guards shooting at the retry spot
   at stations 2-3 is the accepted trade-off (ux_critique #8); do not change guards.
7. **Podium arrival framing.** After the podium teleport the world label RACE AGAIN overlaps the HUD clock panel, NEW
   SKILL is cut off at the right edge, and the all-time billboard is clipped at the top
   (`Q/frames/av_areavolume_finish.png`). Arrive centred between the two lecterns, far enough back that both labels and
   the all-time board are in frame, facing them; RACE AGAIN must still be a few steps away. Frame it.
8. **Medal rule line wraps** ("... - Best streak 10" puts "10" alone on the next line; the board wraps at 920 px). Make
   the line fit: e.g. "GOLD = 10/10 first try   SILVER 7+   Streak 10" (your words, keep it true to `FnmMedal`).
