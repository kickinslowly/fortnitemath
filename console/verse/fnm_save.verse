# FNM console runtime -- what the island remembers about a player between sessions (Verse persistence).
# Persistence is per player: the island keeps each player's own bests, never a list of other players' names, so the
# all-time screen (fnm_director HallLoop) can only rank the players who are on the island right now.

using { /Verse.org/Simulation }

# A player's all-time best finishing time per skill, keyed by cartridge id (not slot index: the slot changes as
# cartridges are inserted). Persistable: never remove or retype a field; only add ones with defaults.
fnm_saved := class<final><persistable>:
    BestTimes : [string]float = map{}

var FnmSaved : weak_map(player, fnm_saved) = map{}

# Player's all-time best for cartridge Id; fails when they have none.
FnmSavedBest(Player:player, Id:string)<transacts><decides>:float =
    FnmSaved[Player].BestTimes[Id]

# Records Time as Player's all-time best for cartridge Id (the caller decides it is a new best).
FnmSaveBest(Player:player, Id:string, Time:float)<transacts>:void =
    var Bests : [string]float = map{}
    if (Saved := FnmSaved[Player]):
        set Bests = Saved.BestTimes
    if (set Bests[Id] = Time) {}
    if (set FnmSaved[Player] = fnm_saved{BestTimes := Bests}) {}
