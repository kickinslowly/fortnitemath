# FNM console runtime -- the device that plays the active cartridge on a linear course of stations.
# Place ONE fnm_director in the level and fill its @editable Stations array (see console/README.md).
#
# Per player: own stage, own question, own HUD, own draw decks (PROTOCOL 6).
# Wrong door  -> that choice's Feedback on the HUD, teleport to the station's RetryTeleporter, same question.
# Right door  -> Explanation on the HUD for CorrectFeedbackSeconds, next question, teleport to NextTeleporter.
# After the last station -> first-try accuracy on the HUD (optionally activates an end_game_device).

using { /Fortnite.com/Devices }
using { /Verse.org/Colors }
using { /Verse.org/Simulation }

# One question station. Doors are listed in A, B, C, D order (2-4 doors).
fnm_station := class<concrete>:
    # trigger_devices for the doors, in order A, B, C, D.
    @editable
    Doors : []trigger_device = array{}

    # Where a player is sent after a wrong answer (in front of this station's doors).
    @editable
    RetryTeleporter : teleporter_device = teleporter_device{}

    # Where a player is sent after a right answer: the next station's start
    # (for the last station: the finish area).
    @editable
    NextTeleporter : teleporter_device = teleporter_device{}

    # Difficulty position in percent, 0 (easiest tier) .. 100 (hardest tier).
    # -1 = automatic: spread evenly from first station (easiest) to last (hardest).
    @editable
    DifficultyOverride : int = -1

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
    @editable
    Stations : []fnm_station = array{}

    # Seconds the wrong-answer feedback stays on the HUD (the player is teleported back immediately).
    @editable
    WrongFeedbackSeconds : float = 4.0

    # Seconds the explanation shows before the player moves on to the next station.
    @editable
    CorrectFeedbackSeconds : float = 3.0

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
    var TierCount : int = 0
    var TierPools : [][]int = array{}
    var PlayerStates : [player]fnm_player_state = map{}
    var Ready : logic = false

    OnBegin<override>()<suspends>:void =
        set Cartridge = FnmActiveCartridge()
        set TierCount = Cartridge.Tiers.Length
        set TierPools = FnmBuildTierPools(Cartridge.Items, TierCount)
        if (Stations.Length = 0):
            Print("FNM: fnm_director has no Stations configured.")
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
                Generation := State.Hud.ShowFeedback("Correct!  " + Item.Explanation, NamedColors.LightGreen)
                Sleep(CorrectFeedbackSeconds)
                if (State.Player.IsActive[], not State.Finished?):
                    State.Hud.ClearFeedbackIf(Generation)
                    AdvancePlayer(State, Station)
                set State.Busy = false
            else:
                set State.MissedCurrent = true
                Generation := State.Hud.ShowFeedback(FeedbackFor(Item, DoorIndex), NamedColors.Tomato)
                Station.RetryTeleporter.Teleport(State.Player)
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
        Station.NextTeleporter.Teleport(State.Player)

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
