# FNM console runtime -- BOSS BATTLE mode (BOSS_MODE.md is the spec). A dedicated arena east of the course
# (tools/build_bossmode.py, Verse tags fnm_bm_*): a player who picks BOSS BATTLE on the picker's grade step answers
# questions from EVERY baked cartridge by stepping on one of four answer pads. A right pad is a MEGA NUKE on a shared
# boss (wall lasers, a strike, a nuke, a white flash); five levels of 2/3/3/4/4 team hits; at each level start the boss
# summons monsters through more and more gates in the walls and a weapon drops on a perch the player must jump up to.
# No lose state: an eliminated player comes back at the arena entry (counted). The director (fnm_director.verse) owns
# the players and routes picks, pads, perches, respawns and the finish here when a player's Mode is Boss; this file
# owns the level table, the arena's devices and the shared fight (one boss and one level for everyone in the mode).

using { /Fortnite.com/Characters }
using { /Fortnite.com/Devices }
using { /UnrealEngine.com/Temporary/SpatialMath }
using { /Verse.org/Colors }
using { /Verse.org/Random }
using { /Verse.org/Simulation }
using { /Verse.org/Simulation/Tags }

# ---------------------------------------------------------------- the level table (BOSS_MODE.md section 4)

# One level: team hits to clear it, seconds between monster spawns, gates active, monsters alive at most (all gates),
# the boss's anger label, the banner's sub line, the perches (1..4) where its weapon drops, the weapon's name.
fnm_bm_level := struct:
    Hits : int
    SpawnSeconds : float
    Gates : int
    MaxAlive : int
    Anger : string
    Banner : string
    Perches : []int
    WeaponName : string

FnmBmLevels()<transacts>:[]fnm_bm_level = array:
    fnm_bm_level{Hits := 2, SpawnSeconds := 20.0, Gates := 1, MaxAlive := 2, Anger := "GRUMPY", Banner := "HERE HE COMES!", Perches := array{1}, WeaponName := "SMG"}
    fnm_bm_level{Hits := 3, SpawnSeconds := 15.0, Gates := 2, MaxAlive := 3, Anger := "ANGRY", Banner := "HE'S ANGRY!", Perches := array{2}, WeaponName := "Pump Shotgun"}
    fnm_bm_level{Hits := 3, SpawnSeconds := 12.0, Gates := 3, MaxAlive := 4, Anger := "FURIOUS", Banner := "HE'S FURIOUS!", Perches := array{3}, WeaponName := "Assault Rifle"}
    fnm_bm_level{Hits := 4, SpawnSeconds := 9.0, Gates := 4, MaxAlive := 5, Anger := "RAGING", Banner := "HE'S RAGING!", Perches := array{4}, WeaponName := "Heavy Sniper"}
    fnm_bm_level{Hits := 4, SpawnSeconds := 7.0, Gates := 4, MaxAlive := 6, Anger := "UNHINGED", Banner := "FINAL LEVEL. UNHINGED!", Perches := array{3, 4}, WeaponName := "Rocket Launcher"}

FnmBmLevelCount()<transacts>:int = 5

# Level L's row, L clamped to 1..5.
FnmBmLevel(L:int)<transacts>:fnm_bm_level =
    Levels := FnmBmLevels()
    if (Row := Levels[Clamp(L, 1, Levels.Length) - 1]) then Row
    else fnm_bm_level{Hits := 1, SpawnSeconds := 20.0, Gates := 1, MaxAlive := 2, Anger := "", Banner := "", Perches := array{}, WeaponName := ""}

FnmBmPerchesFor(L:int)<transacts>:[]int = FnmBmLevel(L).Perches
FnmBmWeaponName(L:int)<transacts>:string = FnmBmLevel(L).WeaponName
FnmBmBannerSub(L:int)<transacts>:string = FnmBmLevel(L).Banner

# Perch P (1..4) as the HUD names it. The player enters facing +Y, so +X is their LEFT (BOSS_MODE.md section 3).
FnmBmPerchName(P:int)<transacts>:string =
    if (P = 1) then "FRONT-RIGHT PERCH"
    else if (P = 2) then "FRONT-LEFT PERCH"
    else if (P = 3) then "BACK-RIGHT PERCH"
    else if (P = 4) then "BACK-LEFT PERCH"
    else ""

# Where level L's weapon drops, for the hint and the log: the perch's name, or "BACK PERCHES" when it is on both.
FnmBmPerchHint(L:int)<transacts>:string =
    Perches := FnmBmPerchesFor(L)
    if (Perches.Length > 1) then "BACK PERCHES"
    else if (P := Perches[0]) then FnmBmPerchName(P)
    else ""

# The boss's line at level L's summon (subtitle; the voice is cue bm_boss_l{L}, FnmBmBossCue in fnm_audio.verse).
FnmBmBossLineText(L:int)<transacts>:string =
    if (L = 2) then "Minions! GET THEM!"
    else if (L = 3) then "Is that all you've got?!"
    else if (L = 4) then "Now I'm ANGRY!"
    else if (L >= 5) then "NO MORE GAMES! EVERYONE, ATTACK!"
    else "You dare challenge ME?!"

# Whole seconds for log lines (a float interpolates with decimals).
FnmBmWholeSeconds(Seconds:float)<transacts>:int =
    if (R := Round[Seconds]) then R else 0

# The id boss-mode bests are saved under (fnm_save.verse; never a cartridge id).
FnmBmSaveId : string = "boss-battle"

# Public feed lines (fnm_director Broadcast) for the mode.
FnmFeedBmJoin<localizes>(Who:agent):message = "{Who} joined the BOSS BATTLE!"
FnmFeedBmHit<localizes>(Who:agent, Level:int, Team:int, Need:int):message = "{Who} nuked the boss!  Level {Level}: {Team}/{Need}"
FnmFeedBmWrong<localizes>(Who:agent, Past:string):message = "{Who} got {Past}  -  BOSS: HA! WRONG!"
FnmFeedBmWeapon<localizes>(Who:agent, Weapon:string):message = "{Who} grabbed the {Weapon}!"
FnmFeedBmFinal<localizes>(Who:agent):message = "{Who} landed the final MEGA NUKE!"
FnmFeedBmClear<localizes>(Level:int):message = "LEVEL {Level} CLEARED!"

# ---------------------------------------------------------------- devices

# A set of laser cannons and what they fire (tools/build_cannon.py): the muzzle VFX spawners, the strike VFX moved onto
# the target and its parked transform, the explosive devices parked under the platform, and (boss mode only) the nuke
# VFX. The race arena's rig has no nuke; fnm_director FireCannons fires either.
fnm_cannon_rig := class:
    Fx : []vfx_spawner_device
    Strike : ?vfx_spawner_device
    StrikeHome : ?transform
    Blasts : fnm_rig
    Nuke : ?vfx_spawner_device

# Binds one answer pad of the boss-mode arena to its letter (0 = A), so one callback serves all four.
fnm_bm_pad_handler := class:
    Director : fnm_director
    DoorIndex : int

    OnTriggered(MaybeAgent:?agent):void =
        Director.OnBmPad(MaybeAgent, DoorIndex)

# Binds one perch's hidden trigger to its number (1..4).
fnm_bm_perch_handler := class:
    Director : fnm_director
    Perch : int

    OnTriggered(MaybeAgent:?agent):void =
        Director.OnBmPerch(MaybeAgent, Perch)

# The boss-mode arena, found by tag at OnBegin. Station: the arena seen as a station (pads as doors, the entry as the
# retry point), so the director's answer and penalty code serve it unchanged. Numbered pieces sit at index slot - 1:
# a boss spawner per level (5), a monster gate's spawner and lightning per gate (4), a perch's trigger and beacon per
# perch (4), a weapon granter's hidden trigger per level (5), an anger-ring VFX per level (5).
fnm_bm_arena := class:
    Station : fnm_station
    var BossSpawners : []?guard_spawner_device = array{false, false, false, false, false}
    var Gates : []?guard_spawner_device = array{false, false, false, false}
    var GateFx : []?vfx_spawner_device = array{false, false, false, false}
    var PerchTriggers : []?trigger_device = array{false, false, false, false}
    var PerchFx : []?vfx_spawner_device = array{false, false, false, false}
    var GrantTriggers : []?trigger_device = array{false, false, false, false, false}
    var AngerFx : []?vfx_spawner_device = array{false, false, false, false, false}
    var Rig : fnm_cannon_rig = fnm_cannon_rig{Fx := array{}, Strike := false, StrikeHome := false, Blasts := fnm_rig{Name := "bm_blast", Parts := array{}, Homes := array{}}, Nuke := false}

    # Which fnm_bm_slot_N an object carries (1..5), -1 for none (like fnm_director DoorLetter).
    SlotOf(Object:creative_object_interface)<transacts>:int =
        ObjectTags := Object.GetTags()
        if (ObjectTags.Has[fnm_bm_slot_1{}]) then 1
        else if (ObjectTags.Has[fnm_bm_slot_2{}]) then 2
        else if (ObjectTags.Has[fnm_bm_slot_3{}]) then 3
        else if (ObjectTags.Has[fnm_bm_slot_4{}]) then 4
        else if (ObjectTags.Has[fnm_bm_slot_5{}]) then 5
        else -1

    # Finds every tagged piece; spawners and VFX are switched off until the fight needs them.
    Find(Director:fnm_director):void =
        for (Object : Director.FindCreativeObjectsWithTag(fnm_bm_boss), Spawner := guard_spawner_device[Object]):
            Spawner.Disable()
            if (set BossSpawners[SlotOf(Object) - 1] = option{Spawner}) {}
        for (Object : Director.FindCreativeObjectsWithTag(fnm_bm_gate), Spawner := guard_spawner_device[Object]):
            Spawner.Disable()
            if (set Gates[SlotOf(Object) - 1] = option{Spawner}) {}
        for (Object : Director.FindCreativeObjectsWithTag(fnm_bm_gate_fx), Fx := vfx_spawner_device[Object]):
            Fx.Disable()
            if (set GateFx[SlotOf(Object) - 1] = option{Fx}) {}
        for (Object : Director.FindCreativeObjectsWithTag(fnm_bm_perch), Trigger := trigger_device[Object]):
            if (set PerchTriggers[SlotOf(Object) - 1] = option{Trigger}) {}
        for (Object : Director.FindCreativeObjectsWithTag(fnm_bm_perch_fx), Fx := vfx_spawner_device[Object]):
            Fx.Disable()
            if (set PerchFx[SlotOf(Object) - 1] = option{Fx}) {}
        for (Object : Director.FindCreativeObjectsWithTag(fnm_bm_grant), Trigger := trigger_device[Object]):
            if (set GrantTriggers[SlotOf(Object) - 1] = option{Trigger}) {}
        for (Object : Director.FindCreativeObjectsWithTag(fnm_bm_anger_fx), Fx := vfx_spawner_device[Object]):
            Fx.Disable()
            if (set AngerFx[SlotOf(Object) - 1] = option{Fx}) {}
        var CannonFx : []vfx_spawner_device = array{}
        for (Object : Director.FindCreativeObjectsWithTag(fnm_bm_cannon_fx), Fx := vfx_spawner_device[Object]):
            Fx.Disable()
            set CannonFx += array{Fx}
        var Strike : ?vfx_spawner_device = false
        var StrikeHome : ?transform = false
        for (Object : Director.FindCreativeObjectsWithTag(fnm_bm_strike), Fx := vfx_spawner_device[Object]):
            Fx.Disable()
            set Strike = option{Fx}
            set StrikeHome = option{Fx.GetTransform()}
        var Nuke : ?vfx_spawner_device = false
        for (Object : Director.FindCreativeObjectsWithTag(fnm_bm_nuke_fx), Fx := vfx_spawner_device[Object]):
            Fx.Disable()
            set Nuke = option{Fx}
        set Rig = fnm_cannon_rig{Fx := CannonFx, Strike := Strike, StrikeHome := StrikeHome, Blasts := Director.BuildRig("bm_blast", fnm_bm_blast), Nuke := Nuke}

    CountSpawners(Items:[]?guard_spawner_device):int =
        var Count : int = 0
        for (Item : Items, Item?):
            set Count += 1
        Count

    CountTriggers(Items:[]?trigger_device):int =
        var Count : int = 0
        for (Item : Items, Item?):
            set Count += 1
        Count

    CountFx(Items:[]?vfx_spawner_device):int =
        var Count : int = 0
        for (Item : Items, Item?):
            set Count += 1
        Count

# ---------------------------------------------------------------- the mode

# The shared fight: one Level (0 = idle), one boss, one set of monsters for every player whose Mode is Boss. Built by the
# director at OnBegin when the map has an fnm_bm entry teleporter.
fnm_boss_mode := class:
    Director : fnm_director
    Arena : fnm_bm_arena
    var Level : int = 0
    var TeamHits : int = 0
    var BossAlive : logic = false
    var BossAgent : ?agent = false
    # When a boss was asked for (-1 = none pending): a spawn that has not come after BossNudgeSeconds gets a Spawn().
    var BossRequestedAt : float = -1.0
    # Monsters up (the gate spawners' SpawnedEvent minus EliminatedEvent; zeroed when the gates close).
    var AliveMonsters : int = 0
    var NextSpawnAt : float = 0.0
    var GateCursor : int = 0
    var GatesOpen : int = 0
    var Summoning : logic = false
    var LevelDownAt : float = -100.0
    # Bumped by ResetShared, so a summon or a level change in flight from an older fight stops itself.
    var Epoch : int = 0
    var LastHitter : ?player = false
    # The perches whose beacon is lit (the current level's), and when the beacons are restarted next.
    var LitPerches : []int = array{}
    var BeaconAt : float = 0.0
    var LastGunHint : [player]float = map{}
    RefreshSeconds : float = 0.25
    SpawnCheckSeconds : float = 0.5
    BossNudgeSeconds : float = 5.0
    BeaconSeconds : float = 2.0
    GateFxSeconds : float = 1.5
    # Seconds the boss line, the weapon hint and the start hint stay on the feedback line.
    LineSeconds : float = 6.0
    StartFlashSeconds : float = 4.0
    LevelClearSeconds : float = 2.5
    WeaponGetSeconds : float = 1.5
    # A wrong-answer wave may go this many over the level's alive cap.
    WaveExtra : int = 2
    # Voice timings after a pad: the boss's grunt, and (wrong pad) its taunt after the penalty's own voice line (which
    # comes PenaltyVoiceDelaySeconds after the buzzer); a streak line after the hit count; the death cry after the kill.
    BossGruntSeconds : float = 0.4
    TauntDelaySeconds : float = 2.5
    StreakCueDelaySeconds : float = 2.3
    BossDeadSeconds : float = 0.5

    # Finds the arena's devices, subscribes the spawners' events and logs what was found.
    Build():void =
        Arena.Find(Director)
        for (MaybeSpawner : Arena.BossSpawners, Spawner := MaybeSpawner?):
            Spawner.SpawnedEvent.Subscribe(OnBossSpawned)
            Spawner.EliminatedEvent.Subscribe(OnBossEliminated)
            Spawner.DamagedEvent.Subscribe(OnBossDamaged)
        for (MaybeSpawner : Arena.Gates, Spawner := MaybeSpawner?):
            Spawner.SpawnedEvent.Subscribe(OnMonsterSpawned)
            Spawner.EliminatedEvent.Subscribe(OnMonsterEliminated)
        Print("FNM: boss mode: arena found: {Arena.Station.Doors.Length} pads, {Arena.CountSpawners(Arena.Gates)} gates, {Arena.CountTriggers(Arena.PerchTriggers)} perches, {Arena.CountSpawners(Arena.BossSpawners)} boss spawners, {Arena.CountTriggers(Arena.GrantTriggers)} granters, {Arena.Rig.Fx.Length} cannons")
        Print("FNM: boss mode: fx {Arena.CountFx(Arena.GateFx)} gate, {Arena.CountFx(Arena.PerchFx)} perch, {Arena.CountFx(Arena.AngerFx)} anger, strike {FnmYesNo(if (Arena.Rig.Strike?) then true else false)}, nuke {FnmYesNo(if (Arena.Rig.Nuke?) then true else false)}, {Arena.Rig.Blasts.Parts.Length} blasts")

    # Every player fighting in the mode (not picking, not finished).
    Fighting()<transacts>:[]fnm_player_state =
        for (State : Director.PlayerStates, State.Mode = fnm_mode.Boss, not State.Finished?, not State.Picking?) { State }

    Fighters()<transacts>:int = Fighting().Length

    BossSpawnerFor(L:int)<transacts>:?guard_spawner_device =
        if (Found := Arena.BossSpawners[L - 1]) then Found else false

    # ------------------------------------------------ joining and leaving

    # BOSS BATTLE picked (or PLAY AGAIN, or DebugAutoBoss): the player joins the fight at its current level, or starts
    # a fresh one at level 1 (DebugBossLevel on their first start) when nobody is fighting. Questions from every
    # cartridge, the arena entry, the loadout, the clock (no 3-2-1: the fight may be on already).
    Start(State:fnm_player_state):void =
        WasEmpty := if (Fighters() = 0 or Level < 1) then true else false
        set State.Picks += 1
        FirstStart := if (State.Picks = 1) then true else false
        if (WasEmpty?):
            ResetShared()
            set Level = if (FirstStart?, Director.DebugBossLevel > 1) then Min(Director.DebugBossLevel, FnmBmLevelCount()) else 1
        set State.Mode = fnm_mode.Boss
        set State.Picking = false
        set State.Finished = false
        set State.Busy = false
        # A run that does not start at level 1 (DebugBossLevel, or joining a fight past level 1) is never saved or boarded.
        set State.Partial = if (Level > 1) then true else false
        set State.Stage = 0
        set State.Level = Level
        set State.Hits = 0
        set State.Deaths = 0
        set State.Answered = 0
        set State.FirstTryCorrect = 0
        set State.Streak = 0
        set State.BestStreak = 0
        set State.TakenLevels = map{}
        set State.RunGeneration += 1
        set State.BmDecks = for (Pools : Director.CartridgePools) { FnmShuffleAll(Pools) }
        set State.BossBest = if (Saved := FnmSavedBest[State.Player, FnmBmSaveId], (State.BossBest < 0.0 or Saved < State.BossBest)) then Saved else State.BossBest
        State.Hud.HidePicker()
        State.Hud.HideResults()
        State.Hud.HideFinishButtons()
        State.Hud.HideBanner()
        State.Hud.SetCountdown("")
        State.Hud.SetTarget("")
        State.Hud.ClearDelta()
        State.Hud.SetStreak("")
        State.Hud.SetTitle("BOSS BATTLE", "Every skill, every grade")
        DrawBmItem(State)
        Director.ShowCurrent(State)
        if (Character := State.Player.GetFortCharacter[]):
            Character.ReleaseFromStasis()
        Director.SendTo(State.Player, Arena.Station.RetryTeleporter)
        Director.GiveLoadout(State.Player)
        Director.SetMusic(State.Player, Level)
        State.Hud.FlashBig("STEP ON THE RIGHT ANSWER!", NamedColors.Gold, StartFlashSeconds)
        spawn{ ShowLine(State, "Bullets can't hurt the boss. Step on the pad with the RIGHT ANSWER to nuke it!", NamedColors.Orange, LineSeconds) }
        set State.StartTime = GetSimulationElapsedTime()
        spawn{ BmClock(State) }
        Director.Broadcast(FnmFeedBmJoin(State.Player), "joined the BOSS BATTLE")
        Print("FNM: boss mode start for the player (level {Level})")
        if (WasEmpty?):
            spawn{ Summon(Level) }
        if (FirstStart?):
            if (Director.DebugAutoRightAnswers?):
                spawn{ Director.DebugBossModeRun(State) }
            if (Director.DebugAutoWrongAnswers > 0):
                spawn{ Director.DebugAutoWrong(State) }

    # The player leaves the mode (CHANGE SKILL, leaving the island): back to Race; their boss line and banner go. The
    # fight resets itself once nobody is left (BossLoop).
    Leave(State:fnm_player_state):void =
        if (State.Mode = fnm_mode.Boss):
            set State.Mode = fnm_mode.Race
            set State.Level = 0
            set State.RunGeneration += 1
            set State.StartTime = -1.0
            State.Hud.ClearBoss()
            set State.BossShown = false
            State.Hud.HideBanner()
            Print("FNM: boss mode: the player left ({Fighters()} still fighting)")

    # An eliminated boss-mode player is back: the arena entry, the loadout, counted (not for a Spike penalty's own death,
    # which happens while the answer is still being processed).
    Respawned(State:fnm_player_state):void =
        Director.SendTo(State.Player, Arena.Station.RetryTeleporter)
        Director.GiveLoadout(State.Player)
        if (not State.Busy?, not State.Finished?):
            set State.Deaths += 1
            spawn{ Director.FlashNotice(State, "Knocked out! Back to the arena entry.") }
        Print("FNM: boss mode respawn at the arena entry (knocked out {State.Deaths}x)")

    # The race clock for a boss-mode run (no countdown): runs until the finish, a new start or leaving the mode.
    BmClock(State:fnm_player_state)<suspends>:void =
        Generation := State.RunGeneration
        loop:
            if (State.RunGeneration <> Generation or State.StartTime < 0.0 or State.Finished? or State.Mode <> fnm_mode.Boss) then break
            State.Hud.SetClock(FnmClock(GetSimulationElapsedTime() - State.StartTime))
            Sleep(0.1)

    # A line on the player's feedback row for Seconds (cleared only if nothing newer replaced it).
    ShowLine(State:fnm_player_state, Text:string, TextColor:color, Seconds:float)<suspends>:void =
        Shown := State.Hud.ShowFeedback(Text, TextColor)
        Sleep(Seconds)
        State.Hud.ClearFeedbackIf(Shown)

    # ------------------------------------------------ questions (BOSS_MODE.md section 2)

    # The next question: a cartridge at random, the tier the level maps to (PROTOCOL 6 with Stage = level, 5 stages), a
    # draw from the player's own deck for that cartridge and tier. Everything downstream reads State.Cartridge.
    DrawBmItem(State:fnm_player_state):void =
        Carts := Director.Cartridges
        var Tries : int = 0
        var Drawn : logic = false
        loop:
            if (Tries >= 8 or Carts.Length = 0) then break
            set Tries += 1
            C := GetRandomInt(0, Carts.Length - 1)
            if (Chosen := Carts[C], Pools := Director.CartridgePools[C], Decks := State.BmDecks[C]):
                Tier := FnmTierForStage(Max(State.Level, 1), FnmBmLevelCount(), Chosen.Tiers.Length, -1)
                if (Pool := Pools[Tier - 1], Deck := Decks[Tier - 1]):
                    Draw := FnmDraw(Deck, Pool)
                    if (Item := Chosen.Items[Draw.ItemIndex]):
                        NewDecks := for (K -> Each : Decks) { if (K = Tier - 1) then Draw.Rest else Each }
                        if (set State.BmDecks[C] = NewDecks) {}
                        set State.CartridgeIndex = C
                        set State.Cartridge = Chosen
                        set State.TierCount = Chosen.Tiers.Length
                        set State.TierPools = Pools
                        set State.CurrentItem = Draw.ItemIndex
                        set State.MissedCurrent = false
                        set State.Order = Shuffle(for (Index := 0..Item.Choices.Length - 1) { Index })
                        set Drawn = true
                        break
        if (not Drawn?):
            Print("FNM: boss mode: no question drawn after {Tries} tries")

    # ------------------------------------------------ pads and perches (BOSS_MODE.md section 7)

    # A pad answered (the director set Busy, as OnDoor does): right = a MEGA NUKE, wrong = the penalty and a wave.
    OnPad(State:fnm_player_state, DoorIndex:int)<suspends>:void =
        if (Item := State.Cartridge.Items[State.CurrentItem]):
            Choice := Director.ChoiceAt(State, DoorIndex)
            if (Choice < 0):
                set State.Busy = false
                Director.FlashNotice(State, "No choice {FnmChoiceLetter(DoorIndex)} here")
            else if (Choice = Item.Answer):
                Hit(State)
                set State.Busy = false
                if (not State.Finished?):
                    Shown := State.Hud.ShowFeedback("Correct!  " + Item.Explanation, NamedColors.LightGreen)
                    Sleep(Director.CorrectFeedbackSeconds)
                    State.Hud.ClearFeedbackIf(Shown)
            else:
                Wrong(State, Item, Choice, DoorIndex)
        else:
            set State.Busy = false

    # A right pad: first-try bookkeeping (streak, cues, boost, feed milestones, as HandleDoor), then one team hit on the
    # boss with the whole show, the player back to the entry, the next question. The kill itself comes through the
    # boss spawner's EliminatedEvent (LevelCleared).
    Hit(State:fnm_player_state):void =
        set State.Answered += 1
        if (not State.MissedCurrent?):
            set State.FirstTryCorrect += 1
            set State.Streak += 1
            set State.BestStreak = Max(State.BestStreak, State.Streak)
            if (StreakCue := FnmStreakCue(State.Streak)?):
                spawn{ Director.SoundLater(State.Player, StreakCue, StreakCueDelaySeconds) }
            spawn{ Director.Boost(State, Min(Director.MaxBoostSeconds, Director.BoostSeconds + Director.StreakBonusSeconds * (State.Streak - 1) * 1.0)) }
            for (Milestone : array{3, 5, 7, 10}, Milestone = State.Streak):
                Director.Broadcast(FnmFeedStreak(State.Player, Milestone), "is on a {Milestone} streak!")
        L := Level
        Need := FnmBmLevel(L).Hits
        if (L >= 1, BossAlive?, TeamHits < Need, Agent := BossAgent?, Character := Agent.GetFortCharacter[]):
            set TeamHits += 1
            set State.Hits += 1
            set LastHitter = option{State.Player}
            Left := Max(Need - TeamHits, 0)
            Stood := Character.GetTransform().Translation
            Amount := if (TeamHits >= Need) then Character.GetHealth() + Character.GetShield() + 100.0 else Character.GetMaxHealth() / (Max(Need, 1) * 1.0)
            Character.Damage(Amount)
            Print("FNM: boss mode hit {State.Hits} by the player (level {L}, team {TeamHits}/{Need}), damage {Amount}, health {BossPercent()}%")
            Label := if (Left > 0) then "MEGA NUKE!  {Left} TO GO" else if (L >= FnmBmLevelCount()) then "MEGA NUKE!  BOSS DEFEATED!" else "MEGA NUKE!  LEVEL {L} CLEARED!"
            State.Hud.FlashNuke(Label, Director.NukeSeconds)
            Director.Sound(State.Player, fnm_cue.BmNuke)
            if (Left > 0):
                spawn{ Director.SoundLater(State.Player, fnm_cue.BmBossHit, BossGruntSeconds) }
            spawn{ Director.SoundAfter(State.Player, FnmBmHitVoice(Left), Director.HitVoiceDelaySeconds) }
            Director.Broadcast(FnmFeedBmHit(State.Player, L, TeamHits, Need), "nuked the boss!  Level {L}: {TeamHits}/{Need}")
            # Back to the entry first, facing the boss: the show plays out ahead of them.
            Director.SendTo(State.Player, Arena.Station.RetryTeleporter)
            spawn{ Director.FireCannons(Arena.Rig, State.Player, Character, Stood, Left, true) }
        else:
            # Between levels (or before the first boss is up) a right answer counts for the player, not as a hit.
            Print("FNM: boss mode right answer by the player, but no boss is up (level {L})")
            Director.Sound(State.Player, fnm_cue.Correct)
            State.Hud.FlashVerdict(true, "")
            Director.SendTo(State.Player, Arena.Station.RetryTeleporter)
        if (not State.Finished?):
            DrawBmItem(State)
            Director.ShowCurrent(State)

    # A wrong pad: the normal penalty (back to the arena entry), a monster wave, the boss's taunt; same question again.
    Wrong(State:fnm_player_state, Item:fnm_item, Choice:int, DoorIndex:int)<suspends>:void =
        set State.MissedCurrent = true
        set State.Streak = 0
        Director.StopBoost(State)
        Kind := Director.PickPenalty()
        Past := FnmPenaltyPast(Kind)
        Director.Broadcast(FnmFeedBmWrong(State.Player, Past), "got {Past}  -  BOSS: HA! WRONG!")
        Director.Sound(State.Player, fnm_cue.Wrong)
        spawn{ Director.SoundLater(State.Player, fnm_cue.BmBossWrong, TauntDelaySeconds) }
        State.Hud.FlashVerdict(false, FnmPenaltyLabel(Kind))
        Shown := State.Hud.ShowFeedback(Director.FeedbackFor(Item, Choice), NamedColors.Tomato)
        Wave()
        Director.Punish(State.Player, Arena.Station, DoorIndex, Kind)
        set State.Busy = false
        Sleep(Director.WrongFeedbackSeconds)
        State.Hud.ClearFeedbackIf(Shown)

    # The wrong-answer wave: one Spawn() on every open gate while the alive count stays within the cap + WaveExtra.
    Wave():void =
        Cap := FnmBmLevel(Level).MaxAlive + WaveExtra
        var Spawned : int = 0
        for (K -> MaybeSpawner : Arena.Gates, K < GatesOpen, Spawner := MaybeSpawner?):
            if (AliveMonsters + Spawned < Cap):
                Spawner.Spawn()
                set Spawned += 1
        Print("FNM: boss mode wave: {Spawned} monsters spawned")

    # A player on perch P: when P is lit for the level and they have not taken this level's weapon, the level's granter
    # hands it over (its hidden trigger, fired for them).
    OnPerch(State:fnm_player_state, P:int):void =
        if (State.Mode = fnm_mode.Boss, not State.Finished?, not State.Picking?, Level >= 1):
            var Lit : logic = false
            for (Each : LitPerches, Each = P):
                set Lit = true
            Taken := if (Got := State.TakenLevels[Level], Got?) then true else false
            if (Lit?, not Taken?):
                Weapon := FnmBmWeaponName(Level)
                if (MaybeTrigger := Arena.GrantTriggers[Level - 1], Trigger := MaybeTrigger?):
                    Trigger.Trigger(State.Player)
                    if (set State.TakenLevels[Level] = true) {}
                    Director.Sound(State.Player, fnm_cue.BmWeapon)
                    State.Hud.FlashBig("{Weapon} GET!", NamedColors.Gold, WeaponGetSeconds)
                    Director.Broadcast(FnmFeedBmWeapon(State.Player, Weapon), "grabbed the {Weapon}!")
                    Print("FNM: boss mode weapon {Weapon} granted at perch {P} (level {Level})")
                else:
                    Print("FNM: boss mode perch {P}: no granter for level {Level}")

    # ------------------------------------------------ levels (BOSS_MODE.md sections 4 and 6)

    # Level L begins: about BmSummonSeconds of banner, announcer, anger ring, the boss, his line, the gates opening and
    # the weapon drop, seen and heard by every player in the mode.
    Summon(L:int)<suspends>:void =
        MyEpoch := Epoch
        Row := FnmBmLevel(L)
        Scale := Max(Director.BmSummonSeconds, 0.5) / 5.0
        set Summoning = true
        set Level = L
        set TeamHits = 0
        set BossRequestedAt = -1.0
        Print("FNM: boss level {L} summon")
        for (State : Fighting()):
            set State.Level = L
            State.Hud.ShowBanner("LEVEL {L}", Row.Banner)
            Director.SetMusic(State.Player, L)
            Director.Sound(State.Player, FnmBmLevelCue(L))
            Director.ShowCurrent(State)
        for (K -> MaybeFx : Arena.AngerFx, Fx := MaybeFx?):
            if (K < L):
                Fx.Enable()
                Fx.Restart()
            else:
                Fx.Disable()
        Sleep(0.8 * Scale)
        if (MyEpoch <> Epoch):
            return
        SpawnBoss(L)
        Sleep(0.7 * Scale)
        if (MyEpoch <> Epoch):
            return
        Line := FnmBmBossLineText(L)
        for (State : Fighting()):
            Director.Sound(State.Player, FnmBmBossCue(L))
            spawn{ ShowLine(State, "BOSS: {Line}", NamedColors.Orange, LineSeconds) }
        Sleep(1.0 * Scale)
        if (MyEpoch <> Epoch):
            return
        OpenGates(Row.Gates)
        for (State : Fighting()):
            Director.Sound(State.Player, fnm_cue.BmGates)
        Director.Broadcast(FnmText("The boss summons his minions!"), "The boss summons his minions!")
        spawn{ GateFxOff() }
        Sleep(1.5 * Scale)
        if (MyEpoch <> Epoch):
            return
        LightPerches(Row.Perches)
        Hint := FnmBmPerchHint(L)
        for (State : Fighting()):
            spawn{ ShowLine(State, "WEAPON DROP: {Hint} - jump up and grab it!", NamedColors.Gold, LineSeconds) }
        Sleep(1.0 * Scale)
        if (MyEpoch <> Epoch):
            return
        for (State : Director.PlayerStates, State.Mode = fnm_mode.Boss):
            State.Hud.HideBanner()
        set NextSpawnAt = GetSimulationElapsedTime() + Row.SpawnSeconds
        set Summoning = false
        Print("FNM: boss level {L} summoned: {Row.Gates} gates, every {FnmBmWholeSeconds(Row.SpawnSeconds)} s, max {Row.MaxAlive} alive, {Row.WeaponName} at {Hint}")

    # Asks level L's boss spawner for its boss (fresh spawn limit, enabled; SpawnedEvent confirms) with a strike at it.
    SpawnBoss(L:int):void =
        if (Spawner := BossSpawnerFor(L)?):
            set BossRequestedAt = GetSimulationElapsedTime()
            Spawner.Reset()
            Spawner.Enable()
            Print("FNM: boss mode boss requested (level {L})")
            spawn{ StrikeAt(Spawner.GetTransform().Translation) }
        else:
            Print("FNM: boss mode: no boss spawner for level {L}")

    # The strike VFX on the boss platform for a beat, then back to its parked spot.
    StrikeAt(At:vector3)<suspends>:void =
        if (Fx := Arena.Rig.Strike?):
            if (Fx.TeleportTo[At, MakeRotationFromYawPitchRollDegrees(0.0, 0.0, 0.0)]) {}
            Fx.Enable()
            Fx.Restart()
            Sleep(Director.CannonFlashSeconds)
            Fx.Disable()
            if (Home := Arena.Rig.StrikeHome?, Fx.TeleportTo[Home]) {}

    # Gates 1..Count: lightning at the mouth, the spawner fresh and on, the first monster out.
    OpenGates(Count:int):void =
        set GatesOpen = Min(Count, Arena.Gates.Length)
        for (K -> MaybeSpawner : Arena.Gates, K < GatesOpen):
            if (MaybeFx := Arena.GateFx[K], Fx := MaybeFx?):
                Fx.Enable()
                Fx.Restart()
            if (Spawner := MaybeSpawner?):
                Spawner.Reset()
                Spawner.Enable()
                Spawner.Spawn()
        Print("FNM: boss mode gates open: {GatesOpen}")

    GateFxOff()<suspends>:void =
        Sleep(GateFxSeconds)
        for (MaybeFx : Arena.GateFx, Fx := MaybeFx?):
            Fx.Disable()

    # Every gate shut: spawners off (their monsters despawn), lightning off, nobody counted alive.
    CloseGates():void =
        for (MaybeSpawner : Arena.Gates, Spawner := MaybeSpawner?):
            Spawner.Disable()
        for (MaybeFx : Arena.GateFx, Fx := MaybeFx?):
            Fx.Disable()
        set GatesOpen = 0
        set AliveMonsters = 0

    # The beacons on Perches on (BossLoop restarts them every BeaconSeconds), every other perch's off.
    LightPerches(Perches:[]int):void =
        set LitPerches = Perches
        set BeaconAt = GetSimulationElapsedTime() + BeaconSeconds
        for (K -> MaybeFx : Arena.PerchFx, Fx := MaybeFx?):
            var On : logic = false
            for (P : Perches, P = K + 1):
                set On = true
            if (On?):
                Fx.Enable()
                Fx.Restart()
            else:
                Fx.Disable()

    # The boss went down (its EliminatedEvent, or BossLoop's backstop): the level is cleared for everyone; the next one
    # is summoned BmRespawnSeconds later, or after level 5 it is the victory.
    LevelCleared():void =
        if (not BossAlive?):
            return
        L := Level
        set BossAlive = false
        set BossAgent = false
        set BossRequestedAt = -1.0
        set LevelDownAt = GetSimulationElapsedTime()
        if (Spawner := BossSpawnerFor(L)?):
            Spawner.Disable()
        CloseGates()
        Print("FNM: boss level {L} cleared")
        LastLevel := if (L >= FnmBmLevelCount()) then true else false
        for (State : Fighting()):
            Director.RefreshVitals(State.Player, L)
            if (not LastLevel?):
                Director.Sound(State.Player, fnm_cue.BmLevelClear)
                State.Hud.FlashBig("LEVEL {L} CLEARED!", NamedColors.Lime, LevelClearSeconds)
        if (LastLevel?):
            Victory()
        else:
            Director.Broadcast(FnmFeedBmClear(L), "LEVEL {L} CLEARED!")
            spawn{ NextLevel(L + 1, Epoch) }

    NextLevel(L:int, MyEpoch:int)<suspends>:void =
        Sleep(Director.BmRespawnSeconds)
        if (MyEpoch = Epoch, Fighters() > 0):
            Summon(L)

    # The boss is defeated: every player in the fight finishes (Finish), then the arena resets for the next fight.
    Victory():void =
        Print("FNM: boss mode: the boss is defeated")
        if (Hitter := LastHitter?):
            Director.Broadcast(FnmFeedBmFinal(Hitter), "landed the final MEGA NUKE!")
        for (State : Fighting()):
            Finish(State)
        ResetShared()

    # One player's win: the clock stops, best and board (id boss-battle, board BossBoardKey; never for a Partial run),
    # the VICTORY! board with PLAY AGAIN / CHANGE SKILL (it holds input: no podium here), the victory cues.
    Finish(State:fnm_player_state):void =
        set State.Finished = true
        set State.Runs += 1
        Time := if (State.StartTime >= 0.0) then GetSimulationElapsedTime() - State.StartTime else 0.0
        set State.StartTime = -1.0
        set State.LastTime = Time
        Director.StopBoost(State)
        HadBest := if (State.BossBest >= 0.0) then true else false
        NewBest := if (not State.Partial?, State.BossBest < 0.0 or Time < State.BossBest) then true else false
        if (NewBest?):
            set State.BossBest = Time
            FnmSaveBest(State.Player, FnmBmSaveId, Time, array{})
        Key := Director.BossBoardKey
        var Record : logic = true
        if (Top := Director.BoardFor(Key)[0], Time >= Top.Time):
            set Record = false
        if (State.Partial?):
            set Record = false
            Print("FNM: partial boss run (not from level 1), not recorded")
        else:
            Director.RecordResult(Key, State.Player, Time, array{})
        Board := Director.BoardFor(Key)
        Medal := if (State.Answered > 0) then FnmMedal(State.FirstTryCorrect, State.Answered) else ""
        MedalColor := if (Medal = "SILVER") then NamedColors.Silver else if (Medal = "BRONZE") then NamedColors.Peru else NamedColors.Gold
        Director.SetMusic(State.Player, 0)
        spawn{ VictorySounds(State.Player, Medal) }
        State.Hud.SetClock(FnmClock(Time))
        State.Hud.SetTarget("")
        State.Hud.ClearDelta()
        State.Hud.SetStreak("")
        State.Hud.ClearQuestion()
        State.Hud.ClearBoss()
        set State.BossShown = false
        State.Hud.HideBanner()
        BestTail := if (NewBest?, HadBest?) then "   NEW BEST!" else ""
        RecordTail := if (Record?) then "   NEW RECORD!" else ""
        RecordLine := if (Top := Board[0]) then FnmHolder(FnmClock(Top.Time), Top.Who, RecordTail) else FnmText("Island record   -")
        Rows := for (K -> Row : Board) { FnmRow(K + 1, Row.Who, FnmClock(Row.Time)) }
        var OwnRow : int = -1
        for (K -> Row : Board, Row.Who = State.Player):
            set OwnRow = K
        BestLine := if (State.BossBest >= 0.0) then "Your best   {FnmClock(State.BossBest)}{BestTail}" else "Your best   -"
        Pct := FnmDiv(State.FirstTryCorrect * 100, State.Answered)
        Accuracy := "Right first try: {State.FirstTryCorrect} / {State.Answered} ({Pct}%)   -   Best streak {State.BestStreak}   -   Knocked out {State.Deaths}x"
        State.Hud.ShowResults("VICTORY!", Medal, MedalColor, "Boss defeated in {FnmClock(Time)}", BestLine, RecordLine, Accuracy, "TOP BOSS TIMES THIS SESSION", Rows, OwnRow)
        State.Hud.ShowFinishButtons(true, true)
        MedalName := if (Medal = "") then "no medal" else Medal
        Print("FNM: boss mode victory in {FnmClock(Time)}, {MedalName}, right first try {State.FirstTryCorrect}/{State.Answered}, best streak {State.BestStreak}, deaths {State.Deaths}, new best {FnmYesNo(NewBest)}, record {FnmYesNo(Record)}")
        Director.Broadcast(FnmFeedFinish(State.Player, FnmClock(Time), MedalName), "finished the BOSS BATTLE in {FnmClock(Time)}  ({MedalName})")

    # bm_victory, then the medal FinishCueGapSeconds later; the boss's death cry BossDeadSeconds after the kill.
    VictorySounds(Player:player, Medal:string)<suspends>:void =
        spawn{ Director.SoundAfter(Player, fnm_cue.BmBossDead, BossDeadSeconds) }
        Director.Sound(Player, fnm_cue.BmVictory)
        if (Medal <> ""):
            Sleep(Director.FinishCueGapSeconds)
            Director.Sound(Player, if (Medal = "GOLD") then fnm_cue.MedalGold else if (Medal = "SILVER") then fnm_cue.MedalSilver else fnm_cue.MedalBronze)

    # Nobody fighting (or a fresh start): every boss, monster and effect off, level 0.
    ResetShared():void =
        set Epoch += 1
        set Level = 0
        set TeamHits = 0
        set BossAlive = false
        set BossAgent = false
        set BossRequestedAt = -1.0
        set Summoning = false
        set LastHitter = false
        set LitPerches = array{}
        set GateCursor = 0
        CloseGates()
        for (MaybeSpawner : Arena.BossSpawners, Spawner := MaybeSpawner?):
            Spawner.Disable()
        for (MaybeFx : Arena.AngerFx + Arena.PerchFx, Fx := MaybeFx?):
            Fx.Disable()

    # ------------------------------------------------ loops and events

    # Monsters (BOSS_MODE.md section 5): every SpawnCheckSeconds, while someone fights and the boss is up, the next open
    # gate (round robin) spawns one when the level's alive cap allows, then not again for the level's SpawnSeconds.
    SpawnLoop()<suspends>:void =
        loop:
            Sleep(SpawnCheckSeconds)
            Now := GetSimulationElapsedTime()
            if (Level >= 1, BossAlive?, not Summoning?, GatesOpen > 0, Now >= NextSpawnAt, Fighters() > 0, Slot := Mod[GateCursor, GatesOpen]):
                set GateCursor += 1
                Row := FnmBmLevel(Level)
                if (AliveMonsters < Row.MaxAlive, MaybeSpawner := Arena.Gates[Slot], Spawner := MaybeSpawner?):
                    Spawner.Spawn()
                    set NextSpawnAt = Now + Row.SpawnSeconds
                    Print("FNM: boss mode monster at gate {Slot + 1} ({AliveMonsters + 1}/{Row.MaxAlive} alive)")

    # Every RefreshSeconds: reset once nobody fights, the kill backstop (health gone, no elimination event), the boss
    # spawn nudge, the perch beacons, and every boss-mode player's boss line.
    BossLoop()<suspends>:void =
        loop:
            Sleep(RefreshSeconds)
            Now := GetSimulationElapsedTime()
            if (Fighters() = 0, Level > 0):
                Print("FNM: boss mode: nobody fighting, arena reset")
                ResetShared()
            if (Level >= 1):
                Need := FnmBmLevel(Level).Hits
                if (BossAlive?, TeamHits >= Need):
                    Down := if (Agent := BossAgent?, Character := Agent.GetFortCharacter[], Character.IsActive[], Character.GetHealth() > 0.0) then false else true
                    if (Down?):
                        Print("FNM: boss mode boss down without an elimination event")
                        LevelCleared()
                else if (not BossAlive?, BossRequestedAt >= 0.0, Now - BossRequestedAt > BossNudgeSeconds, Spawner := BossSpawnerFor(Level)?):
                    Print("FNM: boss mode boss not spawned after 5 s; Spawn()")
                    set BossRequestedAt = Now
                    Spawner.Spawn()
                if (Now >= BeaconAt, LitPerches.Length > 0):
                    set BeaconAt = Now + BeaconSeconds
                    for (P : LitPerches, MaybeFx := Arena.PerchFx[P - 1], Fx := MaybeFx?):
                        Fx.Restart()
            for (State : Director.PlayerStates, State.Mode = fnm_mode.Boss):
                if (not State.Finished?, not State.Picking?):
                    State.Hud.SetBoss(BossLine(State))
                    set State.BossShown = true
                else if (State.BossShown?):
                    State.Hud.ClearBoss()
                    set State.BossShown = false

    # "BOSS  ████------  40%   -   LEVEL 3: FURIOUS   -   hits 1/3", or "BOSS  is getting up ...   -   LEVEL 3: FURIOUS".
    BossLine(State:fnm_player_state):string =
        Row := FnmBmLevel(Level)
        Tail := "LEVEL {Level}: {Row.Anger}"
        if (not BossAlive?):
            return "BOSS  is getting up ...   -   {Tail}"
        Pct := BossPercent()
        Filled := FnmDiv(Pct + 9, 10)
        var Bar : string = ""
        for (K := 1..10):
            set Bar += if (K <= Filled) then "█" else "-"
        "BOSS  {Bar}  {Pct}%   -   {Tail}   -   hits {TeamHits}/{Row.Hits}"

    # The boss's health in percent (rounded up); 0 with no boss up.
    BossPercent():int =
        if (BossAlive?, Agent := BossAgent?, Character := Agent.GetFortCharacter[], Full := Character.GetMaxHealth(), Full > 0.0, P := Ceil[100.0 * Character.GetHealth() / Full]):
            Clamp(P, 0, 100)
        else:
            0

    OnBossSpawned(Agent:agent):void =
        set BossAgent = option{Agent}
        set BossAlive = true
        set BossRequestedAt = -1.0
        if (Character := Agent.GetFortCharacter[]):
            Print("FNM: boss spawned (boss mode, level {Level}), health {Character.GetHealth()} of {Character.GetMaxHealth()}, shield {Character.GetShield()}, at {Character.GetTransform().Translation}")
        else:
            Print("FNM: boss spawned (boss mode, level {Level})")

    OnBossEliminated(Result:device_ai_interaction_result):void =
        Print("FNM: boss mode boss elimination event")
        LevelCleared()

    # Gunfire on the boss: tell the shooter, once every GunHintSeconds, that the pads are the weapon.
    OnBossDamaged(Result:device_ai_interaction_result):void =
        if (Agent := Result.Source?, Shooter := player[Agent], State := Director.PlayerStates[Shooter], State.Mode = fnm_mode.Boss, not State.Finished?):
            Now := GetSimulationElapsedTime()
            Last := if (T := LastGunHint[Shooter]) then T else -100.0
            if (Now - Last >= Director.GunHintSeconds):
                if (set LastGunHint[Shooter] = Now) {}
                Print("FNM: boss mode boss shot by a player; pad hint")
                spawn{ Director.FlashNotice(State, "Bullets can't hurt the boss! Step on the pad with the RIGHT ANSWER") }

    OnMonsterSpawned(Agent:agent):void =
        set AliveMonsters += 1

    OnMonsterEliminated(Result:device_ai_interaction_result):void =
        set AliveMonsters = Max(AliveMonsters - 1, 0)
        if (Source := Result.Source?, Player := player[Source]):
            Print("FNM: boss mode: a player eliminated a monster ({AliveMonsters} alive)")
