"""Decorate the starter course: station numbers over the door walls, wall torches, chalkboards, entry plants, a
finish celebration. Idempotent via actor tag `fnm_decor` (rerun after a course rebuild: geometry is read from the
course actors' bounds, never assumed).

    python tools/build_decor.py               # every station + finish
    python tools/build_decor.py --stations 1  # only station 1 (prototype), finish skipped
    python tools/build_decor.py --clear       # remove all decor

Nothing here may sit where a player runs: props hang on walls above head height, stand in the two entry corners,
or sit on top of walls. Doors, vestibules, obstacles and the centre line stay clear.
"""
import argparse
import random
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import build_course as c  # noqa: E402
import uefn_mcp as u  # noqa: E402

TAG = "fnm_decor"
P = "/CR_Legacy/Playsets/PlaysetProps/"
DIGITS = ["Zero", "One", "Two", "Three", "Four", "Five", "Six", "Seven", "Eight", "Nine"]
# Four colour variants per digit. Order is not consistent across digits; "One" index 3 is yellow (for the finish "100").
NUMBER_IDS = {
    "Zero": ["b16033f9", "b7455c7c", "c3d7a127", "d1876323"], "One": ["1766fe86", "1859d055", "ea4c7014", "9e07c08e"],
    "Two": ["200c3d4f", "a9c1cbd7", "ae281cc7", "b6cec061"], "Three": ["3e2080ed", "5a96a69c", "b51bc4c2", "ee9d894e"],
    "Four": ["2a1a87f6", "756d2980", "9eabb635", "e590ed24"], "Five": ["3e826e76", "8ad036cf", "c3504370", "e0a0cf04"],
    "Six": ["1e241f88", "2c4ecdb3", "2f493817", "70af9243"], "Seven": ["581daa62", "933c2a23", "e6000bb9", "e6a202bb"],
    "Eight": ["1a3c882e", "34125e8c", "638fbf6c", "73935edb"], "Nine": ["03e3bd7f", "1c1bfbcf", "759e7c73", "b532412d"],
}
# Out of reach of play: a Yeet skydive (PENALTIES.md) may pass the sky digits; nothing should snag a player.
GHOST = {"bNoCollision": True}
SKY_SEED = 20261005
SKY_PER_SIDE = 3
SKY_DIST = (2500, 5000)   # from the hallway centre line, well outside the walls (half width ~1150)
SKY_Z = (900, 2600)
SKY_SCALE = (10.0, 18.0)  # 7-12 m digits
TORCH = "PPID_CR_Legacy_Prop_Castle_WallTorch"
CHALKBOARD = "PPID_CR_Legacy_Chalkboard_01"
PLANT = "PPID_CR_Legacy_Athena_Prop_Plant_Houseplant01"
FLOWERS = "PPID_CR_Legacy_CP_Athena_Prop_Plant_PottedFlower01"
PODIUM = "PPID_CR_Legacy_Podium"
FIREWORKS = "PPID_CR_Legacy_CP_P_Atmospheric_Fireworks_79121a1f"

NUMBER_SCALE = 4.0      # a digit is ~67 x 98 cm at scale 1, pivot at its centre
NUMBER_W = 67
NUMBER_H = 98
TORCH_Z = 380           # above head height, on the inner wall face
TORCH_SCALE = 2.0
TORCH_YAW_L, TORCH_YAW_R = 90, -90
CHALK_YAW, CHALK_SCALE = 90, 2.0
CHALK_TEXT_YAW = 90    # the station sign's in-play-proven pose (left wall, yaw -90) turned 180 for the right wall
CHALK_STYLE = {"showBorder": False, "textSize": 24, "textJustification": "Center", "textColor": {"r": 0.95, "g": 0.95, "b": 0.9, "a": 1.0}}
# Chalkboard doodles, one per station. Only glyphs seen rendering in play (PROTOCOL O1): ASCII, × ÷ −, ² ³.
CHALK_LINES = ["3 + 4 × 2 = 11", "a² + b² = c²", "1/2 + 1/4 = 3/4", "2³ = 8", "7 × 8 = 56",
               "A = l × w", "−3 + 5 = 2", "3:4 = 6:8", "25% of 40 = 10", "12 ÷ 3 = 4"]
TORCH_YS = (500, 1250, 2000, 2750)  # along the hallway from its start; the left wall skips the one at the sign


def asset(name):
    return P + name + "." + name


def place(name, label, x, y, z, yaw=0.0, s=1.0):
    r = u.call(c.SCENE, "add_to_scene_from_asset", {"asset_path": asset(name), "name": label,
                                                    "xform": c.xform(x, y, z, s, s, s, yaw)})
    a = r["returnValue"]["refPath"]
    u.call(c.ACTOR, "add_tag", {"actor": c.ref(a), "tag": TAG})
    u.call(c.ACTOR, "set_label", {"actor": c.ref(a), "label": label})
    return a


def device(asset_path, label, x, y, z, yaw=0.0, s=1.0):
    """A device tagged as decor only (build_course.device would also tag it as course)."""
    r = u.call(c.DEV, "PlaceDevice", {"assetPath": c.ref(asset_path), "transform": c.xform(x, y, z, s, s, s, yaw)})
    a = r["returnValue"]["refPath"]
    u.call(c.ACTOR, "add_tag", {"actor": c.ref(a), "tag": TAG})
    u.call(c.ACTOR, "set_label", {"actor": c.ref(a), "label": label})
    return a


def course():
    """{label: bounds} for every course actor."""
    found = u.call(c.SCENE, "find_actors", {"tag": c.TAG, "collision_channels": []})
    actors = found if isinstance(found, list) else found["returnValue"]
    return {a["label"]: a["bounds"] for a in actors}


def number(text, cx, y, z, colour, prefix):
    """Digits of `text` centred on cx, standing on z, readable from -Y."""
    w = NUMBER_W * NUMBER_SCALE + 30
    x0 = cx + w * (len(text) - 1) / 2       # +X is the reader's LEFT, so the first digit sits at +X
    for i, ch in enumerate(text):
        digit = DIGITS[int(ch)]
        name = f"PPID_CR_Legacy_CP_Number_{digit}_{NUMBER_IDS[digit][colour % 4]}"
        a = place(name, f"{prefix}_Number{i}", x0 - w * i, y, z + NUMBER_H * NUMBER_SCALE / 2, yaw=-90, s=NUMBER_SCALE)
        c.props(a, GHOST)


def station(k, b):
    p = f"FNM_S{k:02d}"
    wl, wr, lintel, floor = b[f"{p}_WallL"], b[f"{p}_WallR"], b[f"{p}_Lintel"], b[f"{p}_Floor"]
    left, right = wl["min"]["x"], wr["max"]["x"]          # inner wall faces (+X is the runner's left)
    oy, oz = wl["min"]["y"], floor["max"]["z"]
    cx = (left + right) / 2
    door_y = (lintel["min"]["y"] + lintel["max"]["y"]) / 2
    top = lintel["max"]["z"]
    pre = f"FNM_D{k:02d}"
    number(str(k), cx, lintel["min"]["y"] + 20, top, k - 1, pre)
    for n, dy in enumerate(TORCH_YS):
        if dy == 500:   # the station sign (left) and the chalkboard (right) hang at +600
            continue
        place(TORCH, f"{pre}_TorchL{n}", left - 15, oy + dy, oz + TORCH_Z, yaw=TORCH_YAW_L, s=TORCH_SCALE)
        place(TORCH, f"{pre}_TorchR{n}", right + 15, oy + dy, oz + TORCH_Z, yaw=TORCH_YAW_R, s=TORCH_SCALE)
    place(CHALKBOARD, f"{pre}_Chalkboard", right + 15, oy + 600, oz + 150, yaw=CHALK_YAW, s=CHALK_SCALE)
    chalk = device(c.BILLBOARD, f"{pre}_Chalk", right + 30, oy + 600, oz + 250, yaw=CHALK_TEXT_YAW, s=2.0)
    c.props(chalk, {**CHALK_STYLE, "text": CHALK_LINES[(k - 1) % len(CHALK_LINES)]})
    for side, x in (("L", left - 110), ("R", right + 110)):
        place(PLANT, f"{pre}_Plant{side}", x, oy + 110, oz)
    sky_digits(k, cx, oy, oz, random.Random(SKY_SEED + k))
    return door_y


def sky_digits(k, cx, oy, oz, rng):
    """Giant digits floating beside station k, outside the walls, facing the course (a digit faces its yaw)."""
    for side in (1, -1):
        for n in range(SKY_PER_SIDE):
            digit = rng.choice(DIGITS)
            name = f"PPID_CR_Legacy_CP_Number_{digit}_{rng.choice(NUMBER_IDS[digit])}"
            x = cx + side * rng.uniform(*SKY_DIST)
            y = oy + rng.uniform(0, 3500)
            z = oz + rng.uniform(*SKY_Z)
            r = u.call(c.SCENE, "add_to_scene_from_asset", {"asset_path": asset(name), "name": "sky", "xform": {
                "location": {"x": x, "y": y, "z": z},
                "rotation": {"pitch": 0, "yaw": (180 if side > 0 else 0) + rng.uniform(-25, 25),
                             "roll": rng.uniform(-15, 15)},
                "scale": dict.fromkeys("xyz", rng.uniform(*SKY_SCALE))}})
            a = r["returnValue"]["refPath"]
            u.call(c.ACTOR, "add_tag", {"actor": c.ref(a), "tag": TAG})
            u.call(c.ACTOR, "set_label", {"actor": c.ref(a), "label": f"FNM_D{k:02d}_Sky{'L' if side > 0 else 'R'}{n}"})
            c.props(a, GHOST)


def finish(b):
    wl, wr, end, floor = b["FNM_Finish_WallL"], b["FNM_Finish_WallR"], b["FNM_Finish_WallEnd"], b["FNM_Finish_Floor"]
    left, right = wl["min"]["x"], wr["max"]["x"]
    oy, oz, ey = wl["min"]["y"], floor["max"]["z"], end["min"]["y"]
    cx = (left + right) / 2
    place(PODIUM, "FNM_DF_Podium", cx, ey - 250, oz, yaw=-90, s=2.0)
    number("100", cx, ey - 30, b["FNM_Finish_Sign"]["max"]["z"] + 20, 3, "FNM_DF")   # 100%: done; above the sign
    for side, x in (("L", left - 120), ("R", right + 120)):
        place(FIREWORKS, f"FNM_DF_Fireworks{side}", x, ey - 150, oz)
        place(FLOWERS, f"FNM_DF_FlowersA{side}", x, ey - 500, oz)
        place(PLANT, f"FNM_DF_Plant{side}", x, oy + 110, oz)
    for n, dy in enumerate((300, 800, 1300)):
        place(TORCH, f"FNM_DF_TorchL{n}", left - 15, oy + dy, oz + TORCH_Z, yaw=180, s=TORCH_SCALE)
        place(TORCH, f"FNM_DF_TorchR{n}", right + 15, oy + dy, oz + TORCH_Z, yaw=0, s=TORCH_SCALE)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--stations", type=int, default=0, help="only the first N stations (0 = all) and no finish")
    ap.add_argument("--clear", action="store_true")
    a = ap.parse_args()
    print("removed", c.clear(TAG), "old decor actors")
    if a.clear:
        return
    b = course()
    ks = sorted(int(m.group(1)) for m in (re.match(r"FNM_S(\d\d)_WallL$", lab) for lab in b) if m)
    if a.stations:
        ks = ks[:a.stations]
    for k in ks:
        station(k, b)
        print("decorated station", k)
    if not a.stations:
        finish(b)
        print("decorated finish")


if __name__ == "__main__":
    main()
