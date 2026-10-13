"""Volt, the robot host, in the world: two Animated Mesh devices (actor tag `fnm_mascot`, labels FNM_Mascot_*), one waving beside
station 1's start and one dancing beside the victory area's podium. Idempotent (removes its own actors by tag, then places).
Geometry is read from the course actors' bounds the way tools/build_finish.py does (station 1's floor and walls; the finish
hall's walls, end wall and floor), so it survives a course rebuild and a changed hall length; rerun it after one.

    python tools/build_mascot.py                    # both
    python tools/build_mascot.py --clear            # remove Volt
    python tools/build_mascot.py --start-clip wave --podium-clip dance
    python tools/build_mascot.py --probe            # both, plus a TEMPORARY row of the other clips in the start hall (test only)

Needs `python tools/import_mascot.py` once per UEFN project (FNM_MascotArt: one mesh, one animation per clip). Each device
plays ONE clip, looping from the session start (the Animated Mesh device's Verse API is only Play / Pause / PlayReverse and
Play() never started a device placed Stopped: BOSS_MODE 15b), so a later director that wants Volt to do something else (wag
a finger at a wrong door, cheer a streak) places one more looping device per clip, parked and shrunk like the titan's, and
swaps them with TeleportTo. This builder places only what is on screen now. No Verse tag: the director does not drive them
yet (a tag class would be a Verse change), so the editor tag is the only handle.

BUILD NOTES (measured and seen, 2026-10-13)
- SK_fnm_volt is 150 cm tall with its origin at the feet, and faces +X at yaw 0 (the titan's mesh did the same, and the
  titan's builder turns it the same way: yaw = atan2(dy, dx) toward what it faces).
- Start: where the director stands a player who joins (station 1's entry teleporter, then ArrivalForward 300 cm past it,
  facing +Y), Volt is START_DY ahead of the hall's start and START_DX to the player's right, off the running line and well
  out of the straight line between the spawn and the door wall, turned toward the spawn. The player's right, because the
  left wall carries the STATION 1 sign.
- Seen in play (2026-10-13, frames in the report): the start Volt waves upright at the right of the first frame, facing the
  player, clear of the picker menu and the question panel; the podium Volt dances upright at the left of the arrival frame,
  clear of RACE AGAIN, the lecterns and the board text. Collision: the device has pawn collision on by default; GHOST sets its
  bNoCollision flag (read back true) but blocking was NOT tried in play (no keys allowed).
- Podium: where PodiumLater stands a finisher (centred between the two lecterns, PodiumStandOff in front of RACE AGAIN's
  button, facing +Y, the orbit camera 900 cm behind), Volt stands past the lecterns beside the board, on the RACE AGAIN
  side, clear of the label, the flowers and the wall torches, turned toward that spot.
"""
import argparse
import json
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import build_course as c  # noqa: E402
import build_decor as d  # noqa: E402
import build_finish as f  # noqa: E402
import import_mascot as im  # noqa: E402
import uefn_mcp as u  # noqa: E402

TAG = "fnm_mascot"
ANIMATED_MESH = "/CRD_AnimatedMesh/Device_AnimatedMesh.Device_AnimatedMesh_C"
MESH_HEIGHT = 150.0           # SK_fnm_volt, feet at the origin (import_mascot prints the bounds)
FACING_YAW = 0.0              # the world yaw at which the mesh faces +X (it does: seen in the editor)

# Nobody should bump into the host or shoot him: a Creative device's own collision flag (bNoCollision, settable from MCP, read
# back true) and no damage (build_island does the same to the gallery props). Whether play honours it is checked in play.
GHOST = {"bNoCollision": True, "bCanBeDamaged": False}

START_CLIP = "wave"           # Meshy Big Wave Hello (28)
PODIUM_CLIP = "ymca"          # Meshy YMCA Dance (596); `dance` (Funny Dancing 1) if it misplays
START_HEIGHT = 270.0          # cm: a 3 m robot beside a 1.8 m player reads as a host without towering over the hall
PODIUM_HEIGHT = 300.0
# Station 1 start: the director lands a player ENTRY_Y + ARRIVAL_FORWARD past the hall's first edge, facing +Y.
ENTRY_Y = 150.0               # build_course.station: the entry teleporter's offset from the hallway start
ARRIVAL_FORWARD = 300.0       # the director's ArrivalForward
START_DX = 500.0              # cm to the player's right (-X) of the running line (560 put his legs behind the game's "x 50" ammo
#                               widget at the right of a 1080p frame, seen in play 2026-10-13; the HUD is not ours to move)
START_DY = 1130.0             # cm up the hall from its first edge (the player stands at 450)
# Podium: the director's PodiumStandOff, and the finish rig's own offsets (build_finish).
PODIUM_STAND_OFF = 350.0
BUTTON_OFFSET = 20.0          # build_finish.board: the buttons stand this far in front of their lectern's y
VOLT_DX = 690.0               # cm from the hall's centre line toward RACE AGAIN (+X, the player's left)
VOLT_BACK = 480.0             # cm in front of the end wall: past the lecterns (600) and clear of the board's feet


def hall(course, prefix):
    """(cx, y0, y_end, z) of a hall from its course actors: the walls' inner faces, the floor's first edge and top, and
    (finish only) the end wall's inner face. `prefix` is 'FNM_S01' or 'FNM_Finish'."""
    wl, wr, floor = (course[f"{prefix}_{n}"] for n in ("WallL", "WallR", "Floor"))
    left, right = wl["min"]["x"], wr["max"]["x"]
    end = course[f"{prefix}_WallEnd"]["min"]["y"] if f"{prefix}_WallEnd" in course else None
    return (left + right) / 2, floor["min"]["y"], end, floor["max"]["z"]


def face(x, y, tx, ty):
    """World yaw for a mesh at (x, y) to face (tx, ty)."""
    return math.degrees(math.atan2(ty - y, tx - x)) + FACING_YAW


def start_spec(course, clip=START_CLIP):
    """Volt at the start: (x, y, z, yaw, scale, clip), and the player's spawn spot he faces."""
    cx, y0, _, z = hall(course, "FNM_S01")
    spawn = (cx, y0 + ENTRY_Y + ARRIVAL_FORWARD)
    x, y = cx - START_DX, y0 + START_DY
    return {"label": "FNM_Mascot_Start", "x": x, "y": y, "z": z, "yaw": face(x, y, *spawn),
            "scale": START_HEIGHT / MESH_HEIGHT, "clip": clip, "faces": spawn}


def podium_stand(course):
    """Where the director stands a finisher (fnm_director PodiumSpot): between the lecterns, PodiumStandOff in front of the
    RACE AGAIN button, never nearer than ArrivalForward past the finish entry teleporter."""
    cx, y0, end, _ = hall(course, "FNM_Finish")
    button_y = end - f.PODIUM_BACK - BUTTON_OFFSET
    return cx, max(button_y - PODIUM_STAND_OFF, y0 + ENTRY_Y + ARRIVAL_FORWARD)


def podium_spec(course, clip=PODIUM_CLIP):
    """Volt at the podium: beside the board on the RACE AGAIN side, turned toward the finisher's spot."""
    cx, _, end, z = hall(course, "FNM_Finish")
    stand = podium_stand(course)
    x, y = cx + VOLT_DX, end - VOLT_BACK
    return {"label": "FNM_Mascot_Podium", "x": x, "y": y, "z": z, "yaw": face(x, y, *stand),
            "scale": PODIUM_HEIGHT / MESH_HEIGHT, "clip": clip, "faces": stand}


def device_props(project, clip, own=im.OWN_MESH):
    """The Animated Mesh device's settings for one clip: the shared mesh and its animation, Playing from the start,
    looping (like the titan's clips: build_bossmode.titan_clip_props)."""
    if clip not in im.CLIPS:
        raise ValueError(f"unknown clip {clip!r}; imported clips: {sorted(im.CLIPS)}")
    return {"skeletalMesh": {"refPath": im.mesh_path(project, clip, own)},
            "animation": {"refPath": im.anim_path(project, clip, own)},
            "loop": True, "initialState": "Playing"}


def place(project, spec):
    r = u.call(c.DEV, "PlaceDevice", {"assetPath": c.ref(ANIMATED_MESH),
                                      "transform": c.xform(spec["x"], spec["y"], spec["z"], spec["scale"], spec["scale"],
                                                           spec["scale"], spec["yaw"])})
    actor = r["returnValue"]["refPath"]
    u.call(c.ACTOR, "add_tag", {"actor": c.ref(actor), "tag": TAG})
    u.call(c.ACTOR, "set_label", {"actor": c.ref(actor), "label": spec["label"]})
    c.props(actor, device_props(project, spec["clip"]))
    c.props(actor, GHOST)
    got = json.loads(u.call(c.OBJ, "get_properties", {"instance": c.ref(actor),
                                                       "properties": ["skeletalMesh", "animation", "loop", "initialState"]})["returnValue"])
    if not (got.get("animation") or {}).get("refPath", "").endswith(f"A_fnm_volt_{spec['clip']}"):
        sys.exit(f"{spec['label']}: animation did not take ({got}); run tools/import_mascot.py")
    flags = json.loads(u.call(c.OBJ, "get_properties", {"instance": c.ref(actor), "properties": list(GHOST)})["returnValue"])
    if flags != GHOST:
        sys.exit(f"{spec['label']}: collision/damage flags did not take ({flags})")
    print(f"{spec['label']}: clip {spec['clip']} at ({spec['x']:.0f}, {spec['y']:.0f}, {spec['z']:.0f}) yaw {spec['yaw']:.1f} "
          f"scale {spec['scale']:.2f} ({spec['scale'] * MESH_HEIGHT:.0f} cm), faces {spec['faces'][0]:.0f}, {spec['faces'][1]:.0f}")
    return actor


def probe_specs(course, clips=None, scale=1.6, back=1700.0, step=340.0):
    """A row of clips (default: every clip the two real Volts do not play) in the start hall `back` cm up from its first edge,
    `step` apart, so a play session can sample each one on the shared skeleton while the player stands at the spawn
    (`--probe`; test only, tagged like the real ones, so the next normal build removes it)."""
    cx, y0, _, z = hall(course, "FNM_S01")
    clips = clips or [k for k in im.CLIPS if k not in (START_CLIP, PODIUM_CLIP)]
    spawn = (cx, y0 + ENTRY_Y + ARRIVAL_FORWARD)
    out = []
    for i, clip in enumerate(clips):
        x, y = cx + (i - (len(clips) - 1) / 2) * step, y0 + back
        out.append({"label": f"FNM_Mascot_Probe_{clip}", "x": x, "y": y, "z": z, "yaw": face(x, y, *spawn),
                    "scale": scale, "clip": clip, "faces": spawn})
    return out


def build(start_clip=START_CLIP, podium_clip=PODIUM_CLIP, probe=False, **probe_args):
    print("removed", c.clear(TAG), "old mascot actors")
    project = c.project_mount().strip("/")
    course = d.course()
    specs = [start_spec(course, start_clip), podium_spec(course, podium_clip)]
    for spec in specs + (probe_specs(course, **probe_args) if probe else []):
        place(project, spec)


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--clear", action="store_true", help="remove Volt and stop")
    ap.add_argument("--probe", action="store_true", help="also place a temporary row of the other clips (test only)")
    ap.add_argument("--probe-clips", default="", help="with --probe: comma list instead of every unused clip")
    ap.add_argument("--probe-scale", type=float, default=1.6)
    ap.add_argument("--probe-back", type=float, default=1700.0, help="cm up the hall from its first edge")
    ap.add_argument("--probe-step", type=float, default=340.0, help="cm between probes")
    ap.add_argument("--start-clip", default=START_CLIP)
    ap.add_argument("--podium-clip", default=PODIUM_CLIP)
    args = ap.parse_args()
    for clip in (args.start_clip, args.podium_clip):
        if clip not in im.CLIPS:
            sys.exit(f"unknown clip {clip}; known: {sorted(im.CLIPS)}")
    if args.clear:
        print("removed", c.clear(TAG), "mascot actors")
    else:
        build(args.start_clip, args.podium_clip, args.probe, clips=[x for x in args.probe_clips.split(",") if x] or None,
              scale=args.probe_scale, back=args.probe_back, step=args.probe_step)
        u.call(c.ASSETS, "save_assets", {"asset_paths": []})
