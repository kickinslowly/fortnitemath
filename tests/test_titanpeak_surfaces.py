"""Titan Peak surfaces and door arches (briefs/g9/T1_surfaces_arches.md): which material each course actor wears per tier,
the import's names and kept-not-replaced rule, the banner crop, and the arch's placement maths against the door, the wall and
the lintel letter. Pure logic and recorded fakes: no UEFN."""
import json
import struct
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
sys.path.insert(0, str(ROOT / "tests"))

import build_arches as ba  # noqa: E402
import build_course as c  # noqa: E402
import import_titanpeak as tp  # noqa: E402
from test_arena_layout import FakeUefn  # noqa: E402

S, T = 10, 5     # the course: 10 stations, 5 tiers


# ---------------------------------------------------------------- tier -> material

def test_every_tier_wears_its_own_floor_and_wall():
    for k in range(1, S + 1):
        tier = c.auto_tier(k, S, T)
        for part in ("WallL", "WallR", "WallStart", "Divider1", "Baffle2", "WallC1L", "WallFunnelR", "WallFlareL", "WallC2R3"):
            label = f"FNM_S{k:02d}_{part}"
            assert c.surface_key(label, c.paint_key(label, S, T), S, T) == f"t{tier}_wall", label
        for part in ("Floor", "FloorC1", "FloorFunnel", "FloorFlare", "Step1_03"):
            label = f"FNM_S{k:02d}_{part}"
            assert c.surface_key(label, c.paint_key(label, S, T), S, T) == f"t{tier}_floor", label
    # the brief's table: stations 1-2 BASE CAMP ... 9-10 MAGMA CORE
    assert [c.auto_tier(k, S, T) for k in range(1, 11)] == [1, 1, 2, 2, 3, 3, 4, 4, 5, 5]


def test_the_ice_floor_takes_frost_ridge_and_the_flat_colours_stay_where_they_must():
    key = lambda label: c.surface_key(label, c.paint_key(label, S, T), S, T)  # noqa: E731
    assert 6 in c.ICE_STATIONS and key("FNM_S06_Floor") == "t3_floor"          # FROST RIDGE: the ice station
    assert key("FNM_Arena_Floor") == key("FNM_Arena_FloorC1") == key("FNM_Arena_FloorFunnel") == "forge_floor"
    for label in ("FNM_Arena_WallL", "FNM_Arena_WallC1R",                        # arena walls: left as they are (brief)
                  "FNM_S03_Lintel", "FNM_S10_Lintel",                            # the dark band the door letters read against
                  "FNM_S02_Hurdle1", "FNM_Arena_Platform", "FNM_Arena_PadA", "FNM_Arena_PadD",
                  "FNM_Finish_WallL", "FNM_Finish_Floor"):
        assert key(label) is None, label
    for label in ("FNM_S01_DoorA", "FNM_S01_TriggerB", "FNM_S01_Entry", "FNM_Director"):
        assert c.paint_key(label, S, T) is None and c.surface_key(label, None, S, T) is None


def test_paint_material_paths_and_the_flat_switch():
    c.project_mount.cache_clear()
    saved = c.u.call
    c.u.call = FakeUefn({"ListFiles": [{"name": "/proj/", "type": "Directory"}]})
    try:
        assert c.paint_material("FNM_S03_WallL", S, T, True) == "/proj/FNM_TitanPeakArt/Surfaces/M_fnm_tp_t2_wall.M_fnm_tp_t2_wall"
        assert c.paint_material("FNM_S03_WallL", S, T, False) == "/proj/FNM_Art/M_fnm_wall_tier2.M_fnm_wall_tier2"
        assert c.paint_material("FNM_S03_Lintel", S, T, True) == "/proj/FNM_Art/M_fnm_wall_lintel.M_fnm_wall_lintel"
        assert c.paint_material("FNM_S01_DoorA", S, T, True) is None
        assert c.SURFACES is True                                              # the default; --flat flips it
    finally:
        c.u.call = saved
        c.project_mount.cache_clear()


def test_every_surface_key_is_imported_and_tuned():
    produced = {c.surface_key(f"FNM_S{k:02d}_{p}", c.paint_key(f"FNM_S{k:02d}_{p}", S, T), S, T)
                for k in range(1, S + 1) for p in ("WallL", "Floor", "FloorC1")} | {"forge_floor"}
    assert produced == set(tp.SURFACES), produced ^ set(tp.SURFACES)
    for key in tp.SURFACES:
        assert 200 <= tp.TILE[key] <= 400, key                                 # the brief: about 2-4 m per repeat
        assert all(0.2 <= v <= 1.0 for v in tp.TINT[key]), key                 # a tint only darkens
        maps = tp.maps(key)                                                    # the Mint zip is unzipped
        assert {"base", "normal", "rough"} == set(maps) and all(p.exists() for p in maps.values()), key


def test_surface_paint_names_the_titanpeak_import_and_check_paint_catches_a_wrong_tier():
    """The disproof the brief asks for, as a test: an actor painted with another tier's surface fails check_paint."""
    state = {}
    actors = [{"label": "FNM_S01_WallL", "actorPath": "/lvl/w1"}, {"label": "FNM_S01_Floor", "actorPath": "/lvl/f1"},
              {"label": "FNM_S01_Lintel", "actorPath": "/lvl/l1"}]

    def get_properties(a):
        key, inst = a["properties"][0], a["instance"]["refPath"]
        if key == "staticMeshComponent":
            return {"returnValue": json.dumps({key: {"refPath": inst + ".C"}})}
        return {"returnValue": json.dumps({key: [{"refPath": state[inst]}] if state.get(inst) else [None]})}

    def set_properties(a):
        state[a["instance"]["refPath"]] = json.loads(a["values"])["overrideMaterials"][0]["refPath"]
        return {"returnValue": True}

    have = {"/proj/FNM_Art/M_fnm_wall_lintel", "/proj/FNM_TitanPeakArt/Surfaces/M_fnm_tp_t1_wall"}
    fake = FakeUefn({"ListFiles": [{"name": "/proj/", "type": "Directory"}], "find_actors": actors, "save_assets": True,
                     "exists": lambda a: {"returnValue": a["path"] in have},
                     "get_properties": get_properties, "set_properties": set_properties})
    c.project_mount.cache_clear()
    c._COMPS.clear()
    saved = (c.u.call, c.tier_count)
    c.u.call, c.tier_count = fake, lambda: T
    try:
        with pytest.raises(SystemExit) as e:
            c.paint(surfaces=True)
        assert "t1_floor" in str(e.value) and "import_titanpeak.py --materials" in str(e.value)
        assert "set_properties" not in fake.tools()
        have.add("/proj/FNM_TitanPeakArt/Surfaces/M_fnm_tp_t1_floor")
        c.paint(surfaces=True)
        assert state == {"/lvl/w1.C": "/proj/FNM_TitanPeakArt/Surfaces/M_fnm_tp_t1_wall.M_fnm_tp_t1_wall",
                         "/lvl/f1.C": "/proj/FNM_TitanPeakArt/Surfaces/M_fnm_tp_t1_floor.M_fnm_tp_t1_floor",
                         "/lvl/l1.C": "/proj/FNM_Art/M_fnm_wall_lintel.M_fnm_wall_lintel"}
        assert c.check_paint(surfaces=True) == []
        state["/lvl/w1.C"] = "/proj/FNM_TitanPeakArt/Surfaces/M_fnm_tp_t2_wall.M_fnm_tp_t2_wall"   # tier 2's wall on station 1
        bad = c.check_paint(surfaces=True)
        assert len(bad) == 1 and bad[0].startswith("FNM_S01_WallL") and "M_fnm_tp_t2_wall" in bad[0], bad
        assert len(c.check_paint(surfaces=False)) == 2      # against the flat paint the wall and floor are off (the lintel is flat in both)
    finally:
        c.u.call, c.tier_count = saved
        c.project_mount.cache_clear()
        c._COMPS.clear()


def test_build_course_has_the_flat_flag():
    out = subprocess.run([sys.executable, str(ROOT / "tools" / "build_course.py"), "--help"], capture_output=True, text=True,
                         timeout=60)
    assert out.returncode == 0 and "--flat" in out.stdout
    src = (ROOT / "tools" / "build_course.py").read_text(encoding="utf-8")
    assert "if a.flat:\n        SURFACES = False" in src.replace("\r\n", "\n")


# ---------------------------------------------------------------- import_titanpeak: names, keep, banners

def test_import_names_match_what_t2_codes_against():
    assert set(tp.PROPS) == {"gate", "podium", "jungle_pillar", "river_boulders", "ice_crystals", "obsidian_spire",
                             "lava_vent", "rune_stone"}
    assert set(tp.BANNERS) == {"base_camp", "waterfall_gorge", "frost_ridge", "obsidian_descent", "magma_core",
                               "titans_forge", "hall_of_champions"}
    for name, (sub, glb) in {**tp.PROPS, "arch": tp.ARCH}.items():
        assert (tp.TP / f"{glb}.glb").exists(), glb
        assert not sub.startswith("fnm"), sub                  # a Verse-style folder name breaks the build (uefn-mcp skill)
    for n in tp.ARCH_TIERS:
        assert (tp.TP / "arch" / "raw" / f"arch_t{n}_base_color.png").exists(), n
    assert "SM_fnm_tp_banner_{key}" in Path(tp.__file__).read_text(encoding="utf-8")


def test_an_existing_mesh_or_texture_is_kept_never_deleted_or_reimported():
    fake = FakeUefn({"ListFiles": [{"name": "/proj/", "type": "Directory"}], "exists": True, "find_assets": [],
                     "save_assets": True, "set_properties": True,
                     "get_properties": '{"lODBias": 0, "compressionSettings": "TC_Normalmap", "sRGB": false}'})
    saved = tp.u.call
    tp.u.call = fake
    try:
        tp.props()
        tp.import_texture("/proj/FNM_TitanPeakArt/Surfaces", "T_fnm_tp_t1_floor_base", Path("nowhere.png"))
    finally:
        tp.u.call = saved
    assert "import_file" not in fake.tools() and "delete" not in fake.tools()
    # a kept colour texture the importer took for a normal map (the purple arch_t3 did, 2026-10-13) has its settings put right
    fixed = [json.loads(a["values"]) for t, a in fake.calls if t == "set_properties"]
    assert {"compressionSettings": "TC_Default"} in fixed and {"sRGB": True} in fixed and {"lODBias": 0} not in fixed
    assert '"delete"' not in Path(tp.__file__).read_text(encoding="utf-8")   # no AssetTools delete call anywhere in it


def test_banner_crop_is_power_of_two_and_keeps_the_aspect(tmp_path):
    from PIL import Image
    for key in tp.BANNERS:
        png, aspect = tp.banner_png(key, tmp_path)
        w, h = Image.open(png).size
        assert w == tp.BANNER_TEX_W and h & (h - 1) == 0, (key, w, h)          # power of two: it can stream
        raw = Image.open(tp.TP / "banners" / f"{key}_raw.png")
        assert aspect > 1.4 and abs(aspect - w / h) / aspect < 0.5, (key, aspect)
        assert Image.open(png).getchannel("A").getextrema()[0] == 0          # still has its transparent margin
        assert raw.size == (1376, 768)
        quad = tp.banner_obj(tmp_path, key, aspect).read_text()
        xs = [float(line.split()[1]) for line in quad.splitlines() if line.startswith("v ")]
        ys = [float(line.split()[2]) for line in quad.splitlines() if line.startswith("v ")]
        zs = [float(line.split()[3]) for line in quad.splitlines() if line.startswith("v ")]
        # UEFN's OBJ import keeps OBJ z as up (read back 2026-10-13): the quad stands in x / z, flat in y
        assert set(ys) == {0.0} and max(xs) == -min(xs) == tp.BANNER_W / 2 and min(zs) == 0   # pivot at the bottom centre
        assert abs((max(xs) - min(xs)) / max(zs) - aspect) < 1e-6              # the art's true aspect: not stretched
        # u = 0 at +X: a reader looking +Y has +X on the left, so the art reads left to right from -Y (seen in a capture)
        vts = [line for line in quad.splitlines() if line.startswith("vt ")]
        assert quad.splitlines()[0].split()[1] == str(tp.BANNER_W / 2) and vts[0] == "vt 0 0" and tp.BANNER_FACING == "-Y"


def test_import_flags():
    out = subprocess.run([sys.executable, str(ROOT / "tools" / "import_titanpeak.py"), "--help"], capture_output=True,
                         text=True, timeout=60)
    for flag in ("--props", "--banners", "--arch", "--materials", "--check"):
        assert flag in out.stdout, flag


# ---------------------------------------------------------------- the arch

def _glb_positions(path):
    import numpy as np
    b = path.read_bytes()
    off, chunks = 12, []
    while off < len(b):
        n, _ = struct.unpack("<II", b[off:off + 8])
        chunks.append(b[off + 8:off + 8 + n])
        off += 8 + n
    j = json.loads(chunks[0])
    pr = j["meshes"][0]["primitives"][0]
    a = j["accessors"][pr["attributes"]["POSITION"]]
    bv = j["bufferViews"][a["bufferView"]]
    st = bv.get("byteOffset", 0) + a.get("byteOffset", 0)
    return np.frombuffer(chunks[1][st:st + a["count"] * 12], dtype="<f4").reshape(-1, 3)


def test_arch_opening_constants_come_from_the_mesh():
    import numpy as np
    p = _glb_positions(tp.TP / "arch" / "raw" / "arch_t1.glb")
    x, y = p[:, 0], p[:, 1]                       # glTF: x across, y up
    w, h = x.max() - x.min(), y.max() - y.min()
    below = y < y.min() + 0.7 * h                 # the pillars, under the arch ring
    assert 2 * np.abs(x[below]).min() / w >= ba.OPENING_FRAC - 0.005
    centre = np.abs(x) < 0.05 * w                 # the keystone's underside is the opening's top
    assert (y[centre].min() - y.min()) / h >= ba.OPENING_TOP_FRAC - 0.005
    for n in (2, 3, 4, 5):                        # the tier skins share the mesh exactly
        assert np.array_equal(p, _glb_positions(tp.TP / "arch" / "raw" / f"arch_t{n}.glb")), n


# the arch mesh as UEFN reads it back (get_bounds 2026-10-13): width along local Y, depth X, centred on its bounds
NATIVE = {"min": {"x": -27.42, "y": -88.71, "z": -95.19}, "max": {"x": 27.40, "y": 88.72, "z": 94.94}}
NATIVE_X_WIDE = {"min": {"x": -88.7, "y": -27.4, "z": -95.2}, "max": {"x": 88.7, "y": 27.4, "z": 94.9}}


@pytest.mark.parametrize("native,yaw", [(NATIVE, -90.0), (NATIVE, 90.0), (NATIVE_X_WIDE, 0.0), (NATIVE_X_WIDE, 180.0)])
def test_arch_layout_lands_on_its_footprint(native, yaw):
    door_x, face_y, floor_z = 829.5, -9025.0, 0.0
    x, y, z, sx, sy, sz, got_yaw = ba.layout(door_x, face_y, floor_z, native, yaw)
    corners = [ba._turn(yaw, sx * lx, sy * ly) for lx in (native["min"]["x"], native["max"]["x"])
               for ly in (native["min"]["y"], native["max"]["y"])]
    xs = (x + min(c_[0] for c_ in corners), x + max(c_[0] for c_ in corners))
    ys = (y + min(c_[1] for c_ in corners), y + max(c_[1] for c_ in corners))
    zs = (z + sz * native["min"]["z"], z + sz * native["max"]["z"])
    fp = ba.footprint(door_x, face_y, floor_z)
    for got, want in ((xs, fp["x"]), (ys, fp["y"]), (zs, fp["z"])):
        assert abs(got[0] - want[0]) < 1e-6 and abs(got[1] - want[1]) < 1e-6, (got, want)
    assert got_yaw == yaw
    assert ba.ARCH_YAW == -90.0                   # seen in an editor capture: the carved front faces the runner
    with pytest.raises(SystemExit):               # a yaw that would lay the arch's width across the doorway is refused
        ba.layout(door_x, face_y, floor_z, native, yaw + 90)


def test_arch_frames_every_door_and_stays_out_of_the_doorway():
    import build_door_marks as m
    face_y, floor_z = -9025.0, 2.0
    boxes = []
    for i, dx in enumerate(c.door_centres(4)):
        fp = ba.footprint(dx, face_y, floor_z)
        x0, x1, top = fp["opening"]
        # nothing of the arch in the doorway: the opening clears the door's frame with a margin on both sides and above
        assert x0 <= dx - ba.DOOR_FRAME_W / 2 - 15 and x1 >= dx + ba.DOOR_FRAME_W / 2 + 15
        assert top >= floor_z + ba.DOOR_FRAME_H + 50
        # inside the wall plane: the back sinks into the door wall (the door prop is 44 cm thick, the lintel 50), never through it
        assert fp["y"][1] > face_y and fp["y"][1] - face_y < 22
        # the keystone stands behind the lintel letter: the letter's front stays in front of the arch's front
        letter = m.layout(dx, face_y, floor_z, i)["letter"]
        letter_front = letter[1] - m.LETTER_D * letter[3] / 2
        assert fp["y"][0] > letter_front + 5 and ba.LETTER_FRONT == m.LETTER_OUT + m.LETTER_D
        assert top < letter[2] + m.LETTER_H and fp["z"][1] > letter[2]       # the keystone is in the letter's band
        assert fp["z"][1] <= floor_z + c.WALL_H                               # under the wall top (the station numbers)
        boxes.append(fp["x"])
    half = 4 * c.DOOR_W / 2
    assert boxes[0][1] < half and boxes[-1][0] > -half                        # inside the hallway's side walls
    for a, b in zip(boxes, boxes[1:]):
        assert b[1] < a[0], (a, b)                                            # neighbouring arches do not overlap
