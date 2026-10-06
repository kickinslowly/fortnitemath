"""Decorate the starter course: station numbers over the door walls, burning wall torches, chalkboards, entry plants,
a winter dressing on the ice stations (ICE_STATIONS) and their way in, a finish celebration. Idempotent via actor tag
`fnm_decor` (rerun after a course rebuild: geometry is read from the course actors' bounds, never assumed).

    python tools/build_decor.py               # every station + finish
    python tools/build_decor.py --stations 1  # only station 1 (prototype), finish skipped
    python tools/build_decor.py --only 6      # only station 6 (e.g. the ice station), finish skipped
    python tools/build_decor.py --clear       # remove all decor

Nothing here may sit where a player runs: props hang on walls above head height, stand in the two entry corners,
lie along a side wall's base (within FLOOR_REACH of it, no collision, never in a baffle's gap or by a hurdle or a
slider) or sit on top of walls. Doors, vestibules, obstacles and the centre line stay clear.
The finish's leaderboard screen and button podium belong to tools/build_finish.py (its own tag), not to this script.
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
# A lit torch (Aaron 2026-10-05: "torches have no fire" on the bare Castle_WallTorch mesh). This blueprint carries a
# point light, a flame particle (P_Athena_TT_Torch), an ember cap and a crackle sound. The editor viewport is not
# realtime, so the flame particle shows in a capture only on a torch that happened to tick; the embers always show.
# At yaw 0 its wall bracket points +X: yaw 0 hangs it on a wall to its +X (the runner's left), yaw 180 on the right.
TORCH = "PPID_CR_Legacy_BP_TRV_ALight_Torch_02_CP"
CHALKBOARD = "PPID_CR_Legacy_Chalkboard_01"
PLANT = "PPID_CR_Legacy_Athena_Prop_Plant_Houseplant01"
FLOWERS = "PPID_CR_Legacy_CP_Athena_Prop_Plant_PottedFlower01"
FIREWORKS = "PPID_CR_Legacy_CP_P_Atmospheric_Fireworks_79121a1f"
FIREWORKS_BACK = 1500   # cm behind the finish end wall

NUMBER_SCALE = 4.0      # a digit is ~67 x 98 cm at scale 1, pivot at its centre
NUMBER_W = 67
NUMBER_H = 98
TORCH_Z = 400           # above head height, bracket on the inner wall face; the torch leans out ~1 m
TORCH_SCALE = 2.0
TORCH_YAW_L, TORCH_YAW_R = 0, 180
CHALK_YAW, CHALK_SCALE = 90, 2.0
CHALK_TEXT_YAW = 90    # the station sign's in-play-proven pose (left wall, yaw -90) turned 180 for the right wall
CHALK_STYLE = {"showBorder": False, "textSize": 24, "textJustification": "Center", "textColor": {"r": 0.95, "g": 0.95, "b": 0.9, "a": 1.0}}
# Chalkboard doodles, one per station. Only glyphs seen rendering in play (PROTOCOL O1): ASCII, × ÷ −, ² ³.
CHALK_LINES = ["3 + 4 × 2 = 11", "a² + b² = c²", "1/2 + 1/4 = 3/4", "2³ = 8", "7 × 8 = 56",
               "A = l × w", "−3 + 5 = 2", "3:4 = 6:8", "25% of 40 = 10", "12 ÷ 3 = 4"]
TORCH_YS = (500, 1250, 2000, 2750)  # along the hallway from its start; the left wall skips the one at the sign

# Ice stations (Aaron 2026-10-05: "icy floors should have indication of icy conditions"). Sizes are each prop's bounds
# at scale 1 (bench-measured); every floor-level piece is GHOST, so a slide into it never trips anyone.
SNOWPILES = [("PPID_CR_Legacy_Athena_Prop_Winter_SnowPile", 256, 476),   # (prop, width x, length y) at scale 1
             ("PPID_CR_Legacy_Athena_Prop_Winter_SnowPile2", 346, 420)]
SNOW_W = 135            # a snow pile's width off the wall (its x scale is set to this); long axis along the wall
SNOW_SY, SNOW_SZ = 0.8, 1.2   # ~3.5 m long, ~55-65 cm high
SNOW_YS = range(400, 2700, 250)   # candidate pile centres; obstacle_clear() drops the ones near an obstacle
FLOOR_REACH = 150       # floor-level decor stays within this of a side wall (outside the entry corners)
ICE_BLOCK = "PPID_CR_Legacy_Apollo_IceCube_NoLoot"   # 194 cm cube of blue ice, base at the pivot
ICE_BLOCK_SIZE, ICE_BLOCK_SCALE = 194, 0.7
STATUES = ["PPID_CR_Legacy_Arctic_IceStatue_Raven", "PPID_CR_Legacy_Arctic_IceStatue_RedKnight"]  # ~130 cm, base at pivot
SNOWMAN = "PPID_CR_Legacy_CP_SneakySnowman_Prop"           # 228 x 156 x 216, Santa hat
SNOW_TREE = "PPID_CR_Legacy_CP_Apollo_Holiday_Tree_Snow"   # 333 x 314 x 584 snowy decorated pine
ICICLES = "PPID_CR_Legacy_Prop_Ice"   # an icicle cluster hanging below its pivot: ~67 x 71 x 134 at scale 1
ICICLE_SCALE = 2.0
ICICLE_STEP = 150
SNOWFLAKE = "PPID_CR_Legacy_Apollo_Winter_SnowFlake_01"   # 258 x 39 x 296 flat flake, pivot at its centre, faces +-Y
SNOWFLAKE_H = 296
WALL_SNOW = "PPID_CR_Legacy_Apollo_Winter_SnowPile_Wall_01_bb5f6837"   # 493 x 85 x 24 snow ridge for a wall top
WALL_SNOW_DX = 42       # at yaw 90 the ridge lies on the pivot's -X side: shift it this much to centre it on a wall
GATE_FLAKE_SCALE = 1.5  # giant flakes standing on the connector walls where it opens into an ice hallway
ICE_ENTRY_RUN = 1200    # icicles hang along this last stretch of the connector into an ice hallway


def asset(name):
    return P + name + "." + name


def place(name, label, x, y, z, yaw=0.0, s=1.0, sxyz=None):
    sx, sy, sz = sxyz or (s, s, s)
    r = u.call(c.SCENE, "add_to_scene_from_asset", {"asset_path": asset(name), "name": label,
                                                    "xform": c.xform(x, y, z, sx, sy, sz, yaw)})
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


def clear_station(k):
    """Remove only station k's decor (labels FNM_Dkk_*)."""
    found = u.call(c.SCENE, "find_actors", {"tag": TAG, "collision_channels": []})
    actors = [a for a in (found if isinstance(found, list) else found.get("returnValue", []))
              if a["label"].startswith(f"FNM_D{k:02d}_")]
    for a in actors:
        u.call(c.SCENE, "remove_from_scene", {"actor": c.ref(a["actorPath"])})
    return len(actors)


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
    ice = k in c.ICE_STATIONS
    for n, dy in enumerate(TORCH_YS):
        if dy == 500:   # the station sign (left) and the chalkboard (right) hang at +600
            continue
        if ice:         # big snowflakes flat on the walls instead of fire
            for side, x in (("L", left - 25), ("R", right + 25)):
                c.props(place(SNOWFLAKE, f"{pre}_Flake{side}{n}", x, oy + dy, oz + TORCH_Z, yaw=90), GHOST)
            continue
        torch(f"{pre}_TorchL{n}", left - 15, oy + dy, oz + TORCH_Z, TORCH_YAW_L)
        torch(f"{pre}_TorchR{n}", right + 15, oy + dy, oz + TORCH_Z, TORCH_YAW_R)
    place(CHALKBOARD, f"{pre}_Chalkboard", right + 15, oy + 600, oz + 150, yaw=CHALK_YAW, s=CHALK_SCALE)
    chalk = device(c.BILLBOARD, f"{pre}_Chalk", right + 30, oy + 600, oz + 250, yaw=CHALK_TEXT_YAW, s=2.0)
    c.props(chalk, {**CHALK_STYLE, "text": CHALK_LINES[(k - 1) % len(CHALK_LINES)]})
    if ice:             # a snowman and a snowy pine in the entry corners instead of house plants
        c.props(place(SNOWMAN, f"{pre}_Snowman", left - 130, oy + 140, oz), GHOST)
        c.props(place(SNOW_TREE, f"{pre}_SnowTree", right + 150, oy + 160, oz, s=0.8), GHOST)
        ice_hall(b, p, pre, wl, wr, oy, oz, door_y)
        ice_entry(b, p, pre)
    else:
        for side, x in (("L", left - 110), ("R", right + 110)):
            place(PLANT, f"{pre}_Plant{side}", x, oy + 110, oz)
    sky_digits(k, cx, oy, oz, random.Random(SKY_SEED + k))
    return door_y


def torch(label, x, y, z, yaw):
    c.props(place(TORCH, label, x, y, z, yaw=yaw, s=TORCH_SCALE), GHOST)   # it leans out over a wall-hugger's head


def blocked(b, p, side, left, right, y0, y1, hung=False):
    """True when the stretch y0..y1 along wall `side` ("L"/"R") is no place for decor because of station p's
    obstacles: a hurdle or a slider's lane (both walls), a baffle's gap side (floor decor would narrow the gap), or,
    for wall-hung decor (hung=True), the baffle itself where it meets its wall."""
    for lab, bb in b.items():
        if not lab.startswith(p + "_"):
            continue
        kind = lab[len(p) + 1:]
        lo, hi = bb["min"]["y"], bb["max"]["y"]
        if kind.startswith("Hurdle") or kind.startswith("Slider"):
            if hung:
                continue                      # 70 cm bar / 3 m container: wall-hung decor starts above them
            lo, hi = (lo - 100, hi + 100) if kind.startswith("Hurdle") else (lo - 300, hi + 300)
        elif kind.startswith("Baffle"):
            attached = "L" if bb["max"]["x"] >= left - 5 else "R"
            if side != attached:
                lo, hi = lo - 150, hi + 150   # the gap: floor decor would narrow it
            else:                             # the dead pocket beside a baffle's own wall is fair game
                lo, hi = (lo - 100, hi + 100) if hung else (lo - 10, hi + 10)
        else:
            continue
        if y0 < hi and y1 > lo:
            return True
    return False


def ice_hall(b, p, pre, wl, wr, oy, oz, door_y):
    """Winter dressing for an ice hallway, so the floor reads as ice before anyone steps on it: snow piles along the
    wall bases, ice blocks in the dead pockets beside the baffles, ice statues by the doors, icicles hanging from the
    wall tops and a snow ridge on them. Floor-level pieces stay within FLOOR_REACH of a side wall, no collision."""
    left, right = wl["min"]["x"], wr["max"]["x"]
    walls = (("L", left, -1, wl), ("R", right, 1, wr))   # sgn: the direction from the wall into the hallway
    n = 0
    for dy in SNOW_YS:
        for side, x, sgn, _ in walls:
            name, w, length = SNOWPILES[n % len(SNOWPILES)]
            half = length * SNOW_SY / 2
            y = oy + dy
            if y + half > door_y - 300 or blocked(b, p, side, left, right, y - half, y + half):
                continue
            c.props(place(name, f"{pre}_Snow{side}{n}", x + sgn * SNOW_W / 2, y, oz,
                          sxyz=(SNOW_W / w, SNOW_SY, SNOW_SZ)), GHOST)
            n += 1
    bs = ICE_BLOCK_SIZE * ICE_BLOCK_SCALE
    for lab, bb in b.items():
        if lab.startswith(p + "_Baffle"):   # in the pocket just before the baffle, against the wall it hangs from
            side, x, sgn = ("L", left, -1) if bb["max"]["x"] >= left - 5 else ("R", right, 1)
            y = bb["min"]["y"] - bs / 2 - 30
            if not blocked(b, p, side, left, right, y - bs / 2, y + bs / 2):
                c.props(place(ICE_BLOCK, f"{pre}_IceBlock{side}{lab[-1]}", x + sgn * (bs / 2 + 5), y, oz,
                              s=ICE_BLOCK_SCALE), GHOST)
    for i, (side, x, sgn, _) in enumerate(walls):
        y = door_y - 500
        if not blocked(b, p, side, left, right, y - 80, y + 80):
            c.props(place(STATUES[i % len(STATUES)], f"{pre}_Statue{side}", x + sgn * 80, y, oz, yaw=-90), GHOST)
    for side, x, sgn, w in walls:
        top = w["max"]["z"]
        for dy in range(1050, int(door_y - oy) - 100, ICICLE_STEP):   # from past the sign / chalkboard
            y = oy + dy
            if min(abs(dy - t) for t in TORCH_YS) < 200 or blocked(b, p, side, left, right, y - 80, y + 80, hung=True):
                continue
            c.props(place(ICICLES, f"{pre}_Icicle{side}{dy}", x + sgn * 72, y, top - 15, yaw=dy * 37 % 360,
                          s=ICICLE_SCALE), GHOST)
        wx = (w["min"]["x"] + w["max"]["x"]) / 2 + WALL_SNOW_DX
        for dy in range(250, int(door_y - oy) - 200, 480):
            c.props(place(WALL_SNOW, f"{pre}_WallSnow{side}{dy}", wx, oy + dy, top, yaw=90), GHOST)


def ice_entry(b, p, pre):
    """Announce an ice hallway from the connector leading into it (labelled with the hallway's prefix): giant
    snowflakes standing on its walls where it opens out, icicles and snow along its last ICE_ENTRY_RUN. Only for a
    connector whose last segment runs straight along Y (a yawed wall's bounds would not give its inner face)."""
    segs = sorted(int(m.group(1)) for m in (re.match(re.escape(p) + r"_WallC(\d+)L$", lab) for lab in b) if m)
    if not segs:
        return
    wl, wr = b[f"{p}_WallC{segs[-1]}L"], b[f"{p}_WallC{segs[-1]}R"]
    if any(w["max"]["x"] - w["min"]["x"] > 100 for w in (wl, wr)):
        print("  ice entry: the last connector segment is not straight along Y; skipped")
        return
    end = wl["max"]["y"]
    for side, w, x, sgn in (("L", wl, wl["min"]["x"], -1), ("R", wr, wr["max"]["x"], 1)):
        wx, top = (w["min"]["x"] + w["max"]["x"]) / 2, w["max"]["z"]
        c.props(place(SNOWFLAKE, f"{pre}_GateFlake{side}", wx, end - 100, top + SNOWFLAKE_H / 2 * GATE_FLAKE_SCALE,
                      s=GATE_FLAKE_SCALE), GHOST)
        start = max(w["min"]["y"], end - ICE_ENTRY_RUN)
        for i, y in enumerate(range(int(start) + 75, int(end) - 75, ICICLE_STEP * 2)):
            c.props(place(ICICLES, f"{pre}_EntryIcicle{side}{i}", x + sgn * 72, y, top - 15, yaw=i * 61 % 360,
                          s=ICICLE_SCALE), GHOST)
        for i, y in enumerate(range(int(start) + 250, int(end) - 200, 480)):
            c.props(place(WALL_SNOW, f"{pre}_EntryWallSnow{side}{i}", wx + WALL_SNOW_DX, y, top, yaw=90), GHOST)


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
    # The leaderboard screen and the button podium belong to tools/build_finish.py (2026-10-05), not to decor.
    for side, x in (("L", left - 120), ("R", right + 120)):
        # Behind the end wall: in front of it they burst across the all-time screen and hid the names (seen in play).
        place(FIREWORKS, f"FNM_DF_Fireworks{side}", x, ey + FIREWORKS_BACK, oz)
        place(FLOWERS, f"FNM_DF_FlowersA{side}", x, ey - 500, oz)
        place(PLANT, f"FNM_DF_Plant{side}", x, oy + 110, oz)
    for n, dy in enumerate((300, 800, 1300)):
        torch(f"FNM_DF_TorchL{n}", left - 15, oy + dy, oz + TORCH_Z, TORCH_YAW_L)
        torch(f"FNM_DF_TorchR{n}", right + 15, oy + dy, oz + TORCH_Z, TORCH_YAW_R)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--stations", type=int, default=0, help="only the first N stations (0 = all) and no finish")
    ap.add_argument("--only", type=int, default=0, help="rebuild only station N's decor, and no finish")
    ap.add_argument("--clear", action="store_true")
    a = ap.parse_args()
    if a.only:
        print("removed", clear_station(a.only), f"old station {a.only} decor actors")
    else:
        print("removed", c.clear(TAG), "old decor actors")
    if a.clear:
        return
    b = course()
    ks = sorted(int(m.group(1)) for m in (re.match(r"FNM_S(\d\d)_WallL$", lab) for lab in b) if m)
    if a.stations:
        ks = ks[:a.stations]
    if a.only:
        ks = [a.only]
    for k in ks:
        station(k, b)
        print("decorated station", k)
    if not a.stations and not a.only:
        finish(b)
        print("decorated finish")


if __name__ == "__main__":
    main()
