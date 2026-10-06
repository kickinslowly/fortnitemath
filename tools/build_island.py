"""Make the open UEFN project a 4+ player race: island settings, enough spawn pads, indestructible props.

Aaron (2026-10-06): "check that this game will work for multiplayer, because it is a race, I would love for 4 or
more players". The director is per player already (PROTOCOL 6); what was not were the island's settings, read
from the IslandSettings0 actor through MCP (list_properties / get_properties; the enums are in that listing):
- teams FreeForAll -> Cooperative: everyone on one team, so the guns the guards drop (rocket launchers by the
  end) cannot be turned on classmates (bAllowFriendlyFire is already false). Guards stay hostile (Wildlife team).
- downButNotOut Default -> Off: "Default" is Classic (revivable) for a team, which would turn every guard kill and
  Spike into a crawl instead of the elimination the director waits for (WatchLife, Punish).
- joinInProgressBehavior SpawnDuringNewRound -> SpawnImmediately: the race never starts a new round, so a late
  joiner would have watched forever; now they drop in and the director gives them the picker and station 1.
- environmentDamagePreset All -> Off: no shooting the doors, torches, podiums and chalkboards apart.
- allowBuilding All -> None: no ramps over the hallway walls to skip stations (bInfiniteResources is on).
Spawn pads: the island had two (x = -250 / 250, y = 0); PADS more are placed beside them, on the floor
trace_world finds, so a full class spawns on pads rather than in the air. The director teleports every joining
player to station 1 anyway.
Props: every gallery prop the course, decor, finish rig and penalty rigs placed had bCanBeDamaged true (the doors
too); it is set false on all of them, a second wall behind the island setting (guards' rockets are not "players
damaging the environment").

Idempotent: settings are plain sets; pads this script creates carry the actor tag TAG and are replaced on rerun;
the prop pass is a no-op where the flag is already false.

    python tools/build_island.py            # everything, then prints the settings read back
    python tools/build_island.py --check    # read-only report
"""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import uefn_mcp as u  # noqa: E402
from build_course import ACTOR, DEV, OBJ, SCENE, clear, props, ref, xform  # noqa: E402

TAG = "fnm_island"
PAD = "/CRD_PlayerSpawn/ItemDefinitions/PID_Device_PlayerSpawnPad.PID_Device_PlayerSpawnPad"
# Extra pads: (x, y) beside the two the island came with at (-250, 0) and (250, 0).
PADS = [(-750, 0), (750, 0), (-750, 400), (-250, 400), (250, 400), (750, 400)]
SETTINGS = {
    "teams": {"teamType": "Cooperative", "teamIndex": 1},
    "downButNotOut": "Off",
    "joinInProgressBehavior": "SpawnImmediately",
    "environmentDamagePreset": "Off",
    "allowBuilding": "None",
}
# Read back for the report, beyond SETTINGS.
REPORT = ["maxPlayers", "bAllowFriendlyFire", "spawnLocation", "respawnTime", "spawnLimit", "spawnLimit_Override",
          "roundTimeLimit", "roundTimeLimit_Override", "bForceStartAtMaxPlayers", "matchmaking_MaxPlayersPerSession"]
# Prop hardening: skip devices, engine cubes (not damageable anyway), the Verse device and the item granter.
SKIP_CLASSES = ("Device_", "FortStaticMeshActor", "VerseDevice", "BP_Creative_", "PersistentLevel.IslandSettings")
PROP_TAGS = ("fnm_course", "fnm_decor", "fnm_finish_rig", "fnm_rigs")


def find(**kw):
    found = u.call(SCENE, "find_actors", {**kw, "collision_channels": []})["returnValue"]
    return [a for a in found if isinstance(a, dict)]


def get(path, keys):
    r = u.call(OBJ, "get_properties", {"instance": ref(path), "properties": keys})["returnValue"]
    return json.loads(r) if isinstance(r, str) else r


def island():
    hits = find(name="IslandSettings")
    if not hits:
        sys.exit("no IslandSettings actor in the level")
    return hits[0]["actorPath"]


def settings(check):
    isl = island()
    before = get(isl, list(SETTINGS))
    if not check:
        props(isl, SETTINGS)
    after = get(isl, list(SETTINGS) + REPORT)
    print("island settings:")
    for k, want in SETTINGS.items():
        flag = "ok" if after.get(k) == want else ("WRONG" if not check else "to set")
        print(f"  {k}: {json.dumps(before.get(k))} -> {json.dumps(after.get(k))}  [{flag}]")
    for k in REPORT:
        print(f"  {k} = {json.dumps(after.get(k))}")
    if not check and any(after.get(k) != want for k, want in SETTINGS.items()):
        sys.exit("an island setting did not take")


def pads(check):
    have = find(name="Spawn Pad") + find(tag=TAG)
    print(f"spawn pads: {len({a['actorPath'] for a in have})} present")
    if check:
        return
    print("removed", clear(TAG), "old extra pads")
    placed = 0
    for n, (x, y) in enumerate(PADS, 1):
        # Floor height under the spot (the pads that came with the island stand at z = 0).
        hit = u.call(SCENE, "trace_world", {"start": {"x": x, "y": y, "z": 500}, "end": {"x": x, "y": y, "z": -500}})["returnValue"]
        if hit is None:
            print(f"  pad {n} at ({x}, {y}): no floor, skipped")
            continue
        z = 500 - float(hit)
        r = u.call(DEV, "PlaceDevice", {"assetPath": ref(PAD), "transform": xform(x, y, z, yaw=0 if x > 0 else 180)})
        actor = r["returnValue"]["refPath"]
        u.call(ACTOR, "add_tag", {"actor": ref(actor), "tag": TAG})
        u.call(ACTOR, "set_label", {"actor": ref(actor), "label": f"FNM_SpawnPad{n}"})
        placed += 1
        print(f"  pad {n} at ({x}, {y}, {z:.0f})")
    total = len({a["actorPath"] for a in find(name="Spawn Pad") + find(tag=TAG)})
    print(f"spawn pads: {placed} placed, {total} on the island")


def harden(check):
    seen, flipped, left = 0, 0, []
    for tag in PROP_TAGS:
        for a in find(tag=tag):
            cls = a["actorPath"] + " " + a["nativeClass"]["refPath"]
            if any(s in cls for s in SKIP_CLASSES):
                continue
            seen += 1
            if not get(a["actorPath"], ["bCanBeDamaged"]).get("bCanBeDamaged"):
                continue
            if check:
                left.append(a["label"])
                continue
            props(a["actorPath"], {"bCanBeDamaged": False})
            if get(a["actorPath"], ["bCanBeDamaged"]).get("bCanBeDamaged"):
                left.append(a["label"])
            else:
                flipped += 1
    print(f"props: {seen} gallery props checked, {flipped} set indestructible, {len(left)} still damageable"
          + (f" ({', '.join(left[:8])}{'...' if len(left) > 8 else ''})" if left else ""))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true", help="report only, change nothing")
    a = ap.parse_args()
    settings(a.check)
    pads(a.check)
    harden(a.check)
    if not a.check:
        u.call("editor_toolset.toolsets.asset.AssetTools", "save_assets", {"asset_paths": []})
