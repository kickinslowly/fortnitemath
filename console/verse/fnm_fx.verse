# FNM console runtime -- the boss arena's Niagara effects (BOSS_MODE.md 15f). Verse can spawn a particle system that lives
# in the project (FNM_FX, authored by tools/build_fx.py through UEFN's Niagara MCP toolset); it cannot set a system's user
# parameters, so the laser's length is baked: it runs 18.3 m along the system's +X, the mega cannons' muzzle-to-waist
# distance (tools/build_bossmode.py prints it). The imports stay in this file: /UnrealEngine.com/Assets brings its own
# `mesh` and `material` names.

using { /UnrealEngine.com/Assets }
using { /UnrealEngine.com/Temporary/SpatialMath }
using { /Verse.org/Simulation }

# A laser shot from At along Dir (any length).
FnmSpawnLaser(At:vector3, Dir:vector3):void =
    Flat := Sqrt(Dir.X * Dir.X + Dir.Y * Dir.Y)
    Yaw := ArcTan(Dir.Y, Dir.X) * 180.0 / PiFloat
    Pitch := ArcTan(Dir.Z, Flat) * 180.0 / PiFloat
    SpawnParticleSystem(FNM_FX.NS_fnm_laser_asset, At, ?Rotation := MakeRotationFromYawPitchRollDegrees(Yaw, Pitch, 0.0))

# The electrical explosion where the lasers meet.
FnmSpawnImpact(At:vector3):void =
    SpawnParticleSystem(FNM_FX.NS_fnm_impact_asset, At)
