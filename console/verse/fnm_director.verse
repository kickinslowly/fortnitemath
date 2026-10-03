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
# After the last station -> first-try accuracy on the HUD (optionally activates an end_game_device).

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

    # Wrong-door penalties this map can draw from, one at random per wrong answer. Each penalty's visual
    # is a rig (fnm_rig.verse) placed by tools/build_rigs.py.
    @editable
    Penalties : []fnm_penalty = array{fnm_penalty.Freeze, fnm_penalty.Spike, fnm_penalty.Yeet}
    @editable
    FreezeSeconds : float = 5.0
    # Seconds the air vent stays under a yeeted player, and the most seconds they stay airborne before
    # being put back at the station entry.
    @editable
    YeetSeconds : float = 1.5
    @editable
    YeetAirSeconds : float = 8.0
    # Spike: SpearCount spears wait SpearDepth (cm) under the floor in a ring of radius SpearRing around
    # the player, burst up SpearRise in SpearSeconds, then SpikeDamage eliminates (more than full health
    # + shield). The ring stays up SpikeHoldSeconds.
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
    SpikeHoldSeconds : float = 1.5
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

    OnBegin<override>()<suspends>:void =
        set Cartridge = FnmActiveCartridge()
        set TierCount = Cartridge.Tiers.Length
        set TierPools = FnmBuildTierPools(Cartridge.Items, TierCount)
        set Stations = BuildStations()
        set IceRig = BuildRig("ice", fnm_ice)
        set SpikeRig = BuildRig("spike", fnm_spike)
        set YeetRig = BuildRig("yeet", fnm_yeet)
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
            # Start everyone at station 1 facing the doors, whatever spawn pad the island used.
            if (First := Stations[0]):
                SendTo(Joined, First.RetryTeleporter)
            if (DebugAutoWrongAnswers > 0):
                spawn{ DebugAutoWrong(State) }
            if (DebugPassageTest?):
                spawn{ DebugPassage(State) }
            if (DebugDoorTest >= 0):
                spawn{ DebugDoor(State) }

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
                if (not State.MissedCurrent?):
                    set State.FirstTryCorrect += 1
                State.Hud.FlashVerdict(true, "")
                AdvancePlayer(State, Station, DoorIndex)
                set State.Busy = false
                if (not State.Finished?):
                    Generation := State.Hud.ShowFeedback("Correct!  " + Item.Explanation, NamedColors.LightGreen)
                    Sleep(CorrectFeedbackSeconds)
                    State.Hud.ClearFeedbackIf(Generation)
            else:
                set State.MissedCurrent = true
                Kind := PickPenalty()
                State.Hud.FlashVerdict(false, FnmPenaltyLabel(Kind))
                Generation := State.Hud.ShowFeedback(FeedbackFor(Item, DoorIndex), NamedColors.Tomato)
                Punish(State.Player, Station, Kind)
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
                HandleDoor(State, State.Stage - 1, if (Item.Answer = 0) then 1 else 0)

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

    # Applies Kind to Player, who answered wrong at Station. Returns once the player can play again.
    Punish(Player:player, Station:fnm_station, Kind:fnm_penalty)<suspends>:void =
        Print("FNM: penalty {FnmPenaltyLabel(Kind)}")
        if (Kind = fnm_penalty.Freeze):
            if (Character := Player.GetFortCharacter[]):
                Feet := Character.GetTransform().Translation - vector3{X := 0.0, Y := 0.0, Z := FeetDrop}
                Character.PutInStasis(stasis_args{AllowTurning := false, AllowFalling := false, AllowEmotes := false})
                Ice := IceRig.NextIndex()
                Placed := IceRig.Place(Ice, Feet, 0.0)
                Print("FNM: ice {Ice} placed={FnmYesNo(Placed)} at {Feet}")
                Sleep(FreezeSeconds)
                IceRig.Park(Ice)
                Character.ReleaseFromStasis()
            SendTo(Player, Station.RetryTeleporter)
        else if (Kind = fnm_penalty.Yeet):
            if (Character := Player.GetFortCharacter[]):
                Feet := Character.GetTransform().Translation - vector3{X := 0.0, Y := 0.0, Z := FeetDrop}
                Vent := YeetRig.NextIndex()
                Placed := YeetRig.Place(Vent, Feet, 0.0)
                if (Part := YeetRig.PartAt[Vent], AirVent := air_vent_device[Part]):
                    AirVent.Enable()
                    AirVent.Activate()
                # The vent only launches a player who ENTERS its gust; one standing still as it arrives is
                # ignored. Hop them up into it.
                Sleep(0.1)
                Hop := Character.GetTransform()
                if (Character.TeleportTo[Hop.Translation + vector3{X := 0.0, Y := 0.0, Z := 40.0}, Hop.Rotation]) {}
                Print("FNM: vent {Vent} placed={FnmYesNo(Placed)} at {Feet}")
                Sleep(YeetSeconds)
                Print("FNM: yeet height {Character.GetTransform().Translation.Z - Feet.Z} cm")
                YeetRig.Park(Vent)
                # Rooms have no roof, so a glider can land outside its room: once they touch down (or after
                # YeetAirSeconds), put them back at the station entry.
                var Airborne : float = 0.0
                loop:
                    if (Character.IsOnGround[]) then break
                    if (Airborne >= YeetAirSeconds) then break
                    Sleep(0.25)
                    set Airborne += 0.25
                Print("FNM: yeet landed after {Airborne} s")
            SendTo(Player, Station.RetryTeleporter)
        else:
            if (Character := Player.GetFortCharacter[]):
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
                Character.Damage(SpikeDamage)
                Sleep(SpikeHoldSeconds)
                for (Index : Spears):
                    SpikeRig.Park(Index)
            # Wait for the respawned character (gives up after ~20 s).
            var Waited : int = 0
            loop:
                Sleep(0.25)
                if (Character := Player.GetFortCharacter[], Character.IsActive[]):
                    break
                if (Waited >= 80):
                    break
                set Waited += 1
            Print("FNM: spike respawn after {Waited} polls")
            SendTo(Player, Station.RetryTeleporter)

    # Move Player into open floor just past Pad, facing the doors; falls back to the pad's own teleport
    # if the character can't be moved directly.
    SendTo(Player:player, Pad:teleporter_device):void =
        PadAt := Pad.GetTransform().Translation
        Spot := PadAt + vector3{X := 0.0, Y := ArrivalForward, Z := ArrivalLift}
        Facing := MakeRotationFromYawPitchRollDegrees(ArrivalYaw, 0.0, 0.0)
        if (Character := Player.GetFortCharacter[], Character.TeleportTo[Spot, Facing]):
            Print("FNM: moved player to {Spot} (pad {PadAt})")
            return
        Print("FNM: direct move failed; using the pad's own teleport")
        Pad.Teleport(Player)

    FinishPlayer(State:fnm_player_state):void =
        set State.Finished = true
        Total := Stations.Length
        State.Hud.ShowFinished("Course complete!", FnmAccuracyLine(State.FirstTryCorrect, Total))
        if (UseEndGameDevice?):
            spawn{ EndGameLater(State.Player) }

    EndGameLater(Finisher:player)<suspends>:void =
        Sleep(EndGameDelaySeconds)
        if (Finisher.IsActive[]):
            EndGameDevice.Activate(Finisher)

    # Shows a short orange notice that clears itself after NoticeSeconds.
    FlashNotice(State:fnm_player_state, Message:string)<suspends>:void =
        Generation := State.Hud.ShowFeedback(Message, NamedColors.Orange)
        Sleep(NoticeSeconds)
        State.Hud.ClearFeedbackIf(Generation)
