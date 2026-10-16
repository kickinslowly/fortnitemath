# D: race features in the director (Opus)

Read `briefs/g10/TEAM.md` first (ownership, the D <-> H and D <-> S seams, lock, compile rule, report format), then the
project `CLAUDE.md`, the `uefn-mcp` skill, the header comment of `console/verse/fnm_director.verse` (lines 1-100), and
`reviews/race-2026-10-13/sources/gamification.md` §4 (C1-C3), §5 (R4), §6, §13. Penalties: `console/PENALTIES.md`.

## Why

The 2026-10-13 review's "Next" list (REVIEW.md §10), the items that need no human decision. Its design rule, which every
deliverable obeys: **the first-try right answer is the only thing that earns anything. Mistakes are private; the leader's
mistakes are drama.** Nothing lets speed beat thinking.

## Deliverables, in this order (checkpoint each; the later ones are bigger)

1. **Small fixes, check first, fix what is still open** (several may already be done; say which):
   - Boss mode's own feed names the player on a miss (`fnm_bossmode.verse`). Misses go to the victim alone, as the race
     does since G9 Now 5.
   - Arena: "DIRECT HIT!  N TO GO" when no boss is up; the arena intro firing ~44 m before the hall with its hint
     overwritten in the same tick (it should fire on arena hall entry); two hit counters (one, on the bar); the strip
     saying "station 10" in the arena; the tier-5 label "Boss Level" at stations 9-10 where there is no boss; up to four
     sounds stacking at the kill; Dizzy's two full turns (motion discomfort: one turn, or a blur with no spin).
   - Call H's `SetCompact(true)` at arena entry and for the wrong-door retry hold, `SetCompact(false)` when each ends
     (seam rule: only once it exists in the Verse root).
2. **Next-reward line (C1).** The streak line reads "STREAK x2 - 1 more for a SHIELD" / "x4 - 1 more for a STRIKE".
3. **REDEMPTION at the boss (R4).** Each station a player missed (no first-try right) queues its tier. That player's arena
   pad questions come from those tiers first, in station order, with the slate's stage line "REDEMPTION: <station N>",
   then the usual tier 5. A right redemption pad deals the normal boss hit, shows "REDEEMED!", and restores half credit
   for that station: accuracy counts a redeemed station as 0.5. Medal and accuracy remain course-only otherwise.
4. **SHIELD at streak 3 (C2).** Hold at most one. It blocks the next penalty: the player's own wrong door, or an incoming
   strike. On a wrong door the penalty and the hold are skipped, but the streak resets, first-try credit is lost and the
   door stays shut; the player goes to the retry spot; HUD "SHIELD SAVED YOU - still wrong: <that choice's feedback>".
   `SetShield(On)` (H) shows the charge. The strip row may carry a shield marker if it fits.
5. **STRIKE at streak 5, 10, 15 (C3).** 1 s after it is earned it auto-fires at the **nearest racer ahead** in strip order
   who is not immune, not in a vestibule, not in the arena and not finished. The leader's strike becomes +2 s boost
   ("LEADER BONUS"), so strikes only flow forward. Effect from a light, in-place pool built from the existing penalty
   devices: Freeze 2.5 s, Mud 4 s at 0.6, Dizzy blur 3 s with no spin, Lights Out 1.5 s. Never a send-back; never touches
   the target's question, streak or credit. The target gets "INCOMING STRIKE from <name>" ~1 s before it lands; a shield
   blocks it; 20 s immunity after a hit. Feed (public): "<A> froze <B>!" / "<B>'s shield blocked <A>!".
   `@editable StrikesOn : logic = true` (the host toggle later). Two players have never played together, so add a hook
   `@editable DebugStrikeSelf : logic = false` that fires each earned strike at the player who earned it (warning,
   effect, immunity, shield block), so one client can see every branch but the targeting. Say plainly in the report
   which branches were seen and which were only reasoned.
6. **Medal v2, the part that needs no data (gamification §6).** Accuracy gates (redeemed = half), keeping TODAY's
   thresholds (Aaron has played with them; report what they are). A FLAWLESS badge at 10/10 first-try. A next-goal
   line ("GOLD needs 9/10 - you: 8/10", or "FLAWLESS needs 10/10" at gold; "" when nothing is above). Time gates: build
   them behind `@editable MedalTimeGates : logic = false` with `GoldParSeconds` / `SilverParSeconds` editables, OFF,
   because no par data exists (one human run: Aaron 11:31, SILVER 8/10). No DEV or TEACHER medal this wave. Call H's
   `ShowBragGrid` right after `ShowResults` (marks per station 0/1/2/3, the boss mark, flawless, the next-goal line,
   `@editable IslandCode : string = ""`).
7. **Record inflation (gamification §6 last bullet).** Check what the finish shows a lone first finisher today
   ("Today's record" replaced "ISLAND RECORD" in G9 Now 4). Fix only if a lone first finish is still celebrated as a
   record (the record sound or a NEW RECORD line); otherwise report it as already fixed.
8. **Analytics (seam with S).** Declare `fnm_analytics` in `fnm_tags.verse`; on each station clear call `Submit(Agent)` on
   the device tagged `fnm_analytics` + that station's tag; on the finish the `fnm_finish` one; on the kill the `fnm_boss`
   one. Missing devices are fine (S may land later).

## How to test (single client; nothing takes the foreground)

`DebugAutoPick` + `DebugAutoRightAnswers` + `DebugAutoWrongAnswers N` gives a run with misses (up to two wrong doors at
each station of run 1, N in all), which reaches the arena with a redemption queue. `tools/playtest.py --until` +
`tools/burst.py` for frames (PrintWindow). Log every new branch with an `FNM:` line so the run is checkable from the log.
Read the frames: the redemption stage line, REDEEMED!, the shield line and indicator, the strike warning and effect on
yourself (`DebugStrikeSelf`), the brag grid, the next-goal line. Pure-logic pieces (redemption queue order, half credit,
medal with redeemed stations, strike target choice from a strip order) belong in `fnm_logic.verse`-style helpers with a
Python mirror test in `tests/test_g10_*.py` only if the project already mirrors such logic; otherwise prove them in the log.

Put every debug hook back to its ship value in the repo AND the Verse root before you report.

## Not yours

`fnm_ui.verse` (H). The scene (S, W). New Mint audio (stock sounds only; `tools/build_audio.py` CUES rows are yours).
HEAT mode, host controls, accolades and DEV/TEACHER medals are a later wave: do not start them.
