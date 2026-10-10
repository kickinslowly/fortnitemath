# FNM console runtime -- the boss mode titan: what players see of the boss (BOSS_MODE.md section 15b). A character cannot
# be scaled, so the fight's Megabrute stays hidden on the platform (it keeps the health, the bar and the level clears) and
# a 12 m Meshy monster stands over it: one Animated Mesh device per clip (tools/build_bossmode.py titan, tag fnm_bm_titan
# + slot), swapped in at home while the rest shrink to nothing there. fnm_boss_mode calls Arrive (a level's boss spawns),
# Hurt (a right pad), Taunt (a wrong pad) and Reset (the fight resets).
#
# Every clip device starts Playing on its own and loops; Verse only swaps them by TeleportTo. Play() never started a
# device placed Stopped, PlayReverse threw the mesh flat, and a clip parked 30 m under the floor came back in a broken
# pose, so a resting clip is shrunk to ParkScale at home instead (it keeps rendering and ticking). Titan self-test frames,
# 2026-10-10.

using { /Fortnite.com/Devices }
using { /UnrealEngine.com/Temporary/SpatialMath }
using { /Verse.org/Simulation }

fnm_titan := class:
    # Indexed by slot - 1, build_bossmode TITAN_CLIPS order.
    var Clips : []?animated_mesh_device = array{false, false, false}
    var Home : ?transform = false
    # Bumped by every new sequence, so an older one in flight stops at its next step.
    var Generation : int = 0
    Idle : int = 0
    Flail : int = 1
    Stomp : int = 2
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

    # Clip K at home, every other clip shrunk to nothing there.
    Show(K:int):void =
        if (H := Home?):
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

    # A level's boss arrives: an angry stomp, then idle.
    Arrive()<suspends>:void =
        Beat(Stomp, StompSeconds)

    # A right pad: it flails in the beams, then stomps in rage.
    Hurt()<suspends>:void =
        G := Begin()
        Show(Flail)
        Sleep(FlailSeconds)
        if (G = Generation):
            Beat(Stomp, StompSeconds)

    # A wrong pad: it stomps at the player, then idle.
    Taunt()<suspends>:void =
        Beat(Stomp, StompSeconds)

    # The fight resets: any sequence stops and the titan idles.
    Reset():void =
        Begin()
        Show(Idle)
