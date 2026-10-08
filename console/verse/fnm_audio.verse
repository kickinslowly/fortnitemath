# FNM console runtime -- the sound layer. One Creative audio player per cue (tools/build_audio.py places them, parked
# underground, Verse-tagged fnm_cue_<id> (fnm_tags.verse), heard by the instigating player only, non-spatial). The
# director builds one fnm_audio at OnBegin; it finds the players by tag, and every Play logs "FNM: cue <id>" so a
# play log proves the wiring. A cue with no device (no library sound yet, e.g. the announcer lines) is a logged
# no-op. Ids and tags are shared with the announcer pack: keep every member even where nothing is wired.

using { /Fortnite.com/Devices }
using { /Verse.org/Simulation }
using { /Verse.org/Simulation/Tags }

fnm_cue := enum:
    # countdown beat 3
    Countdown3
    # countdown beat 2
    Countdown2
    # countdown beat 1
    Countdown1
    # GO!
    Go
    # right door, first try
    Correct
    # right door after a miss
    CorrectRetry
    # wrong door
    Wrong
    # the barrier opens for the player
    DoorOpen
    # a speed boost starts
    Boost
    # first-try streak milestones 2..7 (7 repeats above 7)
    Streak2
    Streak3
    Streak4
    Streak5
    Streak6
    Streak7
    # finish with every answer first try
    Perfect
    # crossing the finish
    Finish
    # new personal best
    NewBest
    # new island record
    NewRecord
    # medal at the finish
    MedalGold
    MedalSilver
    MedalBronze
    # each penalty as its effect starts
    PenaltyFreeze
    PenaltySpike
    PenaltyMud
    PenaltyDizzy
    PenaltyBlackout
    PenaltyYeet
    # the skip guard sends a player back
    NoSkip
    # a station's guards switch on
    GuardsUp
    # a player joins
    Welcome
    # the skill picker opens (once per join)
    Choose
    # music bed per tier (loops; Stop on change/finish/picker)
    MusicT1
    MusicT2
    MusicT3
    MusicT4
    MusicT5
    # the boss arena: entering it, a right pad (a hit), the kill
    BossFight
    BossHit
    BossDead
    # the announcer on a boss hit: "Direct hit!" alone, or with the team's hits still to go (4..1), and the kill
    DirectHit
    HitsLeft4
    HitsLeft3
    HitsLeft2
    HitsLeft1
    BossDown

# Every cue, in enum order (FnmCueIds and FnmCueTags follow the same order).
FnmCues()<transacts>:[]fnm_cue = array{fnm_cue.Countdown3, fnm_cue.Countdown2, fnm_cue.Countdown1, fnm_cue.Go, fnm_cue.Correct, fnm_cue.CorrectRetry, fnm_cue.Wrong, fnm_cue.DoorOpen, fnm_cue.Boost, fnm_cue.Streak2, fnm_cue.Streak3, fnm_cue.Streak4, fnm_cue.Streak5, fnm_cue.Streak6, fnm_cue.Streak7, fnm_cue.Perfect, fnm_cue.Finish, fnm_cue.NewBest, fnm_cue.NewRecord, fnm_cue.MedalGold, fnm_cue.MedalSilver, fnm_cue.MedalBronze, fnm_cue.PenaltyFreeze, fnm_cue.PenaltySpike, fnm_cue.PenaltyMud, fnm_cue.PenaltyDizzy, fnm_cue.PenaltyBlackout, fnm_cue.PenaltyYeet, fnm_cue.NoSkip, fnm_cue.GuardsUp, fnm_cue.Welcome, fnm_cue.Choose, fnm_cue.MusicT1, fnm_cue.MusicT2, fnm_cue.MusicT3, fnm_cue.MusicT4, fnm_cue.MusicT5, fnm_cue.BossFight, fnm_cue.BossHit, fnm_cue.BossDead, fnm_cue.DirectHit, fnm_cue.HitsLeft4, fnm_cue.HitsLeft3, fnm_cue.HitsLeft2, fnm_cue.HitsLeft1, fnm_cue.BossDown}

# Snake-case id per cue, enum order: the Verse tag is fnm_cue_<id> (tools/build_audio.py CUES keys).
FnmCueIds()<transacts>:[]string = array{"countdown3", "countdown2", "countdown1", "go", "correct", "correct_retry", "wrong", "door_open", "boost", "streak2", "streak3", "streak4", "streak5", "streak6", "streak7", "perfect", "finish", "new_best", "new_record", "medal_gold", "medal_silver", "medal_bronze", "penalty_freeze", "penalty_spike", "penalty_mud", "penalty_dizzy", "penalty_blackout", "penalty_yeet", "no_skip", "guards_up", "welcome", "choose", "music_t1", "music_t2", "music_t3", "music_t4", "music_t5", "boss_fight", "boss_hit", "boss_dead", "direct_hit", "hits_left4", "hits_left3", "hits_left2", "hits_left1", "boss_down"}

# The announcer's line for a boss hit that leaves Left team hits to go: a counted line for 1..4, "Direct hit!" otherwise.
FnmHitCue(Left:int)<transacts>:fnm_cue =
    if (Left = 4) then fnm_cue.HitsLeft4
    else if (Left = 3) then fnm_cue.HitsLeft3
    else if (Left = 2) then fnm_cue.HitsLeft2
    else if (Left = 1) then fnm_cue.HitsLeft1
    else fnm_cue.DirectHit

FnmCueIndex(Cue:fnm_cue)<transacts>:int =
    var Found : int = -1
    for (K -> Each : FnmCues(), Each = Cue):
        set Found = K
    Found

FnmCueId(Cue:fnm_cue)<transacts>:string =
    if (Id := FnmCueIds()[FnmCueIndex(Cue)]) then Id else "unknown"

# The Verse tag name that marks this cue's audio player: fnm_cue_countdown3, fnm_cue_correct_retry, ...
FnmCueTag(Cue:fnm_cue)<transacts>:string = "fnm_cue_" + FnmCueId(Cue)

# The music bed cue for tier Tier (1..5); false outside that range.
FnmMusicCue(Tier:int)<transacts>:?fnm_cue =
    if (Tier = 1) then option{fnm_cue.MusicT1}
    else if (Tier = 2) then option{fnm_cue.MusicT2}
    else if (Tier = 3) then option{fnm_cue.MusicT3}
    else if (Tier = 4) then option{fnm_cue.MusicT4}
    else if (Tier = 5) then option{fnm_cue.MusicT5}
    else false

# The streak milestone cue after a first-try right answer: Streak2..Streak7 for a streak of 2..7, Streak7 again above.
FnmStreakCue(Streak:int)<transacts>:?fnm_cue =
    if (Streak = 2) then option{fnm_cue.Streak2}
    else if (Streak = 3) then option{fnm_cue.Streak3}
    else if (Streak = 4) then option{fnm_cue.Streak4}
    else if (Streak = 5) then option{fnm_cue.Streak5}
    else if (Streak = 6) then option{fnm_cue.Streak6}
    else if (Streak >= 7) then option{fnm_cue.Streak7}
    else false

fnm_audio := class:
    # The device whose tag search finds the players (the director).
    Owner : creative_device
    # Per cue, enum order: its audio player, if one is placed.
    var Devices : []?audio_player_device = array{}
    # Per player: the music bed tier playing for them (0 = none).
    var MusicTier : [player]int = map{}

    # Finds one audio player per cue by its fnm_cue_<id> tag and logs how many cues are wired.
    Build():void =
        CueTags := FnmCueTags()
        set Devices = for (K -> Cue : FnmCues()):
            var Found : ?audio_player_device = false
            if (CueTag := CueTags[K]):
                for (Object : Owner.FindCreativeObjectsWithTag(CueTag), Device := audio_player_device[Object]):
                    set Found = option{Device}
            Found
        var Wired : int = 0
        var Missing : string = ""
        for (K -> MaybeDevice : Devices):
            if (MaybeDevice?):
                set Wired += 1
            else if (Id := FnmCueIds()[K]):
                set Missing += if (Missing = "") then Id else ", {Id}"
        Print("FNM: audio: {Wired} of {Devices.Length} cues wired, missing: {if (Missing = "") then "none" else Missing}")

    DeviceFor(Cue:fnm_cue)<transacts>:?audio_player_device =
        if (Found := Devices[FnmCueIndex(Cue)]) then Found else false

    # Plays Cue for Player only (a no-op when the cue has no device). Always logged.
    Play(Player:player, Cue:fnm_cue):void =
        if (Device := DeviceFor(Cue)?):
            Device.Play(Player)
            Print("FNM: cue {FnmCueId(Cue)}")
        else:
            Print("FNM: cue {FnmCueId(Cue)} (not wired)")

    Stop(Player:player, Cue:fnm_cue):void =
        if (Device := DeviceFor(Cue)?):
            Device.Stop(Player)
        Print("FNM: cue stop {FnmCueId(Cue)}")

    # A whole-island moment: Cue for every player present.
    PlayAll(Cue:fnm_cue):void =
        for (Player : Owner.GetPlayspace().GetPlayers()):
            Play(Player, Cue)

    # The music bed for Player follows their station tier: stops the old tier's bed and plays tier Tier's (0 = silence).
    # Nothing happens when the tier is unchanged.
    SetMusic(Player:player, Tier:int):void =
        Old := if (Playing := MusicTier[Player]) then Playing else 0
        if (Old <> Tier):
            if (OldCue := FnmMusicCue(Old)?):
                Stop(Player, OldCue)
            if (NewCue := FnmMusicCue(Tier)?):
                Play(Player, NewCue)
            if (set MusicTier[Player] = Tier) {}

    # A player left: forget their music.
    Forget(Player:player):void =
        var Remaining : [player]int = map{}
        for (Key -> Value : MusicTier, Key <> Player):
            if (set Remaining[Key] = Value) {}
        set MusicTier = Remaining
