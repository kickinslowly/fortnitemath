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
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import uefn_mcp as u  # noqa: E402
from build_course import ACTOR, DEV, SCENE, TAG as COURSE_TAG, clear, props, ref, verse_tags, xform  # noqa: E402

TAG = "fnm_guards"
SPAWNER = "/CRD_HenchmanSpawner/SetupAssets/PID_Device_GuardSpawner_V2.PID_Device_GuardSpawner_V2"
# Guards alive at once per station, station 1 first; a longer course repeats the last entry.
GUARDS = [1, 1, 2, 2, 3, 3, 4, 4, 5, 5]
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
    for a in entries:
        k = int(a["label"][5:7])
        n = GUARDS[min(k, len(GUARDS)) - 1]
        y = (a["bounds"]["min"]["y"] + a["bounds"]["max"]["y"]) / 2 + SPAWN_AHEAD
        r = u.call(DEV, "PlaceDevice", {"assetPath": ref(SPAWNER), "transform": xform(0, y, 0, yaw=-90)})
        actor = r["returnValue"]["refPath"]
        u.call(ACTOR, "add_tag", {"actor": ref(actor), "tag": TAG})
        u.call(ACTOR, "set_label", {"actor": ref(actor), "label": f"FNM_S{k:02d}_Guards"})
        props(actor, {**SETTINGS, "spawnCount": n, "totalSpawnLimit": n})
        verse_tags(actor, project, ["fnm_guards", f"fnm_station_{k:02d}"])
        print(f"station {k}: {n} guards at y={y:.0f}")


if __name__ == "__main__":
    build()
