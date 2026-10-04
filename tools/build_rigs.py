"""Place the penalty rigs (console/verse/fnm_rig.verse) in the open UEFN project through UEFN MCP.

Each rig is a prop or device parked underground, out of sight, that the director moves onto a punished
player: an ice cube (Freeze) and a ring of spears that burst out of the floor (Spike). Yeet needs no rig.
COPIES of each so players punished at the same moment each get their own.
Real Fortnite traps can't be used: placed traps (BR TID_Floor_Spikes_Athena_R_T03 and the Creative
TID_Figment_Floor_Spikes_Athena_R_T01) both fail island validation as illegal references.

Idempotent: every actor this script creates is tagged TAG; a run first deletes everything with TAG.

    python tools/build_rigs.py [--copies 4]
"""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import uefn_mcp as u  # noqa: E402
from build_course import ACTOR, DEV, SCENE, ref, verse_tags, xform  # noqa: E402

TAG = "fnm_rigs"
PARK = (-4000, -8000, -1500)   # underground, away from the course
PITCH = 800                    # spacing between parked parts (cm)

# (label, asset, Verse tag, scale, placed as device?, parts per copy)
RIGS = [
    # 2 m Fortnite ice cube, sized to a standing player (bigger fills the third-person view).
    ("Ice", "/CR_Legacy/Playsets/PlaysetProps/PPID_CR_Legacy_Apollo_IceCube_NoLoot.PPID_CR_Legacy_Apollo_IceCube_NoLoot",
     "fnm_ice", (0.9, 0.9, 1.05), False, 1),
    # Coliseum spear (1.8 m, pivot mid-shaft) scaled to 2.7 m; the director rings SpearCount of them.
    ("Spear", "/CR_Legacy/Playsets/PlaysetProps/PPID_CR_Legacy_Apollo_Coliseum_Spear_01.PPID_CR_Legacy_Apollo_Coliseum_Spear_01",
     "fnm_spike", (1.5, 1.5, 1.5), False, 6),
]


def props_set(actor, values):
    u.call("editor_toolset.toolsets.object.ObjectTools", "set_properties",
           {"instance": ref(actor), "values": json.dumps(values)})


def clear(tag):
    found = u.call(SCENE, "find_actors", {"tag": tag, "collision_channels": []})
    actors = found if isinstance(found, list) else found.get("returnValue", [])
    for a in actors:
        u.call(SCENE, "remove_from_scene", {"actor": ref(a["actorPath"] if isinstance(a, dict) else a)})
    return len(actors)


def build(copies):
    root = u.call("ValkyrieToolset.VerseToolset", "ListFiles", {"path": "", "bRecursive": False})
    project = next(e["name"] for e in root["returnValue"] if e["type"] == "Directory" and "(" not in e["name"]).strip("/")
    print("removed", clear(TAG), "old rig actors;", clear("fnm_test"), "test actors")
    for row, (label, asset, vtag, (sx, sy, sz), is_device, per_copy) in enumerate(RIGS):
        for n in range(copies * per_copy):
            x, y, z = PARK[0] + PITCH * n, PARK[1] - PITCH * row, PARK[2]
            t = xform(x, y, z, sx, sy, sz)
            if is_device:
                r = u.call(DEV, "PlaceDevice", {"assetPath": ref(asset), "transform": t})
            else:
                r = u.call(SCENE, "add_to_scene_from_asset", {"asset_path": asset, "name": f"FNM_Rig_{label}{n + 1}", "xform": t})
            actor = r["returnValue"]["refPath"]
            u.call(ACTOR, "add_tag", {"actor": ref(actor), "tag": TAG})
            u.call(ACTOR, "set_label", {"actor": ref(actor), "label": f"FNM_Rig_{label}{n + 1}"})
            verse_tags(actor, project, [vtag])
            # Visual only: with collision the third-person camera is pushed inside the cube or spear ring and
            # the view closes in (bNoCameraCollision is not settable from MCP; bNoCollision is).
            props_set(actor, {"bNoCollision": True})
        print(label, copies * per_copy, "placed")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--copies", type=int, default=4)
    build(ap.parse_args().copies)
