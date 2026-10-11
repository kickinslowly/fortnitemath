"""The boss battle arena's layout constants (tools/build_bossmode.py, BOSS_MODE.md 3, maps/starter/LAYOUT.md "Boss battle
arena") keep its pieces inside the walls and apart, the jump chain within reach, the spawners' settings as the director
expects, and every Verse tag the tool writes declared."""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

import build_bossmode as b  # noqa: E402
import build_course as c  # noqa: E402
import build_guards as g  # noqa: E402

CX, CY = b.CENTRE


def _rect(cx, cy, w, d):
    return (cx - w / 2, cx + w / 2, cy - d / 2, cy + d / 2)


def _overlap(a, q):
    return a[0] < q[1] and q[0] < a[1] and a[2] < q[3] and q[2] < a[3]


def _inside(r, margin=0):
    """Every corner of the rect on the sand, margin short of the podium's inner face."""
    return all(((x - CX) ** 2 + (y - CY) ** 2) ** 0.5 < b.ARENA_R - margin for x in r[:2] for y in r[2:])


def _off(deg, d):
    return abs((deg - d + 180) % 360 - 180)


PADS = [_rect(x, y, c.PAD_SIZE, c.PAD_SIZE) for x, y in b.PAD_SPOTS]
PLATFORM = _rect(b.PLATFORM_X, b.PLATFORM_Y, b.PLATFORM_W, b.PLATFORM_D)
PERCHES = [_rect(x, y, b.PERCH_TOP, b.PERCH_TOP) for x, y, _ in b.PERCHES]
STONES = [_rect(x, y, b.STONE, b.STONE_D) for p in b.PERCHES for x, y, _ in b.stones_for(p)]


def test_pads_inside_apart_and_clear_of_everything():
    assert len(PADS) == 4
    entry = _rect(*b.ENTRY, 300, 300)
    for pad in PADS:
        assert _inside(pad), pad
        for other in [PLATFORM, entry] + PERCHES + STONES:
            assert not _overlap(pad, other), (pad, other)
    for i, pad in enumerate(PADS):
        for q in PADS[i + 1:]:
            assert not _overlap(pad, q)


def test_pad_letters_read_like_the_doors():
    # +X is the player's left: A and C on the left, the near row A B, the far row C D.
    (ax, ay), (bx, by), (cx, cy), (dx, dy) = b.PAD_SPOTS
    assert ax > bx and cx > dx
    assert ay == by < cy == dy


def test_perches_inside_the_walls_and_off_the_gates():
    assert len(b.PERCHES) == 4
    for (px, py, top), r in zip(b.PERCHES, PERCHES):
        assert _inside(r, 100), r            # a player fits round the perch's outer corner
        assert not _overlap(r, PLATFORM)
        for deg in b.GATES:                  # a gate's mouth stays 10 m clear: creatures pour out of it
            gx, gy = b.polar(b.ARENA_R, deg)
            assert ((px - gx) ** 2 + (py - gy) ** 2) ** 0.5 > 1000, (px, py, deg)
    for s in STONES:
        assert _inside(s) and not _overlap(s, PLATFORM)


def test_stone_chain_is_jumpable():
    """Each hop up the chain (floor -> stones -> perch top) rises at most 70 cm (a 70 cm hurdle is cleared with a running
    jump, LAYOUT "Hallway obstacles") over an edge gap of at most 200 cm."""
    assert b.STONE_RISE <= 70 and b.STONE_GAP <= 200
    # B6 keys test: 60 / 150 with 120 cm wide stones was not climbable by a run-and-jump; 50 / 100, stones perch-wide
    assert b.STONE_RISE <= 50 and b.STONE_GAP <= 100 and b.STONE_D >= b.PERCH_TOP
    for perch in b.PERCHES:
        px, py, top = perch
        stones = b.stones_for(perch)
        assert stones, perch
        heights = [0] + [h for _, _, h in reversed(stones)] + [top]
        rises = [hi - lo for lo, hi in zip(heights, heights[1:])]
        assert all(0 < r <= 70 for r in rises), (perch, rises)
        edges = [px] + [x for x, _, _ in stones]
        sizes = [b.PERCH_TOP] + [b.STONE] * len(stones)
        for (x0, s0), (x1, s1) in zip(zip(edges, sizes), zip(edges[1:], sizes[1:])):
            assert abs(x1 - x0) - (s0 + s1) / 2 <= 200
        # laid toward the centre line: the lowest stone is nearest x = 0
        assert abs(stones[-1][0]) < abs(stones[0][0]) < abs(px)


def test_gates_on_the_sides_each_on_an_arch_bay():
    """G1 right-front, G2 left-front, G3 right-back, G4 left-back (right = -X, front = the entry half), each centred on a
    podium slot, clear of the main gate (slot 0), the tribune (90) and the cannon bays."""
    assert len(b.GATES) == 4
    xs = [b.polar(b.ARENA_R, d)[0] for d in b.GATES]
    ys = [b.polar(b.ARENA_R, d)[1] for d in b.GATES]
    assert xs[0] < 0 < xs[1] and xs[2] < 0 < xs[3]
    assert ys[0] < b.CENTRE[1] < ys[2] and ys[1] < b.CENTRE[1] < ys[3]
    slots = [b.slot_of(d) for d in b.GATES]
    assert len(set(slots)) == 4
    for k in slots:
        assert min(k, b.SLOTS - k) > 2
        assert abs(k - b.slot_of(90)) > 2
        assert abs(k - b.slot_of(0)) > 1 and abs(k - b.slot_of(180)) > 1
    assert b.GATE_H < b.WALL_H
    # the stretched arch's opening (~75 % of its height) is the way out; the alcove behind is taller and wider
    assert 0.7 * b.ROW_H * b.ARCH_SZ < b.GATE_H
    assert 0.7 * b.BAY < b.GATE_W < b.BAY


def test_podium_ring_closes():
    """SLOTS bays BAY wide at the inner face close the ring; each kit piece is scaled to it."""
    import math
    assert abs(b.SLOTS * 2 * b.ARENA_R * math.tan(math.pi / b.SLOTS) - b.SLOTS * b.BAY) < 1e-6
    assert all(0.95 < b.BAY_W / w < 1.1 for w in b.KIT_W.values())
    # a bay at its depth spans at least its slot's chord at the podium's back face
    assert b.BAY_W > 2 * (b.ARENA_R + b.PODIUM_T) * math.tan(math.pi / b.SLOTS)
    assert b.WALL_H == 2 * b.ROW_H
    assert [b.slot_angle(b.slot_of(d)) for d in b.GATES] == b.GATES


def test_mega_cannons_in_view_and_clear_of_gates_and_perches():
    """BOSS_MODE 15d: the mega cannons stand on the sand at CANNON_DEG / 180 - CANNON_DEG, inside the podium, in frame for a
    player at the entry (under ~40 degrees off the view's centre), clear of every gate mouth and perch."""
    import math
    for deg in (b.CANNON_DEG, 180 - b.CANNON_DEG):
        x, y = b.polar(b.CANNON_R, deg)
        tail = b.CANNON_R + b.CANNON_SCALE * 95          # its tail at worst points straight at the wall
        assert tail < b.ARENA_R, tail
        assert math.degrees(math.atan2(abs(x), y - b.ENTRY[1])) < 40
        for g_deg in b.GATES:
            assert _off(deg, g_deg) >= 15, (deg, g_deg)
        for px, py, _ in b.PERCHES:
            assert math.hypot(px - x, py - y) > b.PERCH_TOP / 2 + b.CANNON_SCALE * 48, (deg, px, py)


def test_gate_weapons_accepted():
    """The per-level guard bosses and their weapons are gone (BOSS_MODE 15: one Megabrute, under the titan); the gate
    guards' weapons must still be ones the guard spawner takes."""
    accepted = set(g.WEAPONS) | {b._W.format(n) for n in ("WID_Assault_Heavy_Athena_VR_Ore_T03", "WID_Assault_Heavy_Athena_R_Ore_T03")}
    for w in b.GATE_WEAPONS:
        assert w in accepted, w
    assert not hasattr(b, "BOSS_WEAPONS")


def test_gate_settings():
    s = b.GATE_SETTINGS
    assert s["spawnOnTimer"] is False and s["despawnGuardsWhenDisabled"] is True and s["spawnCount"] == 2
    assert s["guardTeamOption"] == g.SETTINGS["guardTeamOption"]
    # the boss is the pinned Megabrute (BOSS_MODE 15), off until SpawnBoss pulses it
    assert b.MEGABOSS_SETTINGS["creature Type"] == b.MEGABOSS
    assert b.CREATURE_SETTINGS["enabled at Game Start"] is False


def test_guards_bosses_and_creatures_are_one_team():
    """Aaron 2026-10-09: monsters and guards all hunt the player, never each other. The creature spawner has no team
    option, its creatures are on Wildlife & Creatures; gate guards and every boss must be on that team too."""
    assert b.TEAM == "Team Wildlife & Creatures"
    assert b.GATE_SETTINGS["guardTeamOption"] == b.TEAM
    src = Path(b.__file__).read_text(encoding="utf-8")
    # the boss spawners are written with the team named explicitly (not left to the device default "Team Index")
    assert '{**BOSS_SETTINGS, "guardTeamOption": TEAM}' in src
    assert "guardTeamOption" not in c.BOSS_SETTINGS or c.BOSS_SETTINGS["guardTeamOption"] == b.TEAM


def test_gate_guards_drop_nothing_race_guards_still_do():
    """Dropped gate-guard guns littered the arena and Verse cannot remove a dropped pickup: gate guards drop nothing.
    The boss keeps BOSS_SETTINGS (drops nothing, as before) and the race course's guards are unchanged."""
    assert b.GATE_SETTINGS["dropInventoryOnElimination"] is False
    assert c.BOSS_SETTINGS["dropInventoryOnElimination"] is False
    assert g.SETTINGS["dropInventoryOnElimination"] is True
    assert g.SETTINGS["guardTeamOption"] == "Team Wildlife & Creatures"


def test_grant_weapons_follow_the_level_table():
    spec = (ROOT / "BOSS_MODE.md").read_text(encoding="utf-8")
    rows = [line for line in spec.splitlines() if re.match(r"\| [1-5] \| \d \|", line)]
    assert len(rows) == 5
    perch_wids = [re.findall(r"WID_\w+", row)[-1] for row in rows]   # the weapon-perch column is the last WID in a row
    assert [w.rsplit(".", 1)[1] for w in b.GRANT_WEAPONS] == perch_wids
    assert b.GRANT_SETTINGS["equipItemOnGrant"] == 1


def test_every_tag_the_tool_writes_is_declared():
    tags = (ROOT / "console" / "verse" / "fnm_tags.verse").read_text(encoding="utf-8")
    src = (ROOT / "tools" / "build_bossmode.py").read_text(encoding="utf-8")
    names = set(re.findall(r'"(fnm_[a-z0-9_]+)"', src)) - {b.TAG, b.DRESS_TAG, b.BOSS_RIG_TAG, "fnm_test"}   # actor tags, not Verse tags
    names |= {f"fnm_bm_slot_{k}" for k in range(1, 6)} | {f"fnm_door_{x}" for x in "abcd"}
    assert "fnm_bm_gate" in names and "fnm_bm_beam" in names
    for name in sorted(names):
        assert f"{name} := class(tag){{}}" in tags, name


def test_fallbacks():
    assert b.nuke_effect(["Fireworks_Deprecated", "LaserBeams", "Small_Fire", "FireworksLarge"]) == "Small_Fire"
    assert b.nuke_effect(["LaserBeams", "LightningBolt_01"]) == "LightningBolt_01"
    assert b.knockback(["None", "Medium", "High", "Very High"]) == "High"
    assert b.knockback(["None", "Medium"]) == "Medium"


def test_no_tool_imports_the_retired_cannon_builder():
    """tools/build_cannon.py is gone (the race finale has the mega cannons too since 2026-10-11, tools/build_race_boss.py);
    its constants live in build_bossmode now."""
    for path in (ROOT / "tools").glob("*.py"):
        assert "import build_cannon" not in path.read_text(encoding="utf-8"), path.name
    assert b.STRIKE_FX["visual_Effect"] == "LightningBolt_03" and b.BOSS_EYE == 90


def test_creature_spawners_in_the_alcoves_off_and_lasting():
    """One creature spawner per kind, on the floor of a gate alcove (SpawnAt was refused for a device under the floor),
    invisible, off at game start, a wide activation range (1 refused every SpawnAt), creatures never despawn on distance."""
    s = b.CREATURE_SETTINGS
    assert len(b.CREATURES) == 5 and len(set(b.CREATURES)) == 5 and "Megabrute" not in b.CREATURES
    assert s["enabled at Game Start"] is False and s["spawner Visibility"] is False and s["invincible Spawner"] is True
    assert s["despawn Type"] == "Do Not Despawn"
    # Limit off made GetSpawnLimit() 0 and SpawnAt refused every creature (2026-10-09 run): on, at the most.
    assert s["limit Spawned Creatures"] is True and s["enum Total Spawn Limit"] == "100"
    assert s["total Spawn Limit"] == 100
    assert s["damage Spawner After Spawn"] is False and s["number of Creatures"] == 1
    assert s["activation Range"] >= 100
    import math
    for x, y, gate in b.creature_spots():
        a = math.radians(b.GATES[gate - 1])
        dx, dy = x - b.CENTRE[0], y - b.CENTRE[1]
        u, v = dx * math.cos(a) + dy * math.sin(a), -dx * math.sin(a) + dy * math.cos(a)
        assert b.ARENA_R + b.PODIUM_T < u < b.ARENA_R + b.PODIUM_T + b.ALCOVE_D       # inside that gate's alcove
        assert abs(v) < b.GATE_W / 2 - 50
    assert len({(x, y) for x, y, _ in b.creature_spots()}) == 5
    assert "creature Type" not in s                      # set per kind
    assert b.KNOCKBACK_WANT == "High"


def test_trigger_detection_box_covers_the_pad_and_the_perch_top():
    """The trigger's detection box is its StepBox (extent 64 x 64 x 15 at z +32, scaled with the actor). B2's 600 cm per
    unit scale sensed only a 64 cm square on a 3 m perch (a player standing on it never triggered it, B6 2026-10-09)."""
    def box(z, w, d, h):
        dz, sx, sy, sz = b.trigger_fit(z, w, d, h)
        cz = dz + b.STEP_Z * sz
        return 2 * b.STEP_BOX[0] * sx, 2 * b.STEP_BOX[1] * sy, cz - b.STEP_BOX[2] * sz, cz + b.STEP_BOX[2] * sz
    w, d, lo, hi = box(b.FLOOR_Z + 180, b.PERCH_TOP, b.PERCH_TOP, b.PERCH_TRIGGER_H)
    assert (round(w), round(d), round(lo), round(hi)) == (300, 300, 182, 382)
    w, d, lo, hi = box(b.FLOOR_Z, c.PAD_SIZE, c.PAD_SIZE, c.PAD_H)
    assert (round(w), round(d), round(lo), round(hi)) == (c.PAD_SIZE, c.PAD_SIZE, 2, 2 + c.PAD_H)
    # disproof of the old recipe: scale w / 600 gives a box a fraction of the perch
    assert 2 * b.STEP_BOX[0] * (b.PERCH_TOP / 600) < b.PERCH_TOP / 2


def test_niagara_laser_length_matches_the_cannons():
    """NS_fnm_laser's beam is baked (Verse cannot set its user parameters): its length must be the mega cannons'
    muzzle-to-waist distance (BOSS_MODE 15f), within 30 cm. Rebuild with tools/build_fx.py after moving a cannon."""
    import math
    import build_fx
    ax, ay, _ = b.boss_aim()
    tz = b.FLOOR_Z + b.PLATFORM_H + b.BEAM_AIM
    bx, by = b.polar(b.CANNON_R, b.CANNON_DEG)
    heading = math.atan2(ay - by, ax - bx)
    f = b.CANNON_MUZZLE[1] * b.CANNON_SCALE + b.MUZZLE_AHEAD
    mx, my = bx + f * math.cos(heading), by + f * math.sin(heading)
    mz = b.FLOOR_Z + b.CANNON_HALF_H * b.CANNON_SCALE + b.CANNON_MUZZLE[2] * b.CANNON_SCALE
    assert abs(math.hypot(ax - mx, ay - my, tz - mz) - build_fx.LENGTH) < 30
    assert all(abs(p - q) < 1e-6 for p, q in zip(b.muzzle_point(b.CANNON_DEG), (mx, my, mz)))


def test_coil_crackle_sits_on_the_coils():
    """BOSS_MODE 15g: Verse puts NS_fnm_coil FnmCannonCoilBack behind the beam's muzzle point on the shot's level heading
    (fnm_fx FnmBehindOnBarrel). That must land on CANNON_COIL for both cannons: the barrel is level, its heading is the
    shot's (aim and platform share x, y), and coil and muzzle share a height."""
    import math
    import re
    verse = (ROOT / "console" / "verse" / "fnm_fx.verse").read_text(encoding="utf-8")
    back = float(re.search(r"^FnmCannonCoilBack : float = ([0-9.]+)$", verse, re.M).group(1))
    assert back == (b.CANNON_MUZZLE[1] - b.CANNON_COIL[1]) * b.CANNON_SCALE + b.MUZZLE_AHEAD
    assert b.boss_aim()[:2] == (b.PLATFORM_X, b.PLATFORM_Y)
    for _, deg in b.CANNON_SIDES:
        _, _, _, point = b.cannon_frame(deg)
        mx, my, mz = b.muzzle_point(deg)
        ax, ay = b.PLATFORM_X, b.PLATFORM_Y              # the beam's aim, as boss_rig lays it
        flat = math.hypot(ax - mx, ay - my)
        coil = (mx - (ax - mx) / flat * back, my - (ay - my) / flat * back, mz)
        assert math.dist(coil, point(b.CANNON_COIL)) < 1.0, (deg, coil, point(b.CANNON_COIL))
    # disproof: the coil is not the muzzle (a zero offset would pass a sloppier check)
    assert math.dist(b.muzzle_point(b.CANNON_DEG), b.cannon_frame(b.CANNON_DEG)[3](b.CANNON_COIL)) > 200


def test_cannons_place_no_vfx_spawners():
    """BOSS_MODE 15g: the cannons' muzzle burst, zap and coil crackle are Niagara now; cannons() places only the mesh
    and the two lights."""
    import inspect
    src = inspect.getsource(b.cannons)
    assert "device(VFX" not in src and "vfx(" not in src and "fnm_bm_cannon_fx" not in src and "Crackle" not in src and "_Zap" not in src
    assert "POINT_LIGHT" in src and "CANNON_ART" in src
