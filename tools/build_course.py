"""Build the Starter Course ("Gate Run") in the open UEFN project through UEFN MCP.

Layout per maps/starter/LAYOUT.md, adapted to ground level: each station is a walled room (no falls
possible) with a door wall of N doorways (A..D) leading into sealed pockets, each pocket holding a
hidden trigger. Rooms sit on a 5-wide grid; a finish room follows the last station.

Idempotent: every actor this script creates is tagged TAG; a run first deletes everything with TAG.

    python tools/build_course.py [--stations 10] [--doors 4]
"""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import uefn_mcp as u  # noqa: E402

TAG = "fnm_course"
CUBE = "/Engine/BasicShapes/Cube.Cube"
TRIGGER = "/CreativeCoreDevices/SetupAssets/PID_Device_Trigger.PID_Device_Trigger"
TELEPORTER = "/CreativeCoreDevices/SetupAssets/PID_Device_Teleporter.PID_Device_Teleporter"
BILLBOARD = "/CreativeCoreDevices/SetupAssets/PID_Device_Billboard.PID_Device_Billboard"
DIRECTOR = "/{root}/_Verse.fnm_director"
TAG_MARKUP = "/Script/VerseTags.VerseTagMarkupComponent"

SPACING = 2800          # room grid pitch (cm); rooms are ~2.1 x 1.9 m*1000 -- keep the course on the template floor
COLS = 4
HALF_W = 1024           # room interior half-width (x)
FRONT_Y = -768          # room interior front edge
DOOR_Y = 768            # door wall centre line
BACK_Y = 1024           # pocket back edge
WALL_H = 800
WALL_T = 40
DOOR_W = 384
DOOR_H = 448
LETTERS = "ABCD"

SCENE = "editor_toolset.toolsets.scene.SceneTools"
ACTOR = "editor_toolset.toolsets.actor.ActorTools"
OBJ = "editor_toolset.toolsets.object.ObjectTools"
DEV = "ValkyrieToolset.DeviceToolset"


def ref(path):
    return {"refPath": path}


def xform(x, y, z, sx=1.0, sy=1.0, sz=1.0, yaw=0.0):
    return {"location": {"x": x, "y": y, "z": z}, "rotation": {"pitch": 0, "yaw": yaw, "roll": 0},
            "scale": {"x": sx, "y": sy, "z": sz}}


def tag(actor, label):
    u.call(ACTOR, "add_tag", {"actor": ref(actor), "tag": TAG})
    u.call(ACTOR, "set_label", {"actor": ref(actor), "label": label})


def box(label, x0, x1, y0, y1, z0, z1):
    """Axis-aligned solid from a scaled 1 m engine cube (pivot at centre)."""
    r = u.call(SCENE, "add_to_scene_from_asset", {
        "asset_path": CUBE, "name": label,
        "xform": xform((x0 + x1) / 2, (y0 + y1) / 2, (z0 + z1) / 2,
                       (x1 - x0) / 100, (y1 - y0) / 100, (z1 - z0) / 100)})
    actor = r["returnValue"]["refPath"]
    tag(actor, label)
    return actor


def device(asset, label, x, y, z, yaw=0.0, sx=1.0, sy=1.0, sz=1.0):
    # Scale goes in the PlaceDevice transform: a later scale-only set_actor_transform resets location.
    r = u.call(DEV, "PlaceDevice", {"assetPath": ref(asset), "transform": xform(x, y, z, sx, sy, sz, yaw)})
    actor = r["returnValue"]["refPath"]
    tag(actor, label)
    return actor


def verse_tags(actor, project, names):
    """Mark a device with Verse tags (console/verse/fnm_tags.verse) via a VerseTagMarkup component."""
    c = u.call(ACTOR, "add_component", {"owner": ref(actor), "component_type": ref(TAG_MARKUP), "name": "FnmTags"})
    tags = [{"internalTag": ref(f"/{project}/_Verse.{n}")} for n in names]
    props(c["returnValue"]["refPath"], {"internalTags": {"internalTags": tags}})


def props(actor, values):
    u.call(OBJ, "set_properties", {"instance": ref(actor), "values": json.dumps(values)})


def clear():
    found = u.call(SCENE, "find_actors", {"tag": TAG, "collision_channels": []})
    actors = found if isinstance(found, list) else found.get("returnValue", [])
    for a in actors:
        u.call(SCENE, "remove_from_scene", {"actor": ref(a["actorPath"] if isinstance(a, dict) else a)})
    return len(actors)


def door_centres(doors):
    """Door A first. A player facing the doors (+Y) has +X on their LEFT, so A starts at +X."""
    pitch = 2 * HALF_W / doors
    return [HALF_W - pitch * (i + 0.5) for i in range(doors)]


def room(prefix, ox, oy, doors):
    """Walls + door wall + pockets for one room. Returns the door centre x offsets (empty for finish)."""
    t = WALL_T
    box(f"{prefix}_WallL", ox - HALF_W - t, ox - HALF_W, oy + FRONT_Y - t, oy + BACK_Y + t, 0, WALL_H)
    box(f"{prefix}_WallR", ox + HALF_W, ox + HALF_W + t, oy + FRONT_Y - t, oy + BACK_Y + t, 0, WALL_H)
    box(f"{prefix}_WallFront", ox - HALF_W, ox + HALF_W, oy + FRONT_Y - t, oy + FRONT_Y, 0, WALL_H)
    box(f"{prefix}_WallBack", ox - HALF_W, ox + HALF_W, oy + BACK_Y, oy + BACK_Y + t, 0, WALL_H)
    if not doors:
        box(f"{prefix}_WallDoor", ox - HALF_W, ox + HALF_W, oy + DOOR_Y - t / 2, oy + DOOR_Y + t / 2, 0, WALL_H)
        return []
    centres = door_centres(doors)
    pitch = 2 * HALF_W / doors
    y0, y1 = oy + DOOR_Y - t / 2, oy + DOOR_Y + t / 2
    # Solid segments between doorways, and a lintel over the whole wall.
    edges = [-HALF_W] + [e for c in sorted(centres) for e in (c - DOOR_W / 2, c + DOOR_W / 2)] + [HALF_W]
    for i in range(0, len(edges), 2):
        if edges[i + 1] > edges[i]:
            box(f"{prefix}_DoorWall{i // 2}", ox + edges[i], ox + edges[i + 1], y0, y1, 0, DOOR_H)
    box(f"{prefix}_Lintel", ox - HALF_W, ox + HALF_W, y0, y1, DOOR_H, WALL_H)
    # Dividers sealing each pocket from its neighbours.
    for i in range(1, doors):
        x = -HALF_W + pitch * i
        box(f"{prefix}_Divider{i}", ox + x - t / 2, ox + x + t / 2, y1, oy + BACK_Y, 0, WALL_H)
    return centres


def build(stations, doors):
    root = u.call("ValkyrieToolset.VerseToolset", "ListFiles", {"path": "", "bRecursive": False})
    project = next(e["name"] for e in root["returnValue"] if e["type"] == "Directory" and "(" not in e["name"]).strip("/")
    print("removed", clear(), "old course actors")

    all_doors, teleporters = [], []
    pocket_depth = BACK_Y - (DOOR_Y + WALL_T / 2)
    for k in range(stations + 1):
        ox, oy = SPACING * (k % COLS), SPACING * (k // COLS)
        finish = k == stations
        prefix = "FNM_Finish" if finish else f"FNM_S{k + 1:02d}"
        centres = room(prefix, ox, oy, 0 if finish else doors)
        tp = device(TELEPORTER, f"{prefix}_Entry", ox, oy - 450, 0, yaw=90)
        props(tp, {"knob_TeleporterGroup": "Group_None", "knob_TargetTeleporterGroup": "Group_None"})
        verse_tags(tp, project, ["fnm_finish"] if finish else [f"fnm_station_{k + 1:02d}", "fnm_entry"])
        teleporters.append(tp)
        # Billboard text faces yaw + 90 degrees: yaw 180 faces -Y (toward a player at the entry),
        # yaw -90 faces +X (out of the left wall).
        sign = device(BILLBOARD, f"{prefix}_Sign", ox - HALF_W + 5, oy, 250, yaw=-90, sx=2, sy=2, sz=2)
        props(sign, {"text": "FINISH!" if finish else f"STATION {k + 1}", "textSize": 24,
                     "textJustification": "Center"})
        for i, cx in enumerate(centres):
            trig = device(TRIGGER, f"{prefix}_Door{LETTERS[i]}", ox + cx, oy + DOOR_Y + WALL_T / 2 + pocket_depth / 2, 128,
                          sx=min(DOOR_W, 2 * HALF_W / doors - WALL_T) / 600, sy=pocket_depth / 600, sz=1.0)
            # Device_Trigger_V2 names (differ from the legacy trigger's).
            props(trig, {"timesCanTrigger_Override": False, "triggerDelay": 0.0, "reset Delay": 0.0,
                         "visible in Game": False, "triggeredByVehicles": False, "triggeredByWater": False,
                         "triggeredByPhysicsProps": False})
            verse_tags(trig, project, [f"fnm_station_{k + 1:02d}", f"fnm_door_{LETTERS[i].lower()}"])
            all_doors.append(trig)
            label = device(BILLBOARD, f"{prefix}_Label{LETTERS[i]}", ox + cx, oy + DOOR_Y - WALL_T, DOOR_H - 70,
                           yaw=180, sx=3, sy=3, sz=3)
            props(label, {"text": LETTERS[i], "textSize": 24, "textJustification": "Center"})
        print(prefix, "built")

    # The director finds stations by tag (fnm_tags.verse): nothing to wire.
    director = device(DIRECTOR.format(root=project), "FNM_Director", -2000, -2000, 0)
    print(f"placed director; tagged {len(all_doors)} doors and {len(teleporters)} teleporters")
    return director


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--stations", type=int, default=10)
    ap.add_argument("--doors", type=int, default=4)
    a = ap.parse_args()
    build(a.stations, a.doors)
