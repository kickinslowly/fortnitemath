# FNM console runtime -- BOSS BATTLE mode (BOSS_MODE.md is the spec). A dedicated arena east of the course
# (tools/build_bossmode.py, Verse tags fnm_bm_*): a player who picks BOSS BATTLE on the picker's grade step answers
# questions from EVERY baked cartridge by stepping on one of four answer pads. A right pad is a MEGA NUKE on a shared
# boss (wall lasers, a strike, a nuke, a white flash); five levels of 2/3/3/4/4 team hits; at each level start the boss
# summons monsters through more and more gates in the walls and a weapon chest unlocks on a perch the player must jump
# up to (opened with E: the level's weapon and its ammo). A giant letter floats over each pad, turned to the player.
# No lose state: an eliminated player comes back at the arena entry (counted). The director (fnm_director.verse) owns
# the players and routes picks, pads, perches, respawns and the finish here when a player's Mode is Boss; this file
# owns the level table, the arena's devices and the shared fight (one boss and one level for everyone in the mode).

using { /Fortnite.com/Characters }
using { /Fortnite.com/Devices }
using { /Fortnite.com/Game }
using { /Fortnite.com/Teams }
using { /UnrealEngine.com/Temporary/SpatialMath }
using { /Verse.org/Colors }
using { /Verse.org/Random }
using { /Verse.org/Simulation }
using { /Verse.org/Simulation/Tags }

# ---------------------------------------------------------------- the level table (BOSS_MODE.md section 4)

# One level: team hits to clear it, seconds between monster spawns, gates active, monsters alive at most (all gates),
# the boss's anger label, the banner's sub line, the perches (1..4) where its weapon drops, the weapon's name, and the
# creature kinds (FnmBmCreatureName, 1..5) its gates send out between the guards (empty = guards only).
fnm_bm_level := struct:
    Hits : int
    SpawnSeconds : float
    Gates : int
    MaxAlive : int
    Anger : string
    Banner : string
    Perches : []int
    WeaponName : string
    Creatures : []int

FnmBmLevels()<transacts>:[]fnm_bm_level = array:
    fnm_bm_level{Hits := 2, SpawnSeconds := 20.0, Gates := 1, MaxAlive := 2, Anger := "GRUMPY", Banner := "HERE HE COMES!", Perches := array{1}, WeaponName := "SMG", Creatures := array{}}
    fnm_bm_level{Hits := 3, SpawnSeconds := 15.0, Gates := 2, MaxAlive := 3, Anger := "ANGRY", Banner := "HE'S ANGRY!", Perches := array{2}, WeaponName := "Pump Shotgun", Creatures := array{1}}
    fnm_bm_level{Hits := 3, SpawnSeconds := 12.0, Gates := 3, MaxAlive := 4, Anger := "FURIOUS", Banner := "HE'S FURIOUS!", Perches := array{3}, WeaponName := "Assault Rifle", Creatures := array{1, 2}}
    fnm_bm_level{Hits := 4, SpawnSeconds := 9.0, Gates := 4, MaxAlive := 5, Anger := "RAGING", Banner := "HE'S RAGING!", Perches := array{4}, WeaponName := "Heavy Sniper", Creatures := array{3, 2}}
    fnm_bm_level{Hits := 4, SpawnSeconds := 7.0, Gates := 4, MaxAlive := 6, Anger := "UNHINGED", Banner := "FINAL LEVEL. UNHINGED!", Perches := array{3, 4}, WeaponName := "Rocket Launcher", Creatures := array{4, 5}}

FnmBmLevelCount()<transacts>:int = 5

# Level L's row, L clamped to 1..5.
FnmBmLevel(L:int)<transacts>:fnm_bm_level =
    Levels := FnmBmLevels()
    if (Row := Levels[Clamp(L, 1, Levels.Length) - 1]) then Row
    else fnm_bm_level{Hits := 1, SpawnSeconds := 20.0, Gates := 1, MaxAlive := 2, Anger := "", Banner := "", Perches := array{}, WeaponName := "", Creatures := array{}}

FnmBmPerchesFor(L:int)<transacts>:[]int = FnmBmLevel(L).Perches
FnmBmWeaponName(L:int)<transacts>:string = FnmBmLevel(L).WeaponName
FnmBmBannerSub(L:int)<transacts>:string = FnmBmLevel(L).Banner

# A right pad's explanation in both arenas: it shows ExplainDelaySeconds after the hit, under the next question by then.
FnmLastOne(Item:fnm_item)<transacts>:string = "Last one:  " + Item.Explanation

# Creature kind K (1..5): the creature spawner tagged fnm_bm_creature + fnm_bm_slot_K spawns this type
# (tools/build_bossmode.py CREATURES, same order).
FnmBmCreatureName(K:int)<transacts>:string =
    if (K = 1) then "Fiend"
    else if (K = 2) then "Brute"
    else if (K = 3) then "Ranged"
    else if (K = 4) then "Red Fiend"
    else if (K = 5) then "Exploding Brute"
    else "creature"

# The gate (1..4) whose alcove holds creature kind K's spawner (tools/build_bossmode.py CREATURE_GATES): its creatures
# come out of that gate. Every level's kinds use only gates it opens (FnmBmLevels Gates).
FnmBmCreatureGate(K:int)<transacts>:int =
    if (K = 1) then 1
    else if (K = 2) then 2
    else if (K = 3) then 3
    else 4

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

# A set of laser cannons and what they fire (tools/build_bossmode.py, tools/build_race_boss.py): the muzzle VFX spawners
# (none since the Niagara muzzle discharge, BOSS_MODE 15g), the strike VFX moved onto the target and its parked transform,
# the explosive devices parked under the platform, and (boss mode only) the nuke VFX. The race arena's rig has no nuke;
# fnm_director FireCannons fires either.
fnm_cannon_rig := class:
    Fx : []vfx_spawner_device
    Strike : ?vfx_spawner_device
    StrikeHome : ?transform
    Blasts : fnm_rig
    Nuke : ?vfx_spawner_device
    # Boss mode: a laser beam prop per cannon and its placed (full-length) transform, hidden between shots; the boss is
    # pinned on its platform, so a knock pins it again (KnockBoss).
    Beams : []creative_prop = array{}
    BeamFull : []transform = array{}
    PinnedBoss : logic = false
    # The race finale's rig: its shots are the shorter NS_fnm_laser_race (fnm_fx FnmSpawnRaceLaser; BOSS_MODE 16).
    RaceLaser : logic = false

# How boss mode's Megabrute is held on its platform: it may turn to face the players, never walk off.
FnmBossPin()<transacts>:stasis_args = stasis_args{AllowTurning := true, AllowFalling := true, AllowEmotes := true}

# A Megabrute boss on its platform (boss mode's, and the race finale's since 2026-10-11): back at Home (a little above it,
# so it lands on the platform), facing the entry, held there (FnmBossPin).
FnmPinBoss(Character:fort_character, Home:?transform):void =
    if (H := Home?):
        Spot := H.Translation + vector3{X := 0.0, Y := 0.0, Z := 150.0}
        if (Character.TeleportTo[Spot, MakeRotationFromYawPitchRollDegrees(-90.0, 0.0, 0.0)]) {}
    Character.ReleaseFromStasis()
    Character.PutInStasis(FnmBossPin())

# Which fnm_bm_slot_N an object carries (1..5), -1 for none (like fnm_director DoorLetter). Boss mode's numbered pieces
# and the race finale's titan clips, beam markers and letters.
FnmBmSlotOf(Object:creative_object_interface)<transacts>:int =
    ObjectTags := Object.GetTags()
    if (ObjectTags.Has[fnm_bm_slot_1{}]) then 1
    else if (ObjectTags.Has[fnm_bm_slot_2{}]) then 2
    else if (ObjectTags.Has[fnm_bm_slot_3{}]) then 3
    else if (ObjectTags.Has[fnm_bm_slot_4{}]) then 4
    else if (ObjectTags.Has[fnm_bm_slot_5{}]) then 5
    else -1

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

# Binds one perch's weapon chest to its perch number (1..4).
fnm_bm_chest_handler := class:
    Director : fnm_director
    Perch : int

    OnOpened(Agent:agent):void =
        Director.OnBmChest(Agent, Perch)

# The race finale's Megabrute (fnm_director OnBossSpawned subscribes it to the creature's DamagedEvent; boss mode's
# OnMegabossDamaged, for the race): any hit from an agent (a player's gun, an add's stray shot) is healed straight back,
# so only a pad's own Damage (Director.RacePadHitting) brings it down; a player's shot also gets the race's pad hint.
# Here, not in the director, because damage_result comes with /Fortnite.com/Game, which this file already uses.
fnm_race_boss_damage := class:
    Director : fnm_director

    OnDamaged(Result:damage_result):void =
        if (Director.RacePadHitting?):
            return
        if (Character := fort_character[Result.Target], Character.IsActive[]):
            Character.Heal(Result.Amount)
            if (Instigator := Result.Instigator?, Agent := Instigator.GetInstigatorAgent[], Shooter := player[Agent]):
                Director.RaceGunHint(Shooter)

# The boss-mode arena, found by tag at OnBegin. Station: the arena seen as a station (pads as doors, the entry as the
# retry point), so the director's answer and penalty code serve it unchanged. Numbered pieces sit at index slot - 1:
# a boss spawner per level (5), a monster gate's spawner and lightning per gate (4), a perch's trigger and beacon per
# perch (4), a weapon granter's hidden trigger per level (5), an anger-ring VFX per level (5), a creature spawner per
# creature kind (5, parked under the arena; its creatures are placed at a gate with SpawnAt).
fnm_bm_arena := class:
    Station : fnm_station
    var BossSpawners : []?guard_spawner_device = array{false, false, false, false, false}
    var Gates : []?guard_spawner_device = array{false, false, false, false}
    var GateFx : []?vfx_spawner_device = array{false, false, false, false}
    var PerchTriggers : []?trigger_device = array{false, false, false, false}
    var PerchFx : []?vfx_spawner_device = array{false, false, false, false}
    var GrantTriggers : []?trigger_device = array{false, false, false, false, false}
    var AngerFx : []?vfx_spawner_device = array{false, false, false, false, false}
    var Creatures : []?creature_spawner_device = array{false, false, false, false, false}
    # A weapon chest's hidden button per perch (off until its level's drop) and a floating letter per pad (A..D).
    var Chests : []?button_device = array{false, false, false, false}
    # What marks a chest that is open for the level (Aaron 2026-10-10: "i can't tell when a chest is active"; BOSS_MODE
    # 15e): a gold arrow beacon over it, with a WEAPON marker on the HUD, and a gold light on it.
    var ChestBeacons : []?beacon_device = array{false, false, false, false}
    var ChestLights : []?customizable_light_device = array{false, false, false, false}
    var Letters : []?creative_prop = array{false, false, false, false}
    # The boss since 2026-10-10: a Megabrute creature spawner on the platform (its transform is where the boss is held);
    # without one the per-level guard boss spawners above serve.
    var Megaboss : ?creature_spawner_device = false
    var BossHome : ?transform = false
    # What players see of the boss since 2026-10-10 (fnm_titan.verse); the Megabrute is hidden inside it.
    Titan : fnm_titan = fnm_titan{}
    # The coil crackle running at each cannon (fnm_fx FnmSpawnCoil, BOSS_MODE 15g): spawned once by StartCoils.
    var Coils : []cancelable = array{}
    var Rig : fnm_cannon_rig = fnm_cannon_rig{Fx := array{}, Strike := false, StrikeHome := false, Blasts := fnm_rig{Name := "bm_blast", Parts := array{}, Homes := array{}}, Nuke := false}

    # Which fnm_bm_slot_N an object carries (1..5), -1 for none.
    SlotOf(Object:creative_object_interface)<transacts>:int = FnmBmSlotOf(Object)

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
        for (Object : Director.FindCreativeObjectsWithTag(fnm_bm_creature), Spawner := creature_spawner_device[Object]):
            Spawner.Disable()
            if (set Creatures[SlotOf(Object) - 1] = option{Spawner}) {}
        for (Object : Director.FindCreativeObjectsWithTag(fnm_bm_chest), Chest := button_device[Object]):
            Chest.Disable()
            if (set Chests[SlotOf(Object) - 1] = option{Chest}) {}
        for (Object : Director.FindCreativeObjectsWithTag(fnm_bm_chest_beacon), Beacon := beacon_device[Object]):
            Beacon.Disable()
            if (set ChestBeacons[SlotOf(Object) - 1] = option{Beacon}) {}
        for (Object : Director.FindCreativeObjectsWithTag(fnm_bm_chest_light), Light := customizable_light_device[Object]):
            Light.TurnOff()
            if (set ChestLights[SlotOf(Object) - 1] = option{Light}) {}
        for (Object : Director.FindCreativeObjectsWithTag(fnm_bm_letter), Letter := creative_prop[Object]):
            set Letter.CanBeDamaged = false
            if (set Letters[SlotOf(Object) - 1] = option{Letter}) {}
        for (Object : Director.FindCreativeObjectsWithTag(fnm_bm_megaboss), Spawner := creature_spawner_device[Object]):
            Spawner.Disable()
            set Megaboss = option{Spawner}
            set BossHome = option{Spawner.GetTransform()}
        for (Object : Director.FindCreativeObjectsWithTag(fnm_bm_titan), Device := animated_mesh_device[Object]):
            Titan.Add(Device, SlotOf(Object))
        var Beams : []creative_prop = array{}
        var BeamFull : []transform = array{}
        for (Object : Director.FindCreativeObjectsWithTag(fnm_bm_beam), Beam := creative_prop[Object]):
            set Beam.CanBeDamaged = false
            set BeamFull += array{Beam.GetTransform()}
            set Beams += array{Beam}
            Beam.Hide()
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
        set Rig = fnm_cannon_rig{Fx := CannonFx, Strike := Strike, StrikeHome := StrikeHome, Blasts := Director.BuildRig("bm_blast", fnm_bm_blast), Nuke := Nuke, Beams := Beams, BeamFull := BeamFull, PinnedBoss := if (Megaboss?) then true else false}

    # The always-on crackle round each cannon's coils, FnmCannonCoilBack behind the beam's muzzle point on the barrel.
    # Once only: a second call (a rebuild of the arena) adds nothing, so the looping systems never stack.
    StartCoils():void =
        if (Coils.Length > 0):
            return
        set Coils = FnmSpawnCoils(Rig.BeamFull, FnmCannonCoilBack)

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

    CountChests(Items:[]?button_device):int =
        var N : int = 0
        for (Item : Items, Item?):
            set N += 1
        N

    # Chest P's marks (beacon and light) on or off.
    MarkChest(P:int, On:logic):void =
        if (MaybeBeacon := ChestBeacons[P - 1], Beacon := MaybeBeacon?):
            if (On?) then Beacon.Enable() else Beacon.Disable()
        if (MaybeLight := ChestLights[P - 1], Light := MaybeLight?):
            if (On?) then Light.TurnOn() else Light.TurnOff()

    CountMarks():int =
        var N : int = 0
        for (Item : ChestBeacons, Item?):
            set N += 1
        for (Item : ChestLights, Item?):
            set N += 1
        N

    CountLetters(Items:[]?creative_prop):int =
        var N : int = 0
        for (Item : Items, Item?):
            set N += 1
        N

    CountCreatures(Items:[]?creature_spawner_device):int =
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
    # Monsters up = Alive(): the gate guard spawners' living agents (GetAgents; an enabled gate also sends a guard of its
    # own, so the devices are counted, not our requests) + guards and creatures asked for and still loading (pending) +
    # the creatures SpawnAt returned that are still up (CreatureAgents; a creature spawner's agents cannot be listed).
    # All zeroed when the gates close.
    var GuardsPending : int = 0
    var CreaturesPending : int = 0
    var CreatureAgents : []agent = array{}
    # The gate guards' team (first guard spawned), which every creature is put on (OnCreatureSpawned).
    var AllyTeam : ?team = false
    # Hits between monsters healed back this level (OnAllyDamaged), logged at the level clear.
    var FriendlyFireHealed : int = 0
    var NextSpawnAt : float = 0.0
    var GateCursor : int = 0
    var GatesOpen : int = 0
    # Which gate guard spawners are switched on this level (a gate's first guard is its Enable: the device sends one by
    # itself when switched on, seen 2026-10-09; later ones are SpawnAt).
    var GateOn : []logic = array{false, false, false, false}
    GuardSettleSeconds : float = 1.5
    var Summoning : logic = false
    var LevelDownAt : float = -100.0
    # Bumped by ResetShared, so a summon or a level change in flight from an older fight stops itself.
    var Epoch : int = 0
    var LastHitter : ?player = false
    # The perches whose beacon is lit (the current level's), and when the beacons are restarted next.
    var LitPerches : []int = array{}
    var BeaconAt : float = 0.0
    var LastGunHint : [player]float = map{}
    # Monster kinds alternate guard / creature on a level with creatures (CreatureNext), the level's creature kinds in
    # turn (CreatureCursor); the alive cap is logged once each time it is reached (CapLogged).
    var CreatureNext : logic = false
    var CreatureCursor : int = 0
    var CapLogged : logic = false
    # The level's boss is down and the next summon has not begun (the boss line reads 0% / CLEARED).
    var Downed : logic = false
    # A creature appears this far above its gate's spawner (the alcove floor).
    CreatureLift : float = 100.0
    CreatureWaitSeconds : float = 6.0
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
    # The floating letters turn to the nearest boss-mode player and bob (fnm_director FaceLetter, shared with the race).
    # A wrong-answer wave may go this many over the level's alive cap.
    WaveExtra : int = 2
    # Voice timings after a pad: the boss's grunt, and (wrong pad) its taunt after the penalty's own voice line (which
    # comes PenaltyVoiceDelaySeconds after the buzzer); a streak line after the hit count; the death cry after the kill.
    BossGruntSeconds : float = 0.4
    TauntDelaySeconds : float = 2.5
    # How long after a right pad its explanation appears (OnPad): fnm_director ExplainDelaySeconds (shared with the race).
    StreakCueDelaySeconds : float = 2.3
    BossDeadSeconds : float = 0.5
    # The Megabrute's health (it ignores every hit but the pads': OnMegabossDamaged) is fnm_director MegabossHealth. A
    # hit's knock throws the Megabrute ~3.3 m (seen 2026-10-10), off its 5 m deep pedestal: BossLoop puts it back once it
    # is Director.BossLeashCm off its spot and Director.LeashAfterHitSeconds have passed since the hit (LastHitAt), so the
    # knock plays out. (Both constants are shared with the race finale's Megabrute.)
    var LastHitAt : float = -100.0
    # True while a pad's own Damage lands, so OnMegabossDamaged lets it through.
    var PadHitting : logic = false

    # Finds the arena's devices, subscribes the spawners' events and logs what was found.
    Build():void =
        Arena.Find(Director)
        Arena.StartCoils()
        for (MaybeSpawner : Arena.BossSpawners, Spawner := MaybeSpawner?):
            Spawner.SpawnedEvent.Subscribe(OnBossSpawned)
            Spawner.EliminatedEvent.Subscribe(OnBossEliminated)
            Spawner.DamagedEvent.Subscribe(OnBossDamaged)
        for (MaybeSpawner : Arena.Gates, Spawner := MaybeSpawner?):
            Spawner.SpawnedEvent.Subscribe(OnMonsterSpawned)
            Spawner.EliminatedEvent.Subscribe(OnMonsterEliminated)
        for (MaybeSpawner : Arena.Creatures, Spawner := MaybeSpawner?):
            Spawner.SpawnedEvent.Subscribe(OnCreatureSpawned)
            Spawner.EliminatedEvent.Subscribe(OnCreatureEliminated)
        if (Mega := Arena.Megaboss?):
            Mega.SpawnedEvent.Subscribe(OnBossSpawned)
            Mega.EliminatedEvent.Subscribe(OnBossEliminated)
        Print("FNM: boss mode: megaboss {FnmYesNo(if (Arena.Megaboss?) then true else false)}, {Arena.Rig.Beams.Length} beams, {Arena.Titan.Found()} titan clips")
        Arena.Titan.Reset()
        Print("FNM: boss mode: arena found: {Arena.Station.Doors.Length} pads, {Arena.CountSpawners(Arena.Gates)} gates, {Arena.CountTriggers(Arena.PerchTriggers)} perches, {Arena.CountSpawners(Arena.BossSpawners)} boss spawners, {Arena.CountTriggers(Arena.GrantTriggers)} granters, {Arena.Rig.Beams.Length} cannons ({Arena.Rig.Fx.Length} muzzle vfx, {Arena.Coils.Length} coil crackles)")
        Print("FNM: boss mode: fx {Arena.CountFx(Arena.GateFx)} gate, {Arena.CountFx(Arena.PerchFx)} perch, {Arena.CountFx(Arena.AngerFx)} anger, strike {FnmYesNo(if (Arena.Rig.Strike?) then true else false)}, nuke {FnmYesNo(if (Arena.Rig.Nuke?) then true else false)}, {Arena.Rig.Blasts.Parts.Length} blasts")
        Print("FNM: boss mode: {Arena.CountCreatures(Arena.Creatures)} creature spawners, {Arena.CountChests(Arena.Chests)} chests ({Arena.CountMarks()} chest beacons + lights), {Arena.CountLetters(Arena.Letters)} letters")
        for (K -> MaybeLetter : Arena.Letters, Letter := MaybeLetter?):
            spawn{ Director.FaceLetter(Letter, Letter.GetTransform().Translation, K, false) }

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
                # The explanation waits until the hit has played out: shown at once, the panel covered the titan's
                # flail (Aaron 2026-10-10). Not if they answered again (or finished) meanwhile.
                Answered := State.Answered
                Sleep(Director.ExplainDelaySeconds)
                if (not State.Finished?, State.Answered = Answered, not State.MissedCurrent?, State.Mode = fnm_mode.Boss):
                    # Prefixed "Last one:": it lands under the NEXT question, so it must not read as that question's answer (Aaron 2026-10-11).
                    Shown := State.Hud.ShowFeedback(FnmLastOne(Item), NamedColors.LightGreen)
                    Print("FNM: boss mode explanation up")
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
        Director.Cleanse(State)
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
            set LastHitAt = GetSimulationElapsedTime()
            set PadHitting = true
            Character.Damage(Amount)
            set PadHitting = false
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
            # The killing hit's flail and fall come from LevelCleared (Titan.Fall).
            if (Left > 0):
                spawn{ Arena.Titan.Hurt() }
            RefreshBossLines()
            for (Fighter : Fighting()):
                spawn{ Fighter.Hud.HitBossBar() }
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
        if (BossAlive?):
            spawn{ Arena.Titan.Taunt() }
        Director.Punish(State.Player, Arena.Station, DoorIndex, Kind)
        set State.Busy = false
        Sleep(Director.WrongFeedbackSeconds)
        State.Hud.ClearFeedbackIf(Shown)

    # The wrong-answer wave: one monster out of every open gate while the alive count stays within the cap + WaveExtra.
    Wave():void =
        Cap := FnmBmLevel(Level).MaxAlive + WaveExtra
        Base := Alive()
        var Spawned : int = 0
        for (K := 0..GatesOpen - 1):
            if (Base + Spawned < Cap):
                SpawnMonster(K, Base + Spawned + 1)
                set Spawned += 1
        Print("FNM: boss mode wave: {Spawned} monsters spawned")

    # One monster out of gate G (0-based); Count is the alive count once it is up (for the log). On a level with creature
    # kinds every other monster is a creature (the level's kinds in turn) from that kind's creature spawner, out of the
    # gate its spawner stands in (FnmBmCreatureGate); otherwise gate G's guard spawner places one guard in its alcove
    # (SpawnAt). Both count as alive at once (pending); a creature that does not come becomes a guard, a refused guard a
    # plain Spawn().
    SpawnMonster(G:int, Count:int):void =
        Row := FnmBmLevel(Level)
        Cap := Row.MaxAlive
        var Kind : int = 0
        if (CreatureNext?, Index := Mod[CreatureCursor, Row.Creatures.Length], K := Row.Creatures[Index], MaybeCreature := Arena.Creatures[K - 1], MaybeCreature?):
            set Kind = K
            set CreatureCursor += 1
        set CreatureNext = if (Row.Creatures.Length > 0, not CreatureNext?) then true else false
        # A creature comes out of its own kind's gate (where its spawner stands), a guard out of gate G.
        Out := if (Kind > 0) then FnmBmCreatureGate(Kind) - 1 else G
        if (MaybeGate := Arena.Gates[Out], Gate := MaybeGate?):
            At := Gate.GetTransform().Translation + vector3{X := 0.0, Y := 0.0, Z := CreatureLift}
            if (Kind > 0, MaybeCreature := Arena.Creatures[Kind - 1], Creature := MaybeCreature?):
                set CreaturesPending += 1
                Print("FNM: boss mode monster at gate {Out + 1} (kind creature, {Count}/{Cap} alive): {FnmBmCreatureName(Kind)}")
                spawn{ SpawnCreature(Creature, Gate, At, Out, Kind, Epoch) }
            else:
                set GuardsPending += 1
                Print("FNM: boss mode monster at gate {G + 1} (kind guard, {Count}/{Cap} alive)")
                spawn{ SpawnGuard(Gate, At, G, Epoch) }

    # One guard out of gate G: a gate still off is switched on (its own first guard is the one; counted pending until
    # GetAgents has it), else its spawner is asked for one at At (its alcove); a refusal falls back to a plain Spawn().
    SpawnGuard(Gate:guard_spawner_device, At:vector3, G:int, MyEpoch:int)<suspends>:void =
        if (On := GateOn[G], not On?):
            if (set GateOn[G] = true) {}
            Gate.Reset()
            Gate.Enable()
            Sleep(GuardSettleSeconds)
            if (MyEpoch = Epoch):
                set GuardsPending = Max(GuardsPending - 1, 0)
            Print("FNM: boss mode guard up at gate {G + 1} on opening it ({Alive()} alive)")
            return
        Result := Gate.SpawnAt(FromVector3(At))
        if (MyEpoch = Epoch):
            set GuardsPending = Max(GuardsPending - 1, 0)
        if (Result?):
            Print("FNM: boss mode guard up at gate {G + 1} ({Alive()} alive)")
        else:
            Print("FNM: boss mode guard refused at gate {G + 1} (spawn limit {Gate.GetSpawnLimit()}); Spawn()")
            if (MyEpoch = Epoch, GatesOpen > 0):
                Gate.Spawn()

    # One creature from kind's creature spawner, as a pulse: Enable, wait for its SpawnedEvent, Disable at once. The device
    # stands in its gate's alcove (tools/build_bossmode.py CREATURE_GATES), so its own first wave (one creature, a few
    # seconds after it is switched on with a player in range) walks out of that gate; switched off at once, it never sends
    # a second. Nothing within CreatureWaitSeconds = a guard from that gate instead. (SpawnAt was tried first, 2026-10-09:
    # refused in the tick of the Enable, and when it took, the call did not return within 30 s and a second creature
    # followed the first.)
    SpawnCreature(Spawner:creature_spawner_device, Gate:guard_spawner_device, At:vector3, G:int, Kind:int, MyEpoch:int)<suspends>:void =
        Spawner.Enable()
        Asked := GetSimulationElapsedTime()
        Result:?agent = race:
            block:
                Up := Spawner.SpawnedEvent.Await()
                option{Up}
            block:
                Sleep(CreatureWaitSeconds)
                false
        Spawner.Disable()
        Took := GetSimulationElapsedTime() - Asked
        if (MyEpoch = Epoch):
            set CreaturesPending = Max(CreaturesPending - 1, 0)
        if (Agent := Result?):
            if (MyEpoch = Epoch, GatesOpen > 0):
                set CreatureAgents += array{Agent}
            Print("FNM: boss mode creature up: {FnmBmCreatureName(Kind)} at gate {G + 1} ({Alive()} alive) after {Took} s")
        else:
            Print("FNM: boss mode creature refused: {FnmBmCreatureName(Kind)} for {Took} s (spawn limit {Spawner.GetSpawnLimit()}); a guard instead")
            if (MyEpoch = Epoch, GatesOpen > 0):
                set GuardsPending += 1
                SpawnGuard(Gate, At, G, MyEpoch)

    # Monsters alive now (see GuardsPending): living guards of the gate spawners, guards on their way, creatures up.
    Alive()<transacts>:int =
        var N : int = GuardsPending + CreaturesPending + CreatureAgents.Length
        for (MaybeSpawner : Arena.Gates, Spawner := MaybeSpawner?, Agent : Spawner.GetAgents(), Character := Agent.GetFortCharacter[], Character.IsActive[]):
            set N += 1
        N

    IsLit(P:int)<transacts>:logic =
        var Lit : logic = false
        for (Each : LitPerches, Each = P):
            set Lit = true
        Lit

    # A player on perch P: when its chest is unlocked for the level and they have not taken this level's weapon, a
    # reminder to open it.
    OnPerch(State:fnm_player_state, P:int):void =
        Print("FNM: boss mode perch {P} reached (level {Level})")
        if (State.Mode = fnm_mode.Boss, not State.Finished?, not State.Picking?, Level >= 1, IsLit(P)?):
            Taken := if (Got := State.TakenLevels[Level], Got?) then true else false
            if (not Taken?):
                spawn{ ShowLine(State, "OPEN THE CHEST! (hold E)", NamedColors.Gold, 3.0) }

    # Perch P's chest was opened (its button held) by State's player: when P is lit and they have not taken this level's
    # weapon, the level's granter hands it over with its ammo (its hidden trigger, fired for them).
    OnChest(State:fnm_player_state, P:int):void =
        Print("FNM: boss mode chest {P} opened (level {Level})")
        if (State.Mode = fnm_mode.Boss, not State.Finished?, not State.Picking?, Level >= 1, IsLit(P)?):
            Taken := if (Got := State.TakenLevels[Level], Got?) then true else false
            Weapon := FnmBmWeaponName(Level)
            if (Taken?):
                spawn{ ShowLine(State, "You already have the {Weapon}!", NamedColors.Gold, 3.0) }
            else if (MaybeTrigger := Arena.GrantTriggers[Level - 1], Trigger := MaybeTrigger?):
                Trigger.Trigger(State.Player)
                if (set State.TakenLevels[Level] = true) {}
                Director.Sound(State.Player, fnm_cue.BmWeapon)
                State.Hud.FlashBig("{Weapon} GET!", NamedColors.Gold, WeaponGetSeconds)
                Director.Broadcast(FnmFeedBmWeapon(State.Player, Weapon), "grabbed the {Weapon}!")
                Print("FNM: boss mode weapon {Weapon} granted from chest {P} (level {Level})")
            else:
                Print("FNM: boss mode chest {P}: no granter for level {Level}")

    # ------------------------------------------------ levels (BOSS_MODE.md sections 4 and 6)

    # Level L begins: about BmSummonSeconds of banner, announcer, anger ring, the boss, his line, the gates opening and
    # the weapon drop, seen and heard by every player in the mode.
    Summon(L:int)<suspends>:void =
        MyEpoch := Epoch
        Row := FnmBmLevel(L)
        Scale := Max(Director.BmSummonSeconds, 0.5) / 5.0
        set Summoning = true
        set Downed = false
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
            spawn{ ShowLine(State, "WEAPON CHEST: {Hint} - jump up and open it!", NamedColors.Gold, LineSeconds) }
        Sleep(1.0 * Scale)
        if (MyEpoch <> Epoch):
            return
        for (State : Director.PlayerStates, State.Mode = fnm_mode.Boss):
            State.Hud.HideBanner()
        set NextSpawnAt = GetSimulationElapsedTime() + Row.SpawnSeconds
        set Summoning = false
        Print("FNM: boss level {L} summoned: {Row.Gates} gates, every {FnmBmWholeSeconds(Row.SpawnSeconds)} s, max {Row.MaxAlive} alive, {Row.WeaponName} at {Hint}")
        if (Director.DebugBossChest > 0, MaybeChest := Arena.Chests[Director.DebugBossChest - 1], Chest := MaybeChest?):
            # Toward the arena's centre line (the entry's X), where the perch's stepping stones are.
            At := Chest.GetTransform().Translation
            Toward := if (At.X > Arena.Station.RetryTeleporter.GetTransform().Translation.X) then -1.0 else 1.0
            Spot := At + vector3{X := Toward * Director.DebugChestDistance, Y := 0.0, Z := 100.0}
            Yaw := if (Toward > 0.0) then 180.0 else 0.0
            for (State : Fighting(), Character := State.Player.GetFortCharacter[]):
                if (Character.TeleportTo[Spot, MakeRotationFromYawPitchRollDegrees(Yaw, 0.0, 0.0)]) {}
            Print("FNM: debug boss chest: stood at chest {Director.DebugBossChest}")

    # Asks level L's boss spawner for its boss (fresh spawn limit, enabled; SpawnedEvent confirms) with a strike at it.
    SpawnBoss(L:int):void =
        if (Mega := Arena.Megaboss?):
            set BossRequestedAt = GetSimulationElapsedTime()
            Mega.Enable()
            spawn{ Arena.Titan.Arrive() }
            Print("FNM: boss mode megaboss requested (level {L})")
            spawn{ StrikeAt(Mega.GetTransform().Translation) }
        else if (Spawner := BossSpawnerFor(L)?):
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

    # Gates 1..Count open: lightning at every mouth, and the boss's first minions: a guard out of gate 1 and, on a level
    # with creatures, its first creature kind out of that kind's gate. The rest come one at a time every SpawnSeconds
    # (SpawnLoop: creature, guard, creature, ... round the gates) up to the level's alive cap, so a level starts light and
    # fills up faster level by level. A gate's guard spawner is switched on at its first guard (SpawnGuard).
    OpenGates(Count:int):void =
        set GatesOpen = Min(Count, Arena.Gates.Length)
        Row := FnmBmLevel(Level)
        set CreatureCursor = 0
        set CapLogged = false
        set GuardsPending = 0
        set CreaturesPending = 0
        set CreatureAgents = array{}
        set GateOn = array{false, false, false, false}
        set GateCursor = 1
        for (K -> MaybeFx : Arena.GateFx, K < GatesOpen, Fx := MaybeFx?):
            Fx.Enable()
            Fx.Restart()
        set CreatureNext = false
        SpawnMonster(0, Alive() + 1)
        if (Row.Creatures.Length > 0):
            SpawnMonster(1, Alive() + 1)
        Print("FNM: boss mode gates open: {GatesOpen}")

    GateFxOff()<suspends>:void =
        Sleep(GateFxSeconds)
        for (MaybeFx : Arena.GateFx, Fx := MaybeFx?):
            Fx.Disable()

    # Every gate shut: guard spawners off (their guards despawn), every creature eliminated and its spawner off, lightning
    # off, nobody counted alive (GatesOpen 0 first, so the eliminations this causes are not counted).
    CloseGates():void =
        set GatesOpen = 0
        set GateOn = array{false, false, false, false}
        for (MaybeSpawner : Arena.Gates, Spawner := MaybeSpawner?):
            Spawner.Disable()
        for (MaybeCreature : Arena.Creatures, Creature := MaybeCreature?):
            Creature.Enable()
            Creature.EliminateCreatures()
            Creature.Disable()
        for (MaybeFx : Arena.GateFx, Fx := MaybeFx?):
            Fx.Disable()
        set GuardsPending = 0
        set CreaturesPending = 0
        set CreatureAgents = array{}

    # The beacons on Perches on (BossLoop restarts them every BeaconSeconds) and their chests' buttons on; every other
    # perch's beacon and chest button off.
    LightPerches(Perches:[]int):void =
        set LitPerches = Perches
        set BeaconAt = GetSimulationElapsedTime() + BeaconSeconds
        for (K -> MaybeFx : Arena.PerchFx, Fx := MaybeFx?):
            if (IsLit(K + 1)?):
                Fx.Enable()
                Fx.Restart()
            else:
                Fx.Disable()
        for (K -> MaybeChest : Arena.Chests, Chest := MaybeChest?):
            if (IsLit(K + 1)?):
                Chest.Enable()
            else:
                Chest.Disable()
        for (P := 1..4):
            Arena.MarkChest(P, IsLit(P))

    # The boss went down (its EliminatedEvent, or BossLoop's backstop): the level is cleared for everyone; the next one
    # is summoned BmRespawnSeconds later, or after level 5 it is the victory.
    LevelCleared():void =
        if (not BossAlive?):
            return
        L := Level
        set BossAlive = false
        set BossAgent = false
        set BossRequestedAt = -1.0
        set Downed = true
        set LevelDownAt = GetSimulationElapsedTime()
        if (Mega := Arena.Megaboss?):
            Mega.Disable()
        else if (Spawner := BossSpawnerFor(L)?):
            Spawner.Disable()
        CloseGates()
        Print("FNM: boss level {L} cleared (friendly fire healed {FriendlyFireHealed} hits)")
        spawn{ Arena.Titan.Fall() }
        set FriendlyFireHealed = 0
        RefreshBossLines()
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
        set Downed = false
        set LastHitter = false
        set LitPerches = array{}
        set GateCursor = 0
        CloseGates()
        for (MaybeSpawner : Arena.BossSpawners, Spawner := MaybeSpawner?):
            Spawner.Disable()
        if (Mega := Arena.Megaboss?):
            Mega.Disable()
            Mega.EliminateCreatures()
        Arena.Titan.Reset()
        for (MaybeFx : Arena.AngerFx + Arena.PerchFx, Fx := MaybeFx?):
            Fx.Disable()
        for (MaybeChest : Arena.Chests, Chest := MaybeChest?):
            Chest.Disable()
        for (P := 1..4):
            Arena.MarkChest(P, false)

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
                Up := Alive()
                if (Up < Row.MaxAlive):
                    set CapLogged = false
                    set NextSpawnAt = Now + Row.SpawnSeconds
                    SpawnMonster(Slot, Up + 1)
                else:
                    # Capped: the gate's turn is not used up; the next check retries once a monster is down.
                    set GateCursor -= 1
                    if (not CapLogged?):
                        set CapLogged = true
                        Print("FNM: boss mode monster cap reached at level {Level} ({Up}/{Row.MaxAlive} alive)")

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
                else if (not BossAlive?, BossRequestedAt >= 0.0, Now - BossRequestedAt > BossNudgeSeconds):
                    set BossRequestedAt = Now
                    if (Mega := Arena.Megaboss?):
                        Print("FNM: boss mode megaboss not spawned after 5 s; Disable, Enable")
                        Mega.Disable()
                        Mega.Enable()
                    else if (Spawner := BossSpawnerFor(Level)?):
                        Print("FNM: boss mode boss not spawned after 5 s; Spawn()")
                        Spawner.Spawn()
                if (BossAlive?, Now - LastHitAt > Director.LeashAfterHitSeconds, Home := Arena.BossHome?, Agent := BossAgent?, Character := Agent.GetFortCharacter[], Character.IsActive[]):
                    At := Character.GetTransform().Translation
                    if (Distance(vector3{X := At.X, Y := At.Y, Z := 0.0}, vector3{X := Home.Translation.X, Y := Home.Translation.Y, Z := 0.0}) > Director.BossLeashCm):
                        Print("FNM: boss mode megaboss wandered to {At}; back on the platform")
                        PinBoss(Character)
                if (Now >= BeaconAt, LitPerches.Length > 0):
                    set BeaconAt = Now + BeaconSeconds
                    for (P : LitPerches, MaybeFx := Arena.PerchFx[P - 1], Fx := MaybeFx?):
                        Fx.Restart()
            for (State : Director.PlayerStates, State.Mode = fnm_mode.Boss):
                if (not State.Finished?, not State.Picking?):
                    ShowBossBar(State)
                    set State.BossShown = true
                else if (State.BossShown?):
                    State.Hud.ClearBoss()
                    set State.BossShown = false

    # Every fighter's boss line now (a hit and a kill do not wait for BossLoop's next refresh).
    RefreshBossLines():void =
        for (State : Fighting()):
            ShowBossBar(State)
            set State.BossShown = true

    # The boss bar at the bottom of the screen (Aaron 2026-10-10: "make healthbar more noticeable"): "MEGABRUTE  -  LEVEL 3:
    # FURIOUS" over a bar filled to the boss's health, "40%   -   hits 1/3" on it.
    ShowBossBar(State:fnm_player_state):void =
        Row := FnmBmLevel(Level)
        Who := if (Arena.Titan.Found() > 0) then "THE MAGMA TITAN" else if (Arena.Megaboss?) then "MEGABRUTE BOSS" else "BOSS"
        Name := "{Who}   -   LEVEL {Level}: {Row.Anger}"
        if (Downed?):
            State.Hud.SetBossBar(Name, 0, "DEFEATED!   LEVEL {Level} CLEARED")
        else if (not BossAlive?):
            State.Hud.SetBossBar(Name, 100, "THE BOSS IS COMING ...")
        else:
            Pct := BossPercent()
            State.Hud.SetBossBar(Name, Pct, "{Pct}%   -   hits {TeamHits}/{Row.Hits}")

    # The boss's health in percent (rounded up); 0 with no boss up.
    BossPercent():int =
        if (BossAlive?, Agent := BossAgent?, Character := Agent.GetFortCharacter[], Full := Character.GetMaxHealth(), Full > 0.0, P := Ceil[100.0 * Character.GetHealth() / Full]):
            Clamp(P, 0, 100)
        else:
            0

    OnBossSpawned(Agent:agent):void =
        if (Mega := Arena.Megaboss?):
            Mega.Disable()
            if (BossAlive?):
                Print("FNM: boss mode: a second megaboss spawned while one is up (ignored)")
                return
            if (Character := Agent.GetFortCharacter[]):
                Character.SetMaxHealth(Director.MegabossHealth)
                Character.SetHealth(Director.MegabossHealth)
                Character.DamagedEvent().Subscribe(OnMegabossDamaged)
                PinBoss(Character)
                # The titan is the boss players see (fnm_titan.verse); the Megabrute only holds the health, inside it.
                if (Arena.Titan.Found() > 0):
                    Character.Hide()
        set BossAgent = option{Agent}
        set BossAlive = true
        set BossRequestedAt = -1.0
        Teams := Director.GetPlayspace().GetTeamCollection()
        ToGuards := if (Team := AllyTeam?, Mine := Teams.GetTeam[Agent], A := Teams.GetTeamAttitude[Mine, Team]) then AttitudeName(A) else "no guard yet"
        Print("FNM: boss mode team: boss on team {TeamNo(Agent)}, to the guards {ToGuards}, vs the player {AttitudeToPlayer(Agent)}")
        if (Character := Agent.GetFortCharacter[]):
            Print("FNM: boss spawned (boss mode, level {Level}), health {Character.GetHealth()} of {Character.GetMaxHealth()}, shield {Character.GetShield()}, at {Character.GetTransform().Translation}")
        else:
            Print("FNM: boss spawned (boss mode, level {Level})")

    OnBossEliminated(Result:device_ai_interaction_result):void =
        Print("FNM: boss mode boss elimination event")
        LevelCleared()

    # The Megabrute on its platform: back at home (a little above it, so it lands on the marble), facing the entry,
    # held there (FnmBossPin).
    PinBoss(Character:fort_character):void =
        FnmPinBoss(Character, Arena.BossHome)

    # Any hit on the Megabrute from an agent (a player's gun, a monster's stray shot) is healed straight back: only the
    # pads' Damage (no instigator) brings it down. A player's shot also gets the pad hint.
    OnMegabossDamaged(Result:damage_result):void =
        if (PadHitting?):
            return
        if (Character := fort_character[Result.Target], Character.IsActive[]):
            Character.Heal(Result.Amount)
            if (Instigator := Result.Instigator?, Agent := Instigator.GetInstigatorAgent[], Shooter := player[Agent]):
                GunHint(Shooter)

    # Gunfire on the boss: tell the shooter, once every GunHintSeconds, that the pads are the weapon.
    OnBossDamaged(Result:device_ai_interaction_result):void =
        if (Agent := Result.Source?, Shooter := player[Agent]):
            GunHint(Shooter)

    GunHint(Shooter:player):void =
        if (State := Director.PlayerStates[Shooter], State.Mode = fnm_mode.Boss, not State.Finished?):
            Now := GetSimulationElapsedTime()
            Last := if (T := LastGunHint[Shooter]) then T else -100.0
            if (Now - Last >= Director.GunHintSeconds):
                if (set LastGunHint[Shooter] = Now) {}
                Print("FNM: boss mode boss shot by a player; pad hint")
                spawn{ Director.FlashNotice(State, "Bullets can't hurt the boss! Step on the pad with the RIGHT ANSWER") }

    # A gate guard spawner's SpawnedEvent: logged only (Alive counts the spawners' agents). More of these than "guard up"
    # lines would mean the device spawns guards of its own (on Enable, or a batch per Spawn).
    OnMonsterSpawned(Agent:agent):void =
        Print("FNM: boss mode guard spawned event ({Alive()} alive)")
        if (Character := Agent.GetFortCharacter[]):
            Character.DamagedEvent().Subscribe(OnAllyDamaged)
        if (not AllyTeam?, Team := Director.GetPlayspace().GetTeamCollection().GetTeam[Agent]):
            set AllyTeam = option{Team}
            Print("FNM: boss mode team: guards on team {TeamNo(Agent)}, vs the player {AttitudeToPlayer(Agent)}")

    # A creature spawner's SpawnedEvent. The creature spawner has no team option and a gate guard shot creatures dead
    # (B6, 2026-10-09: "creature eliminated by a gate guard"), so a creature not friendly with the guards' team is put on
    # it (Aaron: monsters and guards all hunt the player, never each other). Logged with the attitudes before and after.
    OnCreatureSpawned(Agent:agent):void =
        Print("FNM: boss mode creature spawned event ({Alive()} alive)")
        if (Character := Agent.GetFortCharacter[]):
            Character.DamagedEvent().Subscribe(OnAllyDamaged)
        Teams := Director.GetPlayspace().GetTeamCollection()
        if (Team := AllyTeam?):
            Before := if (Mine := Teams.GetTeam[Agent], A := Teams.GetTeamAttitude[Mine, Team]) then AttitudeName(A) else "no team"
            if (Before <> "friendly"):
                Moved := if (Teams.AddToTeam[Agent, Team]) then "moved onto the guards' team" else "AddToTeam refused"
                Print("FNM: boss mode team: creature on team {TeamNo(Agent)} was {Before} to the guards: {Moved}, now vs the player {AttitudeToPlayer(Agent)}")
            else:
                Print("FNM: boss mode team: creature on team {TeamNo(Agent)}, friendly to the guards, vs the player {AttitudeToPlayer(Agent)}")
        else:
            Print("FNM: boss mode team: creature on team {TeamNo(Agent)} before any guard, vs the player {AttitudeToPlayer(Agent)}")

    # Friendly fire (B6, 2026-10-09): guards, bosses and creatures are one team (logged "friendly"), yet a gate guard's stray
    # bullets aimed at the player killed the Red Fiends chasing it ("creature eliminated by a gate guard", 3 in a level-5
    # hold run). Damage to a gate guard or a creature from any agent that is not a player is healed straight back, so only
    # players (and the level clear) take them down. A single lethal hit still kills (the heal comes after the damage).
    OnAllyDamaged(Result:damage_result):void =
        if (Instigator := Result.Instigator?, Agent := Instigator.GetInstigatorAgent[], not player[Agent], Character := fort_character[Result.Target], Character.IsActive[]):
            Character.Heal(Result.Amount)
            set FriendlyFireHealed += 1

    # Team helpers for the log: an agent's team as its 1-based place in GetTeams() (0 = none), and its attitude to the
    # first player in the playspace.
    TeamNo(Agent:agent)<transacts>:int =
        Teams := Director.GetPlayspace().GetTeamCollection()
        if (Team := Teams.GetTeam[Agent]):
            Found := for (I -> Each : Teams.GetTeams(), Each = Team) { I + 1 }
            if (N := Found[0]) then N else -1
        else:
            0

    AttitudeToPlayer(Agent:agent)<transacts>:string =
        Teams := Director.GetPlayspace().GetTeamCollection()
        if (Player := Director.GetPlayspace().GetPlayers()[0], A := Teams.GetTeamAttitude[Agent, Player]) then AttitudeName(A) else "unknown"

    AttitudeName(A:team_attitude)<computes>:string =
        case(A):
            team_attitude.Friendly => "friendly"
            team_attitude.Neutral => "neutral"
            team_attitude.Hostile => "hostile"

    OnMonsterEliminated(Result:device_ai_interaction_result):void =
        if (Source := Result.Source?, Player := player[Source]):
            Print("FNM: boss mode: a player eliminated a monster ({Alive()} alive)")
        else if (GatesOpen > 0):
            Print("FNM: boss mode guard eliminated by {Killer(Result)} ({Alive()} alive)")

    # Who eliminated Result.Target, for the log: a player, the boss, a gate guard, a creature of ours, itself, or no source
    # (Aaron 2026-10-09: monsters and guards must all hunt the player, never each other; this line is the proof).
    Killer(Result:device_ai_interaction_result)<transacts>:string =
        if (Source := Result.Source?):
            if (player[Source]):
                return "a player"
            if (Target := Result.Target?, Target = Source):
                return "itself"
            if (Boss := BossAgent?, Boss = Source):
                return "the boss"
            Guards := for (MaybeSpawner : Arena.Gates, Spawner := MaybeSpawner?, Agent : Spawner.GetAgents(), Agent = Source) { Agent }
            if (Guards.Length > 0):
                return "a gate guard"
            Bosses := for (MaybeSpawner : Arena.BossSpawners, Spawner := MaybeSpawner?, Agent : Spawner.GetAgents(), Agent = Source) { Agent }
            if (Bosses.Length > 0):
                return "a boss spawner's guard"
            Creatures := for (Agent : CreatureAgents, Agent = Source) { Agent }
            if (Creatures.Length > 0):
                return "a creature"
            return "another agent"
        "no source"

    # A creature down: off the count if it was one of ours (CloseGates' own EliminateCreatures, or a creature the device
    # spawned by itself, never counted).
    OnCreatureEliminated(Result:device_ai_interaction_result):void =
        By := Killer(Result)
        if (Target := Result.Target?):
            set CreatureAgents = for (Agent : CreatureAgents, Agent <> Target) { Agent }
        Print("FNM: boss mode creature eliminated by {By} ({Alive()} alive)")
