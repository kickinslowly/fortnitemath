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
    python tools/build_rigs.py --loadout-only    # replace just the two loadout trigger + granter pairs (LOADOUTS)
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
    # Mud: one movement modulator, never touched (no pad, invisible); Verse calls Activate(player) on it. Its
    # Duration (3 s default) is not settable from MCP, so the director re-activates it for MudSeconds.
    # (speedState follows speed by itself.)
    ("Mud", "/CreativeCoreDevices/SetupAssets/PID_Device_MovementModulator.PID_Device_MovementModulator",
     "fnm_mud", (1.0, 1.0, 1.0), True, 0,
     {"speed": 0.5, "visibleDuringGame": "No",
      "pad has Collision": False, "resetDelay": 0}),
    # Boost: the same kind of modulator, faster; the director activates it after a first-try right answer.
    # Speed 2.0: Aaron couldn't feel 1.6 (2026-10-04 playtest).
    ("Boost", "/CreativeCoreDevices/SetupAssets/PID_Device_MovementModulator.PID_Device_MovementModulator",
     "fnm_boost", (1.0, 1.0, 1.0), True, 0,
     {"speed": 2.0, "visibleDuringGame": "No",
      "pad has Collision": False, "resetDelay": 0}),
] + [
    # Screen effects, one post-process device each, blended in and out per player from Verse. Starting strength
    # 0 so nobody sees one until BlendIn(player).
    # Dizzy: a radial blur the director pulses in and out (BlendIn/BlendOut every DizzyPulseSeconds), so its
    # blends are short and even. PP_Crazy's colour swirl confused Aaron rather than dizzying him (2026-10-04).
    (label, "/CRD_PostProcess/SetupAssets/PID_CP_Devices_PostProcess.PID_CP_Devices_PostProcess", vtag,
     (1.0, 1.0, 1.0), True, 0,
     {"postProcessEffect": {"refPath": f"/Game/Creative/PostProcess/{fx}.{fx}_C"}, "effectDuration": 0,
      "startingStrength": 0, "blendInStrength": 1, "blendInDuration": blend_in, "blendOutDuration": blend_out})
    for label, vtag, fx, blend_in, blend_out in [("FxFrost", "fnm_pp_frost", "PP_Frost", 0.3, 0.8),
                                                 ("FxMud", "fnm_pp_mud", "PP_Sepia", 0.3, 0.8),
                                                 ("FxDizzy", "fnm_pp_dizzy", "PP_RadialBlur", 0.5, 0.5)]
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
    project = project_name()
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


# The two loadout granters (loadout()), each bound to its own hidden trigger: (label, Verse tag, granter settings).
# fnm_loadout: the pistol on a respawn, Keep All (an eliminated player has dropped everything already, island
# dropAllItemsOverride ForceDrop) and Only if Not Owned. fnm_loadout_reset: the run-start grant (Pick, NEW RACE, BOSS
# BATTLE start): "Clear Inventory" wipes the bag FIRST, so a new run never carries the last run's guard drops, chest
# weapons and grenades (Aaron 2026-10-16: "Player had weapons from previous run on new run"; a full bag also made the
# boss chests drop their weapon at the feet). E_Device_ItemGranter_GrantBehavior: Clear Inventory | Clear Items |
# Clear Resources | Keep All; GrantCondition: Always | Only If Empty | Only If Space | Only If Initially Empty |
# Only if Not Owned (read from the placed device's list_properties, 2026-10-16).
LOADOUTS = [
    ("Loadout", "fnm_loadout", {"grantBehavior": "Keep All", "grantCondition": "Only if Not Owned"}),
    ("LoadoutReset", "fnm_loadout_reset", {"grantBehavior": "Clear Inventory", "grantCondition": "Always"}),
]


def loadout(project):
    """Starting pistol, twice (LOADOUTS). Verse can't find the legacy item granter by tag, wire it by @editable reference
    (MCP rejects it), or reach the player's (non scene-graph) inventory, so: a hidden trigger tagged fnm_loadout /
    fnm_loadout_reset that Verse fires with the player as instigator, and the granter's Grant Item bound to that trigger."""
    for k, (label, vtag, settings) in enumerate(LOADOUTS):
        x, y, z = PARK[0], PARK[1] - PITCH * (len(RIGS) + k), PARK[2]
        trig = u.call(DEV, "PlaceDevice", {"assetPath": ref(TRIGGER), "transform": xform(x, y, z)})["returnValue"]["refPath"]
        grant = u.call(DEV, "PlaceDevice", {"assetPath": ref(GRANTER), "transform": xform(x + PITCH, y, z)})["returnValue"]["refPath"]
        for actor, suffix in ((trig, "Trigger"), (grant, "Granter")):
            u.call(ACTOR, "add_tag", {"actor": ref(actor), "tag": TAG})
            u.call(ACTOR, "set_label", {"actor": ref(actor), "label": f"FNM_Rig_{label}{suffix}"})
        verse_tags(trig, project, [vtag])
        props_set(trig, {"visible in Game": False, "reset Delay": 0.0})
        props_set(grant, {**settings, "giveExtraAmmo": 1, "equipItemOnGrant": 1,
                          "grantItem": {"eventSubscriptions": [{"object": {"refPath": trig},
                                                                "eventDescriptor": {"memberParent": {"refPath": TRIGGER_CLASS},
                                                                                    "memberName": "OnTriggered"}}]}})
        items = u.call("editor_toolset.toolsets.object.ObjectTools", "get_properties",
                       {"instance": ref(grant), "properties": ["pickupItemList"]})["returnValue"]
        item_list = json.loads(items)["pickupItemList"]["refPath"]
        props_set(item_list, {"itemListData": [{"itemDefinition": {"refPath": PISTOL}, "itemQuantity": 1}]})
        back = json.loads(u.call("editor_toolset.toolsets.object.ObjectTools", "get_properties",
                                 {"instance": ref(grant), "properties": list(settings)})["returnValue"])
        wrong = {key: back.get(key) for key, want in settings.items() if back.get(key) != want}
        if wrong:
            sys.exit(f"{label} granter: settings not taken: {wrong}")
        print(f"{label} granter + trigger placed ({vtag}: {', '.join(f'{k2} {v2}' for k2, v2 in settings.items())})")


def project_name():
    root = u.call("ValkyrieToolset.VerseToolset", "ListFiles", {"path": "", "bRecursive": False})
    return next(e["name"] for e in root["returnValue"] if e["type"] == "Directory" and "(" not in e["name"]).strip("/")


def loadout_only():
    """--loadout-only: replace just the loadout triggers and granters (LOADOUTS), leaving the penalty rigs alone."""
    found = u.call(SCENE, "find_actors", {"tag": TAG, "collision_channels": []})
    actors = found if isinstance(found, list) else found.get("returnValue", [])
    old = [a for a in actors if isinstance(a, dict) and a.get("label", "").startswith("FNM_Rig_Loadout")]
    for a in old:
        u.call(SCENE, "remove_from_scene", {"actor": ref(a["actorPath"])})
    print("removed", len(old), "old loadout actors")
    loadout(project_name())


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--copies", type=int, default=4)
    ap.add_argument("--loadout-only", action="store_true", help="replace only the loadout triggers + granters (LOADOUTS)")
    args = ap.parse_args()
    if args.loadout_only:
        loadout_only()
    else:
        build(args.copies)
