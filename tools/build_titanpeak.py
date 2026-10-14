"""Titan Peak dressing (G9 "Titan Peak", reviews/race-2026-10-13/sources/spectacle.md section 3): the start gate, the champions'
podium, the tier set pieces and the place banners, placed in the open UEFN project through UEFN MCP. Every actor carries the
tag `fnm_titanpeak` and its part's tag (`fnm_titanpeak_gate`, `_podium`, `_set`, `_banners`) and a label FNM_TP_*.

    python tools/build_titanpeak.py                      # all four parts (idempotent: each part removes its own actors first)
    python tools/build_titanpeak.py --part gate          # one part: gate | podium | set | banners
    python tools/build_titanpeak.py --remove [--part X]  # take them out (everything with the tag, or one part)
    python tools/build_titanpeak.py --check              # read-only: what is placed, with bounds
    python tools/build_titanpeak.py --verify             # read-only: every placed actor's bounds against what the plan says (3 cm)
    python tools/build_titanpeak.py --plan               # read-only: every placement the live course would get

The art is T1's (tools/import_titanpeak.py, content folder FNM_TitanPeakArt): meshes SM_fnm_tp_<gate|podium|jungle_pillar|
river_boulders|ice_crystals|obsidian_spire|lava_vent|rune_stone>, banner quads SM_fnm_tp_banner_<key> (a 400 cm wide quad,
pivot at its bottom centre, readable from -Y at yaw 0, collision removed). This file places them and nothing else.

Geometry is read from the course actors (labels FNM_Sxx_Floor / WallL / WallR / Lintel and the obstacles, the arena and finish
halls), never assumed, the way tools/build_finish.py does, so a course rebuild only needs a rerun of this file. One exception:
the actors of a winding or stepped connector are yawed boxes whose bounds give no inner face, so `connector_strips` replays
tools/build_course.py's own recurrence (CONNECTORS, FUNNEL, CONN_W) from the end of the hall before it, and the tests assert that
it lands on the next hall's first edge.

THE RULES EVERY PLACEMENT FOLLOWS (tests/test_titanpeak.py checks them on the course's own numbers; `conflicts` is the checker)
- Nothing blocks the running line, a doorway, a vestibule trigger, a pickup pad, a speed plate or the view of the doors. Set pieces
  stand in a strip along a wall (a hall's outer 466 cm, a connector's outer 200 cm). In a hall: never before s = SIGN_ZONE (the
  arrival corner, the pickup pads at s 480-780, the STATION sign and the chalkboard), never within DOOR_ZONE of the door wall,
  never where they would hide a door panel from the arrival spot, never over a hurdle, baffle or slider and its margin, and (a
  tall one) never under a wall torch. In a connector: only on flat segments, away from the speed plates and the joints.
- Banners hang above the walls' tops, out of reach of anyone walking or jumping.
- Deterministic: a seed per strip (SEED), so a rerun reproduces every actor.

THE PARTS
- gate: the "Base Camp" log gate across station 1's first stretch, its opening centred on the spawn line. The player lands at
  (cx, y0 + 450), the camera 350 behind; the gate stands GATE_AHEAD past the hall's first edge, beyond Volt (build_mascot) and below
  the volcano's peak (build_landmarks), so the course, Volt and the peak are seen through and over it. The BASE CAMP banner quad is
  laid on its sign board.
- podium: the champions' podium in the victory area on the NEW SKILL side, where the trophy's plinth was, turned to the finisher's
  spot; Volt dances on the other side. Clear of both lecterns, their labels, the all-time board, Volt and the flowers. HALL OF
  CHAMPIONS floats above it.
- set: tier set pieces, 2-3 per station hallway and 1-2 per flat segment of a connector: t1 jungle_pillar, t2 river_boulders, t3
  ice_crystals, t4 obsidian_spire, t5 lava_vent (the tier of the hall a connector leads into, as build_course.paint_key), plus a
  rune stone per tier. The arena and the finish hall get none (the boss rig and the victory rig own them).
- banners: each tier's name over the entrance of its first station (tier 1's is the gate's own), TITAN'S FORGE over the arena
  entrance, HALL OF CHAMPIONS over the podium: floating, bottom edge BANNER_Z above the floor, front to the runner.

COLLISION. Every prop import came with ONE convex hull round its whole bounding box (read 2026-10-13: 32 vertices, the gate's spans
10.5 x 6.9 x 6 m with the opening inside it, so a player could not have run through the gate), and a NoCollision flag set on a placed
mesh actor in the editor does not hold in play (uefn-mcp skill, door signs 2026-10-08). So `strip_collision` removes the collision
SHAPES from each mesh asset a part places (StaticMeshTools.remove_collisions, read back, saved): nothing of the dressing can be bumped,
blocked on or caught by the camera, and no flag has to hold. The banner quads were imported without any. GHOST is still written to
the actors as a hint.
"""
import argparse
import json
import math
import random
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import build_course as c  # noqa: E402
import build_decor as d  # noqa: E402
import build_mascot as mascot  # noqa: E402
import uefn_mcp as u  # noqa: E402

TAG = "fnm_titanpeak"
PARTS = ("gate", "podium", "set", "banners")
ART = "FNM_TitanPeakArt"          # tools/import_titanpeak.py (T1)
SEED = 20261013
SCENE, ACTOR, OBJ, ASSETS = c.SCENE, c.ACTOR, c.OBJ, c.ASSETS
STATIC = "editor_toolset.toolsets.static_mesh.StaticMeshTools"
GHOST = {"bNoCollision": True, "bCanBeDamaged": False}
GHOST_TRY = [True]         # emptied the first time the editor refuses GHOST on a placed mesh actor


def part_tag(part):
    return f"{TAG}_{part}"


# ---------------------------------------------------------------- the meshes
# Bounds at scale 1 in UE cm, centred on the origin (Meshy normalises each to ~1.9 m on its longest side): (min, max) per UE axis.
# READ from the imported assets (StaticMeshTools.get_bounds, 2026-10-13): UE x = glTF z (the depth), UE y = glTF x (the width), UE z =
# glTF y (the height), so Meshy's front (glTF +Z) points along +X, like the skeletal meshes (the titan, Volt). `--meshes` re-reads them.
MESH = {
    "gate": ((-63.0, -95.1, -54.8), (62.8, 95.1, 54.5)),
    "podium": ((-36.2, -95.1, -53.8), (36.1, 95.2, 53.5)),
    "jungle_pillar": ((-58.8, -68.8, -95.1), (56.6, 69.0, 94.5)),
    "river_boulders": ((-88.7, -94.2, -41.1), (88.7, 95.0, 40.5)),
    "ice_crystals": ((-89.7, -92.0, -95.2), (89.7, 93.4, 94.8)),
    "obsidian_spire": ((-48.9, -47.0, -95.1), (48.1, 47.6, 94.7)),
    "lava_vent": ((-95.1, -94.4, -38.6), (94.7, 94.6, 38.2)),
    "rune_stone": ((-66.9, -73.7, -95.0), (66.3, 74.3, 94.7)),
}
# The world heading (degrees from +X, counter-clockwise seen from above) a mesh's FRONT faces at yaw 0: the gate's sign board with the
# braziers at its feet, the podium's framed panels, the rune stone's glyph. Meshy's front is glTF +Z = UE +X (above): heading 0.
# A rotationally plain piece (boulders, vent, crystals, pillar, spire) does not care. Confirmed by an editor capture of the placed
# gate and podium (see the report), not only by the bounds.
FRONT0 = {"gate": 0.0, "podium": 0.0, "jungle_pillar": 0.0, "river_boulders": 0.0, "ice_crystals": 0.0,
          "obsidian_spire": 0.0, "lava_vent": 0.0, "rune_stone": 0.0}
SINK = 3.0                         # cm: a piece's foot goes this far into the floor so no seam shows

TIER_MESH = {1: "jungle_pillar", 2: "river_boulders", 3: "ice_crystals", 4: "obsidian_spire", 5: "lava_vent"}
SET_MESHES = tuple(TIER_MESH.values()) + ("rune_stone",)


def asset_name(mesh):
    return f"SM_fnm_tp_{mesh}"


def size(mesh):
    """(x extent, y extent, height) of a mesh at scale 1: its depth (front to back), its width, its height."""
    lo, hi = MESH[mesh]
    return hi[0] - lo[0], hi[1] - lo[1], hi[2] - lo[2]


def rest_z(mesh, scale, floor_z):
    """Actor z that stands the mesh on floor_z (its bottom SINK below it)."""
    return floor_z - MESH[mesh][0][2] * scale - SINK


def half_extents(mesh, scale, yaw):
    """Half x / half y of the world axis-aligned box round the mesh at `scale` turned `yaw` degrees."""
    dx, dy, _ = size(mesh)
    t = math.radians(yaw)
    cs, sn = abs(math.cos(t)), abs(math.sin(t))
    return scale * (dx * cs + dy * sn) / 2, scale * (dx * sn + dy * cs) / 2


def across_along(mesh, scale, rel_yaw):
    """Half extents (across, along) of a mesh whose x axis points rel_yaw degrees off a strip's heading: the box in the strip's axes
    (across = lateral, along = lengthwise)."""
    along, across = half_extents(mesh, scale, rel_yaw)
    return across, along


def yaw_facing(mesh, heading_deg):
    """Actor yaw that turns the mesh's front to world heading `heading_deg` (degrees from +X)."""
    return heading_deg - FRONT0[mesh]


def heading(x, y, tx, ty):
    return math.degrees(math.atan2(ty - y, tx - x))


# ---------------------------------------------------------------- the course, from its actors
def halls(course):
    """{k: hall} for every FNM_Sxx station hallway: cx, half (inner half width), left/right (inner wall faces; +X is the player's
    left), y0 (first edge), y_end (end of the vestibules), door_y (door wall centre), door_face (the lintel's runner side), z
    (floor top), wall (wall height)."""
    out = {}
    for label in course:
        m = re.fullmatch(r"FNM_S(\d\d)_Floor", label)
        if not m:
            continue
        k, p = int(m[1]), f"FNM_S{int(m[1]):02d}"
        fl, wl, wr, li = course[f"{p}_Floor"], course[f"{p}_WallL"], course[f"{p}_WallR"], course[f"{p}_Lintel"]
        left, right = wl["min"]["x"], wr["max"]["x"]
        out[k] = {"k": k, "cx": (left + right) / 2, "half": (left - right) / 2, "left": left, "right": right,
                  "y0": wl["min"]["y"], "y_end": wl["max"]["y"], "door_y": (li["min"]["y"] + li["max"]["y"]) / 2,
                  "door_face": li["min"]["y"], "z": fl["max"]["z"], "wall": wl["max"]["z"] - wl["min"]["z"]}
    return out


def special_hall(course, prefix):
    """The arena's or the finish hall's frame: cx, half, left/right, y0, y_end (the end wall's inner face when it has one, else the
    walls' end), z (floor top), wall (height)."""
    fl, wl, wr = (course[f"{prefix}_{n}"] for n in ("Floor", "WallL", "WallR"))
    left, right = wl["min"]["x"], wr["max"]["x"]
    end = course[f"{prefix}_WallEnd"]["min"]["y"] if f"{prefix}_WallEnd" in course else wl["max"]["y"]
    return {"cx": (left + right) / 2, "half": (left - right) / 2, "left": left, "right": right, "y0": wl["min"]["y"],
            "y_end": end, "z": fl["max"]["z"], "wall": wl["max"]["z"] - wl["min"]["z"]}


def tier_of(k, stations, tiers):
    return c.auto_tier(k, stations, tiers)


def obstacles(course, k, hall=None):
    """[(kind, y0, y1, side)] of station k's hurdles, baffles and sliders, from their actors' bounds. `side` is the wall a baffle
    hangs from (+1 the player's left, -1 right; 0 for the others): its other end is the open gap."""
    hall = hall or halls(course)[k]
    out = []
    for label, b in course.items():
        m = re.fullmatch(rf"FNM_S{k:02d}_(Hurdle|Baffle|Slider)[lr]?\d+", label)
        if m:
            side = 0
            if m[1] == "Baffle":
                side = 1 if b["max"]["x"] >= hall["left"] - 5 else -1
            out.append((m[1].lower(), b["min"]["y"], b["max"]["y"], side))
    return sorted(out, key=lambda o: o[1])


# ---------------------------------------------------------------- set pieces: strips along walls
LANE_HALL = 640.0          # a hall piece's inner edge stays this far from the hall's centre line (the straight line from the spawn to door A is x < 560 until y0 + 2100)
LANE_CONN = 200.0          # a connector's clear centre half width (4 m of its 10 m; the plates sit between the pieces in s)
EDGE = 25.0                # gap between a piece and the wall it stands against
SIGN_ZONE = 1050.0         # the hall's first stretch: arrival corner, pickup pads (s 480-780), STATION sign and chalkboard (y0 + 242 .. 958)
DOOR_ZONE = 800.0          # nothing this near the door wall, and (SIGHT_EYE) nothing that hides a door panel from the arrival spot
SIGHT_EYE = 450.0          # the arrival spot's s: the entry teleporter's 150 + the director's ArrivalForward 300
MARGIN = {"hurdle": 60.0, "baffle": 60.0, "slider": 120.0}   # beyond an obstacle's own extent along the hall
GAP_SIDE_MARGIN = 260.0    # a baffle's open side: a piece there would narrow the 900 cm gap, so it keeps this far from the baffle
TORCH_S = (1250.0, 2000.0, 2750.0)   # the wall torches (build_decor.TORCH_YS; the 500 one is skipped for the sign and chalkboard)
TORCH_CLEAR = 320.0        # a piece lower than this fits under a torch bracket (z 400); a taller one keeps a torch's s clear
GAP = 250.0                # between two pieces along one wall
PLATE_HALF = 450.0         # a speed plate is (CONN_W - 100) square, centred on its fraction
PLATE_MARGIN = 100.0
JOINT = 250.0              # a connector piece keeps this far from a segment's ends (the walls mitre there)
MIN_STRIP = 200.0          # a flat segment shorter than 2 * JOINT + this carries no strip (the 300 and 400 cm landings round a staircase)
GATE_KEEP = 150.0          # cm of bare wall either side of the camp gate's box
VOLT_S1 = (880.0, 1380.0)  # station 1: Volt's stretch (START_DY 1130 from the first edge): the right wall, his side, stays empty from s 880 on
SMALLEST = 0.5             # a piece may be this fraction of its range's low end when the stretch is short
# Scale ranges (editor frames 2026-10-13: the first draw, 1.5-2.6, read small against a 6 m wall): a pillar 4-6 m tall, crystals 3.6-5 m,
# a spire 6-7.6 m (it clears the wall top: a skyline), boulders and vents low and 4-5 m wide, a rune stone 3.8-4.9 m. The fit still cuts
# any piece back to the wall band, so the biggest only appear where there is room.
SCALE = {"jungle_pillar": (2.2, 3.0), "river_boulders": (2.0, 2.8), "ice_crystals": (1.9, 2.6),
         "obsidian_spire": (3.0, 4.0), "lava_vent": (2.2, 3.0), "rune_stone": (2.0, 2.6)}
CONN_SCALE = 0.8           # a connector's corridor is 10 m wide: its pieces are this much smaller (before the fit)
PER_STRIP = {"hall": (2, 3), "conn": (1, 2)}


def hall_strip(course, h, k, stations, tiers):
    """The wall strip of station hallway k: origin (cx, y0), heading +Y, s from y0."""
    keep = []
    for kind, y0, y1, attached in obstacles(course, k, h):
        pad = MARGIN[kind]
        keep.append((y0 - h["y0"] - pad, y1 - h["y0"] + pad, attached if kind == "baffle" else None))
        if kind == "baffle":      # the open side's wall: nothing near, the gap stays 900 wide
            keep.append((y0 - h["y0"] - GAP_SIDE_MARGIN, y1 - h["y0"] + GAP_SIDE_MARGIN, -attached))
    if k == 1:
        g = gate_spec(course)                      # the camp gate stands against the left wall: keep the left wall's set pieces off it
        keep.append((g["y"] - g["hy"] - GATE_KEEP - h["y0"], g["y"] + g["hy"] + GATE_KEEP - h["y0"], 1))
        keep.append((VOLT_S1[0], 1e9, -1))       # the right wall (Volt's side) from his stretch on: a pillar there stood behind Volt in the spawn frame (editor capture, 2026-10-13)
    return {"id": f"S{k:02d}", "kind": "hall", "tier": tier_of(k, stations, tiers), "o": (h["cx"], h["y0"]), "h": 90.0,
            "half": h["half"], "lane": LANE_HALL, "z": h["z"], "s0": SIGN_ZONE, "s1": h["door_y"] - h["y0"] - DOOR_ZONE,
            "keep": keep, "torch": TORCH_S}


def connector_strips(course, hs, stations, tiers):
    """Wall strips on every flat segment of every connector, replaying build_course.connector from the end of the hall before it.
    Returns (strips, ends): ends[k] is where the connector after hall k lands (x, y, level): the next hall's (cx, y0, floor - 2)."""
    strips, ends = [], {}
    for k in sorted(hs):
        h = hs[k]
        name, segments = c.CONNECTORS[(k - 1) % len(c.CONNECTORS)]
        dest_tier = tier_of(k + 1, stations, tiers) if k < stations else 5
        x, y, z, hd = h["cx"], h["y_end"] + c.FUNNEL, h["z"] - 2, 90.0
        for i, (length, turn, rise, plates) in enumerate(segments):
            hd -= turn
            if rise == 0 and length - 2 * JOINT > MIN_STRIP:
                keep = [(length * f - PLATE_HALF - PLATE_MARGIN, length * f + PLATE_HALF + PLATE_MARGIN, None) for f in plates]
                strips.append({"id": f"C{k:02d}_{i + 1}", "kind": "conn", "tier": dest_tier, "o": (x, y), "h": hd, "half": c.CONN_W / 2,
                               "lane": LANE_CONN, "z": z + 2, "s0": JOINT, "s1": length - JOINT, "keep": keep, "torch": ()})
            fx, fy = math.cos(math.radians(hd)), math.sin(math.radians(hd))
            x, y, z = x + fx * length, y + fy * length, z + rise
        ends[k] = (x, y + c.FUNNEL, z)
    return strips, ends


def sight_cap(strip, inner):
    """The farthest s a hall piece whose inner edge is `inner` from the centre line may reach: past it the piece would hide a corner of
    door A or D (the doors nearest the walls) from the arrival spot, along the line from there to that corner."""
    return SIGHT_EYE + (strip["s1"] + DOOR_ZONE - SIGHT_EYE) * inner / strip["half"]


def fit(mesh, rng, strip, rel_scale=1.0):
    """A random scale and yaw for `mesh` in `strip`, the scale cut down until the piece fits between the wall and the lane:
    (scale, yaw, along, across), or None. A rune stone's yaw is chosen later (it faces the corridor): yaw None."""
    lo, hi = SCALE[mesh]
    scale = rng.uniform(lo * SMALLEST, hi) * rel_scale
    yaw = rng.uniform(0.0, 360.0) if mesh != "rune_stone" else None
    room = (strip["half"] - strip["lane"] - EDGE) / 2          # across may be at most half the band
    for _ in range(40):
        across, along = across_along(mesh, scale, (yaw - strip["h"]) if yaw is not None else 0.0)
        if across <= room:
            return scale, yaw, along, across
        scale *= 0.94
    return None


def place_in_strip(strip, mesh, rng, count, taken, rel_scale=1.0):
    """Up to `count` more pieces of `mesh` on `strip` (seeded), appended to `taken` and returned."""
    got = []
    tall = size(mesh)[2] * SCALE[mesh][0] > TORCH_CLEAR
    for _ in range(400):
        if len(got) >= count:
            break
        f = fit(mesh, rng, strip, rel_scale)
        if f is None:
            continue
        scale, yaw, along, across = f
        side = rng.choice((1, -1))
        if strip["s1"] - strip["s0"] <= 2 * along:
            continue
        s = rng.uniform(strip["s0"] + along, strip["s1"] - along)
        if yaw is None:       # a rune stone shows its face to the corridor: the front toward the centre line, a little off
            toward = strip["h"] + (90.0 if side > 0 else -90.0)        # from the left wall (+X at heading 90) toward -X: heading + 90
            yaw = yaw_facing(mesh, toward + rng.uniform(-18.0, 18.0))
            across, along = across_along(mesh, scale, yaw - strip["h"])
            if across > (strip["half"] - strip["lane"] - EDGE) / 2 or s + along > strip["s1"] or s - along < strip["s0"]:
                continue
        if any(s + along > a and s - along < b and sd in (None, side) for a, b, sd in strip["keep"]):
            continue
        if tall and any(abs(s - t) < along * 0.6 + 50.0 for t in strip["torch"]):
            continue
        if strip["kind"] == "hall" and s + along > sight_cap(strip, strip["half"] - 2 * across - EDGE):
            continue
        if any(p["side"] == side and p["strip"] == strip["id"] and abs(p["s"] - s) < along + p["along"] + GAP for p in taken + got):
            continue
        lat = side * (strip["half"] - across - EDGE)
        hr = math.radians(strip["h"])
        fx, fy = math.cos(hr), math.sin(hr)
        lx, ly = fy, -fx                                   # the player's left
        got.append({"mesh": mesh, "strip": strip["id"], "tier": strip["tier"], "side": side, "s": s, "along": along, "across": across,
                    "x": strip["o"][0] + fx * s + lx * lat, "y": strip["o"][1] + fy * s + ly * lat, "z": rest_z(mesh, scale, strip["z"]),
                    "yaw": yaw, "scale": scale, "floor": strip["z"]})
    taken.extend(got)
    return got


def all_strips(course, tiers=None):
    hs = halls(course)
    stations = len(hs)
    tiers = c.tier_count() if tiers is None else tiers
    strips = [hall_strip(course, hs[k], k, stations, tiers) for k in sorted(hs)]
    conn, ends = connector_strips(course, hs, stations, tiers)
    return strips, conn, ends


def set_pieces(course, tiers=None):
    """Every tier set piece the course gets: [spec] with label, mesh, x, y, z, yaw, scale, tier, strip. Deterministic."""
    strips, conn, _ = all_strips(course, tiers)
    taken = []
    for tier in sorted(TIER_MESH):                       # one rune stone per tier first (the crowded strips would leave it no room), on a strip chosen by seed
        rng = random.Random(f"{SEED}-rune-{tier}")
        cand = [s for s in strips + conn if s["tier"] == tier and s["s1"] - s["s0"] > 400]
        rng.shuffle(cand)
        for strip in cand:
            if place_in_strip(strip, "rune_stone", rng, 1, taken, 1.0 if strip["kind"] == "hall" else CONN_SCALE):
                break
    for strip in strips + conn:
        rng = random.Random(f"{SEED}-{strip['id']}")
        n = rng.randint(*PER_STRIP[strip["kind"]])
        place_in_strip(strip, TIER_MESH[strip["tier"]], rng, n, taken, 1.0 if strip["kind"] == "hall" else CONN_SCALE)
    return [{**p, "label": f"FNM_TP_Set_{p['strip']}_{p['mesh']}_{i + 1:02d}"}
            for i, p in enumerate(sorted(taken, key=lambda p: (p["strip"], p["s"], p["side"])))]


def footprint(spec):
    """(x0, x1, y0, y1): the world box round a placed mesh."""
    hx, hy = half_extents(spec["mesh"], spec["scale"], spec["yaw"])
    return spec["x"] - hx, spec["x"] + hx, spec["y"] - hy, spec["y"] + hy


def conflicts(course, specs, tiers=None):
    """[str] of everything wrong with a list of set-piece specs against the course, computed from the course's own actors and the rules
    above (not from the placement's bookkeeping): in the wall band, clear of the lane, the sign zone, the door zone, every obstacle, every
    speed plate, the joints, and standing on the floor. Empty when every piece is fine."""
    strips, conn, _ = all_strips(course, tiers)
    by_id = {s["id"]: s for s in strips + conn}
    hs = halls(course)
    bad = []
    for p in specs:
        s = by_id.get(p["strip"])
        if s is None:
            bad.append(f"{p['label']}: no strip {p['strip']}")
            continue
        hr = math.radians(s["h"])
        fx, fy = math.cos(hr), math.sin(hr)
        dx, dy = p["x"] - s["o"][0], p["y"] - s["o"][1]
        along_s, lat = dx * fx + dy * fy, dx * fy - dy * fx            # lateral: + the player's left
        across, along = across_along(p["mesh"], p["scale"], p["yaw"] - s["h"])
        side = 1 if lat > 0 else -1
        if abs(lat) + across > s["half"] - EDGE + 0.5:
            bad.append(f"{p['label']}: reaches into the wall ({abs(lat) + across:.0f} of {s['half'] - EDGE:.0f})")
        if abs(lat) - across < s["lane"] - 0.5:
            bad.append(f"{p['label']}: inside the running lane ({abs(lat) - across:.0f} from the centre line, lane {s['lane']:.0f})")
        if along_s - along < s["s0"] - 0.5 or along_s + along > s["s1"] + 0.5:
            bad.append(f"{p['label']}: outside the strip's stretch s {along_s - along:.0f}..{along_s + along:.0f} vs {s['s0']:.0f}..{s['s1']:.0f}")
        for a, b, sd in s["keep"]:
            if along_s + along > a and along_s - along < b and sd in (None, side):
                bad.append(f"{p['label']}: over an obstacle, plate or Volt's stretch (s {a:.0f}..{b:.0f})")
        if abs(p["z"] - rest_z(p["mesh"], p["scale"], s["z"])) > 0.5:
            bad.append(f"{p['label']}: not standing on the floor (z {p['z']:.0f})")
        if s["kind"] == "hall" and along_s + along > sight_cap(s, abs(lat) - across) + 0.5:
            bad.append(f"{p['label']}: hides a door panel from the arrival spot")
        if s["kind"] == "hall":
            h = hs[int(s["id"][1:])]
            if along_s + along > h["door_y"] - h["y0"] - DOOR_ZONE + 0.5:
                bad.append(f"{p['label']}: within {DOOR_ZONE:.0f} of the door wall")
    return bad


# ---------------------------------------------------------------- the start gate
# THE DOORS ARE THE GAME (manager, 2026-10-13, on the first placement: a gate across the hall in front of the doors hid B and C in play).
# From the spawn camera all four doors, their colours and their lintel letters must be fully clear, and nothing may stand on the path
# from the spawn to any door. So the gate is camp dressing against the LEFT wall, turned to show its sign to the spawn camera, small
# enough that the whole of it projects outside the door wall's rectangle on the screen. `gate_blockers` is the check (the tests run it
# on this placement and on the ones that failed): it projects every occupied 10 cm cell of the gate's mesh (GATE_VOXELS) through the
# spawn camera and refuses any that lands on the door wall's rectangle (bearing +-21 degrees, elevation -5 to +6.9, plus a margin), and
# any low cell within PATH_CLEAR of a straight path from the spawn to a door.
GATE_SCALE = 2.9           # 1.9 x 1.26 x 1.09 m at scale 1: 5.5 x 3.7 x 3.2 m. About the largest the rule allows at this spot (3.3 only
#                            when it runs along the wall with its sign edge-on; 4.4 and 5.5 hid the doors, and 5.5 hid its own sign)
GATE_TURN = 25.0           # degrees from the wall-parallel pose (front toward -X) toward -Y, the spawn camera: the sign reads from there
GATE_AHEAD = 1290.0        # cm from the hall's first edge to the gate's centre: past the STATION sign (y0 + 242..958), where the cone is narrow
GATE_WALL_GAP = 30.0       # cm between the gate's box and the left wall's inner face
# The sign board on the gate's front, in gate units (1.0 = 100 cm at scale 1), measured on a Blender render of the GLB (front view):
# width 0.64, height 0.23, its middle 0.805 above the model's floor, its front face 0.358 ahead of the centre (the GLB's vertices:
# the plank faces are uneven by a few cm, and a banner laid 1.4 cm in front of the plane was hidden behind them in the editor,
# 2026-10-13: BANNER_STAND_OFF clears it).
GATE_BOARD = {"w": 0.64, "h": 0.23, "mid_z": 0.805, "front": 0.358, "dx": 0.01}
BANNER_STAND_OFF = 14.0    # cm the BASE CAMP quad stands in front of the board's front plane
GATE_BANNER_H = 1.5        # the BASE CAMP quad is this much taller than the board (a hanging sign, not a label)
EYE_BACK = 350.0           # the third-person camera sits this far behind the spawn spot ...
CAMERA_Z = 250.0           # ... and this high above the floor (build_landmarks' estimates)
SPAWN_S = 450.0            # the spawn spot: entry teleporter 150 + the director's ArrivalForward 300
DOOR_MARGIN_DEG = 1.5      # a cell within this many degrees of the door wall's rectangle counts as in front of it
PATH_CLEAR = 100.0         # cm: nothing below head height this near a straight path from the spawn to a door
PATH_HEAD = 200.0          # cells whose bottom is below this height above the floor can be walked into
# The gate mesh's occupied 10 cm cells (local x depth, y width, z height; index = (cm + 100) / 10, three base-20 digits per cell), read from
# the vertices of art/titanpeak/gate/raw/gate.glb (631 cells). Hundreds of wires and garlands join the parts, so the mesh is one blob:
# the cells are the footprint the doors' sightlines are tested against. tests/test_titanpeak.py re-derives them from the GLB when it is there.
GATE_VOXELS = (
    "3553563664444454544554564664674754764774f55155165355445455465475545555565645655665675765e45e55e6"
    "5f45f55f65g55g65i55i661561662562662763563663763864464564665465565665a6646656666766e46e56e66e96ea"
    "6f46f56f66f76f86g46g56g66g76g86h46h56h66h76i56i66j672472572673473573673874474574674774874974a74b"
    "75475575675775875975a75b76476576676876976a76b77977a78978a7987997a97b97ba7c97ca7d47d57d67d97da7e4"
    "7e57e67e77e87e97ea7eb7f47f57f67f77f87f97fa7fb7g47g57g87g97h47h57i47i5824834835836844845846847848"
    "84984a84b85485585685785885985a85b86486586686786886986a86b8d58d68e48e58e68e78e88e98ea8eb8f48f58f6"
    "8f78f88f98fa8fb8g48g58h48h58i492492593493593694494595595695895995a9e59e69e89e99ea9f49f59g49g59h4"
    "9h5a24a25a26a34a35a36a44a45a55a56a57a58a59a5aae5ae6ae7ae8ae9aeaaf4af5ag4ag5ah4ah5ai4ai5b24b25b26"
    "b34b35b36b44b45b46b4bb54b55b56b57b58b59b5ab5bb5cb5db5eb5fb64b65b66b67b68b69b6ab6bb6cb6db6eb6fbd4"
    "bd5bd6bd7bd8bd9bdabdbbdcbddbdebdfbe4be5be6be7be8be9beabebbecbedbeebefbf4bf5bf6bf7bf8bf9bfabfbbfc"
    "bfdbfebg4bg5bg6bh4bh5bi4bi5c25c34c35c36c38c39c44c45c46c48c49c4ac4bc4cc4dc4ec54c56c57c58c59c5ac5b"
    "c5cc5dc5ec5fc64c65c66c67c68c69c6ac6bc6cc6dc6ec6fc7ac7bc7cc7dc8ac8bc8cc8dc9ac9bc9dca9caacaccadcba"
    "cbbcbccbdccaccbcccccdcd4cd5cd6cd7cd8cd9cdacdbcdccddcdecdfce4ce7ce8ce9ceacebceccedceecefcf4cf5cf6"
    "cf7cf8cf9cfacfbcfccfdcfecffcg4cg5cg6cg8cg9cgacgbcgccgdch4ch5ci4ci5d04d06d14d15d16d17d24d25d26d27"
    "d28d34d35d36d37d38d39d3dd44d45d46d47d48d4bd4cd4dd54d55d56d57d58d59d5ad5bd5cd5dd5ed5fd64d65d66d67"
    "d68d69d6ad6bd6cd6dd6ed7bd7cd7dd8bd8cd8dd9bd9ddabdaddbbdbddcbdcddd4dd5dd6dd7dd9ddaddbddcdddddede4"
    "de5de6de7de8de9deadebdecdeddeedefdf4df5df6dfadfbdfcdfddfedg4dg5dg6dg7dg8dg9dgbdgddh4dh5dh6dh7dh8"
    "di4di5di6di7dj4dj5dj6e05e06e14e15e16e24e25e26e34e35e36e44e45e46e54e55e56e64e65e66e74e75ed4ed5ed6"
    "ee4ee5ee6ef4ef5ef6eg4eg5eg6eh5eh6ei4ei5ej5ej6f24f25f34f35f36f44f45f46f47f54f55f56f57f64f65f66f74"
    "fd4fd5fd6fe4fe5fe6fe7ff4ff5ff6fg5fg6g44g54g55g64g65gd4gd5ge4ge5gf4gf5"
)


def gate_cells():
    """[(x, y, z)] local cm of the centre of every occupied 10 cm cell of the gate mesh, at scale 1."""
    dig = "0123456789abcdefghij"
    s = "".join(GATE_VOXELS)
    return [((dig.index(s[i]) + 0.5) * 10.0 - 100.0, (dig.index(s[i + 1]) + 0.5) * 10.0 - 100.0, (dig.index(s[i + 2]) + 0.5) * 10.0 - 100.0)
            for i in range(0, len(s), 3)]


def world_cells(spec):
    """[(x, y, z, half_xy, half_z)] world cm of the gate's cells at its placement: half_xy is the half extent of a turned cell's box."""
    t = math.radians(spec["yaw"])
    cs, sn = math.cos(t), math.sin(t)
    s = spec["scale"]
    h_xy = 5.0 * s * (abs(cs) + abs(sn))
    return [(spec["x"] + lx * s * cs - ly * s * sn, spec["y"] + lx * s * sn + ly * s * cs, spec["z"] + lz * s, h_xy, 5.0 * s)
            for lx, ly, lz in gate_cells()]


def spawn_camera(course):
    """(x, y, z) of the third-person camera at the start: EYE_BACK behind the spawn spot, CAMERA_Z above the floor."""
    h = halls(course)[1]
    return h["cx"], h["y0"] + SPAWN_S - EYE_BACK, h["z"] + CAMERA_Z


def door_screen(course):
    """The door wall as the spawn camera sees it: (half bearing, lowest elevation, highest elevation) in degrees. It spans the whole
    wall (the four doors, their lintel letters and arches are all inside it: floor to wall top, wall to wall)."""
    h = halls(course)[1]
    cam = spawn_camera(course)
    d = h["door_face"] - cam[1]
    return (math.degrees(math.atan2(h["half"], d)), math.degrees(math.atan2(h["z"] - cam[2], d)),
            math.degrees(math.atan2(h["z"] + h["wall"] - cam[2], d)))


def gate_blockers(course, spec, margin=DOOR_MARGIN_DEG):
    """[str] of what the gate (a spec like `gate_spec`'s) does to the doors from the spawn camera: cells that project onto the door wall's
    rectangle, and low cells near a straight path from the spawn to a door. Empty when all four doors and their paths are clear."""
    h = halls(course)[1]
    cam = spawn_camera(course)
    b0, e_lo, e_hi = door_screen(course)
    cells = world_cells(spec)
    bad = []
    on_screen = 0
    for x, y, z, hxy, hz in cells:
        pts = [(x + dx, y + dy, z + dz) for dx in (-hxy, hxy) for dy in (-hxy, hxy) for dz in (-hz, hz)]
        pts = [p for p in pts if p[1] - cam[1] > 20.0]                  # a corner behind the camera is not on the screen
        if not pts:
            continue
        bear = [math.degrees(math.atan2(p[0] - cam[0], p[1] - cam[1])) for p in pts]
        elev = [math.degrees(math.atan2(p[2] - cam[2], p[1] - cam[1])) for p in pts]
        if max(bear) > -b0 - margin and min(bear) < b0 + margin and max(elev) > e_lo - margin and min(elev) < e_hi + margin:
            on_screen += 1
    if on_screen:
        bad.append(f"{on_screen} of {len(cells)} gate cells project onto the door wall (bearing +-{b0:.0f}, elevation {e_lo:.0f}..{e_hi:.0f} degrees)")
    spawn = (h["cx"], h["y0"] + SPAWN_S)
    low = [c_ for c_ in cells if c_[2] - c_[4] < h["z"] + PATH_HEAD]
    for i, dx in enumerate(c.door_centres(4)):
        end = (h["cx"] + dx, h["door_face"])
        for k in range(0, 201):
            q = (spawn[0] + (end[0] - spawn[0]) * k / 200, spawn[1] + (end[1] - spawn[1]) * k / 200)
            if any(math.hypot(max(abs(c_[0] - q[0]) - c_[3], 0.0), max(abs(c_[1] - q[1]) - c_[3], 0.0)) < PATH_CLEAR for c_ in low):
                bad.append(f"the gate stands within {PATH_CLEAR:.0f} cm of the path from the spawn to door {c.LETTERS[i]}")
                break
    return bad


def gate_spec(course, scale=None, ahead=None, turn=None):
    """The gate against station 1's left wall, its sign turned toward the spawn camera (see the block comment above)."""
    h = halls(course)[1]
    s = GATE_SCALE if scale is None else scale
    ahead = GATE_AHEAD if ahead is None else ahead
    turn = GATE_TURN if turn is None else turn
    heading_front = 180.0 + turn                           # front toward -X, turned toward -Y
    yaw = yaw_facing("gate", heading_front)
    hx, hy = half_extents("gate", s, yaw)
    x, y = h["left"] - GATE_WALL_GAP - hx, h["y0"] + ahead
    bd = GATE_BOARD
    t = math.radians(yaw)
    lx, ly = bd["front"] * 100.0 * s + BANNER_STAND_OFF, bd["dx"] * 100.0 * s
    return {"label": "FNM_TP_Gate", "mesh": "gate", "x": x, "y": y, "z": rest_z("gate", s, h["z"]), "yaw": yaw, "scale": s, "turn": turn,
            "floor": h["z"], "hx": hx, "hy": hy, "height": size("gate")[2] * s, "front": heading_front,
            "board": {"x": x + lx * math.cos(t) - ly * math.sin(t), "y": y + lx * math.sin(t) + ly * math.cos(t),
                      "z": h["z"] - SINK + bd["mid_z"] * 100.0 * s, "w": bd["w"] * 100.0 * s, "h": bd["h"] * 100.0 * s}}


# ---------------------------------------------------------------- the champions' podium
PODIUM_SCALE = 2.2
PODIUM_DX = 680.0          # cm from the victory hall's centre line toward NEW SKILL (-X): where the trophy's plinth was, Volt's own offset mirrored
PODIUM_BACK = 480.0        # cm in front of the end wall (Volt's own)
# The centre step's top slab at scale 1 (read from the GLB's vertices above the inset panel): 69.4 deep (x) by 65.4 wide (y), top at +53.5.
PODIUM_STEP = (69.4, 65.4)


def podium_spec(course, scale=None):
    hall = special_hall(course, "FNM_Finish")
    s = PODIUM_SCALE if scale is None else scale
    cx, end, z = hall["cx"], hall["y_end"], hall["z"]
    x, y = cx - PODIUM_DX, end - PODIUM_BACK
    stand = mascot.podium_stand(course)
    yaw = yaw_facing("podium", heading(x, y, *stand))
    hx, hy = half_extents("podium", s, yaw)
    return {"label": "FNM_TP_Podium", "mesh": "podium", "x": x, "y": y, "z": rest_z("podium", s, z), "yaw": yaw, "scale": s,
            "floor": z, "hx": hx, "hy": hy, "top": z - SINK + size("podium")[2] * s, "faces": stand}


# ---------------------------------------------------------------- the place banners
QUAD_W = 400.0             # tools/import_titanpeak.BANNER_W: a banner quad's width at actor scale 1
QUAD_FRONT0 = -90.0        # the heading its readable side faces at yaw 0 (import_titanpeak BANNER_FACING "-Y")
# Width / height of each banner's cropped art (alpha box of art/titanpeak/banners/<key>_raw.png; the quad has this true aspect).
ASPECT = {"base_camp": 1.871, "waterfall_gorge": 2.850, "frost_ridge": 2.508, "obsidian_descent": 2.140, "magma_core": 3.074,
          "titans_forge": 2.502, "hall_of_champions": 2.332}
BANNER_H = 400.0           # cm tall for every place banner (so the widths follow the art: 856 to 1230)
BANNER_Z = 560.0           # bottom edge above the hall's floor: level with the wall tops, nobody walks or jumps into it
PODIUM_BANNER_H = 200.0
PODIUM_BANNER_Z = 440.0    # above the trophy on its podium
TIER_FIRST_BANNER = {2: "waterfall_gorge", 3: "frost_ridge", 4: "obsidian_descent", 5: "magma_core"}


def first_station(tier, stations, tiers):
    return next(k for k in range(1, stations + 1) if tier_of(k, stations, tiers) == tier)


def banner(key, x, y, z_bottom, height, facing, where):
    """A banner quad's placement: front toward world heading `facing`, bottom centre at (x, y, z_bottom), `height` tall."""
    w = height * ASPECT[key]
    return {"label": f"FNM_TP_Banner_{where}_{key}", "key": key, "x": x, "y": y, "z": z_bottom, "w": w, "h": height,
            "scale": w / QUAD_W, "yaw": facing - QUAD_FRONT0, "facing": facing}


def banner_specs(course, tiers=None):
    """[spec] for the six floating banners (BASE CAMP is the gate's own, `gate_banner`)."""
    hs = halls(course)
    stations = len(hs)
    tiers = c.tier_count() if tiers is None else tiers
    out = []
    for tier, key in TIER_FIRST_BANNER.items():
        h = hs[first_station(tier, stations, tiers)]
        out.append(banner(key, h["cx"], h["y0"], h["z"] + BANNER_Z, BANNER_H, -90.0, f"S{h['k']:02d}"))
    arena = special_hall(course, "FNM_Arena")
    out.append(banner("titans_forge", arena["cx"], arena["y0"], arena["z"] + BANNER_Z, BANNER_H, -90.0, "Arena"))
    p = podium_spec(course)
    out.append(banner("hall_of_champions", p["x"], p["y"], p["floor"] + PODIUM_BANNER_Z, PODIUM_BANNER_H,
                      heading(p["x"], p["y"], *p["faces"]), "Podium"))
    return out


def gate_banner(course):
    """BASE CAMP on the gate's sign board: taller than the board (GATE_BANNER_H), centred on it, BANNER_STAND_OFF in front, facing the way
    the gate does (toward the spawn camera)."""
    g = gate_spec(course)
    b = g["board"]
    height = b["h"] * GATE_BANNER_H
    return banner("base_camp", b["x"], b["y"], b["z"] - height / 2, height, g["front"], "Gate")


# ---------------------------------------------------------------- the editor
def project():
    return c.project_mount().strip("/")


def found(tag=TAG):
    r = u.call(SCENE, "find_actors", {"tag": tag, "collision_channels": []})
    return [a for a in (r if isinstance(r, list) else r.get("returnValue", [])) if isinstance(a, dict)]


def remove(part=None):
    actors = found(part_tag(part) if part else TAG)
    for a in actors:
        u.call(SCENE, "remove_from_scene", {"actor": c.ref(a["actorPath"])})
    return len(actors)


def asset_path(name):
    """The imported asset's object path, found by name under FNM_TitanPeakArt."""
    got = u.call(ASSETS, "find_assets", {"folder_path": f"/{project()}/{ART}", "name": name, "recursive": True})["returnValue"]
    exact = [p for p in got if p.split(".")[-1] == name]
    if not exact:
        sys.exit(f"{name} is not imported under /{project()}/{ART}: run python tools/import_titanpeak.py (T1)")
    return exact[0]


def tag_actor(actor, label, part):
    u.call(ACTOR, "add_tag", {"actor": c.ref(actor), "tag": TAG})
    u.call(ACTOR, "add_tag", {"actor": c.ref(actor), "tag": part_tag(part)})
    u.call(ACTOR, "set_label", {"actor": c.ref(actor), "label": label})
    return actor


def shape_count(mesh_path):
    """How many collision shapes (spheres, boxes, capsules, convex hulls) a static mesh asset carries, read from its BodySetup."""
    body = json.loads(u.call(OBJ, "get_properties", {"instance": c.ref(mesh_path), "properties": ["bodySetup"]})["returnValue"])["bodySetup"]
    if not body:
        return 0
    geom = json.loads(u.call(OBJ, "get_properties", {"instance": body, "properties": ["aggGeom"]})["returnValue"])["aggGeom"]
    return sum(len(v) for k, v in geom.items() if k.endswith("Elems"))


def strip_collision(mesh_path):
    """Remove every collision shape from the mesh asset (idempotent), read it back; returns how many it removed."""
    before = shape_count(mesh_path)
    if before:
        u.call(STATIC, "remove_collisions", {"mesh": c.ref(mesh_path)})
        left = shape_count(mesh_path)
        if left:
            sys.exit(f"{mesh_path}: {left} collision shapes survived remove_collisions")
    return before


def place(path, spec, part):
    r = u.call(SCENE, "add_to_scene_from_asset", {"asset_path": path, "name": spec["label"], "xform": c.xform(
        spec["x"], spec["y"], spec["z"], spec["scale"], spec["scale"], spec["scale"], spec["yaw"])})
    actor = tag_actor(r["returnValue"]["refPath"], spec["label"], part)
    if GHOST_TRY:
        try:
            c.props(actor, GHOST)
        except RuntimeError as e:
            GHOST_TRY.clear()
            print(f"  ghost flags refused on {spec['label']}, not tried again ({str(e)[:100]})")
    return actor


def build_gate():
    course = d.course()
    g = gate_spec(course)
    blocked = gate_blockers(course, g)
    if blocked:
        sys.exit("the gate would hide the doors from the spawn camera:\n  " + "\n  ".join(blocked))
    gate_mesh = asset_path(asset_name("gate"))
    print(f"  gate mesh: {strip_collision(gate_mesh)} collision shapes removed")
    place(gate_mesh, g, "gate")
    b = gate_banner(course)
    place(asset_path(f"SM_fnm_tp_banner_{b['key']}"), b, "gate")
    print(f"gate at ({g['x']:.0f}, {g['y']:.0f}, {g['z']:.0f}) scale {g['scale']} yaw {g['yaw']:.1f} (front heading {g['front']:.0f}), "
          f"{g['height']:.0f} cm tall; BASE CAMP banner {b['w']:.0f} x {b['h']:.0f} at z {b['z']:.0f}; doors clear from the spawn camera")
    return g


def build_podium():
    course = d.course()
    p = podium_spec(course)
    mesh = asset_path(asset_name("podium"))
    print(f"  podium mesh: {strip_collision(mesh)} collision shapes removed")
    place(mesh, p, "podium")
    print(f"podium at ({p['x']:.0f}, {p['y']:.0f}, {p['z']:.0f}) scale {p['scale']} yaw {p['yaw']:.1f}, top step at z {p['top']:.0f}")
    return p


def build_set():
    course = d.course()
    specs = set_pieces(course)
    bad = conflicts(course, specs)
    if bad:
        sys.exit("set pieces break their own rules:\n  " + "\n  ".join(bad))
    paths = {m: asset_path(asset_name(m)) for m in SET_MESHES}
    print("  collision shapes removed:", {m: strip_collision(p) for m, p in paths.items()})
    for s in specs:
        place(paths[s["mesh"]], s, "set")
    per = {}
    for s in specs:
        per[s["mesh"]] = per.get(s["mesh"], 0) + 1
    print(f"{len(specs)} set pieces: {per}")
    return specs


def build_banners():
    course = d.course()
    specs = banner_specs(course)
    for b in specs:
        place(asset_path(f"SM_fnm_tp_banner_{b['key']}"), b, "banners")
        print(f"banner {b['key']}: {b['w']:.0f} x {b['h']:.0f} at ({b['x']:.0f}, {b['y']:.0f}, {b['z']:.0f}) yaw {b['yaw']:.0f}")
    return specs


BUILDERS = {"gate": build_gate, "podium": build_podium, "set": build_set, "banners": build_banners}


def build(parts):
    for part in parts:
        print(f"{part}: removed {remove(part)} old actors")
        BUILDERS[part]()
    u.call(ASSETS, "save_assets", {"asset_paths": []})


def check():
    actors = sorted(found(), key=lambda a: a.get("label", ""))
    print(len(actors), f"actors tagged {TAG}:", {part: len(found(part_tag(part))) for part in PARTS})
    for a in actors:
        bd = a.get("bounds", {})
        lo, hi = bd.get("min", {}), bd.get("max", {})
        print(f"  {a.get('label', ''):46} ({lo.get('x', 0):.0f}, {lo.get('y', 0):.0f}, {lo.get('z', 0):.0f}) .. "
              f"({hi.get('x', 0):.0f}, {hi.get('y', 0):.0f}, {hi.get('z', 0):.0f})")


def expected_bounds(spec):
    """(x0, x1, y0, y1, z0, z1) the editor should report for a placed spec: a mesh spec's rotated box, or a banner quad's standing sheet."""
    if "mesh" in spec:
        x0, x1, y0, y1 = footprint(spec)
        lo, hi = MESH[spec["mesh"]]
        return x0, x1, y0, y1, spec["z"] + lo[2] * spec["scale"], spec["z"] + hi[2] * spec["scale"]
    t = math.radians(spec["yaw"])
    hx, hy = spec["w"] / 2 * abs(math.cos(t)), spec["w"] / 2 * abs(math.sin(t))
    return spec["x"] - hx, spec["x"] + hx, spec["y"] - hy, spec["y"] + hy, spec["z"], spec["z"] + spec["h"]


def all_specs(course):
    return [*set_pieces(course), gate_spec(course), podium_spec(course), gate_banner(course), *banner_specs(course)]


def verify(tolerance=3.0):
    """Every actor the plan names is placed, tagged, and reads back the planned bounds (within `tolerance` cm); prints the worst."""
    course = d.course()
    actors = {a.get("label"): a for a in found()}
    specs = all_specs(course)
    bad, worst = [], 0.0
    for s in specs:
        a = actors.get(s["label"])
        if a is None or not a.get("bounds", {}).get("isValid", True):
            bad.append(f"{s['label']}: not placed")
            continue
        b = a["bounds"]
        got = (b["min"]["x"], b["max"]["x"], b["min"]["y"], b["max"]["y"], b["min"]["z"], b["max"]["z"])
        diff = max(abs(g - w) for g, w in zip(got, expected_bounds(s)))
        worst = max(worst, diff)
        if diff > tolerance:
            bad.append(f"{s['label']}: bounds differ by {diff:.1f} cm (got {tuple(round(v) for v in got)}, want {tuple(round(v) for v in expected_bounds(s))})")
    extra = sorted(set(actors) - {s["label"] for s in specs})
    if extra:
        bad.append(f"actors with the tag the plan does not name: {extra[:5]}")
    print(f"{len(specs) - len([b for b in bad if 'not placed' in b])} of {len(specs)} planned actors placed; worst bounds difference {worst:.1f} cm")
    for line in bad:
        print("  " + line)
    if bad:
        sys.exit(1)


def plan():
    course = d.course()
    specs = set_pieces(course)
    for s in specs:
        print(f"{s['label']:46} ({s['x']:.0f}, {s['y']:.0f}, {s['z']:.0f}) scale {s['scale']:.2f} yaw {s['yaw']:.0f}")
    print(len(specs), "set pieces;", len(conflicts(course, specs)), "conflicts")
    for spec in (gate_spec(course), podium_spec(course), gate_banner(course), *banner_specs(course)):
        print({k: (round(v, 1) if isinstance(v, float) else v) for k, v in spec.items()})


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--part", choices=PARTS, help="only this part")
    ap.add_argument("--remove", action="store_true", help="remove the actors (all, or one --part) and stop")
    ap.add_argument("--check", action="store_true", help="list what is placed (read-only)")
    ap.add_argument("--plan", action="store_true", help="print every placement from the live course (read-only)")
    ap.add_argument("--verify", action="store_true", help="compare every placed actor's bounds with the plan (read-only, exit 1 on a miss)")
    args = ap.parse_args()
    if args.remove:
        print("removed", remove(args.part), "actors")
        u.call(ASSETS, "save_assets", {"asset_paths": []})
    elif args.check:
        check()
    elif args.plan:
        plan()
    elif args.verify:
        verify()
    else:
        build([args.part] if args.part else list(PARTS))
