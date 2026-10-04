"""Place the penalty rigs (console/verse/fnm_rig.verse) in the open UEFN project through UEFN MCP.

Each rig is a prop or device parked underground, out of sight, that the director moves onto a punished
player: an ice cube (Freeze), a ring of spears that burst out of the floor (Spike), a tilted air vent (Yeet).
Also the orbit camera the director pushes onto frozen/spiked players, and the starting loadout: an item granter
(pistol + spare ammo) bound to a hidden trigger that the director fires for each joining player.
COPIES of each so players punished at the same moment each get their own.
Real Fortnite traps can't be used: placed traps (BR TID_Floor_Spikes_Athena_R_T03 and the Creative
TID_Figment_Floor_Spikes_Athena_R_T01) both fail island validation as illegal references.

Idempotent: every actor this script creates is tagged TAG; a run first deletes everything with TAG.

    python tools/build_rigs.py [--copies 4]
"""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import uefn_mcp as u  # noqa: E402
from build_course import ACTOR, DEV, SCENE, ref, verse_tags, xform  # noqa: E402

TAG = "fnm_rigs"
PISTOL = "/Game/Athena/Items/Weapons/WID_Pistol_SemiAuto_Athena_R_Ore_T03.WID_Pistol_SemiAuto_Athena_R_Ore_T03"
TRIGGER = "/CreativeCoreDevices/SetupAssets/PID_Device_Trigger.PID_Device_Trigger"
# The binding only fires with the event's owning class set (MemberParent); the name alone saves but does nothing.
TRIGGER_CLASS = "/CreativeCoreDevices/Device_Trigger_V2.Device_Trigger_V2_C"
GRANTER = "/CR_Legacy/Playsets/PID_CP_Devices_ItemGranter.PID_CP_Devices_ItemGranter"
PARK = (-4000, -8000, -1500)   # underground, away from the course
PITCH = 800                    # spacing between parked parts (cm)

# Visual-only props: with collision the third-person camera is pushed inside the cube or spear ring and the view
# closes in (bNoCameraCollision is not settable from MCP; bNoCollision is).
PROP = {"bNoCollision": True}

# (label, asset, Verse tag, scale, placed as device?, parts per copy (0 = exactly one), properties)
RIGS = [
    # 2 m Fortnite ice cube, sized to a standing player (bigger fills the third-person view).
    ("Ice", "/CR_Legacy/Playsets/PlaysetProps/PPID_CR_Legacy_Apollo_IceCube_NoLoot.PPID_CR_Legacy_Apollo_IceCube_NoLoot",
     "fnm_ice", (0.9, 0.9, 1.05), False, 1, PROP),
    # Coliseum spear (1.8 m, pivot mid-shaft) scaled to 2.7 m; the director rings SpearCount of them.
    ("Spear", "/CR_Legacy/Playsets/PlaysetProps/PPID_CR_Legacy_Apollo_Coliseum_Spear_01.PPID_CR_Legacy_Apollo_Coliseum_Spear_01",
     "fnm_spike", (1.5, 1.5, 1.5), False, 6, PROP),
    # Air vent moved under a yeeted player, tilted back so its gust throws them down the hallway; no skydive, so
    # they can't glide off into other rooms. Real movement, unlike per-tick TeleportTo (choppy in play). (A
    # directional launcher would aim better, but it has no Verse class, so Verse can't find or move it.)
    ("Yeet", "/CreativeCoreDevices/SetupAssets/PID_Device_AirVent_V2.PID_Device_AirVent_V2",
     "fnm_yeet", (1.0, 1.0, 1.0), True, 1,
     {"putInDiveMode": False, "launch Strength Modifier": 0.5}),
    # One orbit camera, pushed onto a player only while frozen/spiked: further out than the default camera, and
    # walls go see-through instead of pulling it in.
    ("PenaltyCam", "/CRD_CameraModes/SetupAssets/PID_CP_Devices_Orbit.PID_CP_Devices_Orbit",
     "fnm_penalty_cam", (1.0, 1.0, 1.0), True, 0,
     {"addToPlayersOnStart": False, "distance": 900, "pitchRotationIdeal": -30, "fieldOfView": 90,
      "collisionType": "Transparency", "useAsEliminationCamera": "No",
      "removeOnElimination": True}),
]


def props_set(actor, values):
    """Set each property on its own, so one MCP refuses doesn't stop the rest; report the refusals."""
    for key, value in values.items():
        try:
            u.call("editor_toolset.toolsets.object.ObjectTools", "set_properties",
                   {"instance": ref(actor), "values": json.dumps({key: value})})
        except RuntimeError:
            print(f"  could not set {key} on {actor.rsplit('.', 1)[-1]}")


def clear(tag):
    found = u.call(SCENE, "find_actors", {"tag": tag, "collision_channels": []})
    actors = found if isinstance(found, list) else found.get("returnValue", [])
    for a in actors:
        u.call(SCENE, "remove_from_scene", {"actor": ref(a["actorPath"] if isinstance(a, dict) else a)})
    return len(actors)


def build(copies):
    root = u.call("ValkyrieToolset.VerseToolset", "ListFiles", {"path": "", "bRecursive": False})
    project = next(e["name"] for e in root["returnValue"] if e["type"] == "Directory" and "(" not in e["name"]).strip("/")
    print("removed", clear(TAG), "old rig actors;", clear("fnm_test"), "test actors")
    for row, (label, asset, vtag, (sx, sy, sz), is_device, per_copy, values) in enumerate(RIGS):
        count = copies * per_copy if per_copy else 1
        for n in range(count):
            x, y, z = PARK[0] + PITCH * n, PARK[1] - PITCH * row, PARK[2]
            t = xform(x, y, z, sx, sy, sz)
            if is_device:
                r = u.call(DEV, "PlaceDevice", {"assetPath": ref(asset), "transform": t})
            else:
                r = u.call(SCENE, "add_to_scene_from_asset", {"asset_path": asset, "name": f"FNM_Rig_{label}{n + 1}", "xform": t})
            actor = r["returnValue"]["refPath"]
            u.call(ACTOR, "add_tag", {"actor": ref(actor), "tag": TAG})
            u.call(ACTOR, "set_label", {"actor": ref(actor), "label": f"FNM_Rig_{label}{n + 1}"})
            verse_tags(actor, project, [vtag])
            props_set(actor, values)
        print(label, count, "placed")
    loadout(project)


def loadout(project):
    """Starting pistol. Verse can't find the legacy item granter by tag, wire it by @editable reference (MCP
    rejects it), or reach the player's (non scene-graph) inventory, so: a hidden trigger tagged fnm_loadout
    that Verse fires with the player as instigator, and the granter's Grant Item bound to that trigger."""
    x, y, z = PARK[0], PARK[1] - PITCH * len(RIGS), PARK[2]
    trig = u.call(DEV, "PlaceDevice", {"assetPath": ref(TRIGGER), "transform": xform(x, y, z)})["returnValue"]["refPath"]
    grant = u.call(DEV, "PlaceDevice", {"assetPath": ref(GRANTER), "transform": xform(x + PITCH, y, z)})["returnValue"]["refPath"]
    for actor, label in ((trig, "FNM_Rig_LoadoutTrigger"), (grant, "FNM_Rig_LoadoutGranter")):
        u.call(ACTOR, "add_tag", {"actor": ref(actor), "tag": TAG})
        u.call(ACTOR, "set_label", {"actor": ref(actor), "label": label})
    verse_tags(trig, project, ["fnm_loadout"])
    props_set(trig, {"visible in Game": False, "reset Delay": 0.0})
    props_set(grant, {"grantBehavior": "Keep All", "grantCondition": "Only if Not Owned", "giveExtraAmmo": 1, "equipItemOnGrant": 1,
                      "grantItem": {"eventSubscriptions": [{"object": {"refPath": trig},
                                                            "eventDescriptor": {"memberParent": {"refPath": TRIGGER_CLASS},
                                                                                "memberName": "OnTriggered"}}]}})
    items = u.call("editor_toolset.toolsets.object.ObjectTools", "get_properties",
                   {"instance": ref(grant), "properties": ["pickupItemList"]})["returnValue"]
    item_list = json.loads(items)["pickupItemList"]["refPath"]
    props_set(item_list, {"itemListData": [{"itemDefinition": {"refPath": PISTOL}, "itemQuantity": 1}]})
    print("loadout granter + trigger placed")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--copies", type=int, default=4)
    build(ap.parse_args().copies)
