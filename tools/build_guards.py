"""Place one guard spawner per station hallway in the open UEFN project through UEFN MCP.

Aaron (2026-10-04): hostile NPCs the player fights while answering, more of them at later stations. Each
spawner sits in its hallway in front of the doors, tagged fnm_guards + fnm_station_NN. The director
(fnm_director.verse GuardLoop) enables a station's spawner while a player is on that station and disables it,
despawning its guards, once nobody is. Guards are on the Wildlife team (the default team index 1 is the
players' team, so they would be friendly), low accuracy, with health bars; the guard count per station is
GUARDS. An island may have at most 30 guards alive, and only occupied stations spawn.

Idempotent: every actor this script creates is tagged TAG; a run first deletes everything with TAG.

    python tools/build_guards.py
"""
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import uefn_mcp as u  # noqa: E402
from build_course import ACTOR, DEV, OBJ, SCENE, TAG as COURSE_TAG, clear, props, ref, verse_tags, xform  # noqa: E402

TAG = "fnm_guards"
SPAWNER = "/CRD_HenchmanSpawner/SetupAssets/PID_Device_GuardSpawner_V2.PID_Device_GuardSpawner_V2"
# Guards alive at once per station, station 1 first; a longer course repeats the last entry.
GUARDS = [1, 1, 2, 2, 3, 3, 4, 4, 5, 5]
# The weapon each station's guards carry, station 1 first; a longer course repeats the last entry. Aaron
# (2026-10-04): weapons climb with the stations, and guards drop them (dropInventoryOnElimination), so a player
# who beats them climbs too. Aaron (2026-10-06): the old pistol -> SMG -> shotgun -> AR ladder was "boring"; ramp
# it dramatically, blue (rare) at the start to gold (legendary) at the end, pistol -> SMG -> shotguns -> snipers ->
# launchers by the last stations. Rarity letters: C common, UC uncommon, R rare (blue), VR epic (purple), SR
# legendary (gold). Set through the spawner's ItemList sub-object (PickupItemListComponent, itemListData), the same
# shape as the item granter. The spawner silently drops some weapons (set_properties still answers True and the list
# reads back empty), so build() reads each list back and stops on an empty one. Probed 2026-10-06 (--probe): accepted
# Pistol_SemiAuto R/VR/SR, AutoHeavyPDW (SMG) UC/R/VR/SR, AutoHeavySuppressed UC/R, Shotgun_SemiAuto R/VR,
# Shotgun_Standard (pump) UC/VR/SR, Shotgun_HighSemiAuto (heavy) VR/SR, Shotgun_Combat R/VR/SR, Shotgun_Charge R/VR/SR,
# Assault_AutoHigh VR/SR, Assault_Heavy R/VR/SR, Assault_Surgical R/VR/SR, Assault_Auto R, Sniper_BoltAction_Scope
# R/VR/SR, Sniper_Standard_Scope VR/SR, Sniper_Heavy VR/SR, Sniper_NoScope UC/R, Sniper_Suppressed_Scope VR/SR,
# Launcher_Rocket R/VR/SR, Launcher_Grenade R/VR/SR. Refused: Hand_Cannon, Six_Shooter, AutoHeavy (tactical SMG),
# Compact, Shotgun_SemiAuto SR, Shotgun_Standard R, Break, Automatic, Sniper_Standard_Scope R, Launcher_Quad /
# _Pumpkin / _Rocket_Guided.
_W = "/Game/Athena/Items/Weapons/{0}.{0}"
WEAPONS = [_W.format(n) for n in (
    "WID_Pistol_SemiAuto_Athena_R_Ore_T03",            # 1  pistol, blue (the loadout's)
    "WID_Pistol_AutoHeavyPDW_Athena_R_Ore_T03",        # 2  SMG, blue
    "WID_Pistol_AutoHeavyPDW_Athena_VR_Ore_T03",       # 3  SMG, purple
    "WID_Shotgun_Standard_Athena_VR_Ore_T03",          # 4  pump shotgun, purple
    "WID_Shotgun_Combat_Athena_VR_Ore_T03",            # 5  combat shotgun, purple
    "WID_Shotgun_HighSemiAuto_Athena_VR_Ore_T03",      # 6  heavy shotgun, purple (the ice station)
    "WID_Sniper_BoltAction_Scope_Athena_VR_Ore_T03",   # 7  bolt-action sniper, purple
    "WID_Sniper_Heavy_Athena_SR_Ore_T03",              # 8  heavy sniper, gold
    "WID_Launcher_Grenade_Athena_SR_Ore_T03",          # 9  grenade launcher, gold
    "WID_Launcher_Rocket_Athena_SR_Ore_T03")]          # 10 rocket launcher, gold
# The spawner stands this far (cm) past the station's entry pad, i.e. in the back half of the 30 m hallway
# before the doors (players land ~3 m past the pad, the door wall is ~28.5 m past it).
SPAWN_AHEAD = 2000
SETTINGS = {
    "guardTeamOption": "Team Wildlife & Creatures",
    "enabledAtGameStart": False,
    "spawnOnTimer": True,
    "spawnTimer": 1.0,
    "allowInfiniteSpawn": False,
    "despawnGuardsWhenDisabled": True,
    "spawnRadius_InMeter": 6.0,
    "spawnThroughWalls": False,
    "enablePatrol": True,
    "maxPatrolDistance_InMeter": 8.0,
    "visibilityRange_InMeter": 35.0,
    "accuracy": "LOW",
    "showHealthBar": True,
    "useAlertness": True,
    "dropInventoryOnElimination": True,
    "bCanBeHired": False,
    "bAllowHireConversation": False,
}


def build():
    root = u.call("ValkyrieToolset.VerseToolset", "ListFiles", {"path": "", "bRecursive": False})
    project = next(e["name"] for e in root["returnValue"] if e["type"] == "Directory" and "(" not in e["name"]).strip("/")
    print("removed", clear(TAG), "old guard spawners")
    found = u.call(SCENE, "find_actors", {"tag": COURSE_TAG, "collision_channels": []})["returnValue"]
    entries = sorted((a for a in found if isinstance(a, dict) and re.fullmatch(r"FNM_S\d\d_Entry", a.get("label", ""))),
                     key=lambda a: a["label"])
    floors = {a["label"][:7]: a for a in found if isinstance(a, dict) and re.fullmatch(r"FNM_S\d\d_Floor", a.get("label", ""))}
    for a in entries:
        k = int(a["label"][5:7])
        n = GUARDS[min(k, len(GUARDS)) - 1]
        b = a["bounds"]
        # Stations sit at different X and levels (connectors). A device's bounds carry an editor margin, so the
        # height comes from the station's floor slab (an engine cube, exact bounds): its top face.
        floor = floors[a["label"][:7]]["bounds"]
        x = (floor["min"]["x"] + floor["max"]["x"]) / 2
        y = (b["min"]["y"] + b["max"]["y"]) / 2 + SPAWN_AHEAD
        z = floor["max"]["z"]
        r = u.call(DEV, "PlaceDevice", {"assetPath": ref(SPAWNER), "transform": xform(x, y, z, yaw=-90)})
        actor = r["returnValue"]["refPath"]
        u.call(ACTOR, "add_tag", {"actor": ref(actor), "tag": TAG})
        u.call(ACTOR, "set_label", {"actor": ref(actor), "label": f"FNM_S{k:02d}_Guards"})
        props(actor, {**SETTINGS, "spawnCount": n, "totalSpawnLimit": n})
        weapon = WEAPONS[min(k, len(WEAPONS)) - 1]
        items = json.loads(u.call(OBJ, "get_properties", {"instance": ref(actor), "properties": ["itemList"]})["returnValue"])
        props(items["itemList"]["refPath"], {"itemListData": [{"itemDefinition": ref(weapon), "itemQuantity": 1}]})
        back = json.loads(u.call(OBJ, "get_properties", {"instance": items["itemList"],
                                                         "properties": ["itemListData"]})["returnValue"])["itemListData"]
        if not back or (back[0].get("itemDefinition") or {}).get("refPath") != weapon:
            sys.exit(f"station {k}: the guard spawner refused {weapon}")
        verse_tags(actor, project, ["fnm_guards", f"fnm_station_{k:02d}"])
        print(f"station {k}: {n} guards at x={x:.0f} y={y:.0f} z={z:.0f}, {weapon.rsplit('.', 1)[1]}")


def probe(names):
    """Which of these WID_* names the station-1 spawner keeps (set, read back); the list is restored to WEAPONS[0]."""
    found = u.call(SCENE, "find_actors", {"tag": TAG, "collision_channels": []})["returnValue"]
    first = sorted((a for a in found if isinstance(a, dict) and a.get("label", "").endswith("_Guards")), key=lambda a: a["label"])
    if not first:
        sys.exit("no guard spawner placed yet")
    items = json.loads(u.call(OBJ, "get_properties", {"instance": ref(first[0]["actorPath"]), "properties": ["itemList"]})["returnValue"])
    lst = items["itemList"]["refPath"]
    for name in names + [WEAPONS[0].rsplit(".", 1)[1]]:
        weapon = _W.format(name)
        props(lst, {"itemListData": [{"itemDefinition": ref(weapon), "itemQuantity": 1}]})
        back = json.loads(u.call(OBJ, "get_properties", {"instance": ref(lst), "properties": ["itemListData"]})["returnValue"])["itemListData"]
        kept = bool(back) and (back[0].get("itemDefinition") or {}).get("refPath") == weapon
        if name in names:
            print("accepted" if kept else "REFUSED ", name)


if __name__ == "__main__":
    if len(sys.argv) > 2 and sys.argv[1] == "--probe":
        probe(sys.argv[2].split(","))
    else:
        build()
