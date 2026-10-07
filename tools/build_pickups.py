"""Place pickup pads (Item Spawners) in every other station hallway of the open UEFN project through UEFN MCP.

Aaron (2026-10-06): players pick up Boogie Bombs and Shockwave Grenades to use on each other. Every even station
(ARMED) gets a trail of PADS pads along each side wall in the stretch between where players land (450 cm in) and
the first obstacle (900 cm): one wall holds Boogie Bombs (5 s forced dance, no weapons, no building; any damage
ends it), the other Shockwave Grenades (punt a rival, or launch yourself over a hurdle), and the sides SWAP at each
armed station so no lane is always the "good" one. Pads are picked up by running over them (no E), hold one
grenade each, and respawn it every RESPAWN_SECONDS, so a chasing player finds them stocked too. The director's
skip guard (fnm_director.verse WatchSkip) sends a player who shockwaves over a door wall into a later hallway back
to their own station's entry.

Device: PID_CP_Devices_ItemSpawnerProp (Device_item_SpawnerV2, the holo pad with a spawn timer). Do not confuse it
with PID_CP_Devices_ItemSpawner, which is the Capture Item Spawner (flag stand). Its item list is the
toSpawnList of its Minigame_Spawner_Component ([{pickupToSpawn, pickupQuantity}]); throwables are
/Game/Athena/Items/Consumables/<Name>/Athena_<Name> item definitions, not WID_*: DanceGrenade (Boogie Bomb; _UC is
the 2.5 s uncommon), ShockwaveGrenade/Athena_ShockGrenade, KnockGrenade/Athena_KnockGrenade (Impulse),
IceGrenade/Athena_IceGrenade (Chiller), Grenade/Athena_Grenade, SmokeGrenade, StickyGrenade, GasGrenade (Stink).

Idempotent: every actor this script creates is tagged TAG; a run first deletes everything with TAG. Reads geometry
from the course actors (tools/build_course.py), so rerun after a course rebuild.

    python tools/build_pickups.py
"""
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import uefn_mcp as u  # noqa: E402
from build_course import ACTOR, DEV, OBJ, SCENE, TAG as COURSE_TAG, clear, props, ref, xform  # noqa: E402

TAG = "fnm_pickups"
SPAWNER = "/CR_Legacy/Playsets/PID_CP_Devices_ItemSpawnerProp.PID_CP_Devices_ItemSpawnerProp"
BOOGIE = "/Game/Athena/Items/Consumables/DanceGrenade/Athena_DanceGrenade.Athena_DanceGrenade"
SHOCKWAVE = "/Game/Athena/Items/Consumables/ShockwaveGrenade/Athena_ShockGrenade.Athena_ShockGrenade"
ITEMS = {"boogie": BOOGIE, "shockwave": SHOCKWAVE}


def armed(k):
    """Stations that get pads: every other one, from station 2 (station 1 is the clear warm-up hallway)."""
    return k % 2 == 0


# Pads along each wall, as distances (cm) from the hallway start. Players land 450 cm in; the first obstacle of any
# station is at 900 (OBSTACLES in build_course.py), and the ice station's first baffle wall stands there.
PADS = (480, 580, 680, 780)
PAD_IN = 150            # pad centre this far from the wall's inner face (the chalkboard hangs 15 cm off the right wall)
RESPAWN_SECONDS = 8.0
QUANTITY = 1            # grenades per pad
SETTINGS = {
    "enabledOnStart": True,
    "initialSpawnDelay": 1.0,            # the device's minimum
    "timeBetweenSpawnsSeconds": RESPAWN_SECONDS,
    "isPickupOnTouch": True,             # run over it, no E
    # Gravity drops the grenade onto the pad, where a walking player touches it. "None" left it hovering 2 m up, out
    # of reach (seen in play 2026-10-06: the pads looked stocked but a run along them picked up nothing).
    "itemInitialMovement": "Gravity",
    "isMeshVisibleDuringMinigame": True,
}


def build():
    print("removed", clear(TAG), "old pickup pads")
    found = u.call(SCENE, "find_actors", {"tag": COURSE_TAG, "collision_channels": []})["returnValue"]
    parts = {a["label"]: a["bounds"] for a in found if isinstance(a, dict) and re.fullmatch(r"FNM_S\d\d_(Floor|WallL|WallR)", a.get("label", ""))}
    stations = sorted({int(label[5:7]) for label in parts if label.endswith("_Floor")})
    flip = False
    for k in stations:
        if not armed(k):
            continue
        floor, left, right = (parts[f"FNM_S{k:02d}_{p}"] for p in ("Floor", "WallL", "WallR"))
        # Engine cubes have exact bounds: the floor's top face and start, the walls' inner faces (+X is the player's left).
        oy, z = floor["min"]["y"], floor["max"]["z"]
        sides = [("L", left["min"]["x"] - PAD_IN, "boogie"), ("R", right["max"]["x"] + PAD_IN, "shockwave")]
        if flip:
            sides = [(sides[0][0], sides[0][1], sides[1][2]), (sides[1][0], sides[1][1], sides[0][2])]
        flip = not flip
        for side, x, item in sides:
            for n, dy in enumerate(PADS, 1):
                pad(f"FNM_S{k:02d}_Pad{side}{n}", x, oy + dy, z, item)
            print(f"station {k}: {len(PADS)} {item} pads on the {'left' if side == 'L' else 'right'} at x={x:.0f} z={z:.0f}")


def pad(label, x, y, z, item):
    actor = u.call(DEV, "PlaceDevice", {"assetPath": ref(SPAWNER), "transform": xform(x, y, z)})["returnValue"]["refPath"]
    u.call(ACTOR, "add_tag", {"actor": ref(actor), "tag": TAG})
    u.call(ACTOR, "set_label", {"actor": ref(actor), "label": label})
    for key, value in SETTINGS.items():      # one key per call (a combined write can silently keep an old value)
        props(actor, {key: value})
    spawner = next(c["refPath"] for c in u.call(ACTOR, "get_components", {"actor": ref(actor)})["returnValue"]
                   if c["refPath"].endswith(".Minigame_Spawner_Component"))
    wanted = ITEMS[item]
    props(spawner, {"toSpawnList": [{"pickupToSpawn": ref(wanted), "pickupQuantity": QUANTITY}]})
    back = json.loads(u.call(OBJ, "get_properties", {"instance": ref(spawner), "properties": ["toSpawnList"]})["returnValue"])["toSpawnList"]
    if not back or (back[0].get("pickupToSpawn") or {}).get("refPath") != wanted or back[0].get("pickupQuantity") != QUANTITY:
        sys.exit(f"{label}: the item spawner refused {wanted}: {back}")
    opts = json.loads(u.call(OBJ, "get_properties", {"instance": ref(actor), "properties": list(SETTINGS)})["returnValue"])
    wrong = {k: opts.get(k) for k, v in SETTINGS.items() if opts.get(k) != v}
    if wrong:
        sys.exit(f"{label}: settings not taken: {wrong}")
    return actor


if __name__ == "__main__":
    build()
