# FNM console runtime -- penalty rigs: props and devices parked out of sight that a penalty borrows,
# moves onto the punished player, and parks again (an ice cube for Freeze, a ring of spears that burst out
# of the floor for Spike, an air vent for Yeet). tools/build_rigs.py places them, tagged fnm_ice /
# fnm_spike / fnm_yeet. Several of each so players punished at the same moment each get their own.
# (Real Fortnite traps can't be used: a placed trap, BR or Creative, fails island validation.)

using { /Fortnite.com/Devices }
using { /UnrealEngine.com/Temporary/SpatialMath }
using { /Verse.org/Simulation }

fnm_rig := class:
    Name : string
    Parts : []creative_object
    Homes : []transform
    var Turn : int = 0

    # Index of the part to use next (round robin); -1 when the rig is empty.
    NextIndex()<transacts>:int =
        if (Index := Mod[Turn, Parts.Length]):
            set Turn += 1
            Index
        else:
            -1

    # The next Count indices (round robin, so they may repeat if the rig is smaller than Count).
    NextIndices(Count:int)<transacts>:[]int =
        Indices := for (K := 0..Count - 1, Index := Mod[Turn + K, Parts.Length]) { Index }
        set Turn += Count
        Indices

    # Moves part Index to Spot facing Yaw (keeps its scale). False if the rig is empty or the move failed.
    Place(Index:int, Spot:vector3, Yaw:float)<transacts>:logic =
        if (Part := Parts[Index], Home := Homes[Index]):
            Moved := transform{Translation := Spot, Rotation := MakeRotationFromYawPitchRollDegrees(Yaw, 0.0, 0.0), Scale := Home.Scale}
            if (Part.TeleportTo[Moved]) then true else false
        else:
            false

    # Slides part Index up by Height (cm) over Seconds.
    Rise(Index:int, Height:float, Seconds:float)<suspends>:void =
        if (Part := Parts[Index]):
            At := Part.GetTransform()
            Part.MoveTo(At.Translation + vector3{X := 0.0, Y := 0.0, Z := Height}, At.Rotation, Seconds)

    Park(Index:int)<transacts>:void =
        if (Part := Parts[Index], Home := Homes[Index], Part.TeleportTo[Home]) {}

    PartAt(Index:int)<transacts><decides>:creative_object = Parts[Index]

# "yes" / "no" for log lines (a logic does not interpolate).
FnmYesNo(Value:logic):string = if (Value?) then "yes" else "no"
