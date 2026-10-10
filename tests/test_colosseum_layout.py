"""The colosseum dressing (tools/build_colosseum.py) closes its rings, keeps out of play, and clears the gates, pads
and sign."""
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

import build_bossmode as b  # noqa: E402
import build_colosseum as k  # noqa: E402
import build_course as c  # noqa: E402

HEAD = 300      # nothing hangs lower than this over the sand


def test_seat_rings_close_and_alternate():
    for ring in range(k.SEAT_RINGS):
        blocks = k.seat_ring(ring)
        n = len(blocks)
        r_out = k.SEAT_R0 + (ring + 1) * k.SEAT_D
        assert n % 2 == 0
        assert n * k.SEAT_W >= 2 * math.pi * r_out                     # enough blocks to go round
        sx = blocks[0][1]
        assert sx * k.SEAT_W >= 2 * r_out * math.tan(math.pi / n) - 1e-6  # back edges meet: no gaps
        assert 0.9 < sx <= 1.0
        zs = [z for _, _, z, _ in blocks]
        assert zs[0::2] == [zs[0]] * (n // 2) and zs[1::2] == [zs[0] + 1] * (n // 2)
        assert zs[0] == k.TOP + ring * k.SEAT_H
    # each ring starts where the last one's back edge stands, one rise up
    assert k.SEAT_R0 == b.ARENA_R + b.PODIUM_T and k.CROWN_Z == k.TOP + k.SEAT_RINGS * k.SEAT_H


def test_terraces_only_over_the_entry_and_the_tribune():
    for ring in range(k.SEAT_RINGS):
        for deg, _, _, terrace in k.seat_ring(ring):
            if ring >= k.TERRACE_RINGS:
                assert terrace is None
            elif terrace:
                centre, half = k.TERRACES[terrace]
                assert abs((deg - centre + 180) % 360 - 180) <= half
    names = {t for ring in range(k.TERRACE_RINGS) for *_, t in k.seat_ring(ring) if t}
    assert names == {"Entry", "Tribune"}
    # the main gate (1051 wide, 1270 tall) fits under the entry tower's window and below its top
    assert 2 * math.radians(k.TERRACES["Entry"][1]) * k.SEAT_R0 > 1051
    assert k.TOP + k.TERRACE_RINGS * k.SEAT_H > 1270
    # the tribune stands over the BOSS BATTLE sign
    assert k.TERRACES["Tribune"][0] == 90 and abs(b.SIGN[0]) < 100 and b.SIGN[1] < k.TRIB_FRONT


def test_colonnade_clears_the_pylons_and_rises_in_order():
    cols = k.columns()
    assert len(cols) >= 30
    for deg in cols:
        assert all(abs((deg - p + 180) % 360 - 180) > k.PYLON_CLEAR for p in k.PYLONS)
    assert k.WALK_IN < k.SEAT_R0 + k.SEAT_RINGS * k.SEAT_D < k.COL_R < k.WALK_OUT
    assert k.CROWN_Z < k.COL_TOP < k.CROWN_Z + 2336 * k.PYLON_S       # pylons stand over the entablature
    assert len(k.PYLONS) == 8 and all(abs((p - 270 + 180) % 360 - 180) > 15 for p in k.PYLONS)


def test_nothing_hangs_into_play():
    assert k.TORCH_Z > HEAD
    assert k.TOP - 128 - 273 > HEAD                     # the podium curtains' hems
    assert k.TRIB_Z > b.WALL_H                          # the tribune is above the podium
    for slot in k.curtain_slots():                      # curtains keep off gates, cannons, the main gate and the sign
        deg = b.slot_angle(slot)
        assert all(abs((deg - g + 180) % 360 - 180) > 10 for g in b.GATES)
        assert all(abs((deg - d + 180) % 360 - 180) > 10 for d in (0, 180, 270))
        assert abs((deg - 90 + 180) % 360 - 180) > 20


def test_gate_pilasters_flank_the_arch_opening():
    # a pilaster at +-5 degrees stands R sin 5 off the gate's axis: past the arch's opening (~65 % of the bay) plus its
    # own half width (71)
    off = b.ARENA_R * math.sin(math.radians(5))
    assert off - 71 > 0.65 * b.BAY / 2
    assert k.TORCH_DEG > 5


def test_medallion_clear_of_the_pads_and_braziers_clear_of_the_gates():
    cx, cy = b.CENTRE
    h = c.PAD_SIZE / 2
    for x, y in b.PAD_SPOTS:
        nx = min(max(cx, x - h), x + h)
        ny = min(max(cy, y - h), y + h)
        assert math.hypot(nx - cx, ny - cy) > k.MEDALLION + 80
    for deg in k.BRAZIERS:
        assert all(abs((deg - g + 180) % 360 - 180) > 15 for g in b.GATES)
        assert k.terrace_of(deg) is None


def test_kit_pieces_are_the_measured_ones():
    """Every kit asset the tools place was measured in the editor (2026-10-09 survey); a typo would fail at build time
    half way through."""
    measured = {"Coliseum_Seats_02_0ed32e2a", "Coliseum_Column_02_1a8785d5", "CP_Coliseum_ExtWall_Column_01_NoDestroy",
                "Coliseum_Flag_01", "CP_Coliseum_ExtWall_Railing_Str_01_NoDestroy", "Coliseum_Curtains_01",
                "CP_Coliseum_Statue_01_52f08534", "Coliseum_Statue_Gladiator_1ec91889", "Coliseum_Column_04_Bottom_74658f94",
                "Coliseum_Column_04_Top_7531a576", "CP_Coliseum_WallTorch_01", "Coliseum_Statue_Llama",
                "Coliseum_Brazier_01_FX_NoShadow", "Coliseum_Wall_01", "Coliseum_Wall_02_277f0639",
                "Coliseum_Arch_02_27fb14b8", "Coliseum_Wall_04_4f283961", "CP_Coliseum_ExtWall_MainGate_01_NoDestroy"}
    used = {k.SEATS, k.COLUMN, k.PYLON, k.FLAG, k.RAIL, k.CURTAIN, k.STATUE_BIG, k.STATUE_SMALL, k.COL4_BOT, k.COL4_TOP,
            k.TORCH, k.LLAMA, k.BRAZIER, b.WALL_LOW, b.WALL_HIGH, b.GATE_ARCH, b.GATE_FILL, b.MAIN_GATE}
    assert used <= measured, used - measured
