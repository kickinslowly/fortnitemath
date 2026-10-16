"""Wall trim (tools/build_wall_trim.py, briefs/g10/W_walls.md): the planned pilasters, plinths and crest stay clear of play and
of every other piece of dressing, never reach into or over the invisible lids, keep the lanes wide, and stay off the arena,
the finish, the door walls and the vestibules. Pure Python against a snapshot of the level (tests/test_wall_trim_scene.json,
written by `build_wall_trim.py --dump-scene`); the clearance maths here is its own (numpy), not the planner's."""
import copy
import json
import math
import re
import sys
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

import build_wall_trim as wt  # noqa: E402

SCENE = json.loads((ROOT / "tests" / "test_wall_trim_scene.json").read_text(encoding="utf-8"))
WALKWAY = {"pier", "base", "cap", "plinth", "panel", "post"}
SOLID = {"pier", "base", "plinth", "panel", "post"}           # collision kept (what a player can touch)
TOP = {"crest", "finial"}

# what the brief says the trim must never touch, by obstacle label / tag / class
CATEGORIES = {
    "door wall": lambda o: re.match(r"FNM_S\d\d_(Lintel|Divider\d|Door[A-D])$", o["label"]),
    "arch": lambda o: o["tag"] == "fnm_arches",
    "vestibule / door trigger": lambda o: re.match(r"FNM_S\d\d_Trigger[A-D]$", o["label"]),
    "barrier": lambda o: re.match(r"FNM_S\d\d_Passage[A-D]$", o["label"]),
    "pickup pad": lambda o: re.match(r"FNM_S\d\d_Pad[LR]\d$", o["label"]),
    "pickup row trigger": lambda o: re.match(r"FNM_S\d\d_Row[LR]_Trigger$", o["label"]),
    "guard spawner": lambda o: re.match(r"FNM_S\d\d_Guards$", o["label"]),
    "slider travel": lambda o: re.match(r"FNM_S\d\d_Slider", o["label"]),
    "hurdle / baffle": lambda o: re.match(r"FNM_S\d\d_(Hurdle|Baffle)", o["label"]),
    "speed plate": lambda o: re.match(r"FNM_S\d\d_Plate\d$", o["label"]),
    "finish area": lambda o: o["label"] == "ZONE_Finish" or o["tag"] == "fnm_finish_rig",
    "arena": lambda o: o["label"] == "ZONE_Arena" or o["label"].startswith("FNM_Arena_"),
    "torch": lambda o: re.match(r"FNM_D\w*_Torch", o["label"]),
    "chalkboard": lambda o: re.match(r"FNM_D\d\d_Chalk", o["label"]),
    "station sign": lambda o: re.match(r"FNM_S\d\d_Sign$", o["label"]),
    "banner": lambda o: "_Banner_" in o["label"],
    "set piece": lambda o: "_Set_" in o["label"],
    "BASE CAMP gate": lambda o: o["label"] == "FNM_TP_Gate",
    "door letters and lights": lambda o: o["tag"] == "fnm_door_marks",
    "ice station dressing": lambda o: re.match(r"FNM_D06_", o["label"]),
}


@pytest.fixture(scope="module")
def pieces():
    return wt.plan(SCENE)


def axes(rot):
    """UE rotator (pitch, yaw, roll) -> rows = local X, Y, Z in world (written here from the UE formula, not imported)."""
    p, y, r = np.radians(rot)
    sp, cp, sy, cy, sr, cr = np.sin(p), np.cos(p), np.sin(y), np.cos(y), np.sin(r), np.cos(r)
    return np.array([[cp * cy, cp * sy, sp],
                     [sr * sp * cy - cr * sy, sr * sp * sy + cr * cy, -sr * cp],
                     [-(cr * sp * cy + sr * sy), cy * sr - cr * sp * sy, cr * cp]])


def box(b):
    return np.array(b["c"], float), axes(b["rot"]), np.array(b["size"], float) / 2


def box_corners(b):
    c, a, h = box(b)
    signs = np.array([[i, j, k] for i in (-1, 1) for j in (-1, 1) for k in (-1, 1)], float)
    return c + (signs * h) @ a


def intersects(b1, b2):
    """Separating-axis test for two oriented boxes (touching counts as intersecting)."""
    c1, a1, h1 = box(b1)
    c2, a2, h2 = box(b2)
    d = c2 - c1
    cand = list(a1) + list(a2) + [np.cross(x, y) for x in a1 for y in a2]
    for ax in cand:
        n = np.linalg.norm(ax)
        if n < 1e-6:
            continue
        ax = ax / n
        if abs(d @ ax) > np.abs(a1 @ ax) @ h1 + np.abs(a2 @ ax) @ h2:
            return False
    return True


def clashes(plan, obstacles):
    out = []
    for p in plan:
        pc = box_corners(p)
        plo, phi = pc.min(0), pc.max(0)
        for o in obstacles:
            if o["label"] == p["run"]:                     # a baffle's own dressing stands on it (a side wall is no obstacle)
                continue
            oc = box_corners(o)
            if (plo > oc.max(0)).any() or (phi < oc.min(0)).any():
                continue
            if intersects(p, o):
                out.append((p["label"], o["label"]))
    return out


def wall_frame(label):
    """(centre xy, unit direction along the wall, thickness, top z) of a run wall, from the snapshot's transform."""
    w = next(w for w in SCENE["walls"] if w["label"] == label)
    yaw = math.radians(w["yaw"])
    sx, sy, sz = w["size"]
    d = (math.cos(yaw), math.sin(yaw)) if sx >= sy else (-math.sin(yaw), math.cos(yaw))
    return np.array(w["c"][:2]), np.array(d), min(sx, sy), w["c"][2] + sz / 2, max(sx, sy)


# ---------------------------------------------------------------- the snapshot is not vacuous

def test_the_snapshot_holds_every_kind_of_thing_the_trim_must_avoid():
    for name, match in CATEGORIES.items():
        assert any(match(o) for o in SCENE["obstacles"]), name
    assert len(SCENE["lids"]) >= 60
    assert sum(1 for w in SCENE["walls"] if re.match(r"FNM_S\d\d_Wall[LR]$", w["label"])) == 20


def test_the_plan_is_substantial_and_deterministic(pieces):
    kinds, _ = wt.summary(pieces)
    assert kinds["pier"] >= 120 and kinds["plinth"] >= 100 and kinds["crest"] >= 300 and kinds["panel"] >= 80, kinds
    assert kinds["pier"] == kinds["base"] == kinds["cap"]
    assert kinds["post"] >= 3 and len(pieces) <= 1450, (kinds, len(pieces))      # the actor budget
    baffles = {p["run"] for p in pieces if wt.BAFFLE.match(p["run"]) and p["kind"] == "pier"}
    assert len(baffles) >= 8, baffles                                            # the straight-on walls are dressed
    again = wt.plan(copy.deepcopy(SCENE))
    assert [(p["label"], p["c"]) for p in again] == [(p["label"], p["c"]) for p in pieces]
    assert len({p["label"] for p in pieces}) == len(pieces)
    # every station hallway side wall gets pilasters, except the ice station (its own dressing fills the walls)
    per_wall = {}
    for p in pieces:
        if p["kind"] == "pier":
            per_wall[p["run"]] = per_wall.get(p["run"], 0) + 1
    for k in range(1, 11):
        for side in "LR":
            if k != 6:
                assert per_wall.get(f"FNM_S{k:02d}_Wall{side}", 0) >= 1, (k, side)


# ---------------------------------------------------------------- clearance (the brief's list)

def test_no_trim_piece_touches_play_or_another_decoration(pieces):
    bad = clashes(pieces, SCENE["obstacles"])
    assert not bad, bad[:10]


def test_the_clearance_check_catches_a_piece_on_a_pickup_pad(pieces):
    """Negative control: a plinth pushed onto a pickup pad must be reported (the check above is not vacuous)."""
    pad = next(o for o in SCENE["obstacles"] if re.match(r"FNM_S02_PadL1$", o["label"]))
    p = copy.deepcopy(next(p for p in pieces if p["kind"] == "plinth"))
    p["c"] = list(pad["c"])
    p["label"] = "SABOTAGE"
    assert ("SABOTAGE", "FNM_S02_PadL1") in clashes([p], SCENE["obstacles"])


# ---------------------------------------------------------------- the lids

def test_nothing_in_the_walkway_reaches_the_lids(pieces):
    """Walkway pieces end CAP_GAP under the wall top (the lids' underside) and touch no lid."""
    walk = [p for p in pieces if p["kind"] in WALKWAY]
    for p in walk:
        _, _, _, top, _ = wall_frame(p["run"])
        assert box_corners(p)[:, 2].max() <= top - wt.CAP_GAP + 1e-6, p["label"]
    bad = clashes(walk, SCENE["lids"])
    assert not bad, bad[:5]


def test_whatever_rises_through_a_lid_stands_on_its_wall_not_over_the_walkway(pieces):
    """Crest and finials pierce the invisible lids only on the wall's own footprint (+ OVERHANG): nothing sits above a lid
    over the walkway, and nothing floats (every crest piece starts at or under its wall's top)."""
    for p in (p for p in pieces if p["kind"] in TOP):
        c, d, thick, top, _ = wall_frame(p["run"])
        nrm = np.array([-d[1], d[0]])
        cs = box_corners(p)
        off = (cs[:, :2] - c) @ nrm                       # distance from the wall's centre line
        assert np.abs(off).max() <= thick / 2 + wt.OVERHANG + 1e-6, p["label"]
        assert cs[:, 2].min() <= top + 1e-6, p["label"]
        assert not p["collide"], p["label"]


# ---------------------------------------------------------------- lanes, collision, where it may stand

def test_pilasters_stay_shallow_and_no_lane_narrows_below_3_m(pieces):
    by = {w["label"]: w for w in SCENE["walls"]}
    for p in (p for p in pieces if p["kind"] in WALKWAY):
        c, d, thick, _, _ = wall_frame(p["run"])
        nrm = np.array([-d[1], d[0]])
        off = np.abs((box_corners(p)[:, :2] - c) @ nrm) - thick / 2   # how far it stands proud of the wall face
        assert off.max() <= 80 + 1e-6, p["label"]
        if wt.BAFFLE.match(p["run"]):
            # a baffle stands across the hallway: its dressing stands out along the run, never into the 9 m gap beyond the post
            _, _, _, _, length = wall_frame(p["run"])
            along = np.abs((box_corners(p)[:, :2] - c) @ d)
            assert along.max() <= length / 2 + wt.POST[1] + 1e-6, p["label"]
            continue
        m = wt.PARTNER.match(p["run"])
        partner = by[f"{m[1]}{'R' if m[2] == 'L' else 'L'}{m[3]}"]
        gap = abs((np.array(partner["c"][:2]) - c) @ nrm) - thick      # face-to-face width of the corridor
        assert gap - 2 * 80 >= 300, p["run"]
    # a baffle leaves a 9 m gap on one side: a pilaster opposite it still leaves more than 3 m
    for b in (o for o in SCENE["obstacles"] if re.match(r"FNM_S\d\d_Baffle", o["label"])):
        assert b["size"][0] <= 2212 - 900 + 1


def test_collision_only_where_a_player_stands_and_materials_by_tier(pieces):
    for p in pieces:
        assert p["collide"] == (p["kind"] in SOLID), p["label"]
        tier = SCENE["stations"][p["run"][5:7]]["tier"]
        assert re.fullmatch(rf"t{tier}_(trim|wall|panel)|t3_floor", p["mat"]), (p["label"], p["mat"])
        if p["kind"] in WALKWAY:
            assert p["mat"] == f"t{tier}_{'panel' if p['kind'] == 'panel' else 'trim'}", p["label"]
        if p["kind"] == "panel":                       # a skin, not a ledge
            c, d, thick, _, _ = wall_frame(p["run"])
            off = np.abs((box_corners(p)[:, :2] - c) @ np.array([-d[1], d[0]])) - thick / 2
            assert off.max() <= wt.PANEL_PROUD + 1e-6, p["label"]


def test_trim_stays_off_the_arena_finish_door_walls_and_vestibules(pieces):
    for p in pieces:
        assert wt.RUN.match(p["run"]) or wt.BAFFLE.match(p["run"]), p["run"]
        if p["kind"] in WALKWAY and re.match(r"FNM_S\d\d_Wall[LR]$", p["run"]):
            st = SCENE["stations"][p["run"][5:7]]
            # pilasters and plinths stop short of the arches' front; a 2 cm panel skin may run to the door wall's face
            stop = st["door_y"] - 25 - (0 if p["kind"] == "panel" else 40)
            assert box_corners(p)[:, 1].max() < stop, p["label"]
            assert box_corners(p)[:, 1].min() >= st["oy"] - 1e-6, p["label"]          # from the hallway start


def test_every_trim_material_the_plan_wears_is_imported():
    import import_titanpeak as tp
    used = {p["mat"] for p in wt.plan(SCENE)}
    trims = {m for m in used if m.endswith("_trim")}
    assert trims == set(tp.TRIMS), trims ^ set(tp.TRIMS)
    panels = {m for m in used if m.endswith("_panel")}
    assert panels == set(tp.PANELS), panels ^ set(tp.PANELS)
    assert used - trims - panels <= set(tp.SURFACES)              # the rest are the walls' own surfaces
    for key, art in tp.ART_MAP.items():                               # the second pass's maps are on disk and worn
        assert tp.art_key(key) == art, key
        assert all(p.exists() for p in tp.maps(art).values()), art
    assert not set(tp.TRIMS) & set(tp.SURFACES)                    # build_course's paint never sees a trim key
    for key in tp.TRIMS:
        maps = tp.maps(key)                                        # the Mint zip is unzipped
        assert all(p.exists() for p in maps.values()), key
        assert 200 <= tp.TRIM_TILE[key] <= 400, key
        scalars, vectors = tp.trim_knobs(key)
        assert {k for k, _ in scalars} <= set(tp.SURFACE_PARAMS) | {"MacroBlur"}, key
        assert tp.TRIM_PATCH[key][:-len("_patch")] in tp.SURFACES, key
    for key in tp.PANELS:                                          # no macro blotches on the saturated organic maps (in play)
        scalars, vectors = tp.panel_knobs(key)
        assert dict(scalars)["VariationBlend"] <= 0.5 and dict(scalars)["Jitter"] <= 0.1, key
        assert all(0.2 <= v <= 1.0 for v in dict(vectors)["Tint"]), key
    assert tp.ART == "FNM_TitanPeakArt" and tp.ART_MAP["t3_wall"] == "t3_wall2"   # the remap never shadows the folder again


def test_the_tool_has_the_flags_the_brief_asks_for():
    src = (ROOT / "tools" / "build_wall_trim.py").read_text(encoding="utf-8")
    for flag in ("--remove", "--check", "--only", "--dump-scene"):
        assert f'"{flag}"' in src, flag
    assert wt.TAG == "fnm_wall_trim"
