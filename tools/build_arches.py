"""Door arches (G9 wave 5, briefs/g9/T1_surfaces_arches.md): the Titan Peak stone arch (tools/import_titanpeak.py --arch:
FNM_TitanPeakArt/Arch/SM_fnm_tp_arch, 8k triangles, no collision) framing every answer door, in its tier's skin
(M_fnm_tp_arch_t1..t5: jungle stone, river stone, frost, obsidian, magma), in the open UEFN project through UEFN MCP.

Geometry comes from the course actors, never from assumed coordinates (station hallways sit at different X and levels), so it
survives a course rebuild: rerun this after tools/build_course.py. Per station: the Lintel's bounds give the door wall's
runner-side face (its min y) and the floor (its min z less build_course.DOOR_H); each FNM_Sxx_Door<L>'s bounds give the door's
x centre. The tier is build_course.auto_tier (the one the hallway's paint and the director use).

Per door: the arch stands on the floor, ARCH_W wide and ARCH_H tall, centred on the door, its back ARCH_EMBED cm inside the door
wall and its front ARCH_FRONT cm proud of it (the arch is a relief on the wall, not a free-standing gate). So:
- the opening (OPENING_FRAC of the width between the pillars, up to OPENING_TOP_FRAC of the height: measured from the GLB's
  vertices, tests/test_titanpeak_surfaces.py) clears the door prop's white frame (DOOR_FRAME_W x DOOR_FRAME_H, editor capture
  2026-10-13) with a margin on every side: nothing of the arch is in the doorway, so the door, its trigger and its barrier work
  exactly as before;
- the keystone (the top ~22% of the arch) sits on the lintel band, BEHIND the 3D lintel letter (tools/build_door_marks.py: its
  front 52 cm off the lintel face, the arch's front 40 cm): the letter stays whole in front of it;
- the arch mesh has no collision at all (import_titanpeak removes it), so a pillar never catches a runner or the camera.
Idempotent via actor tag `fnm_arches`: a run first deletes everything with it (or only the chosen station's with --only).

    python tools/build_arches.py             # every station
    python tools/build_arches.py --only 1    # only station 1's arches
    python tools/build_arches.py --check     # read-only: count, transforms against the layout, skins read back
    python tools/build_arches.py --remove    # remove every arch
"""
import argparse
import math
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import build_course as c  # noqa: E402
import uefn_mcp as u  # noqa: E402

TAG = "fnm_arches"
MESH = "FNM_TitanPeakArt/Arch/SM_fnm_tp_arch"
SKIN = "FNM_TitanPeakArt/Arch/M_fnm_tp_arch_t{tier}"
ARCH_W = 520.0              # overall width (a door is c.DOOR_W = 553 apart: neighbouring arches stand 33 cm apart)
ARCH_H = 590.0              # floor to the keystone's top, 10 cm under the wall top (build_decor's numbers stand on it)
ARCH_FRONT = 40.0           # how far the arch stands proud of the door wall (the lintel letter's front is 52 cm out)
ARCH_EMBED = 6.0            # how far its back sinks into the wall (the door prop is 44 thick, the lintel 50: no gap shows)
OPENING_FRAC = 0.47         # the opening's width / the arch's width, at the pillars' narrowest (GLB vertices)
OPENING_TOP_FRAC = 0.78     # the opening's top (the keystone's underside) / the arch's height (GLB vertices)
DOOR_FRAME_W = 190.0        # the OilRig door prop's white door frame (editor capture, 2026-10-13: ~165 door + frame)
DOOR_FRAME_H = 250.0
LETTER_FRONT = 52.0         # build_door_marks: LETTER_OUT 2 + LETTER_D 50, the letter's front off the lintel face
# The imported mesh (read back 2026-10-13): width along its LOCAL Y (177 cm), depth along X (55), height Z (190), centred on
# its bounds (the Blender FBX route turns the glTF's x-wide arch to y-wide). ARCH_YAW turns its width onto world X and its
# carved front (the keystone's face) toward the runner (-Y); seen in an editor capture.
ARCH_YAW = -90.0


def _turn(yaw, x, y):
    """A local horizontal vector turned by an actor yaw (UE: yaw 90 takes local +X to world +Y)."""
    r = math.radians(yaw)
    return x * math.cos(r) - y * math.sin(r), x * math.sin(r) + y * math.cos(r)


def layout(door_x, face_y, floor_z, native, yaw=None):
    """(x, y, z, sx, sy, sz, yaw) for the arch over a door whose centre is door_x, given the door wall's runner-side face y and
    the floor z; native = the mesh's bounds at scale 1 ({"min": {x, y, z}, "max": {...}}). The mesh's wider horizontal axis is
    its width (scaled to ARCH_W), the other its depth (ARCH_FRONT + ARCH_EMBED), Z its height (ARCH_H); yaw (a multiple of 90,
    default ARCH_YAW) must lay the width along world X."""
    yaw = ARCH_YAW if yaw is None else yaw
    mn, mx = native["min"], native["max"]
    ext = {k: mx[k] - mn[k] for k in "xyz"}
    wide = "y" if ext["y"] > ext["x"] else "x"
    if abs(_turn(yaw, *((0, 1) if wide == "y" else (1, 0)))[0]) < 0.99:
        sys.exit(f"yaw {yaw} does not lay the arch's width (local {wide}) along world X")
    s = {wide: ARCH_W / ext[wide], ("x" if wide == "y" else "y"): (ARCH_FRONT + ARCH_EMBED) / ext["x" if wide == "y" else "y"],
         "z": ARCH_H / ext["z"]}
    corners = [_turn(yaw, s["x"] * lx, s["y"] * ly) for lx in (mn["x"], mx["x"]) for ly in (mn["y"], mx["y"])]
    wx0, wx1 = min(c_[0] for c_ in corners), max(c_[0] for c_ in corners)
    wy0 = min(c_[1] for c_ in corners)
    return (door_x - (wx0 + wx1) / 2, face_y - ARCH_FRONT - wy0, floor_z - s["z"] * mn["z"], s["x"], s["y"], s["z"], yaw)


def footprint(door_x, face_y, floor_z):
    """The arch's world box and opening, from the constants alone: {"x": (x0, x1), "y": (front, back), "z": (z0, z1),
    "opening": (x0, x1, top z)} (what tests check against the door, the wall and the letter)."""
    half, inner = ARCH_W / 2, ARCH_W * OPENING_FRAC / 2
    return {"x": (door_x - half, door_x + half), "y": (face_y - ARCH_FRONT, face_y + ARCH_EMBED),
            "z": (floor_z, floor_z + ARCH_H), "opening": (door_x - inner, door_x + inner, floor_z + ARCH_H * OPENING_TOP_FRAC)}


def project():
    return c.project_mount()


def mesh_path():
    return f"{project()}/{MESH}.{MESH.rsplit('/', 1)[-1]}"


def skin_path(tier):
    s = SKIN.format(tier=tier)
    return f"{project()}/{s}.{s.rsplit('/', 1)[-1]}"


def native_bounds():
    return u.call("editor_toolset.toolsets.static_mesh.StaticMeshTools", "get_bounds", {"mesh": c.ref(mesh_path())})["returnValue"]


def doors_by_station():
    """{station number: {"lintel": bounds, "doors": [(letter, x centre)]}} from the course actors."""
    found = [a for a in u.call(c.SCENE, "find_actors", {"tag": c.TAG, "collision_channels": []})["returnValue"] if isinstance(a, dict)]
    out = {}
    for a in found:
        label = a.get("label", "")
        if m := re.fullmatch(r"FNM_S(\d\d)_Lintel", label):
            out.setdefault(int(m[1]), {"doors": []})["lintel"] = a["bounds"]
        elif m := re.fullmatch(r"FNM_S(\d\d)_Door([A-D])", label):
            b = a["bounds"]
            out.setdefault(int(m[1]), {"doors": []})["doors"].append((m[2], (b["min"]["x"] + b["max"]["x"]) / 2))
    for k, v in out.items():
        if "lintel" not in v or not v["doors"]:
            sys.exit(f"station {k}: no lintel or no doors in the course (run tools/build_course.py)")
        v["doors"].sort()
    return out


def placements():
    """[(label, tier, (x, y, z, sx, sy, sz, yaw))] for every door of the course."""
    stations = doors_by_station()
    tiers = c.tier_count()
    native = native_bounds()
    out = []
    for k, v in sorted(stations.items()):
        lb = v["lintel"]
        face_y, floor_z = lb["min"]["y"], lb["min"]["z"] - c.DOOR_H
        tier = c.auto_tier(k, len(stations), tiers)
        for letter, x in v["doors"]:
            out.append((f"FNM_S{k:02d}_Arch{letter}", tier, layout(x, face_y, floor_z, native)))
    return out


def find_arches():
    found = u.call(c.SCENE, "find_actors", {"tag": TAG, "collision_channels": []})["returnValue"]
    return [a for a in found if isinstance(a, dict)]


def remove(only=None):
    n = 0
    for a in find_arches():
        if only is None or a.get("label", "").startswith(f"FNM_S{only:02d}_"):
            u.call(c.SCENE, "remove_from_scene", {"actor": c.ref(a["actorPath"])})
            n += 1
    return n


def skin_of(actor):
    comp = c.read(actor, "staticMeshComponent")["refPath"]
    return comp, c.first_ref(c.read(comp, "overrideMaterials"))


def build(only=None):
    if not c.exists(mesh_path().split(".")[0]):
        sys.exit(f"{mesh_path()} missing: python tools/import_titanpeak.py --arch")
    jobs = [j for j in placements() if only is None or j[0].startswith(f"FNM_S{only:02d}_")]
    missing = sorted({t for _, t, _ in jobs if not c.exists(skin_path(t).split(".")[0])})
    if missing:
        sys.exit(f"arch skins missing for tiers {missing}: python tools/import_titanpeak.py --arch")
    print("removed", remove(only), "old arches")
    for label, tier, (x, y, z, sx, sy, sz, yaw) in jobs:
        r = u.call(c.SCENE, "add_to_scene_from_asset", {"asset_path": mesh_path(), "name": label,
                                                         "xform": c.xform(x, y, z, sx, sy, sz, yaw)})
        actor = r["returnValue"]["refPath"]
        u.call(c.ACTOR, "add_tag", {"actor": c.ref(actor), "tag": TAG})
        u.call(c.ACTOR, "set_label", {"actor": c.ref(actor), "label": label})
        comp, _ = skin_of(actor)
        c.props(comp, {"overrideMaterials": [c.ref(skin_path(tier))]})
    u.call(c.ASSETS, "save_assets", {"asset_paths": []})
    bad = check(quiet=True, only=only)
    if bad:
        sys.exit(f"{len(bad)} arches off after the save: " + "; ".join(bad[:4]))
    print(f"{len(jobs)} arches placed (scale {jobs[0][2][3]:.3f} x {jobs[0][2][4]:.3f} x {jobs[0][2][5]:.3f}, yaw {ARCH_YAW:.0f}); "
          "read back after the save: every transform and skin right")


def check(quiet=False, only=None):
    """Every arch against placements(): present, transform within 1 cm / 0.1 %, its tier's skin. The list of problems."""
    want = {label: (tier, xf) for label, tier, xf in placements() if only is None or label.startswith(f"FNM_S{only:02d}_")}
    have = {a["label"]: a for a in find_arches() if a.get("label") in want or only is None}
    bad = [f"{label} missing" for label in want if label not in have]
    bad += [f"{label} is not a door's arch" for label in have if label not in want]
    for label, a in have.items():
        if label not in want:
            continue
        tier, (x, y, z, sx, sy, sz, yaw) = want[label]
        t = u.call(c.ACTOR, "get_actor_transform", {"actor": c.ref(a["actorPath"])})["returnValue"]
        got = (t["location"]["x"], t["location"]["y"], t["location"]["z"], t["scale"]["x"], t["scale"]["y"], t["scale"]["z"])
        if any(abs(g - w) > (1.0 if i < 3 else 0.001 * abs(w) + 1e-4) for i, (g, w) in enumerate(zip(got, (x, y, z, sx, sy, sz)))):
            bad.append(f"{label} transform {tuple(round(v, 3) for v in got)} != {(round(x, 3), round(y, 3), round(z, 3), sx, sy, sz)}")
        if abs(((t["rotation"]["yaw"] - yaw) + 180) % 360 - 180) > 0.5:
            bad.append(f"{label} yaw {t['rotation']['yaw']} != {yaw}")
        _, skin = skin_of(a["actorPath"])
        if skin != skin_path(tier):
            bad.append(f"{label} skin {skin} != tier {tier}")
    if not quiet:
        print(f"{len(have)} arches checked against {len(want)} doors; {len(bad)} problems" + ("" if not bad else ": " + "; ".join(bad[:6])))
    return bad


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--only", type=int, help="only this station's arches")
    ap.add_argument("--check", action="store_true", help="read-only report")
    ap.add_argument("--remove", action="store_true", help="remove every arch (or --only N's)")
    a = ap.parse_args()
    if a.check:
        sys.exit(1 if check(only=a.only) else 0)
    elif a.remove:
        print("removed", remove(a.only), "arches")
        u.call(c.ASSETS, "save_assets", {"asset_paths": []})
    else:
        build(a.only)
