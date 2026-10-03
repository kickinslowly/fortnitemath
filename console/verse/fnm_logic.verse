# FNM console runtime -- pure logic (no devices, no UI).
# Implements PROTOCOL.md section 6: station tier, per-tier pools, draw without replacement.
# Every function is <transacts> so it may be called from any context, including `if` conditions.

using { /Verse.org/Random }

# Result of one draw: the drawn item index (into fnm_cartridge.Items) and the deck left over.
# ItemIndex is -1 only when the pool for that tier is empty (a cartridge that failed validation).
fnm_draw := struct:
    ItemIndex : int
    Rest : []int

# Integer division for non-negative operands, failure-safe (Quotient is <decides>).
# Returns 0 when Denominator is 0.
FnmDiv(Numerator:int, Denominator:int)<transacts>:int =
    var Result : int = 0
    if (Q := Quotient[Numerator, Denominator]):
        set Result = Q
    Result

# PROTOCOL 6, linear map: stage s (1-based) of S stations, T tiers.
#   tier = 1 + (2*(s-1)*(T-1) + (S-1)) div (2*(S-1))   for S > 1, else 1
FnmAutoTier(Stage:int, StageCount:int, TierCount:int)<transacts>:int =
    var Tier : int = 1
    if (StageCount > 1, TierCount > 1):
        set Tier = 1 + FnmDiv(2 * (Stage - 1) * (TierCount - 1) + (StageCount - 1), 2 * (StageCount - 1))
    Clamp(Tier, 1, Max(TierCount, 1))

# PROTOCOL 6, hand-set difficulty position p% (0..100):
#   tier = 1 + (2*p*(T-1) + 100) div 200
FnmOverrideTier(Percent:int, TierCount:int)<transacts>:int =
    P := Clamp(Percent, 0, 100)
    Tier := 1 + FnmDiv(2 * P * (TierCount - 1) + 100, 200)
    Clamp(Tier, 1, Max(TierCount, 1))

# Station tier: OverridePercent < 0 means "auto" (linear), otherwise a percent difficulty position.
FnmTierForStage(Stage:int, StageCount:int, TierCount:int, OverridePercent:int)<transacts>:int =
    var Tier : int = 1
    if (OverridePercent >= 0):
        set Tier = FnmOverrideTier(OverridePercent, TierCount)
    else:
        set Tier = FnmAutoTier(Stage, StageCount, TierCount)
    Tier

# Indices into Items whose Tier equals Tier.
FnmPoolForTier(Items:[]fnm_item, Tier:int)<transacts>:[]int =
    for (Index -> Item : Items, Item.Tier = Tier):
        Index

# Pools[t - 1] = item indices of tier t, for t in 1..TierCount.
FnmBuildTierPools(Items:[]fnm_item, TierCount:int)<transacts>:[][]int =
    for (Tier := 1..TierCount):
        FnmPoolForTier(Items, Tier)

# A fresh, independently shuffled deck per tier (one set per player).
FnmShuffleAll(Pools:[][]int)<transacts>:[][]int =
    for (Pool : Pools):
        Shuffle(Pool)

# Draw without replacement: take the head of Deck; if Deck is empty, reshuffle the full Pool first.
FnmDraw(Deck:[]int, Pool:[]int)<transacts>:fnm_draw =
    var Source : []int = Deck
    if (Source.Length = 0):
        set Source = Shuffle(Pool)
    var Result : fnm_draw = fnm_draw{ItemIndex := -1, Rest := array{}}
    if (First := Source[0]):
        Rest := for (Index -> Value : Source, Index > 0):
            Value
        set Result = fnm_draw{ItemIndex := First, Rest := Rest}
    Result

# 0 -> "A", 1 -> "B", 2 -> "C", 3 -> "D".
FnmChoiceLetter(Index:int)<transacts>:string =
    var Letter : string = "?"
    if (Index = 0):
        set Letter = "A"
    else if (Index = 1):
        set Letter = "B"
    else if (Index = 2):
        set Letter = "C"
    else if (Index = 3):
        set Letter = "D"
    Letter

# "A: 11     B: 14     C: 10" -- only as many letters as the item has choices.
FnmChoicesLine(Choices:[]string)<transacts>:string =
    var Line : string = ""
    for (Index -> Choice : Choices):
        if (Index > 0):
            set Line = Line + "     "
        set Line = Line + FnmChoiceLetter(Index) + ": " + Choice
    Line

# Name of tier Tier from the cartridge's tier table ("" if missing).
FnmTierName(Tiers:[]fnm_tier, Tier:int)<transacts>:string =
    var Name : string = ""
    for (Entry : Tiers, Entry.Tier = Tier):
        set Name = Entry.Name
    Name

# "First-try accuracy: 7 / 10 (70%)"
FnmAccuracyLine(FirstTryCorrect:int, Total:int)<transacts>:string =
    Percent := FnmDiv(FirstTryCorrect * 100, Total)
    "First-try accuracy: {FirstTryCorrect} / {Total} ({Percent}%)"
