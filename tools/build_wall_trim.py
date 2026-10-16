"""Wall trim (G10, briefs/g10/W_walls.md): stone architecture on the course's side and connector walls so they stop reading
like wallpaper. Aaron (2026-10-13/14): the textured walls "feel repetitive and tiled too monotonously like wallpaper".

Why geometry and not more shader: every wall is a dead-flat 6 m engine box with a ruler-straight top edge, and its Mint texture
paints depth (ledges, snow-capped knobs, carved panels) that repeats every 3.5-4 m on that flat plane (editor frames 2026-10-14,
scratch W/before_*.png). This stands real shapes on it, built from scaled engine cubes (no credits, one mesh reused) wearing
the tier's surfaces (tools/import_titanpeak.py: the walls' M_fnm_tp_<tier>_wall, the tier's stone M_fnm_tp_<tier>_trim and
the bay skins M_fnm_tp_<tier>_panel, made by `--trim`), so the 30 m plane becomes bays:
- PILASTERS: a pier (+ a wider base and a cap) every PIER_GAP cm (3.8-6.8 m in a station hallway, sparser in a connector),
  jittered, 35-60 cm proud, in the tier's trim stone, on every station side wall's hallway part, every flat connector wall
  (funnel, straights, flare) and both faces of every hallway baffle. Collision on (shallow: no lane narrows below 3 m); the
  cap ends CAP_GAP under the wall top, so it never reaches the invisible lids.
- PLINTH: a low course of trim stone along each bay's foot, its height varied per bay.
- PANELS (second pass, 2026-10-15, after the parent's audit: an 8-10 m bay still showed two repeats of the 4 m tile): every
  other bay gets a 2 cm skin of the tier's second stone (ivy, moss and ferns, glacier ice, pumice, scorched strata), so
  neighbouring bays never repeat each other; it passes behind the torches and is cut round signs and boards.
- BAFFLES (second pass): the hallway baffles are seen straight on from the entry, so both faces get pilasters, plinth and
  panels, the top a crest, and the free end a post of trim stone with a finial (where no guard spawner is near).
- CREST: the straight top edge broken per tier, on the wall's own footprint (wall thickness + OVERHANG): t1 BASE CAMP ruined
  merlons, t2 WATERFALL GORGE tumbled slate rocks, t3 FROST RIDGE rocks with snow, t4 OBSIDIAN DESCENT glass shards,
  t5 MAGMA CORE scorched rocks; a taller FINIAL over every pilaster marks the bay. Stair walls get nothing (their tops
  already step up in chunks; the brief's frames showed them reading better than the flat walls).
Nothing is placed where it would touch play or another piece of dressing: every candidate is tested (oriented boxes, MARGIN)
against the doors, door wall, arches, vestibule and row triggers, barriers, pickup pads, guard spawners, slider containers
(their whole travel), hurdles, baffles, speed plates, torches, chalkboards, signs, banners, set pieces, the BASE CAMP gate,
the ice station's dressing and the arena; pilasters slide along the wall to a free spot or are dropped. Stays off the
FNM_Arena_* and FNM_Finish_* walls (another agent's / the finish), the door walls and the vestibules.

Reads geometry from the course actors at run time (like build_decor / build_lids), so RERUN AFTER A COURSE REBUILD.
Idempotent: every actor is tagged TAG and labelled FNM_WT_<run>_<n>_<kind>; a build removes the old ones first.

    python tools/build_wall_trim.py                 # remove + rebuild all trim (needs the UEFN lock)
    python tools/build_wall_trim.py --only S03      # just the runs of station 3 and the connector into it (prototype)
    python tools/build_wall_trim.py --remove        # remove all trim
    python tools/build_wall_trim.py --check         # read-only: placed == planned, materials held, clearance vs the live level
    python tools/build_wall_trim.py --plan          # read-only: print the plan's counts (no writes)
    python tools/build_wall_trim.py --dump-scene F  # read-only: write the scene the planner reads (tests use a snapshot)

The planner (read_scene -> plan) is pure Python on a JSON scene, so tests/test_wall_trim.py checks clearance without UEFN.
"""
import argparse
import json
import math
import random
import re
import sys
import zlib
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import uefn_mcp as u  # noqa: E402

TAG = "fnm_wall_trim"
PREFIX = "FNM_WT"
CUBE = "/Engine/BasicShapes/Cube.Cube"
SCENE = "editor_toolset.toolsets.scene.SceneTools"
ACTOR = "editor_toolset.toolsets.actor.ActorTools"
OBJ = "editor_toolset.toolsets.object.ObjectTools"
ASSETS = "editor_toolset.toolsets.asset.AssetTools"
PROG = "editor_toolset.toolsets.programmatic.ProgrammaticToolset"
SURFACE_DIR = "FNM_TitanPeakArt/Surfaces"

# what the trim must stay clear of (every tag another builder places on or near the course)
OBSTACLE_TAGS = ("fnm_course", "fnm_decor", "fnm_pickups", "fnm_guards", "fnm_arches", "fnm_door_marks", "fnm_titanpeak",
                 "fnm_mascot", "fnm_finish_rig", "fnm_race_boss", "fnm_landmarks", "fnm_analytics")
LID_TAG = "fnm_lids"
# runs: station side walls and connector walls of stations (a connector carries the prefix of the station it leads INTO);
# never the arena's, the finish's, the door wall (Lintel / Dividers) or station 1's back wall
RUN = re.compile(r"^FNM_S(\d\d)_(WallL|WallR|WallFunnel[LR]|WallFlare[LR]|WallC\d+[LR]\d*)$")
STAIR = re.compile(r"^FNM_S\d\d_WallC\d+[LR]\d+$")
# the hallway baffles (build_course obstacles "baffleL/R": a full-height wall from one side): seen straight on from the entry,
# so they are dressed too (second pass, the parent's audit), on both faces, with an end post at the free end
BAFFLE = re.compile(r"^FNM_S(\d\d)_Baffle[lr]\d+$")
PARTNER = re.compile(r"^(.*Wall(?:C\d+|Funnel|Flare)?)([LR])(\d*)$")
# course actors that are not obstacles: the runs' own walls (handled as runs), floors and stair treads (the trim stands on
# them), the course's invisible volumes and off-course devices
NOT_OBSTACLE = re.compile(r"^FNM_(S\d\d|Arena|Finish)_(Wall(L|R|Start|Funnel[LR]|Flare[LR]|C\d+[LR]\d*)|Floor\w*|Step\d+_\d+|"
                          r"IceZone)$|^FNM_(Director|IceFeel)$")
IGNORE_CLASSES = {"Device_MutatorVolume_V2_C", "VerseDevice_C", "Device_PlayerMovement_C", "Device_PostProcess_C",
                  "Device_CameraModes_Orbit_C", "Device_CRD_AudioPlayer_C", "CP_P_Atmospheric_Fireworks_C"}
# devices whose find_actors bounds carry an editor margin (uefn-mcp skill): their real shape comes from the transform
STEP_BOX, STEP_Z = (64, 64, 15), 32            # a Trigger V2 senses only its StepBox (build_course.trigger_fit)
BARRIER_BASE = (511, 511, 384)                  # a barrier's zone per unit scale, bottom at the actor
SLIDE = 1580                                    # a slider container travels 2 x build_course.SLIDE_X along its forward axis

WALL_H = 600
MARGIN = 15             # cm every piece keeps from an obstacle
OVERHANG = 25           # cm a crest piece may hang past the wall's faces (it must stand on the wall, not over the walkway)
CAP_GAP = 25            # a walkway piece's top stays this far under the wall top: 5 cm under the lids' underside (build_lids SINK 20)
SINK = 10               # crest pieces start this far down into the wall top (no visible seam)
END_CLEAR = 150         # pilasters stay this far from a run's ends (joints, corners)
ARCH_CLEAR = 180        # ... and this far from the door wall's face (the arches stand 40 cm proud of it)
START_CLEAR = 120       # ... and from a station hallway's start (the flare corner)
MIN_RUN = 500           # runs shorter than this get crest only
# Spacing per kind of run: the station hallways (where a runner stops, reads and looks round) get the dense dressing, the
# connectors (run through in seconds) a sparser one, which keeps the actor count down.
# Second pass: hallway bays 3.8-6.8 m, so a 4 m tile shows at most about one and a half repeats inside one bay.
PIER_GAP = {"side": (380, 680), "conn": (780, 1150), "baffle": (330, 560)}   # cm between pilaster centres (jittered)
PIER_SHIFT = 40         # a blocked pilaster tries positions this far apart ...
PIER_TRIES = 8          # ... this many each way
PLINTH_MIN = 120        # shorter plinth pieces are dropped
CLUSTER = {"side": (350, 800), "conn": (250, 550), "stair": (200, 400), "baffle": (300, 700)}   # crest clusters this long ...
CLUSTER_GAP = {"side": (100, 300), "conn": (450, 900), "stair": (350, 700), "baffle": (80, 250)}   # ... this much bare top between
# Panels (second pass): a 2 cm skin over every other bay between two pilasters, in the tier's second wall stone (import_titanpeak
# PANELS: its organic Mint layer with the wall blended back in), so neighbouring bays never show the same repeat. Only a skin:
# it keeps PANEL_MARGIN from obstacles (a torch hangs 7 cm off the wall) and is cut round them.
PANEL_PROUD = 2
PANEL_MARGIN = 3
PANEL_MIN = 150
PANEL_FOOT = 80         # its bottom: above the plinth (35-60) and the hurdles (70), so a hurdle does not cut it
# the end post wrapping a baffle's free end: this far back along the baffle, this far past its end, this far proud each side
POST = (50, 20, 22)

# Per tier: pier (width range, depth range), crest style and its materials, finial height. Materials are surface keys
# (tools/import_titanpeak.py): "trim" = M_fnm_tp_t<N>_trim, "wall" = M_fnm_tp_t<N>_wall, or a full key like "t3_floor".
TIERS = {
    1: {"name": "BASE CAMP", "pier_w": (110, 150), "pier_d": (40, 60), "crest": "merlons", "crest_mat": ["trim"],
        "finial": (130, 170)},
    2: {"name": "WATERFALL GORGE", "pier_w": (100, 140), "pier_d": (35, 55), "crest": "rocks", "crest_mat": ["wall", "wall", "trim"],
        "finial": (150, 210)},
    3: {"name": "FROST RIDGE", "pier_w": (100, 140), "pier_d": (35, 55), "crest": "rocks", "crest_mat": ["wall", "t3_floor", "wall"],
        "finial": (150, 210)},
    4: {"name": "OBSIDIAN DESCENT", "pier_w": (90, 130), "pier_d": (35, 50), "crest": "shards", "crest_mat": ["wall", "wall", "trim"],
        "finial": (240, 320)},
    5: {"name": "MAGMA CORE", "pier_w": (100, 140), "pier_d": (35, 55), "crest": "rocks", "crest_mat": ["wall", "trim"],
        "finial": (160, 220)},
}


# ---------------------------------------------------------------- geometry (pure)

def rot_axes(pitch, yaw, roll):
    """UE FRotationMatrix rows: the local X, Y, Z axes in world space (degrees)."""
    p, y, r = (math.radians(v) for v in (pitch, yaw, roll))
    sp, cp, sy, cy, sr, cr = math.sin(p), math.cos(p), math.sin(y), math.cos(y), math.sin(r), math.cos(r)
    return ((cp * cy, cp * sy, sp),
            (sr * sp * cy - cr * sy, sr * sp * sy + cr * cy, -sr * cp),
            (-(cr * sp * cy + sr * sy), cy * sr - cr * sp * sy, cr * cp))


def obb(c, size, rot=(0.0, 0.0, 0.0)):
    """An oriented box: centre, full size along its local axes (cm), rotation (pitch, yaw, roll)."""
    return {"c": list(c), "size": list(size), "rot": list(rot)}


def corners(b):
    ax = rot_axes(*b["rot"])
    h = [s / 2 for s in b["size"]]
    out = []
    for i in (-1, 1):
        for j in (-1, 1):
            for k in (-1, 1):
                out.append(tuple(b["c"][d] + i * h[0] * ax[0][d] + j * h[1] * ax[1][d] + k * h[2] * ax[2][d] for d in range(3)))
    return out


def aabb(b):
    cs = corners(b)
    return [min(p[d] for p in cs) for d in range(3)], [max(p[d] for p in cs) for d in range(3)]


def _dot(a, b):
    return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]


def _cross(a, b):
    return (a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0])


def overlap(a, b, margin=0.0):
    """True when oriented boxes a and b come within `margin` of each other (separating axis test, 15 axes)."""
    aa, ba = rot_axes(*a["rot"]), rot_axes(*b["rot"])
    ha = [s / 2 + margin for s in a["size"]]
    hb = [s / 2 for s in b["size"]]
    d = [b["c"][i] - a["c"][i] for i in range(3)]
    axes = list(aa) + list(ba) + [_cross(x, y) for x in aa for y in ba]
    for L in axes:
        n = math.sqrt(_dot(L, L))
        if n < 1e-6:
            continue
        L = (L[0] / n, L[1] / n, L[2] / n)
        ra = sum(ha[i] * abs(_dot(aa[i], L)) for i in range(3))
        rb = sum(hb[i] * abs(_dot(ba[i], L)) for i in range(3))
        if abs(_dot(d, L)) > ra + rb:
            return False
    return True


# ---------------------------------------------------------------- the scene (read live, or a JSON snapshot)

def _ref(p):
    return {"refPath": p}


def _find(tag):
    r = u.call(SCENE, "find_actors", {"tag": tag, "collision_channels": []})
    acts = r["returnValue"] if isinstance(r, dict) else r
    return [a for a in acts if isinstance(a, dict)]


def transforms(paths, chunk=150):
    """{actor path: transform} for many actors in a few batched calls (ProgrammaticToolset)."""
    out = {}
    paths = list(paths)
    for i in range(0, len(paths), chunk):
        part = paths[i:i + chunk]
        script = ("import json\nP = " + json.dumps(part) + "\n"
                  "def run():\n    out = {}\n    for p in P:\n"
                  "        out[p] = execute_tool('" + ACTOR + ".get_actor_transform', json.dumps({'actor': {'refPath': p}}))"
                  "['returnValue']\n    return out\n")
        r = u.call(PROG, "execute_tool_script", {"script": script})["returnValue"]
        out.update(json.loads(r) if isinstance(r, str) else r)
    return out


def _box_from_bounds(b):
    lo, hi = b["min"], b["max"]
    return obb([(lo[k] + hi[k]) / 2 for k in "xyz"], [hi[k] - lo[k] for k in "xyz"])


def _rot(t):
    r = t["rotation"]
    return [r["pitch"], r["yaw"], r["roll"]]


def _local_box(t, lo, hi):
    """An OBB from an actor-local box lo..hi (cm, already at the actor's scale) and the actor's transform t."""
    ax = rot_axes(*_rot(t))
    mid = [(lo[i] + hi[i]) / 2 for i in range(3)]
    c = [t["location"][k] + sum(mid[i] * ax[i][d] for i in range(3)) for d, k in enumerate("xyz")]
    return obb(c, [hi[i] - lo[i] for i in range(3)], _rot(t))


def obstacle_shapes(a, t):
    """The real shape(s) of obstacle actor `a` (find_actors dict) with transform t (None: use its bounds)."""
    cls = a["class"]["refPath"].split(".")[-1]
    if t is None:
        return [_box_from_bounds(a["bounds"])]
    if cls == "BP_TRV_ALight_Torch_02_CP_C":
        # find_actors bounds (306 x 260 x 488 at scale 2) include the light and the particle; the solid torch is the mesh
        # SM_TRV_Castle_Torch_03 (local x -48..0, y +-10.4, z -57.6..48) and the flame mesh at (-41, -1, 52) x 0.7 (read
        # 2026-10-14), both times the actor's scale, padded a little
        k = t["scale"]["x"]
        return [_local_box(t, [-52 * k, -14 * k, -60 * k], [4 * k, 14 * k, 50 * k]),
                _local_box(t, [-54 * k, -14 * k, 28 * k], [-27 * k, 14 * k, 96 * k])]
    return [_obstacle_shape(a, t, cls)]


def _obstacle_shape(a, t, cls):
    loc, s = t["location"], t["scale"]
    if cls == "Device_Trigger_V2_C":
        return obb([loc["x"], loc["y"], loc["z"] + STEP_Z * s["z"]], [2 * STEP_BOX[0] * s["x"], 2 * STEP_BOX[1] * s["y"],
                                                                     2 * STEP_BOX[2] * s["z"]], _rot(t))
    if cls == "Device_Barrier_V2_Placed_C":
        h = BARRIER_BASE[2] * s["z"]
        return obb([loc["x"], loc["y"], loc["z"] + h / 2], [BARRIER_BASE[0] * s["x"], BARRIER_BASE[1] * s["y"], h], _rot(t))
    if cls == "Device_Teleporter_V2_C":
        return obb([loc["x"], loc["y"], loc["z"] + 150], [300, 300, 300])
    if cls == "Device_PointLight_V2_C":
        return obb([loc["x"], loc["y"], loc["z"]], [60, 60, 60])
    if cls == "Apollo_Industrial_ShippingContainer_01_C":
        # the director slides it SLIDE cm along its forward axis and back: block the whole travel
        b = _box_from_bounds(a["bounds"])
        f = rot_axes(*_rot(t))[0]
        end = [b["c"][d] + f[d] * SLIDE for d in range(3)]
        lo = [min(b["c"][d], end[d]) - b["size"][d] / 2 for d in range(3)]
        hi = [max(b["c"][d], end[d]) + b["size"][d] / 2 for d in range(3)]
        return obb([(lo[d] + hi[d]) / 2 for d in range(3)], [hi[d] - lo[d] for d in range(3)])
    return _box_from_bounds(a["bounds"])


NEEDS_TRANSFORM = {"Device_Trigger_V2_C", "Device_Barrier_V2_Placed_C", "Device_Teleporter_V2_C", "Device_PointLight_V2_C",
                   "Apollo_Industrial_ShippingContainer_01_C", "BP_TRV_ALight_Torch_02_CP_C"}


def read_scene():
    """The planner's input, read from the open level: the run walls, the stations, the obstacles and the lids."""
    from build_course import auto_tier, tier_count     # noqa: PLC0415 (build_course reads the slot to count tiers)
    found = {tag: _find(tag) for tag in OBSTACLE_TAGS + (LID_TAG,)}
    course = {a["label"]: a for a in found["fnm_course"] if "label" in a}
    want = [a for a in course.values() if RUN.match(a["label"]) or BAFFLE.match(a["label"])]
    special = [a for tag in OBSTACLE_TAGS for a in found[tag]
               if a["class"]["refPath"].split(".")[-1] in NEEDS_TRANSFORM and not NOT_OBSTACLE.match(a.get("label", ""))]
    tf = transforms([a["actorPath"] for a in want + special + found[LID_TAG]])
    stations_n = len({lab[5:7] for lab in course if re.match(r"FNM_S\d\d_Lintel$", lab)})
    tiers = tier_count()
    walls = []
    for a in sorted(want, key=lambda a: a["label"]):
        t = tf[a["actorPath"]]
        walls.append({"label": a["label"], "c": [t["location"][k] for k in "xyz"], "yaw": t["rotation"]["yaw"],
                      "size": [t["scale"][k] * 100 for k in "xyz"]})
    stations = {}
    for lab, a in course.items():
        if m := re.match(r"FNM_S(\d\d)_Lintel$", lab):
            k = m[1]
            fl = course[f"FNM_S{k}_Floor"]["bounds"]
            lb = a["bounds"]
            stations[k] = {"tier": auto_tier(int(k), stations_n, tiers), "oy": fl["min"]["y"], "floor_z": fl["max"]["z"],
                           "door_y": (lb["min"]["y"] + lb["max"]["y"]) / 2, "cx": (lb["min"]["x"] + lb["max"]["x"]) / 2}
    obstacles = []
    for tag in OBSTACLE_TAGS:
        for a in found[tag]:
            lab = a.get("label", "")
            cls = a["class"]["refPath"].split(".")[-1]
            if cls in IGNORE_CLASSES or NOT_OBSTACLE.match(lab):
                continue
            for shape in obstacle_shapes(a, tf.get(a["actorPath"])):
                obstacles.append({"label": lab, "tag": tag, "class": cls, **shape})
    # the arena and the finish as whole zones (their walls are not runs and not obstacles above): floor up 12 m
    for zone in ("Arena", "Finish"):
        fl = course.get(f"FNM_{zone}_Floor")
        if fl:
            lo, hi = fl["bounds"]["min"], fl["bounds"]["max"]
            obstacles.append({"label": f"ZONE_{zone}", "tag": "zone", "class": "zone",
                              **obb([(lo["x"] + hi["x"]) / 2, (lo["y"] + hi["y"]) / 2, lo["z"] + 600],
                                    [hi["x"] - lo["x"], hi["y"] - lo["y"], 1200])})
    lids = []
    for a in found[LID_TAG]:
        t = tf[a["actorPath"]]
        lids.append({"label": a.get("label", ""), **obb([t["location"][k] for k in "xyz"], [t["scale"][k] * 100 for k in "xyz"],
                                                         _rot(t))})
    return {"stations": stations, "walls": walls, "obstacles": obstacles, "lids": lids}


# ---------------------------------------------------------------- the planner (pure)

def runs(scene):
    """One run per trim wall: its inner face as a line (p0 + t * s, s in 0..L), the inward normal n, thickness T, the
    wall's bottom z0 and top z1, the zone [a, b] of s where pilasters and plinths may stand (None: crest only), its tier."""
    by = {w["label"]: w for w in scene["walls"]}
    out = []
    for w in scene["walls"]:
        lab = w["label"]
        m = RUN.match(lab) or BAFFLE.match(lab)
        st = scene["stations"].get(m[1])
        if st is None:
            continue
        yaw = math.radians(w["yaw"])
        ex, ey = (math.cos(yaw), math.sin(yaw)), (-math.sin(yaw), math.cos(yaw))
        sx, sy, sz = w["size"]
        t, L, T = (ex, sx, sy) if sx >= sy else (ey, sy, sx)
        n0 = (-t[1], t[0])
        if BAFFLE.match(lab):
            # both faces are runs (face A crowns the top and wraps the free end); the free end is the one nearer the hallway's
            # centre line (the other meets a side wall)
            z0, z1 = w["c"][2] - sz / 2, w["c"][2] + sz / 2
            ends = [(w["c"][0] - t[0] * L / 2, w["c"][1] - t[1] * L / 2), (w["c"][0] + t[0] * L / 2, w["c"][1] + t[1] * L / 2)]
            cx = st.get("cx", 0.0)
            free = 0.0 if abs(ends[0][0] - cx) < abs(ends[1][0] - cx) else L
            for face, n in (("A", n0), ("B", (-n0[0], -n0[1]))):
                p0 = (w["c"][0] + n[0] * T / 2 - t[0] * L / 2, w["c"][1] + n[1] * T / 2 - t[1] * L / 2)
                out.append({"label": lab, "tier": st["tier"], "p0": p0, "t": t, "n": n, "L": L, "T": T, "z0": z0, "z1": z1,
                            "zone": (END_CLEAR, L - END_CLEAR), "kind": "baffle", "face": face, "free": free})
            continue
        pm = PARTNER.match(lab)
        partner = by.get(f"{pm[1]}{'R' if pm[2] == 'L' else 'L'}{pm[3]}")
        if partner is None:
            continue
        d = (partner["c"][0] - w["c"][0], partner["c"][1] - w["c"][1])
        n = n0 if d[0] * n0[0] + d[1] * n0[1] > 0 else (-n0[0], -n0[1])
        p0 = (w["c"][0] + n[0] * T / 2 - t[0] * L / 2, w["c"][1] + n[1] * T / 2 - t[1] * L / 2)
        z0, z1 = w["c"][2] - sz / 2, w["c"][2] + sz / 2
        zone = panel_zone = None
        if not STAIR.match(lab) and L >= MIN_RUN:
            if lab.endswith(("_WallL", "_WallR")):
                # the hallway part only: from its start to short of the door wall (never into the vestibules)
                ys = (st["oy"] + START_CLEAR, st["door_y"] - 25 - ARCH_CLEAR)
                ss = sorted(((y - p0[1]) / t[1]) for y in ys) if abs(t[1]) > 0.5 else (END_CLEAR, L - END_CLEAR)
                zone = (max(ss[0], 0.0), min(ss[1], L))
                ps_ = sorted(((y - p0[1]) / t[1]) for y in (st["oy"], st["door_y"] - 25)) if abs(t[1]) > 0.5 else (0.0, L)
                panel_zone = (max(ps_[0], 0.0), min(ps_[1], L))
            else:
                zone = (END_CLEAR, L - END_CLEAR)
            if zone[1] - zone[0] < 200:
                zone = None
        kind = "stair" if STAIR.match(lab) else "side" if lab.endswith(("_WallL", "_WallR")) else "conn"
        out.append({"label": lab, "tier": st["tier"], "p0": p0, "t": t, "n": n, "L": L, "T": T, "z0": z0, "z1": z1,
                    "zone": zone, "kind": kind, "panel_zone": panel_zone if kind == "side" and zone else None})
    return out


def piece(run, u0, u1, v0, v1, z0, z1, kind, mat, collide, extra=(0.0, 0.0, 0.0)):
    """A box spanning u0..u1 along the run, v0..v1 inward from its inner face, z0..z1; extra = (pitch, dyaw, roll)."""
    uc, vc = (u0 + u1) / 2, (v0 + v1) / 2
    p0, t, n = run["p0"], run["t"], run["n"]
    c = (p0[0] + t[0] * uc + n[0] * vc, p0[1] + t[1] * uc + n[1] * vc, (z0 + z1) / 2)
    yaw = math.degrees(math.atan2(t[1], t[0])) + extra[1]
    return {"kind": kind, "mat": mat, "collide": collide, "run": run["label"],
            **obb(c, [u1 - u0, v1 - v0, z1 - z0], [extra[0], yaw, extra[2]])}


def mat_key(run, m):
    return f"t{run['tier']}_{m}" if m in ("trim", "wall") else m


def blocked(p, obstacles, margin=MARGIN):
    lo, hi = aabb(p)
    for o in obstacles:
        olo, ohi = o["_aabb"]
        if any(lo[d] - margin > ohi[d] or hi[d] + margin < olo[d] for d in range(3)):
            continue
        if overlap(p, o, margin):
            return o["label"]
    return None


def free_stretches(run, u0, u1, make, near, margin=MARGIN, min_len=PLINTH_MIN, step=20.0):
    """Walk u0..u1 in `step` cm slices of make(a, b) (a piece); the pieces made from the stretches whose every slice is clear
    of `near` by `margin` and that are at least min_len long."""
    good, probe = [], u0
    while probe < u1:
        b = min(probe + step, u1)
        good.append((probe, blocked(make(probe, b), near, margin) is None))
        probe += step
    out, start = [], None
    for p0_, ok in good + [(u1, False)]:
        if ok and start is None:
            start = p0_
        if not ok and start is not None:
            if p0_ - start >= min_len:
                out.append(make(start, p0_))
            start = None
    return out


def pilaster(run, s, w, d, rng):
    """pier + base + cap at s along the run (s = centre), as walkway pieces."""
    z0, top = run["z0"], run["z1"] - CAP_GAP
    base_h, cap_h = rng.uniform(55, 85), rng.uniform(28, 40)
    m = mat_key(run, "trim")
    return [piece(run, s - w / 2, s + w / 2, -5, d, z0, top - cap_h, "pier", m, True),
            piece(run, s - w / 2 - 14, s + w / 2 + 14, -5, d + 12, z0, z0 + base_h, "base", m, True),
            piece(run, s - w / 2 - 12, s + w / 2 + 12, -5, d + 10, top - cap_h, top, "cap", m, False)]


def crest_ok(run, p):
    """A crest piece stands on the wall: every corner within the wall's footprint + OVERHANG, none below the wall's top - 60."""
    p0, n = run["p0"], run["n"]
    for x, y, z in corners(p):
        v = (x - p0[0]) * n[0] + (y - p0[1]) * n[1]          # 0 = inner face, -T = outer face
        if v > OVERHANG or v < -run["T"] - OVERHANG or z < run["z1"] - 60:
            return False
    return True


def crest_piece(run, uc, length, height, depth, kind, mat, rot, rng):
    """A crest box centred at uc on the wall's centre line, sunk SINK into the wall top; its rotation is halved until it
    stands on the wall (crest_ok)."""
    z0 = run["z1"] - SINK
    vc = -run["T"] / 2
    for _ in range(6):
        p = piece(run, uc - length / 2, uc + length / 2, vc - depth / 2, vc + depth / 2, z0, z0 + height, kind, mat, False, rot)
        if crest_ok(run, p):
            return p
        rot = tuple(r / 2 for r in rot)
    return None


def crest(run, finials, rng):
    """The run's top edge, per tier style, plus a finial over each pilaster centre in `finials`."""
    style = TIERS[run["tier"]]
    mats = style["crest_mat"]
    out = []
    s, end = 15.0, run["L"] - 15.0
    cluster_end = s + rng.uniform(*CLUSTER[run["kind"]])
    while s < end:
        kind = style["crest"]
        if s > cluster_end:                                  # a stretch of bare wall top between clusters
            s += rng.uniform(*CLUSTER_GAP[run["kind"]])
            cluster_end = s + rng.uniform(*CLUSTER[run["kind"]])
            continue
        if kind == "merlons":                                # a ruined crenellation: some merlons missing, some broken
            length, gap = rng.uniform(110, 190), rng.uniform(60, 120)   # second pass: longer merlons, fewer actors
            if s + length > end:
                break
            if rng.random() > 0.15:
                broken = rng.random() < 0.22
                h = rng.uniform(30, 50) if broken else rng.uniform(60, 110)
                rot = (rng.uniform(-4, 4), rng.uniform(-3, 3), rng.uniform(-6, 6)) if broken else (0.0, 0.0, 0.0)
                p = crest_piece(run, s + length / 2, length, h + SINK, run["T"] + 16, "crest", mat_key(run, rng.choice(mats)),
                                rot, rng)
                if p:
                    out.append(p)
            s += length + gap
        elif kind == "rocks":                                # tumbled rocks, overlapping, of varied size and tilt
            length = rng.uniform(150, 280)            # second pass: longer rocks, fewer actors
            h = rng.uniform(35, 120)
            rot = (rng.uniform(-14, 14), rng.uniform(-18, 18), rng.uniform(-12, 12))
            p = crest_piece(run, s + length / 2, min(length, end - s), h + SINK, rng.uniform(50, 72), "crest",
                            mat_key(run, rng.choice(mats)), rot, rng)
            if p:
                out.append(p)
            s += length * rng.uniform(0.8, 1.05)
        else:                                                # shards: tall thin leaning blades of glass
            length = rng.uniform(40, 80)
            h = rng.uniform(70, 210)
            rot = (rng.uniform(-18, 18), rng.uniform(-25, 25), rng.uniform(-10, 10))
            p = crest_piece(run, s + length / 2, length, h + SINK, rng.uniform(35, 55), "crest", mat_key(run, rng.choice(mats)),
                            rot, rng)
            if p:
                out.append(p)
            s += rng.uniform(90, 180)
    lo, hi = style["finial"]
    for f in finials:
        if style["crest"] == "merlons":
            p = crest_piece(run, f, rng.uniform(130, 170), rng.uniform(lo, hi), run["T"] + 30, "finial", mat_key(run, "trim"),
                            (0.0, 0.0, 0.0), rng)
        elif style["crest"] == "shards":
            p = crest_piece(run, f, rng.uniform(70, 100), rng.uniform(lo, hi), rng.uniform(45, 60), "finial",
                            mat_key(run, "wall"), (rng.uniform(-8, 8), rng.uniform(-20, 20), rng.uniform(-6, 6)), rng)
        else:
            p = crest_piece(run, f, rng.uniform(150, 220), rng.uniform(lo, hi), rng.uniform(60, 75), "finial",
                            mat_key(run, "wall"), (rng.uniform(-10, 10), rng.uniform(-15, 15), rng.uniform(-8, 8)), rng)
        if p:
            out.append(p)
    return out


def near_run(run, obstacles, reach=400):
    """The obstacles whose bounds come within `reach` cm of the run's wall (a cheap prefilter for blocked())."""
    p0, t, L = run["p0"], run["t"], run["L"]
    xs, ys = (p0[0], p0[0] + t[0] * L), (p0[1], p0[1] + t[1] * L)
    lo = (min(xs) - reach, min(ys) - reach, run["z0"] - reach)
    hi = (max(xs) + reach, max(ys) + reach, run["z1"] + reach)
    return [o for o in obstacles if o["label"] != run["label"]
            and all(o["_aabb"][0][d] <= hi[d] and o["_aabb"][1][d] >= lo[d] for d in range(3))]


def plan(scene, only=None):
    """[piece] for the whole course (or only the runs whose label starts FNM_<only>_): pilasters, plinths, crest, finials,
    each clear of every obstacle by MARGIN. Deterministic: the jitter is seeded by each run's label."""
    obstacles = []
    for o in scene["obstacles"]:
        o = dict(o)
        o["_aabb"] = aabb(o)
        obstacles.append(o)
    pieces = []
    for run in runs(scene):
        if only and not run["label"].startswith(f"FNM_{only}_"):
            continue
        rng = random.Random(zlib.crc32(run["label"].encode()))
        near = near_run(run, obstacles)
        style = TIERS[run["tier"]]
        found = []                                   # (s, half width) of placed pilasters
        if run["zone"]:
            a, b = run["zone"]
            s = a + rng.uniform(60, 260)
            while s <= b:
                w, d = rng.uniform(*style["pier_w"]), rng.uniform(*style["pier_d"])
                placed = None
                for k in range(PIER_TRIES * 2 + 1):
                    off = (k + 1) // 2 * PIER_SHIFT * (1 if k % 2 else -1)
                    sc = s + off
                    if sc - w / 2 - 14 < a - 60 or sc + w / 2 + 14 > b + 60:
                        continue
                    ps = pilaster(run, sc, w, d, rng)
                    if not any(blocked(p, near) for p in ps):
                        placed = (sc, ps, w)
                        break
                if placed:
                    sc, ps, w = placed
                    pieces += ps
                    found.append((sc, w / 2 + 14, w / 2))
                    s = sc + rng.uniform(*PIER_GAP[run["kind"]])
                else:
                    s += PIER_GAP[run["kind"]][0] / 2
            # plinth: a low course along every bay, cut round pilaster bases and obstacles
            edges = [a] + [e for sc, hw, _ in found for e in (sc - hw, sc + hw)] + [b]
            for i in range(0, len(edges), 2):
                h, d = rng.uniform(35, 60), rng.uniform(16, 24)
                pieces += free_stretches(run, edges[i], edges[i + 1], lambda u0, u1, h=h, d=d: piece(
                    run, u0, u1, -5, d, run["z0"], run["z0"] + h, "plinth", mat_key(run, "trim"), True), near)
            # panels: every other bay gets the tier's second stone as a 2 cm skin. A bay runs pier to pier, and from the run's
            # ends (a corner; on a station side wall the hallway's start and the door wall's corner) to the nearest pier; the
            # skin is cut round what hangs on the wall (signs, boards) and passes behind the torches
            lo_, hi_ = run.get("panel_zone") or (0.0, run["L"])
            stops = [lo_] + [e for sc, _, hw in found for e in (sc - hw, sc + hw)] + [hi_]
            first = rng.random() < 0.5
            for i in range(0, len(stops) - 1, 2):
                if (i // 2 % 2 == 0) != first:
                    continue
                u0, u1 = stops[i], stops[i + 1]
                pieces += free_stretches(run, u0, u1, lambda a_, b_: piece(
                    run, a_, b_, -3, PANEL_PROUD, run["z0"] + PANEL_FOOT, run["z1"] - CAP_GAP, "panel",
                    f"t{run['tier']}_panel", True), near, PANEL_MARGIN, PANEL_MIN)
        if run["kind"] == "stair":           # a staircase's walls already step up in chunks: their top is not a straight line
            continue
        if run.get("face") == "B":           # a baffle's second face: its top and its end are face A's
            continue
        if run["kind"] == "baffle":          # wrap the free end in a post of trim stone, crowned like a pilaster
            back, past, side = POST
            e = run["free"]
            u0, u1 = (e - back, e + past) if e > 0 else (e - past, e + back)
            post = piece(run, u0, u1, -run["T"] - side, side, run["z0"], run["z1"] - CAP_GAP, "post", mat_key(run, "trim"), True)
            if not blocked(post, near):
                pieces.append(post)
                fin = crest_piece(run, (u0 + u1) / 2, u1 - u0 + 10, rng.uniform(*style["finial"]) * 0.8, run["T"] + 30,
                                  "finial", mat_key(run, "trim"), (0.0, 0.0, 0.0), rng)
                if fin and not blocked(fin, near):
                    pieces.append(fin)
        fins = [sc for sc, _, _ in found]
        if run["kind"] == "conn":            # a connector is run through: a finial over every other pilaster is enough
            fins = fins[::2]
        for p in crest(run, fins, rng):
            if not blocked(p, near):
                pieces.append(p)
    count = {}
    for p in pieces:
        key = p["run"][len("FNM_"):]
        count[key] = count.get(key, 0) + 1
        p["label"] = f"{PREFIX}_{key}_{count[key]:03d}_{p['kind']}"
    return pieces


def summary(pieces):
    kinds, mats = {}, {}
    for p in pieces:
        kinds[p["kind"]] = kinds.get(p["kind"], 0) + 1
        mats[p["mat"]] = mats.get(p["mat"], 0) + 1
    return kinds, mats


# ---------------------------------------------------------------- UEFN (writes need the lock)

def mount():
    root = u.call("ValkyrieToolset.VerseToolset", "ListFiles", {"path": "", "bRecursive": False})
    return next(e["name"] for e in root["returnValue"] if e["type"] == "Directory" and "(" not in e["name"]).rstrip("/")


def material_path(key, project):
    return f"{project}/{SURFACE_DIR}/M_fnm_tp_{key}.M_fnm_tp_{key}"


def remove(only=None):
    found = [a for a in _find(TAG) if not only or a.get("label", "").startswith(f"{PREFIX}_{only}_")]
    paths = [a["actorPath"] for a in found]
    for i in range(0, len(paths), 150):
        script = ("import json\nP = " + json.dumps(paths[i:i + 150]) + "\n"
                  "def run():\n    for p in P:\n"
                  "        execute_tool('" + SCENE + ".remove_from_scene', json.dumps({'actor': {'refPath': p}}))\n"
                  "    return {'n': len(P)}\n")
        u.call(PROG, "execute_tool_script", {"script": script})
    return len(paths)


PLACE_SCRIPT = """import json
J = json.loads(%s)
def run():
    out = {}
    for p in J['pieces']:
        x = {'location': dict(zip('xyz', p['c'])), 'rotation': {'pitch': p['rot'][0], 'yaw': p['rot'][1], 'roll': p['rot'][2]},
             'scale': dict(zip('xyz', [s / 100.0 for s in p['size']]))}
        a = execute_tool('%s.add_to_scene_from_asset', json.dumps({'asset_path': J['cube'], 'name': p['label'], 'xform': x}))['returnValue']['refPath']
        execute_tool('%s.add_tag', json.dumps({'actor': {'refPath': a}, 'tag': J['tag']}))
        execute_tool('%s.set_label', json.dumps({'actor': {'refPath': a}, 'label': p['label']}))
        comp = json.loads(execute_tool('%s.get_properties', json.dumps({'instance': {'refPath': a}, 'properties': ['staticMeshComponent']}))['returnValue'])['staticMeshComponent']['refPath']
        execute_tool('%s.set_properties', json.dumps({'instance': {'refPath': comp}, 'values': json.dumps({'overrideMaterials': [{'refPath': J['mats'][p['mat']]}]})}))
        if not p['collide']:
            execute_tool('%s.set_properties', json.dumps({'instance': {'refPath': comp}, 'values': json.dumps({'bodyInstance': {'collisionEnabled': 'NoCollision', 'collisionProfileName': 'NoCollision'}})}))
        out[p['label']] = a
    return out
""" % ("%s", SCENE, ACTOR, ACTOR, OBJ, OBJ, OBJ)


def place(pieces, chunk=40):
    project = mount()
    mats = {k: material_path(k, project) for k in {p["mat"] for p in pieces}}
    missing = sorted(k for k, m in mats.items() if not u.call(ASSETS, "exists", {"path": m.split(".")[0]})["returnValue"])
    if missing:
        sys.exit(f"materials missing: {missing}: python tools/import_titanpeak.py --trim (and --materials)")
    placed = {}
    for i in range(0, len(pieces), chunk):
        part = [{k: p[k] for k in ("label", "c", "size", "rot", "mat", "collide")} for p in pieces[i:i + chunk]]
        payload = json.dumps({"pieces": part, "cube": CUBE, "tag": TAG, "mats": mats})
        r = u.call(PROG, "execute_tool_script", {"script": PLACE_SCRIPT % repr(payload)})["returnValue"]
        placed.update(json.loads(r) if isinstance(r, str) else r)
        print(f"  placed {len(placed)}/{len(pieces)}", flush=True)
    u.call(ASSETS, "save_assets", {"asset_paths": []})
    return placed


def check(only=None):
    """Read-only: every planned piece is placed (label, transform, material) and nothing else carries TAG; the plan is clear
    of the live level's obstacles. Exit 1 on any problem."""
    scene = read_scene()
    pieces = plan(scene, only)
    want = {p["label"]: p for p in pieces}
    found = {a["label"]: a for a in _find(TAG) if not only or a.get("label", "").startswith(f"{PREFIX}_{only}_")}
    bad = [f"missing {lab}" for lab in sorted(set(want) - set(found))][:10]
    bad += [f"extra {lab}" for lab in sorted(set(found) - set(want))][:10]
    common = sorted(set(want) & set(found))
    tf = transforms([found[lab]["actorPath"] for lab in common])
    project = mount()
    comps = {}
    for i in range(0, len(common), 150):
        part = [found[lab]["actorPath"] for lab in common[i:i + 150]]
        script = ("import json\nP = " + json.dumps(part) + "\n"
                  "def run():\n    out = {}\n    for p in P:\n"
                  "        c = json.loads(execute_tool('" + OBJ + ".get_properties', json.dumps({'instance': {'refPath': p}, "
                  "'properties': ['staticMeshComponent']}))['returnValue'])['staticMeshComponent']['refPath']\n"
                  "        m = json.loads(execute_tool('" + OBJ + ".get_properties', json.dumps({'instance': {'refPath': c}, "
                  "'properties': ['overrideMaterials']}))['returnValue'])['overrideMaterials']\n"
                  "        out[p] = (m[0] or {}).get('refPath') if m else None\n    return out\n")
        r = u.call(PROG, "execute_tool_script", {"script": script})["returnValue"]
        comps.update(json.loads(r) if isinstance(r, str) else r)
    for lab in common:
        p, t = want[lab], tf[found[lab]["actorPath"]]
        got = [t["location"][k] for k in "xyz"]
        if max(abs(g - w) for g, w in zip(got, p["c"])) > 1.0:
            bad.append(f"{lab} moved: {got} != {p['c']}")
        if comps.get(found[lab]["actorPath"]) != material_path(p["mat"], project):
            bad.append(f"{lab} material {comps.get(found[lab]['actorPath'])}")
    obstacles = []
    for o in scene["obstacles"]:
        o = dict(o)
        o["_aabb"] = aabb(o)
        obstacles.append(o)
    own = {}                                  # a baffle's own dressing stands on it: skip the run's own wall
    for p in pieces:
        own.setdefault(p["run"], [o for o in obstacles if o["label"] != p["run"]])
    clash = [f"{p['label']} touches {hit}" for p in pieces
             if (hit := blocked(p, own[p["run"]], PANEL_MARGIN if p["kind"] == "panel" else MARGIN))]
    bad += clash[:10]
    kinds, _ = summary(pieces)
    print(f"{len(found)} trim actors placed, {len(pieces)} planned {kinds}; {len(bad)} problems" +
          ("" if not bad else ":\n  " + "\n  ".join(bad[:20])))
    if bad:
        sys.exit(1)


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--only", help="station prefix, e.g. S03: just its runs (and the connector into it)")
    ap.add_argument("--remove", action="store_true")
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--plan", action="store_true", help="read-only: print what a build would place")
    ap.add_argument("--dump-scene", help="read-only: write the scene JSON the planner reads")
    a = ap.parse_args()
    if a.check:
        return check(a.only)
    if a.remove:
        print("removed", remove(a.only), "trim actors")
        return
    scene = read_scene()
    if a.dump_scene:
        Path(a.dump_scene).write_text(json.dumps(scene, indent=0), encoding="utf-8")
        print(f"scene: {len(scene['walls'])} walls, {len(scene['obstacles'])} obstacles, {len(scene['lids'])} lids -> {a.dump_scene}")
        return
    pieces = plan(scene, a.only)
    kinds, mats = summary(pieces)
    print(f"plan: {len(pieces)} pieces {kinds}; materials {mats}")
    if a.plan:
        return
    print("removed", remove(a.only), "old trim actors")
    place(pieces)
    print(f"placed {len(pieces)} trim actors; run --check to verify")


if __name__ == "__main__":
    main()
