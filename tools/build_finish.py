"""The victory area at the finish: a giant all-time screen above the end wall and a podium with two buttons
(NEW RACE, CHANGE SKILL). Idempotent via actor tag `fnm_finish_rig`; reads the finish geometry from the course actors,
so rerun after a course rebuild. The director finds everything by Verse tag (console/verse/fnm_tags.verse):
fnm_hall_head / fnm_hall_row billboards (rows ordered by height) and fnm_new_race / fnm_change_skill buttons.

    python tools/build_finish.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import build_course as c  # noqa: E402
import build_decor as d  # noqa: E402
import uefn_mcp as u  # noqa: E402

TAG = "fnm_finish_rig"
BUTTON = "/CreativeCoreDevices/SetupAssets/PID_Device_Button.PID_Device_Button"
PODIUM = "PPID_CR_Legacy_Podium"

SCREEN_SCALE = 5.0      # billboard frame: ~357 x 161 cm per unit scale, pivot at its bottom edge
SCREEN_BOTTOM = 120     # the screen IS the end wall's board (seen in play: higher, it was out of view)
HEAD_SCALE = 3.0
ROW_SCALE = 2.2
# Billboard text size (device range 8-24). At 24 a row ("1.  Name   0:59.6") wrapped onto two lines in play.
HEAD_TEXT = 18
# A billboard draws its text near the top of its frame, ~150 cm per unit scale above the actor (seen in play: placed
# by the actor, every line rose to the top of the screen). Positions below are where the text shows. The heading is
# split in two lines (a fixed ALL-TIME BEST and the skill name): one line of both wrapped in play.
TEXT_RISE = 150
ROW_TEXT = 16
ROWS = 6                # kept above the podiums; rows lower than that hid behind them
ROW_STEP = 90           # cm between row billboards
GOLD = {"r": 1.0, "g": 0.8, "b": 0.1, "a": 1.0}
WHITE = {"r": 1.0, "g": 1.0, "b": 1.0, "a": 1.0}
PODIUM_BACK = 600       # podiums stand this far in front of the end wall
PODIUM_SPREAD = 320     # each podium this far left / right of the centre line
PODIUM_SCALE = 1.5      # a 177 cm lectern: its button at eye height, where the third-person crosshair aims


def device(asset, label, x, y, z, yaw=0.0, s=1.0, tags=()):
    r = u.call(c.DEV, "PlaceDevice", {"assetPath": c.ref(asset), "transform": c.xform(x, y, z, s, s, s, yaw)})
    a = r["returnValue"]["refPath"]
    u.call(c.ACTOR, "add_tag", {"actor": c.ref(a), "tag": TAG})
    u.call(c.ACTOR, "set_label", {"actor": c.ref(a), "label": label})
    if tags:
        c.verse_tags(a, PROJECT, tags)
    return a


def prop(name, label, x, y, z, yaw=0.0, s=1.0):
    """A gallery prop tagged as finish rig only (build_decor.place would tag it as decor)."""
    r = u.call(c.SCENE, "add_to_scene_from_asset", {"asset_path": d.asset(name), "name": label,
                                                    "xform": c.xform(x, y, z, s, s, s, yaw)})
    a = r["returnValue"]["refPath"]
    u.call(c.ACTOR, "add_tag", {"actor": c.ref(a), "tag": TAG})
    u.call(c.ACTOR, "set_label", {"actor": c.ref(a), "label": label})
    return a


def board(label, x, y, z, scale, text, colour, tags=(), border=False, size=24):
    a = device(c.BILLBOARD, label, x, y, z, yaw=180, s=scale, tags=tags)
    values = {"text": text, "textColor": colour, "textSize": size, "textJustification": "Center", "showBorder": border}
    if border:
        values["backgroundColor"] = {"r": 0.01, "g": 0.01, "b": 0.04, "a": 1.0}
    c.props(a, values)
    return a


def build():
    print("removed", c.clear(TAG), "old finish rig actors")
    b = d.course()
    wl, wr, end, floor = (b[f"FNM_Finish_{n}"] for n in ("WallL", "WallR", "WallEnd", "Floor"))
    left, right = wl["min"]["x"], wr["max"]["x"]
    cx, ey, oz = (left + right) / 2, end["min"]["y"], floor["max"]["z"]

    # The screen: a framed dark billboard as the backdrop, a gold heading and ROWS white rows in front of it.
    z0 = oz + SCREEN_BOTTOM
    height = 161 * SCREEN_SCALE
    board("FNM_Hall_Screen", cx, ey - 15, z0, SCREEN_SCALE, "", WHITE, border=True)
    top = z0 + height
    board("FNM_Hall_Title", cx, ey - 40, top - 70 - TEXT_RISE * HEAD_SCALE, HEAD_SCALE, "ALL-TIME BEST", GOLD, size=HEAD_TEXT)
    board("FNM_Hall_Head", cx, ey - 40, top - 150 - TEXT_RISE * HEAD_SCALE, HEAD_SCALE, "", GOLD, tags=["fnm_hall_head"], size=HEAD_TEXT)
    for i in range(ROWS):
        board(f"FNM_Hall_Row{i + 1}", cx, ey - 40, top - 250 - i * ROW_STEP - TEXT_RISE * ROW_SCALE, ROW_SCALE, "", WHITE, tags=["fnm_hall_row"], size=ROW_TEXT)

    # The podium: two lecterns facing the way players arrive, a button on each and a label above it.
    for name, side, tag in (("NewRace", 1, "fnm_new_race"), ("ChangeSkill", -1, "fnm_change_skill")):
        x, y = cx + side * PODIUM_SPREAD, ey - PODIUM_BACK
        prop(PODIUM, f"FNM_Podium_{name}", x, y, oz, yaw=-90, s=PODIUM_SCALE)
        button = device(BUTTON, f"FNM_Button_{name}", x, y - 20, oz + 118 * PODIUM_SCALE, yaw=BUTTON_YAW, tags=[tag])
        c.props(button, {"interactionRadius": BUTTON_REACH})
        board(f"FNM_Label_{name}", x, y - 45, oz + 118 * PODIUM_SCALE - 45, 0.6, "NEW RACE" if side > 0 else "CHANGE SKILL", GOLD)
    print(f"finish rig built at x={cx:.0f} y={ey:.0f} level {oz:.0f}")


# Look anywhere this close to the button to press it (device range 0-2.5; 0 = exact aim, which a third-person
# camera over a lectern made hard in play).
BUTTON_REACH = 0.6
BUTTON_YAW = 180        # seen in a capture: at yaw 90 the button faces -X; 180 turns it to -Y, toward arriving players


if __name__ == "__main__":
    root = u.call("ValkyrieToolset.VerseToolset", "ListFiles", {"path": "", "bRecursive": False})
    PROJECT = next(e["name"] for e in root["returnValue"] if e["type"] == "Directory" and "(" not in e["name"]).strip("/")
    build()
    u.call("editor_toolset.toolsets.asset.AssetTools", "save_assets", {"asset_paths": []})
