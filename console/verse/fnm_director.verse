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
# Per player: own stage, own question, own HUD, own draw decks (PROTOCOL 6).
# Wrong door  -> big red X, that choice's Feedback, a random penalty from Penalties, same question.
# Right door  -> big green check, next question, and the way on opens at once (no stall): that door's
#                barrier lets them through, or a teleport to NextTeleporter. The Explanation stays on the
#                HUD for CorrectFeedbackSeconds while the player moves on.
# After the last station -> time, medal and first-try accuracy on the HUD, then (unless an end_game_device is
#                set) a fresh run from station 1 to beat that time.
# Engagement: a 3-2-1-GO countdown and a race clock per run; a first-try right answer builds a streak and a
# speed boost (longer with the streak); shipping containers tagged fnm_slider sweep across the hallways.
# Guards: a guard spawner tagged fnm_guards + fnm_station_NN (tools/build_guards.py, more guards per later station)
# is switched on while any player is on that station and off (its guards despawn) once nobody is. Any player
# eliminated (a guard, a Spike) respawns at the entry of the station they were on, with the pistol.

using { /Fortnite.com/Characters }
using { /Fortnite.com/Devices }
using { /UnrealEngine.com/Temporary/SpatialMath }
using { /Verse.org/Colors }
using { /Verse.org/Random }
using { /Verse.org/Simulation }
using { /Verse.org/Simulation/Tags }

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
    # 1-based stage; stage s is played at Stations[s - 1].
    var Stage : int = 1
    # Remaining shuffled item indices per tier (index t - 1 for tier t).
    var Decks : [][]int = array{}
    # Index into the cartridge's Items of the question on screen (-1 = none).
    var CurrentItem : int = -1
    var MissedCurrent : logic = false
    var FirstTryCorrect : int = 0
    # True while a door result is being processed (blocks double triggers).
    var Busy : logic = false
    var Finished : logic = false
    # Right-first-try answers in a row (a wrong door resets it).
    var Streak : int = 0
    var BestStreak : int = 0
    # Race clock: simulation time the run's GO! showed; -1 = not running yet.
    var StartTime : float = -1.0
    # Bumped per run and per boost, so an older clock or boost loop stops itself.
    var RunGeneration : int = 0
    var BoostGeneration : int = 0
    # Best finishing time this session (-1 = none yet) and runs finished.
    var BestTime : float = -1.0
    var Runs : int = 0

# Binds one door to its station/door index, so a single callback signature can serve every door.
fnm_door_handler := class:
    Director : fnm_director
    StationIndex : int
    DoorIndex : int

    OnTriggered(MaybeAgent:?agent):void =
        Director.OnDoor(MaybeAgent, StationIndex, DoorIndex)

fnm_director := class(creative_device):
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
    @editable
    DizzySeconds : float = 6.0
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
    # right door's vestibule (the real trigger and barrier do the rest), so the finish can be checked
    # without walking. false = off (ship value).
    @editable
    DebugAutoRightAnswers : logic = false
    # Test hook: each joining player starts at this stage's entry (to try a later hallway's obstacles). 0 or 1 =
    # station 1 (ship value 0).
    @editable
    DebugStartStage : int = 0

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
    # Sliding containers: SliderSeconds to cross the hallway, SliderPause at each wall.
    @editable
    SliderSeconds : float = 2.2
    @editable
    SliderPause : float = 0.5
    # Countdown before each run: one beat per number.
    @editable
    CountdownStepSeconds : float = 0.8
    # Seconds the results show before the player is put back at station 1 for another run (no End Game device).
    @editable
    RestartSeconds : int = 12
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

    var Cartridge : fnm_cartridge = fnm_cartridge:
        Protocol := ""
        Id := ""
        Version := ""
        Title := ""
        Subtitle := ""
        Tiers := array{}
        Items := array{}
    var Stations : []fnm_station = array{}
    var TierCount : int = 0
    var TierPools : [][]int = array{}
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
    # Fastest run by anyone this session (-1 = none yet).
    var IslandBest : float = -1.0
    var FrostFx : ?post_process_device = false
    var MudFx : ?post_process_device = false
    var DizzyFx : ?post_process_device = false
    # Per station (index = stage - 1): its guard spawner, if any, and whether its guards are up.
    var GuardSpawners : []?guard_spawner_device = array{}
    var GuardsUp : []logic = array{}
    var GuardsSpawned : int = 0

    OnBegin<override>()<suspends>:void =
        set Cartridge = FnmActiveCartridge()
        set TierCount = Cartridge.Tiers.Length
        set TierPools = FnmBuildTierPools(Cartridge.Items, TierCount)
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
        set FrostFx = FindFx(fnm_pp_frost)
        set MudFx = FindFx(fnm_pp_mud)
        set DizzyFx = FindFx(fnm_pp_dizzy)
        Print("FNM: penalty camera {FnmYesNo(if (PenaltyCam?) then true else false)}, loadout trigger {FnmYesNo(if (LoadoutTrigger?) then true else false)}, mud {FnmYesNo(if (MudDevice?) then true else false)}")
        Print("FNM: screen fx frost {FnmYesNo(if (FrostFx?) then true else false)}, mud {FnmYesNo(if (MudFx?) then true else false)}, dizzy {FnmYesNo(if (DizzyFx?) then true else false)}; {Penalties.Length} penalties in the pool")
        if (Stations.Length = 0):
            Print("FNM: fnm_director found no stations: tag an entry teleporter fnm_station_01 + fnm_entry.")
        else if (TierCount = 0):
            Print("FNM: the active cartridge has no tiers.")
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
        for (State : PlayerStates, not State.Finished?, State.Stage = Index + 1):
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
    # station they were on with the starting loadout. (A Spike penalty waits for this itself.)
    WatchLife(State:fnm_player_state)<suspends>:void =
        var WasAlive : logic = true
        loop:
            Sleep(0.25)
            if (not PlayerStates[State.Player]) then break
            Alive := if (Character := State.Player.GetFortCharacter[], Character.IsActive[]) then true else false
            if (WasAlive?, not Alive?):
                Print("FNM: player eliminated at stage {State.Stage}")
                StopBoost(State)
                set State.Streak = 0
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
        if (not State.Busy?, not State.Finished?):
            spawn{ FlashNotice(State, "Eliminated! Back to the start of station {Stage}.") }

    FindFx(FxTag:castable_subtype(tag)):?post_process_device =
        var Found : ?post_process_device = false
        for (Object : FindCreativeObjectsWithTag(FxTag), Device := post_process_device[Object]):
            set Found = option{Device}
        Found

    # A station with fewer doors than an item has choices could hide the right answer.
    WarnAboutDoorCounts():void =
        var MostChoices : int = 0
        for (Item : Cartridge.Items):
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
        var Remaining : [player]fnm_player_state = map{}
        for (Key -> Value : PlayerStates, Key <> Departed):
            if (set Remaining[Key] = Value) {}
        set PlayerStates = Remaining

    StartPlayer(Joined:player):void =
        if (Ready?, not PlayerStates[Joined]):
            Hud := fnm_hud{}
            Hud.Attach(Joined)
            Hud.SetTitle(Cartridge.Title, Cartridge.Subtitle)
            State := fnm_player_state{Player := Joined, Hud := Hud, Decks := FnmShuffleAll(TierPools)}
            if (set PlayerStates[Joined] = State) {}
            DrawItem(State)
            ShowCurrent(State)
            State.Hud.SetClock(FnmClock(0.0))
            # Start everyone at station 1 facing the doors, whatever spawn pad the island used.
            if (First := Stations[0]):
                SendTo(Joined, First.RetryTeleporter)
            if (DebugStartStage > 1, Start := Stations[DebugStartStage - 1]):
                set State.Stage = DebugStartStage
                DrawItem(State)
                ShowCurrent(State)
                SendTo(Joined, Start.RetryTeleporter)
                Print("FNM: debug start at stage {DebugStartStage}")
            GiveLoadout(Joined)
            spawn{ Countdown(State) }
            spawn{ WatchLife(State) }
            if (DebugAutoWrongAnswers > 0):
                spawn{ DebugAutoWrong(State) }
            if (DebugPassageTest?):
                spawn{ DebugPassage(State) }
            if (DebugDoorTest >= 0):
                spawn{ DebugDoor(State) }
            if (DebugAutoRightAnswers?):
                spawn{ DebugAutoRight(State) }

    # ---------------------------------------------------------------- questions

    # Tier for stage Stage, honouring that station's DifficultyOverride.
    StationTier(Stage:int):int =
        var OverridePercent : int = -1
        if (Station := Stations[Stage - 1]):
            set OverridePercent = Station.DifficultyOverride
        FnmTierForStage(Stage, Stations.Length, TierCount, OverridePercent)

    # Draws the player's next item for their current stage (without replacement, per player).
    DrawItem(State:fnm_player_state):void =
        Tier := StationTier(State.Stage)
        if (Pool := TierPools[Tier - 1], Deck := State.Decks[Tier - 1]):
            Draw := FnmDraw(Deck, Pool)
            if (set State.Decks[Tier - 1] = Draw.Rest) {}
            set State.CurrentItem = Draw.ItemIndex
            set State.MissedCurrent = false

    ShowCurrent(State:fnm_player_state):void =
        if (Item := Cartridge.Items[State.CurrentItem]):
            StageCount := Stations.Length
            TierName := FnmTierName(Cartridge.Tiers, Item.Tier)
            StageLine := "Stage {State.Stage}/{StageCount}  -  {TierName}"
            State.Hud.ShowQuestion(StageLine, Item.Prompt, FnmChoicesLine(Item.Choices))

    # Student-facing text for wrong choice DoorIndex (PROTOCOL 6: ARITH text if missing).
    FeedbackFor(Item:fnm_item, DoorIndex:int):string =
        var Result : string = "Check your arithmetic."
        if (Line := Item.Feedback[DoorIndex], Line <> ""):
            set Result = Line
        Result

    # ---------------------------------------------------------------- doors

    OnDoor(MaybeAgent:?agent, StationIndex:int, DoorIndex:int):void =
        if (Ready?, Agent := MaybeAgent?, Visitor := player[Agent], State := PlayerStates[Visitor]):
            if (not State.Finished?, not State.Busy?):
                if (StationIndex = State.Stage - 1):
                    set State.Busy = true
                    spawn{ HandleDoor(State, StationIndex, DoorIndex) }
                else if (StationIndex > State.Stage - 1):
                    spawn{ FlashNotice(State, "This is not your station. You are on stage {State.Stage}.") }
                # An earlier station: they are walking back through a door they already passed. Ignore.

    HandleDoor(State:fnm_player_state, StationIndex:int, DoorIndex:int)<suspends>:void =
        if (Item := Cartridge.Items[State.CurrentItem], Station := Stations[StationIndex]):
            if (DoorIndex >= Item.Choices.Length):
                set State.Busy = false
                Letter := FnmChoiceLetter(DoorIndex)
                FlashNotice(State, "No choice {Letter} here")
            else if (DoorIndex = Item.Answer):
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
                Generation := State.Hud.ShowFeedback(FeedbackFor(Item, DoorIndex), NamedColors.Tomato)
                Punish(State.Player, Station, DoorIndex, Kind)
                set State.Busy = false
                Sleep(WrongFeedbackSeconds)
                State.Hud.ClearFeedbackIf(Generation)
        else:
            set State.Busy = false

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
            if (Item := Cartridge.Items[State.CurrentItem], not State.Busy?, not State.Finished?):
                set State.Busy = true
                Print("FNM: debug auto-wrong {N}")
                Wrong := if (Item.Answer = 0) then 1 else 0
                # Stand them in that door's vestibule, where a real wrong answer happens.
                if (Station := Stations[State.Stage - 1], Door := Station.Doors[Wrong], Character := State.Player.GetFortCharacter[]):
                    if (Character.TeleportTo[Door.GetTransform().Translation, MakeRotationFromYawPitchRollDegrees(ArrivalYaw, 0.0, 0.0)]) {}
                    Sleep(1.0)
                HandleDoor(State, State.Stage - 1, Wrong)

    DebugAutoRight(State:fnm_player_state)<suspends>:void =
        Sleep(8.0)
        loop:
            if (State.Finished?) then break
            if (Item := Cartridge.Items[State.CurrentItem], Station := Stations[State.Stage - 1], Door := Station.Doors[Item.Answer], Character := State.Player.GetFortCharacter[]):
                Stage := State.Stage
                if (Character.TeleportTo[Door.GetTransform().Translation, MakeRotationFromYawPitchRollDegrees(ArrivalYaw, 0.0, 0.0)]):
                    Print("FNM: debug auto-right stage {Stage} door {FnmChoiceLetter(Item.Answer)}")
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
        if (Item := Cartridge.Items[State.CurrentItem], Station := Stations[0], Door := Station.Doors[Item.Answer], Character := State.Player.GetFortCharacter[]):
            Spot := Door.GetTransform().Translation
            if (Character.TeleportTo[Spot, MakeRotationFromYawPitchRollDegrees(ArrivalYaw, 0.0, 0.0)]):
                Print("FNM: debug passage: dropped into vestibule {FnmChoiceLetter(Item.Answer)} at {Spot}")
            for (N := 1..12):
                Sleep(1.0)
                Print("FNM: debug pos y={Character.GetTransform().Translation.Y} stage={State.Stage}")
            # Then behind a WRONG door's trigger at the current station, facing its (closed) barrier.
            if (Next := Cartridge.Items[State.CurrentItem], Here := Stations[State.Stage - 1], Wrong := Here.Doors[if (Next.Answer = 0) then 1 else 0]):
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
            spawn{ ScreenFx(Player, DizzyFx, DizzySeconds) }
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
        NewBest := if (State.BestTime < 0.0 or Time < State.BestTime) then true else false
        if (NewBest?) then set State.BestTime = Time
        IslandRecord := if (IslandBest < 0.0 or Time < IslandBest) then true else false
        if (IslandRecord?) then set IslandBest = Time
        Medal := FnmMedal(State.FirstTryCorrect, Total)
        MedalColor := if (Medal = "GOLD") then NamedColors.Gold else if (Medal = "SILVER") then NamedColors.Silver else NamedColors.Peru
        State.Hud.SetClock(FnmClock(Time))
        State.Hud.SetStreak("Best streak {State.BestStreak}")
        State.Hud.FlashBig("FINISH!  {Medal}", MedalColor, 5.0)
        Record := if (IslandRecord?) then "ISLAND RECORD!  " else if (NewBest?, State.Runs > 1) then "NEW PERSONAL BEST!  " else ""
        State.Hud.ShowFinished("{Medal} MEDAL  -  {FnmClock(Time)}", "{Record}{FnmAccuracyLine(State.FirstTryCorrect, Total)}")
        Print("FNM: finished run {State.Runs} in {FnmClock(Time)}, {Medal}, first try {State.FirstTryCorrect}/{Total}, best streak {State.BestStreak}")
        if (UseEndGameDevice?):
            spawn{ EndGameLater(State.Player) }
        else:
            spawn{ NextRun(State) }

    # Results for RestartSeconds (with a countdown), then a fresh run from station 1: barriers closed again for
    # this player, new questions, streak and clock reset.
    NextRun(State:fnm_player_state)<suspends>:void =
        Generation := State.RunGeneration
        var Left : int = Max(1, RestartSeconds)
        loop:
            if (Left <= 0) then break
            State.Hud.ShowFeedback("Best {FnmClock(State.BestTime)}  -  island record {FnmClock(IslandBest)}  -  next run in {Left}", NamedColors.Gold)
            Sleep(1.0)
            set Left -= 1
        if (not PlayerStates[State.Player] or State.RunGeneration <> Generation):
            return
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
        State.Hud.SetStreak(if (State.BestTime >= 0.0) then "Beat {FnmClock(State.BestTime)}" else "")
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

    # Speeds the player up (fnm_boost modulator) for Seconds; a newer boost or StopBoost ends this one.
    Boost(State:fnm_player_state, Seconds:float)<suspends>:void =
        if (Device := BoostDevice?):
            set State.BoostGeneration += 1
            Generation := State.BoostGeneration
            StreakLine := if (State.Streak >= 2) then "STREAK x{State.Streak}  -  " else ""
            State.Hud.SetStreak("{StreakLine}SPEED BOOST!")
            var Elapsed : float = 0.0
            loop:
                if (Elapsed >= Seconds or State.BoostGeneration <> Generation) then break
                Device.Activate(State.Player)
                Wait := Min(BoostReapplySeconds, Seconds - Elapsed)
                Sleep(Wait)
                set Elapsed += Wait
            if (State.BoostGeneration = Generation):
                Device.Deactivate(State.Player)
                if (not State.Finished?):
                    State.Hud.SetStreak(if (State.Streak >= 2) then "STREAK x{State.Streak}" else "")

    StopBoost(State:fnm_player_state):void =
        set State.BoostGeneration += 1
        if (Device := BoostDevice?):
            Device.Deactivate(State.Player)
        if (not State.Finished?):
            State.Hud.SetStreak("")

    # Sweeps a container from its placed spot to the mirror image across the hallway (X -> -X) and back, forever.
    Slide(Slider:creative_prop)<suspends>:void =
        Home := Slider.GetTransform()
        Far := vector3{X := -Home.Translation.X, Y := Home.Translation.Y, Z := Home.Translation.Z}
        loop:
            Slider.MoveTo(Far, Home.Rotation, SliderSeconds)
            Sleep(SliderPause)
            Slider.MoveTo(Home.Translation, Home.Rotation, SliderSeconds)
            Sleep(SliderPause)

    EndGameLater(Finisher:player)<suspends>:void =
        Sleep(EndGameDelaySeconds)
        if (Finisher.IsActive[]):
            EndGameDevice.Activate(Finisher)

    # Shows a short orange notice that clears itself after NoticeSeconds.
    FlashNotice(State:fnm_player_state, Message:string)<suspends>:void =
        Generation := State.Hud.ShowFeedback(Message, NamedColors.Orange)
        Sleep(NoticeSeconds)
        State.Hud.ClearFeedbackIf(Generation)
