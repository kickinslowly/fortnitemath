# Brief C — Live race layer: rivals strip, pace deltas, public feed (G6 item 2)

You are building GOALS.md **G6 item 2** in `D:\PyCharm Projects\fortnitemath`: turn the solo time trial into a
visible race. Three HUD features, all per player, driven by the director. Read first, in order:

1. `CLAUDE.md` (whole: tools, Verse line endings, sync + BuildAll, test hooks, playtest.py)
2. `~/.claude/skills/uefn-mcp/SKILL.md` §"Verse UI buttons and HUD menus" and the MCP calling pattern
3. `GOALS.md` §G6 (plan), `PROTOCOL.md` §6 and §6b (per-player rules; bests are per skill), `maps/starter/LAYOUT.md`
4. `console/verse/fnm_ui.verse` (the HUD: `Attach` builds the canvas; the left panel holds `ClockText` +
   `TargetText`; `FnmText/FnmRow/FnmHolder` are the `<localizes>` message helpers that render a player's name from an
   `agent` parameter, which is the ONLY way to show names), `console/verse/fnm_director.verse` (`fnm_player_state`,
   `fnm_result`, `HandleDoor`, `AdvancePlayer`, `FinishPlayer`, `RecordResult`, `BoardFor`, `Countdown`, `Punish`,
   `WatchSkip`, `PlayerStates`), `console/verse/fnm_save.verse` (persistence: fields may be ADDED with defaults,
   never removed or retyped), `console/verse/fnm_penalties.verse`, `console/verse/fnm_audio.verse` (exists; do not
   change it; you may call `Play` on existing cues only where this brief says).

## Repo facts (checked 2026-10-07)
- Windows 11, Git Bash, branch `master`. Python `.venv/Scripts/python`. Tests: `.venv/Scripts/python -m pytest -q`
  (read the current count from a run BEFORE you change anything; keep it green).
- UEFN 42.30 is open with the project; MCP at `http://127.0.0.1:8000/mcp` via `tools/uefn_mcp.py` (importable
  `uefn_mcp`). From Git Bash prefix `MSYS_NO_PATHCONV=1` when an argument starts with `/`.
- After any Verse edit: `.venv/Scripts/python -m fnm sync starter` then
  `.venv/Scripts/python tools/uefn_mcp.py ValkyrieToolset.VerseToolset BuildAll '{}'`. Clean build = proof.
- Verse files are LF: edit with the Edit tool or `tools/patch.py`, never `write_text` from Python.
- Headless runs: `tools/playtest.py --until "finished run 2,stuck at stage" --timeout 300` (relaunch, wait for
  a director line, print `FNM:` lines, screenshots `%TEMP%/pt_*.png` — LOOK at them with the Read tool). Flip the
  director's `@editable` test hooks (`DebugAutoPick`, `DebugAutoRightAnswers`) in the Verse default with
  `tools/patch.py`, sync, BuildAll; restore ship values (0 / false) before you finish. With `DebugAutoRightAnswers`
  the director presses NEW RACE itself, so run 2 happens: that is where the pace deltas become visible (run 1 sets
  the record). Screenshots never take the foreground.
- Verse facts: a `message` is built by a `<localizes>` function with `{Agent}` params (see `FnmRow`). A
  `text_block` has `SetText(message)` and `SetTextColor(color)`; one colour per block. `GetPlayspace().GetPlayers()`
  lists players; `PlayerStates : [player]fnm_player_state` is the director's map.

## Design (fixed; do not redesign)
**A. Rivals strip** — under the clock in the left panel: a heading row `RACE` and up to 8 rows, one per player on
the island, sorted by progress: finished players first (fastest first) as `{Who}  FIN 1:23`, then racers by stage
descending (ties: less elapsed time first) as `{Who}  station 7`, then `{Who}  picking` / `{Who}  lobby`. The
viewer's own row reads `YOU` instead of their name and is drawn in `NamedColors.Gold`; others white. If there are
more than 8 players: top 7 + the viewer. Refreshed by ONE director loop `RaceLoop` every 0.5 s that computes the
order once and writes every player's HUD. Hidden while the viewer is picking or has no HUD. New `fnm_hud` methods:
`SetRivals(Rows:[]message, OwnRow:int)` (collapses unused rows).

**B. Pace deltas** — per player, per skill. A run records `Splits : []float`: the race-clock time at each right
answer (index stage − 1), length = `Stations.Length` at the finish. `fnm_result` gains `Splits : []float = array{}`
and `RecordResult` carries them with the time. `fnm_saved` gains `BestSplits : [string][]float = map{}`;
`FnmSaveBest` gets a `Splits` parameter (saved with the time), plus `FnmSavedSplits(Player, Id)<decides>`.
The **pace target** for a run, chosen at GO!: the session island record's splits for this skill
(`BoardFor(Skill)[0].Splits`, if its length matches) else the player's own saved `BestSplits` else none. At each
right answer at stage s: `Delta := Elapsed − Target[s − 1]`; the left panel shows a new `DeltaText` under
`TargetText`: `−1.8 s` in `NamedColors.LightGreen` when ahead, `+3.2 s` in `NamedColors.Tomato` when behind
(one decimal, a real minus sign `−` as in the cartridges' charset), hidden when there is no target. `TargetText`
keeps `Beat 1:23` and becomes `Record 1:23` when the target is the island record rather than the player's own
best. Log `FNM: split stage {s} at {T} delta {D}` for every split. (Design note for the record: the "pacer orb" in
GOALS is dropped — a prop is visible to every player and a pace is per player; the HUD delta is the pacer.)

**C. Public feed** — a block at the top right under Fortnite's minimap: anchors (1, 0), alignment (1, 0), offsets
Right 20, Top 300 (check it clears the minimap in a screenshot at the client's resolution; if the minimap is taller,
move it down and say so). Up to 3 lines, newest on top, each dropping after 7 s. Dark 0.55 panel like the others,
text size like `TargetText`. Director method `Broadcast(Line:message)` writes the line to EVERY player's HUD
(`fnm_hud.PushFeed(Line)`); the HUD owns the timers (`spawn` a fader per push, generation-guarded so an older fader
cannot clear a newer line). Events and exact copy (new `<localizes>` helpers in `fnm_ui.verse`):
- penalty: `{Who} got {Past} at station {N}` with `FnmPenaltyPast(Kind)`: Freeze → `frozen`, Spike → `spiked`,
  Mud → `stuck in the mud`, Dizzy → `dizzy`, Blackout → `blacked out`, Yeet → `yeeted` (add it to
  `fnm_penalties.verse` next to `FnmPenaltyLabel`).
- finish: `{Who} finished in {Time}  ({Medal})`; island record: `{Who} set the island record  {Time}`.
- streak at 3, 5, 7, 10: `{Who} is on a {N} streak!`
- skip guard: `{Who} tried to skip and was sent back`.
Log every broadcast as `FNM: feed {text without the name}` so a headless log proves it fired.

## Deliverables
1. `fnm_ui.verse`: `DeltaText`, the rivals heading + 8 row blocks, the feed panel + 3 blocks; `SetRivals`,
   `SetDelta(Text, Color)` / `ClearDelta`, `PushFeed`; the message helpers. Keep the existing layout, sizes and
   colours untouched otherwise. The rivals block and feed must NOT be part of the results board.
2. `fnm_director.verse`: `Splits` on `fnm_player_state` (reset per run), target selection at GO!, delta at each
   right answer, `RaceLoop` (started at OnBegin), `Broadcast`, the four feed call sites, splits into
   `RecordResult`/`fnm_result` and `FnmSaveBest`. New `@editable` nothing: no new hooks are needed.
3. `fnm_save.verse`: `BestSplits` field and `FnmSavedSplits`, `FnmSaveBest` signature change (update every caller).
4. `fnm_penalties.verse`: `FnmPenaltyPast`.
5. Docs: `console/README.md` §4 "What players see" gains the three features (short); `PROTOCOL.md` §6b gets one
   bullet: splits are per skill and per map like times. Nothing else in PROTOCOL.

## Verification
- BuildAll clean; pytest count unchanged or higher.
- Headless `DebugAutoPick 0` + `DebugAutoRightAnswers true`, `--until "finished run 2"`: log shows 10 `split stage`
  lines per run with deltas on run 2, `feed finished in` twice, `feed set the island record` on run 1 (and run 2 if
  faster), streak feeds at 3/5/7/10, `RACE` rows. Read the screenshots: the strip under the clock with `YOU
  station N` climbing, the delta under `Record …` on run 2 green or red, the feed top-right not covering the minimap
  or the question panel, nothing overlapping the finish board. Capture one frame mid-run and one at the finish and
  name the files in the report.
- `DebugAutoWrongAnswers 3` (`--watch 3`): three `feed got … at station` lines with the past-tense labels.
- Sabotage once: swap the ahead/behind colours or sign in `SetDelta`, run, confirm the screenshot/log shows it wrong,
  restore by re-applying the original text (never `git checkout`), rebuild. Say what you saw.

## Non-goals / do NOT
- Do NOT commit. Do NOT run any `tools/build_*.py`. Do NOT edit `fnm_audio.verse`, `tools/**`, `GOALS.md`,
  `CLAUDE.md`, `cartridges/**`, `emulator/**`, `fnm/**` (except nothing), the course, penalties' behaviour, timing or
  door logic. Do NOT add sounds (the audio builder owns cues).
- Do NOT persist other players' names (Verse persistence is per player; see fnm_save.verse header).
- Restore every debug `@editable` to its ship value, sync and rebuild before finishing. Checkpoint each file to disk
  as soon as it compiles.

## Report
Files edited; BuildAll result; pytest before/after; the log excerpt (splits with deltas, feed lines, RACE rows);
the screenshot file names and what each shows (in words: positions, colours, overlaps); the sabotage result.
Then **"Anything I decided differently from this brief and why"** and **"Shakiest assumption, stated plainly"**,
and anything in the docs that turned out untrue.
