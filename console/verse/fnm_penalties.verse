# FNM console runtime -- what happens to a player who walks through a wrong door.
# A map picks its pool on the director (`Penalties`); each wrong answer draws one at random, so the
# player never knows what is behind a door.

fnm_penalty := enum:
    # Stuck in place inside a block of ice for FreezeSeconds, then back to the station entry.
    Freeze
    # An air vent appears under them and blasts them into the sky; on landing (or after YeetAirSeconds)
    # they are put back at the station entry.
    Yeet
    # A floor spike trap snaps up under them; after respawning they are put back at the station entry.
    Spike

# Big word shown under the red X.
FnmPenaltyLabel(Kind:fnm_penalty):string =
    if (Kind = fnm_penalty.Freeze) then "FROZEN!"
    else if (Kind = fnm_penalty.Yeet) then "YEET!"
    else "SPIKED!"
