"""Door marks: a big 3D letter on every door's lintel and a letter-coloured arch light in front of it, in the open UEFN
project through UEFN MCP (G9 "Now" 1, reviews/race-2026-10-13: "every door is identical"; the panel paint says the letter
only at the last second, so the runner chooses a door from 30 m away by the arch above it).

Per door (stations 1..N, doors A..D):
- the letter: the CRG_Props Alphabet prop (tools/build_bossmode.letter_asset, ~206 x 201 x 50 cm at scale 1, pivot at its
  bottom centre) standing against the lintel's runner-side face, yaw 180 so its readable face points -Y at the runner
  (the readable face is +Y at yaw 0; the boss arenas' pad letters are placed the same way). `color` is the nearest stock
  colour to build_course.LETTER_COLOURS (build_bossmode.LETTER_PROP_COLOURS), bNoCollision true, bCanBeDamaged false.
  It fills the lintel face (door top to wall top, 216 cm) with a margin, so it sits below the station number
  (tools/build_decor.py stands the digits ON the wall top, from z 600 up) and clear of the door panel (top at 384).
  The lintel is painted near-black by build_course.paint (key `lintel`) so the letters read against it.
- the light: a Customizable Light (PID_Device_PointLight) a little in front of the arch in the letter's colour, a glow
  (lightSizePercentage 25, intensity 40; the brief's 50 / 60-100 bleached the white doors and pale walls in daylight in
  editor frames, 100 floods a room white), so a door reads from the lit pool it throws on the wall and floor at dusk.

Geometry comes from the course actors (their Lintel bounds and Door transforms), never from assumed coordinates: station
hallways sit at different X and levels. Idempotent via actor tag `fnm_door_marks`: a run first deletes everything with it.
Rerun it after a course rebuild (the course's doors and lintels are re-placed).

    python tools/build_door_marks.py             # every station
    python tools/build_door_marks.py --only 1    # only station 1's marks (rebuilds just those)
    python tools/build_door_marks.py --check     # read-only report: counts and the read-back options
    python tools/build_door_marks.py --clear     # remove all door marks
"""
import argparse
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import build_bossmode as b  # noqa: E402
import build_course as c  # noqa: E402
import uefn_mcp as u  # noqa: E402

TAG = "fnm_door_marks"
LETTER_W, LETTER_H, LETTER_D = 206.0, 201.3, 50.0   # the Alphabet letter at scale 1 (build_race_boss; its pivot at the bottom centre)
FACE_H = c.WALL_H - c.DOOR_H                        # the lintel's runner-side face, 216 cm, above the door panel
LETTER_SCALE = 1.0
LETTER_YAW = 180                                    # readable face -Y: toward a runner who faces +Y
LETTER_OUT = 2.0                                    # the letter's back stands this far off the lintel face
# The light: in front of the lintel, under it and over a runner's head (a 384 cm door), so it throws the letter's colour on the
# letter, the lintel and the dark wall round the door without sitting where anyone stands.
LIGHT_BACK = 100.0                                  # cm in front of the lintel face
LIGHT_Z = 350.0                                     # above the station floor
LIGHT_SIZE_PERCENT = 25
LIGHT_INTENSITY_PERCENT = 40


def rgba(rgb):
    return {"r": rgb[0], "g": rgb[1], "b": rgb[2], "a": 1.0}


def layout(door_x, face_y, floor_z, i):
    """Where door i's (A = 0) letter and light go, given the door's x centre, the lintel's runner-side face y and the
    station's floor z: {"letter": (x, y, z, scale, yaw), "light": (x, y, z), "colour": name, "rgb": (r, g, b)}.
    The letter's pivot is its bottom centre, so z is its base; it is centred in the lintel face."""
    h = LETTER_H * LETTER_SCALE
    return {"letter": (door_x, face_y - LETTER_OUT - LETTER_D * LETTER_SCALE / 2,
                       floor_z + c.DOOR_H + (FACE_H - h) / 2, LETTER_SCALE, LETTER_YAW),
            "light": (door_x, face_y - LIGHT_BACK, floor_z + LIGHT_Z),
            "colour": b.LETTER_PROP_COLOURS[i], "rgb": c.LETTER_COLOURS[i]}


def close(got, want):
    """Read-back equality with float noise (a colour 0.3 reads back 0.30000001) and colour dicts."""
    if isinstance(want, dict) and isinstance(got, dict):
        return all(close(got.get(k), v) for k, v in want.items())
    if isinstance(want, (int, float)) and not isinstance(want, bool) and isinstance(got, (int, float)):
        return abs(got - want) < 0.01
    return got == want


def options(actor, values, label):
    """One key per call (a combined write can keep an old value), then read back; {key: what it reads} for each that differs."""
    for key, value in values.items():
        try:
            c.props(actor, {key: value})
        except RuntimeError as e:
            print(f"  {label}: could not set {key}: {str(e)[:120]}")
    back = b.get(actor, values)
    return {k: back.get(k) for k, v in values.items() if not close(back.get(k), v)}


def light_options(i):
    return {"lightColor": rgba(c.LETTER_COLOURS[i]), "lightSizePercentage": LIGHT_SIZE_PERCENT,
            "lightIntensityPercentage": LIGHT_INTENSITY_PERCENT, "enabledDuringPhase": "Always"}


def course_doors():
    """{station: {"lintel": bounds, "doors": {letter index: actor}}} read from the course actors."""
    found = [a for a in u.call(c.SCENE, "find_actors", {"tag": c.TAG, "collision_channels": []})["returnValue"] if isinstance(a, dict)]
    out = {}
    for a in found:
        if m := re.fullmatch(r"FNM_S(\d\d)_Lintel", a.get("label", "")):
            out.setdefault(int(m[1]), {"doors": {}})["lintel"] = a["bounds"]
        elif m := re.fullmatch(r"FNM_S(\d\d)_Door([A-D])", a.get("label", "")):
            out.setdefault(int(m[1]), {"doors": {}})["doors"][c.LETTERS.index(m[2])] = a
    return out


def marks(tag=TAG):
    found = u.call(c.SCENE, "find_actors", {"tag": tag, "collision_channels": []})["returnValue"]
    return [a for a in found if isinstance(a, dict)]


def clear_station(k):
    old = [a for a in marks() if a.get("label", "").startswith(f"FNM_S{k:02d}_Mark")]
    for a in old:
        u.call(c.SCENE, "remove_from_scene", {"actor": c.ref(a["actorPath"])})
    return len(old)


def tagged(actor, label):
    u.call(c.ACTOR, "add_tag", {"actor": c.ref(actor), "tag": TAG})
    u.call(c.ACTOR, "set_label", {"actor": c.ref(actor), "label": label})
    return actor


def build(only=0):
    course = course_doors()
    if not course:
        sys.exit("no FNM_Sxx_Lintel / FNM_Sxx_DoorX course actors: run the course build first")
    print("removed", clear_station(only) if only else c.clear(TAG), "old door marks")
    assets, placed, problems = {}, 0, []
    for k in sorted(course):
        if only and k != only:
            continue
        st = course[k]
        lintel = st.get("lintel")
        if lintel is None or not st["doors"]:
            print(f"station {k}: no lintel or no doors, skipped")
            continue
        face_y = lintel["min"]["y"]                                  # the engine-cube lintel: exact, its runner-side face
        floor_z = lintel["min"]["z"] - c.DOOR_H                      # as build_course.doors_only
        for i in sorted(st["doors"]):
            letter = c.LETTERS[i]
            xf = u.call(c.ACTOR, "get_actor_transform", {"actor": c.ref(st["doors"][i]["actorPath"])})["returnValue"]
            spot = layout(xf["location"]["x"], face_y, floor_z, i)
            if letter not in assets:
                assets[letter] = b.letter_asset(letter)
            x, y, z, s, yaw = spot["letter"]
            r = u.call(c.SCENE, "add_to_scene_from_asset", {"asset_path": assets[letter], "name": f"FNM_S{k:02d}_Mark{letter}",
                                                            "xform": c.xform(x, y, z, s, s, s, yaw)})
            actor = tagged(r["returnValue"]["refPath"], f"FNM_S{k:02d}_Mark{letter}")
            problems += [f"S{k:02d}{letter} letter {w}" for w in options(
                actor, {"color": spot["colour"], "bNoCollision": True, "bCanBeDamaged": False}, f"S{k:02d}{letter}").items()]
            lx, ly, lz = spot["light"]
            # Placed here, not with c.device: that tags it as a course actor, which a course rebuild would delete.
            light = u.call(c.DEV, "PlaceDevice", {"assetPath": c.ref(b.POINT_LIGHT), "transform": c.xform(lx, ly, lz)})["returnValue"]["refPath"]
            tagged(light, f"FNM_S{k:02d}_Mark{letter}Light")
            problems += [f"S{k:02d}{letter} light {w}" for w in options(light, light_options(i), f"S{k:02d}{letter}Light").items()]
            placed += 1
        print(f"station {k}: marks placed on {len(st['doors'])} doors (face y={face_y:.0f}, floor z={floor_z:.0f})")
    u.call(c.ASSETS, "save_assets", {"asset_paths": []})
    print(f"{placed} doors marked: {placed} letters + {placed} lights tagged {TAG}; {len(problems)} read-back problems"
          + ("" if not problems else ": " + "; ".join(map(str, problems[:6]))))
    if problems:
        sys.exit(1)


def check():
    found = marks()
    letters = [a for a in found if re.fullmatch(r"FNM_S\d\d_Mark[A-D]", a.get("label", ""))]
    lights = [a for a in found if re.fullmatch(r"FNM_S\d\d_Mark[A-D]Light", a.get("label", ""))]
    print(f"{len(letters)} letters, {len(lights)} lights tagged {TAG}")
    bad = []
    for a in sorted(letters, key=lambda a: a["label"]):
        i = c.LETTERS.index(a["label"][-1])
        want = {"color": b.LETTER_PROP_COLOURS[i], "bNoCollision": True, "bCanBeDamaged": False}
        got = b.get(a["actorPath"], list(want))
        if not close(got, want):
            bad.append(f"{a['label']} {got}")
    for a in sorted(lights, key=lambda a: a["label"]):
        i = c.LETTERS.index(a["label"][-6])
        want = light_options(i)
        got = b.get(a["actorPath"], list(want))
        if not close(got, want):
            bad.append(f"{a['label']} {got}")
    print(f"{len(bad)} actors read back differently" + ("" if not bad else ": " + "; ".join(bad[:4])))
    if bad:
        sys.exit(1)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", type=int, default=0, help="only station N's marks")
    ap.add_argument("--check", action="store_true", help="read-only report")
    ap.add_argument("--clear", action="store_true", help="remove all door marks")
    a = ap.parse_args()
    if a.check:
        check()
    elif a.clear:
        print("removed", c.clear(TAG), "door marks")
    else:
        build(a.only)
