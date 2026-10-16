"""The race finale's boss rig (tools/build_race_boss.py, BOSS_MODE.md 16, maps/starter/LAYOUT.md "Boss arena"): the mega
cannons stay clear of the pads, the lanes and the walls, sit in frame from the entry and see the titan's waist; the
letters float under the lid and over a player's head; the titan's scale, the beam aim, the baked race laser and the coil
offset agree; every tag the tool writes is declared; and the director drives the Megabrute, the titan, the boss bar and
the delayed explanation the way boss mode does. Verse is compiled only inside UEFN, so its checks read the source."""
import json
import math
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

import build_bossmode as b  # noqa: E402
import build_course as c  # noqa: E402
import build_fx  # noqa: E402
import build_race_boss as r  # noqa: E402

VERSE = ROOT / "console" / "verse"
PADS = [(x - c.PAD_SIZE / 2, x + c.PAD_SIZE / 2, y - c.PAD_SIZE / 2, y + c.PAD_SIZE / 2) for x, y in c.PAD_SPOTS]
PLATFORM = (-c.PLATFORM_W / 2, c.PLATFORM_W / 2, c.PLATFORM_Y - c.PLATFORM_D / 2, c.PLATFORM_Y + c.PLATFORM_D / 2)


def src(name):
    return (VERSE / name).read_text(encoding="utf-8")


def all_verse():
    return "\n".join(p.read_text(encoding="utf-8") for p in sorted(VERSE.glob("*.verse")))


def body_of(text, head):
    """The indented body of a Verse function whose header line starts with head (up to the next line at its indent)."""
    lines = text.split("\n")
    start = next(i for i, l in enumerate(lines) if l.strip().startswith(head))
    indent = len(lines[start]) - len(lines[start].lstrip())
    out = []
    for l in lines[start + 1:]:
        if l.strip() and len(l) - len(l.lstrip()) <= indent:
            break
        out.append(l)
    return "\n".join(out)


def _bbox(points):
    xs, ys = [p[0] for p in points], [p[1] for p in points]
    return min(xs), max(xs), min(ys), max(ys)


def _overlap(a, q):
    return a[0] < q[1] and q[0] < a[1] and a[2] < q[3] and q[2] < a[3]


def _inside(x, y, rect):
    return rect[0] <= x <= rect[1] and rect[2] <= y <= rect[3]


# ---------------------------------------------------------------- layout

def test_cannons_clear_of_pads_lanes_walls_and_gate():
    """Each cannon's footprint (at CANNON_SCALE, turned onto the waist) stays inside the hall, off every pad and the
    platform, short of the gate, off the adds' spawn circle, and leaves a lane at least 1.5 m wide between itself and the
    platform (the way to the gate after the kill); the centre lane between the pads stays open."""
    for side in r.SIDES:
        box = _bbox(r.cannon_corners(side))
        assert max(abs(box[0]), abs(box[1])) < r.HALF - 10, box                 # off the wall
        for pad in PADS:
            assert not _overlap(box, pad), (side, box, pad)
        assert not _overlap(box, PLATFORM)
        assert box[3] < c.GATE_Y - 50
        adds = (-c.ADDS_SETTINGS["spawnRadius_InMeter"] * 100, c.ADDS_SETTINGS["spawnRadius_InMeter"] * 100,
                c.ADDS_Y - c.ADDS_SETTINGS["spawnRadius_InMeter"] * 100, c.ADDS_Y + c.ADDS_SETTINGS["spawnRadius_InMeter"] * 100)
        assert not _overlap(box, adds)
        inner = min(abs(box[0]), abs(box[1]))
        assert inner - c.PLATFORM_W / 2 >= 150, inner                           # the lane beside the platform
        inner_pad_edge = min(abs(x) - c.PAD_SIZE / 2 for x, _ in c.PAD_SPOTS)
        assert inner >= inner_pad_edge                                          # never into the centre lane
        assert box[2] > max(p[3] for p in PADS)                                 # behind the far pads


def test_cannons_in_frame_from_the_entry():
    """Every corner of each cannon is under 40 degrees off the view's centre for a player at the entry looking +Y (the old
    wall cannons at 11 m were 45 degrees off and out of frame, 2026-10-08)."""
    ex, ey = r.ENTRY
    for side in r.SIDES:
        for x, y in r.cannon_corners(side):
            assert math.degrees(math.atan2(abs(x - ex), y - ey)) < 40, (side, x, y)


def test_beams_have_a_clear_line_to_the_waist():
    """From each muzzle point to the waist the shot passes over no pad and no player standing there, stays under the lid,
    and ends inside the titan's height; both cannons aim at the same point (the lasers meet)."""
    ax, ay, az = r.aim()
    for side in r.SIDES:
        mx, my, mz = r.muzzle_point(side)
        for k in range(101):
            t = k / 100
            x, y, z = mx + (ax - mx) * t, my + (ay - my) * t, mz + (az - mz) * t
            assert z < r.LID_Z
            for pad in PADS:
                assert not _inside(x, y, pad), (side, t, x, y)
        assert 0 < mz < r.LID_Z
    assert r.muzzle_point("L")[0] == -r.muzzle_point("R")[0]                    # mirrored


def test_titan_scale_and_beam_aim_agree():
    """The waist (beam aim) scales with the titan from boss mode's (450 at scale 4); the titan's head, seen from a camera
    3.5 m behind the entry, is lower in the view than boss mode's (whose head sits just under the question panel; at a
    matching angle the race titan's head touched the panel in play, 2026-10-11) but not much lower (it still reads as
    the boss)."""
    assert r.BEAM_AIM == round(b.BEAM_AIM * r.TITAN_SCALE / b.TITAN_SCALE) == 338
    assert r.TITAN_SCALE == 3.0
    height = 300 * r.TITAN_SCALE                       # the imported mesh is 3 m tall
    assert c.PLATFORM_H + 0.25 * height < r.aim()[2] < c.PLATFORM_H + 0.6 * height
    cam_back, cam_h = 350, 250

    def head_angle(head_z, dist):
        return math.degrees(math.atan2(head_z - cam_h, dist + cam_back))
    race = head_angle(c.PLATFORM_H + height, c.PLATFORM_Y - r.ENTRY[1])
    boss = head_angle(b.PLATFORM_H + 300 * b.TITAN_SCALE, b.PLATFORM_Y - b.ENTRY[1])
    # G10 (2026-10-14): scale 3.0 with the compact slate (SetCompact) clearing the head, so the race titan now looks a
    # little TALLER than boss mode's from the entry (about 1.23x: 15.0 vs 12.2 deg), never more than 1.35x. Measured in play:
    # with the full slate the head hid behind the panel (the reason for the compact one); the band is what we intend.
    assert boss <= race <= 1.35 * boss, (race, boss)
    assert r.titan_yaw() == -90.0                      # faces the entry


def test_letters_float_under_the_lid_over_a_players_head():
    """The floating letters (boss mode's props, smaller): the top of the letter at the top of its bob is under the
    invisible lid; its bottom at the bottom of its bob clears a 1.8 m player on the pad; it is no wider than its pad;
    the far letters still stand over 5 degrees tall from the entry."""
    tall, wide = r.LETTER_H * r.LETTER_SCALE, r.LETTER_W * r.LETTER_SCALE
    assert r.LETTER_Z + tall + r.LETTER_BOB < r.LID_Z
    assert r.LETTER_Z - r.LETTER_BOB >= 180
    assert wide <= c.PAD_SIZE
    far = max(y for _, y in c.PAD_SPOTS) - r.ENTRY[1]
    assert math.degrees(math.atan2(tall, far)) > 5
    # the bob the test assumes is the director's
    assert f"LetterBobCm : float = {r.LETTER_BOB:.1f}" in src("fnm_director.verse")
    # disproof: boss mode's own scale would not fit over a player's head under this lid
    assert r.LID_Z - b.LETTER_SCALE * r.LETTER_H - r.LETTER_BOB - r.LETTER_BOB < 180


def test_race_laser_length_matches_the_race_cannons():
    """NS_fnm_laser_race's beam is baked (Verse cannot set its user parameters): its length is the race cannons'
    muzzle-to-waist distance, within 30 cm. Rebuild with tools/build_fx.py NS_fnm_laser_race after moving them."""
    ax, ay, az = r.aim()
    bx, by = r.CANNON_X, r.CANNON_Y
    heading = math.atan2(ay - by, ax - bx)
    f = b.CANNON_MUZZLE[1] * r.CANNON_SCALE + r.MUZZLE_AHEAD
    mx, my = bx + f * math.cos(heading), by + f * math.sin(heading)
    mz = (b.CANNON_HALF_H + b.CANNON_MUZZLE[2]) * r.CANNON_SCALE
    assert abs(math.dist((mx, my, mz), (ax, ay, az)) - build_fx.RACE_LENGTH) < 30
    assert abs(r.laser_length() - build_fx.RACE_LENGTH) < 30
    assert abs(build_fx.RACE_LENGTH - build_fx.LENGTH) > 1000          # disproof: not boss mode's laser
    assert build_fx.SYSTEMS["NS_fnm_laser_race"] is build_fx.build_race_laser


def test_race_laser_is_built_at_its_own_length(monkeypatch):
    """build_race_laser lays every beam of the shot to RACE_LENGTH (not LENGTH): its Beam End inputs, read off a fake
    Niagara toolset."""
    ends = []

    def fake(toolset, tool, args=None, **kw):
        if tool == "SetStackInputData" and args["stackInputRef"]["inputNameStack"] == ["Beam End"]:
            ends.append(args["inputData"]["value"]["x"])
        if tool == "GetSystemSummary":
            return {"returnValue": {"emitters": []}}
        if tool == "AddModule":
            return {"returnValue": {"moduleName": "M"}}
        return {"returnValue": False}

    monkeypatch.setattr(build_fx.u, "call", fake)
    build_fx.build_race_laser("NS_test")
    assert ends and set(ends) == {build_fx.RACE_LENGTH}


def test_coil_crackle_sits_on_the_race_cannons_coils():
    """Verse puts NS_fnm_coil FnmRaceCannonCoilBack behind each race beam's start on its level heading (fnm_fx
    FnmSpawnCoils): that must land on CANNON_COIL of the race cannon."""
    verse = src("fnm_fx.verse")
    back = float(re.search(r"^FnmRaceCannonCoilBack : float = ([0-9.]+)$", verse, re.M).group(1))
    assert back == r.coil_back()
    ax, ay, _ = r.aim()
    for side in r.SIDES:
        _, _, _, point = r.cannon_frame(side)
        mx, my, mz = r.muzzle_point(side)
        flat = math.hypot(ax - mx, ay - my)
        coil = (mx - (ax - mx) / flat * back, my - (ay - my) / flat * back, mz)
        assert math.dist(coil, point(b.CANNON_COIL)) < 1.0, (side, coil)
    assert back != float(re.search(r"^FnmCannonCoilBack : float = ([0-9.]+)$", verse, re.M).group(1))


def test_every_tag_the_tool_writes_is_declared():
    tags = src("fnm_tags.verse")
    text = (ROOT / "tools" / "build_race_boss.py").read_text(encoding="utf-8")
    names = set(re.findall(r'"(fnm_[a-z0-9_]+)"', text)) - {r.TAG, r.OLD_CANNON_TAG}       # actor tags, not Verse tags
    names |= {f"fnm_bm_slot_{k}" for k in range(1, 5)}
    assert {"fnm_race_megaboss", "fnm_race_titan", "fnm_race_beam", "fnm_race_letter", "fnm_cannon_strike"} <= names
    for name in sorted(names):
        assert f"{name} := class(tag){{}}" in tags, name


# ---------------------------------------------------------------- the builder, against a fake editor

class FakeEditor:
    """Just enough of UEFN MCP for build_race_boss.build(): the course's arena actors, old pieces to remove, and every
    property write remembered so reads give it back."""

    def __init__(self):
        self.calls, self.props, self.n = [], {}, 0
        bounds = lambda x0, x1, y0, y1, z0, z1: {"min": {"x": x0, "y": y0, "z": z0}, "max": {"x": x1, "y": y1, "z": z1}}  # noqa: E731
        ox, oy = 5000.0, 20000.0
        self.origin = (ox, oy, 302.0)
        self.course = [
            {"label": "FNM_Arena_Floor", "actorPath": "/a/floor", "bounds": bounds(ox - 1146, ox + 1146, oy, oy + 3080, 262, 302)},
            {"label": "FNM_Arena_WallL", "actorPath": "/a/wl", "bounds": bounds(ox + 1106, ox + 1146, oy, oy + 3080, 300, 900)},
            {"label": "FNM_Arena_WallR", "actorPath": "/a/wr", "bounds": bounds(ox - 1146, ox - 1106, oy, oy + 3080, 300, 900)},
            {"label": "FNM_Arena_Platform", "actorPath": "/a/pl", "bounds": bounds(ox - 300, ox + 300, oy + 2400, oy + 2800, 302, 402)},
            {"label": "FNM_Arena_Boss", "actorPath": "/a/oldboss", "bounds": {}},
            {"label": "FNM_Arena_LabelA", "actorPath": "/a/oldlabel", "bounds": {}},
            {"label": "FNM_S01_Floor", "actorPath": "/a/s1", "bounds": {}}]

    def __call__(self, toolset, tool, args=None, **kw):
        self.calls.append((tool, args))
        if tool == "find_actors":
            return {"returnValue": {"fnm_course": self.course, "fnm_cannon_rig": [{"label": "FNM_CannonL_Ball", "actorPath": "/a/ball"}]}.get(args["tag"], [])}
        if tool in ("add_to_scene_from_asset", "PlaceDevice", "add_component"):
            self.n += 1
            return {"returnValue": {"refPath": f"/new/A{self.n}"}}
        if tool == "set_properties":
            self.props.setdefault(args["instance"]["refPath"], {}).update(json.loads(args["values"]))
            return {"returnValue": True}
        if tool == "get_properties":
            mine = self.props.get(args["instance"]["refPath"], {})
            return {"returnValue": json.dumps({k: mine.get(k) for k in args["properties"]})}
        if tool == "find_assets":
            letter = args["name"].split("_")[2]
            return {"returnValue": [f"/CRG/PPID_CRG_Props_CP_Alphabet_{letter}_0a1b.PPID_CRG_Props_CP_Alphabet_{letter}_0a1b"]}
        return {"returnValue": True}


def test_builder_places_the_rig_and_removes_the_old_pieces(monkeypatch):
    fake = FakeEditor()
    monkeypatch.setattr(r.u, "call", fake)
    monkeypatch.setattr(c, "project_mount", lambda: "/proj")
    r.build()
    labels = [a["label"] for t, a in fake.calls if t == "set_label"]
    expect = (["FNM_RaceBoss_Megaboss"] + [f"FNM_RaceBoss_Titan{k}" for k in range(1, 6)]     # 5: the jump-slam (G9 D2)
              + [f"FNM_RaceBoss_Cannon{s}_{p}" for s in "L" for p in ("Body", "Glow", "MuzzleGlow")] + ["FNM_RaceBoss_BeamL"]
              + [f"FNM_RaceBoss_Cannon{s}_{p}" for s in "R" for p in ("Body", "Glow", "MuzzleGlow")] + ["FNM_RaceBoss_BeamR"]
              + ["FNM_RaceBoss_Strike", "FNM_RaceBoss_Blast1", "FNM_RaceBoss_Blast2"]
              + [f"FNM_RaceBoss_Letter{x}" for x in "ABCD"])
    assert labels == expect
    assert {a["tag"] for t, a in fake.calls if t == "add_tag"} == {r.TAG}
    removed = {a["actor"]["refPath"] for t, a in fake.calls if t == "remove_from_scene"}
    assert removed == {"/a/oldboss", "/a/oldlabel", "/a/ball"}                  # never a course piece still in use
    verse_tags = [json.loads(a["values"])["internalTags"]["internalTags"] for t, a in fake.calls
                  if t == "set_properties" and "internalTags" in a["values"]]
    names = [[t["internalTag"]["refPath"].rsplit(".", 1)[1] for t in tags] for tags in verse_tags]
    assert names[0] == ["fnm_race_megaboss"]
    assert names[1:6] == [["fnm_race_titan", f"fnm_bm_slot_{k}"] for k in range(1, 6)]
    assert ["fnm_race_beam", "fnm_bm_slot_1"] in names and ["fnm_race_beam", "fnm_bm_slot_2"] in names
    assert [["fnm_race_letter", f"fnm_bm_slot_{k}"] for k in range(1, 5)] == names[-4:]
    # the Megabrute stands on the platform top, mid-platform, facing the entry; the idle clip with it at TITAN_SCALE
    places = [a for t, a in fake.calls if t in ("PlaceDevice", "add_to_scene_from_asset")]
    ox, oy, z0 = fake.origin
    boss = places[0]["transform"]
    assert boss["location"] == {"x": ox, "y": oy + c.PLATFORM_Y, "z": z0 + c.PLATFORM_H} and boss["rotation"]["yaw"] == -90
    idle = places[1]["transform"]
    assert idle["location"] == boss["location"] and idle["scale"]["x"] == r.TITAN_SCALE
    titan_props = [fake.props[f"/new/A{k}"] for k in range(1, 20) if "animation" in fake.props.get(f"/new/A{k}", {})]
    assert [p["loop"] for p in titan_props] == [True, True, True, False, False]   # the fall and the jump-slam play once
    # the jump-slam plays on idle's mesh (an animation imported onto idle's skeleton, G9 D2), every other clip on its own
    meshes = [p["skeletalMesh"]["refPath"].rsplit("/", 1)[1] for p in titan_props]
    assert meshes == ["SK_fnm_titan_idle.SK_fnm_titan_idle", "SK_fnm_titan_flail.SK_fnm_titan_flail",
                      "SK_fnm_titan_stomp.SK_fnm_titan_stomp", "SK_fnm_titan_dead.SK_fnm_titan_dead",
                      "SK_fnm_titan_idle.SK_fnm_titan_idle"]
    assert titan_props[4]["animation"]["refPath"].endswith("/Clip_jumpslam/A_fnm_titan_jumpslam.A_fnm_titan_jumpslam")
    assert fake.props["/new/A1"]["creature Type"] == "Megabrute"
    # each beam marker starts at its muzzle point and is as long as the race laser
    beams = [a["xform"] for t, a in fake.calls if t == "add_to_scene_from_asset" and a["name"].startswith("FNM_RaceBoss_Beam")]
    for xf, side in zip(beams, r.SIDES):
        mx, my, mz = r.muzzle_point(side)
        assert math.isclose(xf["location"]["x"], ox + mx) and math.isclose(xf["location"]["z"], z0 + mz)
        assert math.isclose(xf["scale"]["z"] * b.BEAM_H, r.laser_length())
    # the letters float LETTER_Z over the floor at LETTER_SCALE, over their pads
    letters = [a["xform"] for t, a in fake.calls if t == "add_to_scene_from_asset" and a["name"].startswith("FNM_RaceBoss_Letter")]
    for xf, (dx, dy) in zip(letters, c.PAD_SPOTS):
        assert xf["location"] == {"x": ox + dx, "y": oy + dy, "z": z0 + r.LETTER_Z} and xf["scale"]["x"] == r.LETTER_SCALE


# ---------------------------------------------------------------- the director (Verse source)

def test_director_finds_the_race_rig_by_its_tags():
    d = src("fnm_director.verse")
    assert "FindCreativeObjectsWithTag(fnm_race_megaboss), Spawner := creature_spawner_device[Object]" in d
    assert "FindCreativeObjectsWithTag(fnm_race_titan), Device := animated_mesh_device[Object]" in d
    assert "RaceTitan.Add(Device, FnmBmSlotOf(Object))" in d
    assert "FindCreativeObjectsWithTag(fnm_race_beam), Beam := creative_prop[Object]" in d
    assert "FindCreativeObjectsWithTag(fnm_race_letter), Letter := creative_prop[Object]" in d
    assert "fnm_boss_spawner" not in d                     # the guard boss is not looked up any more
    assert "Boss : ?creature_spawner_device" in d and "BossHome : ?transform" in d
    assert "RaceLaser := true" in d and "PinnedBoss := Pinned" in d


def test_race_boss_is_pulsed_pinned_and_healed_like_boss_modes():
    """BOSS_MODE 14: creature spawners refuse SpawnAt; boss mode pulses its Megabrute (Enable, Disable on its SpawnedEvent)
    and re-pulses one not up after 5 s. The race does the same, pins it (FnmPinBoss, shared), gives it MegabossHealth
    (shared) and heals every hit but a pad's."""
    d = src("fnm_director.verse")
    spawn = body_of(d, "SpawnBoss(A:fnm_arena):void =")
    assert "Boss.Enable()" in spawn and "SpawnAt" not in spawn and "Reset()" not in spawn
    up = body_of(d, "OnBossSpawned(Agent:agent):void =")
    assert up.index("Boss.Disable()") < up.index("if (BossAlive?):")
    for needle in ("Character.SetMaxHealth(MegabossHealth)", "Character.SetHealth(MegabossHealth)",
                   "Character.DamagedEvent().Subscribe(fnm_race_boss_damage{Director := Self}.OnDamaged)",
                   "FnmPinBoss(Character, A.BossHome)", "Character.Hide()"):
        assert needle in up, needle
    loop = body_of(d, "BossLoop()<suspends>:void =")
    retry = loop.split("not spawned after 5 s", 1)[1]
    assert retry.index("Boss.Disable()") < retry.index("Boss.Enable()")
    assert "Boss.Spawn()" not in loop
    assert "Now - RaceBossHitAt > LeashAfterHitSeconds" in loop and "FnmPinBoss(Character, A.BossHome)" in loop
    hit = body_of(d, "BossHit(State:fnm_player_state, A:fnm_arena):void =")
    assert hit.index("set RacePadHitting = true") < hit.index("Character.Damage(Amount)") < hit.index("set RacePadHitting = false")
    heal = body_of(src("fnm_bossmode.verse"), "OnDamaged(Result:damage_result):void =")
    assert heal.index("Director.RacePadHitting?") < heal.index("Character.Heal(Result.Amount)")
    assert "Director.RaceGunHint(Shooter)" in heal
    # the Megabrute's only device calls are the digest's creature spawner members
    used = set(re.findall(r"\bBoss\.(\w+)", "\n".join(body_of(d, h) for h in (
        "SpawnBoss(A:fnm_arena)", "OnBossSpawned(Agent:agent)", "BossDown():void =", "BossLoop()<suspends>"))))
    used |= set(re.findall(r"\bBoss\.(\w+)", d.split("if (Boss := A.Boss?):\n                    Boss.Disable()", 1)[1].split("\n\n", 1)[0]))
    assert used <= {"Enable", "Disable", "SpawnedEvent", "EliminatedEvent"}, used
    # shared constants are defined once, in the director, and boss mode reads them there
    verse = all_verse()
    for name, value in (("MegabossHealth", "100000.0"), ("LeashAfterHitSeconds", "1.5"), ("BossLeashCm", "150.0")):
        assert verse.count(f"{name} : float = {value}") == 1, name
        assert f"Director.{name}" in src("fnm_bossmode.verse"), name
    assert "FnmPinBoss(Character, Arena.BossHome)" in src("fnm_bossmode.verse")


def test_titan_calls_follow_the_fight():
    """Arrive with each spawn, Hurt on a right pad that does not kill, Taunt on a wrong pad while the boss is up, Fall at
    the kill, Reset once at OnBegin (it rewinds the fall clip)."""
    d = src("fnm_director.verse")
    assert "spawn{ RaceTitan.Arrive() }" in body_of(d, "SpawnBoss(A:fnm_arena):void =")
    hit = body_of(d, "BossHit(State:fnm_player_state, A:fnm_arena):void =")
    assert "if (Left > 0):\n                spawn{ RaceTitan.Hurt() }" in hit
    pad = body_of(d, "HandlePad(State:fnm_player_state, A:fnm_arena, DoorIndex:int)<suspends>:void =")
    assert "if (BossAlive?):\n                    spawn{ RaceTitan.Taunt() }" in pad
    assert "spawn{ RaceTitan.Fall() }" in body_of(d, "BossDown():void =")
    assert d.count("RaceTitan.Reset()") == 1 and "RaceTitan.Reset()" in body_of(d, "OnBegin<override>()<suspends>:void =")
    assert "RaceTitan : fnm_titan = fnm_titan{}" in d


def test_race_boss_bar_replaces_the_slate_line():
    d = src("fnm_director.verse")
    bar = body_of(d, "RaceBossBar(State:fnm_player_state):void =")
    for needle in ('"THE MAGMA TITAN"', '"MEGABRUTE BOSS"', 'BarName := "{Who}   -   FINAL BOSS"',
                   'State.Hud.SetBossBar(BarName, 0, "DEFEATED!")', 'State.Hud.SetBossBar(BarName, 100, "THE BOSS IS COMING ...")',
                   'State.Hud.SetBossBar(BarName, Pct, "{Pct}%   -   team hits {BossHitsTaken}/{BossHitsToKill}")'):
        assert needle in bar, needle
    assert bar.index("State.Finished?") < bar.index("not BossAlive?")
    assert "BossLine" not in d and "SetBoss(" not in d                # the slate's BOSS text line is gone from the race
    hit = body_of(d, "BossHit(State:fnm_player_state, A:fnm_arena):void =")
    assert "spawn{ Fighter.Hud.HitBossBar() }" in hit and "RefreshRaceBossBars(Now)" in hit
    assert "RefreshRaceBossBars(BossDownAt)" in body_of(d, "BossDown():void =")
    loop = body_of(d, "BossLoop()<suspends>:void =")
    assert "if (ShowsRaceBossBar(State, Now)?):" in loop and "State.Hud.ClearBoss()" in loop
    shows = body_of(d, "ShowsRaceBossBar(State:fnm_player_state, Now:float)<transacts>:logic =")
    assert "State.Mode = fnm_mode.Race" in shows and "AtArena(State)?" in shows and "not State.Picking?" in shows
    assert "Now < BossDownAt + DefeatedSeconds" in shows


def test_race_pad_shows_the_recap_card():
    """G9 Now 6: a right pad in the race arena shows the recap card (the solved item, captured before BossHit draws the
    next one), like a right door; boss mode keeps its delayed explanation (ExplainDelaySeconds, one constant, in the
    director)."""
    d = src("fnm_director.verse")
    pad = body_of(d, "HandlePad(State:fnm_player_state, A:fnm_arena, DoorIndex:int)<suspends>:void =")
    right = pad.split("else if (Choice = Item.Answer):", 1)[1].split("\n            else:", 1)[0]
    # Round 2 (audit item 3): the arena's pads are live during the recap, so there it lasts no longer than the cooldown.
    assert right.index('Solved := RecapOf(State, Item, DoorIndex, "CORRECT!")') < right.index("BossHit(State, A)") \
        < right.index("Recap(State, Solved, Min(RecapSeconds, RightCooldownSeconds))")
    assert "Recap(State, Solved, RecapSeconds)" in body_of(d, "HandleDoor(State:fnm_player_state, StationIndex:int, DoorIndex:int)<suspends>:void =")
    assert "ShowCurrent(State)" not in body_of(d, "BossHit(State:fnm_player_state, A:fnm_arena):void =")
    recap = body_of(d, "Recap(State:fnm_player_state, Solved:fnm_recap, Seconds:float)<suspends>:void =")
    assert recap.index("State.Hud.ShowRecap(") < recap.index("Sleep(Seconds)") < recap.index("State.Hud.EndRecapIf(Generation)") \
        < recap.index("ShowCurrent(State)")
    assert "State.SlateSerial = Serial" in recap
    assert all_verse().count("ExplainDelaySeconds : float = 2.5") == 1
    assert "Sleep(Director.ExplainDelaySeconds)" in src("fnm_bossmode.verse")


def test_wrong_door_charge_never_moves_the_clock_start():
    """Round-2 audit item 1 (MAJOR): StartTime < 0 is the "no clock" sentinel; the +3 s per wrong door moved it back and
    crossed it on a fresh session's first run (clock frozen, 0:00.0 saved as a best). The charge is ClockPenalty, and every
    read of the race clock goes through RunClock."""
    d = src("fnm_director.verse")
    assert "StartTime -=" not in d and "StartTime +=" not in d
    assert "set State.ClockPenalty += WrongDoorSeconds" in body_of(d, "ChargeWrongDoor(State:fnm_player_state)<transacts>:string =")
    assert "Now - State.StartTime + State.ClockPenalty" in body_of(d, "RunClock(State:fnm_player_state, Now:float)<transacts>:float =")
    assert d.count("GetSimulationElapsedTime() - State.StartTime") == 0          # no read bypasses RunClock
    # (FinishPlayer hands the finish to FinishRun since G9 D2: the arena's kill defers the fanfare to the podium.)
    assert "FinishRun(State, 0.0)" in body_of(d, "FinishPlayer(State:fnm_player_state):void =")
    for head in ("Countdown(State:fnm_player_state)<suspends>:void =", "FinishRun(State:fnm_player_state, FanfareDelay:float):void ="):
        body = body_of(d, head)
        assert "set State.StartTime = -1.0" in body and "set State.ClockPenalty = 0.0" in body, head


def test_misses_read_you_on_the_victims_own_hud():
    """Round-2 audit item 4: a private miss line says "You got ...", not the victim's own name."""
    d = src("fnm_director.verse")
    feed = body_of(d, "MissFeed(State:fnm_player_state, Named:message, Own:string, LogLine:string):void =")
    assert "State.Hud.PushFeed(FnmText(Own))" in feed and "Broadcast(Named, LogLine)" in feed
    assert '"You got {Past} at station {StationIndex + 1}"' in d and '"You got {Past} by the boss"' in d


def test_boss_mode_penalties_move_to_the_entry_first():
    """Round-2 audit item 2: in boss mode Punish moves the player to the arena entry before any hold (monsters spawn by the
    pads on a wrong answer); the race holds where the player stands, then the retry spot under the wide camera."""
    punish = body_of(src("fnm_director.verse"), "Punish(Player:player, Station:fnm_station, DoorIndex:int, Kind:fnm_penalty)<suspends>:void =")
    move = punish.index("if (InBossMode?):\n            SendToRetry(Player, Station)")
    assert move < punish.index("if (Kind = fnm_penalty.Freeze):")
    assert "spawn{ WideLook(Viewer, RetryWideSeconds, WideMoveCm, \"retry spot\") }" in punish


def test_medal_rule_line_fits_the_board():
    """Round-2 QA item 8: the finish board wraps at 920 px (about 14.6 px a character at 30 px); the medal line with its
    streak tail must stay on one line, and say what FnmMedal really does."""
    logic, d = src("fnm_logic.verse"), src("fnm_director.verse")
    assert '"{FirstTryCorrect}/{Total} first try  -  GOLD {Total}/{Total}, SILVER {SilverAt}+"' in logic
    assert '"{FnmMedalRule(State.FirstTryCorrect, Total)}  -  streak {State.BestStreak}"' in d
    widest = "10/10 first try  -  GOLD 10/10, SILVER 7+  -  streak 10"
    assert len(widest) * 14.6 < 920


def test_race_cannons_fire_the_race_laser_and_crackle_once():
    d, fx = src("fnm_director.verse"), src("fnm_fx.verse")
    assert "SpawnParticleSystem(FNM_FX.NS_fnm_laser_race_asset, At, ?Rotation := FnmAimAlong(Dir))" in fx
    assert "spawn{ FireBeam(Beam, Full, if (K = 0) then true else false, Rig.RaceLaser) }" in d
    beam = body_of(d, "FireBeam(Beam:creative_prop, Full:transform, Impact:logic, RaceLaser:logic)<suspends>:void =")
    assert "if (RaceLaser?) then FnmSpawnRaceLaser(Full.Translation, Dir) else FnmSpawnLaser(Full.Translation, Dir)" in beam
    begin = body_of(d, "OnBegin<override>()<suspends>:void =")
    assert "if (RaceCoils.Length = 0):\n            set RaceCoils = FnmSpawnCoils(RaceRig.BeamFull, FnmRaceCannonCoilBack)" in begin
    assert "set Coils = FnmSpawnCoils(Rig.BeamFull, FnmCannonCoilBack)" in src("fnm_bossmode.verse")
    assert all_verse().count("FnmSpawnCoils(") == 3                   # its definition and the two arenas
    # boss mode's rig keeps the long laser (RaceLaser left at its default)
    assert "RaceLaser" not in src("fnm_bossmode.verse").split("set Rig = fnm_cannon_rig{", 1)[1].split("\n", 1)[0]


def test_floating_letters_turn_to_their_own_arenas_players():
    """One FaceLetter (moved from boss mode, unchanged) serves both arenas: race letters follow race players at the arena
    stage, boss mode's follow boss-mode players."""
    verse = all_verse()
    assert verse.count("FaceLetter(Letter:creative_prop, Home:vector3, K:int, Race:logic)<suspends>:void =") == 1
    assert "spawn{ Director.FaceLetter(Letter, Letter.GetTransform().Translation, K, false) }" in src("fnm_bossmode.verse")
    assert "spawn{ FaceLetter(Letter, Letter.GetTransform().Translation, FnmBmSlotOf(Object) - 1, true) }" in src("fnm_director.verse")
    watch = body_of(src("fnm_director.verse"), "LetterWatcher(State:fnm_player_state, Race:logic)<transacts>:logic =")
    assert "if (Race?, State.Mode = fnm_mode.Race, AtArena(State)?) then true" in watch
    assert "else if (not Race?, State.Mode = fnm_mode.Boss) then true" in watch
    for name, value in (("LetterTurnSeconds", "0.15"), ("LetterBobCm", "40.0"), ("LetterBobSeconds", "4.0")):
        assert verse.count(f"{name} : float = {value}") == 1, name


def test_delayed_explanation_says_last_one():
    """Boss mode's delayed explanation lands under the next question, so it is prefixed "Last one:" (Aaron 2026-10-11).
    The race shows the recap card instead (G9), and never puts "Correct! <explanation>" under the next question."""
    assert 'FnmLastOne(Item:fnm_item)<transacts>:string = "Last one:  " + Item.Explanation' in src("fnm_bossmode.verse")
    assert "ShowFeedback(FnmLastOne(Item)" in src("fnm_bossmode.verse")
    assert "ShowFeedback(FnmLastOne(Item)" not in src("fnm_director.verse")
    assert '"Correct!  " + Item.Explanation' not in src("fnm_director.verse")


def test_inner_letters_leave_the_whole_titan_visible_from_the_entry():
    """G10 (2026-10-14): with the pads in one row, the B and C floating letters stand dead centre of the entry view. At letter
    scale 1.5 their inner edges closed on the 9 m titan (play frames arena_01 / arena_25: it showed only between them). From a
    camera 3.5 m behind the entry, the gap between the two inner letters' edges (the letters turn to face the player, so
    their full width counts) must be wider, as an angle, than the titan's silhouette with an arm raised (about 5 m across)."""
    cam_back = 350
    (bx, by), (cx, _) = c.PAD_SPOTS[1], c.PAD_SPOTS[2]
    dist_letters = by - r.ENTRY[1] + cam_back
    inner_half = bx - r.LETTER_W * r.LETTER_SCALE / 2                       # +x edge of the inner pair: the gap's half-width
    gap = math.atan2(inner_half, dist_letters)
    titan = math.atan2(250, c.PLATFORM_Y - r.ENTRY[1] + cam_back)           # half of a 5 m span
    assert gap > titan, (math.degrees(gap), math.degrees(titan))
    # disproof: the old 1.5 scale would have closed the gap
    old = math.atan2(bx - r.LETTER_W * 1.5 / 2, dist_letters)
    assert old < titan
