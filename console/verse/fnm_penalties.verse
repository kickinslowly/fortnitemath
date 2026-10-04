# FNM console runtime -- what happens to a player who walks through a wrong door.
# A map picks its pool in map.json "penalties" (generated into FnmMapPenalties, fnm_map_profile.verse); each
# wrong answer draws one at random, so the player never knows what is behind a door.

fnm_penalty := enum:
    # Stuck in place inside a block of ice for FreezeSeconds (frosted screen), then back to the station entry.
    Freeze
    # Flung backward down the hallway in a high arc, landing back at the station entry.
    Yeet
    # A ring of spears bursts up around them; after respawning they are put back at the station entry.
    Spike
    # Back at the station entry, slowed to a crawl (brown-tinted screen) for MudSeconds.
    Mud
    # Back at the station entry, the view spins, then the screen blurs in and out for DizzySeconds.
    Dizzy
    # The lights go out; they wake up back at the station entry.
    Blackout

# Big word shown under the red X.
FnmPenaltyLabel(Kind:fnm_penalty):string =
    if (Kind = fnm_penalty.Freeze) then "FROZEN!"
    else if (Kind = fnm_penalty.Yeet) then "YEET!"
    else if (Kind = fnm_penalty.Spike) then "SPIKED!"
    else if (Kind = fnm_penalty.Mud) then "STUCK IN MUD!"
    else if (Kind = fnm_penalty.Dizzy) then "DIZZY!"
    else "LIGHTS OUT!"
