"""Glass ceilings over the whole course in the open UEFN project through UEFN MCP.

Aaron (2026-10-06): "add a ceiling with collision so players can't launch out and over" (Shockwave Grenades from the
pickup pads clear the 6 m walls), "maybe transparent". Every floor piece of the course (station hallways with their
vestibules, the finish hallway, each connector's funnel, flare and corridor segments, and each staircase as one sloped
sheet) gets a matching lid of Creative glass-gallery glass whose underside sits flush with the wall tops (WALL_H):
the course becomes a closed glass-topped tube, the sky and the floating digits stay visible, and nothing can be
jumped out of or into. The director's skip guard (WatchSkip) stays as the backstop.

Reads geometry from the course actors (tools/build_course.py: every cube is placed centred, scale X along its
heading), so rerun after a course rebuild. Idempotent: every actor this script creates is tagged TAG; a run first
deletes everything with TAG.

    python tools/build_lids.py
"""
import json
import math
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import uefn_mcp as u  # noqa: E402
from build_course import ACTOR, CUBE, OBJ, SCENE, TAG as COURSE_TAG, WALL_H, clear, ref  # noqa: E402

TAG = "fnm_lids"
GLASS = "/Game/Creative/Environments/Meshes/Glass/Materials/Glass_version_02/MI_CP_GlassGallery.MI_CP_GlassGallery"
LID_T = 40              # lid thickness (cm)
SINK = 20               # the lid's underside sits this far down into the wall tops, so there is no seam to slip through
# Course floor pieces: a connector's pieces carry the prefix of the station it leads INTO (build_course.connector);
# the boss arena (FNM_Arena_Floor) and the connector into it (FNM_Arena_FloorC1 ...) are lidded like a station.
PIECE = re.compile(r"^(FNM_(?:S\d\d|Finish|Arena))_(Floor|FloorFunnel|FloorFlare|FloorC\d+|Step(\d+)_(\d+))$")


def build():
    print("removed", clear(TAG), "old lids")
    found = u.call(SCENE, "find_actors", {"tag": COURSE_TAG, "collision_channels": []})["returnValue"]
    flats, stairs = [], {}
    for a in found:
        m = PIECE.match(a.get("label", "")) if isinstance(a, dict) else None
        if not m:
            continue
        t = u.call(ACTOR, "get_actor_transform", {"actor": ref(a["actorPath"])})["returnValue"]
        piece = (m.group(1), m.group(2), t)
        if m.group(3):
            stairs.setdefault((m.group(1), int(m.group(3))), []).append((int(m.group(4)), t))
        else:
            flats.append(piece)
    n = 0
    for prefix, kind, t in flats:
        loc, s = t["location"], t["scale"]
        top = loc["z"] + s["z"] * 50                 # a 1 m engine cube, centred
        lid(f"{prefix}_Lid{kind}", loc["x"], loc["y"], top, s["x"], s["y"], t["rotation"]["yaw"], 0.0)
        n += 1
    for (prefix, seg), steps in stairs.items():
        steps.sort()
        (_, first), (_, last) = steps[0], steps[-1]
        f, l = first["location"], last["location"]
        top0 = f["z"] + first["scale"]["z"] * 50
        top1 = l["z"] + last["scale"]["z"] * 50
        tread = first["scale"]["x"] * 100            # scale X runs along the heading
        run = math.hypot(l["x"] - f["x"], l["y"] - f["y"])
        rise = top1 - top0
        pitch = math.degrees(math.atan2(rise, run))  # + pitch lifts the heading end (stairs up); - for stairs down
        length = math.hypot(run + tread, rise)
        lid(f"{prefix}_LidStairs{seg}", (f["x"] + l["x"]) / 2, (f["y"] + l["y"]) / 2, (top0 + top1) / 2,
            length / 100, first["scale"]["y"], first["rotation"]["yaw"], pitch)
        n += 1
        print(f"{prefix} stairs {seg}: {len(steps)} steps, rise {rise:.0f} over {run:.0f}, pitch {pitch:.1f} deg")
    print(f"{n} lids placed ({len(flats)} flat, {len(stairs)} sloped), glass {GLASS.rsplit('.', 1)[1]}")


def lid(label, cx, cy, floor_top, sx, sy, yaw, pitch):
    """A glass slab the footprint of a floor piece, its underside SINK below the wall tops above that floor."""
    cz = floor_top - 2 + WALL_H - SINK + LID_T / 2   # the floor's top is 2 cm above its level oz; walls end at oz + WALL_H
    r = u.call(SCENE, "add_to_scene_from_asset", {
        "asset_path": CUBE, "name": label,
        "xform": {"location": {"x": cx, "y": cy, "z": cz}, "rotation": {"pitch": pitch, "yaw": yaw, "roll": 0},
                  "scale": {"x": sx, "y": sy, "z": LID_T / 100}}})
    actor = r["returnValue"]["refPath"]
    u.call(ACTOR, "add_tag", {"actor": ref(actor), "tag": TAG})
    u.call(ACTOR, "set_label", {"actor": ref(actor), "label": label})
    comp = json.loads(u.call(OBJ, "get_properties", {"instance": ref(actor), "properties": ["staticMeshComponent"]})["returnValue"])
    u.call(OBJ, "set_properties", {"instance": comp["staticMeshComponent"], "values": json.dumps({"overrideMaterials": [ref(GLASS)]})})
    return actor


if __name__ == "__main__":
    build()
