"""Build the Starter Course ("Gate Run" v2: hallway race) in the open UEFN project through UEFN MCP.

Layout per maps/starter/LAYOUT.md. Every station is a hallway facing +Y ending in a wall of real doors (A..D). Behind every door is a vestibule holding a hidden trigger and,
at its far end, a barrier. The vestibules open straight onto the next station's hallway. Walking in fires
the trigger: the right door makes that barrier passable (and invisible) for that player only, so they run
on into the next hallway without stopping; a wrong door fires a penalty. Between stations a connector corridor
(CONNECTORS) funnels down from the vestibules and climbs stairs, drops down stairs, winds left or right, or runs
straight over speed plates, then flares out into the next hallway, which may sit higher, lower or to one side.
Station hallways in ICE_STATIONS have an icy floor. A finish hallway follows the last station. The course sits on
its own floor slabs, so it may run past the template's ground.

Idempotent: every actor this script creates is tagged TAG; a run first deletes everything with TAG.

    python tools/build_course.py [--stations 10] [--doors 4] [--hall 3000]
    python tools/build_course.py --paint-only   # dress walls AND floors by tier (the Titan Peak surfaces, tools/import_titanpeak.py
                                                # --materials; flat colours with --flat: tools/import_art.py), saves, reads back
    python tools/build_course.py --door-paint   # re-apply each door's letter material in place (no replacing), saves, reads back
    python tools/build_course.py --check-paint  # read-only: every door and painted wall / floor against what the build wants (exit 1 if off;
                                                # add --flat to check against the flat colours)
    python tools/build_course.py --doors-only   # swap the door props in place (DOOR_PROPS), no rebuild
    python tools/build_course.py --triggers-only  # refit the vestibule and arena pad triggers in place (trigger_fit)
    python tools/build_course.py --arena-pads   # move the arena's 4 pad tiles + triggers to PAD_SPOTS / RACE_PAD_SIZE in place, reads back

After the last station's connector comes the BOSS ARENA (GOALS G6 item 3, maps/starter/LAYOUT.md "Boss arena"): four
answer pads, the boss platform, an adds spawner, a gate barrier at the exit, then a short connector into the
unchanged finish hallway. The arena is not a numbered station (fnm_boss tag), so the tier formula is untouched. The boss
itself (a hidden Megabrute under the Magma Titan), the mega cannons and the floating pad letters are
tools/build_race_boss.py's: rerun it after a course rebuild.
"""
import argparse
import functools
import math
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
MUTATOR = "/CRD_VolumetricRegion/SetupAssets/PID_Device_Mutator.PID_Device_Mutator"
MODULATOR = "/CreativeCoreDevices/SetupAssets/PID_Device_MovementModulator.PID_Device_MovementModulator"
MOVEMENT = "/CRD_PlayerMovement/SetupAssets/PID_CP_Devices_PlayerMovement.PID_CP_Devices_PlayerMovement"
DIRECTOR = "/{root}/_Verse.fnm_director"
TAG_MARKUP = "/Script/VerseTags.VerseTagMarkupComponent"
PROPS = "/CR_Legacy/Playsets/PlaysetProps"
# Walls with a real (openable) door, 384 tall, pivot centred, stretched to DOOR_W. One prop for every door
# (Aaron 2026-10-04: a door that looks different stands out as a hint); A..D are told apart by colour, the same
# scheme as the HUD answer tiles (Aaron 2026-10-08): each door panel in its letter's colour and, on the panel, a
# dark tile with the letter in that colour, like the HUD tile, painted on it (door_dress). Rewrite the doors alone with --doors-only.
DOOR_PROPS = [("OilRig_Platform_Wall_01_Door_01", 553)] * 4

START_Y = -12000        # hallway 1 starts here; the course runs toward +Y
DOOR_W = 553            # door prop width = door pitch
DOOR_H = 384
WALL_H = 600            # hallway walls; a lintel fills the door wall above the doors
WALL_T = 40
VEST = 700              # vestibule depth behind the door wall
# The vestibule trigger fills the vestibule to just short of the barrier. It was 60% of VEST until 2026-10-06, when
# the back 280 cm (where a player who ran or jumped through the door stops, against the barrier) turned out to be
# outside both the trigger and the director's backstop zone: the right door then did nothing until they moved.
TRIGGER_DEPTH = VEST - 20
VEST_TRIGGER_H = 300    # the vestibule trigger's detection box, from the floor up
# A trigger device senses only its StepBox component (read back 2026-10-09, boss mode B6): half-extent STEP_BOX and centre
# STEP_Z above the device origin, in cm at actor scale 1, both scaled with the actor. Every trigger here is placed with
# trigger_fit. (Until 2026-10-09 the course assumed a 600 cm box per unit scale: an arena pad sensed a 96 cm square 7 cm
# thick, 80 cm off the floor, inside its 450 cm tile; a vestibule trigger a fifth of the vestibule.)
STEP_BOX = (64, 64, 15)
STEP_Z = 32
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
    [("baffleL", 900), ("baffleR", 1450), ("baffleL", 2000)],   # the ice station: a slalom on a slippery floor
    [("slider", 1000), ("sliderR", 1800)],
    [("baffleL", 950), ("slider", 1450), ("baffleR", 1950)],
    [("slider", 950), ("hurdle", 1450), ("sliderR", 1950)],
]
HURDLE_H = 70


# Connector corridors between stations (Aaron 2026-10-04: "sometimes up stairs, down stairs, winding to left,
# winding to right, sometimes straight", with speed plates on the straights). CONNECTORS[k-1] joins station k to
# station k+1 (the last entry leads to the finish); a longer course repeats the list. Each is a list of segments
# (length cm, turn degrees from the previous heading, + = LEFT, rise cm, speed-plate positions as fractions of the
# segment). Every connector must end facing +Y again (the turns sum to 0): the director's arrival facing is +Y.
# A rising segment is a staircase and joins straight segments only (turn 0 at both ends). Levels must stay >= 0
# (the template ground is at 0 near the start).
def seg(length, turn=0, rise=0, plates=()):
    return (length, turn, rise, tuple(plates))


_WIND = [seg(300), seg(1200, 45), seg(500, -45), seg(1200, 45), seg(300, -45)]
CONNECTORS = [
    ("straight", [seg(2600, plates=[0.3])]),
    ("up", [seg(300), seg(800, rise=400), seg(400)]),
    ("left", _WIND),
    ("up", [seg(300), seg(800, rise=400), seg(400)]),
    ("straight", [seg(2600, plates=[0.25, 0.7])]),           # into the ice station
    ("right", [(l, -t, r, p) for l, t, r, p in _WIND]),
    ("down", [seg(300), seg(800, rise=-400), seg(400)]),
    ("left", _WIND),
    ("down", [seg(300), seg(800, rise=-400), seg(400)]),
    ("straight", [seg(3200, plates=[0.2, 0.6])]),           # the run to the finish
]
CONN_W = 1000           # connector width between its walls
FUNNEL = 600            # funnel from a station's full width down to CONN_W (and the flare back out)
STEP_RISE = 25          # stair step height; a staircase's length / steps is the tread
WALL_CHUNK = 4          # steps per stair wall piece (walls follow the stairs up in pieces)
# Speed plate: a visible movement modulator that boosts and pushes along the corridor. Its arrows point along
# the device's -Y (seen in the editor 2026-10-04), so it is placed at the corridor heading + 90; 513 cm square.
PLATE_SIZE = 513
# (Its duration, 3 s, is not settable from MCP.)
PLATE = {"visibleDuringGame": "Yes", "affect Movement Speed": True, "speed": 1.8,
         "apply Impulse": True, "forward Impulse": 2000.0, "upward Impulse": 300.0}
# Ice: station hallways with a slippery floor. A mutator zone over the hallway (fnm_ice_zone) tells the director
# who is on the ice; it applies the player movement device (fnm_ice_floor) to them with low ground friction and
# braking. Defaults (Current BR) are friction 6, braking 800.
ICE_STATIONS = {6}
# The device's Walking settings clamp braking to 800..1000 and refuse the braking curves (list_properties 2026-10-06), so
# friction carries the slide (default 6; 0.15 felt subtle, Aaron 2026-10-06) and the Common settings cap acceleration
# so a player is slow to get going and to turn. ICE_DEVICE: the device adds itself to EVERY player at game start unless
# bAddToPlayersOnStart is off, which put stations 1-5 on faint ice until station 6's exit took it away (Aaron 2026-10-06:
# "non icy levels have icy properties"); the director also RemoveFromAll()s at OnBegin. Re-apply: --ice-only.
# Each settings value is written ALONE (a write that carried the value and its <name>_Override flag together answered
# True but left the old value), then the assets are SAVED: saving is what refreshes the device's userOptionData (the
# propertyData strings the Creative options UI shows and, as far as we know, what a cook ships), which otherwise keeps
# the old number. ice_feel verifies both after the save.
ICE_FEEL = {"groundFriction": 0.05}
ICE_COMMON = {"maximumAcceleration": 500.0}
ICE_DEVICE = {"bAddToPlayersOnStart": False}
ZONE_BASE = (512, 512, 384)   # mutator zone at actor scale 1, bottom at the actor (like the barrier)
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
# Door dressing (door_dress). The panel's material is the prop's doorAnimatingMaterial (+ the DoorComponent override,
# for the editor): M_door_face_<x>, a texture in the door's colour with the HUD answer tile and letter drawn where the
# panel's front face shows it (tools/make_door_signs.py, imported by tools/import_art.py signs). The letter swings away
# with the door and has no collision. The wall frame round the door is a runtime MID that ignores an override: stock.
# THE PAINT IS ONLY AS DURABLE AS THE MATERIAL ASSET: deleting M_door_face_x (or M_fnm_wall_x) and importing it again empties
# every reference to it, and the actors do not repaint themselves (all 40 doors and every wall read back null on 2026-10-13
# after a full import_art run). import_art now keeps existing materials; repair with --door-paint / --paint-only, verify
# with --check-paint (door_dress itself reads each door back and stops the build on a miss).
# Tried and dropped (2026-10-08/09): a sign actor on the panel (stayed in the doorway when the door opened and blocked
# players: a FortStaticMeshActor's NoCollision set in the editor does not hold in play); a component parented to the
# DoorComponent (Creative props are respawned at runtime without editor-added components); the Spooky alphabet meshes
# ("Disallowed reference" at session validation); a billboard (borderless text does not render in play).
SIGN_COLOUR = (1.0, 0.8, 0.1)
# Barrier zone at actor scale 1 ("volume Transform" Box): 511 x 511 x 384, bottom at the actor. Its
# get_actor_bounds add a 128/96 cm editor margin all round, so don't size it from those.
BARRIER_BASE = (511, 511, 384, 0)

# Boss arena (GOALS G6 item 3): between the last station's connector and the finish hallway. A station-wide hall
# ARENA_LEN long; four answer pads (trigger zones PAD_SIZE square and PAD_H tall, each on a floor tile in its letter's
# colour); the boss platform near the far end (the boss, the titan, the cannons and the floating letters over the pads:
# tools/build_race_boss.py, since 2026-10-11); an adds spawner mid-arena; a gate barrier across the exit that opens per
# player at the kill. Every arena actor is labelled FNM_Arena_* (the
# connector INTO the arena carries that prefix too, like every connector carries the prefix of what it leads into).
ARENA = True
ARENA_LEN = 3000
PAD_SIZE = 450          # was 300; Aaron 2026-10-07 never found a pad
PAD_H = 150
PAD_TILE_T = 10
# The race arena's pad tile and trigger size. PAD_SIZE above stays boss mode's (build_bossmode places its pads with it).
# 4 m tiles at a 520 cm pitch leave a 120 cm gap, wider than a player's capsule, so standing on one pad never touches
# the next one's trigger (G10, 2026-10-14).
RACE_PAD_SIZE = 400
RACE_PAD_PITCH = 520
RACE_PAD_Y = 1100       # ~9.5 m in from the entry (ENTRY_Y 150)
# Pad centres, A..D, as (x from the arena's centre line, y from its start): ONE row, A B C D left to right, like every
# station's doors (door_centres: +X is the player's LEFT, A at +X). Edges at +-980 of the hall's +-1106.
PAD_SPOTS = [(RACE_PAD_PITCH * (1.5 - i), RACE_PAD_Y) for i in range(4)]
PLATFORM_W, PLATFORM_D, PLATFORM_H, PLATFORM_Y = 600, 400, 100, 2600
ENTRY_Y = 150           # the entry teleporter (arrival and retry point), this far into the hall on its centre line
ADDS_Y = 1800
GATE_Y = ARENA_LEN       # the gate barrier's front face; the arena's floor ends BARRIER_T past it
ARENA_CONNECTOR = [seg(1000)]
_WID = "/Game/Athena/Items/Weapons/{0}.{0}"
ADDS_WEAPON = _WID.format("WID_Pistol_SemiAuto_Athena_R_Ore_T03")      # the loadout's pistol
# Overrides on build_guards.SETTINGS (merged at build time: build_guards imports this module). BOSS_SETTINGS were the
# race's guard boss's until 2026-10-11 (now a Megabrute, tools/build_race_boss.py); build_bossmode's --check still
# reads its own old guard boss spawners against them.
BOSS_SETTINGS = {"spawnCount": 1, "totalSpawnLimit": 1, "showHealthBar": True, "enablePatrol": False,
                 "spawnRadius_InMeter": 1.0, "dropInventoryOnElimination": False, "maxShield": 0.0, "startingShield": 0.0}
ADDS_SETTINGS = {"spawnCount": 2, "totalSpawnLimit": 2, "spawnRadius_InMeter": 4.0, "maxPatrolDistance_InMeter": 6.0}

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


def ybox(label, cx, cy, length, width, z0, z1, yaw):
    """A solid `length` long along heading `yaw` (degrees, 90 = +Y), `width` across, centred on (cx, cy)."""
    r = u.call(SCENE, "add_to_scene_from_asset", {
        "asset_path": CUBE, "name": label,
        "xform": xform(cx, cy, (z0 + z1) / 2, length / 100, width / 100, (z1 - z0) / 100, yaw)})
    actor = r["returnValue"]["refPath"]
    tag(actor, label)
    return actor


def wall_between(label, ax, ay, bx, by, z0, z1):
    """A wall from point a to point b, overlapping a half thickness past each end so corners close."""
    length = math.hypot(bx - ax, by - ay) + WALL_T
    yaw = math.degrees(math.atan2(by - ay, bx - ax))
    return ybox(label, (ax + bx) / 2, (ay + by) / 2, length, WALL_T, z0, z1, yaw)


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


def trigger_fit(z, w, d, h):
    """(device z, sx, sy, sz) for a trigger whose detection box (StepBox) is w x d x h with its bottom at z."""
    sx, sy, sz = w / (2 * STEP_BOX[0]), d / (2 * STEP_BOX[1]), h / (2 * STEP_BOX[2])
    return z + h / 2 - STEP_Z * sz, sx, sy, sz


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


@functools.lru_cache(maxsize=None)
def project_mount():
    """The project's content mount (its plugin id), e.g. /c498eed2-...; FNM_Art lives under it."""
    root = u.call("ValkyrieToolset.VerseToolset", "ListFiles", {"path": "", "bRecursive": False})
    return next(e["name"] for e in root["returnValue"] if e["type"] == "Directory" and "(" not in e["name"]).rstrip("/")


def wall_material(key):
    return f"{project_mount()}/FNM_Art/M_fnm_wall_{key}.M_fnm_wall_{key}"


def exists(path):
    return u.call(ASSETS, "exists", {"path": path})["returnValue"]


def read(path, key):
    r = u.call(OBJ, "get_properties", {"instance": ref(path), "properties": [key]})["returnValue"]
    return (json.loads(r) if isinstance(r, str) else r)[key]


def first_ref(value):
    """The refPath of a property read back as a ref or a one-item list of refs (None when empty / null)."""
    if isinstance(value, list):
        value = value[0] if value else None
    return (value or {}).get("refPath")


def door_face(i):
    key = LETTERS[i].lower()
    return f"{project_mount()}/FNM_Art/M_door_face_{key}.M_door_face_{key}"


def door_problem(door, i):
    """What is wrong with door prop `door` answering i (A = 0), read back: its panel material and the DoorComponent
    override must both be M_door_face_<letter>. None when right. A null reads back when the asset was deleted and
    re-imported under the door (tools/import_art.py: --force)."""
    want = door_face(i)
    anim, over = first_ref(read(door, "doorAnimatingMaterial")), first_ref(read(f"{door}.DoorComponent", "overrideMaterials"))
    if anim != want or over != want:
        return f"doorAnimatingMaterial {anim}, DoorComponent override {over}, wanted {want}"
    if read(door, "bCanBeDamaged") is not False:
        return "bCanBeDamaged is not false (a door re-placed after tools/build_island.py hardening is damageable again)"
    return None


def door_dress(door, i):
    """Paint door prop `door` as answer i (A = 0): its colour with the letter tile on the panel, and make it indestructible
    (a door placed after build_island.py ran was damageable: 40 of 40 read back true on 2026-10-13). Read back at once: a
    write that did not take (a missing material answers True and reads back null) stops the build."""
    face = ref(door_face(i))
    props(door, {"bCanBeDamaged": False})       # every placed gallery prop is damageable (build_island.harden); a re-placed door was again
    props(door, {"doorAnimatingMaterial": face})
    props(f"{door}.DoorComponent", {"overrideMaterials": [face]})
    if bad := door_problem(door, i):
        sys.exit(f"{door} not painted: {bad}")


def clear_door_signs(found):
    """Remove the letter boards (before 2026-10-08) and sign actors (2026-10-08) that door_face replaced."""
    for a in found:
        if isinstance(a, dict) and re.fullmatch(r"FNM_S\d\d_(Label|DoorSign)[A-D]", a.get("label", "")):
            u.call(SCENE, "remove_from_scene", {"actor": ref(a["actorPath"])})


def door_centres(doors):
    """Door A first. A player facing the doors (+Y) has +X on their LEFT, so A is at +X."""
    half = doors * DOOR_W / 2
    return [half - DOOR_W * (i + 0.5) for i in range(doors)]


def station(k, ox, oy, oz, hall, doors, project, door_assets):
    """Station k (1-based) whose hallway starts at (ox, oy) on level oz (floor top at oz + 2). Returns the y where
    its vestibules end."""
    half = doors * DOOR_W / 2
    t = WALL_T
    prefix = f"FNM_S{k:02d}"
    door_y = oy + hall                      # door wall centre line
    vest0 = door_y + 25                     # vestibule from the door wall's back face ...
    vest1 = vest0 + VEST                    # ... to the barrier
    end = vest1 + BARRIER_T                 # the next hallway starts here

    box(f"{prefix}_Floor", ox - half - t, ox + half + t, oy, end, oz + 2 - SLAB_T, oz + 2)
    box(f"{prefix}_WallL", ox + half, ox + half + t, oy, end, oz, oz + WALL_H)
    box(f"{prefix}_WallR", ox - half - t, ox - half, oy, end, oz, oz + WALL_H)
    if k == 1:
        box(f"{prefix}_WallStart", ox - half - t, ox + half + t, oy - t, oy, oz, oz + WALL_H)
    box(f"{prefix}_Lintel", ox - half, ox + half, door_y - 25, door_y + 25, oz + DOOR_H, oz + WALL_H)
    for i in range(1, doors):
        x = ox + half - DOOR_W * i
        box(f"{prefix}_Divider{i}", x - t / 2, x + t / 2, door_y + 25, vest1, oz, oz + WALL_H)

    tp = device(TELEPORTER, f"{prefix}_Entry", ox, oy + 150, oz, yaw=90)
    props(tp, {"knob_TeleporterGroup": "Group_None", "knob_TargetTeleporterGroup": "Group_None"})
    verse_tags(tp, project, [f"fnm_station_{k:02d}", "fnm_entry"])
    sign = device(BILLBOARD, f"{prefix}_Sign", ox + half - 5, oy + 600, oz + 250, yaw=-90, sx=2, sy=2, sz=2)
    board(sign, f"STATION {k}" + ("  - ICE!" if k in ICE_STATIONS else ""), SIGN_COLOUR)

    obstacles(k, ox, oy, oz, half, project)
    if k in ICE_STATIONS:
        zw, zd, zh = ZONE_BASE
        zone = device(MUTATOR, f"{prefix}_IceZone", ox, (oy + door_y - 25) / 2, oz,
                      sx=2 * half / zw, sy=(door_y - 25 - oy) / zd, sz=WALL_H / zh)
        # bAllowWeaponFire: the Mutator Zone defaults to NO weapon fire inside it (Aaron 2026-10-07: "weapons cannot fire on
        # the ice level"); the ice only changes movement, so guns stay live.
        props(zone, {"bAffectsGuards": False, "bAffectsCreatures": False, "zoneVisibleDuringGame": False,
                     "bAllowWeaponFire": True})
        verse_tags(zone, project, ["fnm_ice_zone"])

    bw, bd, bh, bz = BARRIER_BASE
    for i, dx in enumerate(door_centres(doors)):
        cx = ox + dx
        letter = LETTERS[i]
        asset, width = door_assets[i]
        door_dress(prop(asset, f"{prefix}_Door{letter}", cx, door_y, oz, sx=DOOR_W / width), i)
        inner = DOOR_W - t                  # vestibule width between dividers
        trig_depth = TRIGGER_DEPTH
        tz, tsx, tsy, tsz = trigger_fit(oz, inner, trig_depth, VEST_TRIGGER_H)
        trig = device(TRIGGER, f"{prefix}_Trigger{letter}", cx, vest0 + trig_depth / 2, tz, sx=tsx, sy=tsy, sz=tsz)
        # Device_Trigger_V2 names (differ from the legacy trigger's).
        props(trig, {"timesCanTrigger_Override": False, "triggerDelay": 0.0, "reset Delay": 0.0,
                     "visible in Game": False, "triggeredByVehicles": False, "triggeredByWater": False,
                     "triggeredByPhysicsProps": False})
        verse_tags(trig, project, [f"fnm_station_{k:02d}", f"fnm_door_{letter.lower()}"])
        sz = WALL_H / bh
        bar = device(BARRIER, f"{prefix}_Passage{letter}", cx, vest1 + BARRIER_T / 2, oz - bz * sz,
                     sx=inner / bw, sy=BARRIER_T / bd, sz=sz)
        props(bar, {"invisibleToIgnoredPlayers": True, "collide with Camera": False})
        verse_tags(bar, project, [f"fnm_station_{k:02d}", f"fnm_door_{letter.lower()}"])
    return end


def obstacles(k, ox, oy, oz, half, project):
    """Station k's hallway obstacles (OBSTACLES). +X is the player's left."""
    for n, (kind, dy) in enumerate(OBSTACLES[min(k, len(OBSTACLES)) - 1], 1):
        y = oy + dy
        label = f"FNM_S{k:02d}_{kind.capitalize()}{n}"
        if kind == "hurdle":
            box(label, ox - half, ox + half, y - 20, y + 20, oz, oz + HURDLE_H)
        elif kind == "baffleL":
            box(label, ox + BAFFLE_GAP - half, ox + half, y - WALL_T / 2, y + WALL_T / 2, oz, oz + WALL_H)
        elif kind == "baffleR":
            box(label, ox - half, ox + half - BAFFLE_GAP, y - WALL_T / 2, y + WALL_T / 2, oz, oz + WALL_H)
        else:
            # The director slides a container 2 * SLIDE_X along its own forward axis and back (fnm_director
            # Slide): a left one (+X side) sits at yaw 180 so its forward is -X, a right one at yaw 0 moves +X.
            left = kind == "slider"
            x = ox + (SLIDE_X if left else -SLIDE_X)
            verse_tags(prop(CONTAINER, label, x, y, oz, yaw=180 if left else 0), project, ["fnm_slider"])


def _trim(angle, outer):
    """How far a connector wall runs past (outer, +) or stops short of (inner, -) a joint turning `angle` degrees."""
    k = math.tan(math.radians(abs(angle)) / 2)
    return (CONN_W / 2 + WALL_T) * k if outer else -(CONN_W / 2) * k


def connector(name, segments, ox, y0, oz, half, prefix):
    """The corridor from a station's vestibule exit (ox, y0, level oz) to the next hallway: a funnel down to
    CONN_W, the segments, a flare back to full width. Returns the next hallway's (ox, oy, oz)."""
    t = WALL_T
    w = CONN_W / 2
    box(f"{prefix}_FloorFunnel", ox - half - t, ox + half + t, y0, y0 + FUNNEL, oz + 2 - SLAB_T, oz + 2)
    for side, sgn in (("L", 1), ("R", -1)):
        wall_between(f"{prefix}_WallFunnel{side}", ox + sgn * (half + t / 2), y0, ox + sgn * (w + t / 2), y0 + FUNNEL,
                     oz, oz + WALL_H)
    x, y, z, h = ox, y0 + FUNNEL, oz, 90.0
    plate_n = 0
    for i, (length, turn, rise, plates) in enumerate(segments):
        h -= turn                                   # + turn = left = toward +X from +Y = smaller yaw
        nxt = segments[i + 1][1] if i + 1 < len(segments) else 0
        fx, fy = math.cos(math.radians(h)), math.sin(math.radians(h))
        lx, ly = fy, -fx                            # the player's left
        # At a left turn the left wall is the inner one (stops short), the right the outer one (runs past).
        ends = {"L": (_trim(turn, turn < 0), _trim(nxt, nxt < 0)), "R": (_trim(turn, turn > 0), _trim(nxt, nxt > 0))}
        z1 = z + rise
        if rise == 0:
            a, b = -_trim(turn, True), length + _trim(nxt, True)
            c = (a + b) / 2
            ybox(f"{prefix}_FloorC{i + 1}", x + fx * c, y + fy * c, b - a, CONN_W + 2 * t, z + 2 - SLAB_T, z + 2, h)
            for side, sgn in (("L", 1), ("R", -1)):
                a, b = -ends[side][0], length + ends[side][1]
                c = (a + b) / 2
                off = sgn * (w + t / 2)
                ybox(f"{prefix}_WallC{i + 1}{side}", x + fx * c + lx * off, y + fy * c + ly * off, b - a, t,
                     z, z + WALL_H, h)
            for frac in plates:
                plate_n += 1
                c = length * frac
                plate = device(MODULATOR, f"{prefix}_Plate{plate_n}", x + fx * c, y + fy * c, z + 2, yaw=h + 90,
                               sx=(CONN_W - 100) / PLATE_SIZE)
                props(plate, PLATE)
        else:
            if turn or nxt:
                sys.exit(f"connector {name}: a staircase must join straight segments")
            steps = max(1, round(abs(rise) / STEP_RISE))
            tread, r = length / steps, rise / steps
            low = min(z, z1)
            tops = [z + (j + 1) * r for j in range(steps)]
            for j in range(steps):
                c = (j + 0.5) * tread
                ybox(f"{prefix}_Step{i + 1}_{j + 1:02d}", x + fx * c, y + fy * c, tread, CONN_W + 2 * t,
                     low + 2 - SLAB_T, tops[j] + 2, h)
            for j0 in range(0, steps, WALL_CHUNK):
                j1 = min(steps, j0 + WALL_CHUNK)
                hi = max([z + j0 * r] + tops[j0:j1])
                c = (j0 + j1) / 2 * tread
                for side, sgn in (("L", 1), ("R", -1)):
                    off = sgn * (w + t / 2)
                    ybox(f"{prefix}_WallC{i + 1}{side}{j0 // WALL_CHUNK + 1}", x + fx * c + lx * off,
                         y + fy * c + ly * off, (j1 - j0) * tread, t, low, hi + WALL_H, h)
        x, y, z = x + fx * length, y + fy * length, z1
        if z < 0:
            sys.exit(f"connector {name} goes below level 0")
    if abs(h - 90.0) > 1e-6:
        sys.exit(f"connector {name} ends at heading {h}, not 90 (+Y)")
    box(f"{prefix}_FloorFlare", x - half - t, x + half + t, y, y + FUNNEL, z + 2 - SLAB_T, z + 2)
    for side, sgn in (("L", 1), ("R", -1)):
        wall_between(f"{prefix}_WallFlare{side}", x + sgn * (w + t / 2), y, x + sgn * (half + t / 2), y + FUNNEL,
                     z, z + WALL_H)
    return x, y + FUNNEL, z


def spawner(label, x, y, z, project, tags, overrides, weapon, health=None):
    """A guard spawner (build_guards.SPAWNER) facing -Y with build_guards.SETTINGS + overrides, its weapon read back.
    health: ask the device for this max/starting health and return what it kept (the device's cap)."""
    import build_guards as g                  # it imports this module: import late
    actor = device(g.SPAWNER, label, x, y, z, yaw=-90)
    # Tag first: adding the tag component rebuilds the device's settings sub-objects (uefn-mcp skill).
    verse_tags(actor, project, tags)
    for key, value in {**g.SETTINGS, **overrides}.items():   # one key per call (a combined write can keep an old value)
        props(actor, {key: value})
    kept = None
    if health is not None:
        props(actor, {"max Health": health})
        props(actor, {"startingHealth": health})
        back = json.loads(u.call(OBJ, "get_properties", {"instance": ref(actor), "properties": ["max Health", "startingHealth"]})["returnValue"])
        kept = back.get("max Health")
        print(f"{label}: asked max/starting health {health:.0f}, the device kept {back}")
    items = json.loads(u.call(OBJ, "get_properties", {"instance": ref(actor), "properties": ["itemList"]})["returnValue"])
    props(items["itemList"]["refPath"], {"itemListData": [{"itemDefinition": ref(weapon), "itemQuantity": 1}]})
    back = json.loads(u.call(OBJ, "get_properties", {"instance": items["itemList"], "properties": ["itemListData"]})["returnValue"])["itemListData"]
    if not back or (back[0].get("itemDefinition") or {}).get("refPath") != weapon:
        sys.exit(f"{label}: the guard spawner refused {weapon}")
    opts = json.loads(u.call(OBJ, "get_properties", {"instance": ref(actor), "properties": list(overrides)})["returnValue"])
    wrong = {k: opts.get(k) for k, v in overrides.items() if opts.get(k) != v}
    if wrong:
        print(f"{label}: settings read back differently: {wrong}")
    return actor, kept


def arena(ox, oy, oz, doors, project):
    """The boss arena whose floor starts at (ox, oy) on level oz (LAYOUT.md "Boss arena"). Returns the y where it ends
    (the gate's back face), where the connector to the finish starts."""
    half = doors * DOOR_W / 2
    t = WALL_T
    end = oy + GATE_Y + BARRIER_T
    box("FNM_Arena_Floor", ox - half - t, ox + half + t, oy, end, oz + 2 - SLAB_T, oz + 2)
    box("FNM_Arena_WallL", ox + half, ox + half + t, oy, end, oz, oz + WALL_H)
    box("FNM_Arena_WallR", ox - half - t, ox - half, oy, end, oz, oz + WALL_H)
    tp = device(TELEPORTER, "FNM_Arena_Entry", ox, oy + ENTRY_Y, oz, yaw=90)
    props(tp, {"knob_TeleporterGroup": "Group_None", "knob_TargetTeleporterGroup": "Group_None"})
    verse_tags(tp, project, ["fnm_boss", "fnm_entry"])
    sign = device(BILLBOARD, "FNM_Arena_Sign", ox + half - 5, oy + 600, oz + 250, yaw=-90, sx=2, sy=2, sz=2)
    board(sign, "BOSS ARENA", SIGN_COLOUR)
    for i, (dx, dy) in enumerate(PAD_SPOTS):
        letter = LETTERS[i]
        x, y = ox + dx, oy + dy
        p = RACE_PAD_SIZE / 2
        box(f"FNM_Arena_Pad{letter}", x - p, x + p, y - p, y + p, oz + 2, oz + 2 + PAD_TILE_T)
        tz, tsx, tsy, tsz = trigger_fit(oz + 2, RACE_PAD_SIZE, RACE_PAD_SIZE, PAD_H)
        trig = device(TRIGGER, f"FNM_Arena_Trigger{letter}", x, y, tz, sx=tsx, sy=tsy, sz=tsz)
        props(trig, {"timesCanTrigger_Override": False, "triggerDelay": 0.0, "reset Delay": 0.0,
                     "visible in Game": False, "triggeredByVehicles": False, "triggeredByWater": False,
                     "triggeredByPhysicsProps": False})
        verse_tags(trig, project, ["fnm_boss", f"fnm_door_{letter.lower()}"])
    py = oy + PLATFORM_Y
    box("FNM_Arena_Platform", ox - PLATFORM_W / 2, ox + PLATFORM_W / 2, py - PLATFORM_D / 2, py + PLATFORM_D / 2,
        oz + 2, oz + 2 + PLATFORM_H)
    spawner("FNM_Arena_Adds", ox, oy + ADDS_Y, oz + 2, project, ["fnm_boss_adds"], ADDS_SETTINGS, ADDS_WEAPON)
    bw, bd, bh, bz = BARRIER_BASE
    sz = WALL_H / bh
    gate = device(BARRIER, "FNM_Arena_Gate", ox, oy + GATE_Y + BARRIER_T / 2, oz - bz * sz,
                  sx=2 * half / bw, sy=BARRIER_T / bd, sz=sz)
    props(gate, {"invisibleToIgnoredPlayers": True, "collide with Camera": False})
    verse_tags(gate, project, ["fnm_boss_gate"])
    print(f"arena built at x={ox:.0f} y={oy:.0f}..{end:.0f} level {oz:.0f}; the boss rig is tools/build_race_boss.py's")
    return end


def finish(ox, oy, oz, doors, project):
    half = doors * DOOR_W / 2
    t = WALL_T
    end = oy + FINISH_LEN
    box("FNM_Finish_Floor", ox - half - t, ox + half + t, oy, end + t, oz + 2 - SLAB_T, oz + 2)
    box("FNM_Finish_WallL", ox + half, ox + half + t, oy, end, oz, oz + WALL_H)
    box("FNM_Finish_WallR", ox - half - t, ox - half, oy, end, oz, oz + WALL_H)
    box("FNM_Finish_WallEnd", ox - half - t, ox + half + t, end, end + t, oz, oz + WALL_H)
    tp = device(TELEPORTER, "FNM_Finish_Entry", ox, oy + 150, oz, yaw=90)
    props(tp, {"knob_TeleporterGroup": "Group_None", "knob_TargetTeleporterGroup": "Group_None"})
    verse_tags(tp, project, ["fnm_finish"])
    # The end wall's board is the all-time screen (tools/build_finish.py, Aaron 2026-10-05), not a FINISH! sign.


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


# What paint() colours (labels). Walls, lintels, dividers, baffles, hurdles, the arena's pads and platform take a wall colour;
# floors (a hallway's, a connector's funnel / straight / flare / stair treads, the arena's, the finish's) a darker floor one.
WALL_LABEL = re.compile(r"FNM_(S\d\d|Finish|Arena)_(Wall|Lintel|Divider|Baffle|Hurdle|Pad[A-D]$|Platform$)")
FLOOR_LABEL = re.compile(r"FNM_(S\d\d|Finish|Arena)_Floor(C\d+|Funnel|Flare)?")


def paint_key(label, stations, tiers):
    """The material key (M_fnm_wall_<key>, tools/import_art.py) the actor `label` is painted with, None if it stays as
    built (stations: how many the course has, tiers: the cartridges' tier count). A station hallway's floor takes that
    tier's floor colour; a connector's floor and walls (labelled with the hallway they lead into) the next hallway's;
    the arena the hardest tier's; the finish gold walls over a dark gold-brown floor; the ice station's floor stays ice;
    every station's Lintel (the band over its doors, where build_door_marks stands the letters) dark."""
    floor = FLOOR_LABEL.fullmatch(label) or re.fullmatch(r"FNM_(S\d\d|Finish|Arena)_Step\d+_\d+", label)   # a tread is floor
    if not floor and not WALL_LABEL.match(label):
        return None
    if m := re.fullmatch(r"FNM_S(\d\d)_Floor", label):
        if int(m[1]) in ICE_STATIONS:
            return "ice"
    kind = "floor_" if floor else ""
    if label.endswith("_Lintel"):
        return "lintel"
    # Hurdles are gold (the finish colour) so they stand out against the tier colour; stair treads are floor and take the
    # dark floor colour (they took the wall colour until 2026-10-13, when pale blue steps glared). The arena plays the hardest tier: its walls (and the connector's into it)
    # take the tier-5 colour, each answer pad's tile its letter's colour (M_fnm_wall_pad_a..d).
    if label.startswith("FNM_Finish"):
        return "floor_finish" if floor else "finish"
    if "_Hurdle" in label or label == "FNM_Arena_Platform":
        return "finish"
    if pad := re.fullmatch(r"FNM_Arena_Pad([A-D])", label):
        return f"pad_{pad.group(1).lower()}"
    if label.startswith("FNM_Arena"):
        return f"{kind}tier5"
    return f"{kind}tier{auto_tier(int(label[5:7]), stations, tiers)}"


# Titan Peak surfaces (G9 wave 5, briefs/g9/T1_surfaces_arches.md): the walls and floors of each tier's stations and connectors
# wear that tier's tiling Mint material (tools/import_titanpeak.py --materials: M_fnm_tp_<t1_floor .. t5_wall, forge_floor>,
# world-scale box projection, so a scaled engine cube is not stretched) instead of the flat WALL_COLOURS paint. The arena floor
# wears forge_floor; the arena walls, the lintels (the dark band the door letters read against), the hurdles, the arena pads and
# platform, and the finish keep their flat colours. SURFACES is the default; `--flat` paints (and checks) the old flat colours,
# one command back: `python tools/build_course.py --paint-only --flat`.
SURFACES = True
SURFACE_FOLDER = "FNM_TitanPeakArt/Surfaces"


def surface_key(label, key, stations, tiers):
    """The Titan Peak surface (import_titanpeak.SURFACES) the actor `label` wears in place of its flat paint `key` (paint_key),
    None when it keeps the flat colour."""
    if key is None or key in ("lintel", "finish", "floor_finish") or key.startswith("pad_"):
        return None
    if label.startswith("FNM_Arena"):
        return "forge_floor" if key.startswith("floor_") else None     # TITAN'S FORGE: iron floor, walls left as they are
    if key == "ice":                                                   # the ice station's floor: its tier's (FROST RIDGE) floor
        return f"t{auto_tier(int(label[5:7]), stations, tiers)}_floor"
    m = re.fullmatch(r"(floor_)?tier(\d)", key)
    return f"t{m[2]}_{'floor' if m[1] else 'wall'}" if m else None


def surface_material(key):
    return f"{project_mount()}/{SURFACE_FOLDER}/M_fnm_tp_{key}.M_fnm_tp_{key}"


def paint_material(label, stations, tiers, surfaces=None):
    """The material path paint() puts on actor `label` (None: not painted). surfaces None = the SURFACES default."""
    key = paint_key(label, stations, tiers)
    if key is None:
        return None
    s = surface_key(label, key, stations, tiers) if (SURFACES if surfaces is None else surfaces) else None
    return surface_material(s) if s else wall_material(key)


def paint_jobs(surfaces=None):
    """[(actor, material path)] for every course actor paint() colours, plus (stations, tiers)."""
    found = [a for a in u.call(SCENE, "find_actors", {"tag": TAG, "collision_channels": []})["returnValue"] if isinstance(a, dict)]
    stations = len({a["label"][5:7] for a in found if re.match(r"FNM_S\d\d_(Wall|Lintel)", a.get("label", ""))})
    tiers = tier_count()
    jobs = [(a, m) for a in found if (m := paint_material(a.get("label", ""), stations, tiers, surfaces))]
    return jobs, stations, tiers


_COMPS = {}


def wall_override(actor_path):
    """(static mesh component path, its first overrideMaterials ref path or None)."""
    if actor_path not in _COMPS:
        _COMPS[actor_path] = read(actor_path, "staticMeshComponent")["refPath"]
    comp = _COMPS[actor_path]
    return comp, first_ref(read(comp, "overrideMaterials"))


def short(material):
    """M_fnm_wall_tier1 / M_fnm_tp_t1_wall from a material path (for messages)."""
    return (material or "None").rsplit(".", 1)[-1]


def paint(surfaces=None):
    """Dress each hallway's walls AND floor by the tier played there (the Titan Peak surfaces, or with surfaces=False the flat
    colours of tools/import_art.py), the finish gold, then save and read every actor's override back. Idempotent (an actor
    already right is not written); safe to rerun alone after a cartridge change (--paint-only). A missing material stops it
    before anything is written."""
    jobs, stations, tiers = paint_jobs(surfaces)
    missing = sorted(m for m in {m for _, m in jobs} if not exists(m.split(".")[0]))
    if missing:
        flat = [short(m)[len("M_fnm_wall_"):] for m in missing if "/FNM_Art/" in m]
        tp = [short(m)[len("M_fnm_tp_"):] for m in missing if "/FNM_Art/" not in m]
        sys.exit("materials missing: " + "; ".join(([f"{flat}: python tools/import_art.py {' '.join(flat)}"] if flat else [])
                                                   + ([f"{tp}: python tools/import_titanpeak.py --materials"] if tp else [])))
    wrote = 0
    for a, material in jobs:
        comp, now = wall_override(a["actorPath"])
        if now != material:
            props(comp, {"overrideMaterials": [ref(material)]})
            wrote += 1
    u.call(ASSETS, "save_assets", {"asset_paths": []})
    bad = check_paint(jobs)
    if bad:
        sys.exit(f"{len(bad)} actors did not keep their paint after the save, e.g. " + "; ".join(bad[:4]))
    kind = "Titan Peak surfaces" if (SURFACES if surfaces is None else surfaces) else "flat colours"
    print(f"painted {len(jobs)} actors with {kind} ({wrote} written, the rest already right) over {stations} stations "
          f"({tiers} tiers); read back after save: all {len(jobs)} hold their material")


def check_paint(jobs=None, surfaces=None):
    """Read every painted actor's override back; the list of those that do not hold the wanted material."""
    if jobs is None:
        jobs = paint_jobs(surfaces)[0]
    bad = []
    for a, material in jobs:
        _, now = wall_override(a["actorPath"])
        if now != material:
            bad.append(f"{a['label']} {short(now)} != {short(material)}")
    return bad


def find_doors():
    found = u.call(SCENE, "find_actors", {"tag": TAG, "collision_channels": []})["returnValue"]
    return sorted((a for a in found if isinstance(a, dict) and re.fullmatch(r"FNM_S\d\d_Door[A-D]", a.get("label", ""))),
                  key=lambda a: a["label"])


def door_paint():
    """Re-apply door_dress to every door prop already in the level (nothing is removed or placed), save, and read all of
    them back: the repair after a door face was replaced, and the check that the paint survives a save. Idempotent."""
    doors = find_doors()
    if not doors:
        sys.exit("no FNM_Sxx_DoorX actors: run the full build")
    for a in doors:
        door_dress(a["actorPath"], LETTERS.index(a["label"][-1]))
    u.call(ASSETS, "save_assets", {"asset_paths": []})
    bad = [f"{a['label']}: {p}" for a in doors if (p := door_problem(a["actorPath"], LETTERS.index(a["label"][-1])))]
    if bad:
        sys.exit("doors not painted after the save: " + "; ".join(bad[:4]))
    print(f"{len(doors)} doors painted; after the save every doorAnimatingMaterial and DoorComponent override reads back "
          f"as its own letter's M_door_face_x")


def check_all_paint(surfaces=None):
    """Read-only: every door and every painted wall / floor against what the build wants. Exit 1 when any is off."""
    doors = find_doors()
    bad = [f"{a['label']}: {p}" for a in doors if (p := door_problem(a["actorPath"], LETTERS.index(a["label"][-1])))]
    bad += check_paint(surfaces=surfaces)
    print(f"{len(doors)} doors checked; {len(bad)} paint problems" + ("" if not bad else ": " + "; ".join(bad[:6])))
    if bad:
        sys.exit(1)


def doors_only():
    """Swap every station's door props for DOOR_PROPS in place and paint them (door_dress); nothing else moves.
    Also removes the older letter boards and sign actors. The door-wall line comes from the station's lintel (a cube
    centred on the wall), not from the old door
    prop, whose bounds need not be symmetric in Y. Idempotent."""
    found = u.call(SCENE, "find_actors", {"tag": TAG, "collision_channels": []})["returnValue"]
    found = [a for a in found if isinstance(a, dict)]
    lintels = {a["label"][5:7]: a for a in found if re.fullmatch(r"FNM_S\d\d_Lintel", a.get("label", ""))}
    clear_door_signs(found)
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
        door_x = (lb["min"]["x"] + lb["max"]["x"]) / 2
        door_z = lb["min"]["z"] - DOOR_H
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
            door_dress(prop(assets[name], f"FNM_S{st}_Door{letter}", door_x + centres[i], door_y, door_z,
                            sx=DOOR_W / width), i)
            placed += 1
        print(f"station {int(st)}: removed {len(old)}, placed {len(letters)} doors at y={door_y:.0f}")
    print(f"{placed} doors placed")


def triggers_only():
    """Refit every vestibule trigger and arena pad trigger in place with trigger_fit, x and y kept. The floor comes from
    the door prop of the same station and letter (placed at the station's level) or from the pad tile's bottom. Reads
    every transform back. Idempotent."""
    found = u.call(SCENE, "find_actors", {"tag": TAG, "collision_channels": []})["returnValue"]
    by = {a["label"]: a for a in found if isinstance(a, dict) and "label" in a}
    xf = lambda a: u.call(ACTOR, "get_actor_transform", {"actor": ref(a["actorPath"])})["returnValue"]
    fits = []
    for label, a in sorted(by.items()):
        if m := re.fullmatch(r"FNM_S(\d\d)_Trigger([A-D])", label):
            door = by.get(f"FNM_S{m[1]}_Door{m[2]}") or sys.exit(f"{label}: no FNM_S{m[1]}_Door{m[2]}")
            fits.append((a, trigger_fit(xf(door)["location"]["z"], DOOR_W - WALL_T, TRIGGER_DEPTH, VEST_TRIGGER_H)))
        elif m := re.fullmatch(r"FNM_Arena_Trigger([A-D])", label):
            tile = by.get(f"FNM_Arena_Pad{m[1]}") or sys.exit(f"{label}: no FNM_Arena_Pad{m[1]}")
            fits.append((a, trigger_fit(tile["bounds"]["min"]["z"], RACE_PAD_SIZE, RACE_PAD_SIZE, PAD_H)))
    if not fits:
        sys.exit("no FNM_Sxx_Trigger / FNM_Arena_Trigger actors: run the full build")
    for a, (z, sx, sy, sz) in fits:
        t = xf(a)
        u.call(ACTOR, "set_actor_transform", {"actor": ref(a["actorPath"]), "xform": xform(
            t["location"]["x"], t["location"]["y"], z, sx, sy, sz, yaw=t["rotation"]["yaw"])})
    u.call(ASSETS, "save_assets", {"asset_paths": []})
    bad = []
    for a, want in fits:
        t = xf(a)
        got = (t["location"]["z"], t["scale"]["x"], t["scale"]["y"], t["scale"]["z"])
        if any(abs(g - w) > 0.01 * max(1.0, abs(w)) for g, w in zip(got, want)):
            bad.append(f"{a['label']} {got} != {want}")
    if bad:
        sys.exit("triggers not refit: " + "; ".join(bad))
    print(f"{len(fits)} triggers refit (transforms read back), e.g. {fits[0][0]['label']} z/scale {tuple(round(v, 3) for v in fits[0][1])}")


def arena_pads():
    """Move the arena's four pad tiles and triggers to PAD_SPOTS at RACE_PAD_SIZE in place (G10: one row), keeping their
    tags, labels, paint and Verse tags. The arena's origin comes from FNM_Arena_Entry (on the centre line, ENTRY_Y in).
    A tile keeps its height; a trigger is refit with trigger_fit from the tile's bottom. Reads every transform back."""
    found = u.call(SCENE, "find_actors", {"tag": TAG, "collision_channels": []})["returnValue"]
    by = {a["label"]: a for a in found if isinstance(a, dict) and "label" in a}
    xf = lambda a: u.call(ACTOR, "get_actor_transform", {"actor": ref(a["actorPath"])})["returnValue"]
    entry = xf(by.get("FNM_Arena_Entry") or sys.exit("no FNM_Arena_Entry: run the full build"))["location"]
    ox, oy = entry["x"], entry["y"] - ENTRY_Y
    want = []
    for letter, (dx, dy) in zip(LETTERS, PAD_SPOTS):
        tile = by.get(f"FNM_Arena_Pad{letter}") or sys.exit(f"no FNM_Arena_Pad{letter}")
        trig = by.get(f"FNM_Arena_Trigger{letter}") or sys.exit(f"no FNM_Arena_Trigger{letter}")
        t = xf(tile)
        z0 = tile["bounds"]["min"]["z"]
        tz, tsx, tsy, tsz = trigger_fit(z0, RACE_PAD_SIZE, RACE_PAD_SIZE, PAD_H)
        tt = xf(trig)
        want.append((tile, (ox + dx, oy + dy, t["location"]["z"], RACE_PAD_SIZE / 100, RACE_PAD_SIZE / 100, t["scale"]["z"]), t["rotation"]["yaw"]))
        want.append((trig, (ox + dx, oy + dy, tz, tsx, tsy, tsz), tt["rotation"]["yaw"]))
    for a, v, yaw in want:
        u.call(ACTOR, "set_actor_transform", {"actor": ref(a["actorPath"]), "xform": xform(*v, yaw=yaw)})
    u.call(ASSETS, "save_assets", {"asset_paths": []})
    bad = []
    for a, v, _ in want:
        t = xf(a)
        got = (t["location"]["x"], t["location"]["y"], t["location"]["z"], t["scale"]["x"], t["scale"]["y"], t["scale"]["z"])
        if any(abs(g - w) > 0.01 * max(1.0, abs(w)) for g, w in zip(got, v)):
            bad.append(f"{a['label']} {tuple(round(g, 2) for g in got)} != {tuple(round(w, 2) for w in v)}")
    if bad:
        sys.exit("arena pads not moved: " + "; ".join(bad))
    print(f"4 pad tiles + triggers at y={oy + RACE_PAD_Y:.0f}, x={[round(ox + dx) for dx, _ in PAD_SPOTS]}, {RACE_PAD_SIZE} cm (read back)")


def build(stations, doors, hall, arena_on=ARENA):
    root = u.call("ValkyrieToolset.VerseToolset", "ListFiles", {"path": "", "bRecursive": False})
    project = next(e["name"] for e in root["returnValue"] if e["type"] == "Directory" and "(" not in e["name"]).strip("/")
    print("removed", clear(), "old course actors;", clear("fnm_test"), "test actors")
    door_assets = [(door_asset(n), width) for n, width in DOOR_PROPS[:doors]]
    half = doors * DOOR_W / 2
    ox, oy, oz = 0.0, START_Y, 0.0
    for k in range(1, stations + 1):
        end = station(k, ox, oy, oz, hall, doors, project, door_assets)
        name, segments = CONNECTORS[(k - 1) % len(CONNECTORS)]
        nxt = f"FNM_S{k + 1:02d}" if k < stations else "FNM_Arena" if arena_on else "FNM_Finish"
        ox, oy, oz = connector(name, segments, ox, end, oz, half, nxt)
        print(f"station {k} built; then {name} to x={ox:.0f} y={oy:.0f} level {oz:.0f}")
    if arena_on:
        end = arena(ox, oy, oz, doors, project)
        ox, oy, oz = connector("arena", ARENA_CONNECTOR, ox, end, oz, half, "FNM_Finish")
    finish(ox, oy, oz, doors, project)
    # The director finds stations by tag (fnm_tags.verse): nothing to wire.
    device(DIRECTOR.format(root=project), "FNM_Director", -3000, START_Y, 0)
    if ICE_STATIONS:
        feel = device(MOVEMENT, "FNM_IceFeel", -3000, START_Y + 800, 0)
        # Tag first: adding the tag component rebuilds the device's settings sub-objects (the old ones turn into
        # TRASH_* and lose what was set on them).
        verse_tags(feel, project, ["fnm_ice_floor"])
        ice_feel(feel)
    print(f"finish at x={ox:.0f} y={oy:.0f} level {oz:.0f}; director placed")
    paint()


def ice_feel(feel):
    """Apply ICE_DEVICE, ICE_FEEL (Walking) and ICE_COMMON (Common) to the ice movement device and read them back."""
    props(feel, ICE_DEVICE)
    subs = json.loads(u.call(OBJ, "get_properties", {"instance": ref(feel),
                                                    "properties": ["movementSettings_Walking", "movementSettings_Common"]})["returnValue"])
    walking, common = subs["movementSettings_Walking"]["refPath"], subs["movementSettings_Common"]["refPath"]
    back = json.loads(u.call(OBJ, "get_properties", {"instance": ref(feel), "properties": list(ICE_DEVICE)})["returnValue"])
    for target, values in ((walking, ICE_FEEL), (common, ICE_COMMON)):
        for k, v in values.items():
            props(target, {f"{k}_Override": True})
            props(target, {k: v})
    u.call(ASSETS, "save_assets", {"asset_paths": []})
    for target, values in ((walking, ICE_FEEL), (common, ICE_COMMON)):
        got = json.loads(u.call(OBJ, "get_properties", {"instance": ref(target),
                                                       "properties": list(values) + ["userOptionData"]})["returnValue"])
        shown = {o["propertyName"]: o["propertyData"] for o in got.pop("userOptionData", {}).get("propertyOverrides", [])}
        for k, v in values.items():
            ui = shown.get(k[0].upper() + k[1:], "?")
            back[k] = got.get(k)
            if abs(float(got.get(k, 1e9)) - v) > 1e-6 or abs(float(ui or 1e9) - v) > 1e-6:
                sys.exit(f"ice: {k} read back {got.get(k)!r} (options UI {ui!r}), wanted {v!r}")
    print("ice device:", back)
    if back.get("bAddToPlayersOnStart") is not False:
        sys.exit("ice: bAddToPlayersOnStart did not clear")


def ice_only():
    """Re-apply the ice device's settings in place (after a tuning change; no course rebuild)."""
    found = u.call(SCENE, "find_actors", {"name": "FNM_IceFeel", "collision_channels": []})["returnValue"]
    feel = [a for a in found if isinstance(a, dict) and a.get("label") == "FNM_IceFeel"]
    if not feel:
        sys.exit("no FNM_IceFeel device: run the full build")
    ice_feel(feel[0]["actorPath"])


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--stations", type=int, default=10)
    ap.add_argument("--doors", type=int, default=4)
    ap.add_argument("--hall", type=int, default=3000, help="hallway length (cm) from entry to the door wall")
    ap.add_argument("--paint-only", action="store_true", help="only recolour the walls by tier")
    ap.add_argument("--doors-only", action="store_true", help="only replace the door props in place")
    ap.add_argument("--door-paint", action="store_true", help="only re-apply the doors' letter materials in place and read them back")
    ap.add_argument("--check-paint", action="store_true", help="read-only report of every door's and wall's / floor's paint")
    ap.add_argument("--ice-only", action="store_true", help="only re-apply the ice device's settings (ICE_*)")
    ap.add_argument("--triggers-only", action="store_true", help="only refit the vestibule and arena pad triggers in place (trigger_fit)")
    ap.add_argument("--arena-pads", action="store_true", help="only move the arena's pad tiles + triggers to PAD_SPOTS in place")
    ap.add_argument("--no-arena", action="store_true", help="build without the boss arena (the last connector leads to the finish)")
    ap.add_argument("--flat", action="store_true", help="with --paint-only / --check-paint / a build: the old flat WALL_COLOURS "
                                                        "paint instead of the Titan Peak surfaces")
    a = ap.parse_args()
    if a.flat:
        SURFACES = False
    if a.paint_only:
        paint()
    elif a.door_paint:
        door_paint()
    elif a.check_paint:
        check_all_paint()
    elif a.doors_only:
        doors_only()
    elif a.ice_only:
        ice_only()
    elif a.triggers_only:
        triggers_only()
    elif a.arena_pads:
        arena_pads()
    else:
        build(a.stations, a.doors, a.hall, not a.no_arena)
