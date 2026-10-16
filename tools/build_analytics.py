"""Analytics devices for the Creator Portal funnel (G10, review gamification.md section 6 "Par calibration").

One `analytics_device` per station (10), one at the finish and one at the boss kill. The director (D) calls `Submit(Agent)`
when a player clears a station, finishes, or lands the killing hit; the Creator Portal then shows a per-station funnel,
the data the medal time gates are tuned from. Each device carries the Verse tags PROTOCOL / TEAM.md fix:

    station k   fnm_analytics + fnm_station_NN        (placed at that station's entry teleporter)
    finish      fnm_analytics + fnm_finish            (at the finish hallway's entry teleporter)
    boss        fnm_analytics + fnm_boss              (at the arena's entry teleporter)

Hidden in game. Idempotent: every actor this script places is tagged TAG; a run first deletes everything with TAG.
Reads the entry teleporters' places from the course actors, so rerun after a course rebuild.

    python tools/build_analytics.py            # build (needs the editor open; takes the UEFN write lock)
    python tools/build_analytics.py --check    # read-only: the 12 devices, their tags and event names
    python tools/build_analytics.py --remove   # delete them
"""
import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import uefn_mcp as u  # noqa: E402
from build_course import ACTOR, ASSETS, DEV, OBJ, SCENE, TAG as COURSE_TAG, clear, project_mount, ref, verse_tags, xform  # noqa: E402

TAG = "fnm_analytics_rig"
DEVICE = "/CRD_Analytic/SetupAssets/PID_Device_AnalyticDevice.PID_Device_AnalyticDevice"
STATIONS = 10
VERSE_ROOT_TAGS = Path.home() / "Documents/Fortnite Projects/FortniteMath/Content/fnm_tags.verse"
LIFT = 120      # cm above the entry teleporter's origin, off the floor and out of the way
# The Verse tags a device carries: fnm_analytics + one of these.
NAMES = {**{f"FNM_S{k:02d}_Entry": (f"FNM_Analytics_S{k:02d}", f"fnm_station_{k:02d}", f"fnm_station_{k:02d}")
            for k in range(1, STATIONS + 1)},
         "FNM_Finish_Entry": ("FNM_Analytics_Finish", "fnm_finish", "finish"),
         "FNM_Arena_Entry": ("FNM_Analytics_Boss", "fnm_boss", "boss_kill")}


def plan():
    """[(entry teleporter label, device label, second Verse tag, event name)] in course order. Pure: tests read it."""
    return [(entry, label, tag2, event) for entry, (label, tag2, event) in NAMES.items()]


def found(tag):
    r = u.call(SCENE, "find_actors", {"tag": tag, "collision_channels": []})
    return [a for a in (r if isinstance(r, list) else r.get("returnValue", [])) if isinstance(a, dict)]


def get(actor, keys):
    return json.loads(u.call(OBJ, "get_properties", {"instance": ref(actor), "properties": keys})["returnValue"])


def devices():
    """Every analytics device in the level (tagged or not), by actor path."""
    r = u.call(SCENE, "find_actors", {"name": "Analytic", "collision_channels": []})   # matches the label / name loosely
    return {a["actorPath"] for a in (r if isinstance(r, list) else r.get("returnValue", []))
            if isinstance(a, dict) and a.get("class", {}).get("refPath", "").endswith("Device_AnalyticDevice_V2_C")}


def place(transform):
    """PlaceDevice raises "Accessed None ... CallFunc_GetGameStateAthena_ReturnValue" (the device's construction script
    wants a game state the editor does not have) yet the device IS placed, transform and all (probed 2026-10-14), so a
    raise with that text is read as success and the new actor is found by diff. Any other error is real."""
    before = devices()
    try:
        return u.call(DEV, "PlaceDevice", {"assetPath": ref(DEVICE), "transform": transform})["returnValue"]["refPath"]
    except RuntimeError as e:
        if "GetGameStateAthena" not in str(e):
            raise
    new = devices() - before
    if len(new) != 1:
        sys.exit(f"PlaceDevice raised and left {len(new)} new analytics devices, wanted 1")
    return new.pop()


def build():
    project = project_mount().strip("/")
    entries = {a["label"]: a for a in found(COURSE_TAG) if a.get("label") in NAMES}
    missing = [e for e in NAMES if e not in entries]
    if missing:
        sys.exit(f"entry teleporters missing ({missing}): run the course build first")
    need = ["fnm_analytics"] + sorted({p[2] for p in plan()})
    text = VERSE_ROOT_TAGS.read_text(encoding="utf-8") if VERSE_ROOT_TAGS.exists() else ""
    absent = [n for n in need if f"{n} := class(tag)" not in text]
    if absent:
        sys.exit(f"the Verse root's fnm_tags.verse does not declare {absent} yet (the director's owner copies it in and runs "
                 f"BuildAll); a Verse tag can only be set once its class compiles. Nothing was placed.")
    print("removed", clear(TAG), "old analytics devices")
    for entry, label, tag2, event in plan():
        t = u.call(ACTOR, "get_actor_transform", {"actor": ref(entries[entry]["actorPath"])})["returnValue"]["location"]
        actor = place(xform(t["x"], t["y"], t["z"] + LIFT))
        u.call(ACTOR, "add_tag", {"actor": ref(actor), "tag": TAG})
        u.call(ACTOR, "set_label", {"actor": ref(actor), "label": label})
        # Tag first: the tag component rebuilds a device's sub-objects (uefn-mcp skill).
        verse_tags(actor, project, ["fnm_analytics", tag2])
        props = settings(actor, event)
        print(f"{label}: tags fnm_analytics + {tag2}; {props}")
    u.call(ASSETS, "save_assets", {"asset_paths": []})
    print(f"{len(found(TAG))} analytics devices tagged {TAG}")


def settings(actor, event):
    """Name the device's Analytics event and read it back. The device (Device_AnalyticDevice_V2, probed 2026-10-14) has
    `eventName` (string, default empty) and `visibleInGameComponent`; it has no mesh to show in play beyond its
    edit-only gizmo. Returns what it kept."""
    try:
        u.call(OBJ, "set_properties", {"instance": ref(actor), "values": json.dumps({"eventName": event})})
    except RuntimeError as e:        # the same construction-script noise as PlaceDevice; the read-back below decides
        if "GetGameStateAthena" not in str(e):
            raise
    got = get(actor, ["eventName"])
    if got.get("eventName") != event:
        sys.exit(f"{actor}: eventName read back {got!r}, wanted {event!r}")
    return got


def check():
    actors = sorted(found(TAG), key=lambda a: a.get("label", ""))
    print(len(actors), "analytics devices (want 12)")
    for a in actors:
        comps = u.call(ACTOR, "get_actor_transform", {"actor": ref(a["actorPath"])})["returnValue"]["location"]
        print(f"  {a['label']:24} ({comps['x']:.0f}, {comps['y']:.0f}, {comps['z']:.0f}) {get(a['actorPath'], ['eventName'])}")
    return len(actors)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true", help="list the placed devices and their read-back settings")
    ap.add_argument("--remove", action="store_true", help="delete every analytics device this script placed")
    a = ap.parse_args()
    if a.check:
        sys.exit(0 if check() == len(NAMES) else 1)
    elif a.remove:
        print("removed", clear(TAG), "analytics devices")
        u.call(ASSETS, "save_assets", {"asset_paths": []})
    else:
        build()
