"""Place pickup pads (Item Spawners) in every other station hallway of the open UEFN project through UEFN MCP.

Aaron (2026-10-06): players pick up Boogie Bombs and Shockwave Grenades to use on each other. Every even station
(ARMED) gets a trail of PADS pads along each side wall in the stretch between where players land (450 cm in) and
the first obstacle (900 cm): one wall holds Boogie Bombs (5 s forced dance, no weapons, no building; any damage
ends it), the other Shockwave Grenades (punt a rival, or launch yourself over a hurdle), and the sides SWAP at each
armed station so no lane is always the "good" one. Pads are picked up by running over them (no E), hold one
grenade each, and respawn it every RESPAWN_SECONDS, so a chasing player finds them stocked too. The director's
skip guard (fnm_director.verse WatchSkip) sends a player who shockwaves over a door wall into a later hallway back
to their own station's entry.

How a run-over hands the item over (Aaron 2026-10-08: with a full inventory "the grenades disappear" and never
arrive): a consumable on the pad is auto-picked by a touch whatever the pad's Pickup On Touch says (seen 2026-10-08
with it off: the grenade still went into the bag), so the fix is a second, reliable path. A hidden trigger over each
ROW of pads (Verse tags fnm_pickup + fnm_item_<kind>; ROW_ZONE covers the discs and the grenade's own pickup reach, a
150 cm zone per pad was missed by a player standing on the disc's edge) tells the director a player ran over the row.
The director fires the kind's GRANT trigger (fnm_grant + fnm_item_<kind>), to which an Item Granter holding that item
is bound (the loadout pattern in build_rigs.py): Keep All, grant "Only if Not Owned" (a player who just auto-picked one
gets no second), and "drop at the player's location if the inventory is full", so a full bag gets the grenade at its
feet instead of nothing. One grant per row per player every PickupRepeatSeconds (director). Proven 2026-10-08: a
player dropped onto a row trigger logged "pickup shockwave granted".

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
from build_course import ACTOR, DEV, OBJ, SCENE, TAG as COURSE_TAG, TRIGGER, clear, props, ref, verse_tags, xform  # noqa: E402
from build_rigs import GRANTER, TRIGGER_CLASS  # noqa: E402

TAG = "fnm_pickups"
SPAWNER = "/CR_Legacy/Playsets/PID_CP_Devices_ItemSpawnerProp.PID_CP_Devices_ItemSpawnerProp"
BOOGIE = "/Game/Athena/Items/Consumables/DanceGrenade/Athena_DanceGrenade.Athena_DanceGrenade"
SHOCKWAVE = "/Game/Athena/Items/Consumables/ShockwaveGrenade/Athena_ShockGrenade.Athena_ShockGrenade"
# Aaron (2026-10-07): "players should be able to pick up chug splashes". This content has no Chug Splash item definition
# (only the SpyTech STID and the Chili exotic, which the pad refuses); the Slap Splash is its successor: a throwable splash
# that heals 30 and grants slap energy. Every HEALING station (odd from 3) holds it along both walls.
SPLASH = "/ChronoConsumables/Gameplay/SlapSplash/WID_Chrono_SlapSplash.WID_Chrono_SlapSplash"
ITEMS = {"boogie": BOOGIE, "shockwave": SHOCKWAVE, "splash": SPLASH}


def armed(k):
    """Stations that get pads: every other one, from station 2 (station 1 is the clear warm-up hallway)."""
    return k % 2 == 0


def healing(k):
    """Odd stations from 3 hold Slap Splashes (heal) on both walls."""
    return k % 2 == 1 and k >= 3


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
    "isPickupOnTouch": True,             # run over it, no E (a consumable is auto-picked even with this off)
    # Gravity drops the grenade onto the pad, where a walking player touches it. "None" left it hovering 2 m up, out
    # of reach (seen in play 2026-10-06: the pads looked stocked but a run along them picked up nothing).
    "itemInitialMovement": "Gravity",
    "isMeshVisibleDuringMinigame": True,
}
# The run-over trigger over each row of pads: one zone (x across the hall, y along it, z up; the default zone is 600 cm
# per unit scale) centred on the row, hidden, firing on every entry after a short reset (the director rate-limits per
# player and row). 260 across covers a pad's 256 cm disc; 300 + 260 along covers the four pads at PADS' pitch.
ROW_ZONE = (260, PADS[-1] - PADS[0] + 260, 150)
TRIGGER_SETTINGS = {"visible in Game": False, "reset Delay": 0.5, "timesCanTrigger_Override": False, "triggerDelay": 0.0,
                    "triggeredByVehicles": False, "triggeredByWater": False, "triggeredByPhysicsProps": False}
# The granter per item kind, parked underground on its own row (tools/build_audio.py's row is at y -17000).
PARK = (-4000, -17800, -1500)
PITCH = 800
GRANT_SETTINGS = {"grantBehavior": "Keep All", "grantCondition": "Only if Not Owned",
                  "bDropItemsAtPlayerLocationIfInventoryIsFull": True, "giveExtraAmmo": 0, "equipItemOnGrant": 0}


def project_id():
    root = u.call("ValkyrieToolset.VerseToolset", "ListFiles", {"path": "", "bRecursive": False})
    return next(e["name"] for e in root["returnValue"] if e["type"] == "Directory" and "(" not in e["name"]).strip("/")


def build():
    project = project_id()
    print("removed", clear(TAG), "old pickup pads")
    granters(project)
    found = u.call(SCENE, "find_actors", {"tag": COURSE_TAG, "collision_channels": []})["returnValue"]
    parts = {a["label"]: a["bounds"] for a in found if isinstance(a, dict) and re.fullmatch(r"FNM_S\d\d_(Floor|WallL|WallR)", a.get("label", ""))}
    stations = sorted({int(label[5:7]) for label in parts if label.endswith("_Floor")})
    flip = False
    for k in stations:
        if not armed(k) and not healing(k):
            continue
        floor, left, right = (parts[f"FNM_S{k:02d}_{p}"] for p in ("Floor", "WallL", "WallR"))
        # Engine cubes have exact bounds: the floor's top face and start, the walls' inner faces (+X is the player's left).
        oy, z = floor["min"]["y"], floor["max"]["z"]
        sides = [("L", left["min"]["x"] - PAD_IN, "boogie"), ("R", right["max"]["x"] + PAD_IN, "shockwave")]
        if healing(k):
            sides = [("L", sides[0][1], "splash"), ("R", sides[1][1], "splash")]
        elif flip:
            sides = [(sides[0][0], sides[0][1], sides[1][2]), (sides[1][0], sides[1][1], sides[0][2])]
        if armed(k):
            flip = not flip
        for side, x, item in sides:
            for n, dy in enumerate(PADS, 1):
                pad(f"FNM_S{k:02d}_Pad{side}{n}", x, oy + dy, z, item)
            row_trigger(f"FNM_S{k:02d}_Row{side}_Trigger", x, oy + (PADS[0] + PADS[-1]) / 2, z, item, project)
            print(f"station {k}: {len(PADS)} {item} pads on the {'left' if side == 'L' else 'right'} at x={x:.0f} z={z:.0f}")


def row_trigger(label, x, y, z, item, project):
    """The hidden run-over trigger over one row of pads, tagged first (the tag component rebuilds a device's instanced
    sub-objects), then its options one key per call."""
    sx, sy, sz = (v / 600 for v in ROW_ZONE)
    trig = u.call(DEV, "PlaceDevice", {"assetPath": ref(TRIGGER), "transform": xform(x, y, z + ROW_ZONE[2] / 2, sx, sy, sz)})["returnValue"]["refPath"]
    u.call(ACTOR, "add_tag", {"actor": ref(trig), "tag": TAG})
    u.call(ACTOR, "set_label", {"actor": ref(trig), "label": label})
    verse_tags(trig, project, ["fnm_pickup", f"fnm_item_{item}"])
    for key, value in TRIGGER_SETTINGS.items():
        props(trig, {key: value})
    return trig


def granters(project):
    """One Item Granter per item kind, bound to its own hidden trigger (fnm_grant + fnm_item_<kind>); the director fires
    the trigger with the player as instigator and the granter hands that player one item."""
    for n, (kind, item) in enumerate(ITEMS.items()):
        x, y, z = PARK[0] + 2 * PITCH * n, PARK[1], PARK[2]
        trig = u.call(DEV, "PlaceDevice", {"assetPath": ref(TRIGGER), "transform": xform(x, y, z)})["returnValue"]["refPath"]
        grant = u.call(DEV, "PlaceDevice", {"assetPath": ref(GRANTER), "transform": xform(x + PITCH, y, z)})["returnValue"]["refPath"]
        for actor, label in ((trig, f"FNM_Grant_{kind}_Trigger"), (grant, f"FNM_Grant_{kind}_Granter")):
            u.call(ACTOR, "add_tag", {"actor": ref(actor), "tag": TAG})
            u.call(ACTOR, "set_label", {"actor": ref(actor), "label": label})
        verse_tags(trig, project, ["fnm_grant", f"fnm_item_{kind}"])
        props(trig, {"visible in Game": False, "reset Delay": 0.0})
        for key, value in GRANT_SETTINGS.items():
            props(grant, {key: value})
        props(grant, {"grantItem": {"eventSubscriptions": [{"object": {"refPath": trig},
                                                            "eventDescriptor": {"memberParent": {"refPath": TRIGGER_CLASS},
                                                                                "memberName": "OnTriggered"}}]}})
        item_list = json.loads(u.call(OBJ, "get_properties", {"instance": ref(grant), "properties": ["pickupItemList"]})["returnValue"])["pickupItemList"]["refPath"]
        props(item_list, {"itemListData": [{"itemDefinition": {"refPath": item}, "itemQuantity": QUANTITY}]})
        back = json.loads(u.call(OBJ, "get_properties", {"instance": ref(item_list), "properties": ["itemListData"]})["returnValue"])["itemListData"]
        opts = json.loads(u.call(OBJ, "get_properties", {"instance": ref(grant), "properties": list(GRANT_SETTINGS)})["returnValue"])
        wrong = {k: opts.get(k) for k, v in GRANT_SETTINGS.items() if opts.get(k) != v}
        if not back or (back[0].get("itemDefinition") or {}).get("refPath") != item:
            sys.exit(f"granter {kind}: the item granter refused {item}: {back}")
        if wrong:
            sys.exit(f"granter {kind}: settings not taken: {wrong}")
        print(f"granter {kind}: placed and bound to its trigger")


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
