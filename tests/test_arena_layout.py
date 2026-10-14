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


# ---------------------------------------------------------------- G9 scene work (2026-10-13): paint, doors, marks, guards, time

class FakeUefn:
    """A stand-in for uefn_mcp.call that records every (tool, args) and answers from a dict of canned replies."""

    def __init__(self, replies=None):
        self.calls, self.replies = [], replies or {}

    def __call__(self, toolset, tool, args=None, **_):
        self.calls.append((tool, args or {}))
        r = self.replies.get(tool)
        return r(args or {}) if callable(r) else {"returnValue": r}

    def tools(self):
        return [t for t, _ in self.calls]


def test_paint_key_walls_floors_ice_and_the_rest():
    s, t = 10, 5
    key = lambda label: c.paint_key(label, s, t)
    assert key("FNM_S01_Floor") == "floor_tier1" and key("FNM_S10_Floor") == "floor_tier5"
    assert key("FNM_S06_Floor") == "ice"                                   # the ice station's floor stays ice
    assert key("FNM_S06_FloorC1") == f"floor_tier{c.auto_tier(6, s, t)}"   # its connector is an ordinary floor
    assert (key("FNM_S03_FloorFunnel") == key("FNM_S03_FloorFlare") == key("FNM_S03_FloorC2")
            == f"floor_tier{c.auto_tier(3, s, t)}")
    assert key("FNM_Arena_Floor") == key("FNM_Arena_FloorC1") == "floor_tier5"
    assert key("FNM_Finish_Floor") == "floor_finish" and key("FNM_Finish_WallL") == "finish"
    assert key("FNM_S03_WallL") == f"tier{c.auto_tier(3, s, t)}"
    assert key("FNM_S03_Step1_02") == f"floor_tier{c.auto_tier(3, s, t)}"   # a stair tread is floor, not wall
    assert key("FNM_S03_Lintel") == key("FNM_S10_Lintel") == "lintel"      # the dark header the door letters stand against
    assert key("FNM_S02_Hurdle1") == "finish" and key("FNM_Arena_Platform") == "finish" and key("FNM_Arena_PadB") == "pad_b"
    assert key("FNM_Arena_WallL") == "tier5"
    for label in ("FNM_S01_Entry", "FNM_S01_DoorA", "FNM_S01_TriggerB", "FNM_S01_PassageC", "FNM_S01_Sign", "FNM_Director"):
        assert key(label) is None, label


def test_every_paint_key_has_a_material_and_floors_are_dark():
    import import_art as ia
    keys = {c.paint_key(f"FNM_S{k:02d}_{part}", 10, 5) for k in range(1, 11)
            for part in ("Floor", "FloorC1", "WallL", "Lintel", "Step1_01", "Hurdle1")}
    keys |= {c.paint_key(label, 10, 5) for label in ("FNM_Arena_Floor", "FNM_Arena_WallL", "FNM_Finish_Floor", "FNM_Finish_WallL",
                                                     "FNM_Arena_PadA", "FNM_Arena_PadD", "FNM_Arena_Platform")}
    assert keys <= set(ia.WALL_COLOURS), keys - set(ia.WALL_COLOURS)
    for n in range(1, 6):
        floor, wall = ia.WALL_COLOURS[f"floor_tier{n}"], ia.WALL_COLOURS[f"tier{n}"]
        assert max(floor) <= 0.2 and sum(floor) < 0.5 * sum(wall), (n, floor, wall)   # a flat Kd renders much lighter than its numbers
    assert max(ia.WALL_COLOURS["floor_finish"]) <= 0.2


def test_import_art_never_deletes_a_material_the_level_uses():
    """The 2026-10-13 regression: a full import_art run deleted and re-imported every wall material and door face, which
    emptied every reference to them (all 40 doors and the whole course's wall paint read back null)."""
    import tempfile
    import import_art as ia
    folder = "/proj/FNM_Art"
    present = {f"{folder}/M_fnm_wall_tier1", f"{folder}/M_door_face_a"}
    fake = FakeUefn({"exists": lambda a: {"returnValue": a["path"] in present},
                     "get_referencers": ["/proj/__ExternalActors__/FortStaticMeshActor_1"] * 3,
                     "import_file": [], "delete": True, "move": True, "save_assets": True})
    saved, old_colours = ia.u.call, ia.WALL_COLOURS
    ia.u.call = fake
    ia.WALL_COLOURS = {"tier1": (0.3, 0.7, 0.4), "floor_tier1": (0.05, 0.14, 0.07)}
    try:
        ia.REPLACED.clear()
        with tempfile.TemporaryDirectory() as tmp:
            ia.materials(folder, Path(tmp), None)
            assert "delete" not in fake.tools(), "the default run deleted an existing material"
            assert sum(t == "import_file" for t in fake.tools()) == 1        # only the missing floor_tier1 came in
            assert not ia.REPLACED
            fake.calls.clear()
            ia.materials(folder, Path(tmp), ["tier1"], force=True)           # --force does replace, and says it did
            assert "delete" in fake.tools() and ia.REPLACED == [(f"{folder}/M_fnm_wall_tier1", 3)]
    finally:
        ia.u.call, ia.WALL_COLOURS = saved, old_colours
        ia.REPLACED.clear()


def test_door_dress_stops_on_a_paint_that_did_not_take():
    face_c = '{"refPath":"/proj/FNM_Art/M_door_face_c.M_door_face_c"}'
    def reply(a, face, damageable=False):
        key = a["properties"][0]
        return {"returnValue": {"overrideMaterials": '{"overrideMaterials":[%s]}' % face, "bCanBeDamaged": '{"bCanBeDamaged":%s}'
                                % str(damageable).lower()}.get(key, '{"doorAnimatingMaterial":%s}' % face)}
    good = lambda a: reply(a, face_c)
    null = lambda a: reply(a, "null")
    mount = [{"name": "/proj/", "type": "Directory"}]
    c.project_mount.cache_clear()
    saved = c.u.call
    try:
        c.u.call = FakeUefn({"ListFiles": mount, "set_properties": True, "get_properties": good})
        c.door_dress("/lvl/DoorC", 2)                                         # reads back as its own letter: fine
        assert c.door_problem("/lvl/DoorC", 3) and "M_door_face_d" in c.door_problem("/lvl/DoorC", 3)   # not door D's
        c.u.call = FakeUefn({"ListFiles": mount, "get_properties": lambda a: reply(a, face_c, damageable=True)})
        assert "bCanBeDamaged" in c.door_problem("/lvl/DoorC", 2)             # a damageable door is a problem
        c.u.call = FakeUefn({"ListFiles": mount, "set_properties": True, "get_properties": good})
        c.u.call = FakeUefn({"ListFiles": mount, "set_properties": True, "get_properties": null})
        try:
            c.door_dress("/lvl/DoorC", 2)
            raise AssertionError("a null read-back passed")
        except SystemExit as e:
            assert "not painted" in str(e)
    finally:
        c.u.call = saved
        c.project_mount.cache_clear()


def test_door_marks_fit_the_lintel_and_clear_the_decor():
    import build_decor as d
    import build_door_marks as m
    assert len(m.b.LETTER_PROP_COLOURS) == 4 and m.b.LETTER_PROP_COLOURS[0] == "White"
    for i, x in enumerate(c.door_centres(4)):
        spot = m.layout(x, face_y=-9025.0, floor_z=0.0, i=i)
        lx, ly, lz, s, yaw = spot["letter"]
        assert lx == x and yaw == 180                                    # over its door, readable from -Y (the runner's side)
        assert lz >= c.DOOR_H and lz + m.LETTER_H * s <= c.WALL_H - 5    # inside the lintel face: above the door, under the wall top
        assert m.LETTER_W * s < c.DOOR_W                                 # clear of the neighbouring letters
        assert ly < -9025.0                                              # on the runner's side of the lintel face, not inside it
        assert spot["colour"] == m.b.LETTER_PROP_COLOURS[i] and spot["rgb"] == c.LETTER_COLOURS[i]
        gx, gy, gz = spot["light"]
        assert gx == x and gy < ly and 200 < gz < c.WALL_H               # in front of the letter, over a runner's head
        opts = m.light_options(i)
        assert opts["lightColor"]["r"] == c.LETTER_COLOURS[i][0] and opts["lightColor"]["b"] == c.LETTER_COLOURS[i][2]
        # a glow, not a flood: the brief's 50 / 60-100 bleached the white doors and pale walls in daylight (editor frames
        # 2026-10-13), so this builder runs 25 / 40; nothing above the brief's ceiling
        assert 10 <= opts["lightSizePercentage"] <= 50 and 10 <= opts["lightIntensityPercentage"] <= 100
    # build_decor stands the station number ON the lintel's top (z = c.WALL_H and up): the letters stop below it.
    decor = (ROOT / "tools" / "build_decor.py").read_text(encoding="utf-8")
    assert 'top = lintel["max"]["z"]' in decor and "number(str(k), cx, lintel[\"min\"][\"y\"] + 20, top" in decor
    assert d.NUMBER_H * d.NUMBER_SCALE > 0


def test_station_one_has_no_guard_and_the_others_keep_theirs():
    import build_guards as g
    assert g.GUARDS[0] == 0
    assert g.GUARDS[1:] == [1, 2, 2, 3, 3, 4, 4, 5, 5]                    # stations 2..10 unchanged since 2026-10-04
    bounds = {"min": {"x": 0, "y": 0, "z": 0}, "max": {"x": 0, "y": 0, "z": 0}}
    fake = FakeUefn({"ListFiles": [{"name": "/proj/", "type": "Directory"}], "remove_from_scene": True,
                     "find_actors": [{"label": "FNM_S01_Entry", "actorPath": "/lvl/e1", "bounds": bounds},
                                     {"label": "FNM_S01_Floor", "actorPath": "/lvl/f1", "bounds": bounds}]})
    saved = g.u.call
    g.u.call = fake
    try:
        g.build()
    finally:
        g.u.call = saved
    assert "PlaceDevice" not in fake.tools(), "station 1 got a guard spawner"


def test_island_time_of_day_refuses_unknown_values_and_list_writes_nothing():
    import build_island as bi
    enum = ["NoOverride", "ForceDay", "ForceNight", "Custom"] + [f"Hour{h}" for h in range(24)] + ["Random"]
    schema = '{"timeOfDayOverride": {"enum": [%s]}}' % ", ".join(f'"{v}"' for v in enum)
    fake = FakeUefn({"find_actors": [{"actorPath": "/lvl/IslandSettings_0", "label": "IslandSettings_0"}],
                     "list_properties": schema, "get_properties": '{"timeOfDayOverride":"NoOverride"}',
                     "set_properties": True, "save_assets": True})
    saved = bi.u.call
    bi.u.call = fake
    try:
        bi.time_of_day("list")
        assert "set_properties" not in fake.tools()
        try:
            bi.time_of_day("Hour25")
            raise AssertionError("an unknown value was accepted")
        except SystemExit as e:
            assert "Hour25" in str(e)
        assert "set_properties" not in fake.tools()
    finally:
        bi.u.call = saved


def test_paint_stops_before_writing_when_a_material_is_missing_and_skips_actors_already_right():
    """The flat-colour paint (--flat); the Titan Peak surfaces' own run is test_titanpeak_surfaces.py."""
    import json
    state = {}                                                            # component path -> override ref path
    actors = [{"label": "FNM_S01_Floor", "actorPath": "/lvl/f1"}, {"label": "FNM_S01_WallL", "actorPath": "/lvl/w1"},
              {"label": "FNM_S01_Entry", "actorPath": "/lvl/e1"}]

    def get_properties(a):
        key, inst = a["properties"][0], a["instance"]["refPath"]
        if key == "staticMeshComponent":
            return {"returnValue": json.dumps({key: {"refPath": inst + ".C"}})}
        ref_path = state.get(inst)
        return {"returnValue": json.dumps({key: [{"refPath": ref_path}] if ref_path else [None]})}

    def set_properties(a):
        state[a["instance"]["refPath"]] = json.loads(a["values"])["overrideMaterials"][0]["refPath"]
        return {"returnValue": True}

    made = {"/proj/FNM_Art/M_fnm_wall_floor_tier1": False, "/proj/FNM_Art/M_fnm_wall_tier1": True}
    fake = FakeUefn({"ListFiles": [{"name": "/proj/", "type": "Directory"}], "find_actors": actors, "save_assets": True,
                     "exists": lambda a: {"returnValue": made.get(a["path"], False)},
                     "get_properties": get_properties, "set_properties": set_properties})
    c.project_mount.cache_clear()
    saved = c.u.call
    c.u.call = fake
    try:
        try:
            c.paint(surfaces=False)
            raise AssertionError("paint ran with a material missing")
        except SystemExit as e:
            assert "floor_tier1" in str(e) and "import_art.py" in str(e)
        assert "set_properties" not in fake.tools()
        made["/proj/FNM_Art/M_fnm_wall_floor_tier1"] = True
        c.paint(surfaces=False)
        assert fake.tools().count("set_properties") == 2                  # the floor and the wall; not the entry teleporter
        assert state == {"/lvl/f1.C": "/proj/FNM_Art/M_fnm_wall_floor_tier1.M_fnm_wall_floor_tier1",
                         "/lvl/w1.C": "/proj/FNM_Art/M_fnm_wall_tier1.M_fnm_wall_tier1"}
        fake.calls.clear()
        c.paint(surfaces=False)
        assert "set_properties" not in fake.tools()                       # a second run writes nothing
        state["/lvl/w1.C"] = None                                         # the 2026-10-13 state: a reference emptied
        bad = c.check_paint(surfaces=False)
        assert len(bad) == 1 and bad[0].startswith("FNM_S01_WallL"), bad    # check_paint sees the emptied override
    finally:
        c.u.call = saved
        c.project_mount.cache_clear()


# ---------------------------------------------------------------- import_art --force: only keys the course repaint covers

def _import_art_run(args, force, shared_ok=None):
    """Run import_art.main against a recording fake (everything 'exists', three actors use every asset) with the course
    repaint stubbed out. Returns (tool names called, repaint calls, SystemExit or None)."""
    import import_art as ia
    fake = FakeUefn({"ListFiles": [{"name": "/proj/", "type": "Directory"}], "exists": True,
                     "get_referencers": ["/proj/__ExternalActors__/FortStaticMeshActor_1"] * 3, "find_assets": [],
                     "import_file": [], "delete": True, "move": True, "save_assets": True, "set_properties": True,
                     "get_asset_class": "Material"})
    repaints = []
    saved = (ia.u.call, c.paint, c.door_paint)
    ia.u.call, c.paint, c.door_paint = fake, lambda: repaints.append("paint"), lambda: repaints.append("door_paint")
    ia.REPLACED.clear()
    exit_ = None
    try:
        kw = {} if shared_ok is None else {"shared_ok": shared_ok}
        ia.main(args, force, **kw)
    except BaseException as e:                  # SystemExit is the expected refusal; anything else is a failure to assert on
        exit_ = e
    finally:
        ia.u.call, c.paint, c.door_paint = saved
        ia.REPLACED.clear()
    return fake.tools(), repaints, exit_


def test_import_art_force_without_keys_is_refused_before_touching_uefn():
    """`import_art.py --force` with no keys replaced EVERY material, boss mode's and the colosseum's included (bm_stone has
    100+ users), while the course repaint covers only the course: the rest went unpainted and the script exited 0."""
    tools, repaints, exit_ = _import_art_run(None, True)
    assert isinstance(exit_, SystemExit) and exit_.code not in (0, None) and "explicit keys" in str(exit_), exit_
    assert tools == [] and repaints == [], "it touched UEFN before refusing"


def test_import_art_force_refuses_keys_the_course_repaint_does_not_cover():
    import import_art as ia
    for key in ("bm_stone", "bm_wall", "bm_floor", "bm_perch", "bm_sand", "bm_marble", "pad_a", "pad_d", "steel", "glow"):
        tools, repaints, exit_ = _import_art_run([key], True)
        assert isinstance(exit_, SystemExit) and exit_.code not in (0, None), (key, exit_)
        assert "--force-shared" in str(exit_) and "build_bossmode" in str(exit_), (key, str(exit_))
        assert "delete" not in tools and repaints == [], key
    # every WALL_COLOURS key is either one build_course.paint covers or refused: nothing slips through unnamed
    assert set(ia.WALL_COLOURS) - ia.COURSE_KEYS == {"bm_wall", "bm_floor", "bm_perch", "bm_sand", "bm_stone", "bm_marble",
                                                    "steel", "glow", "pad_a", "pad_b", "pad_c", "pad_d"}
    # a course key the paint can produce is allowed, replaced, then repainted
    for key in ("floor_tier1", "tier3", "lintel", "ice", "finish", "signs"):
        tools, repaints, exit_ = _import_art_run([key], True)
        assert exit_ is None, (key, exit_)
        assert "delete" in tools and repaints == ["paint", "door_paint"], (key, tools, repaints)


def test_import_art_force_shared_replaces_then_exits_nonzero_naming_the_builders_to_rerun():
    tools, repaints, exit_ = _import_art_run(["bm_stone"], True, shared_ok=True)
    assert "delete" in tools and repaints == ["paint", "door_paint"]
    assert isinstance(exit_, SystemExit) and exit_.code not in (0, None), ("it replaced boss mode's material and exited 0", exit_)
    assert "build_bossmode.py" in str(exit_) and "build_colosseum.py" in str(exit_)


def test_import_art_command_line():
    import import_art as ia
    assert ia.parse_args(["floor_tier1", "tier2"]) == (["floor_tier1", "tier2"], False, False)
    assert ia.parse_args(["--force", "signs"]) == (["signs"], True, False)
    assert ia.parse_args(["--force", "--force-shared", "bm_stone"]) == (["bm_stone"], True, True)
    assert ia.parse_args([]) == (None, False, False)
    try:
        ia.parse_args(["--force-shared", "bm_stone"])
        raise AssertionError("--force-shared without --force was accepted")
    except SystemExit as e:
        assert "--force" in str(e)
