# S: arena pads in one row, a bigger titan, analytics devices (Sonnet)

Read `briefs/g10/TEAM.md` first (ownership, the D <-> S seam, lock, report format), then the project `CLAUDE.md`, the
`uefn-mcp` skill, `maps/starter/LAYOUT.md` "Boss arena", `BOSS_MODE.md` §16, `tools/build_course.py` (`arena()`,
`PAD_SPOTS`, `PAD_SIZE`, `trigger_fit`, `--triggers-only`) and `tools/build_race_boss.py`.

## Why

The review (REVIEW.md §4 P1, `sources/ux_critique.md` #11): "Pads sit in a 2x2 grid, so A and B are off-screen at entry
and the mapping differs from the doors ... The titan is 6.3 m (boss mode's is 12 m)." Fix: "Pads in one row A-B-C-D left
to right at about 10 m (hall is 22 m wide, 4 x 4.5 m fits). Rerun trigger_fit and the race-boss letters ... Titan scale
2.1 to 3+." Analytics: gamification §6 "Par calibration": an `analytics_device` at each station and the finish gives a
per-station funnel in the Creator Portal, the data the medal time gates need.

## Deliverables

1. **Pads in one row**, A-B-C-D in the same left-to-right order as every station's doors (check a station's door wall
   for which x is A; do not trust "left" from memory), about 10 m in from the entry, inside the 2212 cm hall. Leave a gap
   wide enough that a player standing on one pad never trips its neighbour's trigger (`trigger_fit` senses the tile);
   shrink `PAD_SIZE` if needed and say so. Move the adds spawner, the floating letters (build_race_boss) and anything
   else keyed to the old spots; the "BOSS ARENA" sign must not collide. Do it **in place**: add an `--arena-pads` mode
   (or similar) to `build_course.py` that re-places only the pad tiles + triggers, keeping their tags and labels. NEVER
   run a full `build_course.py`. Then rerun `build_race_boss.py` for the letters.
   `DebugPadOffset` (180 cm, a director constant) drops the auto-run that far off a pad's centre: if your pad size makes
   180 cm fall off the tile, name it in the report (the parent routes it to D).
2. **A bigger titan.** `TITAN_SCALE` 2.1 -> 3.0-3.5 (fits the 6 x 4 m platform, reads from the entry; boss mode's is 4.0
   in a 64 m colosseum, this hall is 22 x 30 m). The mega cannons aim at its waist (`BEAM_AIM` scales with it) and the
   race laser is baked: rebuild it with `build_fx.py NS_fnm_laser_race` under the lock (CLAUDE.md: rebuild after moving
   the cannons or rescaling that titan). Name any director constant that depends on the titan's size (leash, hit radius,
   `FaceLetter`) in your report; do not edit Verse.
3. **Analytics devices:** new `tools/build_analytics.py`, idempotent via actor tag `fnm_analytics_rig`: one
   `analytics_device` per station (10), one at the finish, one at the boss, with Verse tags exactly per TEAM.md
   (`fnm_analytics` + `fnm_station_NN` / `fnm_finish` / `fnm_boss`). Find the device's class path in
   `reviews/race-2026-10-13/sources/device_catalog.tsv`; set a readable event name per device if the device has one (read
   its properties back). Hidden in game. `--check` and `--remove`.
4. **Tests:** extend `tests/test_arena_layout.py`: pads in one row, the door order, no trigger overlap, all inside the
   hall, letters over their pads; one sabotage (swap two pad x values, the order test goes red; restore by re-applying).

## Verify

Editor captures (no lock; not during a session): the arena from the entry at eye height (floor + 170 cm, looking +Y) and
from above. Then one hooked session under the lock: `DebugStartStage 11` + `DebugAutoPick 0` + `DebugAutoRightAnswers`
(set on the placed director device, one key per `set_properties`, ship values back after; never edit Verse): frames of
the entry view (all four pads and the titan's head on screen), a laser volley hitting the titan's waist, the kill and the
gate. Read every frame. Note: W is changing course walls at the same time (not the arena) and D/H are compiling Verse;
take the lock per batch.
