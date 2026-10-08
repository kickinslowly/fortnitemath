# Brief F — Agency: gamble pad, lifelines, coins + shop (G6 item 4) — DRAFT, not yet fired

Status: written 2026-10-07 while the boss builder ran. Fire only after Aaron has played items 1–3 and after the
parent re-reads this against the then-current director (the boss arena changes stage counting). Read first:
`CLAUDE.md`, `~/.claude/skills/uefn-mcp/SKILL.md`, `GOALS.md` §G6, `maps/starter/LAYOUT.md`, `console/README.md`,
`console/AUDIO.md`, `console/PENALTIES.md`, `tools/build_course.py`, `tools/build_pickups.py` (pads along the walls),
`tools/build_finish.py` (podium buttons), `tools/build_audio.py`, and the whole of `fnm_director.verse`, `fnm_ui.verse`,
`fnm_save.verse`, `fnm_audio.verse`.

## Design (fixed; built to the existing geometry — no door-wall changes)
The original "gold fifth door" would widen some stations and shift every connector; instead every piece of agency
is a **floor pad in the hallway**, which the course already knows how to place (pickup pads) and the director
already knows how to answer (trigger zones).

**A. Double-or-nothing pad** (every odd station from 3, centred in the run line 5 m before the door wall, a gold
tile with a `2x` board): stepping on it arms a gamble for THIS station only (HUD: `DOUBLE OR NOTHING  -  right: skip a
station, wrong: 2 penalties`). Right door → the player skips the next station (stage += 2, the barrier of the right
door opens as usual, the director teleports them to station+2's entry with a `SKIP!` flash, cue `Perfect`), streak
and first-try credit as normal, and the split for the skipped station is recorded equal to this one. Wrong door →
two penalties back to back (the normal one, then a second draw after the player is back at the entry), streak reset,
feed `{Who} lost a double-or-nothing at station {N}`. Armed state clears on any answer. Not available at the last
station or the arena.

**B. Lifelines**, two per run, each a pad on a side wall near the entry (left wall `50/50`, right wall `PEEK`,
stations 2..9; both pads at every one, the budget is per run not per station):
- 50/50: two wrong choices go dark on the HUD's choices line (`A: 72    B: --    C: --    D: 63`), chosen at
  random among the wrong ones; the doors stay. Feed nothing. HUD counter `LIFELINES 1`.
- Peek: the item's `explanation` shows for 3 s in the feedback slot (amber), then hides; the race clock is pushed
  back 5 s (`StartTime -= 5.0`, so the clock jumps forward) and the HUD flashes `+5 s`. Peek is the only hint that
  shows the method, so it costs time.
Pads are triggers tagged `fnm_lifeline_fifty` / `fnm_lifeline_peek` + `fnm_station_NN`. A pad walked over with no
lifelines left flashes `No lifelines left`. Splits are not adjusted for a peek (the time cost is real).

**C. Coins and the podium shop.** 6 coins per station along the walls between the pads and the obstacles (a
`collectible_object_device` each — confirm its Verse API in the digest: `CollectedEvent` per agent and per-player
visibility/respawn options; if it cannot be per player, use a trigger + a small gold prop hidden per player with
`creative_prop.Hide/Show` is NOT per player either, so then coins are a shared pickup with a 20 s respawn and the
brief accepts that). HUD `COINS 12` under the lifelines. Coins persist per player per island (`fnm_saved.Coins`,
added with a default). The shop: three `button_device`s on a third lectern at the podium (`build_finish.py`), text
`SHIELD  10` (the next penalty is skipped once, HUD `SHIELD` badge), `HEAD START  15` (the next run's GO comes with a
6 s boost), `SHOCKWAVE  5` (one Shockwave Grenade granted at the next GO; use a non-legacy `item_granter_device`
found by tag if Verse can see it, else the Item Spawner pad trick from `build_pickups.py`; report which). A purchase
logs `FNM: shop <item> for <coins>` and feeds `{Who} bought a {item}`.

## Deliverables
1. `tools/build_agency.py` (idempotent via `fnm_agency`): gamble pads, lifeline pads, coins, shop lectern + buttons;
   reads station geometry from the course actors like `build_pickups.py`; rerun after a course rebuild (say so in
   CLAUDE.md's tools list, one bullet).
2. Verse: director (arming, lifelines, coins, shop, feed lines, splits rule), `fnm_ui.verse` (choices-line masking,
   lifeline/coin/shield counters under the RACE strip, the peek slot), `fnm_tags.verse`, `fnm_save.verse` (`Coins`,
   `Shield`, `HeadStart`, `Shockwaves` with defaults), `fnm_audio.verse` + `build_audio.py` cues `Gamble`, `Lifeline`,
   `Coin`, `Shop` (library sounds; the announcer pack already has `lifeline`).
3. Debug hooks: `DebugAutoGamble` (arm at every eligible station in an auto-right run → the run finishes in 6 doors),
   `DebugAutoLifelines` (use both on stage 2 and 3), `DebugGrantCoins N` (start with N coins).
4. Docs: LAYOUT.md "Agency pads" section, README §3 tags, PROTOCOL §6: one bullet that a console MAY offer lifelines
   that hide wrong choices and MAY skip a station on a gamble, and that splits for a skipped station copy the previous.

## Verification (sketch; finalize when fired)
Headless: auto-right + `DebugAutoGamble` finishes with 6 `split stage` lines and 4 `SKIP!`; `DebugAutoLifelines`
shows the masked choices line and a `+5 s` jump in the log and in a `--frames` screenshot; a coin walk-over
(`--keys`) increments `COINS`; a shop purchase at the podium by a real E press (ask Aaron first; the client takes
the foreground). Sabotage: make the 50/50 mask the RIGHT choice → the auto-right run must still pass (the doors are
unchanged) but the frame must show the right letter dark — proves the mask is display-only.

## Non-goals
No door-wall or connector changes; no new penalties; no change to medal rules; do not commit.
