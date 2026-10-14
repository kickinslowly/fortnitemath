# FNM console runtime -- the project's Niagara effects: the boss arenas' (BOSS_MODE.md 15f, 15g) and the race's right-answer
# and boost effects (end of file). Verse can spawn a particle system that
# lives in the project (FNM_FX, authored by tools/build_fx.py through UEFN's Niagara MCP toolset); it cannot set a system's
# user parameters, so the laser's length is baked: NS_fnm_laser runs 18.3 m along the system's +X, the boss battle's mega
# cannons' muzzle-to-waist distance (tools/build_bossmode.py prints it); NS_fnm_laser_race 5.1 m, the race finale's
# (tools/build_race_boss.py laser_length, BOSS_MODE.md 16). The imports stay in this file: /UnrealEngine.com/Assets brings its own
# `mesh` and `material` names. Nothing here knows which arena it serves: callers pass points and directions.

using { /UnrealEngine.com/Assets }
using { /UnrealEngine.com/Temporary/SpatialMath }
using { /Verse.org/Simulation }

# Seconds NS_fnm_muzzle charges (cyan specks pulled into the mouth) before its flash (tools/build_fx.py CHARGE): a laser
# fired this long after FnmSpawnMuzzle leaves the muzzle with the flash.
FnmMuzzleCharge : float = 0.15

# The mega cannon's coils sit this far (cm) behind the beam's muzzle point along the barrel: (CANNON_MUZZLE - CANNON_COIL)
# along the barrel x CANNON_SCALE, plus the MUZZLE_AHEAD cm the muzzle point stands ahead of the mouth
# (tools/build_bossmode.py; tests/test_bossmode_layout.py ties the two).
FnmCannonCoilBack : float = 252.0

# The same for the race finale's smaller cannons (tools/build_race_boss.py coil_back(); a test ties the two).
FnmRaceCannonCoilBack : float = 189.0

# A rotation that turns a system's local +X onto Dir (no roll).
FnmAimAlong(Dir:vector3)<transacts>:rotation =
    Flat := Sqrt(Dir.X * Dir.X + Dir.Y * Dir.Y)
    Yaw := ArcTan(Dir.Y, Dir.X) * 180.0 / PiFloat
    Pitch := ArcTan(Dir.Z, Flat) * 180.0 / PiFloat
    MakeRotationFromYawPitchRollDegrees(Yaw, Pitch, 0.0)

# A laser shot from At along Dir (any length).
FnmSpawnLaser(At:vector3, Dir:vector3):void =
    SpawnParticleSystem(FNM_FX.NS_fnm_laser_asset, At, ?Rotation := FnmAimAlong(Dir))

# The race finale's laser shot: the same, 5.1 m long (NS_fnm_laser_race).
FnmSpawnRaceLaser(At:vector3, Dir:vector3):void =
    SpawnParticleSystem(FNM_FX.NS_fnm_laser_race_asset, At, ?Rotation := FnmAimAlong(Dir))

# A cannon's muzzle discharge at At, the shot leaving along Dir: FnmMuzzleCharge s of charge, then the flash, the shock
# ring, the spark cone and arcs (1 s, then the instance dies on its own).
FnmSpawnMuzzle(At:vector3, Dir:vector3):void =
    SpawnParticleSystem(FNM_FX.NS_fnm_muzzle_asset, At, ?Rotation := FnmAimAlong(Dir))

# Back cm behind Muzzle along Dir's level heading: where a level barrel's coils are, when Dir is the (possibly pitched)
# shot leaving its muzzle at Muzzle on the barrel's heading.
FnmBehindOnBarrel(Muzzle:vector3, Dir:vector3, Back:float)<transacts>:vector3 =
    Flat := Sqrt(Dir.X * Dir.X + Dir.Y * Dir.Y)
    if (Flat > 0.0001):
        Muzzle - vector3{X := Dir.X / Flat, Y := Dir.Y / Flat, Z := 0.0} * Back
    else:
        Muzzle

# The always-on coil crackle at At, +X along Dir's level heading (the barrel). It loops forever: keep the cancelable,
# spawn it once per cannon, and Cancel() it to stop it.
FnmSpawnCoil(At:vector3, Dir:vector3):cancelable =
    SpawnParticleSystem(FNM_FX.NS_fnm_coil_asset, At, ?Rotation := FnmAimAlong(vector3{X := Dir.X, Y := Dir.Y, Z := 0.0}))

# One coil crackle per cannon, from each cannon's beam transform (its +Z along the shot, at the muzzle point): Back cm
# behind it on the barrel. Keep the cancelables; call it once per arena, so the looping systems never stack.
FnmSpawnCoils(Beams:[]transform, Back:float):[]cancelable =
    for (Full : Beams):
        Dir := Full.Rotation.GetLocalUp()
        FnmSpawnCoil(FnmBehindOnBarrel(Full.Translation, Dir, Back), Dir)

# The electrical explosion where the lasers meet.
FnmSpawnImpact(At:vector3):void =
    SpawnParticleSystem(FNM_FX.NS_fnm_impact_asset, At)

# --- The race's right-answer and boost effects (tools/build_fx.py; G9 spectacle, reviews/race-2026-10-13/sources/spectacle.md
# 1a). Spawns are global: every player sees every one, which is the point of the pillar and the trail.

# How high above a barrier's base (the vestibule floor) the gate burst fires: chest height in the 384 cm doorway.
FnmGateBurstHeight : float = 190.0

# A right answer opening the barrier whose base centre is At: NS_fnm_gate_burst (0.7 s), its +X along Ahead (the way on),
# so its shock ring stands in the barrier plane.
FnmSpawnGateBurst(At:vector3, Ahead:vector3):void =
    SpawnParticleSystem(FNM_FX.NS_fnm_gate_burst_asset, At + vector3{X := 0.0, Y := 0.0, Z := FnmGateBurstHeight}, ?Rotation := FnmAimAlong(Ahead))

# The pillar of light standing on Base (a vestibule floor): NS_fnm_sky_pillar runs 40 m up world +Z for 1.2 s (no rotation).
FnmSpawnPillar(Base:vector3):void =
    SpawnParticleSystem(FNM_FX.NS_fnm_sky_pillar_asset, Base)

# Seconds between two puffs of a boosting player's comet tail (NS_fnm_trail_*: 20 particles living 0.6 s each, so 16
# boosting players stay near 1.5k particles alive, spectacle 1a's budget).
FnmTrailEvery : float = 0.12

# How far under a fort_character's position (its capsule centre, ~77 cm above the feet) a trail puff goes: at the feet,
# where the third-person camera passes over the puffs instead of through them.
FnmTrailDrop : float = 60.0

# The boost trail's tier for a streak: 0 cyan (streak 1-2), 1 gold (3-5), 2 fire (6+).
FnmTrailTier(Streak:int)<transacts>:int =
    if (Streak >= 6) then 2 else if (Streak >= 3) then 1 else 0

FnmTrailNames : []string = array{"cyan", "gold", "fire"}

# One puff of the comet tail for a streak, under a character's position At (its capsule centre). (The asset type,
# particle_system, lives in /Verse.org/Assets, whose names clash here, so the tier picks the call, not a value.)
FnmSpawnTrail(Streak:int, At:vector3):void =
    Feet := At - vector3{X := 0.0, Y := 0.0, Z := FnmTrailDrop}
    Tier := FnmTrailTier(Streak)
    if (Tier = 2) then SpawnParticleSystem(FNM_FX.NS_fnm_trail_fire_asset, Feet)
    else if (Tier = 1) then SpawnParticleSystem(FNM_FX.NS_fnm_trail_gold_asset, Feet)
    else SpawnParticleSystem(FNM_FX.NS_fnm_trail_cyan_asset, Feet)
