"""Build the Starter Course ("Gate Run" v2: hallway race) in the open UEFN project through UEFN MCP.

Layout per maps/starter/LAYOUT.md. One straight run toward +Y: each station is a long hallway ending in a
wall of real doors (A..D, one colour each). Behind every door is a vestibule holding a hidden trigger and,
at its far end, a barrier. The vestibules open straight onto the next station's hallway. Walking in fires
the trigger: the right door makes that barrier passable (and invisible) for that player only, so they run
on into the next hallway without stopping; a wrong door fires a penalty. A finish hallway follows the last
station. The course sits on its own floor slabs, so it may run past the template's ground.

Idempotent: every actor this script creates is tagged TAG; a run first deletes everything with TAG.

    python tools/build_course.py [--stations 10] [--doors 4] [--hall 3000]
    python tools/build_course.py --paint-only   # recolour walls by tier (materials: tools/import_art.py)
    python tools/build_course.py --doors-only   # swap the door props in place (DOOR_PROPS), no rebuild
"""
import argparse
import re
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
BARRIER = "/CRD_VolumetricRegion/SetupAssets/PID_Device_Barrier.PID_Device_Barrier"
DIRECTOR = "/{root}/_Verse.fnm_director"
TAG_MARKUP = "/Script/VerseTags.VerseTagMarkupComponent"
PROPS = "/CR_Legacy/Playsets/PlaysetProps"
# Walls with a real (openable) door, 384 tall, pivot centred, stretched to DOOR_W. One look for every door
# (Aaron 2026-10-04: a door that looks different stands out as a hint); the coloured letter boards above
# the doors (LETTER_COLOURS) are what tell A..D apart. Rewrite the doors alone with --doors-only.
DOOR_PROPS = [("OilRig_Platform_Wall_01_Door_01", 553)] * 4

START_Y = -12000        # hallway 1 starts here; the course runs toward +Y
DOOR_W = 553            # door prop width = door pitch
DOOR_H = 384
WALL_H = 600            # hallway walls; a lintel fills the door wall above the doors
WALL_T = 40
VEST = 700              # vestibule depth behind the door wall
BARRIER_T = 40
SLAB_T = 40             # floor slab thickness (top at z=2, just above the template ground)
FINISH_LEN = 1500
# Hallway obstacles per station, as (kind, distance from the hallway start in cm). Players land 450 cm in and
# a Yeet pulls them back to 2270 cm, so obstacles stay between 900 and 2000. Later stations get harder; a course
# longer than this list repeats its last entry. hurdle = 70 cm bar to jump (gold), baffleL/R = a wall from one
# side leaving a gap on the other, slider/sliderR = a shipping container the director sweeps across the hallway
# (starting on the left / right).
OBSTACLES = [
    [],
    [("hurdle", 1400)],
    [("baffleL", 1000), ("baffleR", 1800)],
    [("hurdle", 1000), ("hurdle", 1800)],
    [("slider", 1400)],
    [("baffleL", 950), ("hurdle", 1450), ("baffleR", 1950)],
    [("slider", 1000), ("sliderR", 1800)],
    [("hurdle", 950), ("slider", 1450), ("hurdle", 1950)],
    [("baffleL", 950), ("slider", 1450), ("baffleR", 1950)],
    [("slider", 950), ("hurdle", 1450), ("sliderR", 1950)],
]
HURDLE_H = 70
BAFFLE_GAP = 900        # open width a baffle leaves
CONTAINER = ("/CR_Legacy/Playsets/PlaysetProps/PPID_CR_Legacy_Apollo_Industrial_ShippingContainer_01_2bfba750."
             "PPID_CR_Legacy_Apollo_Industrial_ShippingContainer_01_2bfba750")
CONTAINER_W = 607       # along X; it sweeps between +SLIDE_X and -SLIDE_X
SLIDE_X = 790
LETTERS = "ABCD"
# Letter boards: bright text on a dark board, a colour per door (default billboard text is pale grey and
# vanished against the sky in play).
BOARD = {"showBorder": True, "backgroundColor": {"r": 0.02, "g": 0.02, "b": 0.06, "a": 1.0},
         "textSize": 24, "textJustification": "Center"}
LETTER_COLOURS = [(1.0, 1.0, 1.0), (0.3, 0.55, 1.0), (0.2, 0.9, 0.3), (1.0, 0.55, 0.1)]
SIGN_COLOUR = (1.0, 0.8, 0.1)
# Barrier zone at actor scale 1 ("volume Transform" Box): 511 x 511 x 384, bottom at the actor. Its
# get_actor_bounds add a 128/96 cm editor margin all round, so don't size it from those.
BARRIER_BASE = (511, 511, 384, 0)

SCENE = "editor_toolset.toolsets.scene.SceneTools"
ACTOR = "editor_toolset.toolsets.actor.ActorTools"
OBJ = "editor_toolset.toolsets.object.ObjectTools"
DEV = "ValkyrieToolset.DeviceToolset"
ASSETS = "editor_toolset.toolsets.asset.AssetTools"


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


def prop(asset, label, x, y, z, yaw=0.0, sx=1.0):
    r = u.call(SCENE, "add_to_scene_from_asset", {"asset_path": asset, "name": label, "xform": xform(x, y, z, sx, yaw=yaw)})
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


def clear(tag_name=TAG):
    found = u.call(SCENE, "find_actors", {"tag": tag_name, "collision_channels": []})
    actors = found if isinstance(found, list) else found.get("returnValue", [])
    for a in actors:
        u.call(SCENE, "remove_from_scene", {"actor": ref(a["actorPath"] if isinstance(a, dict) else a)})
    return len(actors)


def board(actor, text, rgb):
    props(actor, {**BOARD, "text": text, "textColor": {"r": rgb[0], "g": rgb[1], "b": rgb[2], "a": 1.0}})


def door_asset(name):
    found = u.call(ASSETS, "find_assets", {"folder_path": PROPS, "name": name, "recursive": False})["returnValue"]
    exact = [p for p in found if p.split(".")[-1] == f"PPID_CR_Legacy_{name}"]
    if not exact:
        sys.exit(f"door prop {name} not found")
    return exact[0]


def door_centres(doors):
    """Door A first. A player facing the doors (+Y) has +X on their LEFT, so A is at +X."""
    half = doors * DOOR_W / 2
    return [half - DOOR_W * (i + 0.5) for i in range(doors)]


def station(k, oy, hall, doors, project, door_assets):
    """Station k (1-based) whose hallway starts at oy. Returns where the next hallway starts."""
    half = doors * DOOR_W / 2
    t = WALL_T
    prefix = f"FNM_S{k:02d}"
    door_y = oy + hall                      # door wall centre line
    vest0 = door_y + 25                     # vestibule from the door wall's back face ...
    vest1 = vest0 + VEST                    # ... to the barrier
    end = vest1 + BARRIER_T                 # the next hallway starts here

    box(f"{prefix}_Floor", -half - t, half + t, oy, end, 2 - SLAB_T, 2)
    box(f"{prefix}_WallL", half, half + t, oy, end, 0, WALL_H)
    box(f"{prefix}_WallR", -half - t, -half, oy, end, 0, WALL_H)
    if k == 1:
        box(f"{prefix}_WallStart", -half - t, half + t, oy - t, oy, 0, WALL_H)
    box(f"{prefix}_Lintel", -half, half, door_y - 25, door_y + 25, DOOR_H, WALL_H)
    for i in range(1, doors):
        x = half - DOOR_W * i
        box(f"{prefix}_Divider{i}", x - t / 2, x + t / 2, door_y + 25, vest1, 0, WALL_H)

    tp = device(TELEPORTER, f"{prefix}_Entry", 0, oy + 150, 0, yaw=90)
    props(tp, {"knob_TeleporterGroup": "Group_None", "knob_TargetTeleporterGroup": "Group_None"})
    verse_tags(tp, project, [f"fnm_station_{k:02d}", "fnm_entry"])
    sign = device(BILLBOARD, f"{prefix}_Sign", half - 5, oy + 600, 250, yaw=-90, sx=2, sy=2, sz=2)
    board(sign, f"STATION {k}", SIGN_COLOUR)

    obstacles(k, oy, half, project)

    bw, bd, bh, bz = BARRIER_BASE
    for i, cx in enumerate(door_centres(doors)):
        letter = LETTERS[i]
        asset, width = door_assets[i]
        prop(asset, f"{prefix}_Door{letter}", cx, door_y, 0, sx=DOOR_W / width)
        label = device(BILLBOARD, f"{prefix}_Label{letter}", cx, door_y - 40, DOOR_H + 20, yaw=180, sx=2, sy=2, sz=2)
        board(label, letter, LETTER_COLOURS[i])
        inner = DOOR_W - t                  # vestibule width between dividers
        trig_depth = VEST * 0.6
        trig = device(TRIGGER, f"{prefix}_Trigger{letter}", cx, vest0 + trig_depth / 2, 128,
                      sx=inner / 600, sy=trig_depth / 600, sz=1.0)
        # Device_Trigger_V2 names (differ from the legacy trigger's).
        props(trig, {"timesCanTrigger_Override": False, "triggerDelay": 0.0, "reset Delay": 0.0,
                     "visible in Game": False, "triggeredByVehicles": False, "triggeredByWater": False,
                     "triggeredByPhysicsProps": False})
        verse_tags(trig, project, [f"fnm_station_{k:02d}", f"fnm_door_{letter.lower()}"])
        sz = WALL_H / bh
        bar = device(BARRIER, f"{prefix}_Passage{letter}", cx, vest1 + BARRIER_T / 2, -bz * sz,
                     sx=inner / bw, sy=BARRIER_T / bd, sz=sz)
        props(bar, {"invisibleToIgnoredPlayers": True, "collide with Camera": False})
        verse_tags(bar, project, [f"fnm_station_{k:02d}", f"fnm_door_{letter.lower()}"])
    return end


def obstacles(k, oy, half, project):
    """Station k's hallway obstacles (OBSTACLES). +X is the player's left."""
    for n, (kind, dy) in enumerate(OBSTACLES[min(k, len(OBSTACLES)) - 1], 1):
        y = oy + dy
        label = f"FNM_S{k:02d}_{kind.capitalize()}{n}"
        if kind == "hurdle":
            box(label, -half, half, y - 20, y + 20, 0, HURDLE_H)
        elif kind == "baffleL":
            box(label, BAFFLE_GAP - half, half, y - WALL_T / 2, y + WALL_T / 2, 0, WALL_H)
        elif kind == "baffleR":
            box(label, -half, half - BAFFLE_GAP, y - WALL_T / 2, y + WALL_T / 2, 0, WALL_H)
        else:
            x = SLIDE_X if kind == "slider" else -SLIDE_X
            verse_tags(prop(CONTAINER, label, x, y, 0), project, ["fnm_slider"])


def finish(oy, doors, project):
    half = doors * DOOR_W / 2
    t = WALL_T
    end = oy + FINISH_LEN
    box("FNM_Finish_Floor", -half - t, half + t, oy, end + t, 2 - SLAB_T, 2)
    box("FNM_Finish_WallL", half, half + t, oy, end, 0, WALL_H)
    box("FNM_Finish_WallR", -half - t, -half, oy, end, 0, WALL_H)
    box("FNM_Finish_WallEnd", -half - t, half + t, end, end + t, 0, WALL_H)
    tp = device(TELEPORTER, "FNM_Finish_Entry", 0, oy + 150, 0, yaw=90)
    props(tp, {"knob_TeleporterGroup": "Group_None", "knob_TargetTeleporterGroup": "Group_None"})
    verse_tags(tp, project, ["fnm_finish"])
    sign = device(BILLBOARD, "FNM_Finish_Sign", 0, end - 5, 250, yaw=180, sx=4, sy=4, sz=4)
    board(sign, "FINISH!", SIGN_COLOUR)


def tier_count():
    """Tiers of the cartridges the starter map holds (maps/starter/generated/SLOT.txt, one `cartridge=` line each).
    Walls are painted per tier once for every skill, so the cartridges should agree (PROTOCOL 3: use 5 tiers);
    on a mismatch the first cartridge wins and a warning is printed."""
    root = Path(__file__).parents[1]
    ids = [line.split("=", 1)[1].split()[0] for line in (root / "maps/starter/generated/SLOT.txt").read_text().splitlines()
           if line.startswith("cartridge=")]
    counts = {cid: len(json.loads((root / "cartridges" / cid / "baked.json").read_text(encoding="utf-8"))["tiers"])
              for cid in ids}
    if len(set(counts.values())) > 1:
        print(f"warning: cartridges differ in tier count {counts}; painting for {ids[0]}")
    return counts[ids[0]]


def auto_tier(stage, stages, tiers):
    """fnm_logic.verse FnmAutoTier (PROTOCOL 6), so a hallway's colour matches the tier played in it."""
    if stages > 1 and tiers > 1:
        return max(1, min(tiers, 1 + (2 * (stage - 1) * (tiers - 1) + (stages - 1)) // (2 * (stages - 1))))
    return 1


def paint():
    """Colour each hallway's walls by the tier played there (materials from tools/import_art.py), the finish
    gold. Floors stay white. Idempotent; safe to rerun alone after a cartridge change (--paint-only)."""
    root = u.call("ValkyrieToolset.VerseToolset", "ListFiles", {"path": "", "bRecursive": False})
    mount = next(e["name"] for e in root["returnValue"] if e["type"] == "Directory" and "(" not in e["name"]).rstrip("/")
    found = u.call(SCENE, "find_actors", {"tag": TAG, "collision_channels": []})["returnValue"]
    walls = [a for a in found if isinstance(a, dict) and re.match(r"FNM_(S\d\d|Finish)_(Wall|Lintel|Divider|Baffle|Hurdle)", a.get("label", ""))]
    stations = len({a["label"][5:7] for a in walls if a["label"][4] == "S"})
    tiers = tier_count()
    for a in walls:
        # Hurdles are gold (the finish colour) so they stand out against the tier colour.
        gold = a["label"].startswith("FNM_Finish") or "_Hurdle" in a["label"]
        key = "finish" if gold else f"tier{auto_tier(int(a['label'][5:7]), stations, tiers)}"
        mat = f"{mount}/FNM_Art/M_fnm_wall_{key}.M_fnm_wall_{key}"
        comp = json.loads(u.call(OBJ, "get_properties", {"instance": ref(a["actorPath"]),
                                                        "properties": ["staticMeshComponent"]})["returnValue"])
        props(comp["staticMeshComponent"]["refPath"], {"overrideMaterials": [ref(mat)]})
    print(f"painted {len(walls)} walls over {stations} stations ({tiers} tiers)")


def doors_only():
    """Swap every station's door props for DOOR_PROPS in place, keeping their labels; nothing else moves.
    The door-wall line comes from the station's lintel (a cube centred on the wall), not from the old door
    prop, whose bounds need not be symmetric in Y. Idempotent."""
    found = u.call(SCENE, "find_actors", {"tag": TAG, "collision_channels": []})["returnValue"]
    found = [a for a in found if isinstance(a, dict)]
    lintels = {a["label"][5:7]: a for a in found if re.fullmatch(r"FNM_S\d\d_Lintel", a.get("label", ""))}
    by_station = {}
    for a in found:
        if re.fullmatch(r"FNM_S\d\d_Door[A-D]", a.get("label", "")):
            by_station.setdefault(a["label"][5:7], []).append(a)
    assets = {}
    placed = 0
    for st in sorted(by_station):
        old = by_station[st]
        lb = lintels[st]["bounds"]
        door_y = (lb["min"]["y"] + lb["max"]["y"]) / 2
        letters = sorted({a["label"][-1] for a in old})
        n = LETTERS.index(letters[-1]) + 1
        centres = door_centres(n)
        for a in old:
            u.call(SCENE, "remove_from_scene", {"actor": ref(a["actorPath"])})
        for letter in letters:
            i = LETTERS.index(letter)
            name, width = DOOR_PROPS[i]
            if name not in assets:
                assets[name] = door_asset(name)
            prop(assets[name], f"FNM_S{st}_Door{letter}", centres[i], door_y, 0, sx=DOOR_W / width)
            placed += 1
        print(f"station {int(st)}: removed {len(old)}, placed {len(letters)} doors at y={door_y:.0f}")
    print(f"{placed} doors placed")


def build(stations, doors, hall):
    root = u.call("ValkyrieToolset.VerseToolset", "ListFiles", {"path": "", "bRecursive": False})
    project = next(e["name"] for e in root["returnValue"] if e["type"] == "Directory" and "(" not in e["name"]).strip("/")
    print("removed", clear(), "old course actors;", clear("fnm_test"), "test actors")
    door_assets = [(door_asset(n), width) for n, width in DOOR_PROPS[:doors]]
    oy = START_Y
    for k in range(1, stations + 1):
        oy = station(k, oy, hall, doors, project, door_assets)
        print(f"station {k} built")
    finish(oy, doors, project)
    # The director finds stations by tag (fnm_tags.verse): nothing to wire.
    device(DIRECTOR.format(root=project), "FNM_Director", -3000, START_Y, 0)
    print(f"finish at y={oy}; director placed")
    paint()


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--stations", type=int, default=10)
    ap.add_argument("--doors", type=int, default=4)
    ap.add_argument("--hall", type=int, default=3000, help="hallway length (cm) from entry to the door wall")
    ap.add_argument("--paint-only", action="store_true", help="only recolour the walls by tier")
    ap.add_argument("--doors-only", action="store_true", help="only replace the door props in place")
    a = ap.parse_args()
    if a.paint_only:
        paint()
    elif a.doors_only:
        doors_only()
    else:
        build(a.stations, a.doors, a.hall)
