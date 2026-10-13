# RACE mode fact inventory (fortnitemath), for the UX review

Snapshot: repo HEAD 0a4cc45 (2026-10-11), working tree clean (only untracked `.playwright-mcp/`). Debug hooks in
`console/verse/fnm_director.verse` read at ship values (lines 321-384, 610: 0 / false / -1). This file describes ship behaviour.
Written 2026-10-13. No repo file was edited.

**Tags.** `[seen:Aaron]` = Aaron played it and the notes record it. `[seen:headless]` = Claude saw it in a scripted/headless
UEFN play session (log or frame). `[code]` = read from code/config only, never observed. Where a fact mixes, both tags.
**Units.** HUD sizes are px at 1080p (the HUD is authored at 1080p, `fnm_ui.verse:70-83, 441-530`). World sizes in cm.
Citation `D:` = `console/verse/fnm_director.verse`, `U:` = `fnm_ui.verse`, `L:` = `fnm_logic.verse`, `A:` = `fnm_audio.verse`,
`BC:` = `tools/build_course.py`.

---------------------------------------------------------------------------------------------------------------------

## 0. Scope facts a reviewer needs first

- One island, one map (`maps/starter/map.json`), 11 skills in the slot (`maps/starter/generated/SLOT.txt`): grade 6 has 10, grade 7 has 1
  (`integer-ops`), **grade 8 has none**. Each skill is 5 tiers x 40 items = 200 items (`cartridges/*/baked.json`). `[code]`
- Race = 10 numbered stations (4 doors each) + "stage 11" boss arena + finish hallway + victory area. Station count 10, doors 4
  (`BC:748-750`). `[seen:Aaron]` (full walk 2026-10-04, GOALS G4 line 33).
- A **second game mode, BOSS BATTLE**, is a button on the grade step of the same picker (`U:886-894`, `D:1169-1172`). It is a separate arena
  and out of scope here, but it is the first thing a kid sees on the picker's grade step.
- There are **no human run times in any repo note or retained log** (details in section 5).
- Version state: GOALS records Aaron's private version 8564-2561-9374 (uploaded 2026-10-07, "nothing in it seen in play yet", GOALS line 96-97); the memory note
  (2026-10-09) records a newest private version code 4583-5669-1548 that "predates boss mode". Neither contains the race-finale Titan work (b65ce65) or the "Last one:"
  prefix (0a4cc45); Aaron's 2026-10-09 "arena" report came from a private version that predates boss mode and the pad-trigger fix. The Xbox class-demo build has **not** been
  seen running (GOALS line 94-95). `[code]`

---------------------------------------------------------------------------------------------------------------------

## 1. Timeline of a run, beat by beat

### B0. Join / spawn
- `OnPlayerAdded -> StartPlayer` (`D:1048, 1069`). Needs `Ready` (director finished OnBegin). `[seen:headless]`
- HUD attached (`fnm_hud.Attach`, `U:221`). Tag top-left shows **"Fortnite Math"** (Gold 24 px) / **"Choose your skill"** (Aqua 20 px)
  on a 55%-black backing at Left 20, Top 138 (`D:1074`, `U:76-77, 455-460`). Clock **"0:00.0"** (White 52 px) in the left panel at
  Left 20, Top 230 (`D:1076`, `U:125, 505-512`). Slate collapsed (`U:539`). RACE strip hidden while picking (`D:2810-2811`).
- Teleported to station 1 entry+300 cm Y, +100 cm Z, yaw 90 (+Y), whatever spawn pad was used (`D:1080-1081, 1891-1898`).
  Island has 7 spawn pads (6 added by `tools/build_island.py:39`, GOALS line 168).
- **Held in stasis**: no falling, no emotes, turning allowed (`D:1097-1099`). Held for the whole picker.
- Sound: `welcome` fires at once (`D:1083`): voice am_michael "Welcome to Fortnite Math!" 1.86 s (`tools/audio/announcer/QA.md:63`),
  stock stand-in Match_Start_01 3.83 s (`AUDIO.md:57`). `[seen:headless]` for the cue wiring; voice by ear **not heard**.
- Island: join-in-progress "Spawn Immediately", Cooperative team, building off, environment damage off, down-but-not-out off
  (`tools/build_island.py:42-49`).

### B1. Picker opens (same tick as B0)
- `BeginPicking` (`D:1117`): `Picking = true`, music silenced, picker shown. The `choose` cue fires only the first time the picker opens for a player
  (`Picks = 0`, `D:1136-1137`; not after CHANGE SKILL): voice "Choose your grade and your skill." 1.75 s (QA.md:64). **It fires in the same tick as `welcome`**
  (D:1083 then D:1137), both announcer voice lines -> they overlap. `[code]`
- Picker = its own root, centred (anchor 0.5/0.45), 78%-black panel, `InputMode All` (mouse cursor, **player cannot move**), ZOrder 5
  (`U:553-585, 947`). Heading **"CHOOSE YOUR SKILL"** (Gold 60 px). Step line (Aqua 30 px). First grade button focused so gamepad/
  keyboard can press (`U:949-950`). Both steps are plain Verse buttons.
- **No timeout, no default pick.** A kid who does nothing stays frozen (can look around) indefinitely. `[code]`

### B2. Picker step 1: grade (`U:886-894`)
- Step line **"Pick a grade"**. Above the grade buttons: loud **"BOSS BATTLE"** button with 22 px caption **"Every grade, every skill.
  Right answers NUKE the boss!"**. Then loud **"Grade 6"**, **"Grade 7"**. (Grade list is data-driven: only grades present.)
  `[seen:headless]` for the menu drawing and real clicks (GOALS G5 line 197-203); `[seen:Aaron]` not recorded for the BOSS BATTLE button.
- Click -> `fnm_pick.Grade` -> `ShowSkills` (`D:1173-1177`).

### B3. Picker step 2: skill (`U:900-950`, `D:1141-1149`)
- Step line **"Grade 6  -  pick a skill"**. One regular button per skill = the title; subtitle as a 22 px white caption under it
  (`U:959-968`). More than 5 skills -> **two columns**, left column first (`U:922-933`; PickerColumnAfter 5). Grade 6 order (title sort):
  left: Area & Volume, Data & Statistics, Decimal Operations, Dividing Fractions, Equations & Inequalities; right: Expressions, GCF & LCM,
  Order of Operations, Rational Numbers, Ratios & Rates. Grade 7: Integer Operations only. A quiet **"Back"** button (grade step had >1 grade).
- Captions: "Shapes, Prisms, Surface Area", "Mean, Median, Range, MAD", "Add, Subtract, Multiply, Divide", "How Many Groups?", "Solve One Step",
  "Write, Read, Evaluate", "Factors, Multiples, Distributing", "Exponents & Parentheses", "Number Line & Coordinate Plane",
  "Equivalent Ratios, Unit Rates, Percent", "Positive & Negative Numbers" (manifests).
- 2026-10-06 Aaron "words are cut off" on a 10-skill step -> caption-under-button layout; Aaron "looks much better" `[seen:Aaron]` (GOALS line 13-15).
- Minimum clicks to start: **2** (grade, skill). Per-skill grade/skill choice is per player (two kids can race different skills through the same doors).

### B4. Pick -> start (`D:1186-1231`)
- Picker removed (input back). Tag now shows the skill's title (Gold 24) and subtitle (Aqua 20). Personal best restored = faster of the
  session best and the saved all-time best for this skill (`D:1197-1198`). Slate opens on question 1.
- Loadout: pistol (blue, WID_Pistol_SemiAuto R) + spare ammo through a hidden item-granter trigger; health and shield set to full
  (`D:1863-1869`, `tools/build_rigs.py:25, 126-146`). `[seen:headless]`
- Stasis released, then immediately re-applied by the countdown.
- **Time from join to GO = (time to make 2 clicks) + 2.4 s countdown.** No lobby, no waiting for other players. `[code]`

### B5. Countdown, GO (`D:2164-2191`)
- Player held in stasis (turning allowed) for 3 beats x `CountdownStepSeconds` 0.8 s = **2.4 s** (`D:428`). Beat text "3", "2", "1": **White 96 px**
  at the verdict spot (anchor 0.5/0.68, Alignment 0.5/0.5, `U:483-497`), no image. Cue per beat: stock Timer_UI_Tick_Minigame 0.51 s
  (voice countdown lines are imported but unused, AUDIO.md:106).
- **"GO!"**: Lime 96 px for 1.0 s, cue `go` (voice "Go!" 0.81 s; stock Minigame_Go 2.00 s), music bed T1 starts, race clock starts,
  `ChoosePace` target set. `[seen:headless]` (GO 0.96 voice correlation, GOALS line 238).
- The question and 4 tiles are already on the slate during the 3-2-1 (ShowCurrent in Pick).
- Target line under the clock (Orange 30 px, `U:126`): **"Record 1:23.4"** (session island record has full splits) else **"Beat 1:23.4"**
  (personal best) else nothing (`D:2755-2763`). Shown on run 2+ or when a saved best exists. `[seen:headless]` (`Record 0:59.6`, GOALS line 243).
- Race clock: `m:ss.t` in tenths, truncated (`L:107-115`), refreshed every 0.1 s (`D:2188-2191`).

### B6. Station hallway (stations 1-10)
- Geometry: 30 m hall, 22.12 m wide (4 x 553 cm doors), 6 m walls, tier-coloured (green, blue, purple, orange, red by tier; finish gold)
  (`BC:54-62`, DEEP_MEMORY line 17). Player lands 4.5 m in (entry device at +150 cm, `ArrivalForward` 300). Door wall at 30 m (25.5 m of run).
  Hidden collision lid at wall top (invisible since 2026-10-08). `[seen:Aaron]` for the hall; lid-vs-shockwave **not seen**.
- Slate (top centre, Top 40, 1192 x ~230+ px, x 364-1556) [`U:280-297, 441-453`; README.md:100-104]:
  - stage caption (Aqua 22, left): **"Stage 3/10  -  Parentheses"** (`D:1294`) - tier name from the skill.
  - prompt (White 46 px, centred, wraps at 1120 px) - up to 60 chars (PROTOCOL 5 rule 6).
  - 4 answer tiles 240 x 100 px, ring/letter/value in the door's colour: **A white, B blue, C green, D orange** (`U:36-42`, `U:88-102`);
    letter 20 px, value 34 px; tile with no choice collapses.
  - feedback line (28 px, centred), streak/boost line (Orange 40 px). Slate collapses when there is no question.
  - `[seen:headless]` "compiled clean, seen in play at station 1" (GOALS G7 line 344-346). Aaron's reaction to the slate after the redesign is not recorded.
- Doors are physically painted in the same four colours with the letter on a dark tile (`BC:309-314`, LAYOUT.md:269-278) `[seen:editor]` painted
  version **not yet seen in play**; the earlier sign-actor version blocked the doorway (Aaron's test).
- **Obstacles, guards, pickups, ice per station: section 2.**
- Guards: a guard spawner per hallway is Reset+Enabled while any player's *stage* is that station, polled every 1 s (`D:969-984`);
  `guards_up` cue to players on it (voice "Guards ahead!"). Guards fill one per 1.0 s up to the station count, spawn 21.5 m into the hall,
  radius 6 m, patrol 8 m, accuracy LOW, health bars, drop their weapon (`tools/build_guards.py:57-75`, `SPAWN_AHEAD 2000`). Wildlife team (hostile
  to the Cooperative players). `[seen:Aaron]` (2026-10-04 "good"). Because the trigger is the **stage**, the next station's guards switch on the moment
  the previous door is answered, while the kid is still in the connector. `[code]`
- Pickup pads: stations 2,4,6,8,10 (Boogie Bomb one wall, Shockwave Grenade the other, sides swap), stations 3,5,7,9 (Slap Splash both walls); four pads
  per wall at 480/580/680/780 cm from the hall start - **i.e. right where the kid lands (450 cm)**; run over, 8 s respawn, one item per pad
  (`tools/build_pickups.py:56-71`). Hidden row trigger -> `OnPad` grants (rate limit 3 s per row per player, `D:606, 2721-2728`).
- Skip guard: a player found in a later hallway (shockwave over a door wall) is teleported to their own station entry, "NO SKIPPING!" Red 96 px 2 s, cue
  `no_skip` (voice "No skipping!"), public feed (`D:1458-1466`). `[seen:headless]` teleport test 0.12 s; real shockwave jump **not seen**.
- Hostile fire: any elimination (guard, spike) -> `WatchLife` polls 0.25 s -> respawn, back at *the same station's entry* with the pistol only
  and full health/shield; boost ends, streak kept (`D:1000-1028, 1863-1869`). Notice (Orange 28 px, 2 s): **"Eliminated! Back to the start of station N."**
- The question for station N+1 and its caption are shown at the instant the previous door is answered (kid reads while running the connector).

### B7. Door wall / vestibule
- Doors are real door props opened with **E** (`LAYOUT.md:18`, GOALS G4 line 36 `[seen:Aaron]`). **No HUD text anywhere tells the kid to press E,
  walk through, or that a door commits** (grep of `fnm_director/fnm_ui`: only the podium buttons mention interaction text). `[code]`
- Behind each door a 7 m vestibule with a hidden trigger filling it from the door wall's back face to 20 cm short of the barrier (`TRIGGER_DEPTH`
  680 cm, `BC:63, 376-382`), and a barrier at the back (`BC:383-387`). **Walking in = the answer** (no confirm, trigger on enter; `D:1319-1329`).
- Backstop: `WatchDoors` every 0.25 s answers for a player who has stood 0.4 s in a vestibule with no event taken (`D:1415-1448`, `DoorDwellSeconds`
  0.4). `[seen:headless]` (20/20 doors on the backstop alone; GOALS line 76-78). Aaron's 2026-10-05/06 "door did nothing" reports are fixed but
  **not re-walked by Aaron** (GOALS line 90-91).
- Letter with no choice (a 2- or 3-choice item; 12/200 data-statistics, 27/200 rational-numbers items): orange notice **"No choice D here"** 2 s,
  no penalty, `Busy` released (`D:1366-1369`). `[code]`
- Door of a later station: orange **"This is not your station. You are on stage N."** 2 s (`D:1327-1328`). Earlier station: ignored.
- A door/pad event within `RightCooldownSeconds` 1.5 s of a right answer is dropped (`D:244, 1332-1338`).

### B8a. RIGHT answer (`D:1370-1390`) `[seen:headless]` (many auto-right runs); `[seen:Aaron]` start-to-finish walks
- Verdict (anchor 0.5/0.68, `VerdictSeconds` 1.5 s, `U:174`): green check texture 240x240 over **"CORRECT!"** (Lime 96 px), or **"N IN A ROW!"**
  when streak >= 2 (`D:1377, 1384`; `U:662-669`).
- Cue: first try `correct` (stock SkilledInteract_Success 1.20 s); after a miss `correct_retry` (SkilledInteract_Good 0.30 s) (`D:1383`).
- Health + shield refilled to full on every stage cleared (`D:1475`, `RefreshVitals 1872`; Aaron 2026-10-08).
- `Cleanse`: mud/dizzy stop at once, `LastRight` set (`D:1341-1350`).
- Split recorded; pace delta shown (B9). Stage += 1; next question drawn and shown; music bed swaps if the tier changed (`D:1471-1483`).
- That door's barrier is added to the player's ignore list (invisible and passable for them only) + cue `door_open` (SlidingDoor_Open 1.57 s); the player
  runs on into the connector (`D:1484-1487`). No stall.
- Explanation: **"Correct!  <explanation>"** (LightGreen 28 px) for `CorrectFeedbackSeconds` 4.0 s (`D:1389-1391`). It is set **after** `ShowCurrent`
  (which clears feedback), so it appears **under the NEXT question's tiles**. In the boss arena the same line was changed to **"Last one:  <expl>"**
  on 2026-10-11 for exactly that reason (`D:2321`, `fnm_bossmode.verse:57`); the 10 stations still say "Correct!". `[code]`
- Explanations are <= 115 chars in the shipped data (max over 11 skills), 2 lines at the 1120 px wrap.

### B8b. WRONG answer (`D:1392-1405`) - one random penalty of 6 (`D:1491-1495`, pool = `map.json` penalties)
- `MissedCurrent = true`, streak = 0, boost stopped (`D:1393-1395`). No time is added to the clock; the cost is the penalty + the walk back.
- Cue `wrong` (stock Target_Error 0.77 s) at 0; the penalty's voice line `PenaltyVoiceDelaySeconds` **0.9 s later** (`D:522, 1678`).
- Verdict: red cross over the penalty label (**FROZEN! / YEET! / SPIKED! / STUCK IN MUD! / DIZZY! / LIGHTS OUT!**, Red 96 px, 1.5 s) (`fnm_penalties.verse:20-26`).
- Feedback (Tomato 28 px): the **misconception text of the chosen wrong choice** (<= 80 chars; "Check your arithmetic." for a generic distractor) shown
  during the penalty **plus 4.0 s** after it returns (`D:1401-1405`). It does **not** reveal the right answer.
- Public feed to everyone: **"<Name> got frozen / yeeted / spiked / stuck in the mud / dizzy / blacked out at station N"** (`D:1398`, `fnm_penalties.verse:29-35`).
- The question and the **letter order stay the same** for the retry (Order only re-shuffles on a new draw, `D:1280-1288`). Retry right = no streak, no first-try credit,
  chime `correct_retry`, no boost.
- Penalty table (all happen in/after the vestibule; all end back at the station entry unless noted):

| Penalty | Mechanism | Hold / duration | Visual (player / others) | Sound | Status |
|---|---|---|---|---|---|
| Freeze | stasis (no turning) where they stand, orbit cam 9 m out, walls see-through; ice cube prop (0.9x0.9x1.05) at feet; frost PP (in 0.3 s, out 0.8 s) | `FreezeSeconds` **5.0 s** then teleport to entry (`D:1672-1687, 251`) | frosted screen; others see an ice block on you | Trap_IceBlock_Placed 1.89 s + voice "Frozen!" | `[seen:Aaron]` 10-04 ("all work") |
| Yeet | pulled 5 m in front of the door wall (0.4 s), tilted air vent (50 deg) under feet, hop +40 cm, vent 0.4 s | ~1.8 s to launch, flight up to 6 s (0.9 s / 18.4 m back seen, `LAYOUT.md:262`); lands anywhere in their own hall = carry on from there, else entry (`D:1688-1719`) | thrown backwards down the hall; others see the vent | Cube_LaunchPlayer 2.67 s + "Yeet!" | `[seen:Aaron]` 10-04 |
| Spike | 6 spears ring (r 55 cm) rise 250 cm in 0.12 s, stasis 0.05 s, `Damage(1000)` = elimination, spears held 1.0 s; wait for respawn (poll 0.25 s, max 20 s); then `WatchLife` -> entry + pistol only | ~0.2 + 1.0 + respawn wait (seen 8 polls = 2 s) + 0.3 ~= **3.5 s** (`D:1747-1780`, `GOALS line 28`) | wide cam; Fortnite's own death view; others see spears | DestructionObject_Impact 2.84 s + "Spiked!" | `[seen:Aaron]` 10-04 |
| Mud | back to entry at once; movement modulator speed **0.5**, re-applied every 2.5 s (its own duration is 3 s); sepia PP (in 0.3, out 0.8) | `MudSeconds` **8.0 s**, ended early by any right answer (`D:1720-1726, 1793-1803`) | brown screen | ExplodingBarrel_Explode_Stink 2.82 s + "Stuck in the mud!" | `[seen:headless]` 10-04; Aaron's 10-04 walk: "all work (Mud not drawn that run)" |
| Dizzy | back to entry; stasis; teleport-in-place yaw steps 0.05 s: 2 full turns in 1.5 s; then radial-blur pulses 0.7 s in / 0.7 s out | spin **1.5 s** hold; blur until 6 s elapsed (5 pulses ~ 7 s), free movement during blur; cleared early by a right answer (`D:1727-1733, 1817-1853`) | spinning view, blur | GhostMode_Enter 2.04 s + "Dizzy!" | `[seen:headless]` frames at ~10 fps; smoothness at full fps **unverified**; Aaron 10-04 "confusing, not dizzying" -> rebuilt |
| Blackout | stasis (no turning), full-screen black `color_block` opacity 1.0 (HUD stays on top of it), then teleport + release | **3.0 s** + 0.5 s (`D:1734-1745, 275`) | black; feedback text readable | ActionTrigger_PowerOff 1.45 s + "Lights out!" | `[seen:headless]` 10-04; Aaron's comment on the new penalties that day was about Dizzy only |

- Forced-hold average over the pool of 6 (my arithmetic from the table): (5.0 + 1.8 + 3.5 + 0 + 1.5 + 3.5) / 6 ~= **2.6 s** of no control, plus Mud's 8 s at half speed
  (~4 s of lost running time, spread over 6 -> +0.7 s) and Dizzy's 7 s blur. Plus the walk back: **25.5 m** from the landing to the door wall again
  (Yeet: ~7 m less), through the same obstacles and the same living guards. `[code]` Real elapsed time depends on run speed, which no repo file records.

### B9. Streak, boost, pace (`D:1373-1382, 2195-2238, 2765-2785`)
- First-try right answers build the streak. Streak 1: boost 3 s. Boost length = min(7, 3 + (streak-1)) s -> 3, 4, 5, 6, 7 s (`D:1380`, `BoostSeconds 3`,
  `StreakBonusSeconds 1`, `MaxBoostSeconds 7`). Speed multiplier **2.0x** (`build_rigs.py:67-70`; Aaron 2026-10-04 could not feel 1.6x). Modulator re-applied every 2.5 s.
- Slate line (Orange 40 px, bottom of the slate): **"STREAK x3  -  SPEED BOOST 4s"**, **"SPEED BOOST 3s"** (streak 1), **"STREAK x3"** (boost over) - counts down per second
  (`D:2195-2199, 2222`). `[seen:headless]`; Aaron 10-04 "couldn't notice the streak" -> moved big onto the slate.
- Sound: streak 2..7 voice lines at +0.9 s after the chime ("Double!", "Triple!", "Mega streak!", "Ultra streak!", "Monster streak!", "UNSTOPPABLE!"; streak 8+ repeats
  UNSTOPPABLE) (`D:1378-1379`, `A:178-185`, manifest). Streak 1 gets the 3.5 s Speed boost whoosh at +0.4 s (suppressed at streak >= 2) (`D:2210-2211`).
- Feed: "<Name> is on a 3 / 5 / 7 / 10 streak!" (`D:1381-1382`).
- A wrong door ends streak and boost. An elimination ends only the boost (`D:1007-1008`).
- Pace: a right answer's split (race-clock time) is stored; delta vs the target splits shown under the target line: **"-1.8 s"** LightGreen (ahead, real minus sign),
  **"+3.2 s"** Tomato (behind), 30 px (`D:2781-2785`, `U:129`). Persists until the next right answer, cleared at each countdown. `[seen:headless]` ahead (-3.1 s run 2); **behind/red
  never seen in play**.

### B10. Connectors (`BC:94-124`, LAYOUT.md:30-57)
- 10 m wide corridor, funnel 6 m in/out, tier-coloured walls, white floor. Types and per-hop path length (my calc from constants): straight 38 m + 1 plate;
  stairs 27 m (16 steps x 25 cm over 8 m, +/-4 m); winding 47 m (two 45 deg jogs, 17 m sideways); long straight 44 m + 2 plates before the arena.
- Speed plates: visible movement modulators, speed 1.8 for 3 s + 2000 forward impulse + 300 up, 513 cm square (`BC:122-127`).
- Variation requested by Aaron 2026-10-04; walked 2026-10-05: **"a lot more engaging"** `[seen:Aaron]`.

### B11. Elimination (guard / spike) - see B6, B8b.

### B12. Station 10's right door -> arena stage 11 (`D:1476-1477, 2287-2296`)
- At the answer: `EnterArena` runs while the kid is still in the vestibule, ~44 m from the arena: question redrawn from the **hardest tier**, music T5, cue `boss_fight` (Stinger_Threat
  7.36 s, stock), public feed **"<Name> reached the boss!"**, **big gold flash "STEP ON THE RIGHT ANSWER PAD!" (96 px, 4.0 s)**, and an orange hint line **"Bullets can't hurt it.
  Step on the floor pad (A-D) with the right answer: that is a hit!"** - but `HandleDoor` then sets "Correct!  <stage-10 explanation>" over the hint in the same tick
  (`D:1389` runs after `D:2295`), so the hint line is replaced. `[code]` GOALS line 304-306 records "Seen: the hint frame at arena entry" on 2026-10-07 for the then-current code; no note shows whether
  the hint survives the current ordering.
- Stage caption: **"BOSS  -  hits 0/5  -  step on the right answer pad"** (`D:1294`) - the hits are the *player's own*; the bar shows *team* hits.
- Verdict for stage 10's right answer is overwritten by the gold flash (FlashBig bumps `VerdictGeneration`). `[code]`
- Boss summon starts as soon as one player is at stage 11 (`D:2528-2543`, 0.25 s loop; boss respawn 4 s after the last kill).

### B13. Boss arena loop (`D:2306-2345, 2348-2385`, LAYOUT.md:73-127, BOSS_MODE.md 16)
- Hall 30 m, tier-5 walls. Entry at 1.5 m (land 4.5 m). Four 4.5 m square pads: A (+700 X, 800 Y) B (-700, 800) C (+700, 2200) D (-700, 2200) (+X = player's left),
  each in its letter colour with a 3 m floating 3D letter (scale 1.5, base 2.3 m, bobbing 40 cm / 4 s, turns to the nearest player) (`BC:176-183`, `build_race_boss.py:70-76`).
  Trigger senses the whole tile, 150 cm tall (`BC:529`). A/B pads are 3.5 m from the landing; C/D 17.5 m.
- Boss: hidden Megabrute on a 6x4 m, 1 m platform at Y 2600, health 100000, only a pad's damage counts (20000 a hit), pinned; over it the **Magma Titan at scale 2.1 (6.3 m tall)**
  (Meshy model, 4 animation clips: idle, flail, stomp, fall); two Meshy mega cannons (scale 3) at X +/-780, Y 2700 with cyan lights and a coil crackle (`D:581, 652`, LAYOUT.md:111-125).
- Boss bar (bottom centre, 688x52 gold frame, 680x44 red fill, name Gold 32 px, value White 30 px): **"THE MAGMA TITAN   -   FINAL BOSS"** with **"60%   -   team hits 2/5"** on
  the bar; **"THE BOSS IS COMING ..."** while none is up; **"DEFEATED!"** 3 s after the kill (`D:2403-2412`, `U:112-115, 525-530`).
- Right pad = 1 team hit (`BossHitsToKill` 5): verdict **"DIRECT HIT!  N TO GO"** (check texture, Lime), cue `boss_hit` (barrel explosion 3.97 s), announcer counted line 0.9 s later
  ("Direct hit! Four/Three/Two to go!", "Direct hit! One more hit!"; no line on the killing hit) (`D:2369-2372`), 3 shots per cannon (muzzle charge 0.15 s, laser 0.15 + 0.35 + 0.08 s) -> ~1.7 s volley,
  strike + blast at the titan's feet (`FireCannons`), knock + 0.8 s stun, titan flails 4 s then stomps 2.67 s (`D:2601-2680`, `fnm_titan.verse:36-39`); **the player is teleported back
  to the arena entry at once** and gets the next tier-5 question (`D:2373-2385`). HUD bar flashes white/gold x3 (`U:748-757`).
- Explanation of a right pad: **"Last one:  <explanation>"** (LightGreen 28 px) after `ExplainDelaySeconds` **2.5 s**, shown 4.0 s; skipped if they answered again/finished (`D:2316-2324`).
  `[seen:headless]` (every explanation up 2.4-2.5 s after its hit).
- Wrong pad = the normal penalty (back to the arena entry; Yeet/Freeze/Spike etc. as B8b) **plus** the adds: a spawner brings 2 pistol guards up (only reset when fewer than 2 are up)
  and the titan stomps (`D:2326-2341, 2429-2442`). Feed **"<Name> got <past> by the boss"**. `[seen:headless]` 2026-10-11 (Spike on pad 3 eliminated the player; Aaron has not seen the race finale since the Titan).
- Shooting the boss: heals every non-pad hit, gives the shooter an orange notice **"Bullets can't hurt it! Step on the pad with the RIGHT ANSWER"** at most every 6 s (`D:2482-2489`).
- A hit when the boss is **not up** still plays "DIRECT HIT!  5 TO GO", sends the player back, redraws the question, and deals no damage (`D:2366-2367`). `[code]`
- Minimum solo: 5 right pads (5 more tier-5 questions) after the 10 stations = **15 right answers** per run, plus retries.

### B14. Kill -> FINISH (`D:2497-2522`, `FinishPlayer D:1905-1972`)
- 5th team hit -> boss eliminated -> for every player at stage 11: arena gate added to their ignore list, `FinishPlayer`, cue `boss_dead` (stinger 6.14 s) at once and voice **"BOSS DOWN!"** 1.0 s later;
  titan flails 1.5 s then falls (3 s) (`fnm_titan.verse:112-121`). **The clock stops at the kill, in the arena** (not at the victory area). Feed: "<Name> landed the final hit!".
- Finish board (hung from the top: anchor 0.5/0.0, Top 130, 62%-black panel, **captures no input**, `U:150-164, 344-353, 461-469`):
  - **"FINISH!"** (72 px) and **"GOLD MEDAL" / "SILVER MEDAL" / "BRONZE MEDAL"** (52 px), both in Gold/Silver/Peru (`D:1935`).
  - "Your time   1:23.4" (White 44)
  - "Your best   1:20.0   NEW BEST!" (Aqua 36; tag only if there was an earlier best and this beats it)
  - "Island record   1:10.2  by <Name>   NEW RECORD!" (Gold 36)
  - "First-try accuracy: 7 / 10 (70%)   -   Best streak 5" (LightGreen 30)
  - "TOP TIMES THIS SESSION  -  <skill title>" (Gold 34) + up to 5 rows "1.  <Name>   1:23.4" (White 32; own row Orange)
  - bottom line (Gold 30): **"Walk on!   NEW RACE  /  CHANGE SKILL  at the podium ahead"**
- Clock keeps the final time (SetClock) and stops; target/delta/streak lines cleared (`D:1937-1941`).
- Sounds, `FinishCueGapSeconds` **1.6 s** apart (`D:2900-2912`): `finish` (Match_Win 3.93 s) -> [new_record "NEW ISLAND RECORD!" 1.75 s, else new_best "New personal best!" 1.54 s]
  -> medal ("Gold/Silver/Bronze medal!" ~1.1 s, plus the stock sting) -> `perfect` "Flawless! Perfect run!" 1.73 s if 10/10. Music beds off.
  **On the arena kill these play on top of `boss_dead` (6.14 s) and "BOSS DOWN!" (+1.0 s)** - up to 4 sounds in the first 3 s. `[code]` `[seen:headless]` for the individual cues; by ear none.
- Feed: "<Name> finished in 1:23.4  (GOLD)"; if island record "<Name> set the island record  1:10.2" (`D:1955-1957`).
- Medal rule (`L:118-121`): GOLD = first-try correct >= 10 (all 10 stations); SILVER = >= 70% (7/10); BRONZE otherwise. **Arena answers do not count; time does not matter.**
- NEW BEST rule (`D:1918-1922`): not a Partial (debug-start) run and (no best yet or faster). Saved to Verse persistence per cartridge id with splits.
- NEW RECORD rule (`D:1923-1930`): the session board for that skill is empty or the time is faster than row 0. **The first finisher of a session on any skill always gets "NEW RECORD!"
  + the record voice + the public feed line** (the board is per session, in memory). `[seen:headless]` (every first log run "new record yes").

### B15. Walk to the victory area
- Board hides itself after `ResultsSeconds` **10.0 s** (`D:434, 1975-1979`); then the target line under the clock reads **"Race again: NEW RACE at the podium"**
  (Orange 30, `D:2035`) and stays there. Walk from a kid standing at the arena entry: ~26 m to the gate, 22 m connector, ~9 m of the 15 m finish hall to the podium (6 m before the end wall)
  -> **~55-60 m** (my calc from constants) - at a sprint around 6 m/s (assumed, not in the repo) ~10 s, about as long as the board stays up. `[code]`
- Finish hallway: a gold "100" over the end, flowers, fireworks props behind the end wall, an **ALL-TIME BEST** billboard screen across the end wall
  (title billboard "ALL-TIME BEST", skill heading, 6 rows; `tools/build_finish.py:20-37, 79-85`). Decor was first seen only in editor captures (GOALS line 98-100); torches burning, ice dressing,
  the podium and the ALL-TIME screen were then seen in play 2026-10-05 (GOALS line 101-104, LAYOUT.md:285); chalkboard text is not confirmed in play. The screen lists **players on the island right now**
  by saved best, cycles skills every 8 s, holds a just-finished skill 16 s (`D:2050-2060, 1962`).

### B16. Podium (`D:1984-2045`, `tools/build_finish.py:87-93`)
- Two lecterns 6 m in front of the end wall, 3.2 m either side of centre, each with a button (E, reach 0.6) and a label billboard "NEW RACE" (player's left) /
  "CHANGE SKILL" (right). The E prompt reads **"Race again"** / **"Change skill"** (`D:1986, 1990`).
- NEW RACE: same skill, no picker -> station 1, countdown 3-2-1 (`StartNewRun D:2142-2161`). Pressed before finishing: orange **"Finish the race first!"** 2 s (`D:2023`).
- CHANGE SKILL: back to station 1 in stasis and the picker again (`D:1235-1265`); personal bests stay per skill.
- **No auto-restart on the shipped map** (the 12 s "Next run in N" restart only runs when the map has no podium buttons, `D:1964-1967, 2128-2138`). `[seen:Aaron]` podium 2026-10-05, 10-06 walked.
  A kid who does nothing stays in the victory area forever.

---------------------------------------------------------------------------------------------------------------------

## 2. Station-by-station table (shipped values)

Tier = `1 + (2(s-1)(T-1) + (S-1)) div (2(S-1))` with T=5 tiers, S=10 (`L:23-27`) -> 1,1,2,2,3,3,4,4,5,5. Wall colour per tier green/blue/purple/orange/red (DEEP_MEMORY:17).
Hall start position for the obstacle distances: 0 = hall start; landing at 450 cm; door wall at 3000 cm; first obstacle >= 900 cm.

| # | Tier | Connector before it (`BC:105-117`, path incl. 12 m funnels) | Floor level | Obstacles (`BC:79-90`) | Guards x weapon (`build_guards.py:26, 43-53`) | Pickups (`build_pickups.py:57-65, 112-125`) | Special |
|---|---|---|---|---|---|---|---|
| 1 | 1 | none (start; every join/new run is teleported here) | 0 | none | 1 x pistol (blue) | none | warm-up |
| 2 | 1 | straight, 1 speed plate @30% (38 m) | 0 | hurdle @1400 | 1 x SMG (blue) | Boogie L / Shockwave R | |
| 3 | 2 | stairs up 4 m, 16 steps (27 m) | 400 | baffleL @1000, baffleR @1800 | 2 x SMG (purple) | Slap Splash (heal 30) both walls | |
| 4 | 2 | winding left, two 45 deg jogs (47 m) | 400 | hurdle @1000, hurdle @1800 | 2 x pump shotgun (purple) | Shockwave L / Boogie R | |
| 5 | 3 | stairs up 4 m (27 m) | 800 | slider @1400 (container, from left) | 3 x combat shotgun (purple) | Slap Splash both walls | |
| 6 | 3 | straight, 2 plates @25%,70% (38 m) "into the ice station" | 800 | baffleL @950, hurdle @1450, baffleR @1950 | 3 x heavy shotgun (purple) | Boogie L / Shockwave R | **ICE**: pale-blue floor, sign "STATION 6 - ICE!", friction 0.05, accel cap 500, braking stays 800; icicles, snowflakes, snow piles, snowman, ice statues; guns fire on it (`bAllowWeaponFire`) |
| 7 | 4 | winding right (47 m) | 800 | baffleL @900, baffleR @1450, baffleL @2000 (3-baffle slalom) | 4 x bolt-action sniper (purple) | Slap Splash both walls | |
| 8 | 4 | stairs down 4 m (27 m) | 400 | slider @1000, sliderR @1800 | 4 x heavy sniper (gold) | Shockwave L / Boogie R | |
| 9 | 5 | winding left (47 m) | 400 | baffleL @950, slider @1450, baffleR @1950 | 5 x grenade launcher (gold) | Slap Splash both walls | |
| 10 | 5 | stairs down 4 m (27 m) | 0 | slider @950, hurdle @1450, sliderR @1950 | 5 x rocket launcher (gold) | Boogie L / Shockwave R | |
| Arena (stage 11) | 5 (hardest) | straight 32 m, 2 plates @20%,60% (44 m) | 0 | none (4 pads, platform, cannons) | adds only: 2 x pistol, on a wrong pad | none | Magma Titan boss, 5 team hits |
| Finish hall | - | 10 m straight (22 m) from the arena gate | 0 | none | none | none | 15 m hall, ALL-TIME screen, podium |

Facts about the obstacles: hurdle = 70 cm gold bar, full width, 40 cm thick (walking stops at it, run + jump clears it; Aaron 10-04 "hurdles great" `[seen:Aaron]`); baffle = 600 cm wall
from one side leaving a 900 cm gap (`BAFFLE_GAP`); slider = 607 cm shipping container sweeping +/-790 cm in 2.2 s (7.2 m/s), 0.5 s pause each end, period 5.4 s, identical phase for every player
(`D:421-425, 2241-2248`). **What a hit by a container does to a player: not checked** (GOALS line 52). The code comment at `BC:86` labels the 3-baffle
slalom "the ice station", but the list index is station - 1, so that row is station 7; station 6 (ice, `BC:131`) is baffle/hurdle/baffle (comment drift).
Obstacles are re-met after every wrong door (all penalties but Yeet return the kid to the 450 cm landing; Yeet lands them ~8 m in), and the guards remain.

Pickup pad detail: 4 pads per wall at 480-780 cm from hall start, 150 cm in from the wall; Item Spawner pads, run-over, 1 grenade, respawn 8 s; hidden row trigger and item granter guarantee the item
(or drop at feet when the bag is full) (`build_pickups.py:11-21, 69-93`). Station 1 and the arena have none. `[seen:Aaron/headless]`: stocked pads, "Boogie Bomb x1" in inventory (2026-10-06);
**drop-at-feet on a real full bag, a thrown item on another player: not seen**.

Total path (my calc from constants, `BC` + connectors): 10 x 37.65 m stations + 369 m of connectors + 30.4 m arena + 22 m connector + 15 m finish = **~813 m walked path**, ~792 m of Y extent;
LAYOUT.md:9 still says "about 740 m" (written before the arena/finish hall).

---------------------------------------------------------------------------------------------------------------------

## 3. Feedback systems with numbers

### 3.1 Right answer
- Verdict check + "CORRECT!" / "N IN A ROW!" 1.5 s; chime (1.20 s first try, 0.30 s retry); door_open 1.57 s; explanation 4.0 s ("Correct!  ..." under the next question);
  vitals to full; boost 2.0x for 3-7 s; streak voice +0.9 s; feed at streak 3/5/7/10. Cooldown: next door/pad event ignored for 1.5 s.

### 3.2 Wrong answer
- See the B8b table. Retry keeps question and letter order. No clock penalty. Public feed names the player and the penalty.

### 3.3 Streak / boost
- Thresholds: streak shown at >= 2 ("STREAK xN"), boost on every first-try right (length 3..7 s), voices at 2..7, feed at 3/5/7/10 (B9). Streak never resets between stations or runs
  except a wrong door, a new run, a skill change; elimination keeps it (`D:1007-1008, 1247-1249, 2150-2152`).

### 3.4 Pace deltas / splits
- Splits saved per right answer (`D:2767-2778`); the run's splits are stored with the time only if there are exactly 10 (`D:1914`). Target = session island record's splits (shows "Record m:ss.t")
  else the player's own saved best splits (target line "Beat m:ss.t"). A "Beat" line can show with no pace target (a best exists, no splits) -> no delta (`D:2757-2763`).
  The Record target vanishes with the session (board is in-memory); saved bests persist (unverified across sessions).

### 3.5 Race strip (`D:2794-2866`, `U:130-141, 355-373`)
- Left panel under the delta: heading **"RACE"** (Aqua 24) + up to 8 rows (White 24; own row Gold), refreshed every `RaceSeconds` 0.5 s; hidden while picking.
  Order: finished (fastest first, row tail **"FIN 1:23.4"**), boss-mode players ("BOSS L2"), racers by station furthest-first then less clock, then **"picking"**, then **"lobby"**.
  Own row prefix **"YOU  station 4"**; others **"<Name>  station 4"**. With > 8 players: top 7 + the viewer. A kid in the arena shows as "station 10". `[seen:headless]` single-player; **ordering with 2+ players not seen**.

### 3.6 Public feed (`U:143-147, 377-386, 784-817`; `D:2788-2791`)
- Top right under the minimap (Right 20, Top 348), 3 lines max, newest on top, 26 px White right-justified, 55%-black backing, each line 7.0 s. Broadcast to **every** HUD
  (including players mid-picker). Lines: penalty (all six), finish with medal, island record, streak 3/5/7/10, skip, "reached the boss!", "got <penalty> by the boss", "landed the final hit!".
  `[seen:headless]` ("got frozen / yeeted at station 1"); the skip feed and red delta were **not seen**.

### 3.7 Medals, bests, records, boards
- Medal: first-try correct / 10 stations (B14). Personal best = per skill, min(session, persisted); "NEW BEST!" tag only when beating an earlier best. Island record = best time on the
  *session* board for that skill (in-memory, so it resets every UEFN session). Session board = best per player, 5 rows (`BoardSize`), shown on the finish board.
- Persistence: `fnm_saved` (`fnm_save.verse:9-35`): per player, `BestTimes[cartridge id]` and `BestSplits[...]`; written on every new best. The all-time screen reads it for players present.
  **Unverified** whether a published/private version keeps it between sessions; "each new UEFN play session started with no saved best" (GOALS line 105-107).
- Debug-start ("Partial") runs are never recorded (`D:1926-1930`).

### 3.8 Cooldowns / timers (shipped)
| What | Value | Source |
|---|---|---|
| Countdown beats | 3 x 0.8 s, GO! 1.0 s | D:428, 2181 |
| Verdict flash | 1.5 s | U:174 |
| Wrong feedback line | penalty + 4.0 s | D:238, 1404 |
| Right explanation (stations) | 4.0 s | D:242 |
| Arena explanation delay / show | 2.5 s / 4.0 s | D:593, 2318-2323 |
| Notices ("No choice D here", "not your station", gun hint, eliminated) | 2.0 s | D:463 |
| Door event dropped after a right answer | 1.5 s | D:244 |
| Door backstop dwell / poll | 0.4 s / 0.25 s | D:444, 456 |
| Guard check / guard spawn timer | 1.0 s / 1.0 s per guard | D:459, build_guards.py:61 |
| Pad respawn / row grant rate limit | 8 s / 3 s per row per player | build_pickups.py:71, D:606 |
| Boost reapply / mud reapply | 2.5 s | D:257, 417 |
| Finish cue gap | 1.6 s | D:518 |
| Penalty voice delay | 0.9 s after the buzzer | D:522 |
| Finish board visible | 10.0 s | D:434 |
| All-time screen cycle / hold after a finish | 8 s / 16 s | D:440, 1962 |
| Feed line | 7.0 s | U:147 |
| Gun hint repeat | 6.0 s | D:534 |
| Boss respawn after a kill | 4.0 s | D:537 |
| Boss "stuck spawn" re-pulse | 5 s | D:2544 |
| Rival strip refresh | 0.5 s | D:525 |

### 3.9 Sound inventory (per player only: Instigator-Only audio players, flat 2D, `AUDIO.md:13-28`)
- 65 of 65 cues wired as of 2026-10-09 (46 race/shared cues, 29 of them voiced with am_michael on 2026-10-08, plus the 19 boss-mode cues; GOALS line 275-276, memory notes 2026-10-08/09). `[seen:headless]` wiring + cross-correlation (GO 0.96, WELCOME 0.74-0.77, penalty lines 0.90-0.94 after the fix); **the six hit-count lines and the finish/medal lines were not judged by ear**.
- Stock sounds (all from `/Game/Sounds/Creative` or `/CRD_SkilledInteractionDevice`): `AUDIO.md:35-74` (table in the source). Music beds 5 loops at volume 0.5, on at GO, swap when the tier changes (every 2 stations), off at picker/finish.
- Announcer lines used by the race: Welcome "Welcome to Fortnite Math!", Choose "Choose your grade and your skill.", Go "Go!", "Guards ahead!", "Double!/Triple!/Mega streak!/Ultra streak!/Monster streak!/UNSTOPPABLE!",
  "Flawless! Perfect run!", "New personal best!", "NEW ISLAND RECORD!", "Gold/Silver/Bronze medal!", "Frozen!/Spiked!/Stuck in the mud!/Dizzy!/Lights out!/Yeet!", "No skipping!",
  "Direct hit!", "Direct hit! Four/Three/Two to go!", "Direct hit! One more hit!", "BOSS DOWN!" (tools/audio/announcer/manifest.json). Voice volume 2.5 (`build_audio.py:48`).
- Aaron's Fortnite *Music* slider is 0 on his PC, so the beds are inaudible to his account (AUDIO.md:185-186). `[seen]` rig fact.

---------------------------------------------------------------------------------------------------------------------

## 4. Multiplayer and social surfaces

Island: Cooperative team (no friendly fire), Down-But-Not-Out off, building none, environment damage off, join-in-progress Spawn Immediately, max players 16, respawn 1 s (`build_island.py:42-49`, GOALS line 162-170).
**Two or more real players have never played the race** (GOALS line 170, 253; boss mode likewise). Everything below is `[code]` unless stated.

| Surface | What a player sees of others / what is shared |
|---|---|
| World | Other avatars in the same halls (stations are sequential but kids spread across them); a frozen kid is an **ice block visible to all**; spear rings, air vent props are world props visible to all; guard spawner/guards are **shared per station** (a guard one kid kills stays dead for the others until the station empties); shipping containers sweep with one global phase; pickup pads are shared (first to arrive takes the grenade, 8 s respawn); the arena Titan/Megabrute and its 5 hits are **shared** across everyone at stage 11, one kill finishes all of them. |
| Per-player (private) | The question, the letter shuffle, the HUD, sounds, music, screen effects (frost, sepia, blur, blackout), the barrier opening (invisible/passable only to the answerer), ice friction, boost, vitals, pace target. A neighbour's right door stays solid for you. |
| Left panel RACE strip | Names + "station N" / "FIN m:ss.t" / "picking" / "lobby" for everyone on the island, 8 rows. |
| Public feed (top right, 7 s) | Every kid's penalties ("got frozen at station 4"), finishes with medal, island records, streaks, skips, boss events - to every HUD. |
| Finish board | "Top times this session" for the skill you chose (best per player, 5 rows) and the island record holder's name. Different skills are never mixed. |
| Victory area | ALL-TIME BEST screen of everyone present, per skill, cycling; podium buttons are shared devices but act on the presser's own state. |
| Items | Boogie Bomb / Shockwave Grenade intended "to use on each other" (Aaron 10-06); effects on a second real player **unverified**. Cooperative team means no damage between kids. Guard-dropped weapons fill your own slots. |
| Social exposure | The feed publicly names who got a wrong-door penalty; the strip shows who is behind. |

---------------------------------------------------------------------------------------------------------------------

## 5. Numbers

- **Questions per run**: 10 course stations + 5 arena hits = 15 right answers minimum; a wrong door repeats the same question (it does not draw a new one). Items are drawn without replacement per player
  per tier (`L:61-70`): tiers 1-4 use 2 items per run (40 items last 20 runs), tier 5 uses 7 per run (2 stations + 5 arena; 40 items last 5 full runs, the deck reshuffles during the 6th). `[code]`
- **Course length**: ~813 m walked path (section 2). Hallway 30 m from the 4.5 m landing = 25.5 m of run + 7 m vestibule; connectors 27-47 m.
- **Typical run time**: **no human run time is recorded anywhere**: no number for Aaron's 2026-10-04 "completed once". Logs kept (UnrealEditorFortnite*.log, 2026-10-08 to 2026-10-13): every `FNM: finished run` is a scripted
  run: "1:26.6" / "1:29.8" (auto-right, one teleport per door + 6 s sleeps, GOLD 10/10), "0:29.6" (arena-only DebugStartStage 11, Partial), and one "309:53.3" line (2026-10-08 23:05 UTC, first-try 7/10) from a headless
  session left idling while a guard killed the stuck player every ~2.5 min. These say nothing about kids. A rough bound (assumption, not repo data): ~813 m at ~6 m/s sprint is ~2.3 min of pure running before reading,
  guards, obstacles, penalties; the 2x boost and 1.8x plates shorten it.
- **Wrong door cost**: forced hold average ~2.6 s (+ Mud/Dizzy impairment) plus a 25.5 m re-walk (Yeet: ~7 m less) with obstacles and guards; no clock penalty, but the streak and boost are lost (boost 2x for 3-7 s) (B8b). A blind guesser over
  4 doors meets 1.5 wrong doors per question on average ((4-1)/2), since the letters do not reshuffle on a retry.
- **Time to first play after joining**: no wait. Join -> picker immediately -> 2 clicks -> 2.4 s countdown -> GO. (Fortnite client/cook/matchmaking time is outside the repo.)
- **Distractor feedback quality** (data): across the 11 skills, 17% of all 6549 wrong choices are generic `ARITH` ("Check your arithmetic."): order-of-ops 39%, integer-ops 27%, area-volume 20%, others 5-22% (my count over `baked.json`).
- Tests: 8746 green at 2026-10-11 (memory note); 6 stale boss tests were fixed 687a42d.

---------------------------------------------------------------------------------------------------------------------

## 6. Aaron's playtest feedback (verbatim where the repo has the words) and what happened

Source in brackets. "Fixed" = built and seen in play unless noted; "open" = still listed open/unverified. Items marked (boss) are boss-mode-only.

| Date | Aaron said | What was done | Status |
|---|---|---|---|
| 2026-10-03 | G4 brief: replace room-and-teleport with a race, hallways ending in walls of real doors; right door opens onto the next hallway "with no stall"; wrong door = surprise penalty; big red X / green CORRECT! (GOALS G4 line 21-23, paraphrase); "success must never stall" (LAYOUT.md:60) | Course v2, barriers per player, penalty pool | Fixed `[seen:Aaron]` |
| 2026-10-03 | (sank into the entry pad after a wrong door; "a centred X hid the spears") | `SendTo` +300/+100; verdict to lower third | Fixed, "confirmed in play" (DEEP_MEMORY:21) |
| 2026-10-04 | (Dizzy was) "confusing, not dizzying"; wanted blurred vision in and out, wobble | 1.5 s spin + radial-blur pulses | Rebuilt; smoothness at full fps **open** |
| 2026-10-04 | Spike death lagged the spears (1.2 s) | near-instant (0.12 s + 0.05 s) | Fixed |
| 2026-10-04 | could not feel the 1.6x speed boost (`build_rigs.py:66`) | 2.0x | Built; Aaron's re-test of 2.0x is **open** (GOALS line 127-129) |
| 2026-10-04 | obstacles "feel good, harder with multi-step problems and guards but achievable; hurdles great"; "Couldn't notice the streak (one finish)"; time vs personal best vs island record "not obvious"; wants top scores on the big finish screen | Big streak line on the slate; centre finish board with time/best/record+holder/top 5 | Fixed `[seen:headless]` |
| 2026-10-04 | hurdles: "would recommend additional variation" | - | **Open** (GOALS line 108) |
| 2026-10-04 | guards: "good"; dropped guns fill slots, fine; wants progressively better weapons so the player ends up with them | WEAPONS ladder; 10-06 re-ramped after "boring" | Fixed; balance "Aaron's call" |
| 2026-10-04 | skill choice "like a load-in lobby: choose grade level, then the skill" (G5) | HUD picker (Fortnite has no pre-game lobby) | Fixed `[seen:headless]` real clicks |
| 2026-10-04 | "as long as they can do the concept correctly, that's what I want to know. Some of these current order of operations I can't do in my head and resort to guessing; I don't want people to pull out a calculator." (memory) | PROTOCOL 4a simple-numbers bounds; rebake | Fixed |
| 2026-10-04 | "best Order of Operations on the default map" (never compare skills) | bests/boards/records keyed per skill | Fixed |
| 2026-10-04/05 | "hallways sometimes up stairs, down stairs, winding to left, winding to right, sometimes straight"; speed plates; one icy area | connectors, plates, ice station 6 | Walked 10-05: **"a lot more engaging"** `[seen:Aaron]`; ice subtle at 0.15 |
| 2026-10-05 | "sometimes I run through a door and correct or incorrect doesn't activate, I run around that room a little and eventually it does" (D:1409) | `WatchDoors` backstop | Fixed `[seen:headless]` |
| 2026-10-05 | "after enough runs it would just become memorization" (PROTOCOL:95) | choices shuffled per showing | Fixed |
| 2026-10-05 | "doable in head, even topic related" (PROTOCOL 4b); "torches have no fire"; "icy floors should have indication of icy conditions"; "x it and enjoy themself in the victory area" (finish board / CLOSE) | non-integer bounds; lit torches; ice dressing; victory area + all-time screen | Fixed `[seen]`; torch flames seen after 10-05 |
| 2026-10-05 | Class demo on Xbox via private version | codes 7346-5901-9394, 8564-2561-9374 uploaded | **Open**: never seen running |
| 2026-10-06 | "words are cut off" (10-skill picker step) -> "looks much better" | title + 22 px caption, two columns | Fixed `[seen:Aaron]` |
| 2026-10-06 | (door still did nothing until he ran round the room, 1-2 doors per run) | trigger 680 cm deep, backstop watches whole vestibule | Fixed `[seen:headless]`; **not re-walked** |
| 2026-10-06 | finish board popped up at once and locked him out of the victory area; "non icy levels have icy properties"; guard weapons "boring" | board captures no input, hides after 10 s; ice device add-on-start off + director removes; blue->gold ladder | Fixed `[seen:headless]` |
| 2026-10-06 | "add a ceiling with collision so players can't launch out and over ... maybe transparent" -> 10-08 "make the glass top completely transparent, it's obscuring some things I'd like to see" | lids, then invisible | Fixed; shockwave vs lid **unseen** |
| 2026-10-06 | "check that this game will work for multiplayer, because it is a race, I would love for 4 or more players" (build_island.py) | island settings, 7 spawn pads | Applied; 2+ real players **never tested** |
| 2026-10-06 | players pick up Boogie Bombs and Shockwave Grenades to use on each other | pickup pads | Built; use on others **unverified** |
| 2026-10-07 | "players should be able to pick up chug splashes" (build_pickups.py:50) | no Chug Splash item exists; Slap Splash (heal 30) odd stations from 3 | Built; pads **not picked up in play** |
| 2026-10-07 | "weapons cannot fire on the ice level" | mutator zone `bAllowWeaponFire` true | Fixed in place; not walked |
| 2026-10-07 | "couldn't hear an announcer"; later "I did hear most game sounds ... shots, slamming door" | voice buried under buzzer: volume 2.5, +0.9 s delay, etc. | **Open until he says**; his Music slider is 0 |
| 2026-10-07 | "couldn't beat the final boss" (zero pad events in 2 min) | STEP ON THE RIGHT ANSWER PAD flash + hint, pads 1.5x, weaker SMG boss; 10-09 trigger refit | Fixed `[seen:headless]` |
| 2026-10-07 | "absolutely love these ideas" (G6 fun layer) | sounds, announcer, rivals strip, feed, boss arena | Built |
| 2026-10-08 | "couldn't barely make it past stage 10 until the guards had killed themselves from the blasts"; "every time a player makes it through a stage they should have health and shield refreshed to full" | vitals refreshed per stage; cannons; hit-count announcer | Fixed |
| 2026-10-08 | "epic laser cannon blast the boss and the boss flail or get knocked back"; "make the hit more clear verbally ... 'direct hit!' and how many hits remaining"; "the grenades disappear" | cannons, announcer count lines, row-trigger item granters | Fixed; real full-bag drop **unverified** |
| 2026-10-08 | the floating question and answers "feels like alpha version... clunky" | HUD slate with chalk texture and door-coloured tiles | Built `[seen:headless]`; slate wrapping cases **open** (G7 1a) |
| 2026-10-08 | "make the doors the same colors as the letters and styling for each answer, and place the letters on the doors" | letter painted into the door texture | **Not yet seen in play** |
| 2026-10-09 | parallelogram slanted side "useless information" | removed | Fixed |
| 2026-10-09 | "spawned new guards and soldiers on every death" | adds reset only when < 2 up | Fixed (reasoned, kill-stays-down not seen) |
| 2026-10-09 | "fix the race arena pads too" | `trigger_fit`; `--triggers-only` 44 read back | Fixed `[seen:headless]` |
| 2026-10-10 | "sometimes i think im getting an incorrect answer debuff even though its right and counted right" | `Cleanse` + 1.5 s cooldown | Fixed `[seen:headless]` |
| 2026-10-10 | "yes delay the explanation" (boss) | 2.5 s `ExplainDelaySeconds` | Fixed; 10-11 "Last one:" prefix |
| 2026-10-10/11 | (boss) "make boss bigger and more epic model ... hard to even tell he is the boss", cannons "not styled or cool at all", "match up the boss fight in the end of race with our best learnings and improvements from arena" | Magma Titan, mega cannons, Niagara FX, bar, letters in the race finale | Fixed `[seen:headless]`; **Aaron has not seen the race finale**, no private version |

Other open playtest asks: GOALS lines 127-129, 154-156 ("Aaron playtest of the 2026-10-04 evening build ... / 2026-10-06 build: walk into the victory area while the board shows, then the podium; is station 6 slippery
enough (ONLY station 6); do the launcher stations play; the finish board's new position legible?").

---------------------------------------------------------------------------------------------------------------------

## 7. Known gaps

### 7a. Marked open / unverified in the repo
1. Private version predates almost everything; Xbox class demo never seen (GOALS line 92-97, memory).
2. Two+ real players: strip order, feed, shared guards/boss, item use on others, Cooperative team, `bCanBeDamaged` false vs rockets (GOALS line 170, 253, 386, memory).
3. All-time bests persisting across sessions (GOALS line 105-107). Round time limit (5 min default, override off) not confirmed on a published version (GOALS line 171-172).
4. Ice position poll (`WatchIce`/`IsInVolume`) unverified in play; station 6 slipperiness and "only station 6" not re-walked (GOALS line 157-161, 154).
5. Door paint with letters not seen in play; wall frame stays white; slate edge cases (two-line prompt / explanation growing over the lintel; stage caption sits ~80 px in from the rim) (GOALS line 349-352, 357-360).
6. "Performance Warning: See editor" HUD message seen twice (first on a throttled client); never explained (GOALS line 37, 208).
7. Dizzy spin smoothness at full fps; red delta; skip feed; 5-row board + spacing; announcer lines by ear (6 voice lines unverified); streak7 under arena music; drop-at-feet on a full bag; thrown items; hidden lid vs Shockwave jump.
8. Race finale: Titan stomp pose on a wrong pad unconfirmed; shooter heal; Megabrute reach to pads C/D (20 s probe: no damage); adds staying dead after a kill reasoned not seen (memory, BOSS_MODE.md:795-796).
9. Cook/runtime memory at 11 cartridges unproven (PROTOCOL O4, GOALS line 16); one run on a new grade-6 skill in play not done; Aaron's content review of grade 6 not done; **grade 7 has one skill, grade 8 none** (GOALS line 16-18).
10. Hurdle variation and the weapons/traps backlog (GOALS line 108-111); G6 items 4-10 (agency, modes, traversal variety, XP, comedy escalation) are unbuilt.

### 7b. Observations from reading the code (not previously logged; flagged as observations, not design advice)
1. **Welcome and Choose voice lines fire in the same tick** (`D:1083` then `D:1137`), both announcer voice, so two lines overlap at join. `[code]`
2. **No HUD or world text teaches the controls**: nothing says doors open with E, that walking in commits an answer, that guards can be shot, or that a hurdle needs run + jump. Only the arena has instructions. `[code]`
3. **Picker has no timeout/default and freezes the player**; the BOSS BATTLE mode button sits above the race grades with a gameplay-different promise. `[code]`
4. **Inconsistent copy for the same event**: stations say "Correct!  <old explanation>" under the *next* question (`D:1389`), the arena says "Last one:  ..." (fixed there on 2026-10-11 because it misread). The verdict says "CORRECT!"; the voice (unused) "Correct!"; podium prompt "Race again"; label "NEW RACE"; line "Race again: NEW RACE at the podium"; old board "Next run in N". `[code]`
5. **Wrong-door feedback shows a misconception line but never the right answer or the worked explanation**, and 17% of wrong choices (39% on Order of Operations) only say "Check your arithmetic." Some stock lines name fixed numbers that do not match the question (e.g. "3^2 means 3 x 3, not 3 x 2." appeared on a `(15 - ...)^2` item in my sample; the same sample showed "Skipped the parentheses" on `(5 - 3 + 3)^2`). `[code]` (data in `cartridges/*/baked.json`)
6. **Letters do not reshuffle on a retry**, and nothing is lost for guessing except the penalty's hold time and the first-try credit; with 4 doors a random guesser needs on average 1.5 wrong doors per question. Medals are accuracy-only, time never matters. `[code]`
7. **Dead / waiting time**: Freeze 5 s with no turning, Blackout 3.5 s, Spike respawn wait (up to 20 s polled; 2 s seen), countdown 2.4 s + 1 s on every run, boss spawn pulse and "THE BOSS IS COMING ..." with no way to act, picker with no end. The arena can idle for 4+ s before a boss exists if another kid just killed one. `[code]`
8. **A right pad before the boss is up counts as a "DIRECT HIT!  5 TO GO" but deals no damage** (`D:2366-2367`). `[code]`
9. **Arena entry is announced ~44 m early**: `EnterArena` fires at the stage-10 answer (stinger 7.36 s, big flash 4 s, bar "THE BOSS IS COMING ...", titan stomp) while the kid is still in the vestibule/connector; the orange hint line is overwritten in the same tick; the stage-10 CORRECT! verdict is replaced by the gold flash. `[code]`
10. **Finish board timing vs geography**: the run finishes at the kill in the arena and the board stays only 10 s while the kid still has ~55-60 m to the podium, with up to four finish/boss sounds stacked in the first 3 s. After it hides the only on-screen instruction is the orange "Race again: NEW RACE at the podium" line. No auto-restart; a kid who never presses E is left in the victory area. `[code]`
11. **First finisher of every session on a skill gets "NEW RECORD!"** plus a public feed line (record is the in-memory session board), which inflates the cue for a class's first finishers. `[seen:headless]` ("new record yes" on every first run in the logs).
12. **Public feed names kids with their penalties**, and the strip shows who is last. Social exposure for 11-14 year olds. `[code]`
13. **Pickup pads start 30 cm past where kids land** (480 vs 450 cm), so a kid auto-picks grenades on the first steps of stations 2,4,6,8,10. Boogie Bomb / Shockwave are meant "to use on each other" on a Cooperative-team island; whether they affect teammates is unverified. `[code]`
14. **Gold sniper / grenade-launcher / rocket-launcher guards at stations 8-10** (counts 4, 5, 5), noted in GOALS as "balance is Aaron's call". Health and shield refill on every right answer and on respawn (`GiveLoadout`), but a respawn returns only the pistol. `[seen:Aaron]` for the earlier "barely make it past stage 10" report; the fix is `[seen:headless]`.
15. **Music is a per-tier loop**, but Aaron's Fortnite Music slider is 0 so his account never hears it, and his first "couldn't hear an announcer" (2026-10-07) was voice lines buried under the buzzer and effect sounds (fixed by volume 2.5 and a 0.9 s delay; his confirmation is still open). `[seen]`
16. **Station-comment drift**: `BC:86` says the slalom is "the ice station" but it belongs to station 7; ice station 6 has baffle/hurdle/baffle (hurdle on ice). LAYOUT.md:9 length "about 740 m" predates the arena. Low UX relevance, relevant when reading the docs. `[code]`
17. **Missing-letter doors** (2/3-choice items, 12/200 and 27/200 items) still look and open like normal coloured doors, then say "No choice D here". `[code]`
18. **Retry geometry**: every wrong door is followed by the full re-run of the hall including obstacles and living guards; on station 10 that means five rocket-launcher guards again, for a math mistake. `[code]`

---------------------------------------------------------------------------------------------------------------------

## 8. Sample questions (what a kid reads; `cartridges/<id>/baked.json`)

Format: prompt | choices (A-D as baked; **the game shuffles the letters per showing**) | answer | explanation (shown after the right door) | feedback for one wrong choice (shown after a wrong door).
Slot = 5 tiers x 40 items per skill; the tier is chosen by station (section 2). Station names in the caption are the tier names below.

### Order of Operations - Exponents & Parentheses (grade 6, v1.2.0)
Tiers: 1 Warm-up, 2 Parentheses, 3 Exponents, 4 Power Moves, 5 Boss Level.
- T1 `9 + 6 × 4` | 33 / 60 / 37 / 38 | **A 33** | "6 × 4 = 24, then 9 + 24 = 33." | B 60: "Added or subtracted too early. × and ÷ come first."
- T1 `19 − 3 × 6` | 5 / 11 / 1 / 96 | **C 1** | "3 × 6 = 18, then 19 − 18 = 1." | A 5: "Check your arithmetic."
- T1 `17 − 5 + 5` | 17 / 7 / 13 / 12 | **A 17** | "17 − 5 = 12, then 12 + 5 = 17." | B 7: "+ and − are a team: go left to right between them."
- T2 `20 − (3 + 9)` | 3 / 26 / 8 / 10 | **C 8** | "3 + 9 = 12, then 20 − 12 = 8." | A 3: "Check your arithmetic."
- T2 `5 × (8 − 3) − 10` | 5 / 15 / 27 / 14 | **B 15** | "8 − 3 = 5, then 5 × 5 = 25, then 25 − 10 = 15."
- T2 `8 ÷ 4 × (8 − 7)` | 9 / 0 / 4 / 2 | **D 2** | "8 − 7 = 1, then 8 ÷ 4 = 2, then 2 × 1 = 2." | A 9: "Skipped the parentheses. Do what's inside them first."
- T3 `5^2 − 4 ÷ 2` | 23 / 26 / 8 / 3 | **A 23** | "5^2 = 25, then 4 ÷ 2 = 2, then 25 − 2 = 23."
- T3 `4 − 2 + 9^2` | 121 / 22 / 20 / 83 | **D 83** | "9^2 = 81, then 4 − 2 = 2, then 2 + 81 = 83." | A 121: "Worked left to right. Do × and ÷ before + and −."
- T3 `3^3 − 6 ÷ 3` | 23 / 25 / 7 / 1 | **B 25** | "3^3 = 27, then 6 ÷ 3 = 2, then 27 − 2 = 25."
- T4 `(24 ÷ 8)^3` | 27 / 9 / 17 / 1 | **A 27** | "24 ÷ 8 = 3, then 3^3 = 27." | B 9: "3^2 means 3 × 3, not 3 × 2."
- T4 `(6 ÷ 3)^3` | 18 / 8 / 6 / 12 | **B 8** | "6 ÷ 3 = 2, then 2^3 = 8."
- T4 `(5 − 3 + 3)^2` | 11 / 1 / 10 / 25 | **D 25** | "5 − 3 = 2, then 2 + 3 = 5, then 5^2 = 25." | A 11: "Skipped the parentheses. Do what's inside them first."
- T5 `(15 − (9 − 3 + 8) ÷ 2)^2` | 16 / 256 / 5 / 64 | **D 64** | "9 − 3 = 6, then 6 + 8 = 14, then 14 ÷ 2 = 7, then 15 − 7 = 8, then 8^2 = 64." | A 16: "3^2 means 3 × 3, not 3 × 2."
- T5 `(7 + (8 ÷ 2 − 3))^2` | 2 / 64 / 1 / 16 | **B 64** | "8 ÷ 2 = 4, then 4 − 3 = 1, then 7 + 1 = 8, then 8^2 = 64."
- T5 `(9 ÷ 3 − 2 + (5 − 4))^3` | 8 / 10 / 0 / 6 | **A 8** | "5 − 4 = 1, then 9 ÷ 3 = 3, then 3 − 2 = 1, then 1 + 1 = 2, then 2^3 = 8."

### Ratios & Rates - Equivalent Ratios, Unit Rates, Percent (grade 6, v1.0.0)
Tiers: 1 Ratio Language, 2 Equivalent Ratios, 3 Unit Rates & Units, 4 Percent of a Number, 5 Parts, Wholes & Rates.
- T1 `10 pets: 3 are cats, the rest dogs. Ratio of cats to dogs?` | 7:3 / 3:10 / 7:10 / 3:7 | **D 3:7** | "Dogs: 10 − 3 = 7. Cats to dogs is 3:7." | A 7:3: "Order matters: write the first thing named first."
- T1 `For every 5 cars there are 6 vans. Ratio of vans to cars?` | 6:11 / 5:11 / 6:5 / 5:6 | **C 6:5** | "Vans first, then cars: 6 to 5 is 6:5." | A 6:11: "It asks part to part. Compare the two groups, not a group to the total."
- T2 `6:8 = ?:80` | 60 / 78 / 10 / 800 | **A 60** | "8 × 10 = 80, so 6 × 10 = 60. 6:8 = 60:80." | B 78: "Ratios grow by multiplying, not adding. Times both numbers by the same amount."
- T2 `Slime: 10 glue to 4 water. Glue for 40 water?` | 100 / 10 / 400 / 46 | **A 100** | "4 × 10 = 40, so 10 × 10 = 100." | B 10: "That is only the first step. Use that number to finish."
- T3 `4 points in 2 games. Points per game?` | 1/2 / 8 / 4 / 2 | **D 2** | "4 points ÷ 2 games = 2 points per game." | A 1/2: "Divided the wrong way. Per 1 means divide the total by the count."
- T3 `7 tickets cost $21. Cost per ticket?` | $2 / $1/3 / $147 / $3 | **D $3** | "$21 ÷ 7 = $3 per ticket." | A $2: "Check your arithmetic."
- T4 `What is 70% of 30?` | 3 / 70 / 21 / 23 | **C 21** | "10% of 30 is 3, so 70% is 7 × 3 = 21." | A 3: "Dividing by 10 gives 10%. Then scale it to the percent asked."
- T4 `50% of 60 kids ride a bus. How many?` | 10 / 30 / 6 / 50 | **B 30** | "10% of 60 is 6, so 50% is 5 × 6 = 30." | A 10: "Percent of means a share of the whole, not whole minus the percent."
- T5 `5 pens cost $25. Cost of 8 pens?` | $200 / $40 / $5 / $28 | **B $40** | "$25 ÷ 5 = $5 per pen. 8 × $5 = $40." | A $200: "Find the price of 1 first: total price ÷ how many."
- T5 `Boys:girls is 6:2. 56 kids in all. How many girls?` | 14 / 12 / 42 / 7 | **A 14** | "6 + 2 = 8 parts. 56 ÷ 8 = 7 per part. Girls: 2 × 7 = 14." | B 12: "Check your arithmetic."
- T5 `Boys:girls is 2:5. 14 kids in all. How many girls?` | 35 / 2 / 4 / 10 | **D 10** | "2 + 5 = 7 parts. 14 ÷ 7 = 2 per part. Girls: 5 × 2 = 10."

### Data & Statistics - Mean, Median, Range, MAD (grade 6, v1.0.0) - includes the 2-choice case
Tiers: 1 Range & Mode, 2 Median, 3 Mean, 4 Missing Value & Outliers, 5 Mean Absolute Deviation.
- T1 `Find the mode: 3, 3, 17, 17, 20, 17, 17` | 4 / 20 / 3 / 17 | **D 17** | "17 shows up 4 times, more than any other value (3 shows up 2 times). Mode = 17." | A 4: "That's how many times it shows up. The mode is the value itself."
- T2 `Find the median: 4, 14, 8, 1` | 11 / 4 / 8 / 6 | **D 6** | "In order: 1, 4, 8, 14. Middle two 4 and 8: (4 + 8) ÷ 2 = 6." | A 11: "Put the numbers in order first, then find the middle."
- T3 `Find the mean: 1, 0, 14, 9` | 24 / 8 / 5 / 6 | **D 6** | "1 + 0 + 14 + 9 = 24, and 24 ÷ 4 = 6." | A 24: "Add them up, then divide by how many numbers there are."
- T4 `The mean of 0, 2, 20, 5, ? is 9. What is ?` | 9 / 18 / 19 / 45 | **B 18** | "Total = 9 × 5 = 45. Known: 0 + 2 + 20 + 5 = 27. 45 − 27 = 18." | A 9: "The ? is not the mean. Find the total, then take away the others."
- T4 (2 choices: doors C and D show "No choice C here") `New value 20 joins 1, 3, 7, 9. Which changes less?` | Mean / Median | **B Median** | "Mean 5 to 8, median 5 to 7. The far-off 20 pulls the mean a lot; the median barely moves." | A Mean: "A far-off value pulls the mean a lot. The median barely moves."
- T5 `Mean absolute deviation (MAD): 0, 1, 14` | 14 / 5 / 18 / 6 | **D 6** | "Mean 15 ÷ 3 = 5. Distances 5, 4, 9 sum to 18. 18 ÷ 3 = 6." | A 14: "MAD is the average distance from the mean, not largest − smallest."

Data note: that T4 explanation says "Mean 5 to 8, median 5 to 7" for `1, 3, 7, 9` + 20 (as baked). Other facts: prompt max 60 chars, choice max 14 chars, explanation <= 115 chars in shipped data; all text ASCII plus × ÷ − ^ (PROTOCOL 5).
Tier-5 difficulty for the arena: the same tier-5 pool as stations 9-10.

---------------------------------------------------------------------------------------------------------------------

## Appendix A. Commit history of the race (git log, 81 commits)

2026-10-03 course v2 (cbd91bc), penalties and rigs (f2a958f, a475227), Yeet/Freeze fixes (05b63bf, ba57256) -> 10-04 race layer + obstacles (b54e87a), playtest round 1 (6e0b1c6),
guards (c5328e8), picker (905b756, 43d6ca3), course v3 stairs/winds/ice (36c3a92) -> 10-05 door backstop + shuffle (3c95397), grade-6 library (20bcca5), decor (bd428c0), victory area/torches/ice dressing (95d1987) -> 10-06 pickups + skip guard (36c78af), door dead spot (f14bfc3),
picker captions (159a9a9), finish board + ice + weapons + multiplayer (b69bed5), glass lids (adf8bde) -> 10-07 sound layer (7b1364b), announcer (2a1241c), rivals strip/pace/feed (fdc84e0), boss arena (96ad846), playtest
fixes (6da8def), announcer audible (8c38aa7) -> 10-08 slate HUD (ec64d90), arena cannons/vitals/pickup grants (7950724, 2d5bc31), door colours + invisible lids (69cfb4d) -> 10-09 door paint (fb38d7d), arena pads (6895eb6),
boss mode (8457fd6 ...) -> 10-10/11 titan, cannons, FX (bd2a1ac, f40eeb7, 687a42d) -> 10-11 race finale gets the titan (b65ce65), "Last one:" (0a4cc45).

## Appendix B. Key file index
`console/verse/fnm_director.verse` (runtime), `fnm_ui.verse` (HUD), `fnm_logic.verse`, `fnm_audio.verse`, `fnm_penalties.verse`, `fnm_save.verse`, `fnm_fx.verse`, `fnm_titan.verse`; `tools/build_course.py`
(OBSTACLES `:79`, CONNECTORS `:106`, ICE_STATIONS `:131`, arena `:510`), `build_guards.py` (GUARDS `:26`, WEAPONS `:43`), `build_pickups.py`, `build_decor.py`, `build_finish.py`, `build_race_boss.py`, `build_rigs.py`,
`build_audio.py`, `build_island.py`; docs `console/AUDIO.md`, `PENALTIES.md`, `README.md`, `maps/starter/LAYOUT.md`, `PROTOCOL.md`, `GOALS.md`, `BOSS_MODE.md` §16, `cartridges/LIBRARY.md`.
