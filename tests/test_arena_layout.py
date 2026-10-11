"""The boss arena's layout constants (tools/build_course.py, maps/starter/LAYOUT.md "Boss arena") keep its pieces apart and
inside the hall, and the tag/cue names the director looks for are declared."""
import re
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


def test_two_adds_and_no_guard_boss_from_the_course():
    """The adds stay two pistol guards; since 2026-10-11 the boss is tools/build_race_boss.py's Megabrute under the titan,
    so a course rebuild places neither the old guard boss spawner nor the letter billboards (BOSS_MODE.md 16)."""
    import inspect
    import build_guards as g
    assert c.ADDS_SETTINGS["spawnCount"] == 2 and c.ADDS_WEAPON in g.WEAPONS
    src = inspect.getsource(c.arena)
    assert "FNM_Arena_Boss" not in src and "FNM_Arena_Label" not in src and "fnm_boss_spawner" not in src
    assert "FNM_Arena_Adds" in src and "FNM_Arena_Platform" in src
    assert not hasattr(c, "BOSS_WEAPON") and not hasattr(c, "PAD_BOARD_Z")


def test_arena_tags_declared():
    tags = (ROOT / "console" / "verse" / "fnm_tags.verse").read_text(encoding="utf-8")
    for name in ("fnm_boss", "fnm_boss_adds", "fnm_boss_gate", "fnm_cannon_strike", "fnm_cannon_blast",
                 "fnm_race_megaboss", "fnm_race_titan", "fnm_race_beam", "fnm_race_letter",
                 # retired, still declared so a level holding the old devices loads until build_race_boss removes them
                 "fnm_boss_spawner", "fnm_cannon_fx"):
        assert f"{name} := class(tag){{}}" in tags


def test_the_blasts_do_no_damage():
    """The strike and blasts the race arena keeps (tools/build_race_boss.py takes them from build_bossmode): no damage,
    the math is the only weapon; the strike waits off until Verse fires it. The engine-shape cannons are gone."""
    import build_bossmode as b
    assert b.BLAST["player Damage"] == 0 and b.BLAST["structure Damage"] == 0 and b.BLAST["visible During Game"] is False
    assert b.BLAST["knockback"] == "Medium"      # the race's; boss mode raises it to High at build time
    assert b.STRIKE_FX["enabled On Phase"] == "None" and b.BLASTS >= 1
    assert not (ROOT / "tools" / "build_cannon.py").exists()


def test_every_trigger_is_sized_by_its_stepbox():
    """A trigger senses only its StepBox (build_course.trigger_fit). Until 2026-10-09 the course sized triggers at 600 cm per
    unit scale: an arena pad sensed a 96 cm square inside its 450 cm tile. No builder or director line may assume it."""
    root = ROOT
    for name in ("build_course.py", "build_pickups.py", "build_bossmode.py"):
        src = (root / "tools" / name).read_text(encoding="utf-8")
        assert not re.search(r"(sx|sy|sz)=[^,)]*/ ?600\b", src), name
        assert "v / 600" not in src, name
    verse = (root / "console" / "verse" / "fnm_director.verse").read_text(encoding="utf-8")
    assert "300.0 * Zone.Scale" not in verse
    dz, sx, sy, sz = c.trigger_fit(2, c.PAD_SIZE, c.PAD_SIZE, c.PAD_H)
    centre = dz + c.STEP_Z * sz
    assert round(2 * c.STEP_BOX[0] * sx) == c.PAD_SIZE and round(centre - c.STEP_BOX[2] * sz) == 2
