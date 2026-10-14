"""The race finale's boss rig in the open UEFN project through UEFN MCP: the boss battle arena's best pieces brought into
the race's boss arena (maps/starter/LAYOUT.md "Boss arena", BOSS_MODE.md section 16).

Aaron (2026-10-11): "match up the boss fight in the end of race with our best learnings and improvements from arena".
What this places, all tagged TAG and labelled FNM_RaceBoss_*:
- the boss: a hidden Megabrute creature spawner on the arena's boss platform (Verse tag fnm_race_megaboss; settings
  build_bossmode.MEGABOSS_SETTINGS), and over it the Magma Titan, one Animated Mesh device per clip (fnm_race_titan +
  fnm_bm_slot_N, build_bossmode.TITAN_CLIPS order; tools/import_boss.py once per UEFN project), TITAN_SCALE, facing the
  entry (-Y);
- two Meshy mega laser cannons (FNM_CannonArt/SM_fnm_megacannon, tools/import_cannon.py) beside the platform, barrels
  turned onto the titan's waist, with the cyan coil and muzzle lights; their muzzle discharge, coil crackle, lasers
  (NS_fnm_laser_race, its length baked to laser_length(): tools/build_fx.py) and impact are Niagara systems Verse spawns
  from the beam markers;
- a beam marker per cannon: the Alphabet "I" laid from the muzzle point to the waist (fnm_race_beam + slot), hidden in
  play; Verse fires along it;
- the strike VFX and two explosive blasts parked under the platform (fnm_cannon_strike / fnm_cannon_blast), moved to
  the boss's feet and set off on every hit as before;
- a floating 3D letter over each answer pad (fnm_race_letter + slot 1..4 = A..D), boss mode's Alphabet set and colours,
  which the director turns to face the nearest race player in the arena.

It removes what the race arena had in their place: the guard boss spawner FNM_Arena_Boss and the letter billboards
FNM_Arena_Label[A-D] (both left by a tools/build_course.py older than 2026-10-11), and the engine-shape cannons, muzzle
VFX spawners, strike and blasts of the retired tools/build_cannon.py (actor tag fnm_cannon_rig).

Geometry is read from the course actors (FNM_Arena_Floor / _WallL / _WallR / _Platform, actor tag fnm_course), so rerun
after a course rebuild. Positions below are relative to the arena: x from its centre line (+X is the player's LEFT, as
in build_course), y from the start of its floor, z above its floor top.

Idempotent: every actor this script creates is tagged TAG; a run first deletes everything with TAG.

    python tools/build_race_boss.py
    python tools/build_race_boss.py --check     # list what is placed, with the devices' read-back options
"""
import argparse
import json
import math
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import uefn_mcp as u  # noqa: E402
import build_bossmode as b  # noqa: E402
import build_course as c  # noqa: E402
import build_lids as lids  # noqa: E402
from build_course import ACTOR, ASSETS, DEV, LETTERS, OBJ, SCENE, ref, verse_tags, xform  # noqa: E402

TAG = "fnm_race_boss"
OLD_CANNON_TAG = "fnm_cannon_rig"       # the retired tools/build_cannon.py's actor tag
OLD_COURSE_LABELS = re.compile(r"FNM_Arena_(Boss|Label[A-D])")

# The titan. The hall is short: the entry is 24.5 m from the platform (45 m in boss mode, where scale 4, 12 m, put the
# head just under the question panel). At 2.4 (7.2 m) its head touched the panel's bottom edge from the entry in play
# (2026-10-11) and the explanation line covered it; 2.1 makes it 6.3 m on the 1 m platform, the head clear of the panel.
# It stands taller than the 6 m walls (the lid is invisible).
TITAN_SCALE = 2.1
# The race titan's clips, slots 1..5: boss mode's first five (no scream: the race's wrong pad keeps the stomp). The jump-slam
# (slot 5) is the entrance when a player walks into the arena (fnm_director ArenaArrival; G9 D2).
RACE_TITAN_CLIPS = b.TITAN_CLIPS[:5]
# The beams aim at its waist: boss mode's BEAM_AIM scaled with the titan (450 at scale 4).
BEAM_AIM = round(b.BEAM_AIM * TITAN_SCALE / b.TITAN_SCALE)
# The mega cannons. Scale 3 (5.7 m long, 2.9 m tall; boss mode's 4 in a 64 m colosseum would be 7.6 m in a 22 m hall):
# NS_fnm_coil and NS_fnm_muzzle are authored round the scale-4 coils and mouth and cannot be scaled from Verse, and at
# scale 3 their arcs still sit ~40 cm off the coils (at 2, 60 cm off a block half their length). Body centres CANNON_X
# either side of the centre line, CANNON_Y into the hall: beside the platform, behind the far pads (C, D end at y 2425)
# and short of the gate, so the walking lanes (the centre between the pads, and after the kill each side of the platform
# to the gate) stay open; ~17 degrees off the view's centre from the entry, beside the titan as in boss mode.
CANNON_SCALE = 3.0
CANNON_X = 780
CANNON_Y = 2700
# The beam (and the muzzle discharge) starts this far ahead of the mouth: boss mode's MUZZLE_AHEAD scaled with the cannon.
MUZZLE_AHEAD = b.MUZZLE_AHEAD * CANNON_SCALE / b.CANNON_SCALE
# The floating letters: boss mode's Alphabet props and colours (build_bossmode LETTER_*), smaller and lower. At boss mode's
# scale 1.8 (3.6 m tall) the letter plus its 40 cm bob fits under the lid (5.8 m) only with its base at 1.75 m, inside a
# player standing on the pad; at 1.5 (3 m) its base sits at 2.3 m, over their head, the bob included.
LETTER_SCALE = 1.5
LETTER_Z = 230
LETTER_H, LETTER_W = 201.3, 206          # the Alphabet letter at scale 1 (build_bossmode LETTER_ASSET)
LETTER_BOB = 40                          # fnm_director LetterBobCm
STRIKE_SCALE = 4.0                       # the hall is half the colosseum's size (boss mode: 5)
PARK_DROP = 600                          # the strike and blasts park this far under the floor
ENTRY = (0, c.ENTRY_Y)
LID_Z = c.WALL_H - 2 - lids.SINK         # the invisible lid's underside above the floor top (walls rise from oz, floor top oz + 2)
HALF = 4 * c.DOOR_W / 2                  # the hall's inner half-width (build_course.arena, 4 doors)


# ---------------------------------------------------------------- pure layout (tests read these)

def aim():
    """The titan's waist (x, y, z above the floor top), where the beams meet."""
    return 0.0, float(c.PLATFORM_Y), float(c.PLATFORM_H + BEAM_AIM)


def cannon_frame(side):
    """The cannon on side 'L' (+X, the player's left) or 'R': body (x, y), heading (radians, onto the waist), pivot height,
    and point(local, ahead) -> (x, y, z) for a point on the mesh (scale-1 local coordinates, as build_bossmode
    CANNON_MUZZLE) pushed `ahead` cm further along the barrel. Same frame as build_bossmode.cannon_frame."""
    ax, ay, _ = aim()
    bx, by = (CANNON_X if side == "L" else -CANNON_X), CANNON_Y
    heading = math.atan2(ay - by, ax - bx)
    k = CANNON_SCALE
    pz = b.CANNON_HALF_H * k

    def point(local, ahead=0.0):
        a, f, up = local
        f = f * k + ahead
        return (bx + f * math.cos(heading) + a * k * math.sin(heading),
                by + f * math.sin(heading) - a * k * math.cos(heading), pz + up * k)
    return (bx, by), heading, pz, point


def muzzle_point(side):
    return cannon_frame(side)[3](b.CANNON_MUZZLE, MUZZLE_AHEAD)


def laser_length():
    """Muzzle point to waist: NS_fnm_laser_race's baked length (tools/build_fx.py RACE_LENGTH)."""
    return math.dist(muzzle_point("L"), aim())


def coil_back():
    """How far the coils sit behind the beam's start along the barrel (fnm_fx.verse FnmRaceCannonCoilBack)."""
    return (b.CANNON_MUZZLE[1] - b.CANNON_COIL[1]) * CANNON_SCALE + MUZZLE_AHEAD


def cannon_corners(side):
    """The cannon's footprint at CANNON_SCALE (the mesh is 93 across, 190 along the barrel at scale 1), 4 (x, y) corners."""
    (bx, by), heading, _, _ = cannon_frame(side)
    hw, hl = 93 * CANNON_SCALE / 2, 190 * CANNON_SCALE / 2
    ca, sa = math.cos(heading), math.sin(heading)
    return [(bx + f * ca + a * sa, by + f * sa - a * ca) for f in (-hl, hl) for a in (-hw, hw)]


def titan_yaw():
    """The titan faces the entry (the mesh faces +X)."""
    return math.degrees(math.atan2(ENTRY[1] - c.PLATFORM_Y, ENTRY[0] - 0))


SIDES = ("L", "R")


# ---------------------------------------------------------------- editor helpers (every actor tagged TAG)

def found(tag):
    r = u.call(SCENE, "find_actors", {"tag": tag, "collision_channels": []})
    return [a for a in (r if isinstance(r, list) else r.get("returnValue", [])) if isinstance(a, dict)]


def remove(actors):
    for a in actors:
        u.call(SCENE, "remove_from_scene", {"actor": ref(a["actorPath"])})
    return len(actors)


def tagged(actor, label):
    u.call(ACTOR, "add_tag", {"actor": ref(actor), "tag": TAG})
    u.call(ACTOR, "set_label", {"actor": ref(actor), "label": label})
    return actor


def asset(path, label, x, y, z, scale=1.0, yaw=0.0, rotation=None, sz=None):
    r = u.call(SCENE, "add_to_scene_from_asset", {"asset_path": path, "name": label, "xform": {
        "location": {"x": x, "y": y, "z": z}, "rotation": rotation or {"pitch": 0, "yaw": yaw, "roll": 0},
        "scale": {"x": scale, "y": scale, "z": scale if sz is None else sz}}})
    return tagged(r["returnValue"]["refPath"], label)


def device(path, label, x, y, z, scale=1.0, yaw=0.0):
    # Scale goes in the PlaceDevice transform: a later scale-only set_actor_transform resets location.
    r = u.call(DEV, "PlaceDevice", {"assetPath": ref(path), "transform": xform(x, y, z, scale, scale, scale, yaw)})
    return tagged(r["returnValue"]["refPath"], label)


def arena():
    """The race arena's origin (x of its centre line, y where its floor starts, z of its floor top) from the course actors."""
    parts = {a["label"]: a["bounds"] for a in found(c.TAG) if a.get("label", "").startswith("FNM_Arena_")}
    missing = [p for p in ("Floor", "WallL", "WallR", "Platform") if f"FNM_Arena_{p}" not in parts]
    if missing:
        sys.exit(f"race arena pieces missing ({missing}): run tools/build_course.py first")
    floor, platform = parts["FNM_Arena_Floor"], parts["FNM_Arena_Platform"]
    ox = (floor["min"]["x"] + floor["max"]["x"]) / 2
    oy, z0 = floor["min"]["y"], floor["max"]["z"]
    top = platform["max"]["z"] - z0
    if abs(top - c.PLATFORM_H) > 5:
        print(f"  note: the platform top is {top:.0f} above the floor, build_course says {c.PLATFORM_H}")
    return ox, oy, z0


def require(project):
    """Stop naming the import command when the titan clips or the cannon mesh are missing."""
    need = {f"/{project}/{b.CANNON_ART.split('.')[0]}": "python tools/import_cannon.py"}
    for clip in RACE_TITAN_CLIPS:
        need[f"/{project}/{b.TITAN_ART}/Clip_{clip}/A_fnm_titan_{clip}"] = "python tools/import_boss.py"
    missing = sorted({cmd for path, cmd in need.items() if not u.call(ASSETS, "exists", {"path": path})["returnValue"]})
    if missing:
        sys.exit("art missing: " + "; ".join(missing))


# ---------------------------------------------------------------- build

def build():
    project = c.project_mount().strip("/")
    require(project)
    old_course = [a for a in found(c.TAG) if OLD_COURSE_LABELS.fullmatch(a.get("label", ""))]
    print("removed", remove(found(TAG)), "old race boss actors,", remove(found(OLD_CANNON_TAG)),
          "build_cannon actors,", remove(old_course), "course boss spawner / letter boards")
    ox, oy, z0 = arena()
    at = lambda x, y, z=0.0: (ox + x, oy + y, z0 + z)   # noqa: E731
    top = c.PLATFORM_H

    boss = device(b.CREATURE, "FNM_RaceBoss_Megaboss", *at(0, c.PLATFORM_Y, top), yaw=-90)
    verse_tags(boss, project, ["fnm_race_megaboss"])     # tag first: the tag component rebuilds a device's sub-objects
    wrong = b.options(boss, b.MEGABOSS_SETTINGS, "Megaboss")
    if "creature Type" in wrong:
        sys.exit(f"the creature spawner refused {b.MEGABOSS}: {wrong}")

    titan(project, at, top)

    ax, ay, az = aim()
    for k, side in enumerate(SIDES, 1):
        (bx, by), heading, pz, point = cannon_frame(side)
        body = asset(f"/{project}/{b.CANNON_ART}", f"FNM_RaceBoss_Cannon{side}_Body", *at(bx, by, pz), CANNON_SCALE,
                     math.degrees(heading) - 90)        # the mesh's barrel runs along its +Y
        b.props(body, {"bCanBeDamaged": False})
        for name, local in (("Glow", point(b.CANNON_COIL)), ("MuzzleGlow", point(b.CANNON_MUZZLE, 60 * CANNON_SCALE / b.CANNON_SCALE))):
            b.options(device(b.POINT_LIGHT, f"FNM_RaceBoss_Cannon{side}_{name}", *at(*local)), b.CANNON_LIGHT,
                      f"Cannon{side}_{name}")
        mx, my, mz = muzzle_point(side)
        dx, dy, dz = ax - mx, ay - my, az - mz
        length = math.sqrt(dx * dx + dy * dy + dz * dz)
        # Local +Z along the shot: yaw = its heading, pitch = its elevation - 90 (as build_bossmode.boss_rig).
        rot = {"pitch": math.degrees(math.atan2(dz, math.hypot(dx, dy))) - 90, "yaw": math.degrees(math.atan2(dy, dx)), "roll": 0}
        beam = asset(b.letter_asset(b.BEAM_LETTER), f"FNM_RaceBoss_Beam{side}", *at(mx, my, mz), b.BEAM_W, rotation=rot,
                     sz=length / b.BEAM_H)
        b.props(beam, {"bCanBeDamaged": False})
        b.options(beam, {"color": b.BEAM_COLOUR, "bNoCollision": True}, f"Beam{side}")
        verse_tags(beam, project, ["fnm_race_beam", f"fnm_bm_slot_{k}"])
        print(f"cannon {side}: body ({bx:.0f}, {by:.0f}) yaw {math.degrees(heading) - 90:.1f}, beam {length / 100:.2f} m "
              f"from ({mx:.0f}, {my:.0f}, {mz:.0f}) to the waist")

    park = -PARK_DROP
    strike = device(b.VFX, "FNM_RaceBoss_Strike", *at(0, c.PLATFORM_Y, park), STRIKE_SCALE)
    verse_tags(strike, project, ["fnm_cannon_strike"])
    b.options(strike, b.STRIKE_FX, "Strike")
    for n in range(b.BLASTS):
        blast = device(b.EXPLOSIVE, f"FNM_RaceBoss_Blast{n + 1}", *at(300 * (n + 1), c.PLATFORM_Y, park))
        verse_tags(blast, project, ["fnm_cannon_blast"])
        b.options(blast, b.BLAST, f"Blast{n + 1}")
    print(f"strike + {b.BLASTS} blasts parked {PARK_DROP} cm under the platform")

    for i, (dx, dy) in enumerate(c.PAD_SPOTS):
        letter = LETTERS[i]
        actor = asset(b.letter_asset(letter), f"FNM_RaceBoss_Letter{letter}", *at(dx, dy, LETTER_Z), LETTER_SCALE, 180)
        b.props(actor, {"bCanBeDamaged": False})
        b.options(actor, {"color": b.LETTER_PROP_COLOURS[i], "bNoCollision": True}, f"Letter{letter}")
        verse_tags(actor, project, ["fnm_race_letter", f"fnm_bm_slot_{i + 1}"])
    print(f"4 floating letters at {LETTER_Z} cm, scale {LETTER_SCALE}")

    u.call(ASSETS, "save_assets", {"asset_paths": []})
    print(f"race boss rig built in the arena at ({ox:.0f}, {oy:.0f}, {z0:.0f}): {len(found(TAG))} actors tagged {TAG}; "
          f"laser {laser_length():.0f} cm (build_fx RACE_LENGTH), coil back {coil_back():.0f} cm")


def titan(project, at, top):
    """The titan's clip devices FNM_RaceBoss_Titan1..5 (fnm_race_titan + slot, RACE_TITAN_CLIPS order) on the platform,
    facing the entry; the idle at home, the rest parked under it until Verse shrinks them there."""
    yaw = titan_yaw()
    for k, clip in enumerate(RACE_TITAN_CLIPS, 1):
        z = top if k == 1 else top - b.TITAN_PARK
        dev = device(b.ANIMATED_MESH, f"FNM_RaceBoss_Titan{k}", *at(0, c.PLATFORM_Y, z), TITAN_SCALE, yaw)
        verse_tags(dev, project, ["fnm_race_titan", f"fnm_bm_slot_{k}"])
        u.call(OBJ, "set_properties", {"instance": ref(dev), "values": json.dumps(b.titan_clip_props(project, clip))})
        got = b.get(dev, ["animation"])
        if not got.get("animation", {}).get("refPath", "").endswith(f"A_fnm_titan_{clip}"):
            sys.exit(f"FNM_RaceBoss_Titan{k}: animation did not take ({got}); run tools/import_boss.py")
    print(f"Megabrute spawner + {len(RACE_TITAN_CLIPS)} titan clips at scale {TITAN_SCALE}, yaw {yaw:.1f}")


def retitan():
    """Re-place only the titan's clip devices (FNM_RaceBoss_Titan*), the rest of the rig left as it is (G9 D2: a new clip)."""
    project = c.project_mount().strip("/")
    require(project)
    old = [a for a in found(TAG) if re.fullmatch(r"FNM_RaceBoss_Titan\d+", a.get("label", ""))]
    print("removed", remove(old), "old titan clip devices")
    ox, oy, z0 = arena()
    titan(project, lambda x, y, z=0.0: (ox + x, oy + y, z0 + z), c.PLATFORM_H)
    u.call(ASSETS, "save_assets", {"asset_paths": []})


def check():
    actors = sorted(found(TAG), key=lambda a: a.get("label", ""))
    print(len(actors), "race boss actors;", len(found(OLD_CANNON_TAG)), "build_cannon actors left;",
          len([a for a in found(c.TAG) if OLD_COURSE_LABELS.fullmatch(a.get("label", ""))]), "old course boss pieces left")
    for a in actors:
        label, path = a.get("label", ""), a["actorPath"]
        if label.endswith("Megaboss"):
            print(f"  {label:30} {b.get(path, b.MEGABOSS_SETTINGS)}")
        elif "Blast" in label:
            print(f"  {label:30} {b.get(path, b.BLAST)}")
        elif "Strike" in label:
            print(f"  {label:30} {b.get(path, b.STRIKE_FX)}")
        elif "Titan" in label:
            print(f"  {label:30} {b.get(path, ['animation', 'loop', 'initialState'])}")
        else:
            bd = a.get("bounds", {})
            lo, hi = bd.get("min", {}), bd.get("max", {})
            print(f"  {label:30} ({lo.get('x', 0):.0f}, {lo.get('y', 0):.0f}, {lo.get('z', 0):.0f}) .. "
                  f"({hi.get('x', 0):.0f}, {hi.get('y', 0):.0f}, {hi.get('z', 0):.0f})")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true", help="list the placed actors and the devices' read-back options")
    ap.add_argument("--titan", action="store_true", help="(re)place only the titan's clip devices (RACE_TITAN_CLIPS)")
    a = ap.parse_args()
    check() if a.check else retitan() if a.titan else build()
