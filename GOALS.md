# GOALS

## ✅ G1 — Cartridge protocol v1 — archived to DEEP_MEMORY.md (2026-10-03)

## ✅ G2 — First map in UEFN — done 2026-10-04, archived to DEEP_MEMORY.md (2026-10-04)

## G3 — More cartridges
- [x] Second topic `integer-ops` (grade 7) — plugged in with zero toolchain changes
- [x] Grade-6 library (2026-10-05): 9 new cartridges, 200 items each — ratios-rates, fraction-division, decimal-ops,
  factors-multiples, rational-numbers, expressions, equations-inequalities, area-volume, data-statistics. Plan and
  standards that do not fit multiple choice: `cartridges/LIBRARY.md`. Non-integer bounds: PROTOCOL §4b. Slot now 11
  cartridges (972 KB), compiles clean in UEFN. Picker shows a step with > 5 skills in two columns
- [x] 2026-10-06: the 10-skill grade-6 step ran off the screen (Aaron: "words are cut off"). Stock buttons grow to
  their label at a fixed font, so a skill button now carries the title only, with the subtitle as a 22px caption
  under it (`MakeCell` in fnm_ui.verse). Aaron: "looks much better"
- [ ] One run on a new grade-6 skill in play. Cook/runtime memory at 11 cartridges unproven (PROTOCOL O4)
- [ ] Aaron content review of the grade-6 library (emulator: `emulator/` with the regenerated carts.js)
- [ ] Grade 7 and 8 libraries

## G4 — Race course (Aaron, 2026-10-03)
Replace the room-and-teleport loop with a race: long hallways ending in walls of real doors the player opens.
The right door opens onto the next hallway with no stall. A wrong door triggers a surprise penalty from the
map's pool. Big red X / green CORRECT! flash. Later: obstacles, weapons, traps. Penalty catalog: `console/PENALTIES.md`.
- [x] Penalty runtime: random pick from the map's pool; Freeze and Spike live; big verdict flash; right answer moves on at once
- [x] Players start at station 1 facing the doors (Play-From-Here ignores the requested spawn point)
- [x] Penalty visuals (2026-10-03, seen in play): ice block around a frozen player, a spear ring bursting up for Spike, an air-vent launch for Yeet (rigs: `tools/build_rigs.py`)
- [x] Yeet launches for real (air vent moved under the player, ~75 m skydive); back at the station entry on landing
- [x] Spike respawn wait no longer races the elimination (polls start after the damage; "after 8 polls" in play)
- [x] Aaron playtest of the penalties by walking through wrong doors (2026-10-04): all work (Mud not drawn that run)
- [x] Course layout v2 (2026-10-03): 30 m hallways, real doors, vestibule triggers, per-player barrier passage
  (`AddToIgnoreList`). Verified in play via debug hooks: right door → walk through into the next hallway;
  a closed barrier blocks; penalties on the new course. No `lock_device` needed (doors are plain props).
- [x] Aaron playtest of v2 start to finish (2026-10-04): completed once; door C's whole wall stood out, so all doors
  now share one look and the coloured letters tell them apart (`build_course.py --doors-only`, 2026-10-04; letters seen in play)
- [x] Door C is now a dark stone bank wall with a wooden door (oil-rig "Green" rendered blue like B)
- [x] Every door type opens with E in play and its trigger fires on the way through (A, C, D tested 2026-10-03)
- [ ] One test session showed "Performance Warning: See editor" on the HUD (nothing in the editor log; seen once
  in four runs). Not seen again in ~12 sessions on 2026-10-04 and not in any log; watch item. UEFN's memory panel
  is GUI-only
- [x] Map profile chooses its penalty pool (map.json `penalties` → generated `FnmMapPenalties`, PROTOCOL §6a)
- [x] More penalties (2026-10-04, all seen in play): Mud (slowed + sepia), Dizzy (colour swirl), Blackout (black
  screen, wake at entry); Freeze also frosts the screen. Catalog: `console/PENALTIES.md`
- [x] Verdict check mark / cross as textures (`tools/import_art.py`), seen in play; verdict moved to the lower third so
  it no longer covers the player
- [x] Aaron playtest of the new penalties (2026-10-04): Dizzy was confusing, not dizzying. Wanted: blurred vision
  coming in and out, spinning/wobble. Built 2026-10-04: two spins on the spot (character `TeleportTo` yaw steps) then
  `PP_RadialBlur` pulsed in/out for 6 s; seen in frames from a background-throttled client (~10 fps), so whether the
  spin is smooth at full fps is unverified (`DizzySpinStepSeconds` 0.033 if it strobes). A real camera wobble is not
  exposed to Verse as far as we know
- [x] Obstacles (2026-10-04, seen in play): gold 70 cm hurdles (walking stops at one, run+jump clears it), baffle
  walls, shipping containers sliding across the hallway (Verse `Slide`, `fnm_slider`); harder per station
  (`OBSTACLES` in `tools/build_course.py`). Not checked: what a sliding container does to a player it hits
- [x] Race layer (2026-10-04, seen in play via debug hooks): 3-2-1-GO countdown, race clock (left, under GAME MODE),
  streak ("4 IN A ROW!") + speed boost on first-try right answers, FINISH + GOLD/SILVER/BRONZE medal + time +
  personal best + island record, then an automatic new run 12 s later. Boost speed (1.6x) not yet felt in play
- [x] Aaron playtest of the race layer and obstacles (2026-10-04): obstacles feel good, harder with multi-step problems
  and guards but achievable; hurdles great. Couldn't notice the streak (one finish). Time vs personal best vs island
  record not obvious; wants top scores on the big finish screen. Building: big streak line, streak survives guard
  deaths, boost 2.0x, a centre finish board with your time / best / island record (holder's name) / top 5 session
  times / next-run countdown. Built and seen in play 2026-10-04 (two auto-right runs: NEW BEST!, NEW RECORD!, one
  row per player). Board is per session only
- [x] Course v3, vertical and horizontal variety (Aaron, 2026-10-04: "hallways sometimes up stairs, down stairs,
  winding left, winding right, sometimes straight", speed plates on straights, one icy area). Connector corridors
  between stations (`CONNECTORS` in `tools/build_course.py`, table in `maps/starter/LAYOUT.md`): stairs up 4 m twice,
  down twice, three 45° winding jogs, three straights with speed plates; course now ~740 m, levels 0/4/8 m. Station 6
  is ICE (`ICE_STATIONS`): pale floor, mutator zone + player movement device, friction 0.15 (braking not settable
  from MCP). Sliders now slide along their own axis (`SliderTravel`). Seen in play 2026-10-04: two auto-right runs
  through all 10 relocated stations to the finish, "on ice"/"off ice" fire at station 6, a container sweeps its
  moved hallway. Seen in editor captures: stairs, winding walls, plate arrows facing down the corridor
- [ ] Aaron playtest of course v3, walking it (needs a real player; the auto-run teleports past connectors): stairs,
  plates and ice were walked 2026-10-05 ("a lot more engaging"; ice at 0.15 felt subtle, rebuilt at 0.05 on
  2026-10-06, see below). Still open: does a Yeet on a raised hallway land well
- [x] Aaron playtest of course v3 (2026-10-05): "a lot more engaging". Two notes, both built and seen in play
  2026-10-05: (1) sometimes a door did not answer until he ran around the vestibule. A trigger fires only on
  entering its zone and the director drops an event while the player is Busy; a position backstop (`WatchDoors`)
  now answers for a player standing in a door zone 0.6 s with no answer taken. Proof: with every trigger event
  ignored (`DebugIgnoreTriggerEvents`) two auto-right runs finished on the backstop alone (20/20 doors); with events
  on it fired 0 times. The original cause is not pinned down: logs before the fix do not record trigger events.
  (2) Anti-memorization: the choices of every question are shuffled each time it is shown (PROTOCOL §3 note), so
  the right door moves. Seen: baked `6 + 2 × 4` answer is choice A, shown as B, and the run used door B
- [x] 2026-10-06 (Aaron: a right door still did nothing until he ran around the room, 1-2 doors per run). Cause pinned
  from the live editor: the vestibule triggers were 60% of the vestibule (420 of 700 cm), so a player who ran or
  jumped through the door and stopped against the barrier stood in a 280 cm dead spot past the trigger box, and
  `WatchDoors` mirrored that box, so nothing answered until they walked back into it (his 2026-10-06 run log has
  no "answered by position" line at all). Reproduced headless: `DebugAutoRightOffsetY` 350 (drop 350 cm past the
  trigger centre) stuck at stage 1. Fixed: `WatchDoors` watches the whole vestibule (trigger front face to the
  barrier) and dwell 0.4 s; triggers now `TRIGGER_DEPTH` = 680 cm (`build_course.py --triggers-only`, applied
  in place, bounds read back). Proof: same drop with the fix, 10/10 answered by position, run finished; drop 250
  cm past the resized trigger's centre, the trigger itself fired at 8/10 stations within 60 ms and the backstop
  took the other 2 within 1 s (a teleport-in can miss the overlap; a walk-in is the normal path). Not yet walked
  by Aaron; private version 9216-2361-9000 does not contain it
- [ ] Class demo on Xbox (Aaron, 2026-10-05): private version code via UEFN Publish Project, played on his account
  - Private version uploaded 2026-10-05 06:36: code **7346-5901-9394** (Creator Portal > FortniteMath > Publishing >
    Private Versions). Not yet seen running on the Xbox. Public release still needs the Fortnite Developer Terms (Enroll)
  - Private version **8564-2561-9374** uploaded 2026-10-07 by Aaron (Project > Launch Memory Calculation is the upload; no
    separate Publish step). Should carry adf8bde (lids, pickups + skip guard, door fix, picker captions, finish board, ice
    fix, weapons, island settings); nothing in it seen in play yet. 9216-2361-9000 is now the previous version
- [x] Decor pass (Aaron 2026-10-05, editor only, no play session): station numbers, torches, chalkboards, plants,
  floating sky digits, finish "100" (`tools/build_decor.py`, LAYOUT.md). Seen in editor captures. Not seen in play:
  torch flames, fireworks, chalk text (billboard text does not render in the editor viewport)
- [x] Aaron playtest notes (2026-10-05), built and seen in play the same evening: torches now burn
  (`BP_TRV_ALight_Torch_02_CP`); the ice station has icicles, giant snowflakes, ice blocks, snow piles, a snowman
  and ice statues; the finish board stays until CLOSE; podium NEW RACE / CHANGE SKILL buttons (real E press
  started run 2); an ALL-TIME BEST screen on the end wall (`tools/build_finish.py`)
- [ ] All-time bests across sessions: saved with Verse persistence and read back within a session (the screen shows
  them), but each new UEFN play session started with no saved best. Unverified whether a published/private
  version keeps them between sessions (expected: yes; UEFN test sessions may not)
- [ ] Hurdle variation as we polish (Aaron 2026-10-04: "would recommend additional variation")
- [ ] Leaderboard that persists across sessions (today's board is per session; per-player best could use
  `persistable`, an island-wide board needs a different store)
- [ ] Weapons / traps in the hallways (G4 "later"; guard drops now supply weapons, traps still open)
- [x] Pickup pads (Aaron 2026-10-06, `tools/build_pickups.py`): Boogie Bombs along one wall and Shockwave Grenades along
  the other of every even station (sides swap per station), four pads a side, run-over pickup, 8 s respawn. A director
  skip guard (`WatchSkip`, `DebugSkipTest`) sends a player found in a hallway past their stage back to their own entry,
  since a shockwave clears the 6 m door walls. Seen in play 2026-10-06: pads stocked (the bombs hover in the pad's
  beam), walking across a pad put "Boogie Bomb x1" in the inventory, the guard bounced a stage-1 player dropped at
  station 3 in 0.12 s.
- [ ] Pickups still unverified in play: a thrown Boogie Bomb or Shockwave on another player (needs two players), a
  real shockwave jump over a door wall tripping the skip guard (only the teleport test ran), whether 8 s respawn and
  one grenade per pad suit a class, and whether the overlapping pad bases (100 cm pitch, ~2 m bases) look cluttered.
  The grenade hovers over the pad's centre 150 cm off the wall: a player hugging the wall can run past without
  touching it.
- [x] Glass lids (Aaron 2026-10-06 "ceiling with collision ... maybe transparent", `tools/build_lids.py`): a glass slab
  over every floor piece, staircases sloped, flush with the wall tops; the course is a closed tube and the skip guard
  becomes the backstop. Yeet unchanged under it (18.4 m back, lands at the entry). Open: a real Shockwave jump against
  the glass, Aaron's call on how visible the glass should be (clear gallery glass now; tinted variants exist).
- [ ] Aaron playtest of the 2026-10-04 evening build: Dizzy spin smoothness, the 2.0x boost, the finish board, guard
  weapons at stations 3/5/7/9, identical doors. Claude's own composed play pass is also pending (held while Aaron
  was in Dota: play sessions take the foreground)
- [x] Hostile guards (Aaron, 2026-10-04; seen in play at station 5): a guard spawner per hallway, 1,1,2,2,3,3,4,4,5,5
  guards by station (`tools/build_guards.py`), Wildlife team, low accuracy, health bars, drop their gun. Up only while a
  player is on that station. Any elimination respawns the player at their station's entry with the pistol
- [x] Spike death now lands with the spears (~0.4 s, was ~1.3 s), seen in play
- [x] Aaron playtest of guards (2026-10-04): good. Dropped guns fill the player's slots, fine by him. Wanted:
  progressively better weapons from the guards as stations rise, so the player ends up with them. Built 2026-10-04:
  `WEAPONS` ladder in `tools/build_guards.py` (pistol → suppressed SMG → tactical shotgun → AR UC/R/VR → heavy AR VR)
  through the spawner's `itemList`; seen in play 2026-10-04 (station 7: four guards with rifles, feed "eliminated
  … with a rifle"). Four AR guards killed a standing player in ~6 s from first hit: balance is Aaron's call.
  Stations 1–2 keep the loadout's rare pistol
- [x] Aaron playtest 2026-10-06: the finish board popped up at once and locked him out of the victory area (he saw
  the fireworks from behind it); "subtle" ice on non-ice stations; guard weapons "boring". Built 2026-10-06:
  (1) with a podium the finish board captures no input, hangs from the top of the screen and hides itself after
  `ResultsSeconds` (10 s); NEW RACE / CHANGE SKILL are the podium buttons only (the board keeps its buttons only on a
  map with no podium). Seen headless: board up at the finish, "results closed" 10 s later, run 2 from NEW RACE.
  (2) Ice root cause: the player movement device's `bAddToPlayersOnStart` was on, so EVERY player ran on friction
  0.15 from game start until station 6's exit event took it off — the faint ice on stations 1-5. Off on the device
  (`build_course.py --ice-only`, `ICE_DEVICE`) and in the director (`RemoveFromAll()` at OnBegin, a per-join check
  that logs if it was on, `WatchIce` polling `IsInVolume` every 0.25 s as the backstop for a missed exit event).
  Dialled up: friction 0.05 and a 500 cm/s² acceleration cap while on the ice (`ICE_FEEL`, `ICE_COMMON`); the device
  clamps braking to 800+ and refuses its curves, so the stop stays ~2.5 m from a sprint. (3) Weapons: blue →
  purple → gold, pistol → SMG → pump / combat / heavy shotgun → bolt + heavy sniper → grenade + rocket launcher
  (`WEAPONS`; the 48 ids the spawner accepts are listed in `build_guards.py`, `--probe` tests more). Five guards
  with legendary rocket launchers at station 10: balance is Aaron's call (guard count `GUARDS`, accuracy LOW)
- [ ] Aaron playtest of the 2026-10-06 build: walk into the victory area while the board shows, then the podium;
  is station 6 slippery enough now (and ONLY station 6); do the launcher stations play; the finish board's new
  position (top, 62% black) legible?
- [ ] Ice position poll (`WatchIce` through `mutator_zone_device.IsInVolume`) is UNVERIFIED in play: the headless
  auto-right run never enters the station 6 hallway (it teleports into the door vestibules), and the station-6 start
  session (`DebugStartStage 6`) was killed by the harness for low system memory before it logged anything. Risk if
  `IsInVolume` never succeeds: the poll would take the ice off 0.25 s after the zone's enter event, i.e. no ice at
  all. Check: one `DebugAutoPick 0` + `DebugStartStage 6` session should log one "on ice" and no "off ice"
- [x] Multiplayer pass (`tools/build_island.py`, 2026-10-06; `--check` reports): the director was per player
  already, the island was not. Set: teams Cooperative (was Free For All: classmates could shoot each other with the
  dropped guns; friendly fire already off), Down But Not Out Off (Cooperative's default would make guard kills a
  crawl, not the elimination the director waits for), join in progress Spawn Immediately (was "next round", which
  never comes: late joiners would have spectated forever), environment damage Off and building None (no shooting the
  doors apart, no ramps over the walls; the island hands out infinite materials), five more spawn pads (7; the
  spot at x -750, y 0 has no floor), and `bCanBeDamaged` off on all 295 gallery props. Max players 16, respawn 1 s,
  spawn limit unlimited (override off). Unverified in play: two or more real players; that `bCanBeDamaged` false on
  a gallery prop stops guard rockets (the island setting covers players only)
- [ ] Round time limit reads 5 (minutes, override OFF so the default "none" should apply); nobody has hit a round
  end in sessions longer than 5 minutes, but confirm once on the published version

## Backlog (from 2026-10-02 build audit)
- [x] Order-of-ops 1.1.0: M_BEFORE_D 13, A_BEFORE_S 13 (were 0 / 3)
- [x] Order-of-ops ARITH 53% → 41% via compound misreadings (labelled with first misconception only — playtest whether that feedback reads well)
- [x] integer-ops 1.1.0: T3 ARITH 67% → 34% via MUL_FOR_DIV and ADD_FOR_MUL (review ADD_FOR_MUL's wording: it is
  operation confusion more than a sign rule); T4/T5 drop items with a zero intermediate. Not yet inserted into the map
- [x] Verse root is `<project>/Content/` (verified); `fnm sync starter` works

## G5 — Skill picker and the simple-numbers rule (Aaron, 2026-10-04)
"User chooses the math skill to practice when they first load in, like a load-in lobby: choose grade level, then
the skill." Fortnite has no custom pre-game lobby and islands cannot load content at runtime, so the slot now
holds every inserted cartridge and the choice is an in-game HUD menu per player (PROTOCOL §6b, §7). Standing
content rule from the same conversation: simple numbers, concept over arithmetic (PROTOCOL §4a).
- [x] Compile ceiling checked first: 12 cartridges × 200 items (862 KB) build clean in 2.4 s; disproof with a
  planted unknown identifier reported on line 2606 (PROTOCOL O4). Cook/runtime memory still only proven at the
  real cartridge count
- [x] Toolchain: slot = one `FnmCartridge_<id>()` per baked cartridge + `FnmCartridges()` registry in picker
  order (grade, then title); `fnm insert <id>` emits every baked cartridge; SLOT.txt lists them all;
  `fnm emit` needs no id; `Grade` added to `fnm_cartridge` (§8); lint and tests updated; `build_course.py`
  reads the new SLOT.txt
- [x] Verse (2026-10-04 night): per-player cartridge, grade → skill picker with real `button_loud`/`button_regular`
  widgets on their own `InputMode := All` root, CHANGE SKILL under the finish board, `DebugAutoPick` hook; guards and
  doors ignore a player who is picking; a skill change starts a fresh personal best. Compiles clean (3506 proof);
  headless flow seen in the editor log: `2 cartridges`, `picked integer-ops (grade 7)`, full auto-right run to
  the finish board, `picker shown: 2 grades, 2 skills` at ship values
- [x] Seen in play by Fable (2026-10-04, after Aaron's Dota match; `tools/click_hud.py`): the menu draws centre
  screen with the first button focused; real mouse clicks reach `OnClick` (`grade 7 chosen`, `picked integer-ops`,
  run 1 GO with the Integer Operations title and `−12 + (−11)`); the finish board reads "TOP TIMES THIS SESSION -
  Integer Operations" with CHANGE SKILL clear below it; clicking it logged `change skill`, reopened the menu, and
  grade 6 → Order of Operations started run 3 with `20 − 4 + 4` and no "Beat" target (fresh best for that skill)
- [x] Race times per skill and per map (Aaron, 2026-10-04: "best order of operations on the default map, never
  compare different skills"): personal bests, the session board and the island record are keyed by the cartridge
  (`BestTimes`, `Boards` in the director); the board is headed with the skill title; CHANGE SKILL no longer
  wipes a best, `Pick` restores the chosen skill's. PROTOCOL §6b
- [ ] A 1-row board was seen; the 5-row board + CHANGE SKILL spacing is not (five finishers needed)
- [ ] "Performance Warning: See editor" sat on the HUD for the whole session (background-throttled client); the
  G4 watch item, still nothing in the editor log
- [x] Simple-numbers rebake of both cartridges to 1.2.0 (seeds kept): new per-item bounds tests went red on 130/200
  old order-of-ops items and 105/200 old integer items, green on the rebake; Fable's independent ast re-check of
  all 400 answers and bounds found nothing; no tier near its attempt budget
- [x] Emulator: home screen grouped by grade in §6b order (e2e 13 → 17); "Play again" already existed
- [ ] Aaron playtest: pick a skill on the menu with a real click, finish, change skill; judge the new number
  sizes in play (samples per tier in the 2026-10-04 build report; e.g. T5 `24 ÷ (24 ÷ (6^2 ÷ 9) − 3)`)
- [x] Decision (Aaron, 2026-10-04): boards and bests are per skill and per map, never mixed. Built the same night

## G6 — Fun layer (Aaron, 2026-10-07: "absolutely love these ideas")
Lens: the loop has strong pressure (guards, obstacles, surprise penalties, the clock) and thin reward, spectacle, social
play, agency and sound (the island was silent). Numbered order is the build order. Fable plans and audits; Opus builders
implement from written briefs (`~/.claude/skills/multi-model-delegation`).
- [x] 1a. Sound effects (built 2026-10-07, Opus builder A): 37 cues (`fnm_audio.verse`, `console/AUDIO.md`,
  `tools/build_audio.py`): countdown ticks + GO, correct / retry chimes, wrong, door open, boost, streak milestones
  2..7, finish + new best / record + medal + PERFECT fanfare (spaced 1.2 s), a stinger per penalty, NO SKIPPING, guards
  up, welcome, picker, a music bed per tier. Heard by the instigating player only, 2D. Proven: a headless auto-right
  run logged `audio: 37 of 37 cues wired`, 59 cue lines, and the speaker loopback (`tools/hear.py`) matched 44 of them
  within 0.5 s once the client was unmuted (`tools/audio_meter.py`: the Windows mixer re-mutes the client on a
  session relaunch; Aaron's own Fortnite Music slider is 0, so the beds are silent for his account). Found: only
  `/Game/Sounds/Creative` and `/CRD_SkilledInteractionDevice` sounds pass island validation (Rocket Racing VO, BR
  cues all fail), so the sounds are Creative-library stock. Not yet judged by ear: whether each sound suits its moment
- [x] 1b. Announcer pack (2026-10-07, Opus builder B): 31 lines x 3 voices from local Kokoro TTS (`tools/make_announcer.py`,
  `tools/audio/announcer/<voice>/*.wav`, 48 kHz mono, -13 LUFS, deterministic; QA in `tools/audio/announcer/QA.md`).
  Streak lines DOUBLE / TRIPLE / MEGA / ULTRA / MONSTER / UNSTOPPABLE, penalties, medals, boss + lifeline for later
- [ ] 1c. Announcer into UEFN: Aaron picks the voice (samplers sent; builder's pick am_michael), then the wavs are
  imported through the UEFN Import dialog (no headless path: no auto-import, no `unreal` module in the MCP script
  toolset) and swapped onto the matching cue devices (`CUES` paths) + a pass to decide which moments get the voice
  instead of the stock stinger
- [ ] 2. Live race layer (built 2026-10-07, Opus builder C, commit after aa424c6; NOT yet seen on screen): RACE strip
  under the clock (every player by progress, FIN time / station N / picking / lobby, own row gold), pace deltas per
  right answer vs the island record's splits or your own saved best splits (`Record 1:23` / `Beat 1:23`, green ahead,
  red behind; splits saved per skill in `fnm_save`), public feed top right (penalty past tense, finish, record,
  streak 3/5/7/10, skip). Headless log proves splits, deltas (-3.1 s run 2), feeds and the strip; BuildAll clean,
  8689 tests. The physical pacer orb was dropped: a prop is visible to all, a pace is per player. OPEN: every
  screenshot caught the Fortnite client on LOGIN EXPIRED OR LOGGED IN ELSEWHERE (Aaron's account in use elsewhere,
  likely the Xbox), so unverified: feed position vs the minimap (Top 300), the strip's look, red/behind delta, the
  penalty feed copy, the skip feed, the DeltaCopy sign sabotage. `tools/playtest.py` prints log lines in cp1252 and
  will crash on the delta's real minus sign: run it with PYTHONIOENCODING=utf-8 (fix pending)
- [ ] 3. Boss finale, "math as damage": the finish becomes an arena with a boss guard and a huge health bar; five
  rapid questions, each right door fires a cannon or hands a legendary launcher for 8 s, each wrong one summons adds;
  the run ends on the kill
- [ ] 4. Agency: a gold fifth door at some stations (tier+2 question: skip the next station or eat a nasty penalty); two
  lifelines per run (50/50, a 3 s peek at the explanation for a time cost); coins on the walls and a podium shop
  (shield that eats one penalty, a shockwave, a head start)
- [ ] 5. Modes: team relay (four players, a station each, hand off at the vestibule), survival (endless stations, three
  lives), storm elimination (a storm closes behind the pack), co-op gate (the class needs 100 right answers to open the
  final door, total on the projector)
- [ ] 6. Traversal variety in the connectors: grind rails, ziplines, launch pads, one go-kart straight, a water slide
  instead of stairs
- [ ] 7. Theme: a heist (vault doors, security guards, alarm-system penalties) or tower escape; decor and signage, no
  layout rebuild
- [ ] 8. Progression: persistent XP and ranks with titles ("Bronze Fraction Slayer"), a trophy room, a champion mannequin
  dancing the session winner's emote, a hall-of-fame wall (Verse persistence already carries bests)
- [ ] 9. Comedy escalation from the PENALTIES catalog: trapdoor, boulder, chicken swarm, pinball bumpers, flood; one
  rare jackpot door (1 in 20) that hits the whole class
- [ ] 10. Secrets: hidden rooms behind breakable walls, a collectible coin set with its own board, a developer room
