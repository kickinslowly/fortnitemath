# FNM console runtime -- the device that plays the active cartridge on a linear course of stations.
# Place ONE fnm_director in the level. It finds the course by Verse tags (fnm_tags.verse), so there is
# nothing to wire: tag each station's entry teleporter fnm_station_NN + fnm_entry, each door trigger
# fnm_station_NN + fnm_door_a..d, and the finish teleporter fnm_finish (see console/README.md).
# Optional per door: a barrier_device with the same two tags as its trigger. Then a right answer makes that
# barrier passable for that player alone and they walk on into the next hallway; without one they are
# teleported to the next station's entry.
# Why tags: UEFN 42.30 rejected trigger/teleporter references in this device's @editable arrays from
# both MCP and the Details panel ("is not valid trigger_device"), while tags set cleanly.
#
# Per player: own cartridge, own stage, own question, own HUD, own draw decks (PROTOCOL 6).
# Skill picker (PROTOCOL 6b): the slot holds every inserted cartridge (FnmCartridges(), registry order = grade
# ascending, then title). A joining player is held still at station 1 and picks a grade, then a skill, on a HUD
# menu (real Verse buttons); the grade step is skipped when only one grade exists, the menu when only one
# cartridge does. Then the countdown starts their run. The finish board offers CHANGE SKILL (a fresh personal
# best); otherwise the next run keeps the skill. Guards ignore a player who is picking.
# Test hooks (all @editable, ship values in brackets): DebugAutoPick (-1) picks Cartridges[N] on join with no menu,
# which every other hook needs to run headless; DebugAutoWrongAnswers (0), DebugPassageTest (false), DebugDoorTest
# (-1), DebugAutoRightAnswers (false), DebugVictoryTest (false), DebugStartStage (0), DebugIgnoreTriggerEvents (false), DebugAutoRightOffsetY (0.0),
# DebugAutoBoss (false: a joining player starts BOSS BATTLE with no menu, wins over DebugAutoPick), DebugBossLevel (0: boss
# mode starts at that level, a Partial run), DebugBossHold (0.0: the boss auto-run waits that long before each pad),
# DebugBossChest (0: after each summon, stand every fighter on that perch facing its weapon chest). DebugAutoWrongAnswers N
# with DebugAutoRightAnswers: the auto-right run takes up to two wrong doors at each station of run 1 first, N in all.
# DebugStrikeSelf (false: every strike a player earns is fired at that player, for a one-client test).
# G10 (briefs/g10/D_director.md, 2026-10-14): only a first-try right answer earns anything. The streak line names the next
# reward ("STREAK x2  -  1 more for a SHIELD"). A streak of 3 earns a SHIELD (it takes the next penalty: the player's own
# wrong door or pad, or a strike); 5, 10 and 15 earn a STRIKE fired at the nearest racer ahead (a light in-place effect;
# the leader's becomes a boost). Every station missed (right only after a miss) is queued for REDEMPTION: the arena asks
# its tier first, and a first-try right pad there REDEEMS it (half credit). Medal v2 counts a redeemed station half
# (FnmMedalHalves, today's gates; time gates behind MedalTimeGates), and the finish board adds the brag grid (fnm_hud
# ShowBragGrid). A record is celebrated only against another player. Analytics devices (tag fnm_analytics) count each
# station clear, the finish and the kill. The slate goes compact for a retry hold and in the arena hall.
# BOSS BATTLE mode (BOSS_MODE.md, fnm_bossmode.verse): a player whose Mode is Boss plays in the fnm_bm arena; their pads,
# perches, respawns and finish go to BossMode. Race code paths ignore them (StationOccupied, WatchDoors/Skip/Ice).
# Doors: every showing of a question shuffles its choices (State.Order), so the right door moves; a position
# backstop (WatchDoors) answers for a player who stands anywhere in a door's vestibule when no trigger event was taken.
# Wrong door  -> big red X and +3 s on the race clock, that choice's Feedback, a random penalty from Penalties (a hold of
#                about 2.5 s where they stand), then the station's retry spot 6 m in front of its doors (G9: not back past
#                every obstacle and guard) and the same question with its letters shuffled again.
# Right door  -> big green check, and the way on opens at once (no stall): that door's barrier lets them
#                through, or a teleport to NextTeleporter. The slate shows the solved item as a recap card (right
#                tile lit, the Explanation, "CORRECT!  -1.8 s") for RecapSeconds while they run on, then the next
#                question (G9; it used to put "Correct! <explanation>" under the NEXT question).
# The race finale: when the titan falls, every finisher is stood at the podium (RACE AGAIN / NEW SKILL) PodiumSeconds
#                later (G9). Station 1 shows tutorial captions on a player's first run of the session; the rivals
#                strip shows the top 3, the rival just ahead and you; a wrong door's feed line goes to the victim alone
#                (the leader's stays public).
# After the last station -> a finish board hung from the top of the screen: time, medal, personal best, island
#                record (with the holder's name), first-try accuracy and the session's top times (best per player).
#                It captures no input: the player walks straight on into the victory area while it shows, and it
#                hides itself after ResultsSeconds (Aaron 2026-10-06: the old board popped up and locked him out of
#                the victory area). There the podium's NEW RACE button (fnm_new_race) starts a fresh run from
#                station 1 and CHANGE SKILL (fnm_change_skill) reopens the picker. A giant screen there (fnm_hall_*)
#                ranks everyone present by their all-time best (fnm_save.verse). No podium button on the map: the
#                board keeps its CLOSE / CHANGE SKILL buttons (which hold the player) and the automatic restart
#                after RestartSeconds.
# Engagement: a 3-2-1-GO countdown and a race clock per run; a first-try right answer builds a streak and a
# speed boost (longer with the streak), shown big in the top panel with the boost's seconds counting down;
# shipping containers tagged fnm_slider sweep across the hallways; a player inside an fnm_ice_zone gets the
# fnm_ice_floor movement settings (slippery) until they leave it: zone enter/exit events plus a position poll
# (WatchIce, IsInVolume), so a teleport out always ends the ice; the device's own add-to-everyone-at-start is
# undone at OnBegin (RemoveFromAll), since it put the whole course on faint ice (Aaron 2026-10-06).
# Guards: a guard spawner tagged fnm_guards + fnm_station_NN (tools/build_guards.py, more guards per later station)
# is switched on while any player is on that station and off (its guards despawn) once nobody is. Any player
# eliminated (a guard, a Spike) respawns at the entry of the station they were on, with the pistol. An
# elimination ends a speed boost but keeps the streak: dying to a guard is not a math mistake (a Spike is a
# wrong answer, which already reset it).
# Boss arena (G6 item 3, tools/build_course.py arena): found by its own tag fnm_boss, NOT a numbered station (the tier
# formula keeps Stations.Length). Its stage is Stations.Length + 1, always the hardest tier. The last station's right
# door sends a player on into it (EnterArena); its four pads answer like doors (on entering, no position backstop). A
# right pad is a hit on the shared boss (BossHit: 1/BossHitsToKill of its health, the player back to the arena entry,
# next question); a wrong pad is the normal penalty plus two adds. The kill (BossDown) finishes every player in the
# arena (the clock stops there), opens the exit gate for each of them, and the boss returns BossRespawnSeconds later
# for the next player. Medal and accuracy stay course-only. Since 2026-10-11 (BOSS_MODE.md 16, tools/build_race_boss.py)
# the race boss is boss mode's: a hidden Megabrute (fnm_race_megaboss, pulsed up, pinned, healed of every hit but a pad's)
# under the Magma Titan (RaceTitan, fnm_race_titan), mega cannons firing Niagara lasers along fnm_race_beam markers, the
# bottom boss bar (RaceBossBar), floating letters over the pads (fnm_race_letter, FaceLetter) and the explanation of a
# right pad held back ExplainDelaySeconds.

using { /Fortnite.com/Characters }
using { /Fortnite.com/Devices }
using { /UnrealEngine.com/Temporary/SpatialMath }
using { /Verse.org/Colors }
using { /Verse.org/Random }
using { /Verse.org/Simulation }
using { /Verse.org/Simulation/Tags }

# One finisher's best time this session, for the finish board, with that run's splits (the race-clock time at each
# right answer, index stage - 1; empty when the run did not cover every station): the next runs' pace target.
fnm_result := class:
    Who : player
    Time : float
    Splits : []float = array{}

# One player's place in the live rivals strip (RaceLoop): the strip is sorted by Score, lowest first; Tail is the row
# after the name ("station 7", "FIN 1:23.4", "picking", "lobby").
fnm_race_entry := class:
    Who : player
    Score : float
    Tail : string

# A solved item for the recap card (fnm_director Recap, fnm_hud ShowRecap): its prompt, its choices in the order they
# were shown (tile K = door K), the door that was right, the worked steps and the verdict line ("CORRECT!  -1.8 s").
fnm_recap := struct:
    Prompt : string
    Choices : []string
    Right : int
    Steps : string
    Verdict : string

# The finish board's record line: the record is the session's (fnm_director Boards lives in memory), so it says so (G9).
FnmTodayRecord<localizes>(Time:string, Who:agent, Tail:string):message = "Today's record   {Time}  by {Who}{Tail}"

# G10 feed lines (names are only ever in messages). Public: a strike landing and a shield blocking one. The target's own:
# the warning. The striker's own: where the strike went. A shield saving a wrong door goes through MissFeed (the leader's
# public, anyone else's private).
FnmFeedStrike<localizes>(Striker:agent, Verb:string, Target:agent):message = "{Striker} {Verb} {Target}!"
FnmFeedShieldBlock<localizes>(Target:agent, Striker:agent):message = "{Target}'s shield blocked {Striker}!"
FnmFeedIncoming<localizes>(Striker:agent):message = "INCOMING STRIKE from {Striker}!"
FnmFeedStrikeAway<localizes>(Target:agent):message = "Your STRIKE flies at {Target}!"
FnmFeedShieldSaved<localizes>(Who:agent, Where:string):message = "{Who}'s shield saved them {Where}"

# Flat (x, y) distance from A to B in metres with one decimal, for log lines.
FnmMetres(A:vector3, B:vector3)<transacts>:string =
    D := Distance(vector3{X := A.X, Y := A.Y, Z := 0.0}, vector3{X := B.X, Y := B.Y, Z := 0.0})
    Tenths := if (T := Round[D / 10.0]) then T else 0
    "{FnmDiv(Tenths, 10)}.{Tenths - FnmDiv(Tenths, 10) * 10}"

# One question station, assembled at OnBegin from the director's flat config.
fnm_station := class:
    # trigger_devices for the doors, in order A, B, C, D.
    Doors : []trigger_device
    # Per door (same order): the barrier at the back of its vestibule, if the course has one.
    Passages : []?barrier_device
    # Where a player is sent after a wrong answer (this station's entry point).
    RetryTeleporter : teleporter_device
    # Where a player is sent after a right answer: the next station's entry (last station: finish).
    NextTeleporter : teleporter_device
    # Difficulty position in percent, 0 (easiest tier) .. 100 (hardest tier); -1 = automatic.
    DifficultyOverride : int
    # Where a punished player comes back (G9, RetrySpotFor): in front of the door wall, facing the doors. False = the
    # arrival spot of RetryTeleporter (the two arenas, whose pads stand in the open).
    RetrySpot : ?vector3 = false

# One hallway's footprint for the skip guard (WatchSkip): world cm, Z at the entry pad.
fnm_hallway := class:
    MinX : float
    MaxX : float
    MinY : float
    MaxY : float
    Z : float

# The boss arena, found by tag at OnBegin. Station: the arena seen as a station (its pads as doors, its entry as the
# retry point and penalty return spot), so the door and penalty code serve it unchanged.
fnm_arena := class:
    Station : fnm_station
    Gate : ?barrier_device
    # The boss since 2026-10-11: a Megabrute creature spawner on the platform (hidden inside the titan) and its placed
    # transform, where the boss is held (FnmPinBoss).
    Boss : ?creature_spawner_device
    BossHome : ?transform
    Adds : ?guard_spawner_device

# Which game a player is playing: the race course, or BOSS BATTLE mode (fnm_bossmode.verse).
fnm_mode := enum{Race, Boss}

# Everything the director knows about one player's run.
fnm_player_state := class:
    Player : player
    Hud : fnm_hud
    # The player's chosen cartridge (PROTOCOL 6b): its index in the director's Cartridges (-1 = not picked yet),
    # the cartridge itself, its tier count and per-tier item pools.
    var CartridgeIndex : int = -1
    var Cartridge : fnm_cartridge = fnm_cartridge:
        Protocol := ""
        Id := ""
        Version := ""
        Title := ""
        Subtitle := ""
        Grade := ""
        Tiers := array{}
        Items := array{}
    var TierCount : int = 0
    var TierPools : [][]int = array{}
    # True while the skill picker is up for this player: doors and guards ignore them, the clock is stopped.
    var Picking : logic = false
    # Times this player has picked a skill (the debug hooks start on the first pick only).
    var Picks : int = 0
    # 1-based stage; stage s is played at Stations[s - 1].
    var Stage : int = 1
    # Remaining shuffled item indices per tier (index t - 1 for tier t).
    var Decks : [][]int = array{}
    # Index into the cartridge's Items of the question on screen (-1 = none).
    var CurrentItem : int = -1
    # Display order of the current item's choices: door/letter k shows choice Order[k] (shuffled per question, so a
    # repeated question does not keep its right door; Aaron 2026-10-05: "after enough runs it would become memorization").
    var Order : []int = array{}
    var MissedCurrent : logic = false
    var FirstTryCorrect : int = 0
    # True while a door result is being processed (blocks double triggers).
    var Busy : logic = false
    # Door backstop (WatchDoors): when a door answer was last accepted, which door zone of the current station the
    # player stands in (-1 none), since when, and whether the backstop already answered for this stay.
    var LastAccept : float = -100.0
    # When their last right answer was taken: a door or pad event within RightCooldownSeconds of it is dropped (a late
    # event from the pad they were just teleported off would be checked against the NEXT question and come out wrong).
    var LastRight : float = -100.0
    # Bumped by every right answer (Cleanse): a mud or dizzy penalty still running stops, so a right answer is never
    # followed by a slow-down or blur (Aaron 2026-10-10: "sometimes i think im getting an incorrect answer debuff even
    # though its right and counted right": the 8 s mud re-applied itself every 2.5 s after a quick right answer).
    var PenaltyEpoch : int = 0
    # True from a mud or dizzy penalty until a right answer cleanses it.
    var Afflicted : logic = false
    var ZoneDoor : int = -1
    var ZoneSince : float = 0.0
    var ZoneFired : logic = false
    var Finished : logic = false
    # True for a run that started past stage 1 (DebugStartStage): its time is shown but never saved as a best, put on
    # the board or called a record (2026-10-07: arena-only test runs set a 0:29.6 island record).
    var Partial : logic = false
    # True while the fnm_ice_floor settings are on this player (SetIce).
    var OnIce : logic = false
    # Right-first-try answers in a row (a wrong door resets it).
    var Streak : int = 0
    var BestStreak : int = 0
    # Race clock: simulation time the run's GO! showed; -1 = not running yet (the "no clock" sentinel: never moved, see
    # RunClock). ClockPenalty: seconds the run's wrong doors added (WrongDoorSeconds each, ChargeWrongDoor), WrongDoors
    # how many; both reset with StartTime.
    var StartTime : float = -1.0
    var ClockPenalty : float = 0.0
    var WrongDoors : int = 0
    # Bumped by every WideLook / WideCamera call, so an older wide-camera beat never takes off a newer one's camera.
    var CameraGeneration : int = 0
    # Bumped per run and per boost, so an older clock or boost loop stops itself.
    var RunGeneration : int = 0
    var BoostGeneration : int = 0
    # Best finishing time this session for the current skill (-1 = none yet), and the same per skill, keyed by the
    # cartridge's index in the slot (switching back to a skill brings that skill's best back; PROTOCOL 6b: times
    # across skills are never compared). Runs = runs finished, any skill.
    var BestTime : float = -1.0
    var BestTimes : [int]float = map{}
    var Runs : int = 0
    # Pace (G6): this run's race-clock time at each right answer (index stage - 1), reset per run; the splits it is
    # measured against (ChoosePace at GO!; empty = no target); the last finished run's time (the rivals strip's FIN).
    var Splits : []float = array{}
    var PaceTarget : []float = array{}
    var LastTime : float = -1.0
    # Boss arena: this run's hits on the boss, and whether the boss line is on their HUD; whether they have walked into
    # the arena hall this run (its one instruction fires then, WatchArena).
    var Hits : int = 0
    var BossShown : logic = false
    var ArenaArrived : logic = false
    # Bumped by every ShowCurrent and recap: a recap flips to the next question only if nothing newer took the slate.
    var SlateSerial : int = 0
    # True once the station-1 tutorial captions have run for this player (first run of the session).
    var TutorialDone : logic = false
    # Pickup pads: when each pad (by index) last granted this player its item (OnPad).
    var PadGrants : [int]float = map{}
    # Boss battle mode (fnm_bossmode.verse): the mode, the fight's level as this player last saw it, eliminations this
    # run, right answers this run, one shuffled deck per cartridge per tier, the levels whose weapon they took, and their
    # best boss-mode time (-1 = none).
    var Mode : fnm_mode = fnm_mode.Race
    var Level : int = 0
    var Deaths : int = 0
    var Answered : int = 0
    var BmDecks : [][][]int = array{}
    var TakenLevels : [int]logic = map{}
    var BossBest : float = -1.0
    # G10 (briefs/g10/D_director.md). This run's mark per station (index stage - 1): FnmMarkFirstTry, FnmMarkRedeemed,
    # FnmMarkMissed or FnmMarkUnreached (fnm_logic.verse), for the brag grid and the medal. REDEMPTION (R4): the stations
    # this run missed, in station order, still waiting for their redemption question at the boss; the station the arena
    # question on the slate was drawn for (0 = the arena's own hardest tier); how many were redeemed (half credit each).
    var Marks : []int = array{}
    var RedeemQueue : []int = array{}
    var RedeemStage : int = 0
    var Redeemed : int = 0
    # True when this run ended at the titan's kill (the brag grid's boss tile).
    var BossDowned : logic = false
    # SHIELD (C2): at most one, earned at streak ShieldStreak; it blocks the next penalty (own wrong door or a strike).
    var Shield : logic = false
    # STRIKE (C3): no strike lands on this player before ImmuneUntil; Struck while a strike is aimed at them or holds them.
    var ImmuneUntil : float = -100.0
    var Struck : logic = false
    # When the current boost ends (Boost), so a LEADER BONUS adds its seconds to what is left.
    var BoostUntil : float = -1.0
    # The compact slate (fnm_hud SetCompact): on for a wrong door's retry hold (RetryHold bumps per hold) and in the
    # arena hall; Compact is what the HUD was last told.
    var RetryHold : int = 0
    var RetryHolding : logic = false
    var Compact : logic = false

# Binds one door to its station/door index, so a single callback signature can serve every door.
fnm_door_handler := class:
    Director : fnm_director
    StationIndex : int
    DoorIndex : int

    OnTriggered(MaybeAgent:?agent):void =
        if (not Director.DebugIgnoreTriggerEvents?):
            Director.OnDoor(MaybeAgent, StationIndex, DoorIndex)

# Binds one pickup pad's trigger (tools/build_pickups.py) to its index and item kind, so one callback serves every pad.
fnm_pad_handler := class:
    Director : fnm_director
    Index : int
    Kind : string

    OnTriggered(MaybeAgent:?agent):void =
        Director.OnPad(MaybeAgent, Index, Kind)

fnm_director := class(creative_device, fnm_picker_listener):
    # Optional difficulty position per station in percent (0 easiest .. 100 hardest); -1 or a missing
    # entry = automatic, spread evenly from first station to last (PROTOCOL 6).
    @editable
    DifficultyOverrides : []int = array{}

    # Seconds the wrong-answer feedback stays on the HUD (the player is teleported back immediately).
    @editable
    WrongFeedbackSeconds : float = 4.0

    # Seconds the explanation of a right answer stays on the HUD (the player moves on immediately). Boss mode's; the race
    # shows the recap card instead (RecapSeconds).
    @editable
    CorrectFeedbackSeconds : float = 4.0
    # See LastRight on the player state.
    RightCooldownSeconds : float = 1.5
    # G9 (reviews/race-2026-10-13): a right door's recap card stays RecapSeconds (Recap); a finisher is stood at the podium
    # PodiumSeconds after the titan falls, PodiumStandOff in front of RACE AGAIN (PodiumLater); the station-1 tutorial
    # captions change every TutorialStepSeconds (Tutorial); the announcer's "Choose your grade" comes ChooseDelaySeconds
    # after the welcome (they overlapped); the rivals strip shows the top StripTop, the rival just ahead and the viewer.
    # Round 2 (Fable audit + QA, 2026-10-13): in the race arena the recap lasts at most RightCooldownSeconds (its pads are
    # live meanwhile: a pad stepped on after the cooldown must answer a question already on the slate); the wide camera
    # stays RetryWideSeconds on the retry spot and PodiumWideSeconds at the podium (3 s past the finish board, which hides
    # ResultsSeconds after the finish, PodiumSeconds before the podium teleport), or until the player has moved
    # WideMoveCm (WideLook); the podium spot is centred between the lecterns, PodiumStandOff in front of their buttons.
    RecapSeconds : float = 3.0
    PodiumSeconds : float = 3.0
    PodiumStandOff : float = 350.0
    RetryWideSeconds : float = 4.0
    PodiumWideSeconds : float = 10.0
    WideMoveCm : float = 150.0
    TutorialStepSeconds : float = 3.0
    ChooseDelaySeconds : float = 2.0
    StripTop : int = 3

    # Wrong-door penalties come from the map profile (map.json "penalties" -> FnmMapPenalties), one at random
    # per wrong answer. Each penalty's visual is a rig (fnm_rig.verse) or effect device placed by
    # tools/build_rigs.py.
    # The five-second wrong door (G9, reviews/race-2026-10-13 ux_critique #8): every penalty holds the player about 2.5 s
    # where they stand (FreezeSeconds; the Yeet throw; SpearSeconds + SpikeHoldSeconds; MudStuckSeconds; the Dizzy spin;
    # BlackoutSeconds + 0.5), then puts them on their station's retry spot (RetrySpotFor: RetryStandOff in front of the door
    # wall, facing the doors), the race clock takes WrongDoorSeconds and the letters are shuffled again (Reshuffle). Until
    # 2026-10-13 a wrong door cost 5.8 s (Yeet) to 9.3 s (Freeze) plus a 25.5 m re-run past the obstacles and the guards.
    var Penalties : []fnm_penalty = array{}
    @editable
    FreezeSeconds : float = 2.5
    # Mud: stuck where they stand (turning allowed) with a brown screen for MudStuckSeconds, then on the retry spot slowed
    # (the fnm_mud movement modulator) for MudSeconds. The modulator's own Duration is 3 s and can't be set from MCP, so it
    # is re-applied every MudReapplySeconds.
    @editable
    MudStuckSeconds : float = 2.0
    @editable
    MudSeconds : float = 3.0
    @editable
    MudReapplySeconds : float = 2.5
    # Dizzy: where they stand, the view spins about DizzySpinDegreesPerSecond for DizzySpinSeconds, rounded to whole turns
    # (one since 2026-10-13: two in 1.5 s was a motion-comfort risk, ux_critique 3.9) so it ends facing the doors (the
    # character is re-teleported in place, yaw advanced, every DizzySpinStepSeconds, under stasis); then, on the retry spot,
    # a radial blur pulses in and out (DizzyPulseSeconds each way) for DizzySeconds (two pulses). Aaron 2026-10-04: the old
    # colour swirl (PP_Crazy) was confusing, not dizzying.
    @editable
    DizzySeconds : float = 2.8
    @editable
    DizzyPulseSeconds : float = 0.7
    @editable
    DizzySpinSeconds : float = 1.5
    @editable
    DizzySpinDegreesPerSecond : float = 240.0
    @editable
    DizzySpinStepSeconds : float = 0.05
    # Blackout: the screen goes dark and the player is held this long, then wakes up on the retry spot (the black lifts
    # 0.5 s later).
    @editable
    BlackoutSeconds : float = 2.0
    # Yeet: pulled onto the retry spot (out of the narrow vestibule, so the throw back does not hit the door wall), an air
    # vent (fnm_yeet rig) appears under them at world yaw YeetYaw, tilted YeetPitch so its gust throws them back down their
    # hallway. It stays YeetSeconds; at most YeetAirSeconds after it appeared they are put back on the retry spot (the throw
    # plays; the walk back does not). (Player physics is off in UEFN, so SetLinearVelocity does nothing; per-tick
    # TeleportTo was choppy.)
    @editable
    YeetYaw : float = 90.0
    @editable
    YeetPitch : float = 50.0
    @editable
    YeetSeconds : float = 0.4
    @editable
    YeetAirSeconds : float = 1.6
    # Spike: SpearCount spears wait SpearDepth (cm) under the floor in a ring of radius SpearRing around the player, burst up
    # SpearRise in SpearSeconds and pin them (stasis) for SpikeHoldSeconds under the wide camera; then the retry spot. No
    # elimination since 2026-10-13: the kill showed Fortnite's "bailed early" line and the respawn took every gun the
    # guards had dropped (ux_critique B3). Freeze and Spike happen where the player stands (Aaron: no position change).
    @editable
    SpearCount : int = 6
    @editable
    SpearRing : float = 55.0
    @editable
    SpearDepth : float = 220.0
    @editable
    SpearRise : float = 250.0
    @editable
    SpearSeconds : float = 0.12
    @editable
    SpikeHoldSeconds : float = 2.3
    # The retry spot (RetrySpotFor): RetryStandOff cm in front of the door wall's front face, DoorWallThickness in front of
    # its back face (tools/build_course.py: the door wall runs door_y +/- 25). WrongDoorSeconds go on the race clock per
    # wrong door. 600 (6 m) since the round-2 review: at 3 m only doors B and C were on screen (the wide camera covers the
    # rest, WideLook). RetryFallback: a retry spot found inside a door's zone is not used (the entry's arrival spot is),
    # since a player put there would answer that door by position again and again (false only to prove that in a test).
    # For any RetryStandOff >= 0 the spot lies in front of every zone by construction, so the OnBegin check can only fail
    # for a negative stand-off or a course whose triggers no longer start at the door wall (a rebuilt or other map).
    @editable
    RetryStandOff : float = 600.0
    DoorWallThickness : float = 50.0
    RetryFallback : logic = true
    @editable
    WrongDoorSeconds : float = 3.0
    # A character's reported position is its capsule centre; feet are this far below it (cm, measured
    # standing on the course floor 2026-10-03).
    @editable
    FeetDrop : float = 77.0

    # Test hook: each joining player auto-answers this many questions wrong, one every 12 s, cycling
    # through Penalties in order, so every penalty can be watched without walking. 0 = off (ship value).
    @editable
    DebugAutoWrongAnswers : int = 0
    var DebugPenaltyCursor : int = 0
    # Test hook: 8 s after joining, drop the player into station 1's RIGHT vestibule (firing its trigger),
    # then log their position every second for 12 s, to watch them walk through the opened barrier.
    # false = off (ship value).
    @editable
    DebugPassageTest : logic = false
    # Test hook: 8 s after joining, stand the player 2.5 m in front of station 1's door with this index
    # (0 = A), facing it, to check the real door opens (press E, walk in). -1 = off (ship value).
    @editable
    DebugDoorTest : int = -1
    # Test hook: each joining player answers every station right, one every 6 s, by being dropped into the
    # right door's vestibule (the real trigger and barrier do the rest), for two runs, so the finish board
    # (and a second finish against a best time) can be checked without walking. false = off (ship value).
    @editable
    DebugAutoRightAnswers : logic = false
    # Test hook: with DebugAutoRightAnswers, drop the player this far (cm) PAST the door trigger's centre, deeper into
    # the vestibule, where a player who ran or jumped through the door ends up (2026-10-06: the back of a vestibule
    # was outside the trigger box and the backstop zone, so a right door did nothing until they moved). 0 = ship value.
    @editable
    DebugAutoRightOffsetY : float = 0.0
    # The arena auto-run drops the player this far off the pad's centre in x and y (a 450 cm pad senses to 225): every run
    # proves the trigger senses its whole tile, not just its middle (until 2026-10-09 it sensed a 96 cm square).
    DebugPadOffset : float = 180.0
    # DebugAutoRightAnswers in the race arena: seconds at its entry before the first pad, for the titan's entrance (G9 D2).
    DebugEntranceSeconds : float = 5.0
    # Test hook for the victory area: when a player's finish board hides (ResultsSeconds after the finish, or CLOSE
    # without a podium), stand them 1.5 m in front of the NEW RACE button facing it (press E to try it), and
    # DebugAutoRightAnswers waits for that real press instead of simulating one. false = off (ship value).
    @editable
    DebugVictoryTest : logic = false
    # Test hook: each joining player starts at this stage's entry (to try a later hallway's obstacles). 0 or 1 =
    # station 1 (ship value 0).
    @editable
    DebugStartStage : int = 0
    # Test hook: each joining player picks Cartridges[DebugAutoPick] at once, with no menu (also after CHANGE
    # SKILL), so tools/playtest.py and every other debug hook run headless. -1 = off, the menu shows (ship value).
    @editable
    DebugAutoPick : int = -1
    # Test hook (G9 D2): with DebugAutoPick, show the picker (logo, grade step, its music bed) for this many seconds first,
    # then pick, so a headless session sees the picker with no click. 0 = pick at once (ship value).
    @editable
    DebugPickerSeconds : float = 0.0
    # Test hook: drop every door trigger event, so only the position backstop (WatchDoors) answers doors. Pair with
    # DebugAutoRightAnswers to prove the backstop carries a whole run. false = ship value.
    @editable
    DebugIgnoreTriggerEvents : logic = false
    # Test hook: 8 s after the first pick, drop the player at station 3's entry while they are still on stage 1, to
    # prove the skip guard (WatchSkip) sends them back to station 1. false = off (ship value).
    @editable
    DebugSkipTest : logic = false
    # Test hook: each joining player starts BOSS BATTLE mode at once, with no menu (wins over DebugAutoPick; also after
    # CHANGE SKILL). With DebugAutoRightAnswers the run is played to the victory (DebugBossModeRun). false = ship value.
    @editable
    DebugAutoBoss : logic = false
    # Test hook: boss mode's first start begins at this level (2..5; the run is Partial: never saved or boarded). 0 =
    # level 1 (ship value).
    @editable
    DebugBossLevel : int = 0
    # Test hook: with DebugAutoBoss + DebugAutoRightAnswers, seconds the auto-run waits with the boss up before each pad,
    # so the level's SpawnSeconds elapse and the monster cap is reached. 0.0 = no wait (ship value).
    @editable
    DebugBossHold : float = 0.0
    # Test hook: once a boss-mode level is summoned, stand every fighter on perch N (1..4) facing its weapon chest, to see
    # the chest and press E on it. 0 = off (ship value).
    @editable
    DebugBossChest : int = 0
    # How far in front of the chest DebugBossChest stands the player (cm, toward the stepping stones).
    @editable
    DebugChestDistance : float = 150.0
    # Test hook (G9 F, the pillar's draw distance): every right answer at a station also stands a pillar of light in the
    # same door's vestibule this many stations ahead, 2.5 s later (FarPillarLater), logged with its distance from the
    # player, to see a pillar from afar in a one-player session. 0 = off (ship value).
    @editable
    DebugFarPillar : int = 0
    # Boss mode: seconds from a level's clear to the next level's summon; the summon's length (its timeline scales to it);
    # how long the MEGA NUKE verdict stays up.
    @editable
    BmRespawnSeconds : float = 4.0
    @editable
    BmSummonSeconds : float = 5.0
    @editable
    NukeSeconds : float = 2.5
    # The session board key for boss-mode times (Boards is keyed by cartridge index; no slot holds 9999 cartridges).
    BossBoardKey : int = 9999

    # Where a moved player lands, relative to the target teleporter pad (cm, world axes; the course runs
    # toward +Y, doors ahead). Landing ON the pad left a player sunk into its collision (2026-10-03
    # playtest), so they land in open floor between the pad and the doors, a little above the ground.
    @editable
    ArrivalForward : float = 300.0
    @editable
    ArrivalLift : float = 100.0
    # World yaw a moved player faces (90 = +Y, toward the doors).
    @editable
    ArrivalYaw : float = 90.0

    # Speed boost after a first-try right answer: BoostSeconds, plus StreakBonusSeconds per answer of streak
    # beyond the first, at most MaxBoostSeconds. The fnm_boost modulator's own duration is 3 s (not settable from
    # MCP), so it is re-applied every BoostReapplySeconds.
    @editable
    BoostSeconds : float = 3.0
    @editable
    StreakBonusSeconds : float = 1.0
    @editable
    MaxBoostSeconds : float = 7.0
    @editable
    BoostReapplySeconds : float = 2.5
    # Sliding containers: SliderSeconds to cross the hallway, SliderPause at each wall, SliderTravel cm along the
    # container's own forward axis (tools/build_course.py: 2 * SLIDE_X; the course is no longer centred on X = 0).
    @editable
    SliderSeconds : float = 2.2
    @editable
    SliderTravel : float = 1580.0
    @editable
    SliderPause : float = 0.5
    # Countdown before each run: one beat per number.
    @editable
    CountdownStepSeconds : float = 0.8
    # Seconds before the automatic restart, used only without a podium NEW RACE button or under DebugAutoRightAnswers.
    @editable
    RestartSeconds : int = 12
    # With a podium: seconds the finish board stays up (capturing no input) before it hides itself.
    @editable
    ResultsSeconds : float = 10.0
    # Rows on the finish board's session leaderboard (best time per player). The HUD has room for 5.
    @editable
    BoardSize : int = 5
    # Seconds the all-time screen shows each skill before the next (it cycles through skills with times).
    @editable
    HallCycleSeconds : float = 8.0
    # Door backstop: how often player positions are checked against the door zones, and how long a player must
    # stand in one with no door event taken before it answers for them.
    @editable
    DoorWatchSeconds : float = 0.25
    # A trigger senses only its StepBox: half-extent TriggerHalf (x and y) and centre TriggerLift above the device's origin,
    # in cm at scale 1, both scaled with the actor (tools/build_course.py trigger_fit; the origin sits under the floor).
    # TriggerHalfZ: its half height (STEP_BOX z), so the box's bottom, the floor, is ZoneCentre less TriggerHalfZ * scale.
    TriggerHalf : float = 64.0
    TriggerLift : float = 32.0
    TriggerHalfZ : float = 15.0
    # Skip guard (WatchSkip): a player found in a hallway past their stage (a Shockwave Grenade from a pickup pad
    # clears a 6 m door wall) goes back to their own station's entry. A position more than HallwayHeight above a
    # hallway's entry pad (a Yeet skydive passing over) does not count. FinishHallwayLength = FINISH_LEN in
    # tools/build_course.py.
    HallwayHeight : float = 400.0
    FinishHallwayLength : float = 1500.0
    @editable
    DoorDwellSeconds : float = 0.4
    # How often the director checks which stations have players on them, to switch their guards on or off.
    @editable
    GuardCheckSeconds : float = 1.0

    # Seconds "No choice X here" / "not your station" notices stay up.
    @editable
    NoticeSeconds : float = 2.0

    # Optional: activate an End Game device for a player who finishes the course.
    @editable
    UseEndGameDevice : logic = false

    @editable
    EndGameDevice : end_game_device = end_game_device{}

    # Seconds the results screen shows before the End Game device fires.
    @editable
    EndGameDelaySeconds : float = 10.0

    # Every cartridge in the slot (FnmCartridges(), picker order) and, per cartridge, its per-tier item pools.
    var Cartridges : []fnm_cartridge = array{}
    var CartridgePools : [][][]int = array{}
    var Stations : []fnm_station = array{}
    var PlayerStates : [player]fnm_player_state = map{}
    var Ready : logic = false
    var IceRig : fnm_rig = fnm_rig{Name := "ice", Parts := array{}, Homes := array{}}
    var SpikeRig : fnm_rig = fnm_rig{Name := "spike", Parts := array{}, Homes := array{}}
    var YeetRig : fnm_rig = fnm_rig{Name := "yeet", Parts := array{}, Homes := array{}}
    # Found by tag (tools/build_rigs.py): the wide camera for frozen/spiked players.
    var PenaltyCam : ?gameplay_camera_orbit_device = false
    var LoadoutTrigger : ?trigger_device = false
    var MudDevice : ?movement_modulator_device = false
    var BoostDevice : ?movement_modulator_device = false
    # The low-friction movement settings applied while a player stands in an fnm_ice_zone (icy hallways).
    var IceFloor : ?player_movement_settings_device = false
    var IceZones : []mutator_zone_device = array{}
    # The session's best time per player, fastest first, at most BoardSize rows, PER SKILL: keyed by the cartridge's
    # index in the slot. The map is the island, so a board reads "best Order of Operations on this map" (Aaron,
    # 2026-10-04: never compare timings across skills). Row 0 of a board holds that skill's island record.
    var Boards : [int][]fnm_result = map{}
    var FrostFx : ?post_process_device = false
    var MudFx : ?post_process_device = false
    var DizzyFx : ?post_process_device = false
    # Per station (index = stage - 1): its guard spawner, if any, and whether its guards are up.
    var GuardSpawners : []?guard_spawner_device = array{}
    var GuardsUp : []logic = array{}
    # Each station's hallway (vestibules included) and, last, the finish hallway, as boxes for the skip guard.
    var Hallways : []fnm_hallway = array{}
    var FinishPad : ?teleporter_device = false
    var GuardsSpawned : int = 0
    # Victory area (tools/build_finish.py): podium buttons and the all-time screen's billboards (rows top to bottom).
    var NewRaceButtons : []button_device = array{}
    var ChangeSkillButtons : []button_device = array{}
    var HallHeads : []billboard_device = array{}
    var HallRows : []billboard_device = array{}
    # The screen holds a just-finished skill until this simulation time before cycling on.
    var HallHoldUntil : float = 0.0
    # The sound layer (fnm_audio.verse, tools/build_audio.py): one audio player per cue, found by tag at OnBegin.
    var Audio : ?fnm_audio = false
    # Seconds between the stacked finish voice lines (best/record, medal, perfect), so they do not pile up.
    @editable
    FinishCueGapSeconds : float = 1.6
    # G9 D2: the first of them comes this long after the finish fanfare starts. The Mint fanfare is 5.46 s: a quiet lead-in
    # to 1.75 s, its loud body to ~4.25 s (-19..-23 dB in 0.25 s frames, peak at 2.5 s; -34 dB by 4.5 s), so a line at 1.6 s
    # (the stock fanfare's gap) landed on the body. FinishSounds.
    FinishVoiceSeconds : float = 4.2
    # G9 D2: on a wrong pad in an arena (the race's boss arena, Boss Battle mode) the crowd's aww follows the penalty's voice
    # line by CrowdAfterVoiceSeconds, and in boss mode the boss's taunt follows the aww by TauntAfterCrowdSeconds
    # (PenaltyLines): 0.9 s apart, the mix rule between a voice and a stinger.
    CrowdAfterVoiceSeconds : float = 0.9
    TauntAfterCrowdSeconds : float = 0.9
    # The penalty voice line comes this long after the wrong buzzer and the effect's own sound, so it is not buried under
    # them (2026-10-07: matched filter found the lines at 0.2-0.3 correlation when played on the same instant, GO at 0.88).
    @editable
    PenaltyVoiceDelaySeconds : float = 0.9
    # Live race layer (G6): the rivals strip is refreshed every RaceSeconds and holds RaceRows rows (fnm_hud RivalRows);
    # the last strip logged, so the log gets a RACE line only when the order or a station changes.
    RaceSeconds : float = 0.5
    RaceRows : int = 8
    var LastRaceLog : string = ""
    # The race leader as of the last strip (a race player still racing in first place), whose misses stay public (MissFeed).
    var RaceLeaderNow : ?player = false
    # Boss arena (G6 item 3): right pads it takes, shared by everyone in the arena, to bring the boss down; seconds after
    # a kill before the boss returns; how often the boss line and the boss's state are checked.
    @editable
    BossHitsToKill : int = 5
    # Seconds between "bullets can't hurt it" hints for one player shooting the boss.
    @editable
    GunHintSeconds : float = 6.0
    var LastGunHint : [player]float = map{}
    @editable
    BossRespawnSeconds : float = 4.0
    BossRefreshSeconds : float = 0.25
    var Arena : ?fnm_arena = false
    # The boss now up (its agent), whether it is alive, when a spawn was asked for (-1 = none pending), when it last went
    # down, team hits since it spawned, the player whose hit was the last, whether the adds are switched on.
    var BossAgent : ?agent = false
    var BossAlive : logic = false
    var BossRequestedAt : float = -1.0
    var BossDownAt : float = -100.0
    var BossHitsTaken : int = 0
    var LastHitter : ?player = false
    var AddsUp : logic = false
    # The adds spawner's Spawn Count (tools/build_course.py ADDS_SETTINGS).
    AddsCount : int = 2
    # The laser cannons (Aaron 2026-10-08: "epic laser cannon blast the boss and the boss flail or get knocked back"; the
    # Meshy mega cannons of tools/build_race_boss.py since 2026-10-11): the beam markers the Niagara lasers fire along,
    # the strike VFX spawner moved onto the boss, the explosive devices parked under the platform (one per hit, round
    # robin). How long the flash and strike stay on; the announcer's delay after the bang for the hit count and for BOSS
    # DOWN.
    var RaceRig : fnm_cannon_rig = fnm_cannon_rig{Fx := array{}, Strike := false, StrikeHome := false, Blasts := fnm_rig{Name := "blast", Parts := array{}, Homes := array{}}, Nuke := false}
    # BOSS BATTLE mode (fnm_bossmode.verse), when the map has its arena (an fnm_bm entry teleporter).
    var BossMode : ?fnm_boss_mode = false
    CannonFlashSeconds : float = 1.2
    HitVoiceDelaySeconds : float = 0.9
    BossDownVoiceDelaySeconds : float = 1.0
    # The knock the boss takes on a hit: an impulse back (+Y, away from the entry) and up; if that moves it under 30 cm
    # (an NPC may ignore impulses the way players do), a BossStaggerCm teleport back instead; then BossStunSeconds frozen.
    @editable
    BossKnockImpulse : float = 80000.0
    BossStaggerCm : float = 150.0
    BossStunSeconds : float = 0.8
    # Boss mode's laser beams (FireBeam; Aaron 2026-10-10: "attacks on him more obviously coming from the side laser
    # cannons"): BeamShots shots per hit, each growing out of the muzzle to the boss in BeamTravelSeconds, held
    # BeamHoldSeconds, then BeamGapSeconds dark.
    BeamShots : int = 3
    # The boss arena's shots are Niagara lasers (FNM_FX, tools/build_fx.py) instead of the stretched Alphabet "I" prop.
    NiagaraLaser : logic = true
    BeamPropHeight : float = 201.3      # the Alphabet "I" at scale 1 (build_bossmode BEAM_H): the beam's length is Scale.Z times this
    BeamTravelSeconds : float = 0.15
    BeamHoldSeconds : float = 0.35
    BeamGapSeconds : float = 0.08
    # The race finale's titan (fnm_titan.verse; tools/build_race_boss.py, tag fnm_race_titan): what players see of the race
    # boss, the Megabrute hidden inside it. The race cannons' coil crackle, spawned once at OnBegin.
    RaceTitan : fnm_titan = fnm_titan{}
    var RaceCoils : []cancelable = array{}
    # When the race boss last took a pad's hit (its leash waits for the knock to play out), and true while a pad's own
    # Damage lands (fnm_race_boss_damage lets only that through).
    var RaceBossHitAt : float = -100.0
    var RacePadHitting : logic = false
    # Shared by boss mode and the race finale: a Megabrute boss's health (only the pads' Damage takes it down); a boss
    # knocked more than BossLeashCm off its spot is pinned back once LeashAfterHitSeconds have passed since the hit; a
    # right pad's explanation shows ExplainDelaySeconds after the hit, so the lasers, the flail and the blast are not
    # behind the grown answer panel (Aaron 2026-10-10: "yes delay the explanation").
    MegabossHealth : float = 100000.0
    LeashAfterHitSeconds : float = 1.5
    BossLeashCm : float = 150.0
    ExplainDelaySeconds : float = 2.5
    # The floating pad letters (boss mode's and the race finale's, FaceLetter): each turns to the nearest player of its
    # arena over LetterTurnSeconds, again and again, and bobs LetterBobCm up and down once every LetterBobSeconds.
    LetterTurnSeconds : float = 0.15
    LetterBobCm : float = 40.0
    LetterBobSeconds : float = 4.0
    # The race boss bar reads DEFEATED! this long after the kill (the run is finished by then), then goes.
    DefeatedSeconds : float = 3.0
    # Pickup pads (tools/build_pickups.py): the hidden trigger per item kind, bound to the item granter that hands one
    # over; the run-over trigger over each row of pads; how long one player waits before the same row grants again.
    var GrantTriggers : [string]trigger_device = map{}
    var PadTriggers : []trigger_device = array{}
    var PadCount : int = 0
    PickupRepeatSeconds : float = 3.0
    # Test hook (ship value false): 5 s after the first pick, drops the player onto two of their own station's pad
    # triggers in turn, so the log shows whether a pad trigger fires and grants ("pickup <kind> granted at pad N").
    @editable
    DebugPickupTest : logic = false
    # G10 race rewards (briefs/g10/D_director.md, reviews/race-2026-10-13/sources/gamification.md 4-6). The first-try right
    # answer is the only thing that earns anything: a first-try streak of ShieldStreak earns a SHIELD (hold at most one),
    # of each StrikeStreaks value a STRIKE. StrikesOn: the host's switch (strikes off = no strike and no "for a STRIKE"
    # line). A strike fires StrikeDelaySeconds after it is earned at the nearest racer ahead in strip order who can take
    # one, lands StrikeWarnSeconds after their INCOMING STRIKE warning, and leaves them immune for StrikeImmuneSeconds. With
    # nobody ahead to take it (the leader's, always) it is a LeaderBonusSeconds boost instead. Effects (in place, never a
    # send-back, never the target's question, streak or credit): StrikeFreezeSeconds frozen, StrikeMudSeconds of mud,
    # StrikeBlurSeconds of blur (no spin), StrikeDarkSeconds of lights out.
    @editable
    StrikesOn : logic = true
    ShieldStreak : int = 3
    StrikeStreaks : []int = array{5, 10, 15}
    StrikeDelaySeconds : float = 1.0
    StrikeWarnSeconds : float = 1.0
    StrikeImmuneSeconds : float = 20.0
    LeaderBonusSeconds : float = 2.0
    StrikeFreezeSeconds : float = 2.5
    StrikeMudSeconds : float = 4.0
    StrikeBlurSeconds : float = 3.0
    StrikeDarkSeconds : float = 1.5
    var StrikeCursor : int = 0
    # Test hook: every strike a player earns is fired at that player (the warning, the effect, the immunity, a shield's
    # block), so one client sees every branch but the targeting. false = ship value.
    @editable
    DebugStrikeSelf : logic = false
    # Medal v2 (gamification 6): accuracy gates, a redeemed station counting half (FnmMedalHalves); time gates behind
    # MedalTimeGates (off: no par data yet), each missed gate dropping the medal one tier; a par of 0 = no gate.
    @editable
    MedalTimeGates : logic = false
    @editable
    GoldParSeconds : float = 0.0
    @editable
    SilverParSeconds : float = 0.0
    # The island code the finish board's brag grid prints ("" = no code line; text only, never a QR).
    @editable
    IslandCode : string = ""
    # Analytics (tools/build_analytics.py, S): per station (index stage - 1) the analytics_device tagged fnm_analytics +
    # that station's tag, the finish's and the boss kill's. Missing devices are skipped.
    var StationAnalytics : []?analytics_device = array{}
    var FinishAnalytics : ?analytics_device = false
    var BossAnalytics : ?analytics_device = false

    OnBegin<override>()<suspends>:void =
        set Cartridges = FnmCartridges()
        set CartridgePools = for (Each : Cartridges) { FnmBuildTierPools(Each.Items, Each.Tiers.Length) }
        var Listing : string = ""
        for (K -> Each : Cartridges):
            Separator := if (K > 0) then ", " else ""
            set Listing += "{Separator}{Each.Id} (grade {Each.Grade})"
        Print("FNM: {Cartridges.Length} cartridges: {Listing}")
        for (Each : Cartridges, Each.Tiers.Length = 0):
            Print("FNM: cartridge {Each.Id} has no tiers")
        set Arena = BuildArena()
        BuildBossMode()
        set Stations = BuildStations()
        set Hallways = BuildHallways()
        Print("FNM: {Hallways.Length} hallways for the skip guard")
        set Penalties = FnmMapPenalties()
        set IceRig = BuildRig("ice", fnm_ice)
        set SpikeRig = BuildRig("spike", fnm_spike)
        set YeetRig = BuildRig("yeet", fnm_yeet)
        var CannonFx : []vfx_spawner_device = array{}
        var StrikeFx : ?vfx_spawner_device = false
        var StrikeHome : ?transform = false
        for (Object : FindCreativeObjectsWithTag(fnm_cannon_fx), Device := vfx_spawner_device[Object]):
            Device.Disable()
            set CannonFx += array{Device}
        for (Object : FindCreativeObjectsWithTag(fnm_cannon_strike), Device := vfx_spawner_device[Object]):
            Device.Disable()
            set StrikeFx = option{Device}
            set StrikeHome = option{Device.GetTransform()}
        BlastRig := BuildRig("blast", fnm_cannon_blast)
        var Beams : []creative_prop = array{}
        var BeamFull : []transform = array{}
        for (Object : FindCreativeObjectsWithTag(fnm_race_beam), Beam := creative_prop[Object]):
            set Beam.CanBeDamaged = false
            set BeamFull += array{Beam.GetTransform()}
            set Beams += array{Beam}
            Beam.Hide()
        Pinned := if (A := Arena?, A.Boss?) then true else false
        set RaceRig = fnm_cannon_rig{Fx := CannonFx, Strike := StrikeFx, StrikeHome := StrikeHome, Blasts := BlastRig, Nuke := false, Beams := Beams, BeamFull := BeamFull, PinnedBoss := Pinned, RaceLaser := true}
        # The coil crackle loops forever: spawned once, never stacked.
        if (RaceCoils.Length = 0):
            set RaceCoils = FnmSpawnCoils(RaceRig.BeamFull, FnmRaceCannonCoilBack)
        for (Object : FindCreativeObjectsWithTag(fnm_race_titan), Device := animated_mesh_device[Object]):
            RaceTitan.Add(Device, FnmBmSlotOf(Object))
        # The fall clip has played itself down at the session start: Reset rewinds it (fnm_titan.verse).
        RaceTitan.Reset()
        var RaceLetters : int = 0
        for (Object : FindCreativeObjectsWithTag(fnm_race_letter), Letter := creative_prop[Object]):
            set Letter.CanBeDamaged = false
            spawn{ FaceLetter(Letter, Letter.GetTransform().Translation, FnmBmSlotOf(Object) - 1, true) }
            set RaceLetters += 1
        Print("FNM: cannons: {CannonFx.Length} legacy muzzle vfx (0 expected: the muzzle discharge is Niagara), strike {FnmYesNo(if (StrikeFx?) then true else false)}, {BlastRig.Parts.Length} blasts, {Beams.Length} lasers, {RaceCoils.Length} coil crackles; race titan {RaceTitan.Found()} clips, {RaceLetters} letters")
        for (Object : FindCreativeObjectsWithTag(fnm_pickup), Trigger := trigger_device[Object]):
            Handler := fnm_pad_handler{Director := Self, Index := PadCount, Kind := ItemKind(Object)}
            Trigger.TriggeredEvent.Subscribe(Handler.OnTriggered)
            set PadTriggers += array{Trigger}
            set PadCount += 1
        for (Object : FindCreativeObjectsWithTag(fnm_grant), Trigger := trigger_device[Object]):
            Kind := ItemKind(Object)
            if (set GrantTriggers[Kind] = Trigger) {}
        Print("FNM: {PadCount} pickup rows, {GrantTriggers.Length} item granters")
        for (Object : FindCreativeObjectsWithTag(fnm_penalty_cam), Camera := gameplay_camera_orbit_device[Object]):
            set PenaltyCam = option{Camera}
        for (Object : FindCreativeObjectsWithTag(fnm_loadout), Trigger := trigger_device[Object]):
            set LoadoutTrigger = option{Trigger}
        for (Object : FindCreativeObjectsWithTag(fnm_mud), Device := movement_modulator_device[Object]):
            set MudDevice = option{Device}
        for (Object : FindCreativeObjectsWithTag(fnm_boost), Device := movement_modulator_device[Object]):
            set BoostDevice = option{Device}
        var SliderCount : int = 0
        for (Object : FindCreativeObjectsWithTag(fnm_slider), Slider := creative_prop[Object]):
            set Slider.CanBeDamaged = false
            set SliderCount += 1
            spawn{ Slide(Slider) }
        Print("FNM: boost {FnmYesNo(if (BoostDevice?) then true else false)}, {SliderCount} sliders")
        for (Object : FindCreativeObjectsWithTag(fnm_ice_floor), Device := player_movement_settings_device[Object]):
            set IceFloor = option{Device}
            # The device adds itself to every player at game start unless its bAddToPlayersOnStart is off, which put
            # stations 1-5 on faint ice (Aaron 2026-10-06). Undo it here whatever the placed device says.
            Device.RemoveFromAll()
        for (Object : FindCreativeObjectsWithTag(fnm_ice_zone), Zone := mutator_zone_device[Object]):
            Zone.Enable()
            Zone.AgentEntersEvent.Subscribe(OnIceEnter)
            Zone.AgentExitsEvent.Subscribe(OnIceExit)
            set IceZones += array{Zone}
        Print("FNM: {IceZones.Length} ice zones, ice floor device {FnmYesNo(if (IceFloor?) then true else false)}")
        set FrostFx = FindFx(fnm_pp_frost)
        set MudFx = FindFx(fnm_pp_mud)
        set DizzyFx = FindFx(fnm_pp_dizzy)
        NewAudio := fnm_audio{Owner := Self}
        NewAudio.Build()
        set Audio = option{NewAudio}
        Print("FNM: penalty camera {FnmYesNo(if (PenaltyCam?) then true else false)}, loadout trigger {FnmYesNo(if (LoadoutTrigger?) then true else false)}, mud {FnmYesNo(if (MudDevice?) then true else false)}")
        Print("FNM: screen fx frost {FnmYesNo(if (FrostFx?) then true else false)}, mud {FnmYesNo(if (MudFx?) then true else false)}, dizzy {FnmYesNo(if (DizzyFx?) then true else false)}; {Penalties.Length} penalties in the pool")
        if (Stations.Length = 0):
            Print("FNM: fnm_director found no stations: tag an entry teleporter fnm_station_01 + fnm_entry.")
        else if (Cartridges.Length = 0):
            Print("FNM: the slot holds no cartridges")
        else:
            WarnAboutDoorCounts()
            for (StationIndex -> Station : Stations):
                for (DoorIndex -> Door : Station.Doors):
                    Handler := fnm_door_handler{Director := Self, StationIndex := StationIndex, DoorIndex := DoorIndex}
                    Door.TriggeredEvent.Subscribe(Handler.OnTriggered)
            # The arena's pads answer like a station's doors, as station index Stations.Length (its stage - 1).
            if (A := Arena?):
                for (DoorIndex -> Pad : A.Station.Doors):
                    Handler := fnm_door_handler{Director := Self, StationIndex := Stations.Length, DoorIndex := DoorIndex}
                    Pad.TriggeredEvent.Subscribe(Handler.OnTriggered)
                if (Boss := A.Boss?):
                    Boss.Disable()
                    Boss.SpawnedEvent.Subscribe(OnBossSpawned)
                    Boss.EliminatedEvent.Subscribe(OnBossEliminated)
                if (Adds := A.Adds?):
                    Adds.Disable()
                    Adds.SpawnedEvent.Subscribe(OnGuardSpawned)
                    Adds.EliminatedEvent.Subscribe(OnGuardEliminated)
                spawn{ BossLoop() }
            set Ready = true
            StationTags := FnmStationTags()
            set GuardSpawners = for (K -> Station : Stations):
                if (StationTag := StationTags[K]) then FindGuards(StationTag) else false
            set GuardsUp = for (Spawner : GuardSpawners) { false }
            for (MaybeSpawner : GuardSpawners, Spawner := MaybeSpawner?):
                Spawner.Disable()
                Spawner.SpawnedEvent.Subscribe(OnGuardSpawned)
                Spawner.EliminatedEvent.Subscribe(OnGuardEliminated)
            # A station with no spawner simply has no guards (station 1, the warm-up, since G9: tools/build_guards.py).
            var NoGuards : string = ""
            for (K -> MaybeSpawner : GuardSpawners, not MaybeSpawner?):
                Separator := if (NoGuards = "") then "" else ", "
                set NoGuards += "{Separator}{K + 1}"
            Listed := if (NoGuards = "") then "-" else NoGuards
            Print("FNM: {CountGuardStations()} stations have guards (none at: {Listed})")
            spawn{ GuardLoop() }
            spawn{ DoorWatch() }
            spawn{ RaceLoop() }
            SetUpVictoryArea()
            BuildAnalytics()
            Playspace := GetPlayspace()
            Playspace.PlayerAddedEvent().Subscribe(OnPlayerAdded)
            Playspace.PlayerRemovedEvent().Subscribe(OnPlayerRemoved)
            for (Joined : Playspace.GetPlayers()):
                StartPlayer(Joined)

    # Door letter index (0 = A .. 3 = D) from an object's tags; -1 if it has no door tag.
    DoorLetter(Object:creative_object_interface)<transacts>:int =
        ObjectTags := Object.GetTags()
        if (ObjectTags.Has[fnm_door_a{}]) then 0
        else if (ObjectTags.Has[fnm_door_b{}]) then 1
        else if (ObjectTags.Has[fnm_door_c{}]) then 2
        else if (ObjectTags.Has[fnm_door_d{}]) then 3
        else -1

    # One station's tagged parts: its entry teleporter, its doors in A..D order (missing letters skipped)
    # and each door's barrier (if any).
    FindStationParts(StationTag:castable_subtype(tag)):tuple(?teleporter_device, []trigger_device, []?barrier_device) =
        var Entry : ?teleporter_device = false
        var Triggers : []?trigger_device = array{false, false, false, false}
        var Barriers : []?barrier_device = array{false, false, false, false}
        for (Object : FindCreativeObjectsWithTag(StationTag)):
            if (Teleporter := teleporter_device[Object]):
                set Entry = option{Teleporter}
            else if (Trigger := trigger_device[Object]):
                if (set Triggers[DoorLetter(Object)] = option{Trigger}) {}
            else if (Barrier := barrier_device[Object]):
                if (set Barriers[DoorLetter(Object)] = option{Barrier}) {}
        Doors := for (MaybeDoor : Triggers, Door := MaybeDoor?) { Door }
        Passages := for (Letter -> MaybeDoor : Triggers, MaybeDoor?, Passage := Barriers[Letter]) { Passage }
        (Entry, Doors, Passages)

    # Stations 1, 2, ... in order until the first station tag with no entry teleporter. A wrong answer
    # returns the player to their station's entry; a right answer sends them to the next entry (last
    # station: the fnm_finish teleporter).
    BuildStations():[]fnm_station =
        var Finish : ?teleporter_device = false
        for (Object : FindCreativeObjectsWithTag(fnm_finish), Teleporter := teleporter_device[Object]):
            set Finish = option{Teleporter}
        set FinishPad = Finish
        var Entries : []teleporter_device = array{}
        var DoorSets : [][]trigger_device = array{}
        var PassageSets : [][]?barrier_device = array{}
        var Searching : logic = true
        for (StationTag : FnmStationTags()):
            Parts := FindStationParts(StationTag)
            if (Searching?, Entry := Parts(0)?):
                set Entries = Entries + array{Entry}
                set DoorSets = DoorSets + array{Parts(1)}
                set PassageSets = PassageSets + array{Parts(2)}
            else:
                set Searching = false
        for (K -> Entry : Entries, StationDoors := DoorSets[K], StationPassages := PassageSets[K]):
            var Next : teleporter_device = Entry
            if (Following := Entries[K + 1]):
                set Next = Following
            else if (A := Arena?):
                set Next = A.Station.RetryTeleporter
            else if (FinishPoint := Finish?):
                set Next = FinishPoint
            var OverridePercent : int = -1
            if (Value := DifficultyOverrides[K]):
                set OverridePercent = Value
            var RetryAt : ?vector3 = RetrySpotFor(StationDoors)
            if (Spot := RetryAt?):
                Zone := DoorZoneAt(StationDoors, StationPassages, Spot)
                if (Zone >= 0):
                    Print("FNM: WARNING station {K + 1}: retry spot {Spot} is inside door {FnmChoiceLetter(Zone)}'s zone (clear no); fallback {FnmYesNo(RetryFallback)}")
                    if (RetryFallback?) then set RetryAt = false
                else:
                    Print("FNM: station {K + 1}: retry spot {Spot}, clear yes")
            Print("FNM: station {K + 1}: {StationDoors.Length} doors, {CountPassages(StationPassages)} passages")
            fnm_station{Doors := StationDoors, Passages := StationPassages, RetryTeleporter := Entry, NextTeleporter := Next, DifficultyOverride := OverridePercent, RetrySpot := RetryAt}

    # The boss arena from its tags: the entry and the four pads (fnm_boss, read like a station), the exit gate, the boss's
    # Megabrute creature spawner and the adds' guard spawner. No fnm_boss entry teleporter = no arena (another map):
    # nothing changes.
    BuildArena():?fnm_arena =
        Parts := FindStationParts(fnm_boss)
        var Gate : ?barrier_device = false
        for (Object : FindCreativeObjectsWithTag(fnm_boss_gate), Barrier := barrier_device[Object]):
            set Gate = option{Barrier}
        var Boss : ?creature_spawner_device = false
        var BossHome : ?transform = false
        for (Object : FindCreativeObjectsWithTag(fnm_race_megaboss), Spawner := creature_spawner_device[Object]):
            set Boss = option{Spawner}
            set BossHome = option{Spawner.GetTransform()}
        var Adds : ?guard_spawner_device = false
        for (Object : FindCreativeObjectsWithTag(fnm_boss_adds), Spawner := guard_spawner_device[Object]):
            set Adds = option{Spawner}
        if (Entry := Parts(0)?):
            Print("FNM: arena: {Parts(1).Length} pads, gate {FnmYesNo(if (Gate?) then true else false)}, boss {FnmYesNo(if (Boss?) then true else false)}, adds {FnmYesNo(if (Adds?) then true else false)}")
            ArenaStation := fnm_station{Doors := Parts(1), Passages := array{}, RetryTeleporter := Entry, NextTeleporter := Entry, DifficultyOverride := 100}
            option{fnm_arena{Station := ArenaStation, Gate := Gate, Boss := Boss, BossHome := BossHome, Adds := Adds}}
        else:
            Print("FNM: arena: none (no fnm_boss entry teleporter)")
            false

    # BOSS BATTLE mode from its tags (fnm_bossmode.verse): the fnm_bm entry and pads read like a station; the boss mode
    # finds the rest itself. Its pads and perches answer through their handlers; its two loops run for the whole game.
    BuildBossMode():void =
        Parts := FindStationParts(fnm_bm)
        if (Entry := Parts(0)?):
            Station := fnm_station{Doors := Parts(1), Passages := array{}, RetryTeleporter := Entry, NextTeleporter := Entry, DifficultyOverride := -1}
            BM := fnm_boss_mode{Director := Self, Arena := fnm_bm_arena{Station := Station}}
            BM.Build()
            for (DoorIndex -> Pad : Station.Doors):
                Pad.TriggeredEvent.Subscribe(fnm_bm_pad_handler{Director := Self, DoorIndex := DoorIndex}.OnTriggered)
            for (K -> MaybeTrigger : BM.Arena.PerchTriggers, Trigger := MaybeTrigger?):
                Trigger.TriggeredEvent.Subscribe(fnm_bm_perch_handler{Director := Self, Perch := K + 1}.OnTriggered)
            for (K -> MaybeChest : BM.Arena.Chests, Chest := MaybeChest?):
                Chest.InteractedWithEvent.Subscribe(fnm_bm_chest_handler{Director := Self, Perch := K + 1}.OnOpened)
            set BossMode = option{BM}
            spawn{ BM.SpawnLoop() }
            spawn{ BM.BossLoop() }
        else:
            Print("FNM: boss mode: none (no fnm_bm entry teleporter)")

    # A boss-mode pad: answered like OnDoor (one at a time per player, on the trigger event only: no position backstop).
    OnBmPad(MaybeAgent:?agent, DoorIndex:int):void =
        if (Ready?, Agent := MaybeAgent?, Visitor := player[Agent], State := PlayerStates[Visitor], BM := BossMode?):
            if (State.Mode = fnm_mode.Boss, not State.Finished?, not State.Busy?, not State.Picking?, State.CurrentItem >= 0):
                if (TooSoon(State, "pad {FnmChoiceLetter(DoorIndex)}")?) then return
                set State.Busy = true
                set State.LastAccept = GetSimulationElapsedTime()
                spawn{ BM.OnPad(State, DoorIndex) }

    # A boss-mode perch's hidden trigger (1..4).
    OnBmPerch(MaybeAgent:?agent, Perch:int):void =
        if (Ready?, Agent := MaybeAgent?, Visitor := player[Agent], State := PlayerStates[Visitor], BM := BossMode?):
            BM.OnPerch(State, Perch)

    # A boss-mode perch's weapon chest (1..4) was opened (its hidden button held).
    OnBmChest(Agent:agent, Perch:int):void =
        if (Ready?, Visitor := player[Agent], State := PlayerStates[Visitor], BM := BossMode?):
            BM.OnChest(State, Perch)

    # The station a player answers at: the boss-mode arena in boss mode, else StationFor their stage.
    StationOf(State:fnm_player_state)<transacts>:?fnm_station =
        if (State.Mode = fnm_mode.Boss, BM := BossMode?) then option{BM.Arena.Station} else StationFor(State.Stage)

    # The station played at stage Stage: Stations[Stage - 1], or the arena's at stage Stations.Length + 1.
    StationFor(Stage:int)<transacts>:?fnm_station =
        if (Station := Stations[Stage - 1]) then option{Station}
        else if (Stage = Stations.Length + 1, A := Arena?) then option{A.Station}
        else false

    # True while the player is at the arena stage.
    AtArena(State:fnm_player_state)<transacts>:logic =
        if (State.Stage = Stations.Length + 1, Arena?) then true else false

    CountPassages(Passages:[]?barrier_device):int =
        var Count : int = 0
        for (MaybePassage : Passages, MaybePassage?):
            set Count += 1
        Count

    # Every movable object carrying RigTag, remembered at its parked transform.
    BuildRig(Name:string, RigTag:castable_subtype(tag)):fnm_rig =
        var Parts : []creative_object = array{}
        var Seen : int = 0
        for (Object : FindCreativeObjectsWithTag(RigTag)):
            set Seen += 1
            if (Prop := creative_prop[Object]):
                set Prop.CanBeDamaged = false
                set Parts += array{Prop}
            else if (Device := creative_device_base[Object]):
                set Parts += array{Device}
        Print("FNM: rig {Name}: {Parts.Length} movable of {Seen} tagged")
        Homes := for (Part : Parts) { Part.GetTransform() }
        fnm_rig{Name := Name, Parts := Parts, Homes := Homes}

    # The guard spawner (fnm_guards) among a station's tagged objects, if it has one.
    FindGuards(StationTag:castable_subtype(tag)):?guard_spawner_device =
        var Found : ?guard_spawner_device = false
        for (Object : FindCreativeObjectsWithTag(StationTag), Object.GetTags().Has[fnm_guards{}], Spawner := guard_spawner_device[Object]):
            set Found = option{Spawner}
        Found

    CountGuardStations():int =
        var Count : int = 0
        for (MaybeSpawner : GuardSpawners, MaybeSpawner?):
            set Count += 1
        Count

    # G10 analytics (TEAM.md seam with S, tools/build_analytics.py): the analytics_device tagged fnm_analytics + a station's
    # tag per station, + fnm_finish for the finish, + fnm_boss for the titan's kill. Missing ones are simply not found.
    BuildAnalytics():void =
        StationTags := FnmStationTags()
        set StationAnalytics = for (K -> Station : Stations):
            var Found : ?analytics_device = false
            if (StationTag := StationTags[K]):
                for (Object : FindCreativeObjectsWithTag(StationTag), Object.GetTags().Has[fnm_analytics{}], Device := analytics_device[Object]):
                    set Found = option{Device}
            Found
        for (Object : FindCreativeObjectsWithTag(fnm_analytics), Device := analytics_device[Object]):
            if (Object.GetTags().Has[fnm_finish{}]) then set FinishAnalytics = option{Device}
            else if (Object.GetTags().Has[fnm_boss{}]) then set BossAnalytics = option{Device}
        var Count : int = 0
        for (MaybeDevice : StationAnalytics, MaybeDevice?):
            set Count += 1
        Print("FNM: analytics: {Count} of {Stations.Length} stations, finish {FnmYesNo(if (FinishAnalytics?) then true else false)}, boss {FnmYesNo(if (BossAnalytics?) then true else false)}")

    # Submits Player on an analytics device if there is one, logged with what it counts.
    Analytics(MaybeDevice:?analytics_device, Player:player, What:string):void =
        if (Device := MaybeDevice?):
            Device.Submit(Player)
            Print("FNM: analytics {What}")

    # Hallway boxes for the skip guard: each station from 2 m before its entry pad to the back of its vestibules,
    # as wide as its doors reach, then the finish hallway (FinishHallwayLength past its pad, as wide as the last
    # station).
    BuildHallways():[]fnm_hallway =
        var Boxes : []fnm_hallway = array{}
        var LastHalf : float = 1200.0
        for (Station : Stations):
            Entry := Station.RetryTeleporter.GetTransform().Translation
            var Half : float = 300.0
            var Back : float = Entry.Y + 2850.0
            for (Door : Station.Doors):
                Zone := Door.GetTransform()
                set Half = Max(Half, Abs(Zone.Translation.X - Entry.X) + 300.0)
                set Back = Max(Back, Zone.Translation.Y + TriggerHalf * Zone.Scale.Y + 100.0)
            for (MaybePassage : Station.Passages, Passage := MaybePassage?):
                set Back = Max(Back, Passage.GetTransform().Translation.Y + 100.0)
            set LastHalf = Half
            set Boxes += array{fnm_hallway{MinX := Entry.X - Half, MaxX := Entry.X + Half, MinY := Entry.Y - 200.0, MaxY := Back, Z := Entry.Z}}
        # The boss arena (stage Stations.Length + 1) from 2 m before its entry pad to its exit gate.
        if (A := Arena?):
            At := A.Station.RetryTeleporter.GetTransform().Translation
            var Back : float = At.Y + 2900.0
            if (Gate := A.Gate?):
                set Back = Gate.GetTransform().Translation.Y + 100.0
            set Boxes += array{fnm_hallway{MinX := At.X - LastHalf, MaxX := At.X + LastHalf, MinY := At.Y - 200.0, MaxY := Back, Z := At.Z}}
        if (Pad := FinishPad?):
            At := Pad.GetTransform().Translation
            set Boxes += array{fnm_hallway{MinX := At.X - LastHalf, MaxX := At.X + LastHalf, MinY := At.Y - 200.0, MaxY := At.Y + FinishHallwayLength, Z := At.Z}}
        Boxes

    # Index of the hallway Here is in (0-based; Stations.Length = the arena if there is one, then the finish hallway), or -1.
    HallwayAt(Here:vector3):int =
        var Found : int = -1
        for (Index -> Box : Hallways, Here.X >= Box.MinX, Here.X <= Box.MaxX, Here.Y >= Box.MinY, Here.Y <= Box.MaxY, Abs(Here.Z - Box.Z) <= HallwayHeight):
            set Found = Index
        Found

    # True while any player still racing is on stage Index + 1 (in that station's hallway).
    StationOccupied(Index:int):logic =
        var Found : logic = false
        # A player choosing a skill is held still at station 1: no guards for them. Boss-mode players are in their own arena.
        for (State : PlayerStates, State.Mode = fnm_mode.Race, not State.Finished?, not State.Picking?, State.Stage = Index + 1):
            set Found = true
        Found

    # Guards are up only where a player is: a station's spawner is reset and enabled when its first player
    # arrives (it fills up to its own Guard Count, a guard every second), and disabled, despawning them, once
    # nobody is left there. A guard a player eliminates stays down until the station is emptied and refilled.
    GuardLoop()<suspends>:void =
        loop:
            for (Index -> MaybeSpawner : GuardSpawners, Spawner := MaybeSpawner?, Up := GuardsUp[Index]):
                Occupied := StationOccupied(Index)
                if (Occupied?, not Up?):
                    Spawner.Reset()
                    Spawner.Enable()
                    if (set GuardsUp[Index] = true) {}
                    Print("FNM: guards up at station {Index + 1}")
                    for (State : PlayerStates, not State.Finished?, not State.Picking?, State.Stage = Index + 1):
                        Sound(State.Player, fnm_cue.GuardsUp)
                else if (not Occupied?, Up?):
                    Spawner.Disable()
                    if (set GuardsUp[Index] = false) {}
                    Print("FNM: guards down at station {Index + 1}")
            Sleep(GuardCheckSeconds)

    OnGuardSpawned(Guard:agent):void =
        set GuardsSpawned += 1
        Print("FNM: guard spawned ({GuardsSpawned} so far)")

    OnGuardEliminated(Result:device_ai_interaction_result):void =
        if (Source := Result.Source?, Player := player[Source]):
            Print("FNM: a player eliminated a guard")
        else:
            Print("FNM: a guard was eliminated")

    # Notices a player's elimination (any cause) and, once they respawn, puts them back at the entry of the
    # station they were on with the starting loadout. (A Spike penalty waits for this itself.) An elimination
    # stops a speed boost but keeps the streak: a guard kill is not a wrong answer (a Spike death is, and
    # HandleDoor already reset the streak for it).
    WatchLife(State:fnm_player_state)<suspends>:void =
        var WasAlive : logic = true
        loop:
            Sleep(0.25)
            if (not PlayerStates[State.Player]) then break
            Alive := if (Character := State.Player.GetFortCharacter[], Character.IsActive[]) then true else false
            if (WasAlive?, not Alive?):
                Print("FNM: player eliminated at stage {State.Stage}")
                StopBoost(State)
            else if (not WasAlive?, Alive?):
                Respawned(State)
            set WasAlive = Alive

    Respawned(State:fnm_player_state):void =
        WideCamera(State.Player, false)
        # A boss-mode player comes back at that arena's entry (counted there).
        if (State.Mode = fnm_mode.Boss, BM := BossMode?):
            BM.Respawned(State)
            return
        # An arena-stage player (the boss's AR, an add) comes back at the arena's entry.
        Stage := Min(State.Stage, Stations.Length + (if (Arena?) then 1 else 0))
        if (Station := StationFor(Stage)?):
            SendTo(State.Player, Station.RetryTeleporter)
        GiveLoadout(State.Player)
        Print("FNM: respawned at stage {Stage}")
        if (State.Picking?):
            HoldStill(State)
        if (not State.Busy?, not State.Finished?):
            spawn{ FlashNotice(State, if (Stage > Stations.Length) then "Eliminated! Back to the arena entry." else "Eliminated! Back to the start of station {Stage}.") }

    FindFx(FxTag:castable_subtype(tag)):?post_process_device =
        var Found : ?post_process_device = false
        for (Object : FindCreativeObjectsWithTag(FxTag), Device := post_process_device[Object]):
            set Found = option{Device}
        Found

    # A station with fewer doors than an item has choices could hide the right answer (any cartridge's item).
    WarnAboutDoorCounts():void =
        var MostChoices : int = 0
        for (Each : Cartridges, Item : Each.Items):
            set MostChoices = Max(MostChoices, Item.Choices.Length)
        for (StationIndex -> Station : Stations, Station.Doors.Length < MostChoices):
            StationNumber := StationIndex + 1
            DoorCount := Station.Doors.Length
            Print("FNM: station {StationNumber} has {DoorCount} doors but items have up to {MostChoices} choices. Re-insert the cartridge with a matching max_choices.")

    # ---------------------------------------------------------------- players

    OnPlayerAdded(Joined:player):void =
        StartPlayer(Joined)

    OnPlayerRemoved(Departed:player):void =
        if (State := PlayerStates[Departed]):
            if (BM := BossMode?) then BM.Leave(State)
            set State.Finished = true
        for (Station : Stations, MaybePassage : Station.Passages, Passage := MaybePassage?):
            Passage.RemoveFromIgnoreList(Departed)
        if (A := Arena?, Gate := A.Gate?):
            Gate.RemoveFromIgnoreList(Departed)
        if (Device := IceFloor?):
            Device.RemoveFrom(Departed)
        if (A := Audio?):
            A.Forget(Departed)
        var Remaining : [player]fnm_player_state = map{}
        for (Key -> Value : PlayerStates, Key <> Departed):
            if (set Remaining[Key] = Value) {}
        set PlayerStates = Remaining

    # A joining player: HUD up, held still at station 1, then the skill picker (or an automatic pick).
    StartPlayer(Joined:player):void =
        if (Ready?, not PlayerStates[Joined]):
            Hud := fnm_hud{}
            Hud.Attach(Joined)
            Hud.SetListener(Self)
            Hud.SetTitle("DOORS OF DOOM", "Choose your skill")
            Hud.ClearQuestion()
            Hud.SetClock(FnmClock(0.0))
            State := fnm_player_state{Player := Joined, Hud := Hud}
            if (set PlayerStates[Joined] = State) {}
            # Start everyone at station 1 facing the doors, whatever spawn pad the island used.
            if (First := Stations[0]):
                SendTo(Joined, First.RetryTeleporter)
            HoldStill(State)
            Sound(Joined, fnm_cue.Welcome)
            spawn{ WatchLife(State) }
            # The ice device may have added itself to this player at game start (its bAddToPlayersOnStart): log it,
            # since that was the "faint ice everywhere" of 2026-10-06, and take it off.
            if (Device := IceFloor?):
                var WasOn : logic = false
                for (Agent : Device.GetRegisteredAgents(), Registered := player[Agent], Registered = Joined):
                    set WasOn = true
                if (WasOn?):
                    Device.RemoveFrom(Joined)
                    Print("FNM: ice floor was already on the joining player (device add-on-start); removed")
            BeginPicking(State)

    # Held still while choosing (they may look around); the countdown releases them.
    HoldStill(State:fnm_player_state):void =
        if (Character := State.Player.GetFortCharacter[]):
            Character.PutInStasis(stasis_args{AllowTurning := true, AllowFalling := false, AllowEmotes := false})

    # ---------------------------------------------------------------- skill picker (PROTOCOL 6b)

    # The distinct grades in the slot, in registry order (the registry is sorted by grade, so this is 6b's order).
    GradeList():[]string =
        var Grades : []string = array{}
        for (Each : Cartridges):
            var Seen : logic = false
            for (Grade : Grades, Grade = Each.Grade):
                set Seen = true
            if (not Seen?):
                set Grades += array{Each.Grade}
        Grades

    # Picks for the player at once (DebugAutoBoss starts boss mode; DebugAutoPick, or a slot with one cartridge), else
    # shows the picker: the grade step (with BOSS BATTLE when the map has its arena), or straight to the skill step when
    # there is only one grade and no boss mode.
    BeginPicking(State:fnm_player_state):void =
        set State.Picking = true
        UpdateCompact(State)
        SetMusic(State.Player, 0)
        if (DebugAutoBoss?, BM := BossMode?):
            BM.Start(State)
        else if (DebugAutoPick >= 0, Cartridges[DebugAutoPick], DebugPickerSeconds <= 0.0):
            Pick(State, DebugAutoPick)
        else if (Cartridges.Length = 1, not BossMode?):
            Pick(State, 0)
        else:
            if (DebugAutoPick >= 0, not Cartridges[DebugAutoPick]):
                Print("FNM: DebugAutoPick {DebugAutoPick} is out of range ({Cartridges.Length} cartridges); showing the picker")
            if (DebugAutoPick >= 0, Cartridges[DebugAutoPick]):
                spawn{ DebugPickLater(State) }
            Grades := GradeList()
            WithBoss := if (BossMode?) then true else false
            if (Grades.Length = 1, not WithBoss?, Only := Grades[0]):
                ShowSkills(State, Only, false)
            else:
                State.Hud.ShowGradeStep(Grades, WithBoss)
            Print("FNM: picker shown: {Grades.Length} grades, {Cartridges.Length} skills")
            # The picker's own bed (G9 D2, music_menu) while they choose; the countdown stops it (Countdown), boss mode
            # swaps it for the boss bed (fnm_boss_mode.Start).
            SetMusic(State.Player, FnmBedMenu)
            if (State.Picks = 0):
                spawn{ ChooseLater(State) }

    # DebugPickerSeconds with the picker up, then DebugAutoPick's cartridge, if the player is still picking.
    DebugPickLater(State:fnm_player_state)<suspends>:void =
        Sleep(DebugPickerSeconds)
        if (PlayerStates[State.Player], State.Picking?):
            Print("FNM: debug pick after {FnmBmWholeSeconds(DebugPickerSeconds)} s of the picker")
            Pick(State, DebugAutoPick)

    # "Choose your grade and your skill." ChooseDelaySeconds after the welcome line (StartPlayer plays both in the same tick
    # otherwise, and the two announcer lines overlapped: ux_critique B1), if the player is still picking.
    ChooseLater(State:fnm_player_state)<suspends>:void =
        Sleep(ChooseDelaySeconds)
        if (PlayerStates[State.Player], State.Picking?, State.Picks = 0):
            Sound(State.Player, fnm_cue.Choose)

    # The skill step for Grade: every cartridge of that grade, registry order, its title on the button and its
    # subtitle under it.
    ShowSkills(State:fnm_player_state, Grade:string, WithBack:logic):void =
        var Titles : []string = array{}
        var Subtitles : []string = array{}
        var Indices : []int = array{}
        for (K -> Each : Cartridges, Each.Grade = Grade):
            set Titles += array{Each.Title}
            set Subtitles += array{Each.Subtitle}
            set Indices += array{K}
        State.Hud.ShowSkillStep(Grade, Titles, Subtitles, Indices, WithBack)

    # A click on one of the player's HUD buttons (fnm_hud only reports clicks by its own player).
    OnPickerChoice<override>(Player:player, Kind:fnm_pick, Index:int):void =
        if (State := PlayerStates[Player]):
            # A picker click while not picking is a late click on a step that is already gone: ignored.
            if (Kind = fnm_pick.ChangeSkill):
                if (State.Finished?, not State.Picking?):
                    ChangeSkill(State)
            else if (Kind = fnm_pick.Close):
                if (State.Finished?, not State.Picking?):
                    CloseResults(State)
            else if (Kind = fnm_pick.Again):
                # PLAY AGAIN on the boss-mode win board.
                if (State.Finished?, not State.Picking?, State.Mode = fnm_mode.Boss, BM := BossMode?):
                    State.Hud.HideResults()
                    State.Hud.HideFinishButtons()
                    Print("FNM: boss mode play again")
                    BM.Start(State)
            else if (State.Picking?):
                if (Kind = fnm_pick.Boss):
                    if (BM := BossMode?):
                        Print("FNM: boss battle chosen")
                        BM.Start(State)
                else if (Kind = fnm_pick.Grade):
                    Grades := GradeList()
                    if (Grade := Grades[Index]):
                        Print("FNM: grade {Grade} chosen")
                        ShowSkills(State, Grade, if (Grades.Length > 1) then true else false)
                else if (Kind = fnm_pick.Skill):
                    Pick(State, Index)
                else:
                    Print("FNM: picker back")
                    State.Hud.ShowGradeStep(GradeList(), if (BossMode?) then true else false)

    # Gives the player cartridge Index: its tiers, pools, fresh decks and title; then the first question, the
    # loadout and the countdown. The debug hooks start on the first pick (they read the player's cartridge live).
    Pick(State:fnm_player_state, Index:int):void =
        if (Chosen := Cartridges[Index], Pools := CartridgePools[Index]):
            set State.Picking = false
            set State.Picks += 1
            set State.CartridgeIndex = Index
            set State.Cartridge = Chosen
            set State.TierCount = Chosen.Tiers.Length
            set State.TierPools = Pools
            set State.Decks = FnmShuffleAll(Pools)
            set State.Stage = 1
            # Personal best = the faster of this session's and the all-time one the island saved for them.
            SessionBest := if (Best := State.BestTimes[Index]) then Best else -1.0
            set State.BestTime = if (Saved := FnmSavedBest[State.Player, Chosen.Id], (SessionBest < 0.0 or Saved < SessionBest)) then Saved else SessionBest
            State.Hud.HidePicker()
            State.Hud.SetTitle(Chosen.Title, Chosen.Subtitle)
            DrawItem(State)
            ShowCurrent(State)
            State.Hud.SetClock(FnmClock(0.0))
            Print("FNM: picked {Chosen.Id} (grade {Chosen.Grade}) for the player")
            if (State.Picks = 1, DebugStartStage > 1, Start := StationFor(DebugStartStage)?):
                set State.Stage = DebugStartStage
                set State.Partial = true
                DrawItem(State)
                ShowCurrent(State)
                SendTo(State.Player, Start.RetryTeleporter)
                Print("FNM: debug start at stage {DebugStartStage}")
                if (AtArena(State)?):
                    EnterArena(State, true)
            GiveLoadout(State.Player)
            # The countdown holds them again; release the picker's hold first so the two never stack.
            if (Character := State.Player.GetFortCharacter[]):
                Character.ReleaseFromStasis()
            spawn{ Countdown(State) }
            if (State.Picks = 1):
                # With DebugAutoRightAnswers as well, the auto-right run takes the wrong doors itself (DebugAutoRight).
                if (DebugAutoWrongAnswers > 0, not DebugAutoRightAnswers?):
                    spawn{ DebugAutoWrong(State) }
                if (DebugPassageTest?):
                    spawn{ DebugPassage(State) }
                if (DebugDoorTest >= 0):
                    spawn{ DebugDoor(State) }
                if (DebugAutoRightAnswers?):
                    spawn{ DebugAutoRight(State) }
                if (DebugSkipTest?):
                    spawn{ DebugSkip(State) }
                if (DebugPickupTest?):
                    spawn{ DebugPickup(State) }

    # CHANGE SKILL (finish board or podium): cancels any pending restart and resets the run; then the picker again,
    # from station 1. Best times stay with their skill (BestTimes; Pick restores the chosen skill's).
    ChangeSkill(State:fnm_player_state):void =
        # Out of boss mode first (Mode back to Race, its boss line and banner off).
        if (State.Mode = fnm_mode.Boss, BM := BossMode?):
            BM.Leave(State)
            State.Hud.ClearFeedbackNow()
        set State.RunGeneration += 1
        State.Hud.HideFinishButtons()
        State.Hud.HideResults()
        for (Station : Stations, MaybePassage : Station.Passages, Passage := MaybePassage?):
            Passage.RemoveFromIgnoreList(State.Player)
        ResetArena(State)
        set State.Stage = 1
        set State.FirstTryCorrect = 0
        set State.Streak = 0
        set State.BestStreak = 0
        set State.Finished = false
        set State.Busy = false
        set State.CurrentItem = -1
        State.Hud.SetCountdown("")
        State.Hud.SetTarget("")
        State.Hud.ClearDelta()
        State.Hud.SetStreak("")
        State.Hud.ClearVerdictNow()
        State.Hud.SetTitle("DOORS OF DOOM", "Choose your skill")
        State.Hud.ClearQuestion()
        State.Hud.SetClock(FnmClock(0.0))
        if (First := Stations[0]):
            SendTo(State.Player, First.RetryTeleporter)
        HoldStill(State)
        Print("FNM: change skill")
        BeginPicking(State)

    # ---------------------------------------------------------------- questions

    # Tier for stage Stage of the player's cartridge, honouring that station's DifficultyOverride.
    StationTier(State:fnm_player_state, Stage:int):int =
        # The boss arena always plays the hardest tier.
        if (Stage > Stations.Length):
            return Max(1, State.TierCount)
        var OverridePercent : int = -1
        if (Station := Stations[Stage - 1]):
            set OverridePercent = Station.DifficultyOverride
        FnmTierForStage(Stage, Stations.Length, State.TierCount, OverridePercent)

    # Draws the player's next item for their current stage (without replacement, per player). At the arena stage
    # REDEMPTION (R4) comes first: while the run's RedeemQueue holds missed stations, the question is drawn from the head
    # station's tier (RedeemStage, the slate's "REDEMPTION: STATION N" line); then the arena's hardest tier.
    DrawItem(State:fnm_player_state):void =
        set State.RedeemStage = 0
        var Tier : int = StationTier(State, State.Stage)
        if (State.Mode = fnm_mode.Race, AtArena(State)?, Next := State.RedeemQueue[0]):
            set State.RedeemStage = Next
            set Tier = StationTier(State, Next)
            Print("FNM: redemption question for station {Next} (tier {Tier}), {State.RedeemQueue.Length} queued")
        if (Pool := State.TierPools[Tier - 1], Deck := State.Decks[Tier - 1]):
            Draw := FnmDraw(Deck, Pool)
            if (set State.Decks[Tier - 1] = Draw.Rest) {}
            set State.CurrentItem = Draw.ItemIndex
            set State.MissedCurrent = false
            if (Item := State.Cartridge.Items[Draw.ItemIndex]):
                set State.Order = Shuffle(for (Index := 0..Item.Choices.Length - 1) { Index })

    # The player's current item on the slate: its caption ("STATION 3/10  -  <tier>"; "FINAL BOSS" in the arena, whose
    # hits are counted on the boss bar alone, or "REDEMPTION: STATION 3  -  <tier>" for a redemption question; plus "Only
    # A, B, C this time" when the item has fewer choices than the doors), the prompt and the choices in this showing's order.
    ShowCurrent(State:fnm_player_state):void =
        set State.SlateSerial += 1
        if (Item := State.Cartridge.Items[State.CurrentItem]):
            StageCount := Stations.Length
            TierName := FnmTierName(State.Cartridge.Tiers, Item.Tier)
            ArenaLine := if (State.RedeemStage > 0) then "REDEMPTION: STATION {State.RedeemStage}  -  {TierName}" else "FINAL BOSS"
            Caption := if (State.Mode = fnm_mode.Boss) then "BOSS BATTLE  -  Level {State.Level}/{FnmBmLevelCount()}  -  {State.Cartridge.Title}" else if (State.Stage > StageCount) then ArenaLine else "STATION {State.Stage}/{StageCount}  -  {StationTierLabel(TierName)}"
            StageLine := Caption + OnlyLetters(State, Item)
            Shown := for (Choice : State.Order, Text := Item.Choices[Choice]) { Text }
            State.Hud.ShowQuestion(StageLine, Item.Prompt, Shown)

    # "  -  Only A, B, C this time" when Item has fewer choices than the player's station has doors (or pads), else "":
    # said up front, not after a kid walks into the empty door ("No choice D here", ux_critique 3.1).
    OnlyLetters(State:fnm_player_state, Item:fnm_item)<transacts>:string =
        Doors := if (Station := StationOf(State)?) then Station.Doors.Length else 4
        if (Item.Choices.Length > 0, Item.Choices.Length < Doors):
            var Letters : string = ""
            for (K -> Choice : Item.Choices):
                Separator := if (K > 0) then ", " else ""
                set Letters += "{Separator}{FnmChoiceLetter(K)}"
            "  -  Only {Letters} this time"
        else:
            ""

    # A station's tier name for its slate caption: a tier named for a boss ("Boss Level", the top tier of order-of-ops-exponents
    # and integer-ops) reads "Final Stretch" at stations 9-10, where there is no boss (ux_critique P3); the arena keeps the name.
    StationTierLabel(TierName:string)<transacts>:string =
        if (FnmContains(TierName, "Boss")?) then "Final Stretch" else TierName

    # The baked choice behind door DoorIndex for this showing (-1 = no choice there).
    ChoiceAt(State:fnm_player_state, DoorIndex:int)<transacts>:int =
        if (Choice := State.Order[DoorIndex]) then Choice else -1

    # The door the current item's right answer is behind for this showing.
    AnswerDoor(State:fnm_player_state)<transacts>:int =
        var Door : int = 0
        if (Item := State.Cartridge.Items[State.CurrentItem]):
            for (Index -> Choice : State.Order, Choice = Item.Answer):
                set Door = Index
        Door

    # Student-facing text for wrong choice DoorIndex (PROTOCOL 6: ARITH text if missing).
    FeedbackFor(Item:fnm_item, DoorIndex:int):string =
        var Result : string = "Check your arithmetic."
        if (Line := Item.Feedback[DoorIndex], Line <> ""):
            set Result = Line
        Result

    # ---------------------------------------------------------------- doors

    OnDoor(MaybeAgent:?agent, StationIndex:int, DoorIndex:int):void =
        if (Ready?, Agent := MaybeAgent?, Visitor := player[Agent], State := PlayerStates[Visitor]):
            if (State.Mode = fnm_mode.Race, not State.Finished?, not State.Busy?, not State.Picking?):
                if (StationIndex = State.Stage - 1):
                    if (TooSoon(State, "door {FnmChoiceLetter(DoorIndex)}")?) then return
                    set State.Busy = true
                    set State.LastAccept = GetSimulationElapsedTime()
                    spawn{ HandleDoor(State, StationIndex, DoorIndex) }
                else if (StationIndex > State.Stage - 1):
                    spawn{ FlashNotice(State, "This is not your station. You are on station {State.Stage}.") }
                # An earlier station: they are walking back through a door they already passed. Ignore.

    # A door or pad event within RightCooldownSeconds of a right answer: dropped, and logged.
    TooSoon(State:fnm_player_state, What:string)<transacts>:logic =
        Since := GetSimulationElapsedTime() - State.LastRight
        if (Since < RightCooldownSeconds):
            Print("FNM: {What} event dropped {Since} s after a right answer")
            true
        else:
            false

    # A right answer: remembered for TooSoon, and any mud or dizzy penalty still running stops at once.
    Cleanse(State:fnm_player_state):void =
        set State.LastRight = GetSimulationElapsedTime()
        set State.PenaltyEpoch += 1
        if (State.Afflicted?):
            set State.Afflicted = false
            if (Mud := MudDevice?):
                Mud.Deactivate(State.Player)
            FxOff(State.Player, MudFx)
            FxOff(State.Player, DizzyFx)
            Print("FNM: penalty effects cleared by a right answer")

    # The player's current PenaltyEpoch (-1 when they have no state), for an effect to notice a Cleanse.
    EpochOf(Player:player)<transacts>:int =
        if (State := PlayerStates[Player]) then State.PenaltyEpoch else -1

    Afflict(Player:player):void =
        if (State := PlayerStates[Player]):
            set State.Afflicted = true

    HandleDoor(State:fnm_player_state, StationIndex:int, DoorIndex:int)<suspends>:void =
        if (StationIndex = Stations.Length, A := Arena?):
            HandlePad(State, A, DoorIndex)
            return
        # A door answered ends the retry hold's compact slate (the recap card or the next lesson takes the slate).
        EndRetryHold(State)
        if (Item := State.Cartridge.Items[State.CurrentItem], Station := Stations[StationIndex]):
            Choice := ChoiceAt(State, DoorIndex)
            if (Choice < 0):
                set State.Busy = false
                Letter := FnmChoiceLetter(DoorIndex)
                FlashNotice(State, "No choice {Letter} here")
            else if (Choice = Item.Answer):
                Cleanse(State)
                var Label : string = ""
                if (not State.MissedCurrent?):
                    set State.FirstTryCorrect += 1
                    set State.Streak += 1
                    set State.BestStreak = Max(State.BestStreak, State.Streak)
                    if (State.Streak >= 2) then set Label = "{State.Streak} IN A ROW!"
                    if (StreakCue := FnmStreakCue(State.Streak)?):
                        spawn{ SoundLater(State.Player, StreakCue, 0.9) }
                    spawn{ Boost(State, Min(MaxBoostSeconds, BoostSeconds + StreakBonusSeconds * (State.Streak - 1) * 1.0)) }
                    for (Milestone : array{3, 5, 7, 10}, Milestone = State.Streak):
                        Broadcast(FnmFeedStreak(State.Player, Milestone), "is on a {Milestone} streak!")
                    # G10: a SHIELD at streak 3, a STRIKE at 5, 10, 15 (named on the verdict: "3 IN A ROW!  +SHIELD").
                    set Label += EarnRewards(State)
                Sound(State.Player, if (State.MissedCurrent?) then fnm_cue.CorrectRetry else fnm_cue.Correct)
                State.Hud.FlashVerdict(true, Label)
                # Volt's card (picture only): fire when this answer makes a streak of 3 or more, else thumbs up.
                State.Hud.ShowVolt(if (State.Streak >= 3) then fnm_volt.Fire else fnm_volt.Thumbs)
                # The station's mark for the brag grid (a miss first queues it for REDEMPTION at the boss) and its analytics.
                MarkStation(State, State.Stage, if (State.MissedCurrent?) then FnmMarkMissed else FnmMarkFirstTry)
                Analytics(if (Device := StationAnalytics[StationIndex]) then Device else false, State.Player, "station {StationIndex + 1} cleared")
                Pace := RecordSplit(State)
                Solved := RecapOf(State, Item, DoorIndex, if (Pace = "") then "CORRECT!" else "CORRECT!  {Pace}")
                AdvancePlayer(State, Station, DoorIndex, false)
                set State.Busy = false
                if (not State.Finished?):
                    Recap(State, Solved, RecapSeconds)
            else:
                set State.MissedCurrent = true
                set State.Streak = 0
                StopBoost(State)
                # A held SHIELD takes this door's penalty, hold and clock charge instead (the streak and the first-try
                # credit are gone, the door stays shut, the same question comes back with its letters reshuffled).
                if (State.Shield?):
                    ShieldSaved(State, Station, StationIndex + 1, FeedbackFor(Item, Choice))
                    return
                Kind := PickPenalty()
                Past := FnmPenaltyPast(Kind)
                MissFeed(State, FnmFeedPenalty(State.Player, Past, StationIndex + 1), "You got {Past} at station {StationIndex + 1}", "got {Past} at station {StationIndex + 1}")
                Sound(State.Player, fnm_cue.Wrong)
                Tail := ChargeWrongDoor(State)
                State.Hud.FlashVerdict(false, FnmPenaltyLabel(Kind) + Tail)
                State.Hud.ShowVolt(fnm_volt.Wag)
                Lesson := FeedbackFor(Item, Choice)
                Shown := State.Hud.ShowFeedback(Lesson, NamedColors.Tomato)
                Punish(State.Player, Station, DoorIndex, Kind)
                Retry(State, Lesson)
        else:
            set State.Busy = false

    # The item the player just solved, as shown (before the next one is drawn), for the recap card.
    RecapOf(State:fnm_player_state, Item:fnm_item, DoorIndex:int, Verdict:string)<transacts>:fnm_recap =
        Shown := for (Choice : State.Order, Text := Item.Choices[Choice]) { Text }
        fnm_recap{Prompt := Item.Prompt, Choices := Shown, Right := DoorIndex, Steps := Item.Explanation, Verdict := Verdict}

    # The recap card (G9, ux_critique #5): the solved item stays on the slate for RecapSeconds (its right tile lit, the
    # worked steps, the verdict with the pace delta: fnm_hud ShowRecap), then the question already drawn for the player's
    # new stage. It replaces "Correct!  <explanation>" under the NEXT question, which shared that question's numbers and
    # read as its working (frame 02b). The flip happens only if nothing newer took the slate meanwhile (SlateSerial: a
    # door answered, a new run, the arena); fnm_hud's own generation makes a stale EndRecapIf a no-op too.
    # Seconds: RecapSeconds at a station; in the race arena at most RightCooldownSeconds (HandlePad).
    Recap(State:fnm_player_state, Solved:fnm_recap, Seconds:float)<suspends>:void =
        Generation := State.Hud.ShowRecap(Solved.Prompt, Solved.Choices, Solved.Right, Solved.Steps, Solved.Verdict)
        set State.SlateSerial += 1
        Serial := State.SlateSerial
        Print("FNM: recap up ({Solved.Verdict}), next question in {Seconds} s")
        Sleep(Seconds)
        if (PlayerStates[State.Player], State.SlateSerial = Serial, not State.Finished?, not State.Picking?, State.CurrentItem >= 0):
            State.Hud.EndRecapIf(Generation)
            ShowCurrent(State)
            Print("FNM: recap down, next question up at stage {State.Stage}")
        else:
            Print("FNM: recap superseded (no flip)")

    # Back on the retry spot after a wrong door (or pad): the same question with its letters shuffled again on the slate,
    # the wrong choice's lesson under it for WrongFeedbackSeconds (ShowQuestion cleared it), and doors answer again.
    # G10: the hold is a compact slate (fnm_hud SetCompact) for WrongFeedbackSeconds, so the wide camera shows the lintel
    # letters over the doors; a door answered sooner ends it (HandleDoor, EndRetryHold).
    Retry(State:fnm_player_state, Lesson:string)<suspends>:void =
        set State.RetryHold += 1
        Hold := State.RetryHold
        set State.RetryHolding = true
        UpdateCompact(State)
        if (not State.Finished?, State.CurrentItem >= 0):
            Reshuffle(State)
            ShowCurrent(State)
        Generation := State.Hud.ShowFeedback(Lesson, NamedColors.Tomato)
        set State.Busy = false
        Sleep(WrongFeedbackSeconds)
        State.Hud.ClearFeedbackIf(Generation)
        if (State.RetryHold = Hold) then EndRetryHold(State)

    # The retry hold is over (its time is up, or a door was answered): the slate goes back to full unless the arena keeps
    # it compact.
    EndRetryHold(State:fnm_player_state):void =
        if (State.RetryHolding?):
            set State.RetryHolding = false
            UpdateCompact(State)

    # The compact slate (fnm_hud SetCompact, H): question and choices only, smaller and higher, so the world behind reads.
    # On during a race player's retry hold and in the arena hall (from ArenaArrival to the end of the run); off at the
    # finish and in the picker. The HUD is told only on a change, logged.
    UpdateCompact(State:fnm_player_state):void =
        InArena := if (AtArena(State)?, State.ArenaArrived?) then true else false
        Want := if (State.Mode = fnm_mode.Race, not State.Finished?, not State.Picking?, (State.RetryHolding? or InArena?)) then true else false
        if (Want <> State.Compact):
            set State.Compact = Want
            State.Hud.SetCompact(Want)
            Print("FNM: compact slate {if (Want?) then "on" else "off"} (retry hold {FnmYesNo(State.RetryHolding)}, arena {FnmYesNo(InArena)})")

    # Door backstop (Aaron 2026-10-05: "sometimes I run through a door and correct or incorrect doesn't activate,
    # I run around that room a little and eventually it does"). A trigger fires only on ENTERING its zone, and an
    # event that arrives while the player is Busy is dropped, so a player could stand in a vestibule with nothing
    # happening until they left and came back. Every DoorWatchSeconds this checks each player against the trigger
    # boxes of their current station; a player who has stood in one for DoorDwellSeconds, with no door answer taken
    # since shortly before they entered, answers through it once. Logged, so a play log shows how often it saves one.
    DoorWatch()<suspends>:void =
        loop:
            Sleep(DoorWatchSeconds)
            for (Player -> State : PlayerStates):
                WatchDoors(State)
                WatchIce(State)
                WatchSkip(State)
                WatchArena(State)

    WatchDoors(State:fnm_player_state):void =
        Now := GetSimulationElapsedTime()
        var Inside : int = -1
        if (State.Mode = fnm_mode.Race, not State.Finished?, not State.Picking?, State.CurrentItem >= 0, Station := Stations[State.Stage - 1], Character := State.Player.GetFortCharacter[], Character.IsActive[]):
            set Inside = DoorZoneAt(Station.Doors, Station.Passages, Character.GetTransform().Translation)
        if (Inside <> State.ZoneDoor):
            set State.ZoneDoor = Inside
            set State.ZoneSince = Now
            set State.ZoneFired = false
        else if (Inside >= 0, not State.ZoneFired?, not State.Busy?, Now - State.ZoneSince >= DoorDwellSeconds, State.LastAccept < State.ZoneSince - 1.0):
            set State.ZoneFired = true
            Print("FNM: door {FnmChoiceLetter(Inside)} answered by position at stage {State.Stage} (no trigger event taken)")
            OnDoor(option{State.Player}, State.Stage - 1, Inside)

    # The door (index into Doors) whose zone Here is in, or -1. A zone is the trigger's box (TriggerHalf), its front face
    # at the door wall's back face (tools/build_course.py), on to the barrier: the WHOLE vestibule, since a player who
    # runs or jumps through the door can stop against the barrier, past the trigger box (2026-10-06, Aaron: a right door
    # did nothing until he moved around the room; the triggers were 60% of the vestibule then and this check mirrored
    # them). The backstop (WatchDoors) answers by these zones, and a retry spot must lie outside all of them.
    DoorZoneAt(Doors:[]trigger_device, Passages:[]?barrier_device, Here:vector3)<transacts>:int =
        var Inside : int = -1
        for (Index -> Door : Doors):
            Zone := Door.GetTransform()
            Front := Zone.Translation.Y - TriggerHalf * Zone.Scale.Y
            var Back : float = Zone.Translation.Y + TriggerHalf * Zone.Scale.Y
            if (MaybePassage := Passages[Index], Passage := MaybePassage?):
                set Back = Max(Back, Passage.GetTransform().Translation.Y)
            if (Abs(Here.X - Zone.Translation.X) <= TriggerHalf * Zone.Scale.X, Here.Y >= Front, Here.Y <= Back, Abs(Here.Z - ZoneCentre(Door).Z) <= 300.0):
                set Inside = Index
        Inside

    # A station's retry spot (G9, ux_critique #8): RetryStandOff in front of its door wall's front face, centred on its
    # doors, ArrivalLift above its floor, all read from its own door triggers (a trigger's box starts at the door wall's
    # back face, DoorWallThickness behind the front face; its bottom is the floor), since hallways sit at different X and
    # levels. 6 m in front of the doors (RetryStandOff) is still past every obstacle (the last ones stand 10 to 10.5 m before
    # the door wall; a slider is 246 cm deep), so a math slip costs the penalty and +3 s, not a re-run of the hallway and
    # its guards. False with no doors.
    RetrySpotFor(Doors:[]trigger_device)<transacts>:?vector3 =
        var SumX : float = 0.0
        var WallY : float = 0.0
        var FloorZ : float = 0.0
        for (K -> Door : Doors):
            Zone := Door.GetTransform()
            set SumX += Zone.Translation.X
            Front := Zone.Translation.Y - TriggerHalf * Zone.Scale.Y
            Bottom := ZoneCentre(Door).Z - TriggerHalfZ * Zone.Scale.Z
            if (K = 0 or Front < WallY):
                set WallY = Front
            if (K = 0 or Bottom < FloorZ):
                set FloorZ = Bottom
        if (Doors.Length > 0):
            option{vector3{X := SumX / (Doors.Length * 1.0), Y := WallY - DoorWallThickness - RetryStandOff, Z := FloorZ + ArrivalLift}}
        else:
            false

    # Where a punished player comes back at Station: its retry spot, or (the arenas) the arrival spot of its entry pad.
    RetryPoint(Station:fnm_station)<transacts>:vector3 =
        if (Spot := Station.RetrySpot?) then Spot else ArrivalSpot(Station.RetryTeleporter)

    # Puts a punished player on Station's retry point, facing the doors (+Y); the entry pad's own teleport if the character
    # can't be moved.
    SendToRetry(Player:player, Station:fnm_station):void =
        Spot := RetryPoint(Station)
        if (Character := Player.GetFortCharacter[], Character.TeleportTo[Spot, MakeRotationFromYawPitchRollDegrees(ArrivalYaw, 0.0, 0.0)]):
            Print("FNM: on the retry spot {Spot}")
        else:
            SendTo(Player, Station.RetryTeleporter)

    # A retry (G9): the same question with a new letter order, so walking the next door along is not a free guess. Tries
    # a few shuffles for one that differs from the order just shown; logs the old and new letters.
    Reshuffle(State:fnm_player_state):void =
        Old := State.Order
        var Next : []int = Shuffle(Old)
        var Tries : int = 1
        loop:
            if (Tries >= 8 or not SameOrder(Next, Old)?) then break
            set Next = Shuffle(Old)
            set Tries += 1
        set State.Order = Next
        Print("FNM: letters reshuffled for the retry: {OrderCopy(State, Old)} -> {OrderCopy(State, Next)}")

    SameOrder(A:[]int, B:[]int)<transacts>:logic =
        var Same : logic = if (A.Length = B.Length) then true else false
        for (K -> X : A, Y := B[K], X <> Y):
            set Same = false
        Same

    # "A=33 B=60 C=37 D=38": the current item's choices behind each letter in Order (for the log).
    OrderCopy(State:fnm_player_state, Order:[]int)<transacts>:string =
        var Line : string = ""
        if (Item := State.Cartridge.Items[State.CurrentItem]):
            for (K -> Choice : Order, Text := Item.Choices[Choice]):
                Separator := if (K > 0) then " " else ""
                set Line += "{Separator}{FnmChoiceLetter(K)}={Text}"
        Line

    # The race clock takes WrongDoorSeconds for a wrong door: added to ClockPenalty, which every read of the clock adds
    # (RunClock); a clock not running is left alone. Returns the HUD tail for the verdict ("  +3 s"). (Until the 2026-10-13
    # audit this moved StartTime back instead: once 3 s x the wrong doors passed the session's GO time, StartTime crossed
    # its "no clock" sentinel, the clock froze and the finish saved 0:00.0 as a best. The log shows where it would be.)
    ChargeWrongDoor(State:fnm_player_state)<transacts>:string =
        Whole := if (W := Round[WrongDoorSeconds]) then W else 3
        if (State.StartTime >= 0.0):
            set State.ClockPenalty += WrongDoorSeconds
            set State.WrongDoors += 1
            Print("FNM: +{Whole} s on the race clock (wrong door {State.WrongDoors}, {State.ClockPenalty} s in all; GO at sim {State.StartTime} s, a moved start would now read {State.StartTime - State.ClockPenalty})")
        "  +{Whole} s"

    # The race clock of the player's run at simulation time Now: time since GO plus the wrong doors' charges. Every read of
    # the race clock goes through here (the clock loop, RecordSplit, FinishPlayer, RaceEntry); StartTime < 0 = no clock.
    RunClock(State:fnm_player_state, Now:float)<transacts>:float =
        Now - State.StartTime + State.ClockPenalty

    # The centre of a trigger's detection box (TriggerLift): where a debug drop stands a player (its origin is under the floor).
    ZoneCentre(Door:trigger_device)<transacts>:vector3 =
        Zone := Door.GetTransform()
        Zone.Translation + vector3{X := 0.0, Y := 0.0, Z := TriggerLift * Zone.Scale.Z}

    # Skip guard: a player standing in a hallway beyond their stage (over a door wall with a Shockwave Grenade, or
    # any other way round the doors) is sent back to their own station's entry with a NO SKIPPING! flash. Not while
    # a penalty moves them about (Busy), and never for a hallway at or behind their stage: walking back is harmless.
    WatchSkip(State:fnm_player_state):void =
        if (State.Mode = fnm_mode.Race, not State.Finished?, not State.Picking?, not State.Busy?, State.CurrentItem >= 0, Character := State.Player.GetFortCharacter[], Character.IsActive[]):
            Hallway := HallwayAt(Character.GetTransform().Translation)
            if (Hallway + 1 > State.Stage, Station := StationFor(State.Stage)?):
                Print("FNM: skip guard: stage {State.Stage} player found in hallway {Hallway + 1}, sent back")
                SendTo(State.Player, Station.RetryTeleporter)
                Sound(State.Player, fnm_cue.NoSkip)
                State.Hud.FlashBig("NO SKIPPING!", NamedColors.Red, 2.0)
                Broadcast(FnmFeedSkip(State.Player), "tried to skip and was sent back")

    # Correct answer through door DoorIndex at Station: next stage (or finish), then the way on opens:
    # that door's barrier lets this player (only) through, or they are teleported to the next entry.
    # The barrier stays open for them; walking back through it later is harmless.
    # ShowNow: put the new question on the slate now (false: the caller shows the recap card first, which flips to it).
    AdvancePlayer(State:fnm_player_state, Station:fnm_station, DoorIndex:int, ShowNow:logic):void =
        set State.Stage += 1
        # Every stage cleared refills health and shield (Aaron 2026-10-08: the station-10 guards wore him down; "every
        # time a player makes it through a stage they should have health and shield refreshed to full").
        RefreshVitals(State.Player, State.Stage)
        if (AtArena(State)?):
            EnterArena(State, ShowNow)
        else if (State.Stage > Stations.Length):
            FinishPlayer(State)
        else:
            DrawItem(State)
            if (ShowNow?) then ShowCurrent(State)
            Music(State)
        if (MaybePassage := Station.Passages[DoorIndex], Passage := MaybePassage?):
            Passage.AddToIgnoreList(State.Player)
            Sound(State.Player, fnm_cue.DoorOpen)
            Print("FNM: passage {FnmChoiceLetter(DoorIndex)} open for the player")
        else:
            SendTo(State.Player, Station.NextTeleporter)
        RightAnswerFx(State, Station, DoorIndex)

    # A right answer seen (G9 spectacle, fnm_fx): the pillar of light from the door's vestibule floor (its trigger box sits
    # in the vestibule, its bottom on the floor), for everyone behind to see, and the gate burst on the barrier it opened.
    # DebugFarPillar adds a pillar the same door's vestibule that many stations ahead (State.Stage has already moved on).
    RightAnswerFx(State:fnm_player_state, Station:fnm_station, DoorIndex:int):void =
        var Burst : logic = false
        if (Door := Station.Doors[DoorIndex]):
            FnmSpawnPillar(VestibuleFloor(Door))
        if (MaybePassage := Station.Passages[DoorIndex], Passage := MaybePassage?):
            FnmSpawnGateBurst(Passage.GetTransform().Translation, MakeRotationFromYawPitchRollDegrees(ArrivalYaw, 0.0, 0.0).GetLocalForward())
            set Burst = true
        Print("FNM: fx right answer door {FnmChoiceLetter(DoorIndex)}: pillar, gate burst {FnmYesNo(Burst)}")
        if (DebugFarPillar > 0, Far := Stations[State.Stage - 2 + DebugFarPillar], FarDoor := Far.Doors[DoorIndex]):
            spawn{ FarPillarLater(State, VestibuleFloor(FarDoor)) }

    # DebugFarPillar's pillar, 2.5 s after the answer: time for a test to turn the player's camera up after the auto-run's
    # teleport (which levels it) and look over the HUD slate, which hides the sky ahead.
    FarPillarLater(State:fnm_player_state, Spot:vector3)<suspends>:void =
        Sleep(2.5)
        FnmSpawnPillar(Spot)
        Away := if (Character := State.Player.GetFortCharacter[]) then FnmMetres(Character.GetTransform().Translation, Spot) else "?"
        Print("FNM: fx far pillar {DebugFarPillar} stations ahead at {Spot}, {Away} m from the player")

    # The floor of a door's vestibule under its trigger's box centre.
    VestibuleFloor(Door:trigger_device)<transacts>:vector3 =
        ZoneCentre(Door) - vector3{X := 0.0, Y := 0.0, Z := TriggerHalfZ * Door.GetTransform().Scale.Z}

    PickPenalty()<transacts>:fnm_penalty =
        Index := if (DebugAutoWrongAnswers > 0) then Mod[DebugPenaltyCursor, Max(Penalties.Length, 1)] or 0
                 else GetRandomInt(0, Penalties.Length - 1)
        set DebugPenaltyCursor += 1
        if (Kind := Penalties[Index]) then Kind else fnm_penalty.Freeze

    DebugAutoWrong(State:fnm_player_state)<suspends>:void =
        for (N := 1..DebugAutoWrongAnswers):
            Sleep(12.0)
            if (State.CurrentItem >= 0, not State.Busy?, not State.Finished?):
                set State.Busy = true
                Print("FNM: debug auto-wrong {N}")
                Wrong := if (AnswerDoor(State) = 0) then 1 else 0
                # Stand them in that door's vestibule, where a real wrong answer happens.
                if (Station := StationOf(State)?, Door := Station.Doors[Wrong], Character := State.Player.GetFortCharacter[]):
                    if (Character.TeleportTo[ZoneCentre(Door), MakeRotationFromYawPitchRollDegrees(ArrivalYaw, 0.0, 0.0)]) {}
                    Sleep(1.0)
                if (State.Mode = fnm_mode.Boss, BM := BossMode?):
                    BM.OnPad(State, Wrong)
                else:
                    HandleDoor(State, State.Stage - 1, Wrong)

    DebugAutoRight(State:fnm_player_state)<suspends>:void =
        Sleep(8.0)
        # Boss battle mode has its own run (BOSS_MODE.md section 8).
        if (State.Mode = fnm_mode.Boss):
            DebugBossModeRun(State)
            return
        var Finishes : int = 0
        var WrongsLeft : int = DebugAutoWrongAnswers
        var WrongStage : int = 0
        var WrongsHere : int = 0
        loop:
            # Two runs: after the first finish, wait out the board and the next countdown, then play run 2.
            if (State.Finished?):
                set Finishes += 1
                if (Finishes >= 2) then break
                # With a podium, press NEW RACE for them once the board has hidden itself (DebugVictoryTest: wait for a
                # real press instead). (After CHANGE SKILL, also until the new skill is picked.)
                if (not DebugVictoryTest?, NewRaceButtons.Length > 0):
                    Sleep(ResultsSeconds + 3.0)
                    if (State.Finished?, not State.Picking?):
                        Print("FNM: debug pressing new race")
                        CloseResults(State)
                        set State.RunGeneration += 1
                        spawn{ StartNewRun(State) }
                loop:
                    Sleep(0.5)
                    if (not State.Finished?, not State.Picking?) then break
                Sleep(CountdownStepSeconds * 3.0 + 2.0)
            # With DebugAutoWrongAnswers as well (round 2): up to two wrong doors at each station of run 1 until that many are
            # spent (the +3 s clock charges over a whole run), each followed by a beat on the retry spot (the wide camera).
            # With a boss arena the last one is kept for a wrong pad there (G9 D2: the crowd's aww, the titan's taunt).
            if (State.Stage <> WrongStage):
                set WrongStage = State.Stage
                set WrongsHere = 0
            KeepForArena := if (Arena?, Finishes = 0) then 1 else 0
            loop:
                if (WrongsLeft <= KeepForArena or WrongsHere >= 2 or Finishes > 0 or AtArena(State)? or State.Finished? or State.CurrentItem < 0) then break
                set WrongsLeft -= 1
                set WrongsHere += 1
                DebugWrongDoor(State)
                Sleep(RetryWideSeconds + 1.0)
            Answer := AnswerDoor(State)
            if (AtArena(State)?):
                # The boss arena: in at its entry, a wrong pad if one is left, then onto the right pad until the boss goes down.
                Done := DebugBossRun(State, if (Finishes = 0) then WrongsLeft else 0)
                set WrongsLeft = 0
                if (not Done?):
                    break
            else if (State.CurrentItem >= 0, Station := Stations[State.Stage - 1], Door := Station.Doors[Answer], Character := State.Player.GetFortCharacter[]):
                Stage := State.Stage
                # (The teleport answers at once, so name the door before it: afterwards the next item is up.)
                Print("FNM: debug auto-right stage {Stage} door {FnmChoiceLetter(Answer)}")
                Spot := ZoneCentre(Door) + vector3{X := 0.0, Y := DebugAutoRightOffsetY, Z := 0.0}
                if (Character.TeleportTo[Spot, MakeRotationFromYawPitchRollDegrees(ArrivalYaw, 0.0, 0.0)]) {}
                Sleep(6.0)
                if (State.Stage = Stage):
                    Print("FNM: debug auto-right stuck at stage {Stage}")
                    break
            else:
                break
        Print("FNM: debug auto-right done: finished={FnmYesNo(State.Finished)} stage={State.Stage}")

    # One wrong door for the auto-run, as a player takes it: stood in a wrong door's vestibule (Busy first, so its trigger
    # event is not a second answer), the door answered, back once the retry has cleared Busy.
    DebugWrongDoor(State:fnm_player_state)<suspends>:void =
        Wrong := if (AnswerDoor(State) = 0) then 1 else 0
        if (Station := StationOf(State)?, Door := Station.Doors[Wrong], Character := State.Player.GetFortCharacter[]):
            set State.Busy = true
            Print("FNM: debug wrong door {FnmChoiceLetter(Wrong)} at stage {State.Stage}")
            if (Character.TeleportTo[ZoneCentre(Door), MakeRotationFromYawPitchRollDegrees(ArrivalYaw, 0.0, 0.0)]) {}
            Sleep(1.0)
            spawn{ HandleDoor(State, State.Stage - 1, Wrong) }
            var Waited : float = 0.0
            loop:
                Sleep(0.25)
                set Waited += 0.25
                if (not State.Busy? or Waited >= 12.0) then break

    # DebugAutoRight in the boss arena: waits for a boss, then drops the player onto the right pad (each hit sends them back
    # to the entry), at most 12 tries. True once the kill has finished their run.
    DebugBossRun(State:fnm_player_state, Wrongs:int)<suspends>:logic =
        # G9 D2: first in at the arena entry, as a player walks in, so ArenaArrival's titan entrance (the jump-slam and the
        # roar) plays out before any pad; then Wrongs wrong pads with the boss up (the crowd's aww, the titan's stomp).
        if (not State.ArenaArrived?, A := Arena?):
            SendTo(State.Player, A.Station.RetryTeleporter)
            Print("FNM: debug auto-right at the arena entry")
            Sleep(DebugEntranceSeconds)
        for (N := 1..Wrongs, Wrongs > 0):
            var Waited : float = 0.0
            loop:
                if (BossAlive? or Waited >= 10.0) then break
                Sleep(0.5)
                set Waited += 0.5
            if (not State.Finished?, AtArena(State)?):
                DebugWrongDoor(State)
                Sleep(2.0)
        var Tries : int = 0
        loop:
            if (State.Finished? or not AtArena(State)?) then break
            if (Tries >= 12):
                Print("FNM: debug auto-right boss not down after {Tries} tries (cap reached)")
                break
            var Waited : float = 0.0
            loop:
                if (BossAlive? or Waited >= 10.0) then break
                Sleep(0.5)
                set Waited += 0.5
            Answer := AnswerDoor(State)
            if (A := Arena?, State.CurrentItem >= 0, Pad := A.Station.Doors[Answer], Character := State.Player.GetFortCharacter[]):
                set Tries += 1
                Before := State.Hits
                Print("FNM: debug auto-right boss try {Tries} pad {FnmChoiceLetter(Answer)} (boss up {FnmYesNo(BossAlive)})")
                if (Character.TeleportTo[ZoneCentre(Pad) + vector3{X := DebugPadOffset, Y := DebugPadOffset, Z := 0.0}, MakeRotationFromYawPitchRollDegrees(ArrivalYaw, 0.0, 0.0)]) {}
                Sleep(6.0)
                if (State.Hits > Before):
                    Print("FNM: debug auto-right boss hit {State.Hits}")
                else:
                    Print("FNM: debug auto-right boss pad did not answer")
            else:
                break
        State.Finished

    # DebugAutoRightAnswers in boss mode: 8 s after the start, drops the player onto the right pad every 5 s (waiting up to
    # 12 s for a boss), until the victory, three pads in a row that moved no hit, or 40 pads.
    DebugBossModeRun(State:fnm_player_state)<suspends>:void =
        Sleep(8.0)
        var Pads : int = 0
        var Misses : int = 0
        if (BM := BossMode?):
            loop:
                if (State.Finished? or State.Mode <> fnm_mode.Boss) then break
                if (Pads >= 40):
                    Print("FNM: debug boss mode cap reached ({Pads} pads) at level {BM.Level}")
                    break
                if (Misses >= 3):
                    Print("FNM: debug boss mode stuck at level {BM.Level}")
                    break
                var Waited : float = 0.0
                loop:
                    if (BM.BossAlive? or Waited >= 12.0) then break
                    Sleep(0.5)
                    set Waited += 0.5
                if (DebugBossHold > 0.0, BM.BossAlive?):
                    Print("FNM: debug boss hold {FnmBmWholeSeconds(DebugBossHold)} s at level {BM.Level} ({BM.Alive()} monsters alive)")
                    Sleep(DebugBossHold)
                Answer := AnswerDoor(State)
                if (State.CurrentItem >= 0, Pad := BM.Arena.Station.Doors[Answer], Character := State.Player.GetFortCharacter[]):
                    set Pads += 1
                    Before := State.Hits
                    Print("FNM: debug boss mode pad {Pads} {FnmChoiceLetter(Answer)} (level {BM.Level}, boss up {FnmYesNo(BM.BossAlive)})")
                    # On the pad, 1 m above the arena entry's floor: the pad trigger's origin sits under the floor since
                    # its detection box was fitted to the whole pad (B6, build_bossmode.trigger_fit).
                    PadAt := Pad.GetTransform().Translation
                    Spot := vector3{X := PadAt.X, Y := PadAt.Y, Z := BM.Arena.Station.RetryTeleporter.GetTransform().Translation.Z + 100.0}
                    if (Character.TeleportTo[Spot, MakeRotationFromYawPitchRollDegrees(ArrivalYaw, 0.0, 0.0)]) {}
                    Sleep(5.0)
                    if (State.Hits > Before):
                        set Misses = 0
                    else:
                        set Misses += 1
                else:
                    break
        Print("FNM: debug boss mode done: victory={FnmYesNo(State.Finished)} level={State.Level}")

    DebugDoor(State:fnm_player_state)<suspends>:void =
        Sleep(8.0)
        if (Station := Stations[0], Door := Station.Doors[DebugDoorTest], Character := State.Player.GetFortCharacter[]):
            # The trigger sits 2.3 m past the door wall; stand 2.5 m in front of the wall.
            Spot := ZoneCentre(Door) - vector3{X := 0.0, Y := 480.0, Z := 0.0}
            if (Character.TeleportTo[Spot, MakeRotationFromYawPitchRollDegrees(ArrivalYaw, 0.0, 0.0)]):
                Print("FNM: debug door: in front of {FnmChoiceLetter(DebugDoorTest)} at {Spot}")
            for (N := 1..12):
                Sleep(1.0)
                Print("FNM: debug pos y={Character.GetTransform().Translation.Y} stage={State.Stage}")

    DebugPassage(State:fnm_player_state)<suspends>:void =
        Sleep(8.0)
        if (State.CurrentItem >= 0, Station := Stations[0], Door := Station.Doors[AnswerDoor(State)], Character := State.Player.GetFortCharacter[]):
            Spot := ZoneCentre(Door)
            if (Character.TeleportTo[Spot, MakeRotationFromYawPitchRollDegrees(ArrivalYaw, 0.0, 0.0)]):
                Print("FNM: debug passage: dropped into vestibule {FnmChoiceLetter(AnswerDoor(State))} at {Spot}")
            for (N := 1..12):
                Sleep(1.0)
                Print("FNM: debug pos y={Character.GetTransform().Translation.Y} stage={State.Stage}")
            # Then behind a WRONG door's trigger at the current station, facing its (closed) barrier.
            if (State.CurrentItem >= 0, Here := Stations[State.Stage - 1], Wrong := Here.Doors[if (AnswerDoor(State) = 0) then 1 else 0]):
                Behind := ZoneCentre(Wrong) + vector3{X := 0.0, Y := 350.0, Z := 0.0}
                if (Character.TeleportTo[Behind, MakeRotationFromYawPitchRollDegrees(ArrivalYaw, 0.0, 0.0)]):
                    Print("FNM: debug passage: behind a wrong door at {Behind}")
                for (N := 1..8):
                    Sleep(1.0)
                    Print("FNM: debug pos y={Character.GetTransform().Translation.Y} stage={State.Stage}")

    DebugSkip(State:fnm_player_state)<suspends>:void =
        Sleep(8.0)
        if (State.CurrentItem >= 0, Ahead := Stations[2], Character := State.Player.GetFortCharacter[]):
            Spot := ArrivalSpot(Ahead.RetryTeleporter)
            if (Character.TeleportTo[Spot, MakeRotationFromYawPitchRollDegrees(ArrivalYaw, 0.0, 0.0)]):
                Print("FNM: debug skip: dropped at station 3's entry at stage {State.Stage}")
            for (N := 1..6):
                Sleep(1.0)
                Print("FNM: debug pos y={Character.GetTransform().Translation.Y} stage={State.Stage}")

    # Applies Kind to Player, who answered wrong through door DoorIndex at Station: the gag where they stand (about 2.5 s,
    # see the penalty constants), then Station's retry point (RetryPoint: in front of the doors, facing them). Returns
    # once the player can play again, and logs how long that took from the verdict (HandleDoor flashes it in the same
    # tick, just before this).
    # In boss mode the player is moved to the arena entry FIRST, then held (round-2 audit: Wave() has just released
    # monsters by the pads and stasis does not block damage; until G9 Mud and Dizzy moved first there too). On a race
    # station the wide camera stays on from the hold onto the retry spot (WideLook), so all four doors are on screen.
    Punish(Player:player, Station:fnm_station, DoorIndex:int, Kind:fnm_penalty)<suspends>:void =
        Began := GetSimulationElapsedTime()
        Print("FNM: penalty {FnmPenaltyLabel(Kind)}")
        # Volt is shocked when the penalty lands: with its voice line, a beat after the wag HandleDoor / HandlePad showed.
        spawn{ VoltLater(Player, fnm_volt.Shocked, PenaltyVoiceDelaySeconds) }
        InBossMode := if (Mover := PlayerStates[Player], Mover.Mode = fnm_mode.Boss) then true else false
        Wide := if (Station.RetrySpot?, not InBossMode?) then true else false
        if (InBossMode?):
            SendToRetry(Player, Station)
            Print("FNM: boss mode: at the arena entry before the hold")
        if (Kind = fnm_penalty.Freeze):
            if (Character := Player.GetFortCharacter[]):
                WideCamera(Player, true)
                Feet := Character.GetTransform().Translation - vector3{X := 0.0, Y := 0.0, Z := FeetDrop}
                Character.PutInStasis(stasis_args{AllowTurning := false, AllowFalling := false, AllowEmotes := false})
                FxOn(Player, FrostFx)
                spawn{ PenaltyLines(Player, fnm_cue.PenaltyFreeze) }
                Ice := IceRig.NextIndex()
                Placed := IceRig.Place(Ice, Feet, 0.0)
                Print("FNM: ice {Ice} placed={FnmYesNo(Placed)} at {Feet}")
                Sleep(FreezeSeconds)
                IceRig.Park(Ice)
                FxOff(Player, FrostFx)
                SendToRetry(Player, Station)
                Character.ReleaseFromStasis()
                if (not Wide?) then WideCamera(Player, false)
            else:
                SendToRetry(Player, Station)
        else if (Kind = fnm_penalty.Yeet):
            if (Character := Player.GetFortCharacter[]):
                PullOut(Character, Station)
                Feet := Character.GetTransform().Translation - vector3{X := 0.0, Y := 0.0, Z := FeetDrop}
                Pad := YeetRig.NextIndex()
                Placed := YeetRig.PlaceTilted(Pad, Feet, YeetYaw, YeetPitch)
                if (Part := YeetRig.PartAt[Pad], AirVent := air_vent_device[Part]):
                    AirVent.Enable()
                    AirVent.Activate()
                # The vent only throws a player who ENTERS its gust; hop them into it.
                Sleep(0.1)
                Hop := Character.GetTransform()
                if (Character.TeleportTo[Hop.Translation + vector3{X := 0.0, Y := 0.0, Z := 40.0}, Hop.Rotation]) {}
                spawn{ PenaltyLines(Player, fnm_cue.PenaltyYeet) }
                Print("FNM: vent {Pad} placed={FnmYesNo(Placed)} at {Feet}")
                Sleep(YeetSeconds)
                YeetRig.Park(Pad)
                var Airborne : float = YeetSeconds
                loop:
                    if (Character.IsOnGround[]) then break
                    if (Airborne >= YeetAirSeconds) then break
                    Sleep(0.25)
                    set Airborne += 0.25
                Landed := Character.GetTransform().Translation
                Print("FNM: yeet thrown {Feet.Y - Landed.Y} cm back in {Airborne} s (on the ground {FnmYesNo(if (Character.IsOnGround[]) then true else false)})")
            SendToRetry(Player, Station)
        else if (Kind = fnm_penalty.Mud):
            spawn{ PenaltyLines(Player, fnm_cue.PenaltyMud) }
            Afflict(Player)
            Epoch := EpochOf(Player)
            # Boss mode: no stuck beat, only the slow, as before G9 (a held player at the entry was shot by the wave's
            # guards in the round-2 test; stasis does not block damage).
            StuckFor := if (InBossMode?) then 0.0 else MudStuckSeconds
            spawn{ ScreenFx(Player, MudFx, StuckFor + MudSeconds, Epoch) }
            if (StuckFor > 0.0):
                MaybeCharacter := option{Player.GetFortCharacter[]}
                if (Character := MaybeCharacter?):
                    Character.PutInStasis(stasis_args{AllowTurning := true, AllowFalling := false, AllowEmotes := false})
                Sleep(StuckFor)
                SendToRetry(Player, Station)
                if (Character := MaybeCharacter?):
                    Character.ReleaseFromStasis()
            else:
                SendToRetry(Player, Station)
            spawn{ Muddy(Player, Epoch) }
        else if (Kind = fnm_penalty.Dizzy):
            spawn{ PenaltyLines(Player, fnm_cue.PenaltyDizzy) }
            Afflict(Player)
            Epoch := EpochOf(Player)
            Spin(Player)
            SendToRetry(Player, Station)
            spawn{ DizzyPulses(Player, Epoch) }
        else if (Kind = fnm_penalty.Blackout):
            if (Character := Player.GetFortCharacter[]):
                Character.PutInStasis(stasis_args{AllowTurning := false, AllowFalling := false, AllowEmotes := false})
                if (State := PlayerStates[Player]) then State.Hud.SetBlack(true)
                spawn{ PenaltyLines(Player, fnm_cue.PenaltyBlackout) }
                Sleep(BlackoutSeconds)
                SendToRetry(Player, Station)
                Character.ReleaseFromStasis()
                Sleep(0.5)
                if (State := PlayerStates[Player]) then State.Hud.SetBlack(false)
            else:
                SendToRetry(Player, Station)
        else:
            # Spike: the ring bursts up round them and pins them under the wide camera; no elimination (G9).
            if (Character := Player.GetFortCharacter[]):
                WideCamera(Player, true)
                Feet := Character.GetTransform().Translation - vector3{X := 0.0, Y := 0.0, Z := FeetDrop}
                Spears := SpikeRig.NextIndices(SpearCount)
                var Placed : int = 0
                for (K -> Index : Spears):
                    Angle := 2.0 * PiFloat * (K * 1.0) / (Max(Spears.Length, 1) * 1.0)
                    Spot := Feet + vector3{X := SpearRing * Cos(Angle), Y := SpearRing * Sin(Angle), Z := -SpearDepth}
                    if (SpikeRig.Place(Index, Spot, Angle * 180.0 / PiFloat)?):
                        set Placed += 1
                Print("FNM: spears placed {Placed}/{Spears.Length} at {Feet}")
                for (Index : Spears):
                    spawn{ SpikeRig.Rise(Index, SpearRise, SpearSeconds) }
                spawn{ PenaltyLines(Player, fnm_cue.PenaltySpike) }
                Sleep(SpearSeconds)
                Character.PutInStasis(stasis_args{AllowTurning := false, AllowFalling := false, AllowEmotes := false})
                Sleep(SpikeHoldSeconds)
                SendToRetry(Player, Station)
                for (Index : Spears):
                    SpikeRig.Park(Index)
                Character.ReleaseFromStasis()
                if (not Wide?) then WideCamera(Player, false)
                Print("FNM: spike: still standing {FnmYesNo(if (Character.IsActive[]) then true else false)}, health {Character.GetHealth()}")
            else:
                SendToRetry(Player, Station)
        Took := GetSimulationElapsedTime() - Began
        Print("FNM: wrong door {FnmPenaltyLabel(Kind)}: ready on the retry spot {RetryPoint(Station)} {Took} s after the verdict")
        if (Wide?, Viewer := PlayerStates[Player]):
            # On the retry spot with all four doors in view: Volt thinks about it (the card and the quiet warble).
            Viewer.Hud.ShowVolt(fnm_volt.Think)
            Sound(Player, fnm_cue.VoltHmm)
            spawn{ WideLook(Viewer, RetryWideSeconds, WideMoveCm, "retry spot") }

    # Blends a screen effect in (FxOn) or out (FxOff) for Player only.
    FxOn(Player:player, Fx:?post_process_device):void =
        if (Device := Fx?):
            Device.BlendIn(Player)

    FxOff(Player:player, Fx:?post_process_device):void =
        if (Device := Fx?):
            Device.BlendOut(Player)

    # The mud and dizzy effects stop early, without switching anything off themselves, once a right answer bumps the
    # player's PenaltyEpoch past Epoch (Cleanse switches them off).
    Muddy(Player:player, Epoch:int)<suspends>:void =
        MuddyFor(Player, Epoch, MudSeconds)

    # The mud modulator on Player for Seconds (a wrong door's MudSeconds, a strike's StrikeMudSeconds).
    MuddyFor(Player:player, Epoch:int, Seconds:float)<suspends>:void =
        if (Mud := MudDevice?):
            var Elapsed : float = 0.0
            loop:
                if (EpochOf(Player) <> Epoch) then return
                if (Elapsed >= Seconds) then break
                Mud.Activate(Player)
                Wait := Min(MudReapplySeconds, Seconds - Elapsed)
                Sleep(Wait)
                set Elapsed += Wait
            Mud.Deactivate(Player)

    ScreenFx(Player:player, Fx:?post_process_device, Seconds:float, Epoch:int)<suspends>:void =
        FxOn(Player, Fx)
        var Elapsed : float = 0.0
        loop:
            if (EpochOf(Player) <> Epoch) then return
            if (Elapsed >= Seconds) then break
            Sleep(0.25)
            set Elapsed += 0.25
        FxOff(Player, Fx)

    # Dizzy spin: held in stasis, the character is teleported in place with its yaw advanced every
    # DizzySpinStepSeconds (a character TeleportTo turns the view too, as SendTo's facing does), then released.
    Spin(Player:player)<suspends>:void =
        if (Character := Player.GetFortCharacter[]):
            Character.PutInStasis(stasis_args{AllowTurning := false, AllowFalling := false, AllowEmotes := false})
            Step := Max(DizzySpinStepSeconds, 0.016)
            # Whole turns (nearest to DizzySpinDegreesPerSecond * DizzySpinSeconds, at least one), so the spin ends
            # facing the doors again: 540 degrees left the player staring at the back wall (2026-10-04 frames).
            Turns := Max(1, if (T := Round[DizzySpinDegreesPerSecond * DizzySpinSeconds / 360.0]) then T else 1)
            Steps := Max(1, if (N := Ceil[DizzySpinSeconds / Step]) then N else 1)
            StepDegrees := 360.0 * Turns / (Steps * 1.0)
            var Yaw : float = ArrivalYaw
            var Turned : int = 0
            for (K := 1..Steps):
                Sleep(Step)
                set Yaw += StepDegrees
                Here := Character.GetTransform().Translation
                if (Character.TeleportTo[Here, MakeRotationFromYawPitchRollDegrees(Yaw, 0.0, 0.0)]):
                    set Turned += 1
            Character.ReleaseFromStasis()
            Print("FNM: dizzy spin {Turned} steps, ended at yaw {Yaw}")

    # Dizzy blur: in for DizzyPulseSeconds, out for DizzyPulseSeconds, repeated for DizzySeconds; ends out.
    DizzyPulses(Player:player, Epoch:int)<suspends>:void =
        BlurFor(Player, Epoch, DizzySeconds)

    # The radial blur pulsing on Player for Seconds (a wrong door's DizzySeconds, a strike's StrikeBlurSeconds; no spin).
    BlurFor(Player:player, Epoch:int, Seconds:float)<suspends>:void =
        if (Device := DizzyFx?):
            Pulse := Max(DizzyPulseSeconds, 0.1)
            var Elapsed : float = 0.0
            var Pulses : int = 0
            loop:
                if (EpochOf(Player) <> Epoch) then return
                if (Elapsed >= Seconds) then break
                Device.BlendIn(Player)
                Sleep(Pulse)
                Device.BlendOut(Player)
                Sleep(Pulse)
                set Elapsed += 2.0 * Pulse
                set Pulses += 1
            Device.BlendOut(Player)
            Print("FNM: dizzy blur {Pulses} pulses")

    # Pushes (On) or pops the wide orbit camera for Player: further out than the default camera, walls turn
    # see-through instead of pulling it in.
    WideCamera(Player:player, On:logic):void =
        if (State := PlayerStates[Player]):
            set State.CameraGeneration += 1
        if (Camera := PenaltyCam?):
            if (On?) then Camera.AddTo(Player) else Camera.RemoveFrom(Player)

    # The wide camera for a beat (round 2, items 6 and 7): from the retry spot, 6 m from the door wall, the player's own
    # camera frames only doors B and C (it sees about 2.6 door pitches there), and at the podium the lecterns fill the
    # screen and the all-time board is cut off; the orbit camera (fnm_penalty_cam: 900 cm out, walls see-through) shows the
    # whole door wall with its lintel letters, or both lecterns and the board. It goes once the player has moved MoveCm
    # (flat) or after Seconds, unless a newer WideLook / WideCamera call has taken over (CameraGeneration).
    WideLook(State:fnm_player_state, Seconds:float, MoveCm:float, Why:string)<suspends>:void =
        set State.CameraGeneration += 1
        Generation := State.CameraGeneration
        if (Camera := PenaltyCam?, Character := State.Player.GetFortCharacter[]):
            Camera.AddTo(State.Player)
            From := Character.GetTransform().Translation
            Print("FNM: wide camera on ({Why})")
            var Waited : float = 0.0
            var Moved : float = 0.0
            loop:
                Sleep(0.1)
                set Waited += 0.1
                if (State.CameraGeneration <> Generation) then return
                if (Character.IsActive[]):
                    At := Character.GetTransform().Translation
                    set Moved = Distance(vector3{X := At.X, Y := At.Y, Z := 0.0}, vector3{X := From.X, Y := From.Y, Z := 0.0})
                if (Moved >= MoveCm or Waited >= Seconds) then break
            Camera.RemoveFrom(State.Player)
            Print("FNM: wide camera off ({Why}) after {Waited} s, moved {Moved} cm")

    # Starting loadout: the pistol and spare ammo (fires the fnm_loadout trigger, which the item granter
    # listens to), full health and full shield.
    GiveLoadout(Player:player):void =
        if (Trigger := LoadoutTrigger?):
            Trigger.Trigger(Player)
        if (Character := Player.GetFortCharacter[]):
            Character.SetHealth(Character.GetMaxHealth())
            Character.SetShield(Character.GetMaxShield())
            Print("FNM: loadout: health {Character.GetHealth()}, shield {Character.GetShield()}")

    # Full health and full shield for Player, logged with the stage it was earned at.
    RefreshVitals(Player:player, Stage:int):void =
        if (Character := Player.GetFortCharacter[]):
            Character.SetHealth(Character.GetMaxHealth())
            Character.SetShield(Character.GetMaxShield())
            Print("FNM: vitals refreshed at stage {Stage}: health {Character.GetHealth()}, shield {Character.GetShield()}")

    # Moves a player about to be yeeted out of the narrow vestibule onto Station's retry point (open hallway in front of
    # the door wall, facing the doors), so the throw back does not hit the wall, and lets them land.
    PullOut(Character:fort_character, Station:fnm_station)<suspends>:void =
        Spot := RetryPoint(Station)
        if (Character.TeleportTo[Spot, MakeRotationFromYawPitchRollDegrees(ArrivalYaw, 0.0, 0.0)]):
            Print("FNM: pulled out to {Spot}")
        Sleep(0.4)

    # Where SendTo puts a player: open floor just past Pad, a little above the ground.
    ArrivalSpot(Pad:teleporter_device)<transacts>:vector3 =
        Pad.GetTransform().Translation + vector3{X := 0.0, Y := ArrivalForward, Z := ArrivalLift}

    # Move Player into open floor just past Pad, facing the doors; falls back to the pad's own teleport
    # if the character can't be moved directly.
    SendTo(Player:player, Pad:teleporter_device):void =
        Spot := ArrivalSpot(Pad)
        Facing := MakeRotationFromYawPitchRollDegrees(ArrivalYaw, 0.0, 0.0)
        if (Character := Player.GetFortCharacter[], Character.TeleportTo[Spot, Facing]):
            Print("FNM: moved player to {Spot}")
            return
        Print("FNM: direct move failed; using the pad's own teleport")
        Pad.Teleport(Player)

    FinishPlayer(State:fnm_player_state):void =
        FinishRun(State, 0.0)

    # The finish, with its fanfare FanfareDelay seconds later (FinishSounds): 0 at the finish pad, PodiumSeconds after the
    # arena's kill (BossDown), where the fanfare and the crowd's cheer greet the player at the podium (PodiumLater).
    FinishRun(State:fnm_player_state, FanfareDelay:float):void =
        set State.Finished = true
        set State.Runs += 1
        Total := Stations.Length
        Now := GetSimulationElapsedTime()
        Time := if (State.StartTime >= 0.0) then RunClock(State, Now) else 0.0
        RealSeconds := if (State.StartTime >= 0.0) then Now - State.StartTime else 0.0
        Print("FNM: run clock {FnmClock(Time)} = real {RealSeconds} s + {State.ClockPenalty} s for {State.WrongDoors} wrong doors")
        set State.StartTime = -1.0
        set State.ClockPenalty = 0.0
        set State.WrongDoors = 0
        set State.LastTime = Time
        StopBoost(State)
        # This run's splits travel with its time (a pace target only when they cover every station).
        Splits : []float = if (State.Splits.Length = Total) then State.Splits else array{}
        # Personal best and the board are per skill (the cartridge's index in the slot).
        Skill := State.CartridgeIndex
        HadBest := if (State.BestTime >= 0.0) then true else false
        NewBest := if (not State.Partial?, State.BestTime < 0.0 or Time < State.BestTime) then true else false
        if (NewBest?):
            set State.BestTime = Time
            if (set State.BestTimes[Skill] = Time) {}
            FnmSaveBest(State.Player, State.Cartridge.Id, Time, Splits)
        var IslandRecord : logic = true
        if (Top := BoardFor(Skill)[0], Time >= Top.Time):
            set IslandRecord = false
        # G10 (gamification 6, record inflation): the fastest time of the session is still the board's row 0, but it is
        # celebrated (the record sound, "NEW!", the public feed line) only against someone: another player already on
        # today's board for the skill, or other players present whose saved bests it beats. A lone first finisher was told
        # "NEW!" and heard "NEW ISLAND RECORD!" at every session start.
        Rival := HasRival(Skill, State.Player, Time)
        Celebrate := if (IslandRecord?, Rival?, not State.Partial?) then true else false
        if (State.Partial?):
            set IslandRecord = false
            Print("FNM: partial run (debug start), not recorded")
        else:
            RecordResult(Skill, State.Player, Time, Splits)
        Board := BoardFor(Skill)
        # Medal v2 (G10, gamification 6): accuracy in half answers, a redeemed station counting half, today's gates
        # (FnmMedalHalves); time gates only with MedalTimeGates (GateMedal).
        Halves := 2 * State.FirstTryCorrect + State.Redeemed
        Earned := FnmMedalHalves(Halves, Total)
        Medal := GateMedal(Earned, Time)
        Flawless := if (State.FirstTryCorrect >= Total) then true else false
        SetMusic(State.Player, 0)
        spawn{ FinishSounds(State, FanfareDelay, if (NewBest?, HadBest?) then true else false, Celebrate, Medal, if (State.FirstTryCorrect >= Total) then true else false) }
        MedalColor := if (Medal = "GOLD") then NamedColors.Gold else if (Medal = "SILVER") then NamedColors.Silver else NamedColors.Peru
        # The board is the only thing on screen besides the clock, which keeps the final time.
        State.Hud.SetClock(FnmClock(Time))
        State.Hud.SetTarget("")
        State.Hud.ClearDelta()
        State.Hud.SetStreak("")
        State.Hud.SetShield(false)
        State.Hud.ClearQuestion()
        State.Hud.ClearVerdictNow()
        UpdateCompact(State)
        BestTail := if (NewBest?, HadBest?) then "   NEW BEST!" else ""
        # The record is the session's (Boards lives in memory): "Today's record", so the first finisher of every session
        # is not told it is an island record (ux_critique B7).
        RecordTail := if (Celebrate?) then "   NEW!" else ""
        RecordLine := if (Top := Board[0]) then FnmTodayRecord(FnmClock(Top.Time), Top.Who, RecordTail) else FnmText("Today's record   -")
        Rows := for (K -> Row : Board) { FnmRow(K + 1, Row.Who, FnmClock(Row.Time)) }
        var OwnRow : int = -1
        for (K -> Row : Board, Row.Who = State.Player):
            set OwnRow = K
        State.Hud.ShowResults("FINISH!", Medal, MedalColor, "Your time   {FnmClock(Time)}", "Your best   {FnmClock(State.BestTime)}{BestTail}",
            RecordLine, "{FnmMedalRule(State.FirstTryCorrect, Total)}  -  streak {State.BestStreak}",
            "TODAY'S TOP TIMES  -  {State.Cartridge.Title}", Rows, OwnRow)
        # The brag grid under the medal line (fnm_hud, H): a tile per station, the boss tile, FLAWLESS, the next goal and
        # the island code.
        NextGoal := NextGoalLine(Medal, Halves, Total, Time)
        BossMark := if (State.BossDowned?) then FnmMarkFirstTry else FnmMarkMissed
        State.Hud.ShowBragGrid(State.Marks, BossMark, Flawless, NextGoal, IslandCode)
        Print("FNM: brag grid {MarksCopy(State.Marks)} boss {BossMark}, flawless {FnmYesNo(Flawless)}, next goal \"{NextGoal}\", code \"{IslandCode}\"")
        Print("FNM: medal {Medal} (accuracy {Earned}: {FnmHalvesCopy(Halves)}/{Total} = {State.FirstTryCorrect} first try + {State.Redeemed} redeemed x 0.5; time gates {FnmYesNo(MedalTimeGates)})")
        Print("FNM: finished run {State.Runs} in {FnmClock(Time)}, {Medal}, first try {State.FirstTryCorrect}/{Total}, best streak {State.BestStreak}, new best {FnmYesNo(NewBest)}, new record {FnmYesNo(IslandRecord)}, board {Board.Length} rows (size {BoardSize}) for {State.Cartridge.Id}")
        Print("FNM: record celebrated {FnmYesNo(Celebrate)} (fastest today {FnmYesNo(IslandRecord)}, a rival {FnmYesNo(Rival)})")
        Analytics(FinishAnalytics, State.Player, "finish")
        # The public feed: the finish, then (on top) a record set against someone.
        # (The public finish line names no medal: fnm_hud FnmFeedFinish, G9.)
        Broadcast(FnmFeedFinish(State.Player, FnmClock(Time), Medal), "finished in {FnmClock(Time)}")
        if (Celebrate?):
            Broadcast(FnmFeedRecord(State.Player, FnmClock(Time)), "set today's record  {FnmClock(Time)}")
        if (UseEndGameDevice?):
            State.Hud.SetCountdown("")
            spawn{ EndGameLater(State.Player) }
        else:
            set HallHoldUntil = GetSimulationElapsedTime() + HallCycleSeconds * 2.0
            ShowHall(Skill)
            if (NewRaceButtons.Length = 0):
                # No podium: the board's own buttons (they hold the player still) and the automatic restart.
                State.Hud.ShowFinishButtons(if (Cartridges.Length > 1) then true else false, false)
                spawn{ NextRun(State) }
            else:
                # A podium: the board captures no input (Aaron 2026-10-06: the old board popped up and locked him out of
                # the victory area) and hides itself after ResultsSeconds. After the arena's kill the player is stood at
                # the podium a moment later (PodiumLater).
                State.Hud.SetCountdown("RACE AGAIN  or  NEW SKILL:  press E at the podium")
                spawn{ HideResultsLater(State) }

    # True when a finish in Time on skill Skill has someone to beat (FinishRun, before its own row goes on the board): another
    # player already on today's board for the skill, or other players present with a saved best for it, every one of
    # which Time beats.
    HasRival(Skill:int, Who:player, Time:float):logic =
        var OnBoard : logic = false
        for (Row : BoardFor(Skill), Row.Who <> Who):
            set OnBoard = true
        var Saved : int = 0
        var Beaten : logic = true
        if (Cartridge := Cartridges[Skill]):
            for (Each : GetPlayspace().GetPlayers(), Each <> Who, Best := FnmSavedBest[Each, Cartridge.Id]):
                set Saved += 1
                if (Time >= Best) then set Beaten = false
        if (OnBoard?) then true
        else if (Saved > 0, Beaten?) then true
        else false

    # Medal v2's time gates (gamification 6), only with MedalTimeGates: a GOLD slower than GoldParSeconds, or a SILVER
    # slower than SilverParSeconds, drops one tier (once; a par of 0 = no gate). Off by default: no par data exists yet.
    GateMedal(Medal:string, Time:float)<transacts>:string =
        Par := if (Medal = "GOLD") then GoldParSeconds else if (Medal = "SILVER") then SilverParSeconds else 0.0
        if (MedalTimeGates?, Par > 0.0, Time > Par) then FnmMedalDown(Medal) else Medal

    # The brag grid's next-goal line: what the medal above needs and where the run stands ("GOLD needs 10/10  -  you:
    # 8.5/10"; with time gates also the par: "GOLD needs 10/10 in 5:00.0  -  you: 10/10, 6:10.2"); at GOLD, "FLAWLESS
    # needs 10/10 first try" unless it was; "" when nothing is above.
    NextGoalLine(Medal:string, Halves:int, Total:int, Time:float)<transacts>:string =
        Target := if (Medal = "BRONZE") then "SILVER" else if (Medal = "SILVER") then "GOLD" else ""
        if (Target = ""):
            if (Halves >= 2 * Total) then "" else "FLAWLESS needs {Total}/{Total} first try  -  you: {FnmHalvesCopy(Halves)}/{Total}"
        else:
            Par := if (Target = "GOLD") then GoldParSeconds else SilverParSeconds
            Timed := if (MedalTimeGates?, Par > 0.0) then true else false
            Needs := "{Target} needs {FnmHalvesCopy(FnmMedalNeeds(Target, Total))}/{Total}"
            if (Timed?) then "{Needs} in {FnmClock(Par)}  -  you: {FnmHalvesCopy(Halves)}/{Total}, {FnmClock(Time)}"
            else "{Needs}  -  you: {FnmHalvesCopy(Halves)}/{Total}"

    # "0 0 2 1 0 3 ..." (the marks, for the log).
    MarksCopy(Marks:[]int)<transacts>:string =
        var Line : string = ""
        for (K -> Mark : Marks):
            set Line += if (K > 0) then " {Mark}" else "{Mark}"
        Line

    # Hides the finish board ResultsSeconds after a finish, unless a new run or a skill change already did.
    HideResultsLater(State:fnm_player_state)<suspends>:void =
        Generation := State.RunGeneration
        Sleep(ResultsSeconds)
        if (PlayerStates[State.Player], State.Finished?, State.RunGeneration = Generation):
            CloseResults(State)

    # ---------------------------------------------------------------- victory area

    # Finds the podium buttons and the all-time screen (tools/build_finish.py) and starts the screen.
    SetUpVictoryArea():void =
        # One name per action everywhere (G9, ux_critique B8: four names for one action): RACE AGAIN and NEW SKILL.
        for (Object : FindCreativeObjectsWithTag(fnm_new_race), Button := button_device[Object]):
            Button.SetInteractionText(FnmText("RACE AGAIN"))
            Button.InteractedWithEvent.Subscribe(OnNewRaceButton)
            set NewRaceButtons += array{Button}
        for (Object : FindCreativeObjectsWithTag(fnm_change_skill), Button := button_device[Object]):
            Button.SetInteractionText(FnmText("NEW SKILL"))
            Button.InteractedWithEvent.Subscribe(OnChangeSkillButton)
            set ChangeSkillButtons += array{Button}
        for (Object : FindCreativeObjectsWithTag(fnm_hall_head), Board := billboard_device[Object]):
            set HallHeads += array{Board}
        var Rows : []billboard_device = array{}
        for (Object : FindCreativeObjectsWithTag(fnm_hall_row), Board := billboard_device[Object]):
            set Rows += array{Board}
        # Top row first: insertion by height, highest first.
        for (Row : Rows):
            var Next : []billboard_device = array{}
            var Placed : logic = false
            for (Other : HallRows):
                if (not Placed?, Row.GetTransform().Translation.Z > Other.GetTransform().Translation.Z):
                    set Next += array{Row}
                    set Placed = true
                set Next += array{Other}
            if (not Placed?):
                set Next += array{Row}
            set HallRows = Next
        Print("FNM: victory area: {NewRaceButtons.Length} new-race, {ChangeSkillButtons.Length} change-skill buttons, screen {HallHeads.Length} heading + {HallRows.Length} rows")
        if (HallHeads.Length + HallRows.Length > 0):
            spawn{ HallLoop() }

    # NEW RACE on the podium: a finished player starts a fresh run of the same skill at once.
    OnNewRaceButton(Agent:agent):void =
        if (Player := player[Agent], State := PlayerStates[Player]):
            if (State.Finished?, not State.Picking?):
                Print("FNM: new race pressed")
                # Cancels an automatic restart that may still be counting down.
                set State.RunGeneration += 1
                spawn{ StartNewRun(State) }
            else:
                spawn{ FlashNotice(State, "Finish the race first!") }

    # CHANGE SKILL on the podium: same as the finish board's button.
    OnChangeSkillButton(Agent:agent):void =
        if (Player := player[Agent], State := PlayerStates[Player], State.Finished?, not State.Picking?):
            Print("FNM: change skill pressed at the podium")
            ChangeSkill(State)

    # The finish board goes (its timer, or CLOSE without a podium) and so do its buttons, if any.
    CloseResults(State:fnm_player_state):void =
        State.Hud.HideResults()
        State.Hud.HideFinishButtons()
        State.Hud.SetTarget(if (NewRaceButtons.Length > 0) then "RACE AGAIN: press E at the podium" else "")
        Print("FNM: results closed")
        if (DebugVictoryTest?):
            spawn{ DebugToPodium(State) }

    # The titan has fallen for a player who just finished (BossDown): PodiumSeconds later, with the fall under way, they
    # are stood in the victory area before the podium, RACE AGAIN within reach, facing it (G9, ux_critique #10: the
    # podium was a 55-60 m walk away with nothing on screen to lead there, and no auto-restart). Not if a new run or a
    # skill change came first.
    PodiumLater(State:fnm_player_state)<suspends>:void =
        Generation := State.RunGeneration
        Sleep(PodiumSeconds)
        if (PlayerStates[State.Player], State.Finished?, not State.Picking?, State.RunGeneration = Generation, State.Mode = fnm_mode.Race):
            if (Spot := PodiumSpot[], Character := State.Player.GetFortCharacter[], Character.TeleportTo[Spot, MakeRotationFromYawPitchRollDegrees(ArrivalYaw, 0.0, 0.0)]):
                Print("FNM: to the podium at {Spot}, {PodiumDistance(Spot)}")
                # The crowd cheers them in (G9 D2), with the finish fanfare (FinishSounds waits PodiumSeconds too); not on
                # the kill, which has boss_dead and BOSS DOWN.
                Sound(State.Player, fnm_cue.CrowdCheer)
                spawn{ WideLook(State, PodiumWideSeconds, WideMoveCm, "podium") }
            else:
                Print("FNM: podium teleport failed (no RACE AGAIN button, or the character could not be moved)")

    # Where a finisher is stood at the podium: centred between the RACE AGAIN (fnm_new_race) and NEW SKILL buttons, which
    # face -Y, the way players arrive, PodiumStandOff in front of them (a few steps), on the victory area's floor (the
    # fnm_finish pad's level), ArrivalLift up; never closer than ArrivalForward past that pad (landing on a pad sank a
    # player into it, 2026-10-03). The wide camera frames both lecterns and the all-time board (PodiumLater, WideLook):
    # standing far enough back for the player's own camera to see the board would put them on the pad (round-2 QA).
    PodiumSpot()<transacts><decides>:vector3 =
        Race := NewRaceButtons[0].GetTransform().Translation
        Other := if (Skill := ChangeSkillButtons[0]) then Skill.GetTransform().Translation else Race
        FloorZ := if (Pad := FinishPad?) then Pad.GetTransform().Translation.Z else Race.Z - 177.0
        var Y : float = Race.Y - PodiumStandOff
        if (Pad := FinishPad?):
            set Y = Max(Y, Pad.GetTransform().Translation.Y + ArrivalForward)
        vector3{X := (Race.X + Other.X) / 2.0, Y := Y, Z := FloorZ + ArrivalLift}

    # "RACE AGAIN 2.4 m, NEW SKILL 4.9 m" from Spot, for the log (flat distances).
    PodiumDistance(Spot:vector3)<transacts>:string =
        var Line : string = ""
        for (Button : NewRaceButtons):
            set Line += "RACE AGAIN {FnmMetres(Spot, Button.GetTransform().Translation)} m"
        for (Button : ChangeSkillButtons):
            set Line += ", NEW SKILL {FnmMetres(Spot, Button.GetTransform().Translation)} m"
        Line

    DebugToPodium(State:fnm_player_state)<suspends>:void =
        Sleep(1.0)
        if (Button := NewRaceButtons[0], Character := State.Player.GetFortCharacter[]):
            Spot := Button.GetTransform().Translation - vector3{X := 0.0, Y := 200.0, Z := 100.0}
            if (Character.TeleportTo[Spot, MakeRotationFromYawPitchRollDegrees(ArrivalYaw, 0.0, 0.0)]):
                Print("FNM: debug at podium {Spot}")

    # The all-time screen (a fixed ALL-TIME BEST line, then the skill name and its rows): one skill at a time, every player on the island ranked by their saved all-time best for it
    # (fnm_save.verse). Cycles every HallCycleSeconds through the skills anyone present has a time for; a finish shows
    # its skill at once and holds it (FinishPlayer sets HallHoldUntil).
    HallLoop()<suspends>:void =
        var Cursor : int = 0
        loop:
            if (GetSimulationElapsedTime() >= HallHoldUntil):
                Skills := HallSkills()
                if (Skills.Length = 0):
                    SetHall("", array{FnmText("Finish a race to get on the board!")})
                else if (Slot := Mod[Cursor, Skills.Length], Skill := Skills[Slot]):
                    ShowHall(Skill)
                set Cursor += 1
            Sleep(HallCycleSeconds)

    # Indices of the skills at least one present player has an all-time best for.
    HallSkills():[]int =
        Players := GetPlayspace().GetPlayers()
        for (K -> Each : Cartridges, HallHasTime[Players, Each.Id]) { K }

    HallHasTime(Players:[]player, Id:string)<transacts><decides>:void =
        var Found : logic = false
        for (Each : Players, FnmSavedBest[Each, Id]):
            set Found = true
        Found?

    ShowHall(Skill:int):void =
        if (Cartridge := Cartridges[Skill]):
            var Rows : []fnm_result = array{}
            for (Each : GetPlayspace().GetPlayers(), Time := FnmSavedBest[Each, Cartridge.Id]):
                set Rows += array{fnm_result{Who := Each, Time := Time}}
            Lines := for (K -> Row : SortResults(Rows)) { FnmRow(K + 1, Row.Who, FnmClock(Row.Time)) }
            SetHall(Cartridge.Title, Lines)

    SetHall(Head:string, Lines:[]message):void =
        for (Board : HallHeads):
            Board.SetText(FnmText(Head))
            Board.UpdateDisplay()
        for (K -> Board : HallRows):
            Board.SetText(if (Line := Lines[K]) then Line else FnmText(""))
            Board.UpdateDisplay()

    # The session board for skill Index (empty until someone finishes that skill).
    BoardFor(Index:int)<transacts>:[]fnm_result =
        if (Rows := Boards[Index]) then Rows else array{}

    # Puts Who's Time (with that run's Splits) on skill Index's board: replaces their row only when faster, else adds
    # one; fastest first, capped at BoardSize.
    RecordResult(Index:int, Who:player, Time:float, Splits:[]float):void =
        var Rows : []fnm_result = array{}
        var Had : logic = false
        for (Row : BoardFor(Index)):
            if (Row.Who = Who):
                set Had = true
                set Rows += array{if (Time < Row.Time) then fnm_result{Who := Who, Time := Time, Splits := Splits} else Row}
            else:
                set Rows += array{Row}
        if (not Had?):
            set Rows += array{fnm_result{Who := Who, Time := Time, Splits := Splits}}
        Sorted := SortResults(Rows)
        Capped := for (K -> Row : Sorted, K < BoardSize) { Row }
        if (set Boards[Index] = Capped) {}

    # Fastest first (insertion sort; boards are a handful of rows).
    SortResults(Rows:[]fnm_result)<transacts>:[]fnm_result =
        var Sorted : []fnm_result = array{}
        for (Row : Rows):
            var Next : []fnm_result = array{}
            var Placed : logic = false
            for (Other : Sorted):
                if (not Placed?, Row.Time < Other.Time):
                    set Next += array{Row}
                    set Placed = true
                set Next += array{Other}
            if (not Placed?):
                set Next += array{Row}
            set Sorted = Next
        Sorted

    # The automatic restart (no podium button, or DebugAutoRightAnswers): results for RestartSeconds with a countdown,
    # then StartNewRun. CHANGE SKILL (ChangeSkill) or NEW RACE bumps RunGeneration, which cancels this.
    NextRun(State:fnm_player_state)<suspends>:void =
        Generation := State.RunGeneration
        var Left : int = Max(1, RestartSeconds)
        loop:
            if (Left <= 0 or State.RunGeneration <> Generation) then break
            State.Hud.SetCountdown("Next run in {Left}")
            Sleep(1.0)
            set Left -= 1
        if (not PlayerStates[State.Player] or State.RunGeneration <> Generation):
            return
        StartNewRun(State)

    # A fresh run from station 1: barriers closed again for this player, new questions, streak and clock reset;
    # same skill.
    StartNewRun(State:fnm_player_state)<suspends>:void =
        set State.Partial = false
        State.Hud.HideFinishButtons()
        State.Hud.HideResults()
        for (Station : Stations, MaybePassage : Station.Passages, Passage := MaybePassage?):
            Passage.RemoveFromIgnoreList(State.Player)
        ResetArena(State)
        set State.Stage = 1
        set State.FirstTryCorrect = 0
        set State.Streak = 0
        set State.BestStreak = 0
        set State.Finished = false
        set State.Busy = false
        DrawItem(State)
        ShowCurrent(State)
        State.Hud.SetClock(FnmClock(0.0))
        if (First := Stations[0]):
            SendTo(State.Player, First.RetryTeleporter)
        GiveLoadout(State.Player)
        Countdown(State)

    # 3, 2, 1, GO! with the player held still, then the race clock runs until they finish (or a new run starts).
    Countdown(State:fnm_player_state)<suspends>:void =
        set State.RunGeneration += 1
        Generation := State.RunGeneration
        # The picker's bed stops at the countdown (G9 D2); GO starts the tier's (Music).
        SetMusic(State.Player, 0)
        # Station 1 as the tutorial (G9): on the player's first run of the session.
        if (not State.TutorialDone?, State.Stage = 1, State.Mode = fnm_mode.Race):
            set State.TutorialDone = true
            spawn{ Tutorial(State, Generation) }
        set State.StartTime = -1.0
        set State.ClockPenalty = 0.0
        set State.WrongDoors = 0
        set State.Splits = array{}
        NewRunMarks(State)
        State.Hud.ClearDelta()
        ChoosePace(State)
        State.Hud.SetStreak(StreakCopy(State, 0))
        MaybeCharacter := option{State.Player.GetFortCharacter[]}
        if (Character := MaybeCharacter?):
            Character.PutInStasis(stasis_args{AllowTurning := true, AllowFalling := false, AllowEmotes := false})
        for (Count : array{3, 2, 1}):
            State.Hud.FlashBig("{Count}", NamedColors.White, 0.0)
            Sound(State.Player, if (Count = 3) then fnm_cue.Countdown3 else if (Count = 2) then fnm_cue.Countdown2 else fnm_cue.Countdown1)
            Sleep(CountdownStepSeconds)
        if (Character := MaybeCharacter?):
            Character.ReleaseFromStasis()
        State.Hud.FlashBig("GO!", NamedColors.Lime, 1.0)
        State.Hud.ShowVolt(fnm_volt.Go)
        Sound(State.Player, fnm_cue.Go)
        Music(State)
        # The pace target is fixed at GO! (a record set during the countdown counts).
        ChoosePace(State)
        set State.StartTime = GetSimulationElapsedTime()
        Print("FNM: run {State.Runs + 1} GO at sim {State.StartTime} s, pace target {State.PaceTarget.Length} splits")
        loop:
            if (State.RunGeneration <> Generation or State.StartTime < 0.0 or State.Finished?) then break
            State.Hud.SetClock(FnmClock(RunClock(State, GetSimulationElapsedTime())))
            Sleep(0.1)

    # Station 1 teaches the rule on a player's first run of the session (G9, ux_critique #2: no copy said door = answer,
    # how a door opens, that walking in commits, or that A is on the left): three captions under 50 characters on the
    # slate's line under the tiles, from the countdown on, each up long enough to read while walking the 30 m hall. They
    # stop at the first door answered (a wrong door's lesson takes the line) or once the player leaves station 1.
    Tutorial(State:fnm_player_state, Generation:int)<suspends>:void =
        Whole := if (W := Round[WrongDoorSeconds]) then W else 3
        TipA : tuple(string, float) = ("Each door is an answer. A is on the left.", CountdownStepSeconds * 3.0 + 0.5)
        TipB : tuple(string, float) = ("Run through your answer's door. E opens it.", TutorialStepSeconds)
        TipC : tuple(string, float) = ("Wrong door: a penalty, +{Whole} s, then try again.", TutorialStepSeconds + 1.0)
        Steps : []tuple(string, float) = array{TipA, TipB, TipC}
        Print("FNM: tutorial captions (first run of the session)")
        var K : int = 0
        var Shown : int = -1
        loop:
            if (Step := Steps[K], TutorialOn(State, Generation)?):
                set Shown = State.Hud.ShowFeedback(Step(0), NamedColors.Gold)
                Print("FNM: tutorial {K + 1}/{Steps.Length}: {Step(0)}")
                Sleep(Step(1))
                set K += 1
            else:
                break
        if (Shown >= 0) then State.Hud.ClearFeedbackIf(Shown)
        Print("FNM: tutorial done ({K} of {Steps.Length} captions shown)")

    # A run starts (Countdown): every station not reached yet, no redemption queued, no shield held, no immunity, no
    # strike pending on them.
    NewRunMarks(State:fnm_player_state):void =
        set State.Marks = for (Station : Stations) { FnmMarkUnreached }
        set State.RedeemQueue = array{}
        set State.RedeemStage = 0
        set State.Redeemed = 0
        set State.BossDowned = false
        set State.Shield = false
        set State.ImmuneUntil = -100.0
        State.Hud.SetShield(false)

    # Station Stage's mark for this run (FnmMark*); a right door after a miss also queues the station for REDEMPTION.
    MarkStation(State:fnm_player_state, Stage:int, Mark:int):void =
        if (set State.Marks[Stage - 1] = Mark) {}
        if (Mark = FnmMarkMissed):
            set State.RedeemQueue += array{Stage}
            Print("FNM: station {Stage} missed (right after a miss): queued for redemption ({State.RedeemQueue.Length} queued)")

    # The tutorial goes on while the player is still on this run's station 1 and has not answered a door yet.
    TutorialOn(State:fnm_player_state, Generation:int)<transacts>:logic =
        if (PlayerStates[State.Player], State.RunGeneration = Generation, State.Stage = 1, State.Mode = fnm_mode.Race, not State.Finished?, not State.Picking?, not State.Busy?, not State.MissedCurrent?) then true else false

    # Streak line for the top panel: "" (no streak), "STREAK x3", "STREAK x3  -  SPEED BOOST 4s" or (streak 1)
    # "SPEED BOOST 3s". BoostLeft = whole seconds of boost left (0 = none running).
    # G10 (C1, the goal gradient): with a streak the line also names the next reward, "STREAK x2  -  1 more for a SHIELD"
    # (NextRewardCopy).
    StreakCopy(State:fnm_player_state, BoostLeft:int):string =
        Next := NextRewardCopy(State)
        StreakPart := if (State.Streak >= 2, Next <> "") then "STREAK x{State.Streak}  -  {Next}" else if (State.Streak >= 2) then "STREAK x{State.Streak}" else ""
        if (BoostLeft <= 0) then StreakPart
        else if (StreakPart = "") then "SPEED BOOST {BoostLeft}s"
        else "{StreakPart}  -  SPEED BOOST {BoostLeft}s"

    # The next reward the first-try streak earns: "1 more for a SHIELD" (streak ShieldStreak, when none is held), "2 more
    # for a STRIKE" (each StrikeStreaks value, when StrikesOn); the nearest one; "" past the last.
    NextRewardCopy(State:fnm_player_state)<transacts>:string =
        var At : int = 0
        var Name : string = ""
        if (not State.Shield?, ShieldStreak > State.Streak):
            set At = ShieldStreak
            set Name = "SHIELD"
        if (StrikesOn?):
            for (Milestone : StrikeStreaks, Milestone > State.Streak, (At = 0 or Milestone < At)):
                set At = Milestone
                set Name = "STRIKE"
        if (At > 0) then "{At - State.Streak} more for a {Name}" else ""

    # Speeds the player up (fnm_boost modulator) for Seconds; a newer boost or StopBoost ends this one. Ticks once a
    # second so the HUD counts the boost down, re-activating the modulator (3 s duration) every BoostReapplySeconds
    # or sooner.
    Boost(State:fnm_player_state, Seconds:float)<suspends>:void =
        set State.BoostGeneration += 1
        Generation := State.BoostGeneration
        set State.BoostUntil = GetSimulationElapsedTime() + Seconds
        if (Device := BoostDevice?):
            # Just after the right-door chime, so the two do not land on the same instant.
            # With a streak the voice line is the celebration; the 3.5 s boost whoosh would bury it.
            if (State.Streak < 2):
                spawn{ SoundLater(State.Player, fnm_cue.Boost, 0.4) }
            spawn{ BoostTrail(State, Generation, Seconds) }
            var Elapsed : float = 0.0
            var SinceApply : float = BoostReapplySeconds
            loop:
                if (Elapsed >= Seconds or State.BoostGeneration <> Generation) then break
                Tick := Min(1.0, Seconds - Elapsed)
                if (SinceApply + Tick > BoostReapplySeconds):
                    Device.Activate(State.Player)
                    set SinceApply = 0.0
                Left := if (Up := Ceil[Seconds - Elapsed]) then Up else 0
                if (not State.Finished?):
                    State.Hud.SetStreak(StreakCopy(State, Left))
                Sleep(Tick)
                set Elapsed += Tick
                set SinceApply += Tick
            if (State.BoostGeneration = Generation):
                Device.Deactivate(State.Player)
                if (not State.Finished?):
                    State.Hud.SetStreak(StreakCopy(State, 0))
        else if (not State.Finished?):
            State.Hud.SetStreak(StreakCopy(State, 0))

    # The boost's comet tail (G9 spectacle, fnm_fx): a puff of NS_fnm_trail_* at the player's feet every FnmTrailEvery s in
    # the streak's colour (FnmTrailTier: 1-2 cyan, 3-5 gold, 6+ fire), so the others see a streaker go by. It stops when
    # the boost runs out or ends early (a newer boost or StopBoost: a wrong door, an elimination, the finish), when the
    # player finishes or leaves; nothing is spawned while they are down.
    BoostTrail(State:fnm_player_state, Generation:int, Seconds:float)<suspends>:void =
        Streak := State.Streak
        Colour := FnmTrailNames[FnmTrailTier(Streak)] or "?"
        Start := GetSimulationElapsedTime()
        var Puffs : int = 0
        var Why : string = "ran out"
        loop:
            if (State.BoostGeneration <> Generation):
                set Why = "boost ended early"
                break
            if (State.Finished? or not PlayerStates[State.Player]):
                set Why = "finished or left"
                break
            if (GetSimulationElapsedTime() - Start >= Seconds) then break
            if (Character := State.Player.GetFortCharacter[], Character.IsActive[]):
                FnmSpawnTrail(Streak, Character.GetTransform().Translation)
                set Puffs += 1
            Sleep(FnmTrailEvery)
        Print("FNM: fx boost trail {Colour} (streak {Streak}): {Puffs} puffs in {GetSimulationElapsedTime() - Start} s, {Why}")

    StopBoost(State:fnm_player_state):void =
        set State.BoostGeneration += 1
        set State.BoostUntil = -1.0
        if (Device := BoostDevice?):
            Device.Deactivate(State.Player)
        if (not State.Finished?):
            State.Hud.SetStreak(StreakCopy(State, 0))

    # Sweeps a container SliderTravel along its own forward axis (across the hallway) and back, forever.
    Slide(Slider:creative_prop)<suspends>:void =
        Home := Slider.GetTransform()
        Far := Home.Translation + Home.Rotation.GetLocalForward() * SliderTravel
        loop:
            Slider.MoveTo(Far, Home.Rotation, SliderSeconds)
            Sleep(SliderPause)
            Slider.MoveTo(Home.Translation, Home.Rotation, SliderSeconds)
            Sleep(SliderPause)

    # Ice hallways: slippery footing while inside a zone, normal footing once out. The zone's enter/exit events answer
    # at once; WatchIce polls the zones (IsInVolume) every DoorWatchSeconds as the backstop, so a teleport out of the
    # zone (a penalty, an elimination, a new run) ends the ice even when no exit event comes.
    OnIceEnter(Agent:agent):void =
        if (Player := player[Agent], State := PlayerStates[Player]):
            SetIce(State, true)

    OnIceExit(Agent:agent):void =
        if (Player := player[Agent], State := PlayerStates[Player]):
            SetIce(State, false)

    WatchIce(State:fnm_player_state):void =
        var Inside : logic = false
        # (A boss-mode player is never on ice: no ice zone in that arena.)
        for (Zone : IceZones, State.Mode = fnm_mode.Race, Zone.IsInVolume[State.Player]):
            set Inside = true
        SetIce(State, Inside)

    SetIce(State:fnm_player_state, On:logic):void =
        if (On <> State.OnIce, Device := IceFloor?):
            set State.OnIce = On
            if (On?):
                Device.AddTo(State.Player)
                Print("FNM: on ice")
            else:
                Device.RemoveFrom(State.Player)
                Print("FNM: off ice")

    EndGameLater(Finisher:player)<suspends>:void =
        Sleep(EndGameDelaySeconds)
        if (Finisher.IsActive[]):
            EndGameDevice.Activate(Finisher)

    # ---------------------------------------------------------------- G10 rewards: SHIELD and STRIKE (gamification 4)

    # A first-try right answer that makes the streak ShieldStreak earns a SHIELD (when none is held); one that makes it a
    # StrikeStreaks value earns a STRIKE (StrikesOn), fired StrikeDelaySeconds later (StrikeLater). Returns the verdict's
    # tail: "  +SHIELD", "  +STRIKE" or "".
    EarnRewards(State:fnm_player_state):string =
        var Tail : string = ""
        if (State.Streak = ShieldStreak, not State.Shield?):
            set State.Shield = true
            State.Hud.SetShield(true)
            set Tail = "  +SHIELD"
            Print("FNM: shield earned at streak {State.Streak}")
        if (StrikesOn?):
            for (Milestone : StrikeStreaks, Milestone = State.Streak):
                set Tail = "  +STRIKE"
                Print("FNM: strike earned at streak {State.Streak}")
                spawn{ StrikeLater(State, State.Streak) }
        Tail

    # A held SHIELD takes a wrong door's (or pad's) penalty: no penalty effect, no hold, no clock charge. The caller has
    # already reset the streak and the first-try credit, and the door stays shut. The player goes to the retry spot (with
    # the wide camera at a station) and the same question comes back reshuffled under "SHIELD SAVED YOU  -  still wrong:
    # <that choice's feedback>". StationNumber names the station in the feed line (0 = the boss arena).
    ShieldSaved(State:fnm_player_state, Station:fnm_station, StationNumber:int, Lesson:string)<suspends>:void =
        set State.Shield = false
        State.Hud.SetShield(false)
        Sound(State.Player, fnm_cue.Wrong)
        State.Hud.FlashVerdict(false, "SHIELD!")
        Where := if (StationNumber > 0) then "at station {StationNumber}" else "at the boss"
        MissFeed(State, FnmFeedShieldSaved(State.Player, Where), "Your SHIELD saved you {Where}", "a shield saved them {Where}")
        Print("FNM: shield saved the player {Where}: no penalty, no hold, no clock charge (streak and first-try credit lost)")
        SendToRetry(State.Player, Station)
        if (Station.RetrySpot?):
            spawn{ WideLook(State, RetryWideSeconds, WideMoveCm, "retry spot, shield") }
        Retry(State, "SHIELD SAVED YOU  -  still wrong: {Lesson}")

    # A STRIKE (C3), StrikeDelaySeconds after it was earned: aimed at the nearest racer ahead in strip order who can take
    # one (StrikeTarget; DebugStrikeSelf: the striker), who is warned ("INCOMING STRIKE!" big, the striker's name in their
    # feed) and struck StrikeWarnSeconds later (StrikeLand). With nobody ahead to take it, LeaderBonusSeconds of boost
    # instead (LeaderBonus; the leader's always, so strikes only flow forward). Dropped if the striker's run ended.
    StrikeLater(State:fnm_player_state, Streak:int)<suspends>:void =
        Generation := State.RunGeneration
        Sleep(StrikeDelaySeconds)
        Live := if (PlayerStates[State.Player], State.RunGeneration = Generation, not State.Finished?, not State.Picking?) then true else false
        if (not Live?):
            Print("FNM: strike from streak {Streak} dropped (the striker's run ended)")
            return
        MaybeTarget := if (DebugStrikeSelf?) then option{State} else StrikeTarget(State)
        if (Target := MaybeTarget?):
            set Target.Struck = true
            AtSelf := if (Target.Player = State.Player) then true else false
            Print("FNM: strike from streak {Streak} aimed at {if (AtSelf?) then "the striker (DebugStrikeSelf)" else "the racer ahead"}; warning up, lands in {StrikeWarnSeconds} s")
            # A stock timer tick (guards_up carries the announcer's "Guards ahead!"), with the big warning.
            Sound(Target.Player, fnm_cue.Countdown1)
            Target.Hud.FlashBig("INCOMING STRIKE!", NamedColors.Orange, StrikeWarnSeconds + 0.3)
            Target.Hud.PushFeed(FnmFeedIncoming(State.Player))
            if (not AtSelf?) then State.Hud.PushFeed(FnmFeedStrikeAway(Target.Player))
            Sleep(StrikeWarnSeconds)
            StrikeLand(State, Target)
        else:
            LeaderBonus(State, Streak)

    # The nearest racer ahead of State in strip order (SortRace / RaceEntry, the order the rivals strip shows) who can take
    # a strike now (StrikeOpen); false when there is none.
    StrikeTarget(State:fnm_player_state):?fnm_player_state =
        Now := GetSimulationElapsedTime()
        Entries := SortRace(for (Each : GetPlayspace().GetPlayers()) { RaceEntry(Each, Now) })
        var Mine : int = -1
        for (K -> Entry : Entries, Entry.Who = State.Player):
            set Mine = K
        var Found : ?fnm_player_state = false
        for (K -> Entry : Entries, K < Mine, Other := PlayerStates[Entry.Who], StrikeOpen(Other, Now)?):
            set Found = option{Other}
        Found

    # Who can take a strike at Now: a race player racing (past GO, not picking, not finished), not at the arena stage,
    # not answering a door or under a penalty (Busy), not in a door's vestibule, standing, not already struck or aimed
    # at, and past their immunity.
    StrikeOpen(Target:fnm_player_state, Now:float)<transacts>:logic =
        if (Target.Mode = fnm_mode.Race, not Target.Picking?, not Target.Finished?, Target.StartTime >= 0.0, not AtArena(Target)?, not Target.Busy?, not Target.Struck?, Now >= Target.ImmuneUntil, not InVestibule(Target)?, Character := Target.Player.GetFortCharacter[], Character.IsActive[]) then true else false

    # True while the player stands in one of their current station's door zones (DoorZoneAt: the whole vestibule).
    InVestibule(State:fnm_player_state)<transacts>:logic =
        if (Station := Stations[State.Stage - 1], Character := State.Player.GetFortCharacter[], DoorZoneAt(Station.Doors, Station.Passages, Character.GetTransform().Translation) >= 0) then true else false

    # The strike's effect, from C3's light, in-place pool (penalty kinds, for their labels and voice lines), drawn when a
    # strike lands (a shield's block draws none): random; under DebugStrikeSelf in turn (Freeze, Mud, Dizzy, Lights Out)
    # so a test sees each.
    PickStrike()<transacts>:fnm_penalty =
        Pool := array{fnm_penalty.Freeze, fnm_penalty.Mud, fnm_penalty.Dizzy, fnm_penalty.Blackout}
        Index := if (DebugStrikeSelf?) then Mod[StrikeCursor, Pool.Length] or 0 else GetRandomInt(0, Pool.Length - 1)
        set StrikeCursor += 1
        if (Kind := Pool[Index]) then Kind else fnm_penalty.Freeze

    # The feed's verb for a strike: "<A> froze <B>!".
    StrikeVerb(Kind:fnm_penalty)<transacts>:string =
        if (Kind = fnm_penalty.Freeze) then "froze"
        else if (Kind = fnm_penalty.Mud) then "muddied"
        else if (Kind = fnm_penalty.Dizzy) then "dizzied"
        else "blacked out"

    # The strike lands: a held shield blocks it (the shield is spent, the public feed tells it); else the effect, the
    # public feed line and StrikeImmuneSeconds of immunity. A real target that has meanwhile walked into a vestibule,
    # answered a door, finished or reached the arena is missed (DebugStrikeSelf lands on the striker regardless, but
    # never while they pick or after their finish).
    StrikeLand(Striker:fnm_player_state, Target:fnm_player_state)<suspends>:void =
        Now := GetSimulationElapsedTime()
        set Target.Struck = false
        Present := if (PlayerStates[Target.Player]) then true else false
        Open := if (DebugStrikeSelf?, Present?, Target.Mode = fnm_mode.Race, not Target.Finished?, not Target.Picking?) then true else if (Present?, StrikeOpen(Target, Now)?) then true else false
        if (not Open?):
            Print("FNM: strike missed (the target was no longer open: finished, at a door, in the arena or gone)")
            Striker.Hud.PushFeed(FnmText("Your STRIKE missed!"))
            return
        if (Target.Shield?):
            set Target.Shield = false
            Target.Hud.SetShield(false)
            Sound(Target.Player, fnm_cue.CorrectRetry)
            Target.Hud.FlashBig("SHIELD BLOCKED IT!", NamedColors.Aqua, 1.5)
            Broadcast(FnmFeedShieldBlock(Target.Player, Striker.Player), "a shield blocked a strike")
            Print("FNM: strike blocked by the target's shield (shield spent)")
            return
        Kind := PickStrike()
        set Target.Struck = true
        set Target.ImmuneUntil = Now + StrikeImmuneSeconds
        Print("FNM: strike lands: {FnmPenaltyLabel(Kind)}, immune for {StrikeImmuneSeconds} s")
        Broadcast(FnmFeedStrike(Striker.Player, StrikeVerb(Kind), Target.Player), "{StrikeVerb(Kind)} a racer with a strike")
        Target.Hud.FlashBig(FnmPenaltyLabel(Kind), NamedColors.Orange, 1.5)
        spawn{ PenaltyLines(Target.Player, StrikeCue(Kind)) }
        StrikeEffect(Target, Kind)
        set Target.Struck = false

    # A strike's effect on Target, in place (never a send-back; the question, streak and credit untouched): Freeze
    # StrikeFreezeSeconds in the ice cube (held, frost), Mud StrikeMudSeconds (the fnm_mud modulator and its screen), Dizzy
    # StrikeBlurSeconds of radial blur with no spin, Lights Out StrikeDarkSeconds black (held). Mud and the blur stop at
    # the target's next right answer (Cleanse), like a wrong door's.
    StrikeEffect(Target:fnm_player_state, Kind:fnm_penalty)<suspends>:void =
        Player := Target.Player
        Began := GetSimulationElapsedTime()
        if (Kind = fnm_penalty.Freeze):
            if (Character := Player.GetFortCharacter[]):
                Feet := Character.GetTransform().Translation - vector3{X := 0.0, Y := 0.0, Z := FeetDrop}
                # The wide camera, as a wrong door's Freeze: the player's own camera sat inside the ice cube (a white
                # screen, seen in play 2026-10-14); 9 m out they see themselves frozen.
                WideCamera(Player, true)
                Character.PutInStasis(stasis_args{AllowTurning := false, AllowFalling := false, AllowEmotes := false})
                FxOn(Player, FrostFx)
                Ice := IceRig.NextIndex()
                Placed := IceRig.Place(Ice, Feet, 0.0)
                Print("FNM: strike ice {Ice} placed={FnmYesNo(Placed)} at {Feet}")
                Sleep(StrikeFreezeSeconds)
                IceRig.Park(Ice)
                FxOff(Player, FrostFx)
                Character.ReleaseFromStasis()
                WideCamera(Player, false)
        else if (Kind = fnm_penalty.Mud):
            Afflict(Player)
            Epoch := EpochOf(Player)
            spawn{ ScreenFx(Player, MudFx, StrikeMudSeconds, Epoch) }
            MuddyFor(Player, Epoch, StrikeMudSeconds)
        else if (Kind = fnm_penalty.Dizzy):
            Afflict(Player)
            Epoch := EpochOf(Player)
            BlurFor(Player, Epoch, StrikeBlurSeconds)
        else:
            if (Character := Player.GetFortCharacter[]):
                Character.PutInStasis(stasis_args{AllowTurning := false, AllowFalling := false, AllowEmotes := false})
                Target.Hud.SetBlack(true)
                Sleep(StrikeDarkSeconds)
                Character.ReleaseFromStasis()
                Target.Hud.SetBlack(false)
        Print("FNM: strike effect {FnmPenaltyLabel(Kind)} over after {GetSimulationElapsedTime() - Began} s; immune until sim {Target.ImmuneUntil}")

    # The penalty voice line a strike's effect plays (its PenaltyLines, as a wrong door's).
    StrikeCue(Kind:fnm_penalty)<transacts>:fnm_cue =
        if (Kind = fnm_penalty.Freeze) then fnm_cue.PenaltyFreeze
        else if (Kind = fnm_penalty.Mud) then fnm_cue.PenaltyMud
        else if (Kind = fnm_penalty.Dizzy) then fnm_cue.PenaltyDizzy
        else fnm_cue.PenaltyBlackout

    # No racer ahead could take the strike (always so for the leader): LeaderBonusSeconds added to the boost left, "LEADER
    # BONUS" when the striker leads the racers.
    LeaderBonus(State:fnm_player_state, Streak:int):void =
        Now := GetSimulationElapsedTime()
        Entries := SortRace(for (Each : GetPlayspace().GetPlayers()) { RaceEntry(Each, Now) })
        var Leads : logic = false
        var Seen : logic = false
        for (Entry : Entries, Racing(Entry.Who)?):
            if (not Seen?):
                set Seen = true
                if (Entry.Who = State.Player) then set Leads = true
        Left := Max(0.0, State.BoostUntil - Now)
        Whole := if (W := Round[LeaderBonusSeconds]) then W else 2
        spawn{ Boost(State, Left + LeaderBonusSeconds) }
        State.Hud.FlashBig(if (Leads?) then "LEADER BONUS!  +{Whole} s BOOST" else "NO TARGET  -  +{Whole} s BOOST", NamedColors.Gold, 1.5)
        Print("FNM: strike from streak {Streak}: nobody ahead could take it (leader {FnmYesNo(Leads)}): boost +{LeaderBonusSeconds} s on {Left} s left")

    # ---------------------------------------------------------------- boss arena (G6 item 3)

    # A player reaches the arena stage (the last station's right door, or DebugStartStage): a hardest-tier question (on the
    # slate now, or after the recap card when ShowNow is false) and the boss music. BossLoop brings a boss up for them. The
    # fight's cue, its feed line and the arena's one instruction wait until they walk into the arena hall (WatchArena,
    # ArenaArrival): fired here, 44 m early, the instruction flashed while the kid was still in the vestibule and its hint
    # line was overwritten in the same tick (ux_critique B6).
    EnterArena(State:fnm_player_state, ShowNow:logic):void =
        set State.Hits = 0
        set State.ArenaArrived = false
        DrawItem(State)
        if (ShowNow?) then ShowCurrent(State)
        Music(State)
        Print("FNM: arena stage reached ({BossHitsToKill} hits to win)")

    # The player has walked into the arena hall (WatchArena, once per run): the fight cue, the public feed line and the
    # arena's one instruction, big. The hits are counted on the boss bar alone; a player who shoots the boss is told
    # bullets do nothing (RaceGunHint).
    ArenaArrival(State:fnm_player_state):void =
        set State.ArenaArrived = true
        # G10: the compact slate from here to the end of the run, so the titan reads over it.
        UpdateCompact(State)
        Sound(State.Player, fnm_cue.BossFight)
        # The titan's entrance (G9 D2): the jump-slam from its first frame and the roar as the slam lands, SlamLandsSeconds
        # (1.15) after boss_fight, past the 0.9 s mix rule. Not while it lies after a kill: the respawn's Arrive stands it up.
        if (not RaceTitan.Falling?):
            spawn{ RaceTitan.Entrance() }
            spawn{ SoundLater(State.Player, fnm_cue.TitanRoar, RaceTitan.SlamLandsSeconds) }
        Broadcast(FnmFeedBoss(State.Player), "reached the boss!")
        State.Hud.FlashBig("STEP ON THE RIGHT ANSWER PAD!", NamedColors.Gold, 4.0)
        Print("FNM: entered the arena: instruction up")

    # Arena entry (G9): a race player at the arena stage found inside the arena hall (its hallway box) for the first time
    # this run.
    WatchArena(State:fnm_player_state):void =
        if (State.Mode = fnm_mode.Race, not State.ArenaArrived?, not State.Finished?, not State.Picking?, AtArena(State)?, Character := State.Player.GetFortCharacter[], Character.IsActive[]):
            Hall := HallwayAt(Character.GetTransform().Translation)
            if (Hall = Stations.Length):
                ArenaArrival(State)

    # A new run or skill: the gate closes again for this player and their hits reset.
    ResetArena(State:fnm_player_state):void =
        set State.Hits = 0
        set State.ArenaArrived = false
        set State.RetryHolding = false
        UpdateCompact(State)
        if (A := Arena?, Gate := A.Gate?):
            Gate.RemoveFromIgnoreList(State.Player)

    # A pad answered at the arena stage: a right one is a hit on the boss, a wrong one the normal penalty (back to the
    # arena entry) plus the adds.
    HandlePad(State:fnm_player_state, A:fnm_arena, DoorIndex:int)<suspends>:void =
        if (Item := State.Cartridge.Items[State.CurrentItem]):
            Choice := ChoiceAt(State, DoorIndex)
            if (Choice < 0):
                set State.Busy = false
                FlashNotice(State, "No choice {FnmChoiceLetter(DoorIndex)} here")
            else if (A.Boss?, not BossAlive?):
                # No titan up yet (it rises as the first fighter reaches the arena stage, and BossRespawnSeconds after a
                # kill): the pad takes no answer, right or wrong, and the question stays (G10; it used to say "DIRECT HIT!
                # 5 TO GO", send the player back and burn the question for no damage, ux_critique P2).
                set State.Busy = false
                Print("FNM: pad {FnmChoiceLetter(DoorIndex)} held: no boss up yet (no answer taken)")
                FlashNotice(State, "The titan is rising... step on your pad again when it stands!")
            else if (Choice = Item.Answer):
                # The recap card, as at the stations (G9): the solved item, then the next question. It replaced the delayed
                # "Last one:  <explanation>" line under the NEXT question (boss mode keeps that, FnmLastOne).
                Solved := RecapOf(State, Item, DoorIndex, "CORRECT!")
                BossHit(State, A)
                set State.Busy = false
                # The pads are live during the recap and the entry is ~2 s from them: the card stays no longer than the
                # answer cooldown (TooSoon), so a pad answers only a question that is on the slate (round-2 audit).
                if (not State.Finished?):
                    Recap(State, Solved, Min(RecapSeconds, RightCooldownSeconds))
            else:
                set State.MissedCurrent = true
                set State.Streak = 0
                StopBoost(State)
                # A held SHIELD takes a wrong pad's penalty too; the titan still calls its adds (G10).
                if (State.Shield?):
                    SummonAdds(A)
                    ShieldSaved(State, A.Station, 0, FeedbackFor(Item, Choice))
                    return
                Kind := PickPenalty()
                Past := FnmPenaltyPast(Kind)
                MissFeed(State, FnmFeedBossPenalty(State.Player, Past), "You got {Past} by the boss", "got {Past} by the boss")
                Sound(State.Player, fnm_cue.Wrong)
                Tail := ChargeWrongDoor(State)
                State.Hud.FlashVerdict(false, FnmPenaltyLabel(Kind) + Tail)
                State.Hud.ShowVolt(fnm_volt.Wag)
                Lesson := FeedbackFor(Item, Choice)
                Shown := State.Hud.ShowFeedback(Lesson, NamedColors.Tomato)
                SummonAdds(A)
                if (BossAlive?):
                    spawn{ RaceTitan.Taunt() }
                Punish(State.Player, A.Station, DoorIndex, Kind)
                Retry(State, Lesson)
        else:
            set State.Busy = false

    # A right pad: one hit on the shared boss (BossDamage), DIRECT HIT! with the team's hits still to go on the HUD and
    # from the announcer (FnmHitCue), the cannons' show (FireCannons), the player back to the arena entry and the next
    # question. The kill itself comes through the boss spawner's EliminatedEvent (BossDown).
    # G10: a redemption question answered right first try is REDEEMED! (its station half credit, Redeem); the killing hit
    # plays no boss_hit (boss_dead and BOSS DOWN carry the kill: up to four sounds stacked there, REVIEW 4). Left stays -1
    # when no boss is up (HandlePad holds such a pad, so it is only a safety net): no "N TO GO" then.
    BossHit(State:fnm_player_state, A:fnm_arena):void =
        Cleanse(State)
        Redeemed := Redeem(State)
        set State.Hits += 1
        set LastHitter = option{State.Player}
        var Left : int = -1
        var Target : ?fort_character = false
        var Stood : vector3 = vector3{X := 0.0, Y := 0.0, Z := 0.0}
        if (BossAlive?, Agent := BossAgent?, Character := Agent.GetFortCharacter[]):
            set BossHitsTaken += 1
            set Left = Max(BossHitsToKill - BossHitsTaken, 0)
            set Stood = Character.GetTransform().Translation
            set Target = option{Character}
            Amount := BossDamage(Character)
            set RaceBossHitAt = GetSimulationElapsedTime()
            set RacePadHitting = true
            Character.Damage(Amount)
            set RacePadHitting = false
            Print("FNM: boss hit {State.Hits} by the player (team {BossHitsTaken}/{BossHitsToKill}), damage {Amount}, health {BossPercent()}%")
        else:
            Print("FNM: boss hit {State.Hits} by the player, but no boss is up")
        Head := if (Redeemed?) then "REDEEMED!" else if (Left < 0) then "CORRECT!" else "DIRECT HIT!"
        if (Left > 0) then Sound(State.Player, fnm_cue.BossHit) else if (Left < 0) then Sound(State.Player, fnm_cue.Correct)
        State.Hud.FlashVerdict(true, if (Left > 0) then "{Head}  {Left} TO GO" else Head)
        # Volt cheers a hit that leaves the titan standing; the killing hit gets the finish board instead.
        if (Left > 0):
            State.Hud.ShowVolt(fnm_volt.Thumbs)
            spawn{ SoundLater(State.Player, FnmHitCue(Left), HitVoiceDelaySeconds) }
        # Back to the entry first, facing the boss: the show plays out ahead of them, and the blast cannot catch them.
        SendTo(State.Player, A.Station.RetryTeleporter)
        if (Character := Target?):
            spawn{ FireCannons(RaceRig, State.Player, Character, Stood, Left, false) }
            # The killing hit's flail and fall come from BossDown (RaceTitan.Fall).
            if (Left > 0):
                spawn{ RaceTitan.Hurt() }
            Now := GetSimulationElapsedTime()
            RefreshRaceBossBars(Now)
            for (Fighter : PlayerStates, ShowsRaceBossBar(Fighter, Now)?):
                spawn{ Fighter.Hud.HitBossBar() }
        # The next question is drawn here and shown by the caller after the recap card (HandlePad, Recap).
        if (not State.Finished?):
            DrawItem(State)

    # REDEMPTION (R4, G10): a right pad on a redemption question (RedeemStage) takes its station off the queue. Right first
    # try, the station is REDEEMED (its mark FnmMarkRedeemed, half credit in the medal); right only after a wrong pad, it
    # stays missed (the first-try right answer is the only thing that earns anything). True when it was redeemed.
    Redeem(State:fnm_player_state)<transacts>:logic =
        Stage := State.RedeemStage
        if (Stage <= 0):
            false
        else:
            set State.RedeemQueue = for (Queued : State.RedeemQueue, Queued <> Stage) { Queued }
            set State.RedeemStage = 0
            if (State.MissedCurrent?):
                Print("FNM: redemption station {Stage}: right after a wrong pad, not redeemed ({State.RedeemQueue.Length} still queued)")
                false
            else:
                set State.Redeemed += 1
                if (set State.Marks[Stage - 1] = FnmMarkRedeemed) {}
                Print("FNM: REDEEMED station {Stage} ({State.Redeemed} redeemed this run, {State.RedeemQueue.Length} still queued)")
                true

    # The damage of one hit: 1/BossHitsToKill of the boss's max health; the team's last hit whatever is left (gunfire may
    # have chipped it, a shield may have soaked some).
    BossDamage(Character:fort_character):float =
        if (BossHitsTaken >= BossHitsToKill) then Character.GetHealth() + Character.GetShield() + 100.0
        else Character.GetMaxHealth() / (Max(BossHitsToKill, 1) * 1.0)

    # The boss's health in percent (rounded up, so it reads 1% until it is down); 0 with no boss up.
    BossPercent():int =
        if (BossAlive?, Agent := BossAgent?, Character := Agent.GetFortCharacter[], Full := Character.GetMaxHealth(), Full > 0.0, P := Ceil[100.0 * Character.GetHealth() / Full]):
            Clamp(P, 0, 100)
        else:
            0

    # The race boss bar at the bottom of the screen (boss mode's, BOSS_MODE 15; it replaced the slate's BOSS text line on
    # 2026-10-11): "THE MAGMA TITAN   -   FINAL BOSS" over a bar filled to the boss's health with "60%   -   team hits 2/5"
    # on it, THE BOSS IS COMING ... while none is up, and DEFEATED! once the kill has finished the player's run.
    RaceBossBar(State:fnm_player_state):void =
        Who := if (RaceTitan.Found() > 0) then "THE MAGMA TITAN" else if (A := Arena?, A.Boss?) then "MEGABRUTE BOSS" else "BOSS"
        BarName := "{Who}   -   FINAL BOSS"
        if (State.Finished?):
            State.Hud.SetBossBar(BarName, 0, "DEFEATED!")
        else if (not BossAlive?):
            State.Hud.SetBossBar(BarName, 100, "THE BOSS IS COMING ...")
        else:
            Pct := BossPercent()
            State.Hud.SetBossBar(BarName, Pct, "{Pct}%   -   team hits {BossHitsTaken}/{BossHitsToKill}")

    # Who sees the race boss bar at Now: a race player at the arena stage, not picking, still fighting or finished by a
    # kill less than DefeatedSeconds ago.
    ShowsRaceBossBar(State:fnm_player_state, Now:float)<transacts>:logic =
        if (State.Mode = fnm_mode.Race, AtArena(State)?, not State.Picking?, (not State.Finished? or Now < BossDownAt + DefeatedSeconds)) then true else false

    # Every race boss bar now (a hit and the kill do not wait for BossLoop's next refresh).
    RefreshRaceBossBars(Now:float):void =
        for (State : PlayerStates, ShowsRaceBossBar(State, Now)?):
            RaceBossBar(State)
            set State.BossShown = true

    # A wrong pad: the adds spawner (two guards with pistols) comes on, or tops back up to two. A Reset() refills its spawn
    # limit, and its timer then replaces every add a player kills (Aaron, 2026-10-09: "spawned new guards and soldiers on
    # every death"; the 2026-10-08 log: twice an add went down and a new one came 1 s later, between wrong pads), so it
    # is reset only when fewer than two are up: every wrong pad brings the adds back to two, and a kill stays a kill.
    SummonAdds(A:fnm_arena):void =
        if (Adds := A.Adds?):
            var Up : int = 0
            for (Agent : Adds.GetAgents(), Character := Agent.GetFortCharacter[], Character.IsActive[]):
                set Up += 1
            if (AddsUp?, Up >= AddsCount):
                Print("FNM: adds already up ({Up})")
                return
            Adds.Reset()
            Adds.Enable()
            if (Up = 0):
                Adds.Spawn()
            set AddsUp = true
            Print("FNM: adds summoned ({Up} were up)")

    # Asks the Megabrute spawner for the boss with a pulse (BOSS_MODE 14: creature spawners refuse SpawnAt): Enable, and
    # OnBossSpawned switches it off again at once, so it never sends a second. The titan stomps in.
    SpawnBoss(A:fnm_arena):void =
        if (Boss := A.Boss?):
            set BossRequestedAt = GetSimulationElapsedTime()
            set BossHitsTaken = 0
            Boss.Enable()
            spawn{ RaceTitan.Arrive() }
            Print("FNM: boss requested")

    # The Megabrute is up (boss mode's OnBossSpawned): the pulse ends, it gets MegabossHealth that only the pads take away
    # (fnm_race_boss_damage heals every other hit), it is pinned on the platform and hidden inside the titan.
    OnBossSpawned(Agent:agent):void =
        if (A := Arena?, Boss := A.Boss?):
            Boss.Disable()
        if (BossAlive?):
            Print("FNM: a second race boss spawned while one is up (ignored)")
            return
        if (Character := Agent.GetFortCharacter[]):
            Character.SetMaxHealth(MegabossHealth)
            Character.SetHealth(MegabossHealth)
            Character.DamagedEvent().Subscribe(fnm_race_boss_damage{Director := Self}.OnDamaged)
            if (A := Arena?):
                FnmPinBoss(Character, A.BossHome)
            if (RaceTitan.Found() > 0):
                Character.Hide()
        set BossAgent = option{Agent}
        set BossAlive = true
        set BossRequestedAt = -1.0
        set BossHitsTaken = 0
        set LastHitter = false
        if (Character := Agent.GetFortCharacter[]):
            Print("FNM: boss spawned, health {Character.GetHealth()} of {Character.GetMaxHealth()}, shield {Character.GetShield()}, at {Character.GetTransform().Translation}")
        else:
            Print("FNM: boss spawned")

    # Gunfire on the boss (Aaron 2026-10-07 stood in the arena for a minute without touching a pad): tell the shooter once
    # every GunHintSeconds that bullets do nothing and the pads are the weapon (fnm_race_boss_damage calls it).
    RaceGunHint(Shooter:player):void =
        if (State := PlayerStates[Shooter], AtArena(State)?, not State.Finished?):
            Now := GetSimulationElapsedTime()
            Last := if (T := LastGunHint[Shooter]) then T else -100.0
            if (Now - Last >= GunHintSeconds):
                if (set LastGunHint[Shooter] = Now) {}
                Print("FNM: boss shot by a player; pad hint")
                spawn{ FlashNotice(State, "Bullets can't hurt it! Step on the pad with the RIGHT ANSWER") }

    OnBossEliminated(Result:device_ai_interaction_result):void =
        Print("FNM: boss elimination event")
        BossDown()

    # The kill: the gate opens and the run finishes (the clock stops) for every player at the arena stage; the last
    # hitter gets the feed; the adds go; the boss comes back BossRespawnSeconds later if anyone is (or arrives) there.
    BossDown():void =
        if (not BossAlive?):
            return
        set BossAlive = false
        set BossAgent = false
        set BossDownAt = GetSimulationElapsedTime()
        set BossHitsTaken = 0
        Print("FNM: boss eliminated")
        spawn{ RaceTitan.Fall() }
        if (Hitter := LastHitter?):
            Broadcast(FnmFeedFinalHit(Hitter), "landed the final hit!")
        set LastHitter = false
        if (A := Arena?):
            if (Adds := A.Adds?):
                Adds.Disable()
                set AddsUp = false
            if (Boss := A.Boss?):
                Boss.Disable()
            for (State : PlayerStates, AtArena(State)?, not State.Finished?, not State.Picking?):
                if (Gate := A.Gate?):
                    Gate.AddToIgnoreList(State.Player)
                    Print("FNM: gate open for the player")
                set State.BossDowned = true
                Analytics(BossAnalytics, State.Player, "boss kill")
                FinishRun(State, PodiumSeconds)
                Sound(State.Player, fnm_cue.BossDead)
                spawn{ SoundAfter(State.Player, fnm_cue.BossDown, BossDownVoiceDelaySeconds) }
                spawn{ PodiumLater(State) }
            RefreshRaceBossBars(BossDownAt)

    # Every BossRefreshSeconds: a boss for whoever is at the arena stage (BossRespawnSeconds after the last kill; a
    # spawn that has not come after 5 s is pulsed again, Disable then Enable, as boss mode does), the adds off once the
    # arena is empty, a backstop for a missed elimination event, the boss back on its platform after a knock, and every
    # race player's boss bar.
    BossLoop()<suspends>:void =
        loop:
            Sleep(BossRefreshSeconds)
            if (A := Arena?):
                Now := GetSimulationElapsedTime()
                var Fighters : int = 0
                for (State : PlayerStates, AtArena(State)?, not State.Finished?, not State.Picking?):
                    set Fighters += 1
                if (BossAlive?, BossHitsTaken >= BossHitsToKill):
                    Down := if (Agent := BossAgent?, Character := Agent.GetFortCharacter[], Character.IsActive[], Character.GetHealth() > 0.0) then false else true
                    if (Down?):
                        Print("FNM: boss down without an elimination event")
                        BossDown()
                if (Fighters > 0, not BossAlive?):
                    if (BossRequestedAt < 0.0, Now >= BossDownAt + BossRespawnSeconds):
                        SpawnBoss(A)
                    else if (BossRequestedAt >= 0.0, Now - BossRequestedAt > 5.0, Boss := A.Boss?):
                        Print("FNM: boss not spawned after 5 s; Disable, Enable")
                        set BossRequestedAt = Now
                        Boss.Disable()
                        Boss.Enable()
                if (BossAlive?, Now - RaceBossHitAt > LeashAfterHitSeconds, Home := A.BossHome?, Agent := BossAgent?, Character := Agent.GetFortCharacter[], Character.IsActive[]):
                    At := Character.GetTransform().Translation
                    if (Distance(vector3{X := At.X, Y := At.Y, Z := 0.0}, vector3{X := Home.Translation.X, Y := Home.Translation.Y, Z := 0.0}) > BossLeashCm):
                        Print("FNM: race boss wandered to {At}; back on the platform")
                        FnmPinBoss(Character, A.BossHome)
                if (Fighters = 0, AddsUp?, Adds := A.Adds?):
                    Adds.Disable()
                    set AddsUp = false
                # (Boss-mode players' boss bar is fnm_boss_mode BossLoop's.)
                for (State : PlayerStates, State.Mode = fnm_mode.Race):
                    if (ShowsRaceBossBar(State, Now)?):
                        RaceBossBar(State)
                        set State.BossShown = true
                    else if (State.BossShown?):
                        State.Hud.ClearBoss()
                        set State.BossShown = false

    # A pad's floating letter, forever (boss mode's, and the race finale's since 2026-10-11): turned toward the nearest
    # player of its arena (Race: race players at the arena stage; else boss-mode players), its readable face +Y at yaw 0
    # (build_bossmode LETTER_ASSET), bobbing round its home; still while nobody is there.
    FaceLetter(Letter:creative_prop, Home:vector3, K:int, Race:logic)<suspends>:void =
        var Yaw : float = 0.0
        var Phase : float = 0.25 * K
        loop:
            var Best : float = -1.0
            for (State : PlayerStates, LetterWatcher(State, Race)?, Character := State.Player.GetFortCharacter[]):
                At := Character.GetTransform().Translation
                D := (At.X - Home.X) * (At.X - Home.X) + (At.Y - Home.Y) * (At.Y - Home.Y)
                if (Best < 0.0 or D < Best):
                    set Best = D
                    set Yaw = ArcTan(At.Y - Home.Y, At.X - Home.X) * 180.0 / PiFloat - 90.0
            if (Best < 0.0):
                Sleep(0.5)
            else:
                set Phase += LetterTurnSeconds / Max(LetterBobSeconds, 0.5)
                Bob := LetterBobCm * Sin(2.0 * PiFloat * Phase)
                Letter.MoveTo(Home + vector3{X := 0.0, Y := 0.0, Z := Bob}, MakeRotationFromYawPitchRollDegrees(Yaw, 0.0, 0.0), LetterTurnSeconds)

    # Whose position a floating letter follows: race players at the arena stage (Race), else boss-mode players.
    LetterWatcher(State:fnm_player_state, Race:logic)<transacts>:logic =
        if (Race?, State.Mode = fnm_mode.Race, AtArena(State)?) then true
        else if (not Race?, State.Mode = fnm_mode.Boss) then true
        else false

    # ---------------------------------------------------------------- laser cannons (Aaron 2026-10-08)

    # The cannons' show for one hit: every muzzle fires its beams (a VFX burst with the beam sound), the strike effect
    # and a blast go off at the boss's feet (At: where it stood as the hit landed; a fort_character's position is its
    # capsule centre, ~77 cm up), and the boss is knocked back and stunned (KnockBoss). CannonFlashSeconds later the
    # effects are off again, the strike is back at its parked spot and the blast parks under the platform.
    # Rig: the race arena's (RaceRig) or boss mode's. Nuke (boss mode's MEGA NUKE): also the nuke VFX at the feet, a
    # second blast, and a white flash on the screen of every boss-mode player.
    FireCannons(Rig:fnm_cannon_rig, Shooter:player, Character:fort_character, At:vector3, Left:int, Nuke:logic)<suspends>:void =
        CannonFx := Rig.Fx
        StrikeFx := Rig.Strike
        StrikeHome := Rig.StrikeHome
        BlastRig := Rig.Blasts
        Feet := At + vector3{X := 0.0, Y := 0.0, Z := -77.0}
        Level := MakeRotationFromYawPitchRollDegrees(0.0, 0.0, 0.0)
        for (Fx : CannonFx):
            Fx.Enable()
            Fx.Restart()
        # Beams first: the strike and the blast land as the first shot reaches the boss.
        for (K -> Beam : Rig.Beams, Full := Rig.BeamFull[K]):
            spawn{ FireBeam(Beam, Full, if (K = 0) then true else false, Rig.RaceLaser) }
        if (Rig.Beams.Length > 0):
            Sleep(BeamTravelSeconds + (if (NiagaraLaser?) then FnmMuzzleCharge else 0.0))
        if (Fx := StrikeFx?, Fx.TeleportTo[Feet, Level]):
            Fx.Enable()
            Fx.Restart()
        Blast := BlastRig.NextIndex()
        if (Part := BlastRig.PartAt[Blast], Bomb := explosive_device[Part]):
            Bomb.Reset()
            if (Part.TeleportTo[Feet, Level]) {}
            Bomb.Explode(Shooter)
        Print("FNM: cannons fired ({CannonFx.Length} muzzle vfx, {Rig.Beams.Length} lasers, blast {Blast}) at {Feet}, {Left} hits to go")
        var Second : int = -1
        if (Nuke?):
            if (Fx := Rig.Nuke?, Fx.TeleportTo[Feet, Level]):
                Fx.Enable()
                Fx.Restart()
            set Second = BlastRig.NextIndex()
            if (Second <> Blast, Part := BlastRig.PartAt[Second], Bomb := explosive_device[Part]):
                Bomb.Reset()
                if (Part.TeleportTo[Feet, Level]) {}
                Bomb.Explode(Shooter)
            for (State : PlayerStates, State.Mode = fnm_mode.Boss, not State.Picking?):
                spawn{ State.Hud.Flash(0.5) }
            Print("FNM: mega nuke at {Feet} (nuke fx {FnmYesNo(if (Rig.Nuke?) then true else false)}, second blast {Second})")
        spawn{ KnockBoss(Character, Rig.PinnedBoss) }
        Sleep(CannonFlashSeconds)
        for (Fx : CannonFx):
            Fx.Disable()
        if (Fx := StrikeFx?):
            Fx.Disable()
            if (Home := StrikeHome?, Fx.TeleportTo[Home]) {}
        BlastRig.Park(Blast)
        if (Nuke?):
            if (Fx := Rig.Nuke?):
                Fx.Disable()
            if (Second <> Blast) then BlastRig.Park(Second)

    # Knocks the boss back along +Y (away from the entry) and up, then freezes it for a beat. An NPC may ignore the
    # impulse the way players do (uefn-mcp skill: "physics disabled"); if it moved under 30 cm it is staggered back
    # BossStaggerCm by teleport instead, so the hit always reads. Logged with how far it went.
    # Pinned (boss mode's Megabrute, held on its platform in stasis): let go for the knock, pinned again after the stun.
    KnockBoss(Character:fort_character, Pinned:logic)<suspends>:void =
        if (not Character.IsActive[]):
            return
        if (Pinned?):
            Character.ReleaseFromStasis()
        Before := Character.GetTransform().Translation
        Character.ApplyLinearImpulse(FnmImpulse(0.0, BossKnockImpulse, BossKnockImpulse * 0.5))
        Sleep(0.3)
        if (not Character.IsActive[]):
            return
        After := Character.GetTransform().Translation
        Moved := Distance(Before, After)
        if (Moved < 30.0):
            Facing := Character.GetTransform().Rotation
            Spot := After + vector3{X := 0.0, Y := BossStaggerCm, Z := 20.0}
            if (Character.TeleportTo[Spot, Facing]):
                Print("FNM: boss staggered back {BossStaggerCm} cm by teleport (the impulse moved it {Moved} cm)")
            else:
                Print("FNM: boss stagger teleport failed (the impulse moved it {Moved} cm)")
        else:
            Print("FNM: boss knocked {Moved} cm by the impulse")
        Character.PutInStasis(stasis_args{AllowTurning := false, AllowFalling := true, AllowEmotes := false})
        Sleep(BossStunSeconds)
        Character.ReleaseFromStasis()
        if (Pinned?, Character.IsActive[]):
            Character.PutInStasis(FnmBossPin())

    # One cannon's laser for a hit: BeamShots times the beam prop grows out of the muzzle to the boss (its placed, full
    # transform; tools/build_bossmode.py boss_rig), holds and goes dark. TeleportTo after the move in case MoveTo does not
    # carry the scale.
    # NiagaraLaser (BOSS_MODE 15f): each shot is the Niagara laser (fnm_fx.verse) along the beam prop's axis, and the
    # prop stays hidden; the first shot also sets off the impact at the far end (Impact: one beam of the pair does it).
    # Each shot starts with the muzzle discharge (BOSS_MODE 15g): it charges FnmMuzzleCharge s, then the laser leaves
    # with its flash; the shots keep their cadence. RaceLaser: the race finale's rig, whose shots are the shorter
    # NS_fnm_laser_race (its cannons are 5.1 m from the titan's waist, boss mode's 18.3 m; BOSS_MODE 16).
    FireBeam(Beam:creative_prop, Full:transform, Impact:logic, RaceLaser:logic)<suspends>:void =
        if (NiagaraLaser?):
            Dir := Full.Rotation.GetLocalUp()
            for (Shot := 1..BeamShots):
                FnmSpawnMuzzle(Full.Translation, Dir)
                Sleep(FnmMuzzleCharge)
                if (RaceLaser?) then FnmSpawnRaceLaser(Full.Translation, Dir) else FnmSpawnLaser(Full.Translation, Dir)
                if (Shot = 1, Impact?):
                    spawn{ LaserImpact(Full.Translation + Dir * (Full.Scale.Z * BeamPropHeight)) }
                Sleep(BeamTravelSeconds + BeamHoldSeconds + BeamGapSeconds - FnmMuzzleCharge)
            return
        Short := transform{Translation := Full.Translation, Rotation := Full.Rotation, Scale := vector3{X := Full.Scale.X, Y := Full.Scale.Y, Z := 0.02}}
        for (Shot := 1..BeamShots):
            if (Beam.TeleportTo[Short]) {}
            Beam.Show()
            Beam.MoveTo(Full, BeamTravelSeconds)
            if (Beam.TeleportTo[Full]) {}
            Sleep(BeamHoldSeconds)
            Beam.Hide()
            Sleep(BeamGapSeconds)

    LaserImpact(At:vector3)<suspends>:void =
        Sleep(BeamTravelSeconds)
        FnmSpawnImpact(At)

    # ---------------------------------------------------------------- pickup pads (Aaron 2026-10-08)

    # A player ran over pickup row Index (one hidden trigger per row of pads, tools/build_pickups.py): the item granter
    # for Kind hands them one through its hidden trigger, at most once per PickupRepeatSeconds per row and player. The
    # granter skips a player who already owns the item (the pad's own auto-pickup got there first) and drops it at
    # their feet when the inventory is full, where the pad's pickup swallowed it (Aaron: "the grenades disappear").
    OnPad(MaybeAgent:?agent, Index:int, Kind:string):void =
        if (Agent := MaybeAgent?, Player := player[Agent], State := PlayerStates[Player], not State.Picking?):
            Now := GetSimulationElapsedTime()
            Last := if (T := State.PadGrants[Index]) then T else -100.0
            if (Now - Last >= PickupRepeatSeconds, Trigger := GrantTriggers[Kind]):
                if (set State.PadGrants[Index] = Now) {}
                Trigger.Trigger(Player)
                Print("FNM: pickup {Kind} granted at pad {Index} (stage {State.Stage})")

    # DebugPickupTest: after the countdown, stand the player on two pad triggers of their own station, 2 s apart.
    DebugPickup(State:fnm_player_state)<suspends>:void =
        Sleep(5.0)
        var Dropped : int = 0
        for (Index -> Trigger : PadTriggers, Dropped < 2):
            Spot := Trigger.GetTransform().Translation + vector3{X := 0.0, Y := 0.0, Z := 60.0}
            Hall := HallwayAt(Spot)
            if (Hall = State.Stage - 1, Character := State.Player.GetFortCharacter[], Character.TeleportTo[Spot, MakeRotationFromYawPitchRollDegrees(ArrivalYaw, 0.0, 0.0)]):
                set Dropped += 1
                Print("FNM: debug pickup test: dropped on pad trigger {Index} at {Spot}")
                Sleep(2.0)
        Print("FNM: debug pickup test done ({Dropped} drops)")

    # The item kind a tagged pad trigger or grant trigger carries (fnm_item_* tags).
    ItemKind(Object:creative_object_interface)<transacts>:string =
        if (Object.GetTags().Has[fnm_item_boogie{}]) then "boogie"
        else if (Object.GetTags().Has[fnm_item_shockwave{}]) then "shockwave"
        else if (Object.GetTags().Has[fnm_item_splash{}]) then "splash"
        else "unknown"

    # ---------------------------------------------------------------- live race layer (G6)

    # The run's pace target (per skill, like times; PROTOCOL 6b): the session island record's splits when they cover
    # the course, else the player's own saved best run's, else none. The target line under the clock says which:
    # "Record 1:23.4" or "Beat 1:23.4" (the personal best).
    ChoosePace(State:fnm_player_state):void =
        set State.PaceTarget = array{}
        var Line : string = if (State.BestTime >= 0.0) then "Beat {FnmClock(State.BestTime)}" else ""
        if (Top := BoardFor(State.CartridgeIndex)[0], Top.Splits.Length = Stations.Length):
            set State.PaceTarget = Top.Splits
            set Line = "Today's record {FnmClock(Top.Time)}"
        else if (Saved := FnmSavedSplits[State.Player, State.Cartridge.Id], Saved.Length = Stations.Length):
            set State.PaceTarget = Saved
        State.Hud.SetTarget(Line)

    # A right answer at the player's current stage: its race-clock split, and against the pace target the delta under
    # the target line (green ahead, red behind). Returns the delta ("−1.8 s"; "" with no pace target) for the recap card.
    RecordSplit(State:fnm_player_state):string =
        var Copy : string = ""
        if (State.StartTime >= 0.0):
            Stage := State.Stage
            Elapsed := RunClock(State, GetSimulationElapsedTime())
            set State.Splits += array{Elapsed}
            if (Target := State.PaceTarget[Stage - 1]):
                Delta := Elapsed - Target
                set Copy = DeltaCopy(Delta)
                State.Hud.SetDelta(Copy, if (Delta < 0.0) then NamedColors.LightGreen else NamedColors.Tomato)
                Print("FNM: split stage {Stage} at {FnmClock(Elapsed)} delta {Copy}")
            else:
                Print("FNM: split stage {Stage} at {FnmClock(Elapsed)} delta none")
        Copy

    # "−1.8 s" (ahead: a real minus sign, as in the cartridges' charset) or "+3.2 s" (behind), one decimal.
    DeltaCopy(Seconds:float)<transacts>:string =
        Tenths := if (T := Round[Abs(Seconds) * 10.0]) then T else 0
        Whole := FnmDiv(Tenths, 10)
        Sign := if (Seconds < 0.0) then "−" else "+"
        "{Sign}{Whole}.{Tenths - Whole * 10} s"

    # A public feed line to EVERY player's HUD (fnm_hud PushFeed), logged without the name (a log cannot show one).
    Broadcast(Line:message, LogLine:string):void =
        Print("FNM: feed {LogLine}")
        for (State : PlayerStates):
            State.Hud.PushFeed(Line)

    # A wrong door's (or pad's) feed line (G9, ux_critique #6): on the victim's own HUD only, since a feed that named every
    # miss to the whole class was a public failure log; except the race leader's misses, which stay public (drama about
    # the one in front, naming nobody who is behind). The leader is the strip's first row when that is a racer
    # (RaceLeaderNow, UpdateRace).
    # Named: the line for every HUD ("<name> got frozen at station 3"); Own: the victim's own line ("You got frozen at
    # station 3": their own HUD used to show their own name, round-2 audit).
    MissFeed(State:fnm_player_state, Named:message, Own:string, LogLine:string):void =
        if (Leader := RaceLeaderNow?, Leader = State.Player):
            Print("FNM: feed (public: the leader's miss)")
            Broadcast(Named, LogLine)
        else:
            Print("FNM: feed (own HUD only) {Own}")
            State.Hud.PushFeed(FnmText(Own))

    # One loop for the rivals strip: every RaceSeconds the order is computed once and written to every player's HUD.
    RaceLoop()<suspends>:void =
        loop:
            UpdateRace()
            Sleep(RaceSeconds)

    UpdateRace():void =
        Now := GetSimulationElapsedTime()
        Entries := SortRace(for (Each : GetPlayspace().GetPlayers()) { RaceEntry(Each, Now) })
        var Summary : string = ""
        for (K -> Entry : Entries):
            Separator := if (K > 0) then ", " else ""
            set Summary += "{Separator}{K + 1}) {Entry.Tail}"
        if (Summary <> LastRaceLog):
            set LastRaceLog = Summary
            Print("FNM: RACE {Summary}")
        # The leader (MissFeed): the first row, if that player is racing and someone else is too (a lone racer leads nobody).
        var Racers : int = 0
        for (Entry : Entries, Racing(Entry.Who)?):
            set Racers += 1
        set RaceLeaderNow = if (Racers >= 2, First := Entries[0], Racing(First.Who)?) then option{First.Who} else false
        for (State : PlayerStates):
            if (State.Picking?):
                State.Hud.SetRivals(array{}, -1)
            else:
                Shown := RaceRowsFor(Entries, State.Player)
                State.Hud.SetRivals(Shown(0), Shown(1))

    # Finished players first (fastest first), then racers by station, furthest first (ties: less time on the clock
    # first), then players picking a skill, then players with no state yet (lobby).
    RaceEntry(Who:player, Now:float):fnm_race_entry =
        if (State := PlayerStates[Who]):
            if (State.Picking?):
                return fnm_race_entry{Who := Who, Score := 4000000.0, Tail := "picking"}
            if (State.Finished?, State.LastTime >= 0.0):
                return fnm_race_entry{Who := Who, Score := State.LastTime, Tail := "FIN {FnmClock(State.LastTime)}"}
            # Boss battle mode: after the finishers, before the racers, higher levels first.
            if (State.Mode = fnm_mode.Boss):
                return fnm_race_entry{Who := Who, Score := 900000.0 + (10 - State.Level) * 1000.0, Tail := "BOSS L{State.Level}"}
            Elapsed := if (State.StartTime >= 0.0) then RunClock(State, Now) else 0.0
            # The arena (stage Stations.Length + 1) ranks ahead of station 10 and reads BOSS (it said "station 10").
            Stage := Max(1, Min(State.Stage, Stations.Length + 1))
            # G10: a racer holding a SHIELD shows it on the strip.
            Where := if (AtArena(State)?) then "BOSS" else "station {Min(Stage, Stations.Length)}"
            Tail := if (State.Shield?) then "{Where}  +SHIELD" else Where
            return fnm_race_entry{Who := Who, Score := 1000000.0 + (Stations.Length + 1 - Stage) * 100000.0 + Min(Elapsed, 99999.0), Tail := Tail}
        fnm_race_entry{Who := Who, Score := 5000000.0, Tail := "lobby"}

    # True for a player racing right now: a race-mode run past its pick, not finished.
    Racing(Who:player)<transacts>:logic =
        if (State := PlayerStates[Who], State.Mode = fnm_mode.Race, not State.Picking?, not State.Finished?, State.StartTime >= 0.0) then true else false

    # Lowest Score first (insertion sort; a handful of players).
    SortRace(Entries:[]fnm_race_entry):[]fnm_race_entry =
        var Sorted : []fnm_race_entry = array{}
        for (Entry : Entries):
            var Next : []fnm_race_entry = array{}
            var Placed : logic = false
            for (Other : Sorted):
                if (not Placed?, Entry.Score < Other.Score):
                    set Next += array{Entry}
                    set Placed = true
                set Next += array{Other}
            if (not Placed?):
                set Next += array{Entry}
            set Sorted = Next
        Sorted

    # Viewer's strip (G9, ux_critique #6): the top StripTop, the one rival just ahead of the viewer, and the viewer, in
    # race order; never the full ranking, so nobody sees who is last (unless it is themselves, or a top-3 row with three
    # players). The closest rival is the number that drives a racer. The viewer's row reads YOU; returns the rows and the
    # viewer's row index.
    RaceRowsFor(Entries:[]fnm_race_entry, Viewer:player):tuple([]message, int) =
        var ViewerAt : int = -1
        for (K -> Entry : Entries, Entry.Who = Viewer):
            set ViewerAt = K
        Picked := for (K -> Entry : Entries, (K < StripTop or K = ViewerAt or K = ViewerAt - 1)) { Entry }
        var OwnRow : int = -1
        var Rows : []message = array{}
        for (K -> Entry : Picked):
            if (Entry.Who = Viewer):
                set OwnRow = K
                set Rows += array{FnmText("YOU  {Entry.Tail}")}
            else:
                set Rows += array{FnmRivalRow(Entry.Who, Entry.Tail)}
        (Rows, OwnRow)

    # ---------------------------------------------------------------- sound (fnm_audio.verse)

    # Plays Cue for Player only (logged; a no-op for a cue with no audio player).
    Sound(Player:player, Cue:fnm_cue):void =
        if (A := Audio?):
            A.Play(Player, Cue)

    # Cue a moment after an answer (boost, streak); dropped once the player has finished, so the last door's boost and
    # streak cues do not land on the finish fanfare.
    SoundLater(Player:player, Cue:fnm_cue, Seconds:float)<suspends>:void =
        Sleep(Seconds)
        if (State := PlayerStates[Player], not State.Finished?):
            Sound(Player, Cue)

    # Volt's reaction card on Player's HUD a moment later (a penalty landing: with its voice line). Pure UI: nothing here touches
    # the run. Dropped once the player has finished or is picking (the finish board and the picker have the screen).
    VoltLater(Player:player, Kind:fnm_volt, Seconds:float)<suspends>:void =
        Sleep(Seconds)
        if (State := PlayerStates[Player], not State.Finished?, not State.Picking?):
            State.Hud.ShowVolt(Kind)

    # Cue a moment later whether or not the player has finished (BOSS DOWN lands after FinishPlayer).
    SoundAfter(Player:player, Cue:fnm_cue, Seconds:float)<suspends>:void =
        Sleep(Seconds)
        if (Player.IsActive[]):
            Sound(Player, Cue)

    # The music bed for Player: tier Tier's loop (0 = silence; also while the picker is up and after the finish).
    SetMusic(Player:player, Tier:int):void =
        if (A := Audio?):
            A.SetMusic(Player, Tier)

    # The bed for the tier of the player's current station; the boss bed in the race's boss arena and in boss mode (G9 D2,
    # music_boss: boss mode played the tier beds by level until then).
    Music(State:fnm_player_state):void =
        if (not State.Finished?, not State.Picking?):
            if (State.Mode = fnm_mode.Boss or AtArena(State)?) then SetMusic(State.Player, FnmBedBoss) else SetMusic(State.Player, StationTier(State, State.Stage))

    # The finish sounds, Delay seconds after the finish (FinishRun): the fanfare, then FinishVoiceSeconds later (its loud body
    # played out; G9 D2, the 5.5 s Mint fanfare) today's record or else a new personal best, the medal, and PERFECT when
    # every answer was right first try, FinishCueGapSeconds apart. A new run or a skill change meanwhile (RunGeneration)
    # silences what is left.
    FinishSounds(State:fnm_player_state, Delay:float, NewBest:logic, Record:logic, Medal:string, Perfect:logic)<suspends>:void =
        Generation := State.RunGeneration
        Player := State.Player
        if (Delay > 0.0):
            Sleep(Delay)
        if (not FinishLive(State, Generation)?) then return
        Sound(Player, fnm_cue.Finish)
        Sleep(FinishVoiceSeconds)
        if (not FinishLive(State, Generation)?) then return
        if (Record?):
            Sound(Player, fnm_cue.NewRecord)
            Sleep(FinishCueGapSeconds)
        else if (NewBest?):
            Sound(Player, fnm_cue.NewBest)
            Sleep(FinishCueGapSeconds)
        if (not FinishLive(State, Generation)?) then return
        Sound(Player, if (Medal = "GOLD") then fnm_cue.MedalGold else if (Medal = "SILVER") then fnm_cue.MedalSilver else fnm_cue.MedalBronze)
        if (Perfect?):
            Sleep(FinishCueGapSeconds)
            if (FinishLive(State, Generation)?) then Sound(Player, fnm_cue.Perfect)

    # Still the finished run FinishSounds began for: present, finished, no new run or pick since.
    FinishLive(State:fnm_player_state, Generation:int)<transacts>:logic =
        if (PlayerStates[State.Player], State.Finished?, State.RunGeneration = Generation, not State.Picking?) then true else false

    # A penalty's voice line PenaltyVoiceDelaySeconds after Punish's moment for it (as SoundLater; the yeet's comes 0.5 s
    # later than the others, after the pull-out). In an arena (the race's boss arena, Boss Battle mode) the crowd's aww
    # follows CrowdAfterVoiceSeconds after the line, and in boss mode the boss's taunt (its voice and the titan's scream,
    # fnm_boss_mode.Taunt) TauntAfterCrowdSeconds after the aww (G9 D2): timed from the voice, each 0.9 s from the last, so no
    # two start together and at most two start in any second (console/AUDIO.md mix rules). A race station stays as it was.
    PenaltyLines(Player:player, Voice:fnm_cue)<suspends>:void =
        SoundLater(Player, Voice, PenaltyVoiceDelaySeconds)
        if (State := PlayerStates[Player], (State.Mode = fnm_mode.Boss or AtArena(State)?)):
            Sleep(CrowdAfterVoiceSeconds)
            if (PlayerStates[Player], not State.Finished?):
                Sound(Player, fnm_cue.CrowdAww)
                if (State.Mode = fnm_mode.Boss, BM := BossMode?):
                    Sleep(TauntAfterCrowdSeconds)
                    if (PlayerStates[Player], not State.Finished?, State.Mode = fnm_mode.Boss):
                        BM.Taunt(State)

    # Shows a short orange notice that clears itself after NoticeSeconds.
    FlashNotice(State:fnm_player_state, Message:string)<suspends>:void =
        Generation := State.Hud.ShowFeedback(Message, NamedColors.Orange)
        Sleep(NoticeSeconds)
        State.Hud.ClearFeedbackIf(Generation)
