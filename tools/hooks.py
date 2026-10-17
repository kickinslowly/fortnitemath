"""Read or set the placed fnm_director's @editable test hooks through UEFN MCP (no Verse edit, no BuildAll).

    python tools/hooks.py                                   # read every known hook
    python tools/hooks.py DebugAutoPick=0 DebugDoorTest=0   # set some (JSON values: 0, 2.5, true, false), read them back
    python tools/hooks.py --ship                            # every known hook back to its ship value, read back

The hooks and their ship values are the director's (CLAUDE.md "Test hooks on the director"); a hook missing here is set
by name all the same. A set takes effect at the next session launch (tools/playtest.py relaunches one). Values live in
the level, so save it (any build tool's save, or the editor) before closing UEFN if they should stay.
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import uefn_mcp as u  # noqa: E402

SCENE = "editor_toolset.toolsets.scene.SceneTools"
DEV = "ValkyrieToolset.DeviceToolset"
# Ship values (the Verse defaults): -1 = off for the index hooks, 0 / false for the rest.
SHIP = {
    "DebugAutoPick": -1, "DebugPickerSeconds": 0.0, "DebugPickerGrade": -1, "DebugAutoWrongAnswers": 0,
    "DebugAutoRightAnswers": False, "DebugAutoRightOffsetY": 0.0, "DebugIgnoreTriggerEvents": False, "DebugVictoryTest": False,
    "DebugPassageTest": False, "DebugDoorTest": -1, "DebugLockCycleSeconds": 0.0, "DebugStartStage": 0, "DebugSkipTest": False,
    "DebugStrikeSelf": False, "DebugPickupTest": False, "DebugFarPillar": 0,
    "DebugAutoBoss": False, "DebugBossLevel": 0, "DebugBossHold": 0.0, "DebugBossChest": 0,
}


def ref(path):
    return {"refPath": path}


def director():
    found = u.call(SCENE, "find_actors", {"name": "fnm_director", "collision_channels": []})
    actors = found if isinstance(found, list) else found.get("returnValue", [])
    actors = [a for a in actors if isinstance(a, dict)]
    if not actors:
        sys.exit("no fnm_director in the level")
    return actors[0]["actorPath"]


def read(names):
    r = u.call(DEV, "GetDeviceProperties", {"device": ref(director()), "propertyNames": list(names)})["returnValue"]
    return json.loads(r) if isinstance(r, str) else r


def write(values):
    d = director()
    for name, value in values.items():
        u.call(DEV, "SetDeviceProperty", {"device": ref(d), "propertyName": name, "value": json.dumps(value)})
    back = read(values)
    wrong = {k: back.get(k) for k, v in values.items() if back.get(k) != v}
    if wrong:
        sys.exit(f"hooks not taken: {wrong}")
    return back


def main(argv):
    if argv == ["--ship"]:
        back = write(SHIP)
    elif argv:
        values = {}
        for arg in argv:
            name, _, raw = arg.partition("=")
            if not raw:
                sys.exit(f"expected Name=value, got {arg!r}")
            values[name] = json.loads(raw)
        back = write(values)
    else:
        back = read(SHIP)
    for name, value in back.items():
        ship = SHIP.get(name)
        print(f"  {name} = {json.dumps(value)}" + ("" if ship is None or ship == value else f"   (ship {json.dumps(ship)})"))


if __name__ == "__main__":
    main(sys.argv[1:])
