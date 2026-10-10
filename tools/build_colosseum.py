"""Dress the BOSS BATTLE arena (tools/build_bossmode.py) as a colosseum from Fortnite's Coliseum playset kit (Aaron,
2026-10-09: "an arena, large, circular colloseum like, with pillars and other design features that make it feel epic").

Nothing here is gameplay: floor, podium ring, gates, lid and every device are build_bossmode.py's. Everything stands on or
above the podium top (out of reach under the arena's hidden lid) or flat against the podium face, except the floor
medallion (1-3 cm proud of the sand) and a pilaster each side of every gate arch (80 cm deep against the podium).

- Stands: SEAT_RINGS rings of the kit's stone seating block (Seats_02) on the podium top, each ring as many blocks as
  close its back edge; alternate blocks sit 1 cm higher so their overlapping treads never z-fight. Over the entry and at
  the boss end the first TERRACE_RINGS rings are flat stone blocks instead (TERRACES): a tower over the main gate, the
  tribune deck at the boss end.
- Crown: a walkway on the top ring, a colonnade of fluted marble columns (Column_02) carrying an entablature, PYLONS tall
  pylons (ExtWall_Column_01) each flying a pennant (Flag_01).
- Tribune (boss end, over the BOSS BATTLE sign): a balcony with railings, four columns, a canopy and back wall, curtains,
  the kit's giant gladiator statue and two small ones.
- Podium: a pilaster (Column_04 bottom + top) each side of every gate arch with a wall torch beside it, a llama statue
  over each gate, curtains on the marble row, braziers on the podium top.
- Floor: a marble medallion round the arena's centre.

Kit bounds at scale 1, measured in the editor 2026-10-09 (x across, y depth, z up from the pivot): Seats_02 512 x 542 x
392 (y 0..542 from its high back edge, the steps falling toward +Y), Column_02 142 x 175 x 527, Column_04 bottom 140 x
158 x 384 and top 142 x 160 x 383, ExtWall_Column_01 528 x 545 x 2336 (y -3..542), Flag_01 pole at the pivot and pennant
toward +X (568 tall), Curtains_01 446 x 256 hanging 273 below the pivot, WallTorch_01 y -80..192, Statue_Llama 183 x 533 x
684, CP_Coliseum_Statue_01 459 x 360 x 958, Statue_Gladiator 179 x 72 x 175, ExtWall_Railing_Str_01 532 x 35 x 115.

Idempotent via actor tag TAG (not build_bossmode's: a gameplay rebuild keeps this, and this reruns alone).
Materials: python tools/import_art.py bm_sand bm_stone bm_marble.

    python tools/build_colosseum.py           # (re)build the dressing
    python tools/build_colosseum.py --clear   # remove it
"""
import argparse
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import build_bossmode as b  # noqa: E402
import uefn_mcp as u  # noqa: E402
from build_course import ASSETS  # noqa: E402

TAG = "fnm_bm_colosseum"
P = "FNM_BMC_"
Z0 = b.FLOOR_Z
TOP = Z0 + b.WALL_H                         # the podium top
R = b.ARENA_R

SEATS = "Coliseum_Seats_02_0ed32e2a"
SEAT_W, SEAT_D, SEAT_H = 512, 537, 384
SEAT_RINGS = 4
SEAT_R0 = R + b.PODIUM_T                    # the first ring's front edge
SEAT_YAW = 90                               # added to the block's angle: its +Y (the falling steps) toward the centre
TERRACE_RINGS = 2
TERRACES = {"Entry": (270, 11), "Tribune": (90, 16)}   # centre angle, half width in degrees
CROWN_Z = TOP + SEAT_RINGS * SEAT_H         # the top ring's back edge
CROWN_SEGS = 48
WALK_IN = SEAT_R0 + SEAT_RINGS * SEAT_D - 30
WALK_OUT = WALK_IN + 520
COLUMN = "Coliseum_Column_02_1a8785d5"
COL_S = 1.3
COL_R = WALK_IN + 260
COL_TOP = CROWN_Z + 2 + 527 * COL_S
ENTAB_D, ENTAB_H = 260, 90
PYLON = "CP_Coliseum_ExtWall_Column_01_NoDestroy"
PYLON_S = 0.75
PYLONS = [(292.5 + 45 * i) % 360 for i in range(8)]
PYLON_CLEAR = 4.0                           # no colonnade column within this many degrees of a pylon
FLAG = "Coliseum_Flag_01"
FLAG_S = 2.0

TRIB_Z = TOP + TERRACE_RINGS * SEAT_H       # the tribune deck
TRIB_FRONT = b.CENTRE[1] + SEAT_R0          # its front face (y), due north
TRIB_COL_S = 1.4
TRIB_TOP = TRIB_Z + 527 * TRIB_COL_S
RAIL = "CP_Coliseum_ExtWall_Railing_Str_01_NoDestroy"
CURTAIN = "Coliseum_Curtains_01"
STATUE_BIG = "CP_Coliseum_Statue_01_52f08534"
STATUE_SMALL = "Coliseum_Statue_Gladiator_1ec91889"
STATUE_YAW = -90                            # the statues' faces toward the arena (-Y at the tribune)

COL4_BOT, COL4_TOP = "Coliseum_Column_04_Bottom_74658f94", "Coliseum_Column_04_Top_7531a576"
TORCH = "CP_Coliseum_WallTorch_01"
TORCH_Z = Z0 + 480
TORCH_DEG = 9.0                             # either side of a gate
LLAMA = "Coliseum_Statue_Llama"
LLAMA_S = 0.8
BRAZIER = "Coliseum_Brazier_01_FX_NoShadow"
BRAZIERS = (315, 225, 45, 135, 250, 290, 70, 110)
MEDALLION = 520                             # sand inside a marble ring round the centre (the pads stay outside 600)


# ---------------------------------------------------------------- pure layout (tests read these)

def ring_count(r_out):
    """Blocks in a ring whose back edge is r_out from the centre: enough to close it, even (the 1 cm alternation)."""
    n = math.ceil(2 * math.pi * r_out / SEAT_W)
    return n + n % 2


def seat_ring(k):
    """Ring k's blocks: [(deg, x scale, base z, terrace name or None)]. The x scale makes neighbouring back edges meet;
    odd rings are staggered half a block."""
    r_out = SEAT_R0 + (k + 1) * SEAT_D
    n = ring_count(r_out)
    sx = 2 * r_out * math.tan(math.pi / n) / SEAT_W
    step = 360 / n
    out = []
    for j in range(n):
        deg = (270 + (k % 2) * step / 2 + j * step) % 360
        out.append((deg, sx, TOP + k * SEAT_H + j % 2, terrace_of(deg) if k < TERRACE_RINGS else None))
    return out


def terrace_of(deg):
    for name, (centre, half) in TERRACES.items():
        if abs((deg - centre + 180) % 360 - 180) <= half:
            return name
    return None


def columns():
    """The colonnade's angles: every 360 / CROWN_SEGS degrees, none within PYLON_CLEAR of a pylon."""
    out = []
    for j in range(CROWN_SEGS):
        deg = (270 + j * 360 / CROWN_SEGS) % 360
        if all(abs((deg - p + 180) % 360 - 180) > PYLON_CLEAR for p in PYLONS):
            out.append(deg)
    return out


def curtain_slots():
    """Podium slots that carry a curtain: every other slot clear of the gates (and their torches), the main gate, the
    cannons and the sign under the tribune."""
    gates = {b.slot_of(g) for g in b.GATES}
    busy = {0, 1, b.SLOTS - 1, b.slot_of(0), b.slot_of(180)} | {(g + d) % b.SLOTS for g in gates for d in (-1, 0, 1)}
    busy |= {(b.slot_of(90) + d) % b.SLOTS for d in (-2, -1, 0, 1, 2)}
    busy |= {(b.slot_of(0) + d) % b.SLOTS for d in (-1, 1)} | {(b.slot_of(180) + d) % b.SLOTS for d in (-1, 1)}
    return [k for k in range(b.SLOTS) if k not in busy and k % 2 == 0]


# ---------------------------------------------------------------- build

def kit(name, label, x, y, z, yaw=0.0, sx=1.0, sy=None, sz=None):
    return b.kit(name, P + label, x, y, z, yaw, sx, sy or sx, sz or sx, tag=TAG)


def stands(mat):
    placed = terraces = 0
    for k in range(SEAT_RINGS):
        r_in, r_out = SEAT_R0 + k * SEAT_D, SEAT_R0 + (k + 1) * SEAT_D
        for j, (deg, sx, z, terrace) in enumerate(seat_ring(k)):
            if terrace:
                half = r_out * math.tan(math.pi / ring_count(r_out))
                b.rbox(f"{P}{terrace}{k}_{j:02d}", deg, r_in, r_out, -half, half, z, TOP + TERRACE_RINGS * SEAT_H + j % 2,
                       mat["bm_stone"], tag=TAG)
                if k == 0:      # its face: the podium's stone-and-marble bays again, flush with the podium face
                    w = 2 * r_in * math.tan(math.pi / ring_count(r_out)) * 1.04
                    x, y = b.polar(r_in - b.PODIUM_T / 2, deg)
                    kit(b.WALL_LOW, f"{terrace}Face{j:02d}_Low", x, y, TOP, deg + 90, w / b.KIT_W[b.WALL_LOW], 1.0, 1.0)
                    kit(b.WALL_HIGH, f"{terrace}Face{j:02d}_High", x, y, TOP + SEAT_H, deg + 90,
                        w / b.KIT_W[b.WALL_HIGH], 1.0, 1.0)
                terraces += 1
                continue
            kit(SEATS, f"Seat{k}_{j:02d}", *b.polar(r_out, deg), z, deg + SEAT_YAW, sx, 1.0, 1.0)
            placed += 1
    print(f"stands: {placed} seat blocks in {SEAT_RINGS} rings, {terraces} terrace blocks")


def crown(mat):
    step = 360 / CROWN_SEGS
    half = WALK_OUT * math.tan(math.pi / CROWN_SEGS)
    e_half = (COL_R + ENTAB_D / 2) * math.tan(math.pi / CROWN_SEGS)
    for j in range(CROWN_SEGS):
        deg = (270 + j * step) % 360
        b.rbox(f"{P}Walk{j:02d}", deg, WALK_IN, WALK_OUT, -half, half, CROWN_Z - 100, CROWN_Z + 2 + j % 2, mat["bm_stone"],
               tag=TAG)
        b.rbox(f"{P}Entab{j:02d}", deg + step / 2, COL_R - ENTAB_D / 2, COL_R + ENTAB_D / 2, -e_half, e_half, COL_TOP,
               COL_TOP + ENTAB_H + j % 2, mat["bm_marble"], tag=TAG)
    cols = columns()
    for j, deg in enumerate(cols):
        kit(COLUMN, f"Column{j:02d}", *b.polar(COL_R, deg), CROWN_Z + 2, deg + 90, COL_S)
    for j, deg in enumerate(PYLONS):
        kit(PYLON, f"Pylon{j}", *b.polar(COL_R - PYLON_S * 270, deg), CROWN_Z + 2, deg - 90, PYLON_S)
        kit(FLAG, f"Flag{j}", *b.polar(COL_R, deg), CROWN_Z + 2 + 2336 * PYLON_S, deg + 90, FLAG_S)
    print(f"crown: walkway and entablature in {CROWN_SEGS} segments, {len(cols)} columns, {len(PYLONS)} pylons with flags")


def tribune(mat):
    y0 = TRIB_FRONT
    b.box(f"{P}Balcony", -1000, 1000, y0 - 110, y0 + 80, TRIB_Z - 40, TRIB_Z + 3, mat["bm_marble"], tag=TAG)
    for n, x in enumerate((-788, -256, 276, 808)):
        kit(RAIL, f"Rail{n}", x - 10, y0 - 108, TRIB_Z + 3, 0)
    for n, (x, y) in enumerate(((-850, y0), (850, y0), (-850, y0 + 920), (850, y0 + 920))):
        kit(COLUMN, f"TribColumn{n}", x, y, TRIB_Z + 3, 0, TRIB_COL_S)
    b.box(f"{P}Canopy", -1050, 1050, y0 - 100, y0 + 1080, TRIB_TOP, TRIB_TOP + 80, mat["bm_marble"], tag=TAG)
    b.box(f"{P}TribBack", -1000, 1000, y0 + 1010, y0 + 1074, TRIB_Z, TRIB_TOP, mat["bm_marble"], tag=TAG)
    for n, x in enumerate((-450, 450)):
        kit(CURTAIN, f"TribCurtain{n}", x, y0 - 60, TRIB_TOP - 128, 0)
    kit(STATUE_BIG, "TribStatue", 0, y0 + 650, TRIB_Z + 3, STATUE_YAW, 0.72)
    for n, x in enumerate((-520, 520)):
        kit(STATUE_SMALL, f"TribGladiator{n}", x, y0 + 200, TRIB_Z + 3, STATUE_YAW, 2.2)
    print("tribune: balcony, railings, 4 columns, canopy, curtains, 3 statues")


def podium():
    for k, deg in enumerate(b.GATES, 1):
        for side, d in (("A", -5.0), ("B", 5.0)):
            x, y = b.polar(R - 80, deg + d)
            kit(COL4_BOT, f"Gate{k}_Pilaster{side}", x, y, Z0, deg + 90)
            kit(COL4_TOP, f"Gate{k}_Capital{side}", x, y, Z0 + 384, deg + 90)
            kit(TORCH, f"Gate{k}_Torch{side}", *b.polar(R, deg + (TORCH_DEG if d > 0 else -TORCH_DEG)), TORCH_Z, deg + 90)
        kit(LLAMA, f"Gate{k}_Llama", *b.polar(R + b.PODIUM_T / 2, deg), TOP, deg, LLAMA_S)
    slots = curtain_slots()
    for k in slots:
        deg = b.slot_angle(k)
        kit(CURTAIN, f"Curtain{k:02d}", *b.polar(R - 128, deg), TOP - 128, deg + 90)
    for n, deg in enumerate(BRAZIERS):
        kit(BRAZIER, f"Brazier{n}", *b.polar(R + b.PODIUM_T / 2, deg), TOP, deg + 90)
    print(f"podium: pilasters, torches and a llama at {len(b.GATES)} gates, {len(slots)} curtains, {len(BRAZIERS)} braziers")


def floor(mat):
    b.disc(f"{P}MedallionRing", MEDALLION + 80, Z0, Z0 + 2, mat["bm_marble"], tag=TAG)
    b.disc(f"{P}MedallionSand", MEDALLION, Z0, Z0 + 2.5, mat["bm_sand"], tag=TAG)
    b.disc(f"{P}MedallionBoss", 140, Z0, Z0 + 3, mat["bm_marble"], tag=TAG)
    print("floor: medallion")


def build():
    mat = b.materials(("bm_sand", "bm_stone", "bm_marble"))
    print("removed", b.clear(TAG), "old colosseum actors")
    floor(mat)
    podium()
    stands(mat)
    crown(mat)
    tribune(mat)
    u.call(ASSETS, "save_assets", {"asset_paths": []})
    print(f"colosseum: {len(b.placed(TAG))} actors tagged {TAG}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--clear", action="store_true", help="remove the dressing")
    a = ap.parse_args()
    print("removed", b.clear(TAG)) if a.clear else build()
