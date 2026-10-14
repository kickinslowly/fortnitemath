"""Titan Peak dressing (tools/build_titanpeak.py): the start gate, the champions' podium, the tier set pieces and the place banners,
with no UEFN. The course comes from tools/build_course.py itself, run offline with its placement calls recorded (`offline_course`),
so the checks run on the numbers the builder reads from the editor: that copy was compared with the live editor's 386 recorded
boxes on 2026-10-13 (worst difference 0.0 cm, `test_the_offline_course_is_the_live_course` pins a dozen of them)."""
import json
import math
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

import build_course as c  # noqa: E402
import build_finish as fin  # noqa: E402
import build_landmarks as lm  # noqa: E402
import build_mascot as mascot  # noqa: E402
import build_titanpeak as tp  # noqa: E402

PROJECT = "c498eed2-96c5-4757-91a1-edb374b16d67"
TIERS = 5
EYE_BACK = 350.0            # the default third-person camera sits about this far behind the player
CAMERA_Z = 250.0            # ... and this high above the floor (build_landmarks' own estimate)
PEAK_DEG = 18.5             # the volcano's peak seen from station 1's camera (build_landmarks.PEAK_DEG)
ARM_HALF = 72.14            # SK_fnm_volt's half extent along the arms (T-pose), cm at scale 1
WIDE_BACK = 900.0           # the orbit camera (fnm_penalty_cam) at the podium


# ---------------------------------------------------------------- the course, offline
def bounds(x0, x1, y0, y1, z0, z1):
    return {"min": {"x": x0, "y": y0, "z": z0}, "max": {"x": x1, "y": y1, "z": z1}, "isValid": True}


def offline_course(stations=10, doors=4, hall=3000, arena=True):
    """{label: bounds} of the starter course, from tools/build_course.py with its editor calls replaced by recorders."""
    rec = {}

    def box(label, x0, x1, y0, y1, z0, z1):
        rec[label] = bounds(x0, x1, y0, y1, z0, z1)
        return label

    def ybox(label, cx, cy, length, width, z0, z1, yaw):
        t = math.radians(yaw)
        hx = (length * abs(math.cos(t)) + width * abs(math.sin(t))) / 2
        hy = (length * abs(math.sin(t)) + width * abs(math.cos(t))) / 2
        rec[label] = bounds(cx - hx, cx + hx, cy - hy, cy + hy, z0, z1)
        return label

    def prop(asset, label, x, y, z, yaw=0.0, sx=1.0):
        # a slider is a 607 x 246 x 295 container; every other prop here is a door (553 wide, 44 deep, 384 tall)
        rec[label] = bounds(x - 303.5, x + 303.5, y - 123, y + 123, z, z + 295) if "Slider" in label \
            else bounds(x - 276.5, x + 276.5, y - 22, y + 22, z, z + 384)
        return label

    names = ("box", "ybox", "prop", "device", "props", "verse_tags", "board", "door_dress", "spawner")
    saved = {n: getattr(c, n) for n in names}
    c.box, c.ybox, c.prop = box, ybox, prop
    c.device = lambda *a, **k: a[1]
    c.props = c.verse_tags = c.board = c.door_dress = lambda *a, **k: None
    c.spawner = lambda *a, **k: (a[0], None)
    try:
        half = doors * c.DOOR_W / 2
        ox, oy, oz = 0.0, c.START_Y, 0.0
        door_assets = [("x", c.DOOR_W)] * doors
        for k in range(1, stations + 1):
            end = c.station(k, ox, oy, oz, hall, doors, "proj", door_assets)
            name, segments = c.CONNECTORS[(k - 1) % len(c.CONNECTORS)]
            ox, oy, oz = c.connector(name, segments, ox, end, oz, half, f"FNM_S{k + 1:02d}" if k < stations else "FNM_Arena")
        end = c.arena(ox, oy, oz, doors, "proj")
        ox, oy, oz = c.connector("arena", c.ARENA_CONNECTOR, ox, end, oz, half, "FNM_Finish")
        c.finish(ox, oy, oz, doors, "proj")
    finally:
        for n, f in saved.items():
            setattr(c, n, f)
    return rec


COURSE = offline_course()
HALLS = tp.halls(COURSE)
STRIPS, CONN, ENDS = tp.all_strips(COURSE, TIERS)
SET = tp.set_pieces(COURSE, TIERS)
GATE = tp.gate_spec(COURSE)
PODIUM = tp.podium_spec(COURSE)
BANNERS = tp.banner_specs(COURSE, TIERS)
GATE_BANNER = tp.gate_banner(COURSE)


def rect_gap(px, py, rect):
    """Distance from a point to an axis-aligned rectangle (x0, x1, y0, y1); 0 inside."""
    x0, x1, y0, y1 = rect
    return math.hypot(max(x0 - px, 0.0, px - x1), max(y0 - py, 0.0, py - y1))


def segment_gap(a, b, rect, step=10.0):
    """Least distance from the segment a-b to a rectangle, sampled every `step` cm."""
    n = max(1, int(math.hypot(b[0] - a[0], b[1] - a[1]) / step))
    return min(rect_gap(a[0] + (b[0] - a[0]) * i / n, a[1] + (b[1] - a[1]) * i / n, rect) for i in range(n + 1))


def overlap(r1, r2, gap=0.0):
    """True when two (x0, x1, y0, y1) rectangles come within `gap` of each other."""
    return r1[0] - gap < r2[1] and r2[0] - gap < r1[1] and r1[2] - gap < r2[3] and r2[2] - gap < r1[3]


def hall_pieces(k):
    return [p for p in SET if p["strip"] == f"S{k:02d}"]


# ---------------------------------------------------------------- the course the maths run on
def test_the_offline_course_is_the_live_course():
    """Numbers read from the live editor on 2026-10-13 (find_actors tag fnm_course)."""
    live = {"FNM_S01_Floor": (-1146, 1146, -12000, -8235, -38, 2), "FNM_S01_Lintel": (-1106, 1106, -9025, -8975, 384, 600),
            "FNM_S03_Floor": (-1146, 1146, 2030, 5795, 362, 402), "FNM_S04_Floor": (551, 2843, 9792, 13557, 362, 402),
            "FNM_S05_Floor": (551, 2843, 16257, 20022, 762, 802), "FNM_S07_WallL": (1106, 1146, 31584, 35349, 800, 1400),
            "FNM_S10_DoorA": (2250, 2803, 55255, 55298, 0, 384), "FNM_Arena_Floor": (551, 2843, 60441, 63481, -38, 2),
            "FNM_Finish_Floor": (551, 2843, 65681, 67221, -38, 2), "FNM_Finish_WallEnd": (551, 2843, 67181, 67221, 0, 600),
            "FNM_S03_Bafflel1": (-206, 1106, 3010, 3050, 400, 1000), "FNM_S02_FloorC1": (-540, 540, -7635, -5035, -38, 2)}
    for label, (x0, x1, y0, y1, z0, z1) in live.items():
        b = COURSE[label]
        got = (b["min"]["x"], b["max"]["x"], b["min"]["y"], b["max"]["y"], b["min"]["z"], b["max"]["z"])
        assert got == pytest.approx((x0, x1, y0, y1, z0, z1), abs=1.0), label


def test_ten_halls_five_tiers_with_two_stations_each():
    assert sorted(HALLS) == list(range(1, 11))
    assert [tp.tier_of(k, 10, TIERS) for k in range(1, 11)] == [1, 1, 2, 2, 3, 3, 4, 4, 5, 5]


def test_the_connector_replay_lands_on_the_next_halls_first_edge():
    """`connector_strips` replays build_course.connector: where it ends must be the next hall's start, or its strips are off the corridor."""
    arena = tp.special_hall(COURSE, "FNM_Arena")
    for k in range(1, 11):
        want = (HALLS[k + 1]["cx"], HALLS[k + 1]["y0"], HALLS[k + 1]["z"] - 2) if k < 10 else (arena["cx"], arena["y0"], arena["z"] - 2)
        assert ENDS[k] == pytest.approx(want, abs=1.0), f"connector after station {k}"


def test_connector_strips_are_flat_segments_long_enough_to_hold_a_piece_and_stairs_carry_none():
    assert len(CONN) >= 9
    for s in CONN:
        assert s["half"] == c.CONN_W / 2 and s["s1"] - s["s0"] >= tp.MIN_STRIP
    # connectors 2, 4, 7 and 9 are the staircases ("up" / "down"): their flat landings are 300 and 400 cm, too short for a strip
    assert not ({"C02", "C04", "C07", "C09"} & {s["id"][:3] for s in CONN})
    assert {c.CONNECTORS[k][0] for k in (1, 3, 6, 8)} == {"up", "down"}


# ---------------------------------------------------------------- set pieces
def test_each_tier_gets_its_own_piece_and_a_rune_stone():
    for p in SET:
        if p["mesh"] != "rune_stone":
            assert p["mesh"] == tp.TIER_MESH[p["tier"]], p["label"]
    for tier in range(1, 6):
        mine = [p for p in SET if p["tier"] == tier]
        assert sum(1 for p in mine if p["mesh"] == "rune_stone") == 1, tier
        assert sum(1 for p in mine if p["mesh"] == tp.TIER_MESH[tier]) >= 2, tier


def test_a_connector_takes_the_tier_of_the_hall_it_leads_into():
    by = {s["id"]: s for s in STRIPS + CONN}
    assert by["C01_1"]["tier"] == 1 and by["C03_2"]["tier"] == 2 and by["C06_2"]["tier"] == 4 and by["C10_1"]["tier"] == 5
    assert by["C08_2"]["tier"] == 5          # into station 9


def test_piece_counts_stay_under_the_budget():
    per = {}
    for p in SET:
        per[p["strip"]] = per.get(p["strip"], 0) + 1
    assert max(v for k, v in per.items() if k.startswith("S")) <= 3 + 1          # 2-3 of the tier's, plus a rune stone
    assert max(v for k, v in per.items() if k.startswith("C")) <= 2 + 1
    total = len(SET) + 2 + 1 + len(BANNERS)
    assert 30 <= total <= 60, total
    assert len({p["label"] for p in SET}) == len(SET)


def test_no_set_piece_breaks_a_rule():
    assert tp.conflicts(COURSE, SET, TIERS) == []


def test_hall_pieces_stand_in_the_wall_band_clear_of_every_door_path_and_obstacle():
    """Independent of `conflicts`: boxes in the hall's own axes against the walls, the straight paths from the arrival spot to each door,
    the obstacle actors, the sign zone and the door wall."""
    for k in HALLS:
        h = HALLS[k]
        eye = (h["cx"], h["y0"] + 450.0)
        doors = [(h["cx"] + dx, h["door_face"]) for dx in c.door_centres(4)]
        for p in hall_pieces(k):
            x0, x1, y0, y1 = tp.footprint(p)
            assert h["right"] <= x0 and x1 <= h["left"], p["label"]                          # inside the walls
            assert min(abs(x0 - h["cx"]), abs(x1 - h["cx"])) >= 600 or (x0 - h["cx"]) * (x1 - h["cx"]) > 0, p["label"]
            assert not (x0 < h["cx"] + 600 and x1 > h["cx"] - 600), p["label"]                # the centre 12 m is the running field
            assert y0 >= h["y0"] + 1000 and y1 <= h["door_y"] - 700, p["label"]               # past the arrival corner, the pads, the signs; off the door wall
            for d_ in doors:
                assert segment_gap(eye, d_, (x0, x1, y0, y1)) >= 100, f"{p['label']} stands on the path to a door"
            for kind, oy0, oy1, _ in tp.obstacles(COURSE, k):
                assert y1 < oy0 - 40 or y0 > oy1 + 40 or (kind == "baffle"), f"{p['label']} over a {kind}"
            for kind, oy0, oy1, side in tp.obstacles(COURSE, k):
                if kind == "baffle":                                                         # a baffle's open side keeps its 900 cm gap
                    gap_x = (h["right"], h["right"] + 900) if side > 0 else (h["left"] - 900, h["left"])
                    assert not (overlap((x0, x1, y0, y1), (gap_x[0], gap_x[1], oy0, oy1), 150)), f"{p['label']} narrows a baffle's gap"
                    assert not overlap((x0, x1, y0, y1), (h["right"], h["left"], oy0, oy1), 0), f"{p['label']} inside a baffle"


def test_no_hall_piece_hides_a_door_panel_from_the_arrival_spot():
    for k in HALLS:
        h = HALLS[k]
        eye = (h["cx"], h["y0"] + 450.0)
        for p in hall_pieces(k):
            rect = tp.footprint(p)
            for x in (h["cx"] - 1106, h["cx"] - 553, h["cx"] + 553, h["cx"] + 1106):             # the door wall's outer corners and panel edges
                assert segment_gap(eye, (x, h["door_face"]), rect) > 0, f"{p['label']} hides the door wall at x {x:.0f}"


def test_connector_pieces_keep_the_corridors_middle_and_the_speed_plates_clear():
    by = {s["id"]: s for s in CONN}
    for p in SET:
        if not p["strip"].startswith("C"):
            continue
        s = by[p["strip"]]
        hr = math.radians(s["h"])
        dx, dy = p["x"] - s["o"][0], p["y"] - s["o"][1]
        along, lat = dx * math.cos(hr) + dy * math.sin(hr), dx * math.sin(hr) - dy * math.cos(hr)
        across, half_along = tp.across_along(p["mesh"], p["scale"], p["yaw"] - s["h"])
        assert abs(lat) - across >= 200 - 0.5 and abs(lat) + across <= 500, p["label"]
        assert half_along <= along <= s["s1"] + tp.JOINT - half_along + 0.5, p["label"]
        for a, b, _ in s["keep"]:                                                            # the plates (+ margin)
            assert along + half_along <= a + 0.5 or along - half_along >= b - 0.5, p["label"]


def test_pieces_stand_on_their_floor_and_none_hangs_in_the_air_or_sinks_deep():
    for p in SET:
        bottom = p["z"] + tp.MESH[p["mesh"]][0][2] * p["scale"]
        assert bottom == pytest.approx(p["floor"] - tp.SINK, abs=0.01), p["label"]
        assert p["scale"] > 0.5, p["label"]


def test_tall_pieces_keep_out_from_under_the_wall_torches():
    for p in SET:
        h = tp.size(p["mesh"])[2] * p["scale"]
        if p["strip"].startswith("S") and h > tp.TORCH_CLEAR:
            s = p["s"]
            assert all(abs(s - t) >= p["along"] * 0.6 + 49.0 for t in tp.TORCH_S), p["label"]


def test_station_1_keeps_volts_stretch_and_every_hall_keeps_its_pads_signs_and_chalkboard_clear():
    volt = mascot.start_spec(COURSE)
    for p in hall_pieces(1):
        x0, x1, y0, y1 = tp.footprint(p)
        arm = ARM_HALF * volt["scale"]
        assert not overlap((x0, x1, y0, y1), (volt["x"] - arm, volt["x"] + arm, volt["y"] - arm, volt["y"] + arm), 200), p["label"]
    for k, h in HALLS.items():
        for p in hall_pieces(k):
            assert tp.footprint(p)[2] >= h["y0"] + 1000, p["label"]        # the pickup rows (s 480-780), the STATION sign and the chalkboard (242-958)


def test_nothing_stands_behind_volt_in_the_spawn_frame():
    """From the start camera Volt is ~26 degrees to the right; no station 1 piece may fall within 12 degrees of him, or he is drawn against a
    pillar (seen in the first editor frame)."""
    h = HALLS[1]
    cam = (h["cx"], h["y0"] + 450 - EYE_BACK)
    volt = mascot.start_spec(COURSE)
    vb = math.degrees(math.atan2(volt["x"] - cam[0], volt["y"] - cam[1]))
    for p in hall_pieces(1):
        x0, x1, y0, y1 = tp.footprint(p)
        bearings = [math.degrees(math.atan2(x - cam[0], y - cam[1])) for x in (x0, x1) for y in (y0, y1)]
        assert max(bearings) < vb - 12 or min(bearings) > vb + 12, f"{p['label']} {min(bearings):.0f}..{max(bearings):.0f} vs Volt {vb:.0f}"


def test_rune_stones_face_the_corridor():
    for p in SET:
        if p["mesh"] != "rune_stone":
            continue
        s = {x["id"]: x for x in STRIPS + CONN}[p["strip"]]
        face = math.radians(p["yaw"] + tp.FRONT0["rune_stone"])                              # the world heading its front faces
        hr = math.radians(s["h"])
        left = (math.sin(hr), -math.cos(hr))                                                  # the player's left along this strip
        lat = (p["x"] - s["o"][0]) * left[0] + (p["y"] - s["o"][1]) * left[1]
        inward = (-left[0], -left[1]) if lat > 0 else left                                    # from its wall toward the centre line
        assert math.cos(face) * inward[0] + math.sin(face) * inward[1] > math.cos(math.radians(30)), p["label"]


def test_the_set_is_deterministic_and_the_seed_matters(monkeypatch):
    again = tp.set_pieces(COURSE, TIERS)
    assert again == SET
    monkeypatch.setattr(tp, "SEED", tp.SEED + 1)
    assert tp.set_pieces(COURSE, TIERS) != SET


# ---------------------------------------------------------------- the disproofs
def test_disproof_a_piece_on_the_running_line_is_caught():
    p = dict(next(q for q in SET if q["strip"] == "S02"))
    h = HALLS[2]
    assert tp.conflicts(COURSE, [p], TIERS) == []
    p["x"] = h["cx"]                                                  # dead centre of the hall
    bad = tp.conflicts(COURSE, [p], TIERS)
    assert any("running lane" in b for b in bad), bad
    x0, x1, y0, y1 = tp.footprint(p)
    eye = (h["cx"], h["y0"] + 450.0)
    assert segment_gap(eye, (h["cx"] + 276.5, h["door_face"]), (x0, x1, y0, y1)) < 100 or segment_gap(eye, (h["cx"] - 276.5, h["door_face"]), (x0, x1, y0, y1)) < 100


def test_disproof_a_piece_over_an_obstacle_or_past_the_door_zone_is_caught():
    p = dict(next(q for q in SET if q["strip"] == "S02"))
    hurdle = next(o for o in tp.obstacles(COURSE, 2))
    p["y"] = (hurdle[1] + hurdle[2]) / 2
    assert any("obstacle" in b or "sight" in b or "door" in b for b in tp.conflicts(COURSE, [p], TIERS)), tp.conflicts(COURSE, [p], TIERS)
    q = dict(next(q for q in SET if q["strip"] == "S02"))
    q["y"] = HALLS[2]["door_y"] - 300
    assert tp.conflicts(COURSE, [q], TIERS)
    r = dict(next(q for q in SET if q["strip"] == "S02"))
    r["z"] += 80
    assert any("floor" in b for b in tp.conflicts(COURSE, [r], TIERS))


def intrusions(specs):
    """How many hall pieces reach into the central 12 m or onto a path from the arrival spot to a door."""
    hit = 0
    for p in specs:
        if not p["strip"].startswith("S"):
            continue
        h = HALLS[int(p["strip"][1:])]
        rect = tp.footprint(p)
        eye = (h["cx"], h["y0"] + 450.0)
        if (rect[0] < h["cx"] + 600 and rect[1] > h["cx"] - 600) or any(segment_gap(eye, (h["cx"] + dx, h["door_face"]), rect) < 100 for dx in c.door_centres(4)):
            hit += 1
    return hit


def test_disproof_the_lane_is_what_keeps_big_pieces_off_the_running_line(monkeypatch):
    """Blow every scale range up 1.6x: with the lane the fit cuts each piece back to the wall band and nothing intrudes; with the lane
    taken away the same pieces reach onto the running line and the independent check goes red."""
    monkeypatch.setattr(tp, "SCALE", {k: (lo * 1.6, hi * 1.6) for k, (lo, hi) in tp.SCALE.items()})
    assert intrusions(tp.set_pieces(COURSE, TIERS)) == 0
    monkeypatch.setattr(tp, "LANE_HALL", 0.0)
    monkeypatch.setattr(tp, "sight_cap", lambda strip, inner: 1e9)             # the door-sight rule would stop them too: take it away as well
    assert intrusions(tp.set_pieces(COURSE, TIERS)) > 0


# ---------------------------------------------------------------- the gate
# THE DOORS ARE THE GAME: from the spawn camera all four doors, their colours and their lintel letters are clear, and nothing stands on a path
# from the spawn to a door. The first two placements (a gate across the hall, 5.5 then 4.4) failed this in play (2026-10-13); they are kept
# here as the disproof.
def door_rectangle():
    """The door wall as the spawn camera sees it, worked out here (not read from the builder): (half bearing, low, high elevation) degrees."""
    h = HALLS[1]
    cam_y, cam_z = h["y0"] + 450.0 - EYE_BACK, h["z"] + CAMERA_Z
    d = h["door_face"] - cam_y
    return (math.degrees(math.atan2(h["half"], d)), math.degrees(math.atan2(h["z"] - cam_z, d)),
            math.degrees(math.atan2(h["z"] + h["wall"] - cam_z, d)))


def cells_on_the_doors(spec, margin=1.0):
    """How many of the gate's occupied cells project onto the door wall's rectangle from the spawn camera (own implementation: cell corners
    through a pinhole at the camera)."""
    h = HALLS[1]
    cx, cy, cz = h["cx"], h["y0"] + 450.0 - EYE_BACK, h["z"] + CAMERA_Z
    b0, e0, e1 = door_rectangle()
    t = math.radians(spec["yaw"])
    n = 0
    for lx, ly, lz in tp.gate_cells():
        wx = spec["x"] + (lx * math.cos(t) - ly * math.sin(t)) * spec["scale"]
        wy = spec["y"] + (lx * math.sin(t) + ly * math.cos(t)) * spec["scale"]
        wz = spec["z"] + lz * spec["scale"]
        half = 5.0 * spec["scale"] * 1.5                           # a cell's box, generously (its turned diagonal)
        corners = [(wx + sx * half, wy + sy * half, wz + sz * 5.0 * spec["scale"]) for sx in (-1, 1) for sy in (-1, 1) for sz in (-1, 1)]
        corners = [p for p in corners if p[1] > cy + 20]
        if not corners:
            continue
        bear = [math.degrees(math.atan2(p[0] - cx, p[1] - cy)) for p in corners]
        elev = [math.degrees(math.atan2(p[2] - cz, p[1] - cy)) for p in corners]
        if max(bear) > -b0 - margin and min(bear) < b0 + margin and max(elev) > e0 - margin and min(elev) < e1 + margin:
            n += 1
    return n


def cells_near_the_paths(spec, clear=100.0):
    """The door letters whose straight path from the spawn passes within `clear` cm of a gate cell low enough to walk into."""
    h = HALLS[1]
    t = math.radians(spec["yaw"])
    hit = set()
    for lx, ly, lz in tp.gate_cells():
        wz = spec["z"] + lz * spec["scale"]
        if wz - 5.0 * spec["scale"] > h["z"] + 200:
            continue
        wx = spec["x"] + (lx * math.cos(t) - ly * math.sin(t)) * spec["scale"]
        wy = spec["y"] + (lx * math.sin(t) + ly * math.cos(t)) * spec["scale"]
        for letter, dx in zip("ABCD", c.door_centres(4)):
            ax, ay, bx, by = h["cx"], h["y0"] + 450.0, h["cx"] + dx, h["door_face"]
            u = max(0.0, min(1.0, ((wx - ax) * (bx - ax) + (wy - ay) * (by - ay)) / ((bx - ax) ** 2 + (by - ay) ** 2)))
            if math.hypot(wx - (ax + u * (bx - ax)), wy - (ay + u * (by - ay))) < clear + 5.0 * spec["scale"]:
                hit.add(letter)
    return sorted(hit)


def test_the_gate_hides_none_of_the_four_doors_from_the_spawn_camera():
    b0, e0, e1 = door_rectangle()
    assert 20 < b0 < 22 and -5.5 < e0 < -4.5 and 6.5 < e1 < 7.2                        # the door wall: +-21 degrees wide, floor -5 to lintel top +6.9
    assert cells_on_the_doors(GATE) == 0
    assert tp.gate_blockers(COURSE, GATE) == []


def test_nothing_of_the_gate_stands_on_the_path_from_the_spawn_to_any_door():
    assert cells_near_the_paths(GATE) == []


def test_the_gate_cells_are_the_meshs_own():
    """GATE_VOXELS were read from art/titanpeak/gate/raw/gate.glb: every vertex of it lies in an occupied cell, and the cells stay inside its bounds."""
    cells = {(round(x), round(y), round(z)) for x, y, z in tp.gate_cells()}
    assert 500 < len(cells) < 800 and len(cells) == len(tp.gate_cells())
    lo, hi = tp.MESH["gate"]
    for x, y, z in tp.gate_cells():
        assert lo[0] - 10 <= x <= hi[0] + 10 and lo[1] - 10 <= y <= hi[1] + 10 and lo[2] - 10 <= z <= hi[2] + 10
    path = ROOT / "art" / "titanpeak" / "gate" / "raw" / "gate.glb"
    if not path.exists():
        pytest.skip("the gate GLB is not in this checkout")
    import struct
    data = path.read_bytes()
    off, meta, binary = 12, None, None
    while off < len(data):
        n, kind = struct.unpack("<I4s", data[off:off + 8])
        if kind == b"JSON":
            meta = json.loads(data[off + 8:off + 8 + n])
        elif kind.startswith(b"BIN"):
            binary = data[off + 8:off + 8 + n]
        off += 8 + n
    acc = meta["accessors"][meta["meshes"][0]["primitives"][0]["attributes"]["POSITION"]]
    view = meta["bufferViews"][acc["bufferView"]]
    base = view.get("byteOffset", 0) + acc.get("byteOffset", 0)
    stride = view.get("byteStride", 12)
    for i in range(acc["count"]):
        gx, gy, gz = struct.unpack_from("<3f", binary, base + i * stride)
        key = (math.floor((gz * 100 + 100) / 10), math.floor((gx * 100 + 100) / 10), math.floor((gy * 100 + 100) / 10))     # UE x = glTF z, y = glTF x, z = glTF y
        assert (key[0] * 10 - 95, key[1] * 10 - 95, key[2] * 10 - 95) in cells, i


def test_disproof_the_first_two_gate_placements_fail_the_door_rule():
    """The gate across the hall, 5.5 times then 4.4 times the mesh, stood in front of doors B and C and on every path: both rules go red on them."""
    h = HALLS[1]
    for scale, ahead in ((5.5, 1850.0), (4.4, 1800.0)):
        old = {"x": h["cx"], "y": h["y0"] + ahead, "z": tp.rest_z("gate", scale, h["z"]), "yaw": -90.0, "scale": scale}
        assert cells_on_the_doors(old) > 100, scale
        assert cells_near_the_paths(old) == ["A", "B", "C", "D"], scale
        bad = tp.gate_blockers(COURSE, old)
        assert any("project onto the door wall" in b for b in bad) and sum("path from the spawn" in b for b in bad) == 4, bad
    moved = dict(GATE, x=h["cx"])                                              # the new gate dragged onto the centre line
    assert cells_on_the_doors(moved) > 0 and tp.gate_blockers(COURSE, moved)
    bigger = tp.gate_spec(COURSE, scale=4.0)                                    # and simply too big for its spot
    assert cells_on_the_doors(bigger) > 0 and tp.gate_blockers(COURSE, bigger)


def test_the_gate_stands_against_the_left_wall_clear_of_the_sign_volt_and_the_set_pieces():
    h = HALLS[1]
    rect = (GATE["x"] - GATE["hx"], GATE["x"] + GATE["hx"], GATE["y"] - GATE["hy"], GATE["y"] + GATE["hy"])
    assert rect[1] <= h["left"] - 20 and rect[0] > h["cx"] + 400                    # on the left (+X) wall's side, 4 m off the centre line at the least
    assert rect[2] >= h["y0"] + 940                                                 # past the STATION sign (y0 + 242..958)
    assert rect[3] <= h["door_y"] - 1000                                            # nowhere near the door wall
    volt = mascot.start_spec(COURSE)
    arm = ARM_HALF * volt["scale"]
    assert not overlap(rect, (volt["x"] - arm, volt["x"] + arm, volt["y"] - arm, volt["y"] + arm), 300)       # Volt is on the right wall
    for p in hall_pieces(1):
        assert not overlap(rect, tp.footprint(p), 100), p["label"]
    assert GATE["height"] < h["wall"] - 150                                         # camp dressing, lower than the walls: it hides no sky behind the doors


def test_the_base_camp_sign_reads_from_the_spawn_camera_and_the_banner_lies_on_it():
    h = HALLS[1]
    cam = (h["cx"], h["y0"] + 450.0 - EYE_BACK, h["z"] + CAMERA_Z)
    bd, b = GATE["board"], GATE_BANNER
    bearing = math.degrees(math.atan2(bd["x"] - cam[0], bd["y"] - cam[1]))             # + is the player's left
    elevation = math.degrees(math.atan2(bd["z"] - cam[2], math.hypot(bd["x"] - cam[0], bd["y"] - cam[1])))
    assert 22 <= bearing <= 38, bearing                                              # inside the 80 degree frame, off the doors' 21 degrees
    to_camera = math.degrees(math.atan2(cam[1] - bd["y"], cam[0] - bd["x"]))
    assert abs((to_camera - GATE["front"] + 180) % 360 - 180) <= 45                    # the sign's front points within 45 degrees of the camera
    px = 960 - 960 * math.tan(math.radians(bearing)) / math.tan(math.radians(40))      # 1080p, 80 degree horizontal frame, horizon at 500 px
    py = 500 - 21.3 * elevation
    assert px > 100 and not (px < 335 and py < 380)                                    # not under the HUD boxes at the left (x < 335, y < 378)
    assert not (375 < px < 1545 and py < 345)                                          # nor under the question panel
    assert b["key"] == "base_camp" and b["facing"] == pytest.approx(GATE["front"])
    assert (b["x"], b["y"]) == pytest.approx((bd["x"], bd["y"]), abs=1) and b["z"] < bd["z"] < b["z"] + b["h"]
    assert b["w"] / b["h"] == pytest.approx(tp.ASPECT["base_camp"], abs=0.01)
    assert abs(b["w"]) <= 1.1 * bd["w"] + 10                                         # about as wide as the board


# ---------------------------------------------------------------- the podium
def ray_hits_box(a, b, lo, hi):
    """Slab test: does the segment a-b pass through the box (lo, hi)?"""
    t0, t1 = 0.0, 1.0
    for i in range(3):
        d = b[i] - a[i]
        if abs(d) < 1e-9:
            if a[i] < lo[i] or a[i] > hi[i]:
                return False
            continue
        ta, tb = (lo[i] - a[i]) / d, (hi[i] - a[i]) / d
        t0, t1 = max(t0, min(ta, tb)), min(t1, max(ta, tb))
        if t0 > t1:
            return False
    return True


def lectern_rects(end, cx):
    out = []
    for side in (1, -1):
        x, y = cx + side * fin.PODIUM_SPREAD, end - fin.PODIUM_BACK
        out.append((x - 60, x + 60, y - 60, y + 60))                           # a 1.5-scale lectern is ~1.2 m on a side
    return out


def test_the_podium_stands_on_the_new_skill_side_inside_the_hall_facing_the_finisher():
    hall = tp.special_hall(COURSE, "FNM_Finish")
    assert PODIUM["x"] < hall["cx"] and PODIUM["x"] - PODIUM["hx"] > hall["right"] + 100
    assert PODIUM["x"] + PODIUM["hx"] < hall["cx"] - fin.PODIUM_SPREAD                # left of the NEW SKILL lectern
    stand = mascot.podium_stand(COURSE)
    want = math.degrees(math.atan2(stand[1] - PODIUM["y"], stand[0] - PODIUM["x"]))
    assert PODIUM["yaw"] + tp.FRONT0["podium"] == pytest.approx(want, abs=1e-6)       # its front toward the finisher's spot
    assert PODIUM["top"] == pytest.approx(PODIUM["floor"] - tp.SINK + 107.3 * PODIUM["scale"], abs=2)


def test_the_podium_covers_no_lectern_label_board_volt_flower_or_the_finishers_spot():
    hall = tp.special_hall(COURSE, "FNM_Finish")
    end, cx = hall["y_end"], hall["cx"]
    rect = (PODIUM["x"] - PODIUM["hx"], PODIUM["x"] + PODIUM["hx"], PODIUM["y"] - PODIUM["hy"], PODIUM["y"] + PODIUM["hy"])
    for lec in lectern_rects(end, cx):
        assert not overlap(rect, lec, 100), "a lectern"
    for side in (1, -1):                                                              # the labels over the lecterns' buttons
        label = (cx + side * fin.PODIUM_SPREAD - 107, cx + side * fin.PODIUM_SPREAD + 107, end - 645 - 40, end - 645 + 40)
        assert not overlap(rect, label, 60), "a label"
    assert rect[3] < end - 40 - 100                                                    # the all-time board's text plane stands 40 cm off the end wall
    volt = mascot.podium_spec(COURSE)
    arm = ARM_HALF * volt["scale"]
    assert not overlap(rect, (volt["x"] - arm, volt["x"] + arm, volt["y"] - arm, volt["y"] + arm), 300)
    for x in (hall["left"] - 120, hall["right"] + 120):                                # the flower pots at the end of the hall (build_decor FNM_DF_FlowersA*)
        assert not overlap(rect, (x - 50, x + 50, end - 500 - 50, end - 500 + 50), 60), "a flower pot"
    stand = mascot.podium_stand(COURSE)
    assert rect_gap(*stand, rect) > 250                                                # the finisher is not stood in it
    cam_xy = (stand[0], stand[1] - WIDE_BACK)
    box_lo = (rect[0], rect[2], PODIUM["floor"])
    box_hi = (rect[1], rect[3], PODIUM["top"] + 130)                                    # the podium plus the trophy standing on its top step
    for cam_z in (200.0, 400.0):                                                        # the orbit camera's height is not known: two guesses
        cam = (*cam_xy, PODIUM["floor"] + cam_z)
        for x in (cx - 450, cx, cx + 450):                                              # the board's text columns, rows from z 230 to 700 (build_finish)
            for z in (230.0, 700.0):
                assert not ray_hits_box(cam, (x, end - 40, PODIUM["floor"] + z), box_lo, box_hi), f"hides the board at x {x - cx:.0f}, z {z:.0f}"
        for button in lectern_rects(end, cx):
            tgt = ((button[0] + button[1]) / 2, button[2] - 20, PODIUM["floor"] + 177.0)
            assert not ray_hits_box(cam, tgt, box_lo, box_hi), "hides a lectern button"
    for button in lectern_rects(end, cx):                                              # nor on the path from the finisher to a button
        bx, by = (button[0] + button[1]) / 2, (button[2] + button[3]) / 2
        assert segment_gap(stand, (bx, by - 60), rect) > 100


def test_the_wide_camera_sees_the_podium():
    """The orbit camera 900 cm behind the finisher's spot sees both lecterns and the board; the podium stands inside the same frame."""
    stand = mascot.podium_stand(COURSE)
    cam = (stand[0], stand[1] - WIDE_BACK)
    bearing = math.degrees(math.atan2(PODIUM["x"] - cam[0], PODIUM["y"] - cam[1]))
    assert abs(bearing) < 38, bearing                                                  # inside an 80 degree horizontal frame (+-40), with the edge to spare


def test_the_trophy_can_stand_on_the_podiums_top_step_and_the_default_keeps_its_plinth():
    """tools/build_landmarks.py --on-podium: P's own trophy spot (and P's tests) are untouched unless the podium is asked for."""
    assert lm.trophy_spec(COURSE)["plinth"] is not None
    t = lm.trophy_spec(COURSE, podium=PODIUM)
    assert t["plinth"] is None and t["label"] == "FNM_Landmark_Trophy" and t["faces"] == PODIUM["faces"]
    assert (t["x"], t["y"]) == (PODIUM["x"], PODIUM["y"])
    assert t["z"] + lm.TROPHY_MESH["min"][2] * t["scale"] == pytest.approx(PODIUM["top"])      # the cup's base on the top step
    assert t["yaw"] == pytest.approx(PODIUM["yaw"], abs=1e-6)                                    # both fronts toward the finisher's spot
    depth = (lm.TROPHY_MESH["max"][0] - lm.TROPHY_MESH["min"][0]) * t["scale"]
    width = (lm.TROPHY_MESH["max"][1] - lm.TROPHY_MESH["min"][1]) * t["scale"]
    assert depth <= tp.PODIUM_STEP[0] * PODIUM["scale"] - 10 and width <= tp.PODIUM_STEP[1] * PODIUM["scale"] - 10   # the cup fits on the slab
    top_of_cup = t["z"] + lm.TROPHY_MESH["max"][2] * t["scale"]
    hoc = BANNERS[-1]
    assert hoc["z"] >= top_of_cup + 50                                                           # HALL OF CHAMPIONS floats clear above it


def test_the_cup_on_the_podium_still_covers_no_lectern_or_board_text():
    stand = mascot.podium_stand(COURSE)
    cam = (stand[0], stand[1] - WIDE_BACK, PODIUM["floor"] + 300.0)
    t = lm.trophy_spec(COURSE, podium=PODIUM)
    cup = lm.trophy_rects(t)["cup"]
    lo = (cup[0], cup[2], t["z"] + lm.TROPHY_MESH["min"][2] * t["scale"])
    hi = (cup[1], cup[3], t["z"] + lm.TROPHY_MESH["max"][2] * t["scale"])
    hall = tp.special_hall(COURSE, "FNM_Finish")
    for x in (hall["cx"] - 450, hall["cx"], hall["cx"] + 450):
        for z in (230.0, 700.0):
            assert not ray_hits_box(cam, (x, hall["y_end"] - 40, PODIUM["floor"] + z), lo, hi)
    assert not ray_hits_box(cam, (hall["cx"] - fin.PODIUM_SPREAD, hall["y_end"] - 620, PODIUM["floor"] + 177.0), lo, hi)


# ---------------------------------------------------------------- the banners
def test_six_floating_banners_one_per_place_and_the_gates_own_base_camp():
    assert [b["key"] for b in BANNERS] == ["waterfall_gorge", "frost_ridge", "obsidian_descent", "magma_core", "titans_forge", "hall_of_champions"]
    assert GATE_BANNER["key"] == "base_camp" and "base_camp" not in {b["key"] for b in BANNERS}
    assert set(tp.ASPECT) == {b["key"] for b in BANNERS} | {"base_camp"}


def test_each_tier_banner_hangs_over_the_entrance_of_that_tiers_first_station():
    for b, tier in zip(BANNERS[:4], (2, 3, 4, 5)):
        k = tp.first_station(tier, 10, TIERS)
        h = HALLS[k]
        assert tp.tier_of(k, 10, TIERS) == tier and tp.tier_of(k - 1, 10, TIERS) == tier - 1
        assert b["label"].endswith(f"S{k:02d}_{b['key']}")
        assert b["x"] == pytest.approx(h["cx"]) and b["y"] == pytest.approx(h["y0"])         # over the hall's first edge, on its centre line
        assert b["z"] - h["z"] >= h["wall"] - 40                                              # bottom edge at the wall tops: nobody reaches it
        assert b["yaw"] == pytest.approx(0)                                                   # readable from the connector (-Y)
        assert b["w"] < 2 * h["half"] - 600                                                   # inside the hall's width with room to spare


def test_the_arena_banner_hangs_over_the_arena_entrance_and_the_podium_one_over_the_podium():
    arena = tp.special_hall(COURSE, "FNM_Arena")
    forge = next(b for b in BANNERS if b["key"] == "titans_forge")
    assert forge["x"] == pytest.approx(arena["cx"]) and forge["y"] == pytest.approx(arena["y0"])
    assert forge["z"] - arena["z"] >= arena["wall"] - 40
    hoc = BANNERS[-1]
    assert hoc["x"] == pytest.approx(PODIUM["x"]) and hoc["y"] == pytest.approx(PODIUM["y"])
    assert hoc["z"] > PODIUM["top"] + 100                                                     # above the trophy that stands on the top step
    assert hoc["yaw"] + tp.QUAD_FRONT0 == pytest.approx(math.degrees(math.atan2(PODIUM["faces"][1] - PODIUM["y"], PODIUM["faces"][0] - PODIUM["x"])))


def test_banner_sizes_follow_the_arts_true_aspect():
    for b in BANNERS + [GATE_BANNER]:
        assert b["w"] / b["h"] == pytest.approx(tp.ASPECT[b["key"]], abs=0.01)
        assert b["scale"] * tp.QUAD_W == pytest.approx(b["w"])
    # the art's own crop (alpha box) gives these aspects: a re-render of a banner PNG that changes its shape must change ASPECT
    pil = pytest.importorskip("PIL.Image")
    for key, aspect in tp.ASPECT.items():
        path = ROOT / "art" / "titanpeak" / "banners" / f"{key}_raw.png"
        if not path.exists():
            pytest.skip("banner art not in this checkout")
        im = pil.open(path).convert("RGBA")
        box = im.getchannel("A").point(lambda v: 0 if v < 16 else v).getbbox()
        assert (box[2] - box[0]) / (box[3] - box[1]) == pytest.approx(aspect, abs=0.01), key


def test_no_banner_hangs_where_a_player_can_reach_it():
    """A walking player is 180 cm tall and a jump adds ~130, so 310; every banner's bottom edge is far above that, and a banner never
    stands on the ground. (The imported quads have their collision removed as well.)"""
    floors = [HALLS[k]["z"] for k in (3, 5, 7, 9)] + [tp.special_hall(COURSE, "FNM_Arena")["z"], tp.special_hall(COURSE, "FNM_Finish")["z"]]
    for b, floor in zip(BANNERS, floors):
        assert b["z"] - floor >= 400, b["label"]
    assert tp.BANNER_Z >= 500 and tp.PODIUM_BANNER_Z >= 400


def test_expected_bounds_follow_the_footprint_the_height_and_the_banner_sheet():
    p = SET[0]
    x0, x1, y0, y1, z0, z1 = tp.expected_bounds(p)
    assert (x0, x1, y0, y1) == tp.footprint(p)
    assert z0 == pytest.approx(p["floor"] - tp.SINK) and z1 - z0 == pytest.approx(tp.size(p["mesh"])[2] * p["scale"])
    b = BANNERS[-1]                                                                       # turned 55 degrees: its sheet's box is thin in one axis
    bx0, bx1, by0, by1, bz0, bz1 = tp.expected_bounds(b)
    assert (bz0, bz1) == (b["z"], b["z"] + b["h"])
    assert math.hypot(bx1 - bx0, by1 - by0) == pytest.approx(b["w"])


# ---------------------------------------------------------------- the builder, against a fake editor
class Editor:
    """A fake UEFN: the course, the imported art, and a scene that records what the builder places and tags."""

    def __init__(self):
        self.actors, self.log, self.n = {}, [], 0
        self.shapes = {}          # mesh asset path -> collision shapes it carries (the imports came with one convex hull each)
        self.keeps_collision = False

    def __call__(self, toolset, tool, args=None, **kw):
        args = args or {}
        self.log.append((tool, args))
        if tool == "find_actors":
            if args["tag"] == c.TAG:
                return {"returnValue": [{"label": k, "bounds": v, "actorPath": f"/course/{k}"} for k, v in COURSE.items()]}
            return {"returnValue": [{"label": a["label"], "bounds": {}, "actorPath": p} for p, a in self.actors.items() if args["tag"] in a["tags"]]}
        if tool == "find_assets":
            return {"returnValue": [f"/{PROJECT}/{tp.ART}/Sub/{args['name']}.{args['name']}"]}
        if tool == "get_properties":
            inst = args["instance"]["refPath"]
            if args["properties"] == ["bodySetup"]:
                return {"returnValue": json.dumps({"bodySetup": {"refPath": inst + ":BodySetup_0"}})}
            if args["properties"] == ["aggGeom"]:
                n = self.shapes.setdefault(inst.split(":")[0], 1)
                return {"returnValue": json.dumps({"aggGeom": {"convexElems": [{}] * n, "boxElems": [], "sphereElems": []}})}
        if tool == "remove_collisions":
            if not self.keeps_collision:
                self.shapes[args["mesh"]["refPath"]] = 0
            return {"returnValue": True}
        if tool == "add_to_scene_from_asset":
            self.n += 1
            path = f"/Level/Actor_{self.n}"
            self.actors[path] = {"label": args["name"], "tags": [], "xform": args["xform"], "asset": args["asset_path"], "props": {}}
            return {"returnValue": {"refPath": path}}
        if tool == "add_tag":
            self.actors[args["actor"]["refPath"]]["tags"].append(args["tag"])
        elif tool == "set_label":
            self.actors[args["actor"]["refPath"]]["label"] = args["label"]
        elif tool == "remove_from_scene":
            self.actors.pop(args["actor"]["refPath"])
        elif tool == "set_properties":
            self.actors[args["instance"]["refPath"]]["props"].update(__import__("json").loads(args["values"]))
        return {"returnValue": True}


@pytest.fixture
def editor(monkeypatch):
    ed = Editor()
    monkeypatch.setattr(tp.u, "call", ed)
    monkeypatch.setattr(tp, "project", lambda: PROJECT)
    return ed


def test_a_full_build_places_every_part_tagged_labelled_and_under_the_budget(editor):
    tp.build(list(tp.PARTS))
    assert len(editor.actors) == len(SET) + 2 + 1 + len(BANNERS) <= 60
    for path, a in editor.actors.items():
        assert tp.TAG in a["tags"], a["label"]
        assert sum(t.startswith(tp.TAG + "_") for t in a["tags"]) == 1, a["label"]
        assert a["label"].startswith("FNM_TP_"), a["label"]
    assert {t for a in editor.actors.values() for t in a["tags"]} == {tp.TAG, *(tp.part_tag(p) for p in tp.PARTS)}
    assert len({a["label"] for a in editor.actors.values()}) == len(editor.actors)
    assert any(t == "save_assets" for t, _ in editor.log)


def test_a_rebuild_replaces_its_actors_and_never_stacks_them(editor):
    tp.build(["set"])
    first = {a["label"]: (a["xform"]["location"]["x"], a["xform"]["location"]["y"]) for a in editor.actors.values()}
    tp.build(["set"])
    again = {a["label"]: (a["xform"]["location"]["x"], a["xform"]["location"]["y"]) for a in editor.actors.values()}
    assert again == first and len(editor.actors) == len(SET)


def test_one_part_rebuilds_alone_and_remove_takes_only_what_it_is_told(editor):
    tp.build(list(tp.PARTS))
    ids = {a["label"] for a in editor.actors.values()}
    gate_before = {p for p, a in editor.actors.items() if tp.part_tag("gate") in a["tags"]}
    tp.build(["podium"])
    assert {a["label"] for a in editor.actors.values()} == ids                              # same set of labels after a podium-only run
    assert gate_before <= set(editor.actors)                                                # the gate's actors were never touched
    assert tp.remove("banners") == len(BANNERS)
    assert len(editor.actors) == len(ids) - len(BANNERS)
    assert tp.remove() == len(ids) - len(BANNERS) and editor.actors == {}


def test_the_assets_come_from_t1s_folder_by_name(editor):
    tp.build(["gate", "banners", "set"])
    assets = {a["asset"].rsplit("/", 1)[-1].split(".")[0] for a in editor.actors.values()}
    assert assets <= {tp.asset_name(m) for m in tp.MESH} | {f"SM_fnm_tp_banner_{k}" for k in tp.ASPECT}
    assert {"SM_fnm_tp_gate", "SM_fnm_tp_banner_base_camp", "SM_fnm_tp_banner_titans_forge", "SM_fnm_tp_rune_stone"} <= assets
    assert all(a["asset"].startswith(f"/{PROJECT}/{tp.ART}/") for a in editor.actors.values())


def test_placements_carry_each_specs_transform(editor):
    tp.build(["gate", "podium"])
    gate = next(a for a in editor.actors.values() if a["label"] == "FNM_TP_Gate")
    assert gate["xform"]["scale"] == {"x": tp.GATE_SCALE, "y": tp.GATE_SCALE, "z": tp.GATE_SCALE}
    assert gate["xform"]["rotation"]["yaw"] == pytest.approx(GATE["yaw"])
    assert gate["xform"]["location"]["z"] == pytest.approx(GATE["z"])
    assert gate["props"].get("bCanBeDamaged") is False


def test_every_mesh_a_part_places_loses_its_collision_shapes_and_the_build_checks_it(editor):
    """The imports carry one convex hull round the whole bounding box: the gate's would wall off its own opening."""
    tp.build(["gate", "podium", "set"])
    placed = {a["asset"] for a in editor.actors.values() if "banner" not in a["asset"]}
    assert len(placed) == 2 + len(tp.SET_MESHES) and all(editor.shapes[m] == 0 for m in placed)
    assert any(t == "remove_collisions" for t, _ in editor.log)


def test_disproof_collision_that_survives_remove_collisions_stops_the_build(editor):
    editor.keeps_collision = True
    with pytest.raises(SystemExit) as e:
        tp.build(["gate"])
    assert "collision shapes survived" in str(e.value)


def test_a_missing_import_stops_the_build_with_a_pointer_to_t1(editor, monkeypatch):
    def none(toolset, tool, args=None, **kw):
        return {"returnValue": []} if tool == "find_assets" else editor(toolset, tool, args)
    monkeypatch.setattr(tp.u, "call", none)
    with pytest.raises(SystemExit) as e:
        tp.build(["gate"])
    assert "import_titanpeak" in str(e.value)
