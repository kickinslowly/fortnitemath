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

HW = b.ARENA_W / 2


def _rect(cx, cy, w, d):
    return (cx - w / 2, cx + w / 2, cy - d / 2, cy + d / 2)


def _overlap(a, q):
    return a[0] < q[1] and q[0] < a[1] and a[2] < q[3] and q[2] < a[3]


def _inside(r):
    return -HW < r[0] and r[1] < HW and 0 < r[2] and r[3] < b.ARENA_L


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
        assert _inside(r)
        assert not _overlap(r, PLATFORM)
        for side, gy in b.GATES:
            mouth = (min(side * HW, side * (HW - 400)), max(side * HW, side * (HW - 400)), gy - b.GATE_W / 2, gy + b.GATE_W / 2)
            assert not _overlap(r, mouth), (px, py, gy)
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


def test_gates_on_the_side_walls():
    assert len(b.GATES) == 4
    assert {s for s, _ in b.GATES} == {1, -1}
    for side, gy in b.GATES:
        assert 0 < gy - b.GATE_W / 2 and gy + b.GATE_W / 2 < b.ARENA_L
        assert b.GATE_H < b.WALL_H


def test_cannons_on_the_walls_short_of_the_platform():
    import build_cannon as cn
    assert 0 < b.CANNON_Y < b.PLATFORM_Y - b.PLATFORM_D / 2
    assert cn.CANNON_Z + cn.BALL_D + cn.RING_D < b.WALL_H
    for side, gy in b.GATES:      # not over a gate opening
        assert abs(b.CANNON_Y - gy) > b.GATE_W / 2 + cn.BRACKET[1] / 2


def test_boss_weapons_accepted_and_not_one_shot():
    accepted = set(g.WEAPONS) | {b._W.format(n) for n in ("WID_Assault_Heavy_Athena_VR_Ore_T03", "WID_Assault_Heavy_Athena_R_Ore_T03")}
    # Assault_Heavy R/VR are in build_guards' probed accepted list (its docstring), not in its station table.
    assert "Assault_Heavy R/VR/SR" in g.__doc__ or "Assault_Heavy R/VR/SR" in Path(g.__file__).read_text(encoding="utf-8")
    assert len(b.BOSS_WEAPONS) == 5
    for w in b.BOSS_WEAPONS + b.GATE_WEAPONS:
        assert w in accepted, w
    for w in b.BOSS_WEAPONS:
        assert "Sniper" not in w and "Launcher" not in w


def test_gate_settings():
    s = b.GATE_SETTINGS
    assert s["spawnOnTimer"] is False and s["despawnGuardsWhenDisabled"] is True and s["spawnCount"] == 2
    assert s["guardTeamOption"] == g.SETTINGS["guardTeamOption"]
    assert b.BOSS_SETTINGS is c.BOSS_SETTINGS and b.BOSS_HEALTH_ASK == 100000.0


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
    boss_wids = [re.findall(r"WID_\w+", row)[0] for row in rows]
    assert [w.rsplit(".", 1)[1] for w in b.BOSS_WEAPONS] == boss_wids
    assert b.GRANT_SETTINGS["equipItemOnGrant"] == 1


def test_every_tag_the_tool_writes_is_declared():
    tags = (ROOT / "console" / "verse" / "fnm_tags.verse").read_text(encoding="utf-8")
    src = (ROOT / "tools" / "build_bossmode.py").read_text(encoding="utf-8")
    names = set(re.findall(r'"(fnm_[a-z0-9_]+)"', src)) - {b.TAG, "fnm_test"}   # actor tags, not Verse tags
    names |= {f"fnm_bm_slot_{k}" for k in range(1, 6)} | {f"fnm_door_{x}" for x in "abcd"}
    assert "fnm_bm_gate" in names and "fnm_bm_cannon_fx" in names
    for name in sorted(names):
        assert f"{name} := class(tag){{}}" in tags, name


def test_fallbacks():
    assert b.nuke_effect(["Fireworks_Deprecated", "LaserBeams", "Small_Fire", "FireworksLarge"]) == "Small_Fire"
    assert b.nuke_effect(["LaserBeams", "LightningBolt_01"]) == "LightningBolt_01"
    assert b.knockback(["None", "Medium", "High", "Very High"]) == "High"
    assert b.knockback(["None", "Medium"]) == "Medium"


def test_race_cannon_defaults_unchanged(monkeypatch):
    """build_cannon.cannon() with its defaults still labels FNM_Cannon*, tags fnm_cannon_rig and the muzzle fnm_cannon_fx."""
    import build_cannon as cn
    calls = []

    def fake(toolset, tool, args=None, **kw):
        calls.append((tool, args))
        if tool in ("add_to_scene_from_asset", "PlaceDevice", "add_component"):
            return {"returnValue": {"refPath": f"/x/A{len(calls)}"}}
        if tool == "get_properties":
            return {"returnValue": '{"staticMeshComponent": {"refPath": "/x/C"}}'}
        return {"returnValue": True}

    monkeypatch.setattr(cn.u, "call", fake)
    monkeypatch.setattr(cn, "settings", lambda *a, **k: {})
    cn.cannon("L", 1000, 0, 2, (0, 2600, 192), "proj", "/m/steel", "/m/glow")
    labels = [a["label"] for t, a in calls if t == "set_label"]
    assert labels == ["FNM_CannonL_Bracket", "FNM_CannonL_Ball", "FNM_CannonL_Barrel", "FNM_CannonL_Ring", "FNM_CannonL_Fx"]
    assert {a["tag"] for t, a in calls if t == "add_tag"} == {"fnm_cannon_rig"}
    tag_writes = [a["values"] for t, a in calls if t == "set_properties" and "internalTags" in a["values"]]
    assert tag_writes and all("_Verse.fnm_cannon_fx" in v for v in tag_writes)


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
    hw = b.ARENA_W / 2
    for (x, y, gate), dy in zip(b.creature_spots(), b.CREATURE_DY):
        side, gy = b.GATES[gate - 1]
        assert side * x > hw + b.WALL_T and side * x < hw + b.WALL_T + b.ALCOVE_D       # inside that gate's alcove
        assert abs(y - gy) < b.GATE_W / 2 - 50
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
