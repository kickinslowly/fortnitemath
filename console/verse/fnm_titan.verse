# FNM console runtime -- the boss mode titan: what players see of the boss (BOSS_MODE.md section 15b). A character cannot
# be scaled, so the fight's Megabrute stays hidden on the platform (it keeps the health, the bar and the level clears) and
# a 12 m Meshy monster stands over it: one Animated Mesh device per clip (tools/build_bossmode.py titan, tag fnm_bm_titan
# + slot), swapped in at home while the rest shrink to nothing there. fnm_boss_mode calls Arrive (a level's boss spawns),
# Hurt (a right pad), Taunt (a wrong pad), Fall (a level cleared) and Reset (the fight resets).
#
# Every clip device starts Playing on its own and loops; Verse only swaps them by TeleportTo. Play() never started a
# device placed Stopped, PlayReverse threw a looping clip flat, and a clip parked 30 m under the floor came back in a
# broken pose, so a resting clip is shrunk to ParkScale at home instead (it keeps rendering and ticking). Titan self-test
# frames, 2026-10-10. The fall is the exception: it plays once and holds lying down; Play() does not restart it once
# finished, but PlayReverse() runs it back to standing (shrunk, out of sight), and Play() then falls again.

using { /Fortnite.com/Devices }
using { /UnrealEngine.com/Temporary/SpatialMath }
using { /Verse.org/Simulation }

fnm_titan := class:
    # Indexed by slot - 1, build_bossmode TITAN_CLIPS order.
    var Clips : []?animated_mesh_device = array{false, false, false, false}
    var Home : ?transform = false
    # Bumped by every new sequence, so an older one in flight stops at its next step.
    var Generation : int = 0
    Idle : int = 0
    Flail : int = 1
    Stomp : int = 2
    # Plays once and holds lying down (build_bossmode TITAN_ONCE); Fall restarts it.
    Dead : int = 3
    # The killing hit's flail shows this long before the fall; the fall clip runs FallSeconds; it then lies at least
    # DownHoldSeconds before the next level's Arrive stands it up (the next boss is summoned 4 s after a clear).
    FallDelaySeconds : float = 1.5
    FallSeconds : float = 3.0
    DownHoldSeconds : float = 1.5
    # From a Fall until the next Arrive or Hurt: Reset keeps it down (the victory resets the fight at the killing hit).
    var Falling : logic = false
    var FallEnds : float = 0.0
    # How long each beat shows: the flail outlasts the answer feedback that covers the titan for the first seconds after
    # a pad; the stomp runs two loops of its 1.33 s clip.
    FlailSeconds : float = 4.0
    StompSeconds : float = 2.67
    ParkScale : float = 0.001

    Add(Device:animated_mesh_device, Slot:int):void =
        if (Slot = 1):
            set Home = option{Device.GetTransform()}
        if (set Clips[Slot - 1] = option{Device}) {}

    Found()<transacts>:int =
        var N : int = 0
        for (MaybeClip : Clips, MaybeClip?):
            set N += 1
        N

    # Clip K at home, every other clip shrunk to nothing there (nothing changes when clip K was not found).
    Show(K:int):void =
        if (H := Home?, Shown := Clips[K]?):
            Park := transform{Translation := H.Translation, Rotation := H.Rotation, Scale := H.Scale * ParkScale}
            for (I -> MaybeClip : Clips, Clip := MaybeClip?):
                if (I = K):
                    if (Clip.TeleportTo[H]) {}
                else:
                    if (Clip.TeleportTo[Park]) {}

    Begin()<transacts>:int =
        set Generation += 1
        Generation

    # Clip K for Seconds, then idle, unless a newer sequence began meanwhile.
    Beat(K:int, Seconds:float)<suspends>:void =
        G := Begin()
        Show(K)
        Sleep(Seconds)
        if (G = Generation):
            Show(Idle)

    # The fall clip runs back to standing, ready for the next Fall (call it with the fall shrunk away).
    Rewind():void =
        if (MaybeClip := Clips[Dead], Clip := MaybeClip?):
            Clip.PlayReverse()

    # A level's boss arrives: once the last fall has played out, an angry stomp, then idle.
    Arrive()<suspends>:void =
        G := Generation
        Wait := FallEnds - GetSimulationElapsedTime()
        if (Falling?, Wait > 0.0):
            Sleep(Wait)
        if (G = Generation):
            Mine := Begin()
            Show(Stomp)
            if (Falling?):
                set Falling = false
                Rewind()
            Sleep(StompSeconds)
            if (Mine = Generation):
                Show(Idle)

    # A right pad: it flails in the beams, then stomps in rage.
    Hurt()<suspends>:void =
        G := Begin()
        Show(Flail)
        if (Falling?):
            set Falling = false
            Rewind()
        Sleep(FlailSeconds)
        if (G = Generation):
            Beat(Stomp, StompSeconds)

    # A wrong pad: it stomps at the player, then idle.
    Taunt()<suspends>:void =
        Beat(Stomp, StompSeconds)

    # A level cleared: the killing hit's flail, then it falls and stays down until the next Arrive (or Reset).
    Fall()<suspends>:void =
        G := Begin()
        set Falling = true
        set FallEnds = GetSimulationElapsedTime() + FallDelaySeconds + FallSeconds + DownHoldSeconds
        Show(Flail)
        Sleep(FallDelaySeconds)
        if (G = Generation, MaybeClip := Clips[Dead], Clip := MaybeClip?):
            Clip.Play()
            Show(Dead)
            Print("FNM: titan falls")

    # The fight resets: any sequence stops and the titan idles; a fall in progress or lying down stays.
    # (At the build, the fall clip has played itself down at the session start: this rewinds it too.)
    Reset():void =
        if (Falling?) then return
        Begin()
        Show(Idle)
        Rewind()
