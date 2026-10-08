"""Place the boss arena's laser cannons (fnm_director.verse FireCannons) in the open UEFN project through UEFN MCP.

Aaron (2026-10-08): "when player steps on correct answer, we can see some epic laser cannon blast the boss and the boss
flail or get knocked back". Two cannons, one on each arena wall CANNON_Y into the hall, aimed at the boss platform: a
gunmetal bracket, turret ball and barrel with a glowing muzzle ring, built from engine shapes and painted with the
M_fnm_wall_steel / _glow materials (tools/import_art.py). At each muzzle sits a VFX Spawner (LaserBeams, burst,
Beam_Attack sound; Verse tag fnm_cannon_fx) the director enables for a second on every hit. For the boss: one VFX
Spawner (LightningBolt_01, Electric_Blast; fnm_cannon_strike) and BLASTS explosive devices (no damage, medium knockback,
audio + VFX; fnm_cannon_blast) parked under the platform, moved to the boss's feet and set off per hit, alternating.

Geometry comes from the arena actors (tools/build_course.py), so rerun after a course rebuild. The engine shapes are
scenery only: Verse cannot find or move them, which is why the devices carry the tags and the muzzle VFX spawner IS the
muzzle the director knows about.

Idempotent: every actor this script creates is tagged TAG; a run first deletes everything with TAG.

    python tools/build_cannon.py
    python tools/build_cannon.py --check     # list what is placed, with each device's read-back options
"""
import argparse
import json
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import uefn_mcp as u  # noqa: E402
from build_course import ACTOR, CUBE, DEV, OBJ, SCENE, TAG as COURSE_TAG, props, ref, verse_tags  # noqa: E402

TAG = "fnm_cannon_rig"
CYLINDER = "/Engine/BasicShapes/Cylinder.Cylinder"     # 100 cm tall along its Z, 100 cm across
SPHERE = "/Engine/BasicShapes/Sphere.Sphere"           # 100 cm across
VFX = "/CRD_VFX_Spawner/SetupAssets/PID_Device_VFX_Spawner_V2.PID_Device_VFX_Spawner_V2"
EXPLOSIVE = "/CreativeCoreDevices/SetupAssets/PID_Device_ExplosiveBarrel.PID_Device_ExplosiveBarrel"

CANNON_Y = 1100         # cannons this far into the arena: ahead of a player at the entry, so the flashes are in view
CANNON_IN = 110         # the turret ball's centre this far off the wall's inner face
CANNON_Z = 330          # the bracket's top this high above the floor (the walls are 600)
BRACKET = (170, 140, 30)   # bracket depth off the wall, width along the hall, thickness
BALL_D = 90
BARREL_LEN, BARREL_D = 260, 36
RING_LEN, RING_D = 16, 50
BOSS_EYE = 90           # aim this high above the platform top (a standing guard's chest)
BLASTS = 2
# Devices: the muzzle effect at each cannon, the strike moved onto the boss, the blast moved under its feet. "enabled On
# Phase" None keeps a VFX spawner off until Verse enables it; a burst effect also needs Restart() (its Verse digest).
MUZZLE_FX = {"enabled On Phase": "None", "visual_Effect": "LaserBeams", "effectType": "Burst",
             "sound_Effect": "Beam_Attack", "clearParticlesOnDisable": True}
STRIKE_FX = {"enabled On Phase": "None", "visual_Effect": "LightningBolt_01", "effectType": "Burst",
             "sound_Effect": "Electric_Blast", "clearParticlesOnDisable": True}
BLAST = {"visible During Game": False, "can be Damaged": False, "player Damage": 0, "structure Damage": 0,
         "knockback": "Medium", "play Audio / VFX": True, "explode on Proximity": False,
         "has Timed Detonation From Game Start": False, "time Until Reset Allowed": 0.5}
PARK_DROP = 600         # parked devices sit this far under the arena floor


def mount():
    root = u.call("ValkyrieToolset.VerseToolset", "ListFiles", {"path": "", "bRecursive": False})
    return next(e["name"] for e in root["returnValue"] if e["type"] == "Directory" and "(" not in e["name"]).rstrip("/")


def found(tag):
    r = u.call(SCENE, "find_actors", {"tag": tag, "collision_channels": []})
    actors = r if isinstance(r, list) else r.get("returnValue", [])
    return [a for a in actors if isinstance(a, dict)]


def clear():
    actors = found(TAG)
    for a in actors:
        u.call(SCENE, "remove_from_scene", {"actor": ref(a["actorPath"])})
    return len(actors)


def tagged(actor, label):
    u.call(ACTOR, "add_tag", {"actor": ref(actor), "tag": TAG})
    u.call(ACTOR, "set_label", {"actor": ref(actor), "label": label})
    return actor


def shape(asset, label, x, y, z, sx, sy, sz, pitch=0.0, yaw=0.0, material=None):
    r = u.call(SCENE, "add_to_scene_from_asset", {
        "asset_path": asset, "name": label,
        "xform": {"location": {"x": x, "y": y, "z": z}, "rotation": {"pitch": pitch, "yaw": yaw, "roll": 0},
                  "scale": {"x": sx, "y": sy, "z": sz}}})
    actor = tagged(r["returnValue"]["refPath"], label)
    if material:
        comp = json.loads(u.call(OBJ, "get_properties", {"instance": ref(actor), "properties": ["staticMeshComponent"]})["returnValue"])
        props(comp["staticMeshComponent"]["refPath"], {"overrideMaterials": [ref(material)]})
    return actor


def device(asset, label, x, y, z, pitch=0.0, yaw=0.0):
    r = u.call(DEV, "PlaceDevice", {"assetPath": ref(asset), "transform": {
        "location": {"x": x, "y": y, "z": z}, "rotation": {"pitch": pitch, "yaw": yaw, "roll": 0},
        "scale": {"x": 1, "y": 1, "z": 1}}})
    return tagged(r["returnValue"]["refPath"], label)


def settings(actor, values, label):
    """One key per call (a combined write can silently keep an old value); then read back and report differences."""
    for key, value in values.items():
        try:
            props(actor, {key: value})
        except RuntimeError as e:
            print(f"  {label}: could not set {key}: {str(e)[:120]}")
    back = json.loads(u.call(OBJ, "get_properties", {"instance": ref(actor), "properties": list(values)})["returnValue"])
    wrong = {k: back.get(k) for k, v in values.items() if back.get(k) != v}
    if wrong:
        print(f"  {label}: read back differently: {wrong}")
    return wrong


def aim(dx, dy, dz):
    """Pitch and yaw (degrees) that turn an engine cylinder's own Z axis onto the unit direction (dx, dy, dz).
    UE pitch turns about Y (nose up tips the up-vector toward -X), yaw about Z: up -> (-sinP cosY, -sinP sinY, cosP)."""
    p = math.degrees(math.acos(max(-1.0, min(1.0, dz))))
    y = math.degrees(math.atan2(-dy, -dx))
    return p, y


def arena():
    parts = {a["label"]: a["bounds"] for a in found(COURSE_TAG) if a.get("label", "").startswith("FNM_Arena_")}
    floor, left, right, platform = (parts[f"FNM_Arena_{p}"] for p in ("Floor", "WallL", "WallR", "Platform"))
    ox = (floor["min"]["x"] + floor["max"]["x"]) / 2
    oy, ztop = floor["min"]["y"], floor["max"]["z"]
    boss = (ox, (platform["min"]["y"] + platform["max"]["y"]) / 2, platform["max"]["z"] + BOSS_EYE)
    return ox, oy, ztop, left["min"]["x"], right["max"]["x"], boss


def cannon(side, face, oy, ztop, boss, project, steel, glow):
    """One cannon on the wall whose inner face is at x = face (side L: +X wall, the player's left)."""
    out = 1 if side == "L" else -1          # from the wall into the hall is -X on the left wall, +X on the right
    bd, bw, bt = BRACKET
    cy = oy + CANNON_Y
    z = ztop + CANNON_Z
    shape(CUBE, f"FNM_Cannon{side}_Bracket", face - out * bd / 2, cy, z - bt / 2, bd / 100, bw / 100, bt / 100, material=steel)
    ball = (face - out * CANNON_IN, cy, z + BALL_D / 2)
    shape(SPHERE, f"FNM_Cannon{side}_Ball", *ball, BALL_D / 100, BALL_D / 100, BALL_D / 100, material=steel)
    dx, dy, dz = boss[0] - ball[0], boss[1] - ball[1], boss[2] - ball[2]
    length = math.hypot(dx, dy, dz)
    d = (dx / length, dy / length, dz / length)
    pitch, yaw = aim(*d)
    along = lambda k: tuple(b + k * c for b, c in zip(ball, d))   # noqa: E731
    shape(CYLINDER, f"FNM_Cannon{side}_Barrel", *along(BARREL_LEN / 2 + 10), BARREL_D / 100, BARREL_D / 100, BARREL_LEN / 100,
          pitch, yaw, material=steel)
    shape(CYLINDER, f"FNM_Cannon{side}_Ring", *along(BARREL_LEN + 10 - RING_LEN / 2), RING_D / 100, RING_D / 100, RING_LEN / 100,
          pitch, yaw, material=glow)
    muzzle = along(BARREL_LEN + 30)
    fx = device(VFX, f"FNM_Cannon{side}_Fx", *muzzle, pitch, yaw)
    verse_tags(fx, project, ["fnm_cannon_fx"])     # tag first: the tag component rebuilds a device's sub-objects
    settings(fx, MUZZLE_FX, f"Cannon{side}_Fx")
    print(f"cannon {side}: ball at ({ball[0]:.0f}, {ball[1]:.0f}, {ball[2]:.0f}), muzzle at ({muzzle[0]:.0f}, {muzzle[1]:.0f}, "
          f"{muzzle[2]:.0f}), aimed pitch {pitch:.1f} yaw {yaw:.1f} over {length / 100:.1f} m")


def build():
    project = mount().strip("/")
    art = f"{mount()}/FNM_Art"
    steel, glow = (f"{art}/M_fnm_wall_{k}.M_fnm_wall_{k}" for k in ("steel", "glow"))
    print("removed", clear(), "old cannon actors")
    ox, oy, ztop, left_face, right_face, boss = arena()
    cannon("L", left_face, oy, ztop, boss, project, steel, glow)
    cannon("R", right_face, oy, ztop, boss, project, steel, glow)
    park_z = ztop - PARK_DROP
    strike = device(VFX, "FNM_Cannon_Strike", ox, boss[1], park_z)
    verse_tags(strike, project, ["fnm_cannon_strike"])
    settings(strike, STRIKE_FX, "Cannon_Strike")
    for n in range(BLASTS):
        blast = device(EXPLOSIVE, f"FNM_Cannon_Blast{n + 1}", ox + 300 * (n + 1), boss[1], park_z)
        verse_tags(blast, project, ["fnm_cannon_blast"])
        settings(blast, BLAST, f"Cannon_Blast{n + 1}")
    u.call("editor_toolset.toolsets.asset.AssetTools", "save_assets", {"asset_paths": []})
    print(f"cannons built: boss aim point ({boss[0]:.0f}, {boss[1]:.0f}, {boss[2]:.0f}); strike + {BLASTS} blasts parked at z {park_z:.0f}")


def check():
    actors = found(TAG)
    print(len(actors), "cannon actors")
    for a in sorted(actors, key=lambda a: a.get("label", "")):
        label = a.get("label", "")
        if "_Fx" in label or "_Strike" in label or "_Blast" in label:
            want = BLAST if "_Blast" in label else STRIKE_FX if "_Strike" in label else MUZZLE_FX
            back = json.loads(u.call(OBJ, "get_properties", {"instance": ref(a["actorPath"]), "properties": list(want)})["returnValue"])
            print(f"  {label:24} {back}")
        else:
            b = a.get("bounds", {})
            print(f"  {label:24} {json.dumps(b.get('min', {}))} .. {json.dumps(b.get('max', {}))}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true", help="list the placed cannon actors and the devices' read-back options")
    a = ap.parse_args()
    check() if a.check else build()
