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
# (-1), DebugAutoRightAnswers (false), DebugVictoryTest (false), DebugStartStage (0), DebugIgnoreTriggerEvents (false), DebugAutoRightOffsetY (0.0).
# Doors: every showing of a question shuffles its choices (State.Order), so the right door moves; a position
# backstop (WatchDoors) answers for a player who stands anywhere in a door's vestibule when no trigger event was taken.
# Wrong door  -> big red X, that choice's Feedback, a random penalty from Penalties, same question.
# Right door  -> big green check, next question, and the way on opens at once (no stall): that door's
#                barrier lets them through, or a teleport to NextTeleporter. The Explanation stays on the
#                HUD for CorrectFeedbackSeconds while the player moves on.
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

using { /Fortnite.com/Characters }
using { /Fortnite.com/Devices }
using { /UnrealEngine.com/Temporary/SpatialMath }
using { /Verse.org/Colors }
using { /Verse.org/Random }
using { /Verse.org/Simulation }
using { /Verse.org/Simulation/Tags }

# One finisher's best time this session, for the finish board.
fnm_result := class:
    Who : player
    Time : float

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
    var ZoneDoor : int = -1
    var ZoneSince : float = 0.0
    var ZoneFired : logic = false
    var Finished : logic = false
    # True while the fnm_ice_floor settings are on this player (SetIce).
    var OnIce : logic = false
    # Right-first-try answers in a row (a wrong door resets it).
    var Streak : int = 0
    var BestStreak : int = 0
    # Race clock: simulation time the run's GO! showed; -1 = not running yet.
    var StartTime : float = -1.0
    # Bumped per run and per boost, so an older clock or boost loop stops itself.
    var RunGeneration : int = 0
    var BoostGeneration : int = 0
    # Best finishing time this session for the current skill (-1 = none yet), and the same per skill, keyed by the
    # cartridge's index in the slot (switching back to a skill brings that skill's best back; PROTOCOL 6b: times
    # across skills are never compared). Runs = runs finished, any skill.
    var BestTime : float = -1.0
    var BestTimes : [int]float = map{}
    var Runs : int = 0

# Binds one door to its station/door index, so a single callback signature can serve every door.
fnm_door_handler := class:
    Director : fnm_director
    StationIndex : int
    DoorIndex : int

    OnTriggered(MaybeAgent:?agent):void =
        if (not Director.DebugIgnoreTriggerEvents?):
            Director.OnDoor(MaybeAgent, StationIndex, DoorIndex)

fnm_director := class(creative_device, fnm_picker_listener):
    # Optional difficulty position per station in percent (0 easiest .. 100 hardest); -1 or a missing
    # entry = automatic, spread evenly from first station to last (PROTOCOL 6).
    @editable
    DifficultyOverrides : []int = array{}

    # Seconds the wrong-answer feedback stays on the HUD (the player is teleported back immediately).
    @editable
    WrongFeedbackSeconds : float = 4.0

    # Seconds the explanation of a right answer stays on the HUD (the player moves on immediately).
    @editable
    CorrectFeedbackSeconds : float = 4.0

    # Wrong-door penalties come from the map profile (map.json "penalties" -> FnmMapPenalties), one at random
    # per wrong answer. Each penalty's visual is a rig (fnm_rig.verse) or effect device placed by
    # tools/build_rigs.py.
    var Penalties : []fnm_penalty = array{}
    @editable
    FreezeSeconds : float = 5.0
    # Mud: slowed (the fnm_mud movement modulator) with a brown screen for MudSeconds. The modulator's own
    # Duration is 3 s and can't be set from MCP, so it is re-applied every MudReapplySeconds.
    @editable
    MudSeconds : float = 8.0
    @editable
    MudReapplySeconds : float = 2.5
    # Dizzy: back at the entry, the view spins about DizzySpinDegreesPerSecond for DizzySpinSeconds, rounded to whole
    # turns so it ends facing the doors (the character is re-teleported in place, yaw advanced, every
    # DizzySpinStepSeconds, under stasis), then a radial blur
    # pulses in and out (DizzyPulseSeconds each way) for DizzySeconds. Aaron 2026-10-04: the old colour swirl
    # (PP_Crazy) was confusing, not dizzying.
    @editable
    DizzySeconds : float = 6.0
    @editable
    DizzyPulseSeconds : float = 0.7
    @editable
    DizzySpinSeconds : float = 1.5
    @editable
    DizzySpinDegreesPerSecond : float = 360.0
    @editable
    DizzySpinStepSeconds : float = 0.05
    # Blackout: the screen goes dark and the player is held this long, then wakes up at the station entry.
    @editable
    BlackoutSeconds : float = 3.0
    # Yeet: an air vent (fnm_yeet rig) appears under the player at world yaw YeetYaw, tilted YeetPitch so its
    # gust throws them back down their hallway. It stays YeetSeconds; they get YeetAirSeconds to land.
    # (Player physics is off in UEFN, so SetLinearVelocity does nothing; per-tick TeleportTo was choppy.)
    @editable
    YeetYaw : float = 90.0
    @editable
    YeetPitch : float = 50.0
    @editable
    YeetSeconds : float = 0.4
    @editable
    YeetAirSeconds : float = 6.0
    # Yeet first pulls the player out of the narrow vestibule to this far (cm) in front of the door wall,
    # mid-hallway, so the throw back doesn't hit the door wall. Freeze and Spike happen where the player
    # stands (Aaron: no position change) and use the wide camera instead.
    @editable
    PenaltyStandOff : float = 500.0
    # Spike: SpearCount spears wait SpearDepth (cm) under the floor in a ring of radius SpearRing around
    # the player, burst up SpearRise in SpearSeconds and pin them (stasis) for SpikeWatchSeconds under the
    # wide camera; then SpikeDamage eliminates them (more than full health + shield). The ring stays up
    # SpikeHoldSeconds after that. (The orbit camera as elimination camera jumped to a random wall, so the death
    # view is Fortnite's own.) Aaron 2026-10-04: the death lagged the spears (1.2 s watch), so it is near-instant.
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
    SpikeWatchSeconds : float = 0.05
    @editable
    SpikeHoldSeconds : float = 1.0
    @editable
    SpikeDamage : float = 1000.0
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
    # Test hook: drop every door trigger event, so only the position backstop (WatchDoors) answers doors. Pair with
    # DebugAutoRightAnswers to prove the backstop carries a whole run. false = ship value.
    @editable
    DebugIgnoreTriggerEvents : logic = false

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
    var GuardsSpawned : int = 0
    # Victory area (tools/build_finish.py): podium buttons and the all-time screen's billboards (rows top to bottom).
    var NewRaceButtons : []button_device = array{}
    var ChangeSkillButtons : []button_device = array{}
    var HallHeads : []billboard_device = array{}
    var HallRows : []billboard_device = array{}
    # The screen holds a just-finished skill until this simulation time before cycling on.
    var HallHoldUntil : float = 0.0

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
        set Stations = BuildStations()
        set Penalties = FnmMapPenalties()
        set IceRig = BuildRig("ice", fnm_ice)
        set SpikeRig = BuildRig("spike", fnm_spike)
        set YeetRig = BuildRig("yeet", fnm_yeet)
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
            set Ready = true
            StationTags := FnmStationTags()
            set GuardSpawners = for (K -> Station : Stations):
                if (StationTag := StationTags[K]) then FindGuards(StationTag) else false
            set GuardsUp = for (Spawner : GuardSpawners) { false }
            for (MaybeSpawner : GuardSpawners, Spawner := MaybeSpawner?):
                Spawner.Disable()
                Spawner.SpawnedEvent.Subscribe(OnGuardSpawned)
                Spawner.EliminatedEvent.Subscribe(OnGuardEliminated)
            Print("FNM: {CountGuardStations()} stations have guards")
            spawn{ GuardLoop() }
            spawn{ DoorWatch() }
            SetUpVictoryArea()
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
            else if (FinishPoint := Finish?):
                set Next = FinishPoint
            var OverridePercent : int = -1
            if (Value := DifficultyOverrides[K]):
                set OverridePercent = Value
            Print("FNM: station {K + 1}: {StationDoors.Length} doors, {CountPassages(StationPassages)} passages")
            fnm_station{Doors := StationDoors, Passages := StationPassages, RetryTeleporter := Entry, NextTeleporter := Next, DifficultyOverride := OverridePercent}

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

    # True while any player still racing is on stage Index + 1 (in that station's hallway).
    StationOccupied(Index:int):logic =
        var Found : logic = false
        # A player choosing a skill is held still at station 1: no guards for them.
        for (State : PlayerStates, not State.Finished?, not State.Picking?, State.Stage = Index + 1):
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
        Stage := Min(State.Stage, Stations.Length)
        if (Station := Stations[Stage - 1]):
            SendTo(State.Player, Station.RetryTeleporter)
        GiveLoadout(State.Player)
        Print("FNM: respawned at stage {Stage}")
        if (State.Picking?):
            HoldStill(State)
        if (not State.Busy?, not State.Finished?):
            spawn{ FlashNotice(State, "Eliminated! Back to the start of station {Stage}.") }

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
            set State.Finished = true
        for (Station : Stations, MaybePassage : Station.Passages, Passage := MaybePassage?):
            Passage.RemoveFromIgnoreList(Departed)
        if (Device := IceFloor?):
            Device.RemoveFrom(Departed)
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
            Hud.SetTitle("Fortnite Math", "Choose your skill")
            Hud.ClearQuestion()
            Hud.SetClock(FnmClock(0.0))
            State := fnm_player_state{Player := Joined, Hud := Hud}
            if (set PlayerStates[Joined] = State) {}
            # Start everyone at station 1 facing the doors, whatever spawn pad the island used.
            if (First := Stations[0]):
                SendTo(Joined, First.RetryTeleporter)
            HoldStill(State)
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

    # Picks for the player at once (DebugAutoPick, or a slot with one cartridge), else shows the picker: the grade
    # step, or straight to the skill step when there is only one grade.
    BeginPicking(State:fnm_player_state):void =
        set State.Picking = true
        if (DebugAutoPick >= 0, Cartridges[DebugAutoPick]):
            Pick(State, DebugAutoPick)
        else if (Cartridges.Length = 1):
            Pick(State, 0)
        else:
            if (DebugAutoPick >= 0):
                Print("FNM: DebugAutoPick {DebugAutoPick} is out of range ({Cartridges.Length} cartridges); showing the picker")
            Grades := GradeList()
            if (Grades.Length = 1, Only := Grades[0]):
                ShowSkills(State, Only, false)
            else:
                State.Hud.ShowGradeStep(Grades)
            Print("FNM: picker shown: {Grades.Length} grades, {Cartridges.Length} skills")

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
            else if (State.Picking?):
                if (Kind = fnm_pick.Grade):
                    Grades := GradeList()
                    if (Grade := Grades[Index]):
                        Print("FNM: grade {Grade} chosen")
                        ShowSkills(State, Grade, if (Grades.Length > 1) then true else false)
                else if (Kind = fnm_pick.Skill):
                    Pick(State, Index)
                else:
                    Print("FNM: picker back")
                    State.Hud.ShowGradeStep(GradeList())

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
            if (State.Picks = 1, DebugStartStage > 1, Start := Stations[DebugStartStage - 1]):
                set State.Stage = DebugStartStage
                DrawItem(State)
                ShowCurrent(State)
                SendTo(State.Player, Start.RetryTeleporter)
                Print("FNM: debug start at stage {DebugStartStage}")
            GiveLoadout(State.Player)
            # The countdown holds them again; release the picker's hold first so the two never stack.
            if (Character := State.Player.GetFortCharacter[]):
                Character.ReleaseFromStasis()
            spawn{ Countdown(State) }
            if (State.Picks = 1):
                if (DebugAutoWrongAnswers > 0):
                    spawn{ DebugAutoWrong(State) }
                if (DebugPassageTest?):
                    spawn{ DebugPassage(State) }
                if (DebugDoorTest >= 0):
                    spawn{ DebugDoor(State) }
                if (DebugAutoRightAnswers?):
                    spawn{ DebugAutoRight(State) }

    # CHANGE SKILL (finish board or podium): cancels any pending restart and resets the run; then the picker again,
    # from station 1. Best times stay with their skill (BestTimes; Pick restores the chosen skill's).
    ChangeSkill(State:fnm_player_state):void =
        set State.RunGeneration += 1
        State.Hud.HideFinishButtons()
        State.Hud.HideResults()
        for (Station : Stations, MaybePassage : Station.Passages, Passage := MaybePassage?):
            Passage.RemoveFromIgnoreList(State.Player)
        set State.Stage = 1
        set State.FirstTryCorrect = 0
        set State.Streak = 0
        set State.BestStreak = 0
        set State.Finished = false
        set State.Busy = false
        set State.CurrentItem = -1
        State.Hud.SetCountdown("")
        State.Hud.SetTarget("")
        State.Hud.SetStreak("")
        State.Hud.ClearVerdictNow()
        State.Hud.SetTitle("Fortnite Math", "Choose your skill")
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
        var OverridePercent : int = -1
        if (Station := Stations[Stage - 1]):
            set OverridePercent = Station.DifficultyOverride
        FnmTierForStage(Stage, Stations.Length, State.TierCount, OverridePercent)

    # Draws the player's next item for their current stage (without replacement, per player).
    DrawItem(State:fnm_player_state):void =
        Tier := StationTier(State, State.Stage)
        if (Pool := State.TierPools[Tier - 1], Deck := State.Decks[Tier - 1]):
            Draw := FnmDraw(Deck, Pool)
            if (set State.Decks[Tier - 1] = Draw.Rest) {}
            set State.CurrentItem = Draw.ItemIndex
            set State.MissedCurrent = false
            if (Item := State.Cartridge.Items[Draw.ItemIndex]):
                set State.Order = Shuffle(for (Index := 0..Item.Choices.Length - 1) { Index })

    ShowCurrent(State:fnm_player_state):void =
        if (Item := State.Cartridge.Items[State.CurrentItem]):
            StageCount := Stations.Length
            TierName := FnmTierName(State.Cartridge.Tiers, Item.Tier)
            StageLine := "Stage {State.Stage}/{StageCount}  -  {TierName}"
            Shown := for (Choice : State.Order, Text := Item.Choices[Choice]) { Text }
            State.Hud.ShowQuestion(StageLine, Item.Prompt, FnmChoicesLine(Shown))

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
            if (not State.Finished?, not State.Busy?, not State.Picking?):
                if (StationIndex = State.Stage - 1):
                    set State.Busy = true
                    set State.LastAccept = GetSimulationElapsedTime()
                    spawn{ HandleDoor(State, StationIndex, DoorIndex) }
                else if (StationIndex > State.Stage - 1):
                    spawn{ FlashNotice(State, "This is not your station. You are on stage {State.Stage}.") }
                # An earlier station: they are walking back through a door they already passed. Ignore.

    HandleDoor(State:fnm_player_state, StationIndex:int, DoorIndex:int)<suspends>:void =
        if (Item := State.Cartridge.Items[State.CurrentItem], Station := Stations[StationIndex]):
            Choice := ChoiceAt(State, DoorIndex)
            if (Choice < 0):
                set State.Busy = false
                Letter := FnmChoiceLetter(DoorIndex)
                FlashNotice(State, "No choice {Letter} here")
            else if (Choice = Item.Answer):
                var Label : string = ""
                if (not State.MissedCurrent?):
                    set State.FirstTryCorrect += 1
                    set State.Streak += 1
                    set State.BestStreak = Max(State.BestStreak, State.Streak)
                    if (State.Streak >= 2) then set Label = "{State.Streak} IN A ROW!"
                    spawn{ Boost(State, Min(MaxBoostSeconds, BoostSeconds + StreakBonusSeconds * (State.Streak - 1) * 1.0)) }
                State.Hud.FlashVerdict(true, Label)
                AdvancePlayer(State, Station, DoorIndex)
                set State.Busy = false
                if (not State.Finished?):
                    Generation := State.Hud.ShowFeedback("Correct!  " + Item.Explanation, NamedColors.LightGreen)
                    Sleep(CorrectFeedbackSeconds)
                    State.Hud.ClearFeedbackIf(Generation)
            else:
                set State.MissedCurrent = true
                set State.Streak = 0
                StopBoost(State)
                Kind := PickPenalty()
                State.Hud.FlashVerdict(false, FnmPenaltyLabel(Kind))
                Generation := State.Hud.ShowFeedback(FeedbackFor(Item, Choice), NamedColors.Tomato)
                Punish(State.Player, Station, DoorIndex, Kind)
                set State.Busy = false
                Sleep(WrongFeedbackSeconds)
                State.Hud.ClearFeedbackIf(Generation)
        else:
            set State.Busy = false

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

    WatchDoors(State:fnm_player_state):void =
        Now := GetSimulationElapsedTime()
        var Inside : int = -1
        if (not State.Finished?, not State.Picking?, State.CurrentItem >= 0, Station := Stations[State.Stage - 1], Character := State.Player.GetFortCharacter[], Character.IsActive[]):
            Here := Character.GetTransform().Translation
            for (Index -> Door : Station.Doors):
                Zone := Door.GetTransform()
                # A trigger's box is 600 x 600 cm at scale 1, centred on the device, its front face at the door wall's
                # back face (tools/build_course.py). The zone watched here is the WHOLE vestibule, on to the barrier:
                # a player who runs or jumps through the door can stop against the barrier, past the trigger box
                # (2026-10-06, Aaron: a right door did nothing until he moved around the room; the triggers were
                # 60% of the vestibule then and this check mirrored them).
                Front := Zone.Translation.Y - 300.0 * Zone.Scale.Y
                var Back : float = Zone.Translation.Y + 300.0 * Zone.Scale.Y
                if (MaybePassage := Station.Passages[Index], Passage := MaybePassage?):
                    set Back = Max(Back, Passage.GetTransform().Translation.Y)
                if (Abs(Here.X - Zone.Translation.X) <= 300.0 * Zone.Scale.X, Here.Y >= Front, Here.Y <= Back, Abs(Here.Z - Zone.Translation.Z) <= 300.0):
                    set Inside = Index
        if (Inside <> State.ZoneDoor):
            set State.ZoneDoor = Inside
            set State.ZoneSince = Now
            set State.ZoneFired = false
        else if (Inside >= 0, not State.ZoneFired?, not State.Busy?, Now - State.ZoneSince >= DoorDwellSeconds, State.LastAccept < State.ZoneSince - 1.0):
            set State.ZoneFired = true
            Print("FNM: door {FnmChoiceLetter(Inside)} answered by position at stage {State.Stage} (no trigger event taken)")
            OnDoor(option{State.Player}, State.Stage - 1, Inside)

    # Correct answer through door DoorIndex at Station: next stage (or finish), then the way on opens:
    # that door's barrier lets this player (only) through, or they are teleported to the next entry.
    # The barrier stays open for them; walking back through it later is harmless.
    AdvancePlayer(State:fnm_player_state, Station:fnm_station, DoorIndex:int):void =
        set State.Stage += 1
        if (State.Stage > Stations.Length):
            FinishPlayer(State)
        else:
            DrawItem(State)
            ShowCurrent(State)
        if (MaybePassage := Station.Passages[DoorIndex], Passage := MaybePassage?):
            Passage.AddToIgnoreList(State.Player)
            Print("FNM: passage {FnmChoiceLetter(DoorIndex)} open for the player")
        else:
            SendTo(State.Player, Station.NextTeleporter)

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
                if (Station := Stations[State.Stage - 1], Door := Station.Doors[Wrong], Character := State.Player.GetFortCharacter[]):
                    if (Character.TeleportTo[Door.GetTransform().Translation, MakeRotationFromYawPitchRollDegrees(ArrivalYaw, 0.0, 0.0)]) {}
                    Sleep(1.0)
                HandleDoor(State, State.Stage - 1, Wrong)

    DebugAutoRight(State:fnm_player_state)<suspends>:void =
        Sleep(8.0)
        var Finishes : int = 0
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
            Answer := AnswerDoor(State)
            if (State.CurrentItem >= 0, Station := Stations[State.Stage - 1], Door := Station.Doors[Answer], Character := State.Player.GetFortCharacter[]):
                Stage := State.Stage
                # (The teleport answers at once, so name the door before it: afterwards the next item is up.)
                Print("FNM: debug auto-right stage {Stage} door {FnmChoiceLetter(Answer)}")
                Spot := Door.GetTransform().Translation + vector3{X := 0.0, Y := DebugAutoRightOffsetY, Z := 0.0}
                if (Character.TeleportTo[Spot, MakeRotationFromYawPitchRollDegrees(ArrivalYaw, 0.0, 0.0)]) {}
                Sleep(6.0)
                if (State.Stage = Stage):
                    Print("FNM: debug auto-right stuck at stage {Stage}")
                    break
            else:
                break
        Print("FNM: debug auto-right done: finished={FnmYesNo(State.Finished)} stage={State.Stage}")

    DebugDoor(State:fnm_player_state)<suspends>:void =
        Sleep(8.0)
        if (Station := Stations[0], Door := Station.Doors[DebugDoorTest], Character := State.Player.GetFortCharacter[]):
            # The trigger sits 2.3 m past the door wall; stand 2.5 m in front of the wall.
            Spot := Door.GetTransform().Translation - vector3{X := 0.0, Y := 480.0, Z := 0.0}
            if (Character.TeleportTo[Spot, MakeRotationFromYawPitchRollDegrees(ArrivalYaw, 0.0, 0.0)]):
                Print("FNM: debug door: in front of {FnmChoiceLetter(DebugDoorTest)} at {Spot}")
            for (N := 1..12):
                Sleep(1.0)
                Print("FNM: debug pos y={Character.GetTransform().Translation.Y} stage={State.Stage}")

    DebugPassage(State:fnm_player_state)<suspends>:void =
        Sleep(8.0)
        if (State.CurrentItem >= 0, Station := Stations[0], Door := Station.Doors[AnswerDoor(State)], Character := State.Player.GetFortCharacter[]):
            Spot := Door.GetTransform().Translation
            if (Character.TeleportTo[Spot, MakeRotationFromYawPitchRollDegrees(ArrivalYaw, 0.0, 0.0)]):
                Print("FNM: debug passage: dropped into vestibule {FnmChoiceLetter(AnswerDoor(State))} at {Spot}")
            for (N := 1..12):
                Sleep(1.0)
                Print("FNM: debug pos y={Character.GetTransform().Translation.Y} stage={State.Stage}")
            # Then behind a WRONG door's trigger at the current station, facing its (closed) barrier.
            if (State.CurrentItem >= 0, Here := Stations[State.Stage - 1], Wrong := Here.Doors[if (AnswerDoor(State) = 0) then 1 else 0]):
                Behind := Wrong.GetTransform().Translation + vector3{X := 0.0, Y := 350.0, Z := 0.0}
                if (Character.TeleportTo[Behind, MakeRotationFromYawPitchRollDegrees(ArrivalYaw, 0.0, 0.0)]):
                    Print("FNM: debug passage: behind a wrong door at {Behind}")
                for (N := 1..8):
                    Sleep(1.0)
                    Print("FNM: debug pos y={Character.GetTransform().Translation.Y} stage={State.Stage}")

    # Applies Kind to Player, who answered wrong through door DoorIndex at Station. Returns once the player
    # can play again.
    Punish(Player:player, Station:fnm_station, DoorIndex:int, Kind:fnm_penalty)<suspends>:void =
        Print("FNM: penalty {FnmPenaltyLabel(Kind)}")
        if (Kind = fnm_penalty.Freeze):
            if (Character := Player.GetFortCharacter[]):
                WideCamera(Player, true)
                Feet := Character.GetTransform().Translation - vector3{X := 0.0, Y := 0.0, Z := FeetDrop}
                Character.PutInStasis(stasis_args{AllowTurning := false, AllowFalling := false, AllowEmotes := false})
                FxOn(Player, FrostFx)
                Ice := IceRig.NextIndex()
                Placed := IceRig.Place(Ice, Feet, 0.0)
                Print("FNM: ice {Ice} placed={FnmYesNo(Placed)} at {Feet}")
                Sleep(FreezeSeconds)
                IceRig.Park(Ice)
                FxOff(Player, FrostFx)
                Character.ReleaseFromStasis()
                WideCamera(Player, false)
            SendTo(Player, Station.RetryTeleporter)
        else if (Kind = fnm_penalty.Yeet):
            if (Character := Player.GetFortCharacter[]):
                PullOut(Character, Station, DoorIndex)
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
                Print("FNM: yeet landed at {Landed} after {Airborne} s, {Feet.Y - Landed.Y} cm back")
                # Where they land in their own hallway is where they carry on; anywhere else, the entry.
                EntryY := Station.RetryTeleporter.GetTransform().Translation.Y
                InHallway := if (Landed.Y >= EntryY, Landed.Y <= Feet.Y + 100.0, Landed.Z <= Feet.Z + 300.0) then true else false
                if (not InHallway?):
                    SendTo(Player, Station.RetryTeleporter)
            else:
                SendTo(Player, Station.RetryTeleporter)
        else if (Kind = fnm_penalty.Mud):
            SendTo(Player, Station.RetryTeleporter)
            spawn{ Muddy(Player) }
            spawn{ ScreenFx(Player, MudFx, MudSeconds) }
        else if (Kind = fnm_penalty.Dizzy):
            SendTo(Player, Station.RetryTeleporter)
            Spin(Player)
            spawn{ DizzyPulses(Player) }
        else if (Kind = fnm_penalty.Blackout):
            if (Character := Player.GetFortCharacter[]):
                Character.PutInStasis(stasis_args{AllowTurning := false, AllowFalling := false, AllowEmotes := false})
                if (State := PlayerStates[Player]) then State.Hud.SetBlack(true)
                Sleep(BlackoutSeconds)
                SendTo(Player, Station.RetryTeleporter)
                Character.ReleaseFromStasis()
                Sleep(0.5)
                if (State := PlayerStates[Player]) then State.Hud.SetBlack(false)
            else:
                SendTo(Player, Station.RetryTeleporter)
        else:
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
                Sleep(SpearSeconds)
                Character.PutInStasis(stasis_args{AllowTurning := false, AllowFalling := false, AllowEmotes := false})
                Sleep(SpikeWatchSeconds)
                Character.ReleaseFromStasis()
                WideCamera(Player, false)
                Character.Damage(SpikeDamage)
                Sleep(SpikeHoldSeconds)
                for (Index : Spears):
                    SpikeRig.Park(Index)
            # Wait for the respawned character (gives up after ~20 s); WatchLife puts them back at the entry.
            var Waited : int = 0
            loop:
                Sleep(0.25)
                if (Character := Player.GetFortCharacter[], Character.IsActive[]):
                    break
                if (Waited >= 80):
                    break
                set Waited += 1
            Print("FNM: spike respawn after {Waited} polls")
            Sleep(0.3)

    # Blends a screen effect in (FxOn) or out (FxOff) for Player only.
    FxOn(Player:player, Fx:?post_process_device):void =
        if (Device := Fx?):
            Device.BlendIn(Player)

    FxOff(Player:player, Fx:?post_process_device):void =
        if (Device := Fx?):
            Device.BlendOut(Player)

    Muddy(Player:player)<suspends>:void =
        if (Mud := MudDevice?):
            var Elapsed : float = 0.0
            loop:
                if (Elapsed >= MudSeconds) then break
                Mud.Activate(Player)
                Wait := Min(MudReapplySeconds, MudSeconds - Elapsed)
                Sleep(Wait)
                set Elapsed += Wait
            Mud.Deactivate(Player)

    ScreenFx(Player:player, Fx:?post_process_device, Seconds:float)<suspends>:void =
        FxOn(Player, Fx)
        Sleep(Seconds)
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
    DizzyPulses(Player:player)<suspends>:void =
        if (Device := DizzyFx?):
            Pulse := Max(DizzyPulseSeconds, 0.1)
            var Elapsed : float = 0.0
            var Pulses : int = 0
            loop:
                if (Elapsed >= DizzySeconds) then break
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
        if (Camera := PenaltyCam?):
            if (On?) then Camera.AddTo(Player) else Camera.RemoveFrom(Player)

    # Starting loadout: the pistol and spare ammo (fires the fnm_loadout trigger, which the item granter
    # listens to), full health and full shield.
    GiveLoadout(Player:player):void =
        if (Trigger := LoadoutTrigger?):
            Trigger.Trigger(Player)
        if (Character := Player.GetFortCharacter[]):
            Character.SetHealth(Character.GetMaxHealth())
            Character.SetShield(Character.GetMaxShield())
            Print("FNM: loadout: health {Character.GetHealth()}, shield {Character.GetShield()}")

    # Moves a punished player out of the vestibule behind door DoorIndex into open hallway PenaltyStandOff in
    # front of the door wall (centred like the entry), facing the doors, and lets them land.
    PullOut(Character:fort_character, Station:fnm_station, DoorIndex:int)<suspends>:void =
        if (Door := Station.Doors[DoorIndex]):
            DoorAt := Door.GetTransform().Translation
            Entry := ArrivalSpot(Station.RetryTeleporter)
            # The trigger sits 2.3 m past the door wall.
            Spot := vector3{X := Entry.X, Y := DoorAt.Y - 230.0 - PenaltyStandOff, Z := Entry.Z}
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
        set State.Finished = true
        set State.Runs += 1
        Total := Stations.Length
        Time := if (State.StartTime >= 0.0) then GetSimulationElapsedTime() - State.StartTime else 0.0
        set State.StartTime = -1.0
        StopBoost(State)
        # Personal best and the board are per skill (the cartridge's index in the slot).
        Skill := State.CartridgeIndex
        HadBest := if (State.BestTime >= 0.0) then true else false
        NewBest := if (State.BestTime < 0.0 or Time < State.BestTime) then true else false
        if (NewBest?):
            set State.BestTime = Time
            if (set State.BestTimes[Skill] = Time) {}
            FnmSaveBest(State.Player, State.Cartridge.Id, Time)
        var IslandRecord : logic = true
        if (Top := BoardFor(Skill)[0], Time >= Top.Time):
            set IslandRecord = false
        RecordResult(Skill, State.Player, Time)
        Board := BoardFor(Skill)
        Medal := FnmMedal(State.FirstTryCorrect, Total)
        MedalColor := if (Medal = "GOLD") then NamedColors.Gold else if (Medal = "SILVER") then NamedColors.Silver else NamedColors.Peru
        # The board is the only thing on screen besides the clock, which keeps the final time.
        State.Hud.SetClock(FnmClock(Time))
        State.Hud.SetTarget("")
        State.Hud.SetStreak("")
        State.Hud.ClearQuestion()
        State.Hud.ClearVerdictNow()
        BestTail := if (NewBest?, HadBest?) then "   NEW BEST!" else ""
        RecordTail := if (IslandRecord?) then "   NEW RECORD!" else ""
        RecordLine := if (Top := Board[0]) then FnmHolder(FnmClock(Top.Time), Top.Who, RecordTail) else FnmText("Island record   -")
        Rows := for (K -> Row : Board) { FnmRow(K + 1, Row.Who, FnmClock(Row.Time)) }
        var OwnRow : int = -1
        for (K -> Row : Board, Row.Who = State.Player):
            set OwnRow = K
        State.Hud.ShowResults(Medal, MedalColor, "Your time   {FnmClock(Time)}", "Your best   {FnmClock(State.BestTime)}{BestTail}",
            RecordLine, "{FnmAccuracyLine(State.FirstTryCorrect, Total)}   -   Best streak {State.BestStreak}",
            "TOP TIMES THIS SESSION  -  {State.Cartridge.Title}", Rows, OwnRow)
        Print("FNM: finished run {State.Runs} in {FnmClock(Time)}, {Medal}, first try {State.FirstTryCorrect}/{Total}, best streak {State.BestStreak}, new best {FnmYesNo(NewBest)}, new record {FnmYesNo(IslandRecord)}, board {Board.Length} rows (size {BoardSize}) for {State.Cartridge.Id}")
        if (UseEndGameDevice?):
            State.Hud.SetCountdown("")
            spawn{ EndGameLater(State.Player) }
        else:
            set HallHoldUntil = GetSimulationElapsedTime() + HallCycleSeconds * 2.0
            ShowHall(Skill)
            if (NewRaceButtons.Length = 0):
                # No podium: the board's own buttons (they hold the player still) and the automatic restart.
                State.Hud.ShowFinishButtons(if (Cartridges.Length > 1) then true else false)
                spawn{ NextRun(State) }
            else:
                # A podium: the board captures no input, so the player walks on into the victory area at once (Aaron
                # 2026-10-06: the old board popped up and locked him out of it); it hides itself after ResultsSeconds.
                State.Hud.SetCountdown("Walk on!   NEW RACE  /  CHANGE SKILL  at the podium ahead")
                spawn{ HideResultsLater(State) }

    # Hides the finish board ResultsSeconds after a finish, unless a new run or a skill change already did.
    HideResultsLater(State:fnm_player_state)<suspends>:void =
        Generation := State.RunGeneration
        Sleep(ResultsSeconds)
        if (PlayerStates[State.Player], State.Finished?, State.RunGeneration = Generation):
            CloseResults(State)

    # ---------------------------------------------------------------- victory area

    # Finds the podium buttons and the all-time screen (tools/build_finish.py) and starts the screen.
    SetUpVictoryArea():void =
        for (Object : FindCreativeObjectsWithTag(fnm_new_race), Button := button_device[Object]):
            Button.SetInteractionText(FnmText("Race again"))
            Button.InteractedWithEvent.Subscribe(OnNewRaceButton)
            set NewRaceButtons += array{Button}
        for (Object : FindCreativeObjectsWithTag(fnm_change_skill), Button := button_device[Object]):
            Button.SetInteractionText(FnmText("Change skill"))
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
        State.Hud.SetTarget(if (NewRaceButtons.Length > 0) then "Race again: NEW RACE at the podium" else "")
        Print("FNM: results closed")
        if (DebugVictoryTest?):
            spawn{ DebugToPodium(State) }

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

    # Puts Who's Time on skill Index's board: replaces their row only when faster, else adds one; fastest first,
    # capped at BoardSize.
    RecordResult(Index:int, Who:player, Time:float):void =
        var Rows : []fnm_result = array{}
        var Had : logic = false
        for (Row : BoardFor(Index)):
            if (Row.Who = Who):
                set Had = true
                set Rows += array{if (Time < Row.Time) then fnm_result{Who := Who, Time := Time} else Row}
            else:
                set Rows += array{Row}
        if (not Had?):
            set Rows += array{fnm_result{Who := Who, Time := Time}}
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
        State.Hud.HideFinishButtons()
        State.Hud.HideResults()
        for (Station : Stations, MaybePassage : Station.Passages, Passage := MaybePassage?):
            Passage.RemoveFromIgnoreList(State.Player)
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
        set State.StartTime = -1.0
        State.Hud.SetTarget(if (State.BestTime >= 0.0) then "Beat {FnmClock(State.BestTime)}" else "")
        State.Hud.SetStreak(StreakCopy(State, 0))
        MaybeCharacter := option{State.Player.GetFortCharacter[]}
        if (Character := MaybeCharacter?):
            Character.PutInStasis(stasis_args{AllowTurning := true, AllowFalling := false, AllowEmotes := false})
        for (Count : array{3, 2, 1}):
            State.Hud.FlashBig("{Count}", NamedColors.White, 0.0)
            Sleep(CountdownStepSeconds)
        if (Character := MaybeCharacter?):
            Character.ReleaseFromStasis()
        State.Hud.FlashBig("GO!", NamedColors.Lime, 1.0)
        set State.StartTime = GetSimulationElapsedTime()
        Print("FNM: run {State.Runs + 1} GO")
        loop:
            if (State.RunGeneration <> Generation or State.StartTime < 0.0 or State.Finished?) then break
            State.Hud.SetClock(FnmClock(GetSimulationElapsedTime() - State.StartTime))
            Sleep(0.1)

    # Streak line for the top panel: "" (no streak), "STREAK x3", "STREAK x3  -  SPEED BOOST 4s" or (streak 1)
    # "SPEED BOOST 3s". BoostLeft = whole seconds of boost left (0 = none running).
    StreakCopy(State:fnm_player_state, BoostLeft:int):string =
        StreakPart := if (State.Streak >= 2) then "STREAK x{State.Streak}" else ""
        if (BoostLeft <= 0) then StreakPart
        else if (StreakPart = "") then "SPEED BOOST {BoostLeft}s"
        else "{StreakPart}  -  SPEED BOOST {BoostLeft}s"

    # Speeds the player up (fnm_boost modulator) for Seconds; a newer boost or StopBoost ends this one. Ticks once a
    # second so the HUD counts the boost down, re-activating the modulator (3 s duration) every BoostReapplySeconds
    # or sooner.
    Boost(State:fnm_player_state, Seconds:float)<suspends>:void =
        set State.BoostGeneration += 1
        Generation := State.BoostGeneration
        if (Device := BoostDevice?):
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

    StopBoost(State:fnm_player_state):void =
        set State.BoostGeneration += 1
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
        for (Zone : IceZones, Zone.IsInVolume[State.Player]):
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

    # Shows a short orange notice that clears itself after NoticeSeconds.
    FlashNotice(State:fnm_player_state, Message:string)<suspends>:void =
        Generation := State.Hud.ShowFeedback(Message, NamedColors.Orange)
        Sleep(NoticeSeconds)
        State.Hud.ClearFeedbackIf(Generation)
