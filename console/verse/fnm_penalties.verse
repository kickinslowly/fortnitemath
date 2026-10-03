# FNM console runtime -- what happens to a player who walks through a wrong door.
# A map picks its pool on the director (`Penalties`); each wrong answer draws one at random, so the
# player never knows what is behind a door.
# (Separate file because the character physics calls take /Verse.org/SpatialMath vectors, which clash with
# the /UnrealEngine.com/Temporary/SpatialMath ones the director uses.)

using { /Fortnite.com/Characters }
using { /Verse.org/SpatialMath }

fnm_penalty := enum:
    # Stuck in place (stasis) for FreezeSeconds, then back to the station entry.
    Freeze
    # Flung backwards and up, away from the door wall. No teleport: they land and run back.
    Yeet
    # Eliminated on the spot; after respawning they are put back at the station entry.
    Spike

# Big word shown under the red X.
FnmPenaltyLabel(Kind:fnm_penalty):string =
    if (Kind = fnm_penalty.Freeze) then "FROZEN!"
    else if (Kind = fnm_penalty.Yeet) then "YEET!"
    else "SPIKED!"

# Launch Character back along the course (world -Y, which is Verse.org "Left") and up, in m/s.
FnmYeet(Character:fort_character, BackSpeed:float, UpSpeed:float):void =
    Character.SetLinearVelocity(vector3{Forward := 0.0, Left := BackSpeed, Up := UpSpeed})

FnmVelocityLine(Character:fort_character):string =
    Velocity := Character.GetLinearVelocity()
    "velocity {Velocity.Left} back, {Velocity.Up} up"
