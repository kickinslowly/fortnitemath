"""The landmarks (tools/import_landmarks.py, tools/build_landmarks.py): placement maths, device props and the editor call
order, with no UEFN. The fixture is the live course's bounds (read 2026-10-13 from the editor): station 1's floor, walls and
lintel, the arena, and the finish hall, so the checks run on the numbers the builder sees."""
import math
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

import build_bossmode as bm  # noqa: E402
import build_finish as f  # noqa: E402
import build_landmarks as lm  # noqa: E402
import build_mascot as mascot  # noqa: E402
import import_landmarks as il  # noqa: E402

PROJECT = "c498eed2-96c5-4757-91a1-edb374b16d67"
WIDE_BACK = 900.0           # the orbit camera (fnm_penalty_cam) at the podium
END = 67181                 # the finish end wall's inner face


def bounds(x0, x1, y0, y1, z0, z1):
    return {"min": {"x": x0, "y": y0, "z": z0}, "max": {"x": x1, "y": y1, "z": z1}}


def course(finish_shift=0.0):
    fy = finish_shift
    return {
        "FNM_S01_Floor": bounds(-1146, 1146, -12000, -8235, -38, 2),
        "FNM_S01_WallL": bounds(1106, 1146, -12000, -8235, 0, 600),
        "FNM_S01_WallR": bounds(-1146, -1106, -12000, -8235, 0, 600),
        "FNM_S01_Lintel": bounds(-1106, 1106, -9025, -8975, 384, 600),
        "FNM_Arena_Floor": bounds(551, 2843, 60441, 63481, -38, 2),
        "FNM_Arena_WallL": bounds(2803, 2843, 60441, 63481, 0, 600),
        "FNM_Arena_WallR": bounds(551, 591, 60441, 63481, 0, 600),
        "FNM_Finish_Floor": bounds(551, 2843, 65681 + fy, 67221 + fy, -38, 2),
        "FNM_Finish_WallL": bounds(2803, 2843, 65681 + fy, 67181 + fy, 0, 600),
        "FNM_Finish_WallR": bounds(551, 591, 65681 + fy, 67181 + fy, 0, 600),
        "FNM_Finish_WallEnd": bounds(551, 2843, 67181 + fy, 67221 + fy, 0, 600),
    }


def bearing(frm, x, y):
    """Degrees off the +Y axis of (x, y) seen from frm (positive = toward +X, the player's left)."""
    return math.degrees(math.atan2(x - frm[0], y - frm[1]))


def span(rect, frm):
    """The bearing interval a rectangle (x0, x1, y0, y1) covers from frm."""
    x0, x1, y0, y1 = rect
    b = [bearing(frm, x, y) for x in (x0, x1) for y in (y0, y1)]
    return min(b), max(b)


# ---------------------------------------------------------------- the volcano

def test_the_peak_stands_above_the_door_wall_from_station_1s_start():
    cam = lm.eye(course())
    wall = lm.elevation(cam, *lm.wall_top(course()))
    v = lm.volcano_spec(course())
    peak = lm.peak_degrees(v, cam)
    assert 5 < wall < 9, wall                                     # the lintel top, ~7 degrees up from the camera
    assert peak == pytest.approx(lm.PEAK_DEG, abs=0.05)
    assert peak - wall >= 8, (peak, wall)                         # a clear margin, not a tip
    assert (peak - wall) / peak >= 0.5                            # over half of the cone's height is above the wall


def test_the_volcano_grows_as_the_player_climbs():
    c = course()
    v = lm.volcano_spec(c)
    at_start = lm.peak_degrees(v, lm.eye(c))
    arena_entry = (0.0, 60441 + 150.0, lm.CAMERA_Z + 2)
    assert lm.peak_degrees(v, arena_entry) > at_start + 3


def test_the_volcano_is_one_and_a_half_to_two_and_a_half_km_past_the_arena():
    v = lm.volcano_spec(course())
    past_arena = (v["y"] - 63481) / 100000.0
    assert 1.5 <= past_arena <= 2.5, past_arena
    assert v["y"] > lm.course_end(course())                       # beyond the finish hall too


def test_the_volcano_is_centred_between_station_1_and_the_arena_and_follows_a_longer_course():
    c = course()
    v = lm.volcano_spec(c)
    assert v["x"] == pytest.approx((0 + (551 + 2843) / 2) / 2)
    assert v["y"] > 63481 and v["z"] < 0 + v["height"]            # its origin is mid-mesh, not at the foot
    shifted = lm.volcano_spec(course(finish_shift=1000))
    assert shifted["y"] - v["y"] == pytest.approx(1000)
    assert shifted["sz"] > v["sz"]                                 # farther by 1000 cm: a hair bigger to keep the angle


def test_the_foot_is_at_the_course_floor_and_the_rim_is_the_peak():
    c = course()
    v = lm.volcano_spec(c)
    assert v["base_z"] < 2 and v["base_z"] > -0.05 * v["height"]          # sunk a little, not far
    rx, ry, rz, r = lm.rim_point(v)
    assert rz == pytest.approx(v["peak_z"])
    assert abs(rx - v["x"]) < 0.2 * r and abs(ry - v["y"]) < 0.2 * r    # the crater sits (near enough) on the axis
    assert r > 0


def test_the_scale_follows_the_angle_and_the_distance_not_a_fixed_number():
    c = course()
    near, far = lm.volcano_spec(c, past=150000), lm.volcano_spec(c, past=250000)
    assert far["sz"] > near["sz"]                                          # farther = bigger for the same angle
    cam = lm.eye(c)
    assert lm.peak_degrees(near, cam) == pytest.approx(lm.peak_degrees(far, cam))


def test_disproof_a_volcano_too_far_for_its_size_hides_behind_the_door_wall():
    c = course()
    cam = lm.eye(c)
    wall = lm.elevation(cam, *lm.wall_top(c))
    v = lm.volcano_spec(c)
    # the same mountain (same height) ten times farther away: its peak drops under the wall's top edge
    far_y = lm.eye(c)[1] + 10 * (v["peak_y"] - cam[1])
    assert lm.elevation(cam, far_y, v["peak_z"]) < wall
    # and at the chosen distance with a tenth of the height it hides too
    assert lm.elevation(cam, v["peak_y"], cam[2] + v["height"] / 10) < wall


def test_a_squat_cone_can_be_stretched_taller_without_moving_its_peak():
    c = course()
    a, b = lm.volcano_spec(c, tall=1.0), lm.volcano_spec(c, tall=1.4)
    assert b["peak_z"] == pytest.approx(a["peak_z"]) and b["sz"] == pytest.approx(a["sz"])
    assert b["sx"] == pytest.approx(a["sx"] / 1.4)


# ---------------------------------------------------------------- the titan on the rim

def test_the_titan_stands_on_the_rim_facing_the_course():
    c = course()
    v = lm.volcano_spec(c)
    t = lm.titan_spec(c, v)
    rx, ry, rz, r = lm.rim_point(v)
    assert t["y"] < ry and abs(t["x"] - rx) < 0.01 * r                     # the near (course) side of the crater
    assert math.hypot(t["x"] - rx, t["y"] - ry) <= r                       # on the rim, inside its outer edge
    assert abs(t["z"] - rz) < 0.02 * v["height"]
    assert t["yaw"] == pytest.approx(-90, abs=5)                           # the mesh faces +X: yaw -90 turns it to -Y
    assert t["scale"] == lm.TITAN_SCALE


def test_the_titan_reads_as_a_figure_from_the_start_and_does_not_tower_over_the_mountain():
    c = course()
    v = lm.volcano_spec(c)
    t = lm.titan_spec(c, v)
    cam = lm.eye(c)
    height = 300.0 * t["scale"]                                            # SK_fnm_titan is 3 m tall
    angle = math.degrees(math.atan2(height, t["y"] - cam[1]))
    assert angle >= 5.0, angle                                             # >100 px on a 1080p frame: a figure, not a speck (60x was 40 px)
    assert height <= 0.45 * v["height"]
    assert lm.PEAK_DEG + angle < 25.3                                      # the titan's head stays under the top of an 80 degree 16:9 frame


def test_the_titan_device_plays_its_idle_clip_looping_and_carries_no_verse_tag():
    p = bm.titan_clip_props(PROJECT, "idle")
    assert p["loop"] is True and p["initialState"] == "Playing"
    assert p["animation"]["refPath"].endswith("FNM_BossArt/Clip_idle/A_fnm_titan_idle.A_fnm_titan_idle")
    assert lm.ANIMATED_MESH == "/CRD_AnimatedMesh/Device_AnimatedMesh.Device_AnimatedMesh_C"
    assert "verse_tags" not in open(ROOT / "tools" / "build_landmarks.py").read().split("def place_titan")[1].split("def build")[0]


# ---------------------------------------------------------------- the trophy

def test_trophy_stands_opposite_volt_inside_the_hall_clear_of_the_walls_and_decor():
    c = course()
    t = lm.trophy_spec(c)
    r = lm.trophy_rects(t)
    cx = (2803 + 591) / 2
    volt = mascot.podium_spec(c)
    assert t["label"] == "FNM_Landmark_Trophy" and t["plinth"]["label"] == "FNM_Landmark_Plinth"
    assert t["x"] < cx and volt["x"] > cx                                  # the other side of the hall
    assert t["x"] - cx == pytest.approx(-(volt["x"] - cx))                 # mirrored
    for name, (x0, x1, y0, y1) in r.items():
        assert 591 + 150 < x0 and x1 < 2803 - 150, name                    # clear of the side walls (and their torches, to x 784)
        assert y1 < END - 100, name                                        # not in the end wall
        assert y0 > 65681 + 150, name                                      # past the entry
    # the right-hand flower pots (build_decor finish: x = wall + 120, y = end - 500; ~150 x 112 cm)
    for name, (x0, x1, y0, y1) in r.items():
        assert x0 > 711 + 75 + 60 or y1 < END - 500 - 56 - 60 or y0 > END - 500 + 56 + 60, name
    # the mesh's origin is mid-height: the cup's base (origin + min z * scale) is on the plinth's top
    assert t["z"] + lm.TROPHY_MESH["min"][2] * t["scale"] == pytest.approx(2 + lm.PLINTH[2])


def test_trophy_is_out_of_the_walking_line_between_the_stand_spot_and_the_lecterns():
    c = course()
    r = lm.trophy_rects(lm.trophy_spec(c))
    cx = (2803 + 591) / 2
    lectern_half = f.PODIUM_SPREAD + 55
    for name, (x0, x1, y0, y1) in r.items():
        assert x1 < cx - lectern_half - 100, f"{name} reaches the lecterns' lane"


def test_trophy_covers_no_label_lectern_text_row_or_volt_from_the_wide_camera():
    c = course()
    t = lm.trophy_spec(c)
    cx, sy = mascot.podium_stand(c)
    cam = (cx, sy - WIDE_BACK)
    assert t["faces"] == (cx, sy)
    cup, plinth = lm.trophy_rects(t)["cup"], lm.trophy_rects(t)["plinth"]
    lo = min(span(cup, cam)[0], span(plinth, cam)[0])
    hi = max(span(cup, cam)[1], span(plinth, cam)[1])
    assert abs(lo) < 40 and abs(hi) < 40                                   # inside Fortnite's 80 degree field
    ly = END - f.PODIUM_BACK - 45
    for side in (1, -1):
        lx = cx + side * f.PODIUM_SPREAD
        for rect in ((lx - 107, lx + 107, ly - 8, ly + 8),                 # the label (214 cm wide)
                     (lx - 55, lx + 55, END - f.PODIUM_BACK - 45, END - f.PODIUM_BACK + 45)):   # the lectern
            a, b = span(rect, cam)
            assert hi < a or lo > b, f"trophy span {lo:.1f}..{hi:.1f} covers {a:.1f}..{b:.1f}"
    text = (1304, 2090, 67080, 67142)                                      # the leaderboard rows (build_finish ROW billboards)
    a, b = span(text, cam)
    assert hi < a or lo > b, "trophy covers the all-time rows"
    vlo, vhi = span((volt["x"] - 150, volt["x"] + 150, volt["y"] - 150, volt["y"] + 150), cam) if (volt := mascot.podium_spec(c)) else (0, 0)
    assert hi < vlo or lo > vhi, "trophy covers Volt"


def test_trophy_faces_the_finishers_spot_and_follows_a_changed_hall():
    c = course()
    t = lm.trophy_spec(c)
    t2 = lm.trophy_spec(course(finish_shift=1000))
    assert t2["y"] - t["y"] == pytest.approx(1000) and t2["x"] == t["x"]
    dx, dy = t["faces"][0] - t["x"], t["faces"][1] - t["y"]
    assert math.degrees(math.atan2(dy, dx)) - lm.TROPHY_FRONT_YAW == pytest.approx(t["yaw"])


def test_trophy_stands_two_to_three_metres_tall_on_a_plain_plinth_no_taller_than_volt():
    cup_h = (lm.TROPHY_MESH["max"][2] - lm.TROPHY_MESH["min"][2]) * lm.TROPHY_SCALE
    assert 190 <= cup_h <= 260
    assert cup_h + lm.PLINTH[2] <= 320                                      # about Volt's 300 cm
    assert lm.PLINTH_COLOUR_KEY == "bm_marble"


# ---------------------------------------------------------------- the editor: importer and builder against a stub

class _Editor:
    """Records every UEFN call; answers the ones the scripts read back."""

    def __init__(self, exists=False, actors=()):
        self.calls, self._exists, self._actors, self.n = [], exists, list(actors), 0
        self.props = {}             # (instance refPath, key) -> the value last set, read back like the real editor does

    def __call__(self, toolset, tool, args=None, **_):
        args = args or {}
        self.calls.append((tool, args))
        if tool == "find_assets":
            name, folder = args.get("name", ""), args.get("folder_path", "")
            if name == "M_fnm_wall_bm_marble":
                return {"returnValue": [f"/{PROJECT}/FNM_Art/M_fnm_wall_bm_marble.M_fnm_wall_bm_marble"]}
            return {"returnValue": [f"{folder}/{name}00.{name}00"] if name else [f"{folder}/SM_x.SM_x"]}
        if tool == "exists":
            return {"returnValue": self._exists}
        if tool == "find_actors":
            return {"returnValue": self._actors}
        if tool in ("add_to_scene_from_asset", "PlaceDevice"):
            self.n += 1
            return {"returnValue": {"refPath": f"/Game/Map.Map:PersistentLevel.Actor_{self.n}"}}
        if tool == "get_property_input":
            return {"returnValue": {"output_name": "RGB", "expression": None, "input_name": ""}}
        if tool == "get_expressions":
            return {"returnValue": []}
        if tool == "add_expression":
            self.n += 1
            return {"returnValue": {"refPath": f"/m/Material_0.Material_0:{args['expression_class']['refPath'].rsplit('.', 1)[-1]}_{self.n}"}}
        if tool == "get_triangle_count":
            return {"returnValue": 1000}
        if tool == "get_bounds":
            return {"returnValue": {"min": {"x": -1, "y": -1, "z": -1}, "max": {"x": 1, "y": 1, "z": 1}, "isValid": True}}
        if tool == "set_properties":
            for k, v in json_loads(args["values"]).items():
                self.props[(args["instance"]["refPath"], k)] = v
            return {"returnValue": True}
        if tool == "get_properties" and "animation" not in args["properties"]:
            got = {k: self.props.get((args["instance"]["refPath"], k)) for k in args["properties"]}
            return {"returnValue": json_dumps(got)}
        if tool == "get_properties":
            return {"returnValue": '{"animation": {"refPath": "/x/A_fnm_titan_idle.A_fnm_titan_idle"}, "loop": true, "initialState": "Playing"}'}
        if tool == "add_component":
            return {"returnValue": {"refPath": "/Game/Map.Map:PersistentLevel.Actor_9.Comp"}}
        return {"returnValue": True}


def test_importer_imports_both_meshes_in_their_own_folders_and_sets_lod_bias_zero(monkeypatch):
    ed = _Editor()
    monkeypatch.setattr(il.u, "call", ed)
    monkeypatch.setattr(il, "make_fbx", lambda name: Path(f"C:/x/{name}_blender.fbx"))
    il.main.__globals__["sys"].argv = ["import_landmarks.py"]
    il.main()
    imports = [a for t, a in ed.calls if t == "import_file"]
    assert [a["asset_name"] for a in imports] == ["SM_fnm_volcano", "SM_fnm_trophy"]
    assert [a["folder_path"].rsplit("/", 2)[-2:] for a in imports] == [["FNM_LandmarkArt", "Volcano"], ["FNM_LandmarkArt", "Trophy"]]
    assert all(a["import_materials"] and a["import_textures"] for a in imports)
    assert all(a["source_file"].endswith("_blender.fbx") for a in imports)
    lods = [a for t, a in ed.calls if t == "set_properties" and "lODBias" in a["values"]]
    assert len(lods) == 2 and all(json_loads(a["values"]) == {"lODBias": 0} for a in lods)
    assert any(t == "save_assets" for t, _ in ed.calls)
    stripped = [a["mesh"]["refPath"] for t, a in ed.calls if t == "remove_collisions"]
    assert [p.rsplit("/", 1)[-1] for p in stripped] == ["SM_fnm_volcano.SM_fnm_volcano", "SM_fnm_trophy.SM_fnm_trophy"]


def json_loads(s):
    import json
    return json.loads(s)


def json_dumps(o):
    import json
    return json.dumps(o)


def test_importer_keeps_existing_assets_unless_forced(monkeypatch):
    ed = _Editor(exists=True)
    monkeypatch.setattr(il.u, "call", ed)
    monkeypatch.setattr(il, "make_fbx", lambda name: Path("x"))
    il.main.__globals__["sys"].argv = ["import_landmarks.py"]
    il.main()
    assert not [1 for t, _ in ed.calls if t in ("import_file", "delete")]
    assert [t for t, _ in ed.calls].count("remove_collisions") == 2          # idempotent: stripped on every run, imported or kept
    ed2 = _Editor(exists=True)
    monkeypatch.setattr(il.u, "call", ed2)
    il.main.__globals__["sys"].argv = ["import_landmarks.py", "--force"]
    il.main()
    tools = [t for t, _ in ed2.calls]
    assert tools.index("delete") < tools.index("import_file") and tools.count("import_file") == 2


def test_the_art_folder_is_not_a_verse_name_and_the_mesh_paths_match_the_importer():
    assert il.ART == "FNM_LandmarkArt" and lm.TAG == "fnm_landmarks"
    assert il.mesh_path(PROJECT, "volcano") == f"/{PROJECT}/FNM_LandmarkArt/Volcano/SM_fnm_volcano.SM_fnm_volcano"
    assert il.mesh_path(PROJECT, "trophy") == f"/{PROJECT}/FNM_LandmarkArt/Trophy/SM_fnm_trophy.SM_fnm_trophy"
    assert il.TEXTURE == {"lODBias": 0}


def test_builder_removes_its_own_actors_first_tags_every_placement_and_labels_them(monkeypatch):
    old = [{"actorPath": "/Game/Map.Map:PersistentLevel.Old_1", "label": "FNM_Landmark_Volcano"}]
    ed = _Editor(exists=True, actors=old)
    monkeypatch.setattr(lm.u, "call", ed)
    monkeypatch.setattr(lm.c, "project_mount", lambda: "/" + PROJECT)
    monkeypatch.setattr(lm.c.u, "call", ed)
    monkeypatch.setattr(lm.d, "course", course)
    monkeypatch.setattr(lm, "found", lambda tag=lm.TAG: old)
    monkeypatch.setattr(lm.il, "u", lm.u)
    lm.build()
    tools = [t for t, _ in ed.calls]
    assert tools.index("remove_from_scene") < tools.index("add_to_scene_from_asset")
    placed = [t for t in tools if t in ("add_to_scene_from_asset", "PlaceDevice")]
    assert placed.count("add_to_scene_from_asset") == 3 and placed.count("PlaceDevice") == 1    # volcano, plinth, cup; the titan
    tags = [a for t, a in ed.calls if t == "add_tag"]
    assert len(tags) == len(placed) and all(a["tag"] == "fnm_landmarks" for a in tags)
    labels = [a["label"] for t, a in ed.calls if t == "set_label"]
    assert sorted(labels) == ["FNM_Landmark_Plinth", "FNM_Landmark_Titan", "FNM_Landmark_Trophy", "FNM_Landmark_Volcano"]
    meshes = [a["asset_path"] for t, a in ed.calls if t == "add_to_scene_from_asset"]
    assert any(p.endswith("SM_fnm_volcano.SM_fnm_volcano") for p in meshes) and any(p.endswith("SM_fnm_trophy.SM_fnm_trophy") for p in meshes)


def _built(monkeypatch, far=True):
    ed = _Editor(exists=True)
    monkeypatch.setattr(lm.u, "call", ed)
    monkeypatch.setattr(lm.c, "project_mount", lambda: "/" + PROJECT)
    monkeypatch.setattr(lm.c.u, "call", ed)
    monkeypatch.setattr(lm.d, "course", course)
    monkeypatch.setattr(lm, "found", lambda tag=lm.TAG: [])
    lm.build(far=far)
    return ed


def test_far_art_never_culls_is_always_loaded_and_casts_no_shadow(monkeypatch):
    # The disproof run (play, 2026-10-13): placed WITHOUT these settings (`--probe-no-far`) the volcano and the titan were missing
    # from every play frame while the editor showed them; with them both stood on the horizon.
    ed = _built(monkeypatch)
    actors = [f"/Game/Map.Map:PersistentLevel.Actor_{n}" for n in (1, 3)]                # volcano is the first placement, the titan the second
    volcano, titan = "/Game/Map.Map:PersistentLevel.Actor_1", "/Game/Map.Map:PersistentLevel.Actor_2"
    assert ed.props[(volcano, "bIsSpatiallyLoaded")] is False
    assert ed.props[(volcano + ".StaticMeshComponent0", "bNeverDistanceCull")] is True
    assert ed.props[(volcano + ".StaticMeshComponent0", "castShadow")] is False
    assert ed.props[(titan, "bIsSpatiallyLoaded")] is False
    assert ed.props[(titan + ".SkeletalMeshComponent", "bNeverDistanceCull")] is True
    assert actors


def test_probe_flag_skips_the_far_art_settings(monkeypatch):
    ed = _built(monkeypatch, far=False)
    assert not [k for k in ed.props if k[1] in ("bIsSpatiallyLoaded", "bNeverDistanceCull", "castShadow")]
    lm.FAR = True


def test_remove_takes_out_only_the_tagged_actors(monkeypatch):
    ed = _Editor()
    monkeypatch.setattr(lm.u, "call", ed)
    monkeypatch.setattr(lm, "found", lambda tag=lm.TAG: [{"actorPath": f"/Game/Map.Map:PersistentLevel.A_{i}"} for i in range(4)])
    assert lm.remove() == 4
    assert [t for t, _ in ed.calls].count("remove_from_scene") == 4
    assert not [t for t, _ in ed.calls if t in ("add_to_scene_from_asset", "PlaceDevice")]


class _GlowEditor(_Editor):
    def __call__(self, toolset, tool, args=None, **kw):
        if tool == "get_property_input":
            self.calls.append((tool, args))
            return {"returnValue": {"output_name": "RGB", "input_name": "",
                                    "expression": {"refPath": "/m/Material_0.Material_0:MaterialExpressionTextureSample_0"}}}
        return super().__call__(toolset, tool, args, **kw)


def test_lava_glow_masks_the_red_channel_and_keeps_the_textures_hue(monkeypatch):
    ed = _GlowEditor()
    monkeypatch.setattr(il.u, "call", ed)
    il.lava_glow("/m/Material_0.Material_0")
    wires = [(a.get("to_input_name"), a["from_expression"]["refPath"].split(":")[-1].rsplit("_", 1)[0]) for t, a in ed.calls if t == "connect_expressions"]
    assert any(pin == "Base" and "TextureSample" in src for pin, src in wires)          # the texture's R channel -> Power (the mask)
    assert any(c["from_output_name"] == "R" for t, c in ed.calls if t == "connect_expressions")
    assert any(pin == "A" and "Power" in src for pin, src in wires)                     # Power -> Multiply
    out = [a for t, a in ed.calls if t == "connect_to_output"]
    assert len(out) == 1 and out[0]["material_property"] == "MP_EmissiveColor"
    sets = {k: v for (inst, k), v in ed.props.items()}
    assert sets["constExponent"] == il.GLOW_POWER and sets["constB"] == il.GLOW_STRENGTH
    assert [t for t, _ in ed.calls].count("recompile") == 1
