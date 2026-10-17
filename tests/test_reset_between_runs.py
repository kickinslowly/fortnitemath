"""The map resets between runs (Aaron's Xbox playtest, 2026-10-16): a new run starts with an empty bag and every door shut,
boss chests re-arm a knocked-out fighter, and the island code watermark stays off the slate. Text pins on the seams, like
tests/test_g10_director.py, so a later edit cannot quietly drop one of them."""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DIRECTOR = (ROOT / "console/verse/fnm_director.verse").read_text(encoding="utf-8")
BOSSMODE = (ROOT / "console/verse/fnm_bossmode.verse").read_text(encoding="utf-8")
TAGS = (ROOT / "console/verse/fnm_tags.verse").read_text(encoding="utf-8")
RIGS = (ROOT / "tools/build_rigs.py").read_text(encoding="utf-8")
ISLAND = (ROOT / "tools/build_island.py").read_text(encoding="utf-8")
COURSE = (ROOT / "tools/build_course.py").read_text(encoding="utf-8")


def body(src, signature):
    return src.split(signature, 1)[1].split("\n\n", 1)[0]


def test_every_run_start_resets_the_inventory_and_respawns_keep_the_plain_loadout():
    assert "fnm_loadout_reset := class(tag){}" in TAGS
    assert "FindCreativeObjectsWithTag(fnm_loadout_reset), Trigger := trigger_device[Object]" in DIRECTOR
    for start in ("    Pick(State:fnm_player_state, Index:int):void =", "    StartNewRun(State:fnm_player_state)<suspends>:void ="):
        assert "ResetLoadout(State.Player)" in body(DIRECTOR, start), start
        assert "GiveLoadout(State.Player)" not in body(DIRECTOR, start), start
    assert "Director.ResetLoadout(State.Player)" in body(BOSSMODE, "    Start(State:fnm_player_state):void =")
    # a respawn re-arms without clearing: an eliminated player has dropped everything already (island ForceDrop)
    assert "GiveLoadout(State.Player)" in body(DIRECTOR, "    Respawned(State:fnm_player_state):void =")
    assert "Director.GiveLoadout(State.Player)" in body(BOSSMODE, "    Respawned(State:fnm_player_state):void =")
    reset = body(DIRECTOR, "    ResetLoadout(Player:player):void =")
    assert "Trigger := ResetTrigger?" in reset and "GiveLoadout(Player)" in reset       # falls back without the rig


def test_the_reset_granter_clears_the_bag_and_the_respawn_granter_keeps_it():
    rows = dict(re.findall(r'\("(\w+)", "(fnm_loadout\w*)"', RIGS))
    assert rows == {"Loadout": "fnm_loadout", "LoadoutReset": "fnm_loadout_reset"}
    assert '"fnm_loadout", {"grantBehavior": "Keep All", "grantCondition": "Only if Not Owned"}' in RIGS
    assert '"fnm_loadout_reset", {"grantBehavior": "Clear Inventory", "grantCondition": "Always"}' in RIGS
    assert "--loadout-only" in RIGS and "def loadout_only():" in RIGS


def test_doors_are_shut_at_a_run_start_and_for_the_station_ahead():
    assert "Locks : []lock_device = array{}" in body(DIRECTOR, "fnm_station := class:")
    parts = body(DIRECTOR, "    FindStationParts(StationTag:castable_subtype(tag))")
    assert "Lock := lock_device[Object]" in parts and "(Entry, Doors, Passages, Locks)" in parts
    assert "Locks := StationLocks}" in DIRECTOR
    for start in ("    Pick(State:fnm_player_state, Index:int):void =", "    StartNewRun(State:fnm_player_state)<suspends>:void ="):
        assert "CloseAllDoors(State.Player" in body(DIRECTOR, start), start
    advance = body(DIRECTOR, "    AdvancePlayer(State:fnm_player_state, Station:fnm_station, DoorIndex:int, ShowNow:logic):void =")
    assert "CloseDoors(State.Player, Ahead" in advance
    assert "Lock.Close(Player)" in body(DIRECTOR, "    CloseDoors(Player:player, Station:fnm_station, Why:string):void =")
    assert re.search(r"^    DebugLockCycleSeconds : float = 0\.0$", DIRECTOR, re.M)


def test_the_course_tool_puts_a_key_lock_on_every_door():
    assert 'LOCK = "/CreativeCoreDevices/SetupAssets/PID_CP_Devices_KeyLock_V2.PID_CP_Devices_KeyLock_V2"' in COURSE
    assert 'LOCK_SETTINGS = {"initial Door Position": "Closed", "starts Locked": "Unlocked", "visible During Game": False}' in COURSE
    station = COURSE.split("def station(", 1)[1].split("\ndef ", 1)[0]
    assert "door_lock(door, k, letter, cx, door_y, oz, project)" in station
    lock = COURSE.split("def door_lock(", 1)[1].split("\ndef ", 1)[0]
    assert '"lockableObject": {"refPath": door}' in lock and 'f"fnm_station_{k:02d}", f"fnm_door_{letter.lower()}"' in lock
    assert "--locks-only" in COURSE and "def locks_only():" in COURSE


def test_boss_chests_fire_the_granter_every_time_and_celebrate_the_first_grab_only():
    chest = body(BOSSMODE, "    OnChest(State:fnm_player_state, P:int):void =")
    assert chest.index("Trigger.Trigger(State.Player)") < chest.index("if (Taken?):")
    assert 'FlashBig("{Weapon} GET!"' in chest.split("else:", 1)[1]
    assert "You already have the" not in chest


def test_the_island_code_watermark_is_off_and_written_alone():
    settings = ISLAND.split("SETTINGS = {", 1)[1].split("\n}", 1)[0]
    assert '"publishedIslandCodeDisplay": "Off"' in settings
    assert '"bShowIslandCodeWatermark"' not in settings     # never written: writing it flips the enum back (2026-10-16)
    assert "--settings" in ISLAND
