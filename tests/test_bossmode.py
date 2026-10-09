"""BOSS BATTLE mode's Verse agrees with its spec (BOSS_MODE.md): the level table (section 4), the tags the runtime looks
up exist in fnm_tags.verse, the debug hooks ship off, the picker and win-board choices exist, the two boss textures are
referenced, the race arena's cannon log line is unchanged, and the player-facing copy of section 9 is in the Verse.
Regex over the source, like test_audio_cues.py: Verse is compiled only inside UEFN."""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VERSE = ROOT / "console" / "verse"


def src(name):
    return (VERSE / name).read_text(encoding="utf-8")


def all_verse():
    return "\n".join(p.read_text(encoding="utf-8") for p in sorted(VERSE.glob("*.verse")))


ROW = re.compile(r'fnm_bm_level\{Hits := (\d+), SpawnSeconds := ([\d.]+), Gates := (\d+), MaxAlive := (\d+), '
                 r'Anger := "([^"]*)", Banner := "([^"]*)", Perches := array\{([\d, ]*)\}, WeaponName := "([^"]*)", '
                 r'Creatures := array\{([\d, ]*)\}\}')


def ints(s):
    return [int(p) for p in s.replace(" ", "").split(",") if p]


def levels(text=None):
    text = src("fnm_bossmode.verse") if text is None else text
    body = text.split("FnmBmLevels()<transacts>:[]fnm_bm_level = array:\n", 1)[1].split("\n\n", 1)[0]
    rows = []
    for m in ROW.finditer(body):
        hits, secs, gates, alive, anger, banner, perches, weapon, creatures = m.groups()
        rows.append(dict(hits=int(hits), secs=float(secs), gates=int(gates), alive=int(alive), anger=anger,
                         banner=banner, perches=ints(perches), weapon=weapon, creatures=ints(creatures)))
    return rows


def test_level_table_matches_spec():
    rows = levels()
    assert len(rows) == 5
    assert [r["hits"] for r in rows] == [2, 3, 3, 4, 4]
    assert sum(r["hits"] for r in rows) == 16
    secs = [r["secs"] for r in rows]
    assert secs == [20.0, 15.0, 12.0, 9.0, 7.0]
    assert all(a > b for a, b in zip(secs, secs[1:]))                  # strictly faster spawns
    gates = [r["gates"] for r in rows]
    assert all(a <= b for a, b in zip(gates, gates[1:])) and max(gates) <= 4
    alive = [r["alive"] for r in rows]
    assert alive == [2, 3, 4, 5, 6]
    assert all(a <= b for a, b in zip(alive, alive[1:])) and max(alive) <= 6
    assert [r["anger"] for r in rows] == ["GRUMPY", "ANGRY", "FURIOUS", "RAGING", "UNHINGED"]
    assert [r["banner"] for r in rows] == ["HERE HE COMES!", "HE'S ANGRY!", "HE'S FURIOUS!", "HE'S RAGING!",
                                           "FINAL LEVEL. UNHINGED!"]
    assert [r["weapon"] for r in rows] == ["SMG", "Pump Shotgun", "Assault Rifle", "Heavy Sniper", "Rocket Launcher"]


def test_perches_per_level():
    rows = levels()
    assert [r["perches"] for r in rows[:4]] == [[1], [2], [3], [4]]
    assert sorted(rows[4]["perches"]) == [3, 4]
    for r in rows:
        assert r["perches"] and all(1 <= p <= 4 for p in r["perches"])
    text = src("fnm_bossmode.verse")
    for name in ("FRONT-RIGHT PERCH", "FRONT-LEFT PERCH", "BACK-RIGHT PERCH", "BACK-LEFT PERCH", "BACK PERCHES"):
        assert f'"{name}"' in text, name


def test_level_count_and_boss_lines():
    text = src("fnm_bossmode.verse")
    assert "FnmBmLevelCount()<transacts>:int = 5" in text
    for line in ("You dare challenge ME?!", "Minions! GET THEM!", "Is that all you've got?!", "Now I'm ANGRY!",
                 "NO MORE GAMES! EVERYONE, ATTACK!"):
        assert f'"{line}"' in text, line


def test_every_bm_tag_the_runtime_names_is_declared():
    tags = src("fnm_tags.verse")
    declared = set(re.findall(r"^(fnm_bm\w*) := class\(tag\)\{\}", tags, re.M))
    runtime = src("fnm_bossmode.verse") + src("fnm_director.verse")
    used = set(re.findall(r"FindCreativeObjectsWithTag\((fnm_bm\w*)\)", runtime))
    used |= set(re.findall(r"FindStationParts\((fnm_bm\w*)\)", runtime))
    used |= set(re.findall(r"BuildRig\(\"\w+\", (fnm_bm\w*)\)", runtime))
    used |= set(re.findall(r"Has\[(fnm_bm\w*)\{\}\]", runtime))
    expected = {"fnm_bm", "fnm_bm_boss", "fnm_bm_gate", "fnm_bm_gate_fx", "fnm_bm_perch", "fnm_bm_perch_fx",
                "fnm_bm_grant", "fnm_bm_cannon_fx", "fnm_bm_strike", "fnm_bm_blast", "fnm_bm_nuke_fx",
                "fnm_bm_anger_fx", "fnm_bm_creature"} | {f"fnm_bm_slot_{n}" for n in range(1, 6)}
    assert used == expected
    assert used <= declared, used - declared


def test_slot_tags_list_has_five():
    tags = src("fnm_tags.verse")
    body = re.search(r"FnmBmSlotTags\(\)<transacts>:\[\]castable_subtype\(tag\) = array\{(.*)\}", tags).group(1)
    assert [t.strip() for t in body.split(",")] == [f"fnm_bm_slot_{n}" for n in range(1, 6)]


SHIP_DEFAULTS = ("DebugAutoBoss : logic = false", "DebugBossLevel : int = 0", "DebugBossHold : float = 0.0", "DebugAutoRightAnswers : logic = false",
                 "DebugAutoPick : int = -1", "DebugAutoWrongAnswers : int = 0", "BmRespawnSeconds : float = 4.0",
                 "BmSummonSeconds : float = 5.0", "NukeSeconds : float = 2.5", "BossBoardKey : int = 9999")


def test_ship_defaults():
    director = src("fnm_director.verse")
    for line in SHIP_DEFAULTS:
        assert line in director, line


def test_picker_choices_and_call_sites():
    ui = src("fnm_ui.verse")
    body = ui.split("fnm_pick := enum:\n", 1)[1].split("\n\n", 1)[0]
    members = [l.strip() for l in body.splitlines() if l.strip() and not l.strip().startswith("#")]
    assert members == ["Grade", "Skill", "Back", "ChangeSkill", "Close", "Boss", "Again"]
    assert "ShowGradeStep(Grades:[]string, WithBoss:logic):void =" in ui
    assert "ShowFinishButtons(WithChange:logic, Again:logic):void =" in ui
    assert "ShowResults(Title:string, Medal:string," in ui
    director = src("fnm_director.verse")
    # The race keeps its board and buttons: FINISH! and no PLAY AGAIN.
    assert 'State.Hud.ShowResults("FINISH!", Medal, MedalColor,' in director
    assert "State.Hud.ShowFinishButtons(if (Cartridges.Length > 1) then true else false, false)" in director
    assert 'State.Hud.ShowResults("VICTORY!",' in src("fnm_bossmode.verse")
    assert "State.Hud.ShowFinishButtons(true, true)" in src("fnm_bossmode.verse")
    # A BOSS BATTLE click while picking is routed before the Back fall-through.
    choice = director.split("OnPickerChoice<override>", 1)[1].split("\n    Pick(", 1)[0]
    assert choice.index("fnm_pick.Boss") < choice.index("fnm_pick.Grade")
    assert "fnm_pick.Again" in choice


def test_boss_textures_referenced():
    verse = all_verse()
    assert "FNM_Art.T_fnm_banner" in verse
    assert "FNM_Art.T_fnm_nuke" in verse


def test_race_cannon_line_unchanged():
    director = src("fnm_director.verse")
    line = 'Print("FNM: cannons fired ({CannonFx.Length} muzzles, blast {Blast}) at {Feet}, {Left} hits to go")'
    assert director.count(line) == 1
    assert "spawn{ FireCannons(RaceRig, State.Player, Character, Stood, Left, false) }" in director
    assert "Director.FireCannons(Arena.Rig, State.Player, Character, Stood, Left, true)" in src("fnm_bossmode.verse")


HUD_COPY = ("BOSS BATTLE", "Every grade, every skill. Right answers NUKE the boss!", "Every skill, every grade",
            "MEGA NUKE!", "STEP ON THE RIGHT ANSWER!", "VICTORY!", "PLAY AGAIN", "TOP BOSS TIMES THIS SESSION",
            "Bullets can't hurt the boss. Step on the pad with the RIGHT ANSWER to nuke it!",
            "Knocked out! Back to the arena entry.", "WEAPON DROP: {Hint} - jump up and grab it!",
            "BOSS BATTLE  -  Level {State.Level}/{FnmBmLevelCount()}  -  {State.Cartridge.Title}",
            "MEGA NUKE!  {Left} TO GO", "MEGA NUKE!  LEVEL {L} CLEARED!", "MEGA NUKE!  BOSS DEFEATED!",
            "LEVEL {L} CLEARED!", "Boss defeated in {FnmClock(Time)}", "The boss summons his minions!")


def test_hud_copy_present():
    verse = all_verse()
    for copy in HUD_COPY:
        assert copy in verse, copy


# The log lines B4's acceptance waits on (BOSS_MODE.md section 12), as the Verse spells them.
LOG_LINES = ("FNM: boss mode: arena found: {Arena.Station.Doors.Length} pads, {Arena.CountSpawners(Arena.Gates)} gates, "
             "{Arena.CountTriggers(Arena.PerchTriggers)} perches, {Arena.CountSpawners(Arena.BossSpawners)} boss spawners, "
             "{Arena.CountTriggers(Arena.GrantTriggers)} granters, {Arena.Rig.Fx.Length} cannons",
             "FNM: boss mode: none (no fnm_bm entry teleporter)",
             "FNM: boss mode start for the player (level {Level})",
             "FNM: boss level {L} summon\"",
             "FNM: boss level {L} summoned: {Row.Gates} gates, every {FnmBmWholeSeconds(Row.SpawnSeconds)} s, "
             "max {Row.MaxAlive} alive, {Row.WeaponName} at {Hint}",
             "FNM: boss mode hit {State.Hits} by the player (level {L}, team {TeamHits}/{Need}), damage {Amount}, "
             "health {BossPercent()}%",
             "FNM: boss mode monster at gate {G + 1} (kind guard, {Count}/{Cap} alive)",
             "FNM: boss mode monster at gate {Out + 1} (kind creature, {Count}/{Cap} alive): {FnmBmCreatureName(Kind)}",
             "FNM: boss mode monster cap reached at level {Level} ({Up}/{Row.MaxAlive} alive)",
             "FNM: boss mode guard up at gate {G + 1} ({Alive()} alive)",
             "FNM: boss mode creature up: {FnmBmCreatureName(Kind)} at gate {G + 1} ({Alive()} alive)",
             "FNM: debug boss hold {FnmBmWholeSeconds(DebugBossHold)} s at level {BM.Level}",
             "FNM: boss mode wave: {Spawned} monsters spawned",
             "FNM: boss level {L} cleared",
             "FNM: boss mode weapon {Weapon} granted at perch {P} (level {Level})",
             "FNM: boss mode victory in {FnmClock(Time)}, {MedalName}, right first try",
             "FNM: debug boss mode done: victory={FnmYesNo(State.Finished)} level={State.Level}",
             "FNM: debug boss mode stuck at level {BM.Level}",
             "FNM: boss spawned (boss mode, level {Level})")


def test_log_lines_present():
    verse = all_verse()
    for line in LOG_LINES:
        assert line in verse, line


def test_cue_helpers_follow_levels():
    audio = src("fnm_audio.verse")
    level_cue = audio.split("FnmBmLevelCue(Level:int)<transacts>:fnm_cue =", 1)[1].split("\n\n", 1)[0]
    assert re.findall(r"fnm_cue\.(\w+)", level_cue) == ["BmLevel2", "BmLevel3", "BmLevel4", "BmLevel5", "BmStart"]
    boss_cue = audio.split("FnmBmBossCue(Level:int)<transacts>:fnm_cue =", 1)[1].split("\n\n", 1)[0]
    assert re.findall(r"fnm_cue\.(\w+)", boss_cue) == ["BmBossL2", "BmBossL3", "BmBossL4", "BmBossL5", "BmBossL1"]
    assert "if (Left >= 1, Left <= 4) then FnmHitCue(Left) else fnm_cue.BmMegaNuke" in audio


def test_race_paths_skip_boss_players():
    director = src("fnm_director.verse")
    for needle in ("for (State : PlayerStates, State.Mode = fnm_mode.Race, not State.Finished?, not State.Picking?, State.Stage = Index + 1):",
                   "if (State.Mode = fnm_mode.Race, not State.Finished?, not State.Picking?, State.CurrentItem >= 0, Station := Stations[State.Stage - 1],",
                   "if (State.Mode = fnm_mode.Race, not State.Finished?, not State.Picking?, not State.Busy?, State.CurrentItem >= 0,",
                   "for (Zone : IceZones, State.Mode = fnm_mode.Race, Zone.IsInVolume[State.Player]):",
                   "if (State.Mode = fnm_mode.Race, not State.Finished?, not State.Busy?, not State.Picking?):"):
        assert needle in director, needle
    assert "fnm_mode := enum{Race, Boss}" in director
    # Boss-mode pads answer on the trigger event only: the position backstop (WatchDoors) never sees that arena.
    assert "BM.Arena.Station" not in director.split("WatchDoors(State:fnm_player_state):void =", 1)[1].split("\n\n", 1)[0]


# ---------------------------------------------------------------- monsters, banner, boss line (B5, 2026-10-09)

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


def FnmGate(fn, k):
    """FnmBmCreatureGate(k) evaluated from its Verse if-chain."""
    for kk, g in re.findall(r"K = (\d)\) then (\d)", fn):
        if int(kk) == k:
            return int(g)
    return int(re.search(r"else (\d)\s*$", fn.strip()).group(1))


def creature_names():
    text = src("fnm_bossmode.verse")
    fn = text.split("FnmBmCreatureName(K:int)<transacts>:string =", 1)[1].split("\n\n", 1)[0]
    return dict((int(k), v) for k, v in re.findall(r'K = (\d)\) then "([^"]+)"', fn))


def test_creature_escalation_by_level():
    """L1 guards only; L2 + Fiends; L3 Fiends and Brutes; L4 Ranged and Brutes; L5 Red Fiends and Exploding Brutes.
    No Megabrute anywhere (too tough for grades 6-8)."""
    names = creature_names()
    kinds = [[names[k] for k in r["creatures"]] for r in levels()]
    assert kinds == [[], ["Fiend"], ["Fiend", "Brute"], ["Ranged", "Brute"], ["Red Fiend", "Exploding Brute"]]
    assert "Megabrute" not in names.values()


def test_creature_names_match_the_builder_slots():
    import sys as _sys
    _sys.path.insert(0, str(ROOT / "tools"))
    import build_bossmode as b
    assert creature_names() == {k: v for k, v in enumerate(b.CREATURES, 1)}
    text = src("fnm_bossmode.verse")
    fn = text.split("FnmBmCreatureGate(K:int)<transacts>:int =", 1)[1].split("\n\n", 1)[0]
    gates = {k: FnmGate(fn, k) for k in range(1, 6)}
    assert [gates[k] for k in range(1, 6)] == b.CREATURE_GATES
    # Every level's creature kinds come out of gates that level opens.
    for r in levels():
        for k in r["creatures"]:
            assert gates[k] <= r["gates"], (r, k)
    probed = ("Fiend, Red Fiend, Brute, Red Brute, Ranged, Megabrute, Ice Fiend, Major Ice Fiend, Ice Brute, "
              "Major Ice Brute, Ice Ranged, Poison Fiend, Exploding Brute").split(", ")   # LAYOUT.md probe answers
    assert set(b.CREATURES) <= set(probed)


def test_spawns_alternate_guard_and_creature_under_one_cap():
    text = src("fnm_bossmode.verse")
    spawn = body_of(text, "SpawnMonster(G:int, Count:int):void =")
    assert "spawn{ SpawnCreature(" in spawn and "spawn{ SpawnGuard(" in spawn
    assert "set CreatureNext = if (Row.Creatures.Length > 0, not CreatureNext?) then true else false" in spawn
    assert "set CreaturesPending += 1" in spawn and "set GuardsPending += 1" in spawn     # both count at once
    loop = body_of(text, "SpawnLoop()<suspends>:void =")
    assert "Up := Alive()" in loop and "if (Up < Row.MaxAlive):" in loop and "SpawnMonster(Slot, Up + 1)" in loop
    assert "SpawnMonster(K, " in body_of(text, "Wave():void =")
    # A level opens light: one guard (gate 1) and, with creatures, one creature; the rest come on the timer.
    opening = body_of(text, "OpenGates(Count:int):void =")
    assert opening.count("SpawnMonster(") == 2 and "SpawnMonster(0, Alive() + 1)" in opening
    assert "Spawner.Enable()" not in opening and "Spawn()" not in opening
    # A gate's guard spawner is switched on at its first guard (its Enable sends that guard).
    guard = body_of(text, "SpawnGuard(Gate:guard_spawner_device")
    assert guard.index("Gate.Enable()") < guard.index("return") < guard.index("Gate.SpawnAt(")
    # Nothing spawns a monster any other way: one SpawnAt per device kind, the plain Spawn() only as a guard's fallback.
    assert text.count("Gate.Spawn()") == 1 and "Gate.Spawn()" in body_of(text, "SpawnGuard(")
    assert text.count(".SpawnAt(") == 1 and "Gate.SpawnAt(" in body_of(text, "SpawnGuard(")
    # The cap counts living guards from the devices themselves, not their SpawnedEvent.
    alive = body_of(text, "Alive()<transacts>:int =")
    assert "Spawner.GetAgents()" in alive and "GuardsPending + CreaturesPending + CreatureAgents.Length" in alive
    # Creature eliminations count down.
    build = body_of(text, "Build():void =")
    assert "Spawner.EliminatedEvent.Subscribe(OnCreatureEliminated)" in build.split("Arena.Creatures", 1)[1]


def test_level_clear_removes_creatures():
    close = body_of(src("fnm_bossmode.verse"), "CloseGates():void =")
    assert "Creature.EliminateCreatures()" in close and "Creature.Disable()" in close
    assert close.index("set GatesOpen = 0") < close.index("EliminateCreatures")


def test_creature_api_is_the_digest_s():
    """Only members creature_spawner_device has in the 42.30 Fortnite digest (no Spawn(), no type setter); SpawnAt is
    not used (refused or never returning in the 2026-10-09 probes): the pulse lets the device's own first wave out."""
    allowed = {"SpawnedEvent", "SpawnAt", "EliminatedEvent", "Enable", "Disable", "DestroySpawner",
               "EliminateCreatures", "GetSpawnLimit"}
    pulse = body_of(src("fnm_bossmode.verse"), "SpawnCreature(")
    # The pulse: on, wait for the SpawnedEvent (the device's own first wave), off.
    assert pulse.index("Spawner.Enable()") < pulse.index("Spawner.SpawnedEvent.Await()") < pulse.index("Spawner.Disable()")
    assert "Sleep(CreatureWaitSeconds)" in pulse
    text = src("fnm_bossmode.verse")
    used = set(re.findall(r"\bCreature\.(\w+)", "\n".join(
        body_of(text, h) for h in ("SpawnMonster(G:int", "CloseGates()", "OpenGates("))))
    used |= set(re.findall(r"\bSpawner\.(\w+)", body_of(text, "SpawnCreature(")))
    guard_api = {"SpawnAt", "Spawn", "GetSpawnLimit", "GetAgents", "Enable", "Disable", "Reset"}
    guard_used = set(re.findall(r"\bGate\.(\w+)", body_of(text, "SpawnGuard(") + body_of(text, "SpawnMonster(G:int")))
    assert guard_used <= guard_api | {"GetTransform"}, guard_used
    assert used and used <= allowed, used - allowed


def test_boss_line_refreshes_on_hit_and_kill():
    text = src("fnm_bossmode.verse")
    assert "RefreshBossLines()" in body_of(text, "Hit(State:fnm_player_state):void =")
    cleared = body_of(text, "LevelCleared():void =")
    assert "set Downed = true" in cleared and "RefreshBossLines()" in cleared
    assert cleared.index("set BossAlive = false") < cleared.index("RefreshBossLines()")
    assert 'return "BOSS  ----------  0%   -   LEVEL {Level} CLEARED!"' in body_of(text, "BossLine(State:fnm_player_state):string =")


def test_banner_sits_between_slate_and_verdict():
    """At 1080p the slate ends near y 430 and the verdict label (image collapsed) spans about 680..790; the 200 px banner
    must fit between them. At 0.33 it covered the slate's STREAK and BOSS rows."""
    ui = src("fnm_ui.verse")
    slot = ui.split("Widget := Banner\n", 1)[1].split("SizeToContent", 1)[0]
    y = float(re.search(r"Minimum := vector2\{X := 0\.5, Y := ([\d.]+)\}", slot).group(1))
    verdict = ui.split("Widget := VerdictLabel", 1)[1].split("SizeToContent", 1)[0]
    vy = float(re.search(r"Minimum := vector2\{X := 0\.5, Y := ([\d.]+)\}", verdict).group(1))
    banner_h = float(re.search(r"BannerArt : texture_block = .*?Y := ([\d.]+)\}", ui).group(1))
    top, bottom = y * 1080 - banner_h / 2, y * 1080 + banner_h / 2
    label_top = vy * 1080 - 55            # the 96 px label alone, centred on the verdict slot
    assert top >= 430 + 20, top
    assert bottom <= label_top, (bottom, label_top)


def test_verdict_image_hidden_while_banner_up():
    ui = src("fnm_ui.verse")
    for fn in ("FlashVerdict(Correct:logic, Label:string):void =", "FlashNuke(Label:string, Seconds:float):void ="):
        body = body_of(ui, fn)
        assert "VerdictImage.SetVisibility(widget_visibility.Visible)" in body
        assert "if (not BannerUp?) then VerdictImage.SetVisibility(widget_visibility.Visible)" in body, fn
    show = body_of(ui, "ShowBanner(Big:string, Sub:string):void =")
    assert "set BannerUp = true" in show and "VerdictImage.SetVisibility(widget_visibility.Collapsed)" in show
    assert "set BannerUp = false" in body_of(ui, "HideBanner():void =")
