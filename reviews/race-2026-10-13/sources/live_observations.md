# Live play observations, 2026-10-13 (lead reviewer, from fresh UEFN play sessions)

Build: repo HEAD 0a4cc45 + debug hooks only (DebugAutoPick 7 = Order of Operations; DebugAutoRightAnswers / DebugAutoWrongAnswers /
DebugDoorTest per session). Client captured with PrintWindow at 1920x1080. Frames are in `frames/` next to this file. On-screen white
"FNM: ..." lines in some frames are editor debug prints that a published island does not show: ignore them.

Auto-run (teleports into each right vestibule every 6 s, so hallways are not walked): run 1 finished 1:29.8 GOLD 10/10, run 2 1:26.6.
A human run has never been timed.

## Frame index
| File | What it shows |
|---|---|
| 01_picker.png | FIRST SCREEN a kid sees (ship values) |
| 02_countdown.png, 03_go.png (misnamed: log lag) | station 2 hallway, slate, clock, strip (night lighting) |
| 04_station1_hall.png, 05_correct_s1.png | station 3 with "Correct! <previous explanation>" under the NEW question, STREAK x2 SPEED BOOST |
| 07_streak3.png | station 4, STREAK x3, feed "is on a 3 streak!" |
| 08_after_s4.png, 09_after_s5_ice.png | station 6 approach, ice dressing (icicles), STREAK x5 |
| 10_after_s8.png | station 9 "Boss Level" tier caption, STREAK x8 |
| 11_arena_entry.png | arena entry flash STEP ON THE RIGHT ANSWER PAD!, boss bar, titan far away |
| 12_cannons.png | cannons firing lightning lasers at the titan, floating C / D letters (night) |
| 13_boss_hit2.png, 14_boss_down.png | hit 2; FINISH board over the arena, feed overlapping it, DEFEATED! bar |
| 15/16_finish_board*.png | finish board |
| 17_victory_area.png | after the board hides: still in the arena, "Race again: NEW RACE at the podium", ALL-TIME screen far behind the titan |
| 18_new_race.png, 19_run2_pace.png, 20_run2_finish.png | run 2 countdown, pace delta, run-2 finish |
| now_client.png | same arena spot in daylight (dawn): true colours |
| burst/wrong_13.png | FREEZE: frost whites out the screen, ice cube, feed "got frozen at station 1", feedback "Check your arithmetic." |
| burst/wrong_22.png | station 1 from the landing spot, daylight: the door wall at 25 m |
| burst/wrong_33.png | after a YEET: back in the hall facing the doors |
| burst/wrong_50.png | SPIKE: orbit view of a white door; Fortnite's own line "Humanist_NA (91) bailed early" |
| burst/wrong_71.png | MUD: sepia turns the whole screen orange and blown out |
| burst/wrong_86.png | DIZZY |
| burst/door_*.png | close-up of station 1 door B (see "Doors" below) |

## Observations (lead reviewer's own, from the frames)
1. **First screen** (01): Fortnite's own "GAME MODE / Game in Progress" panel top left, then a "Fortnite Math / Choose your skill" tag, then a
   race clock already reading 0:00.0. The menu heading says "CHOOSE YOUR SKILL" while the step line says "Pick a grade". Three identical yellow
   buttons: BOSS BATTLE (a different game mode) sits above GRADE 6 and GRADE 7 with equal weight. No title card, logo, mascot, trailer moment,
   or one-line "how to play". Behind it: a pastel hallway, glare-white floor, giant pink/blue digits floating in the sky.
2. **Lighting is uncontrolled.** Island Settings `timeOfDayOverride` = NoOverride, so the island runs Fortnite's day/night cycle. The whole
   auto-run happened at NIGHT: every frame is blue-cyan and flat, the tier wall colours (green/blue/purple/orange/red) are gone, the orange
   Magma Titan reads blue, the walls show a checker texture. At dawn (now_client) the floor is a white glare. Kids get a random mood each session.
3. **The hallway reads as a greybox**: flat painted cube walls, white floor, torches, floating digits. Nothing in the world says "math" or
   gives a place identity except the ice station's icicles. Connectors are bare.
4. **HUD load**: 8+ panels at once (Fortnite GAME MODE panel, skill tag, clock + target + delta + RACE strip, the slate (about 1180 x 330 px with
   feedback and streak lines, top centre), minimap, feed, health/shield, inventory, ammo). The slate sits exactly where the door wall is when
   you look down the hall from the landing spot.
5. **Right-answer copy misleads**: the explanation of the question you just answered appears as "Correct! ..." under the NEXT question's tiles
   (05: question `4 x (10 / 2 + 2)` with "Correct! 2 x 2 = 4, then 2 + 4 = 6."; 10: question `(2 x (4 / (8 - 6)))^2` with "Correct! 8 / 4 = 2,
   then 2 x 5 = 10, then 10^2 = 100."). A kid reads it as the working for the current question.
6. **No world feedback on a right answer**: the verdict is a HUD flash (not caught in any frame because it lasts 1.5 s), the barrier vanishes.
   No burst, no light, no camera, nothing a classmate can see.
7. **The streak line works**: big yellow STREAK xN - SPEED BOOST Ns, feed echoes it top right. Readable.
8. **Arena** (11, 12): entry shouts STEP ON THE RIGHT ANSWER PAD! across the screen while the slate's caption and the boss bar say it again;
   the stage-10 explanation is still on the slate. The cannon volley (lightning lasers, floating 3D letters) is the strongest visual moment in
   the race. (Correction: the "0 muzzle vfx" log counter counts the retired VFX-Spawner muzzles; the Niagara muzzle fires in both arenas.)
   The titan is 6.3 m and small at the far end of the hall.
9. **Finish** (14): a translucent wall of 8 text lines (FINISH!, GOLD MEDAL, time, best, island record + NEW RECORD!, accuracy + streak, TOP
   TIMES THIS SESSION, row 1, "Walk on!..."). The medal is a word, not an object. The feed overlaps the board's right edge. The run "finishes"
   in the arena; the podium and ALL-TIME screen are 55-60 m away and tiny in frame (17).
10. **Penalties** look strong as screen gags: frost white-out with an ice cube (13), sepia mud (71) is so strong the screen is orange glare.
    Spike shows Fortnite's own elimination line "bailed early". Every penalty publishes "<name> got frozen at station 1" to the whole island.
11. **Wrong-door feedback** on a warm-up item `2 + 7 x 9` was "Check your arithmetic." (no worked step, no hint of the rule).
12. **Doors**: see the door close-up section below.

## Doors (verified 2026-10-13, P0)
- In play (burst/wrong_22, wrong_33, wrong_86: daylight, from the landing spot) the four doors of station 1 look **identical**: white wall
  panels with pale glass-blue door leaves. No A/B/C/D letters, no white/blue/green/orange colour coding.
- Close-up (burst/door_02.png, 2.5 m from door B, night): plain perforated door leaf, no letter, no colour. Fortnite's native "E OPEN" prompt
  does appear at that range (so a kid does get told to press E once they are at the door).
- Editor (frames/editor_doors_s1.png): the same four identical doors.
- Cause found: `FNM_S01_DoorB` reads back `doorAnimatingMaterial: null` and `DoorComponent.overrideMaterials: [null]`, while the four
  `M_door_face_a..d` materials exist in FNM_Art. The door paint from fb38d7d (`build_course.door_dress`) is no longer applied (lost in a later
  rebuild/swap; which one is not diagnosed). Fix path: re-run the door dress (`build_course.py --doors-only` or `door_dress`), then see it in play.
- Consequence: the HUD shows four coloured, lettered tiles; the world shows four identical doors. The only mapping is left-to-right order
  (A leftmost, D rightmost, which does match the tiles' order). This is the core loop's single most important affordance.
