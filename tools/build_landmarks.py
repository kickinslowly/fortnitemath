"""The landmarks (G9 "Titan Peak"), all tagged `fnm_landmarks` and labelled FNM_Landmark_*:

- the VOLCANO (Meshy, SM_fnm_volcano): far along +Y beyond the finish hall, so the player at station 1's start sees its peak
  standing above the door wall, and it grows as they climb. Always loaded (`bIsSpatiallyLoaded` false), no collision.
- the TITAN on its rim: the race titan's skeletal mesh (idle clip) on ONE Animated Mesh device, giant, facing the course (-Y).
  It reuses the imported FNM_BossArt mesh (no new memory); it carries NO Verse tag, so the director does not drive it yet. A later
  director could place the other clips beside it (one looping device per clip, parked and shrunk like the race titan's:
  BOSS_MODE 15b) and roar when a player reaches the arena.
- the TROPHY (Meshy, SM_fnm_trophy: the Titan Cup) on a plain plinth in the victory area, opposite Volt, beside the NEW SKILL
  lectern's side wall: out of the walking line, clear of the labels, lecterns, the all-time board's text and Volt.

Geometry is read from the course actors (`tools/build_decor.course()`: station 1's floor, walls and lintel, the arena, the finish
hall), so it survives a course rebuild and a changed hall length; rerun it after one. Idempotent: a run removes its own actors
first. Needs `python tools/import_landmarks.py` once per UEFN project (and `tools/import_boss.py` for the titan).

    python tools/build_landmarks.py               # place everything
    python tools/build_landmarks.py --remove      # take it all out (one tag)
    python tools/build_landmarks.py --check       # list what is placed with the read-back settings (read-only)
    python tools/build_landmarks.py --no-titan    # volcano and trophy only
    python tools/build_landmarks.py --on-podium   # the trophy on the champions' podium's top step (tools/build_titanpeak.py --part podium), no plinth

VOLCANO MATHS (cm; the pure functions below are what tests/test_landmarks.py checks)
- Every hallway faces +Y and the arena is at +Y, so a mountain straight ahead is above the door wall in every station. From station 1's
  start the third-person camera sits CAMERA_Z above the floor and EYE_BACK behind the spawn spot; the door wall's lintel top edge
  (z 600, 25 m ahead) is the horizon the player sees, at about 7 degrees. The peak is put at PEAK_DEG above the camera: the cone's
  upper part stands above the wall and its foot is hidden behind it. It is VOLCANO_PAST beyond the finish end wall, so it is a
  mountain, not a prop, and it GROWS as they climb (the angle rises as the distance falls).
- Size follows from that angle and the distance, not the other way round: the mesh is 1.03 m tall and 1.9 wide, so the scale comes
  out at about 573 x 573 x 716 (a 725 m peak, 1.1 km wide, 2.2 km from station 1's camera). TALL stretches Z over X/Y: the squat
  Meshy cone reads better taller (offline Blender previews of the view from station 1, 2026-10-13).

SEEN (2026-10-13, UEFN 42.30; frames under scratchpad/team/P, listed in the builder's report)
- The island is an ocean, so the volcano stands in the sea at the horizon, which suits it. The base is far below any wall.
- FAR ART MUST BE SET UP OR IT IS NOT DRAWN IN PLAY. A freshly placed static mesh actor is spatially loaded and its component reads
  cachedMaxDrawDistance 40000 (400 m); the same volcano and titan placed without `far_settings` (`--probe-no-far`) were in the editor
  and MISSING from the play frame, with the sky digits still there. With `bIsSpatiallyLoaded` false and `bNeverDistanceCull` true both
  stood on the horizon at Hour19, no pop-in in the first seconds. (Which of the two settings carries it was not separated.)
- The titan's idle plays on the device at scale 90 (upright, a slightly different pose in frames 4 s apart); it faces the course.
- Haze: at 2.2 km the dusk atmosphere turns the basalt cone lavender and the rim hot pink. The lava glow (import_landmarks.lava_glow)
  is what keeps the rim reading as fire.
- THE QUESTION PANEL HIDES IT IN THE RACE. From station 1's default camera the door wall's top edge sits at the panel's bottom edge, so
  the whole sky above the wall (the panel spans 40 to 345 px of 1080, 370 to 1550 across) is HUD: only the titan's head clears the
  panel's top. The volcano shows in the grade/skill picker, before the first question, with the camera pitched up, and from any
  view without the panel. The fix is the panel's (a shorter or fading question card), not the volcano's: nothing placed in the world
  can be above the panel unless it is above the screen.
"""
import argparse
import json
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import build_course as c  # noqa: E402
import build_decor as d  # noqa: E402
import build_finish as fin  # noqa: E402
import import_landmarks as il  # noqa: E402
import uefn_mcp as u  # noqa: E402

TAG = "fnm_landmarks"
ANIMATED_MESH = "/CRD_AnimatedMesh/Device_AnimatedMesh.Device_AnimatedMesh_C"
CUBE = "/Engine/BasicShapes/Cube.Cube"
MARBLE = "M_fnm_wall_bm_marble"          # the plinth's cream stone (tools/import_art.py)

# ---------------------------------------------------------------- the player's eye (station 1's start)
ENTRY_Y = 150.0           # build_course.station: the entry teleporter's offset from the hallway start
ARRIVAL_FORWARD = 300.0   # the director's ArrivalForward
CAMERA_Z = 250.0          # default third-person camera height above the floor (an estimate; see the report)
EYE_BACK = 350.0          # ... and how far behind the player (tests/test_mascot.py EYE_BACK)

# ---------------------------------------------------------------- the volcano
# The mesh's local bounds at scale 1 in UE cm (import_landmarks --check prints them; read 2026-10-13).
VOLCANO_MESH = {"min": (-95.2, -89.8, -51.6), "max": (95.1, 89.6, 51.6)}
VOLCANO_RIM = {"centre": (4.3, -0.7), "radius": 34.2}   # the crater ring: centre xy and outer radius, mesh cm at scale 1 (Blender read, axes swapped to UE)
VOLCANO_PAST = 150000.0   # beyond the finish hall's end wall: 1.54 km past the arena's gate
PEAK_DEG = 17.5           # the peak's elevation seen from station 1's camera (headroom under the 25 degree top of an 80 degree 16:9 frame for the titan on the rim)
TALL = 1.25               # Z stretch over X/Y: the squat Meshy cone reads better as a taller one (preview renders 2026-10-13)
SINK = 0.02               # the foot goes this fraction of the height below the course floor
VOLCANO_YAW = 0.0         # the lava rivers face the course at yaw 0 (preview renders and the play frames)

# ---------------------------------------------------------------- the titan on the rim
TITAN_SCALE = 90.0        # the mesh is 3 m: 270 m (6 degrees tall from station 1: 60 was a 40 px speck in the first editor frame)
TITAN_STAND = 0.8         # of the rim's outer radius from its centre, on the side nearest the course
TITAN_SINK = 0.01         # of the volcano's height: its feet go this far into the rim

# ---------------------------------------------------------------- the trophy
TROPHY_MESH = {"min": (-53.6, -91.5, -95.2), "max": (53.5, 91.5, 95.1)}   # UE cm at scale 1 (import_landmarks --check, read 2026-10-13)
TROPHY_SCALE = 1.3        # 2.5 m of cup (1.05 read as a toy beside Volt's 3 m in the first editor frame)
TROPHY_DX = 690.0         # cm from the hall's centre line, toward NEW SKILL (-X): Volt's own offset, mirrored
TROPHY_BACK = 480.0       # cm in front of the end wall: Volt's own
PLINTH = (150.0, 150.0, 60.0)
PLINTH_COLOUR_KEY = "bm_marble"
TROPHY_ON_PODIUM_SCALE = 0.65   # --on-podium: 1.2 m of cup on the centre step's ~1.3 x 1.5 m top (the podium is 2.2 x its mesh: build_titanpeak)
TROPHY_FRONT_YAW = 0.0    # the world yaw at which the cup's emblem faces +X (set from a capture, then fixed here)

GHOST = {"bCanBeDamaged": False}
FAR = True                # --probe-no-far sets it False: the disproof that the far-art settings are what keep the volcano drawn
# Far-away art (read from the live volcano 2026-10-13): a static mesh component's cachedMaxDrawDistance reads 40000 (400 m), so the
# volcano would vanish in play unless it never distance-culls (cachedMaxDrawDistance itself is not settable); its actor is spatially
# loaded by default (World Partition would stream it by distance); a 1.5 km mountain must not cast shadows or join the distance-field
# scene. One key per call (a combined write can keep the old value).
FAR_ACTOR = {"bIsSpatiallyLoaded": False}
FAR_COMPONENT = {"bNeverDistanceCull": True, "lDMaxDrawDistance": 0, "bAllowCullDistanceVolume": False, "castShadow": False,
                 "bCastDynamicShadow": False, "bAffectDistanceFieldLighting": False}


# ---------------------------------------------------------------- pure layout (tests read these)

def hall(course, prefix):
    """(cx, y0, y_end, z) of a hall from its course actors: the walls' inner faces, the floor's first edge and top, and
    (finish only) the end wall's inner face."""
    wl, wr, floor = (course[f"{prefix}_{n}"] for n in ("WallL", "WallR", "Floor"))
    end = course[f"{prefix}_WallEnd"]["min"]["y"] if f"{prefix}_WallEnd" in course else None
    return (wl["min"]["x"] + wr["max"]["x"]) / 2, floor["min"]["y"], end, floor["max"]["z"]


def eye(course):
    """Station 1's start camera: (x, y, z) behind the player's landing spot, and the landing spot's y."""
    cx, y0, _, z = hall(course, "FNM_S01")
    spawn_y = y0 + ENTRY_Y + ARRIVAL_FORWARD
    return cx, spawn_y - EYE_BACK, z + CAMERA_Z, spawn_y


def wall_top(course):
    """The door wall's top edge seen from the start: (y of its near face, z of its top). The lintel fills the wall above the doors."""
    lin = course["FNM_S01_Lintel"]
    return lin["min"]["y"], lin["max"]["z"]


def elevation(cam, y, z):
    """Degrees above the horizontal of the point at depth y, height z, seen from cam (x, y, z)."""
    return math.degrees(math.atan2(z - cam[2], y - cam[1]))


def course_end(course):
    """The last y of anything the player walks in (the finish hall's end wall)."""
    return max(b["max"]["y"] for k, b in course.items() if k.startswith("FNM_Finish_"))


def volcano_spec(course, past=None, peak_deg=None, tall=None, mesh=None, yaw=None):
    """The volcano actor: location, scale (sx, sy, sz), yaw, and what it stands for (peak, rim, base)."""
    past = VOLCANO_PAST if past is None else past
    peak_deg = PEAK_DEG if peak_deg is None else peak_deg
    tall = TALL if tall is None else tall
    mesh = mesh or VOLCANO_MESH
    yaw = VOLCANO_YAW if yaw is None else yaw
    cam = eye(course)
    s1 = hall(course, "FNM_S01")
    arena = hall(course, "FNM_Arena")
    cx = (s1[0] + arena[0]) / 2
    y = course_end(course) + past
    floor_z = s1[3]
    peak_z = cam[2] + (y - cam[1]) * math.tan(math.radians(peak_deg))
    h_mesh = mesh["max"][2] - mesh["min"][2]
    base_z = floor_z - SINK * (peak_z - floor_z)
    sz = (peak_z - base_z) / h_mesh
    sxy = sz / tall
    z = base_z - mesh["min"][2] * sz           # the actor's origin: mesh z is not centred on it
    return {"label": "FNM_Landmark_Volcano", "x": cx, "y": y, "z": z, "yaw": yaw, "sx": sxy, "sy": sxy, "sz": sz,
            "peak_z": peak_z, "base_z": base_z, "peak_y": y, "height": peak_z - base_z,
            "half_width": sxy * max(mesh["max"][0], -mesh["min"][0], mesh["max"][1], -mesh["min"][1])}


def peak_degrees(spec, cam):
    """The peak's elevation in degrees seen from cam (x, y, z)."""
    return elevation(cam, spec["peak_y"], spec["peak_z"])


def rim_point(spec, mesh=None, rim=None):
    """World (x, y, z) of the crater rim's centre and its outer radius (cm)."""
    mesh = mesh or VOLCANO_MESH
    rim = rim or VOLCANO_RIM
    yaw = math.radians(spec["yaw"])
    dx, dy = rim["centre"][0] * spec["sx"], rim["centre"][1] * spec["sy"]
    x = spec["x"] + dx * math.cos(yaw) - dy * math.sin(yaw)
    y = spec["y"] + dx * math.sin(yaw) + dy * math.cos(yaw)
    z = spec["z"] + mesh["max"][2] * spec["sz"]
    return x, y, z, rim["radius"] * spec["sx"]


def titan_spec(course, spec=None, scale=None, stand=None):
    """The titan on the rim's side nearest the course, feet on the rim, facing the arena (the mesh faces +X: yaw = atan2 toward it)."""
    spec = spec or volcano_spec(course)
    scale = TITAN_SCALE if scale is None else scale
    stand = TITAN_STAND if stand is None else stand
    rx, ry, rz, r = rim_point(spec)
    arena = hall(course, "FNM_Arena")
    x, y = rx, ry - stand * r
    yaw = math.degrees(math.atan2(arena[1] - y, arena[0] - x))
    return {"label": "FNM_Landmark_Titan", "x": x, "y": y, "z": rz - TITAN_SINK * spec["height"], "yaw": yaw, "scale": scale}


def trophy_spec(course, scale=None, front_yaw=None, podium=None):
    """The Titan Cup: opposite Volt (he is TROPHY_DX toward RACE AGAIN, +X), turned to the finisher's spot (cx, between the lecterns).
    With `podium` (tools/build_titanpeak.podium_spec: x, y, top, faces) it stands on that podium's top step instead, facing the same
    way, on no plinth (spec["plinth"] None); the cup is TROPHY_ON_PODIUM_SCALE unless `scale` says otherwise."""
    scale = (TROPHY_ON_PODIUM_SCALE if podium else TROPHY_SCALE) if scale is None else scale
    front = TROPHY_FRONT_YAW if front_yaw is None else front_yaw
    cx, _, end, floor_z = hall(course, "FNM_Finish")
    mesh_min_z = TROPHY_MESH["min"][2]
    if podium:
        stand = podium["faces"]
        yaw = math.degrees(math.atan2(stand[1] - podium["y"], stand[0] - podium["x"])) - front
        return {"label": "FNM_Landmark_Trophy", "x": podium["x"], "y": podium["y"], "z": podium["top"] - mesh_min_z * scale, "yaw": yaw,
                "scale": scale, "plinth": None, "faces": stand}
    x, y = cx - TROPHY_DX, end - TROPHY_BACK
    stand = (cx, end - fin.PODIUM_BACK - 20.0 - 350.0)       # the director's PodiumSpot (fnm_director PodiumStandOff 350)
    yaw = math.degrees(math.atan2(stand[1] - y, stand[0] - x)) - front
    # the mesh's origin is mid-height (bounds z -95..+95): the cup's base sits on the plinth's top
    return {"label": "FNM_Landmark_Trophy", "x": x, "y": y, "z": floor_z + PLINTH[2] - mesh_min_z * scale, "yaw": yaw, "scale": scale,
            "plinth": {"label": "FNM_Landmark_Plinth", "x": x, "y": y, "z": floor_z + PLINTH[2] / 2, "yaw": 0.0, "size": PLINTH},
            "faces": stand}


def trophy_rects(spec, mesh=None):
    """The trophy's and the plinth's footprints as axis-aligned (x0, x1, y0, y1) rectangles in the world (the cup's own bounds rotated by
    its yaw, then boxed)."""
    mesh = mesh or TROPHY_MESH
    s, yaw = spec["scale"], math.radians(spec["yaw"])

    def boxed(corners):
        xs, ys = [p[0] for p in corners], [p[1] for p in corners]
        return min(xs), max(xs), min(ys), max(ys)

    corners = []
    for ax in (mesh["min"][0], mesh["max"][0]):
        for ay in (mesh["min"][1], mesh["max"][1]):
            lx, ly = ax * s, ay * s
            corners.append((spec["x"] + lx * math.cos(yaw) - ly * math.sin(yaw), spec["y"] + lx * math.sin(yaw) + ly * math.cos(yaw)))
    if spec["plinth"] is None:                              # on the podium: the cup's box is all there is
        return {"cup": boxed(corners)}
    pl = spec["plinth"]["size"]
    return {"cup": boxed(corners),
            "plinth": (spec["x"] - pl[0] / 2, spec["x"] + pl[0] / 2, spec["y"] - pl[1] / 2, spec["y"] + pl[1] / 2)}


# ---------------------------------------------------------------- editor helpers
SCENE, ACTOR, OBJ, ASSETS = c.SCENE, c.ACTOR, c.OBJ, c.ASSETS


def found(tag=TAG):
    r = u.call(SCENE, "find_actors", {"tag": tag, "collision_channels": []})
    return [a for a in (r if isinstance(r, list) else r.get("returnValue", [])) if isinstance(a, dict)]


def tagged(actor, label):
    u.call(ACTOR, "add_tag", {"actor": c.ref(actor), "tag": TAG})
    u.call(ACTOR, "set_label", {"actor": c.ref(actor), "label": label})
    return actor


def get(obj, keys):
    return json.loads(u.call(OBJ, "get_properties", {"instance": c.ref(obj), "properties": keys})["returnValue"])


def set_each(obj, values):
    """One key per set_properties call, each read back; returns {key: value read} for the ones that did not take."""
    bad = {}
    for k, v in values.items():
        u.call(OBJ, "set_properties", {"instance": c.ref(obj), "values": json.dumps({k: v})})
        got = get(obj, [k]).get(k)
        if got != v:
            bad[k] = got
    return bad


def far_settings(actor, component):
    """Always loaded, never distance-culled, no shadows: the volcano and the titan are seen from 2 km. Stops on a refused key."""
    if not FAR:
        return
    bad = {**set_each(actor, FAR_ACTOR), **set_each(component, FAR_COMPONENT)}
    if bad:
        sys.exit(f"far-art settings did not take on {actor}: {bad}")


def place_mesh(path, spec, scale=None):
    sx, sy, sz = (spec["sx"], spec["sy"], spec["sz"]) if scale is None else scale
    r = u.call(SCENE, "add_to_scene_from_asset", {"asset_path": path, "name": spec["label"],
                                                  "xform": c.xform(spec["x"], spec["y"], spec["z"], sx, sy, sz, spec["yaw"])})
    return tagged(r["returnValue"]["refPath"], spec["label"])


def place_titan(project, spec):
    import build_bossmode as b
    r = u.call(c.DEV, "PlaceDevice", {"assetPath": c.ref(ANIMATED_MESH), "transform": c.xform(
        spec["x"], spec["y"], spec["z"], spec["scale"], spec["scale"], spec["scale"], spec["yaw"])})
    actor = tagged(r["returnValue"]["refPath"], spec["label"])
    c.props(actor, b.titan_clip_props(project, "idle"))
    c.props(actor, {"bNoCollision": True, "bCanBeDamaged": False})
    far_settings(actor, actor + ".SkeletalMeshComponent")
    got = get(actor, ["animation", "loop", "initialState"])
    if not got.get("animation", {}).get("refPath", "").endswith("A_fnm_titan_idle"):
        sys.exit(f"{spec['label']}: animation did not take ({got}); run tools/import_boss.py")
    return actor


def build(titan=True, far=True, on_podium=False):
    global FAR
    FAR = far
    project = c.project_mount().strip("/")
    for name in il.MESHES:
        sub, sm = il.MESHES[name]
        if not c.exists(f"/{project}/{il.ART}/{sub}/{sm}"):
            sys.exit(f"{sm} is not imported: run python tools/import_landmarks.py")
    gone = remove()
    print("removed", gone, "old landmark actors")
    course = d.course()
    v = volcano_spec(course)
    actor = place_mesh(il.mesh_path(project, "volcano"), v)
    c.props(actor, GHOST)
    far_settings(actor, actor + ".StaticMeshComponent0")
    print(f"volcano at ({v['x']:.0f}, {v['y']:.0f}, {v['z']:.0f}) scale {v['sx']:.1f} x {v['sy']:.1f} x {v['sz']:.1f}: peak {v['peak_z'] / 100:.0f} m "
          f"({peak_degrees(v, eye(course)):.1f} deg from station 1), {2 * v['half_width'] / 100:.0f} m wide")
    if titan:
        t = titan_spec(course, v)
        place_titan(project, t)
        print(f"titan on the rim at ({t['x']:.0f}, {t['y']:.0f}, {t['z']:.0f}) scale {t['scale']:.0f} yaw {t['yaw']:.1f}")
    if on_podium:
        import build_titanpeak as tp
        tr = trophy_spec(course, podium=tp.podium_spec(course))
    else:
        tr = trophy_spec(course)
    pl = tr["plinth"]
    if pl:
        plinth = place_mesh(CUBE, pl, scale=(pl["size"][0] / 100, pl["size"][1] / 100, pl["size"][2] / 100))
        c.props(plinth + ".StaticMeshComponent0", {"overrideMaterials": [c.ref(f"/{project}/FNM_Art/{MARBLE}.{MARBLE}")]})
        c.props(plinth, GHOST)
    cup = place_mesh(il.mesh_path(project, "trophy"), tr, scale=(tr["scale"],) * 3)
    c.props(cup, GHOST)
    print(f"trophy at ({tr['x']:.0f}, {tr['y']:.0f}, {tr['z']:.0f}) scale {tr['scale']} yaw {tr['yaw']:.1f} " +
          (f"on a {pl['size']} plinth" if pl else "on the champions' podium's top step"))
    u.call(ASSETS, "save_assets", {"asset_paths": []})


def remove():
    actors = found()
    for a in actors:
        u.call(SCENE, "remove_from_scene", {"actor": c.ref(a["actorPath"])})
    return len(actors)


def check():
    actors = sorted(found(), key=lambda a: a.get("label", ""))
    print(len(actors), "landmark actors")
    for a in actors:
        bd = a.get("bounds", {})
        lo, hi = bd.get("min", {}), bd.get("max", {})
        print(f"  {a.get('label', ''):26} ({lo.get('x', 0):.0f}, {lo.get('y', 0):.0f}, {lo.get('z', 0):.0f}) .. "
              f"({hi.get('x', 0):.0f}, {hi.get('y', 0):.0f}, {hi.get('z', 0):.0f})")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--remove", action="store_true", help="remove every landmark actor and stop")
    ap.add_argument("--check", action="store_true", help="list what is placed")
    ap.add_argument("--no-titan", action="store_true", help="volcano and trophy only")
    ap.add_argument("--on-podium", action="store_true", help="the trophy on the champions' podium (tools/build_titanpeak.py), no plinth")
    ap.add_argument("--probe-no-far", action="store_true",
                    help="TEST ONLY: skip the far-art settings (the disproof: does the volcano vanish in play without them?)")
    args = ap.parse_args()
    if args.remove:
        print("removed", remove(), "landmark actors")
        u.call(ASSETS, "save_assets", {"asset_paths": []})
    elif args.check:
        check()
    else:
        build(titan=not args.no_titan, far=not args.probe_no_far, on_podium=args.on_podium)
