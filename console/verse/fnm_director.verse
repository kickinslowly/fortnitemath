# FNM console runtime -- the device that plays the active cartridge on a linear course of stations.
# Place ONE fnm_director in the level. It finds the course by Verse tags (fnm_tags.verse), so there is
# nothing to wire: tag each station's entry teleporter fnm_station_NN + fnm_entry, each door trigger
# fnm_station_NN + fnm_door_a..d, and the finish teleporter fnm_finish (see console/README.md).
# Why tags: UEFN 42.30 rejected trigger/teleporter references in this device's @editable arrays from
# both MCP and the Details panel ("is not valid trigger_device"), while tags set cleanly.
#
# Per player: own stage, own question, own HUD, own draw decks (PROTOCOL 6).
# Wrong door  -> big red X, that choice's Feedback, a random penalty from Penalties, same question.
# Right door  -> big green check, next question, teleport to NextTeleporter at once (no stall); the
#                Explanation stays on the HUD for CorrectFeedbackSeconds while the player moves on.
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

    # Wrong-door penalties this map can draw from, one at random per wrong answer. Yeet is out of the
    # default pool until it launches for real: SetLinearVelocity is a no-op on players (verified 2026-10-03).
    @editable
    Penalties : []fnm_penalty = array{fnm_penalty.Freeze, fnm_penalty.Spike}
    @editable
    FreezeSeconds : float = 5.0
    # Yeet launch velocity in m/s: back along the course (-Y) and up.
    @editable
    YeetBackSpeed : float = 25.0
    @editable
    YeetUpSpeed : float = 12.0
    # Damage dealt by Spike; more than full health + shield eliminates.
    @editable
    SpikeDamage : float = 1000.0

    # Test hook: each joining player auto-answers this many questions wrong, one every 12 s, cycling
    # through Penalties in order, so every penalty can be watched without walking. 0 = off (ship value).
    @editable
    DebugAutoWrongAnswers : int = 0
    var DebugPenaltyCursor : int = 0

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

    OnBegin<override>()<suspends>:void =
        set Cartridge = FnmActiveCartridge()
        set TierCount = Cartridge.Tiers.Length
        set TierPools = FnmBuildTierPools(Cartridge.Items, TierCount)
        set Stations = BuildStations()
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

    # One station's tagged parts: its entry teleporter and its doors in A..D order (missing letters skipped).
    FindStationParts(StationTag:castable_subtype(tag)):tuple(?teleporter_device, []trigger_device) =
        var Entry : ?teleporter_device = false
        var DoorA : ?trigger_device = false
        var DoorB : ?trigger_device = false
        var DoorC : ?trigger_device = false
        var DoorD : ?trigger_device = false
        for (Object : FindCreativeObjectsWithTag(StationTag)):
            if (Teleporter := teleporter_device[Object]):
                set Entry = option{Teleporter}
            else if (Trigger := trigger_device[Object]):
                ObjectTags := Object.GetTags()
                if (ObjectTags.Has[fnm_door_a{}]):
                    set DoorA = option{Trigger}
                else if (ObjectTags.Has[fnm_door_b{}]):
                    set DoorB = option{Trigger}
                else if (ObjectTags.Has[fnm_door_c{}]):
                    set DoorC = option{Trigger}
                else if (ObjectTags.Has[fnm_door_d{}]):
                    set DoorD = option{Trigger}
        Doors := for (MaybeDoor : array{DoorA, DoorB, DoorC, DoorD}, Door := MaybeDoor?):
            Door
        (Entry, Doors)

    # Stations 1, 2, ... in order until the first station tag with no entry teleporter. A wrong answer
    # returns the player to their station's entry; a right answer sends them to the next entry (last
    # station: the fnm_finish teleporter).
    BuildStations():[]fnm_station =
        var Finish : ?teleporter_device = false
        for (Object : FindCreativeObjectsWithTag(fnm_finish), Teleporter := teleporter_device[Object]):
            set Finish = option{Teleporter}
        var Entries : []teleporter_device = array{}
        var DoorSets : [][]trigger_device = array{}
        var Searching : logic = true
        for (StationTag : FnmStationTags()):
            Parts := FindStationParts(StationTag)
            if (Searching?, Entry := Parts(0)?):
                set Entries = Entries + array{Entry}
                set DoorSets = DoorSets + array{Parts(1)}
            else:
                set Searching = false
        for (K -> Entry : Entries, StationDoors := DoorSets[K]):
            var Next : teleporter_device = Entry
            if (Following := Entries[K + 1]):
                set Next = Following
            else if (FinishPoint := Finish?):
                set Next = FinishPoint
            var OverridePercent : int = -1
            if (Value := DifficultyOverrides[K]):
                set OverridePercent = Value
            fnm_station{Doors := StationDoors, RetryTeleporter := Entry, NextTeleporter := Next, DifficultyOverride := OverridePercent}

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
                else:
                    spawn{ FlashNotice(State, "This is not your station. You are on stage {State.Stage}.") }

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
                AdvancePlayer(State, Station)
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

    # Correct answer at Station: next stage (or finish), then move the player on.
    AdvancePlayer(State:fnm_player_state, Station:fnm_station):void =
        set State.Stage += 1
        if (State.Stage > Stations.Length):
            FinishPlayer(State)
        else:
            DrawItem(State)
            ShowCurrent(State)
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

    # Applies Kind to Player, who answered wrong at Station. Returns once the player can play again.
    Punish(Player:player, Station:fnm_station, Kind:fnm_penalty)<suspends>:void =
        Print("FNM: penalty {FnmPenaltyLabel(Kind)}")
        if (Kind = fnm_penalty.Freeze):
            if (Character := Player.GetFortCharacter[]):
                Character.PutInStasis(stasis_args{AllowTurning := true, AllowFalling := true, AllowEmotes := false})
                Sleep(FreezeSeconds)
                Character.ReleaseFromStasis()
            SendTo(Player, Station.RetryTeleporter)
        else if (Kind = fnm_penalty.Yeet):
            if (Character := Player.GetFortCharacter[]):
                FnmYeet(Character, YeetBackSpeed, YeetUpSpeed)
                Sleep(0.2)
                Print("FNM: yeet {FnmVelocityLine(Character)}")
            Sleep(1.5)
        else:
            if (Character := Player.GetFortCharacter[]):
                Character.Damage(SpikeDamage)
            # Wait out the elimination, then for the respawned character (gives up after ~20 s).
            Sleep(1.0)
            var Waited : int = 0
            loop:
                if (Character := Player.GetFortCharacter[], Character.IsActive[]):
                    break
                if (Waited >= 80):
                    break
                set Waited += 1
                Sleep(0.25)
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
