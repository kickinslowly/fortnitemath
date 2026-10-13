"""Volt, the robot host (tools/import_mascot.py, tools/build_mascot.py): the placement maths and the Animated Mesh device's
props, with no UEFN. The fixture is the live course's bounds (read 2026-10-13 from the editor): station 1's floor and walls
and the finish hall's walls, end wall and floor, so the checks run on the numbers the builder sees."""
import math
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

import build_finish as f  # noqa: E402
import build_mascot as m  # noqa: E402
import import_mascot as im  # noqa: E402

PROJECT = "c498eed2-96c5-4757-91a1-edb374b16d67"
ARM_HALF = 72.14            # SK_fnm_volt's bounds half extent along the arms (T-pose), cm at scale 1: the widest it gets
EYE_BACK = 350.0            # the default third-person camera sits about this far behind the player
WIDE_BACK = 900.0           # the orbit camera (fnm_penalty_cam) at the podium


def bounds(x0, x1, y0, y1, z0, z1):
    return {"min": {"x": x0, "y": y0, "z": z0}, "max": {"x": x1, "y": y1, "z": z1}}


def course(finish_shift=0.0):
    fy = finish_shift
    return {
        "FNM_S01_Floor": bounds(-1146, 1146, -12000, -8235, -38, 2),
        "FNM_S01_WallL": bounds(1106, 1146, -12000, -8235, 0, 600),
        "FNM_S01_WallR": bounds(-1146, -1106, -12000, -8235, 0, 600),
        "FNM_Finish_Floor": bounds(551, 2843, 65681 + fy, 67221 + fy, -38, 2),
        "FNM_Finish_WallL": bounds(2803, 2843, 65681 + fy, 67181 + fy, 0, 600),
        "FNM_Finish_WallR": bounds(551, 591, 65681 + fy, 67181 + fy, 0, 600),
        "FNM_Finish_WallEnd": bounds(551, 2843, 67181 + fy, 67221 + fy, 0, 600),
    }


def span(spec):
    """x/y footprint of Volt with his arms out, cm."""
    half = ARM_HALF * spec["scale"]
    return spec["x"] - half, spec["x"] + half, spec["y"] - half, spec["y"] + half


def bearing(frm, x, y):
    """Degrees off the +Y axis of (x, y) seen from frm (positive = toward +X, the player's left)."""
    return math.degrees(math.atan2(x - frm[0], y - frm[1]))


def facing(spec):
    return math.cos(math.radians(spec["yaw"] - m.FACING_YAW)), math.sin(math.radians(spec["yaw"] - m.FACING_YAW))


# ---------------------------------------------------------------- the start

def test_start_reads_the_hall_and_sits_beside_the_spawn():
    s = m.start_spec(course())
    assert s["label"] == "FNM_Mascot_Start" and s["clip"] == "wave"
    spawn = (0.0, -12000 + m.ENTRY_Y + m.ARRIVAL_FORWARD)                      # the director's landing spot, 450 in
    assert s["faces"] == spawn
    assert s["z"] == 2                                                         # on the floor's top, not the slab's
    assert abs(s["scale"] * m.MESH_HEIGHT - 270) < 1


def test_start_is_off_the_running_line_and_inside_the_walls():
    s = m.start_spec(course())
    x0, x1, y0, y1 = span(s)
    # nobody runs or spawns within 2 m of the centre line; a door wall 30 m ahead spans the whole hall
    assert x0 > 200 or x1 < -200, "Volt's footprint reaches the running line"
    assert abs(s["x"]) >= 400
    assert -1106 + 100 < x0 and x1 < 1106 - 100          # clear of both walls
    assert s["y"] > -12000 + 450 + 200                    # ahead of the spawn, so he is in front of the camera
    assert s["y"] < -9000 - 1500                           # nowhere near the door wall


def test_start_is_in_the_players_view_and_faces_them():
    s = m.start_spec(course())
    cam = (0.0, s["faces"][1] - EYE_BACK)
    angle = bearing(cam, s["x"], s["y"])
    assert abs(angle) < 35, angle                          # Fortnite's default FOV is 80 degrees across
    fx, fy = facing(s)
    tx, ty = s["faces"][0] - s["x"], s["faces"][1] - s["y"]
    n = math.hypot(tx, ty)
    assert (fx * tx + fy * ty) / n > 0.999                 # the mesh's +X points at the spawn spot


def test_start_is_to_the_players_right_of_the_station_sign():
    # the STATION 1 sign is on the left wall (build_course.station: x = ox + half - 5); Volt must not stand in front of it
    s = m.start_spec(course())
    assert s["x"] < 0


# ---------------------------------------------------------------- the podium

def test_podium_stand_spot_matches_the_directors_formula():
    stand = m.podium_stand(course())
    cx = (2803 + 591) / 2
    button_y = 67181 - f.PODIUM_BACK - 20                  # build_finish: buttons 20 cm in front of the lecterns' y
    assert stand == (cx, max(button_y - 350, 65681 + 150 + 300))
    assert stand[1] == button_y - 350                      # the entry floor is not the limit in the real hall


def test_podium_volt_is_inside_the_hall_clear_of_the_decor():
    s = m.podium_spec(course())
    x0, x1, y0, y1 = span(s)
    cx = (2803 + 591) / 2
    assert s["label"] == "FNM_Mascot_Podium" and s["clip"] == "ymca"
    assert abs(s["scale"] * m.MESH_HEIGHT - 300) < 1
    assert s["z"] == 2
    assert 591 < x0 and x1 < 2803                          # inside the walls
    assert x1 < 2602 - 50                                  # the left-hand flower pots (build_decor DF_FlowersAL) start at x 2602
    assert y1 < 67181 - 100                                # not in the end wall
    assert x0 > cx + f.PODIUM_SPREAD + 107 + 100          # clear of the RACE AGAIN label (214 cm wide) at its lectern


def test_podium_volt_does_not_cover_the_labels_the_lecterns_or_the_board_text():
    s = m.podium_spec(course())
    cx, sy = m.podium_stand(course())
    cam = (cx, sy - WIDE_BACK)                             # the wide orbit camera
    end = 67181
    x0, x1, _, _ = span(s)
    vlo = min(bearing(cam, x0, s["y"]), bearing(cam, x0, s["y"] - ARM_HALF * s["scale"]))
    vhi = max(bearing(cam, x1, s["y"]), bearing(cam, x1, s["y"] + ARM_HALF * s["scale"]))
    ly = end - f.PODIUM_BACK - 45                          # the labels' y (build_finish: y - 45 from the lectern's y)
    for side in (1, -1):
        lx = cx + side * f.PODIUM_SPREAD
        lo, hi = bearing(cam, lx - 107, ly), bearing(cam, lx + 107, ly)      # 214 cm wide label
        assert vhi < lo or vlo > hi, f"Volt's view span {vlo:.1f}..{vhi:.1f} covers the label at {lo:.1f}..{hi:.1f}"
        ply = end - f.PODIUM_BACK                          # the lectern, 109 cm wide
        lo, hi = bearing(cam, lx - 55, ply), bearing(cam, lx + 55, ply)
        assert vhi < lo or vlo > hi
    # the leaderboard's text rows are 786 cm wide, centred (build_finish ROW billboards: x 1304..2090 in the real hall)
    assert x0 > cx + 393


def test_podium_volt_is_in_the_wide_cameras_frame_and_faces_the_finisher():
    s = m.podium_spec(course())
    cx, sy = m.podium_stand(course())
    cam = (cx, sy - WIDE_BACK)
    assert abs(bearing(cam, s["x"], s["y"])) < 35
    fx, fy = facing(s)
    tx, ty = cx - s["x"], sy - s["y"]
    assert (fx * tx + fy * ty) / math.hypot(tx, ty) > 0.999
    assert s["y"] > sy                                     # past the finisher, in front of the board, not behind them


def test_podium_follows_a_longer_or_shorter_finish_hall():
    a, b = m.podium_spec(course()), m.podium_spec(course(finish_shift=1000))
    assert b["y"] - a["y"] == pytest.approx(1000) and b["x"] == a["x"] and b["yaw"] == pytest.approx(a["yaw"])


# ---------------------------------------------------------------- the device's props

def test_device_props_name_the_clip_loop_and_play():
    p = m.device_props(PROJECT, "wave")
    assert p["skeletalMesh"]["refPath"] == f"/{PROJECT}/FNM_MascotArt/Volt/SK_fnm_volt.SK_fnm_volt"
    assert p["animation"]["refPath"] == f"/{PROJECT}/FNM_MascotArt/Volt/A_fnm_volt_wave.A_fnm_volt_wave"
    assert p["loop"] is True and p["initialState"] == "Playing"


def test_volt_is_a_ghost_nobody_can_bump_or_shoot():
    assert m.GHOST == {"bNoCollision": True, "bCanBeDamaged": False}


def test_every_clip_has_its_own_animation_on_one_shared_mesh():
    props = {k: m.device_props(PROJECT, k) for k in im.CLIPS}
    assert len({p["animation"]["refPath"] for p in props.values()}) == len(im.CLIPS)
    assert len({p["skeletalMesh"]["refPath"] for p in props.values()}) == 1 + len(im.OWN_MESH)


def test_a_clip_with_its_own_mesh_points_at_it():
    p = m.device_props(PROJECT, "ymca", own=frozenset({"ymca"}))
    assert p["skeletalMesh"]["refPath"].endswith("Clip_ymca/SK_fnm_volt_ymca.SK_fnm_volt_ymca")
    assert p["animation"]["refPath"].endswith("Clip_ymca/A_fnm_volt_ymca.A_fnm_volt_ymca")


def test_an_unknown_clip_is_refused():
    with pytest.raises(ValueError):
        m.device_props(PROJECT, "moonwalk")


def test_placed_clips_exist_and_the_art_folder_is_not_a_verse_name():
    assert m.START_CLIP in im.CLIPS and m.PODIUM_CLIP in im.CLIPS
    assert im.ART == "FNM_MascotArt" and m.TAG == "fnm_mascot"
    assert m.ANIMATED_MESH == "/CRD_AnimatedMesh/Device_AnimatedMesh.Device_AnimatedMesh_C"


def test_the_clips_the_world_needs_have_their_fbx():
    raw = ROOT / "art" / "mascot" / "raw"
    assert set(im.REQUIRED) == {"idle", m.START_CLIP, m.PODIUM_CLIP}
    for clip in im.REQUIRED:
        assert (raw / f"{im.CLIPS[clip]}.fbx").is_file(), clip


# ---------------------------------------------------------------- the importer, against a stub editor

class _Editor:
    """Records every UEFN call the importer makes; answers the few it reads back."""

    def __init__(self):
        self.calls = []

    def __call__(self, toolset, tool, args=None, **_):
        self.calls.append((tool, args or {}))
        if tool == "find_assets":
            name = (args or {}).get("name", "")
            folder = (args or {}).get("folder_path", "")
            return {"returnValue": [f"/proj/x/M_fnm_wall_bm_marble.M"] if name == "M_fnm_wall_bm_marble"
                    else [f"{folder}/{name}.{name}"] if name else []}
        if tool == "exists":
            return {"returnValue": False}
        if tool == "get_vertex_count":
            return {"returnValue": 1}
        if tool == "get_bounds":
            return {"returnValue": {}}
        return {"returnValue": True}


def test_importer_keeps_one_mesh_and_skips_missing_spare_clips(tmp_path, monkeypatch, capsys):
    for stem in ("idle_0", "wave_28", "ymca_596"):
        (tmp_path / f"{stem}.fbx").write_bytes(b"fbx")
    editor = _Editor()
    monkeypatch.setattr(im.u, "call", editor)
    monkeypatch.setattr(im, "RAW", tmp_path)
    im.main()
    imports = [a for t, a in editor.calls if t == "import_file"]
    assert [a["asset_name"] for a in imports] == ["SK_fnm_volt", "SK_fnm_volt_tmp_wave", "SK_fnm_volt_tmp_ymca"]
    assert imports[0]["import_materials"] and imports[0]["import_textures"] and "skeleton" not in imports[0]
    for a in imports[1:]:                                   # shared skeleton, no second texture, the throwaway mesh is deleted
        assert a["skeleton"]["refPath"].endswith("SK_fnm_volt_Skeleton.SK_fnm_volt_Skeleton")
        assert not a["import_materials"] and not a["import_textures"] and a["import_animations"]
    deleted = [a["path"] for t, a in editor.calls if t == "delete"]
    assert any(p.endswith("Tmp_wave") for p in deleted) and any(p.endswith("Tmp_ymca") for p in deleted)
    assert "skipped dance" in capsys.readouterr().out


def test_importer_refuses_a_missing_clip_the_world_needs(tmp_path, monkeypatch):
    (tmp_path / "idle_0.fbx").write_bytes(b"fbx")
    monkeypatch.setattr(im.u, "call", _Editor())
    monkeypatch.setattr(im, "RAW", tmp_path)
    with pytest.raises(SystemExit):
        im.main()
