"""The boss arena's layout constants (tools/build_course.py, maps/starter/LAYOUT.md "Boss arena") keep its pieces apart and
inside the hall, and the tag/cue names the director looks for are declared."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

import build_course as c  # noqa: E402


def _rect(cx, cy, w, d):
    return (cx - w / 2, cx + w / 2, cy - d / 2, cy + d / 2)


def _overlap(a, b):
    return a[0] < b[1] and b[0] < a[1] and a[2] < b[3] and b[2] < a[3]


def test_pads_inside_the_hall_and_apart():
    half = 4 * c.DOOR_W / 2
    pads = [_rect(x, y, c.PAD_SIZE, c.PAD_SIZE) for x, y in c.PAD_SPOTS]
    platform = _rect(0, c.PLATFORM_Y, c.PLATFORM_W, c.PLATFORM_D)
    assert len(pads) == 4
    for p in pads:
        assert -half < p[0] and p[1] < half, p
        assert 450 < p[2] and p[3] < c.GATE_Y, p          # past where players land (entry + 300), before the gate
        assert not _overlap(p, platform)
    for i, p in enumerate(pads):
        for q in pads[i + 1:]:
            assert not _overlap(p, q)
    assert platform[3] < c.GATE_Y


def test_pad_letters_read_like_the_doors():
    # +X is the player's left: A and C on the left, then B and D, the near row first (A B, then C D).
    (ax, ay), (bx, by), (cx, cy), (dx, dy) = c.PAD_SPOTS
    assert ax > bx and cx > dx
    assert ay == by < cy == dy


def test_one_boss_and_two_adds():
    assert c.BOSS_SETTINGS["spawnCount"] == 1 and c.BOSS_SETTINGS["totalSpawnLimit"] == 1
    assert c.BOSS_SETTINGS["showHealthBar"] is True and c.BOSS_SETTINGS["enablePatrol"] is False
    assert c.ADDS_SETTINGS["spawnCount"] == 2
    # Aaron 2026-10-07 could not beat the legendary-AR boss: it now carries a weapon the spawner accepts (build_guards.WEAPONS)
    # that is neither a sniper nor a launcher (no one-shot kills); the purple SMG today.
    import build_guards as g
    assert c.BOSS_WEAPON in g.WEAPONS and "Sniper" not in c.BOSS_WEAPON and "Launcher" not in c.BOSS_WEAPON


def test_arena_tags_declared():
    tags = (ROOT / "console" / "verse" / "fnm_tags.verse").read_text(encoding="utf-8")
    for name in ("fnm_boss", "fnm_boss_spawner", "fnm_boss_adds", "fnm_boss_gate",
                 "fnm_cannon_fx", "fnm_cannon_strike", "fnm_cannon_blast"):
        assert f"{name} := class(tag){{}}" in tags


def test_cannons_on_the_walls_short_of_the_platform():
    """The laser cannons (tools/build_cannon.py) hang on the walls between the entry and the boss platform, under the
    wall tops and the glass lid, and their blast does no damage (the math is the only weapon)."""
    import build_cannon as cn
    assert 450 < cn.CANNON_Y < c.PLATFORM_Y - c.PLATFORM_D / 2
    assert cn.CANNON_Z + cn.BALL_D + cn.RING_D < c.WALL_H
    assert cn.CANNON_IN + cn.BALL_D / 2 < c.PAD_SPOTS[0][0] - c.PAD_SIZE / 2 + 1500   # off the wall, over the pad row
    assert cn.BLAST["player Damage"] == 0 and cn.BLAST["structure Damage"] == 0 and cn.BLAST["visible During Game"] is False
    assert cn.MUZZLE_FX["enabled On Phase"] == "None" and cn.STRIKE_FX["enabled On Phase"] == "None"
    assert cn.BLASTS >= 1
