"""Import Volt, the robot host (Meshy rig + animations, art/mascot/raw/*.fbx), into the UEFN project as FNM_MascotArt:
ONE skeletal mesh (SK_fnm_volt, from idle_0.fbx: mesh, skeleton, 2K base colour texture) and one AnimSequence per clip
(A_fnm_volt_<clip>). Idempotent: deletes FNM_MascotArt first.

    python tools/import_mascot.py                 # every clip shared on idle's mesh + skeleton (the default)
    python tools/import_mascot.py --own ymca      # import clip ymca with its OWN mesh (the titan's way), if it misplays shared

The folder is FNM_MascotArt, not a Verse-style name: a content folder becomes a Verse module (uefn-mcp skill).

Memory (the spectacle review's section 4a: a skeletal mesh per clip is a full mesh copy, and the titan does exactly that):
every Meshy clip FBX carries the skin too, but `SkeletalMeshTools.import_file` takes an existing `skeleton`, so each clip is
imported against idle's skeleton with no materials or textures, its AnimSequence is moved next to the idle's, and the clip's
throwaway mesh is deleted with its temp folder. The result is ONE mesh and ONE texture and N animations; every Animated Mesh
device names SK_fnm_volt and its own clip. A clip that plays wrong on the device (the titan's chest pound tipped flat, its
knockdown spun on the spot; BOSS_MODE 15b) goes in OWN: imported with its own mesh and skeleton under FNM_MascotArt/Clip_<clip>,
sharing idle's material (so no second texture).

Seen in play 2026-10-13 (headless, frames sampled over a loop each): wave and ymca (the two placed), idle, dance, victory, cheer
and wag all play upright on idle's skeleton, so OWN_MESH is empty. Not a misplay: the wag leans its big head ~40 degrees toward
the viewer for ~1 s of every 5 (Blender reads the same lean in the FBX: head joint z 0.82 -> 0.69 m, forward 0.2 m), which a
front view foreshortens to a dome; dance (Funny Dancing 1) spins and bows by design. A clip whose FBX is not in art/mascot/raw
(not committed) is skipped with a note, so a checkout that keeps only idle + wave + ymca still imports.
"""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import uefn_mcp as u  # noqa: E402

ASSETS = "editor_toolset.toolsets.asset.AssetTools"
SKEL = "editor_toolset.toolsets.skeletal_mesh.SkeletalMeshTools"
OBJ = "editor_toolset.toolsets.object.ObjectTools"
RAW = Path(__file__).resolve().parent.parent / "art" / "mascot" / "raw"

ART = "FNM_MascotArt"
MESH = "SK_fnm_volt"             # idle_0.fbx: the one mesh, its skeleton SK_fnm_volt_Skeleton, texture Material_0_baseColor
BASE = "idle_0"
# Clip name (as the devices use it) -> Meshy FBX stem. The number is Meshy's action id. idle is the mesh's own clip.
CLIPS = {"idle": "idle_0", "wave": "wave_28", "ymca": "ymca_596", "dance": "dance_22", "victory": "victory_59",
         "cheer": "cheer_298", "wag": "wag_409"}
# Clips that are imported with their own mesh because they misplay on the shared skeleton (none: all seven were sampled in play;
# `--own` overrides). Written here so build_mascot and the tests read the same list.
OWN_MESH = frozenset()
# The clips the world needs (build_mascot places wave and ymca on idle's mesh); the others are spare, for a director that wants
# Volt to wag at a wrong door or cheer a streak, and are skipped when their FBX is missing.
REQUIRED = ("idle", "wave", "ymca")


def mount():
    r = u.call(ASSETS, "find_assets", {"folder_path": "", "name": "M_fnm_wall_bm_marble", "recursive": True})["returnValue"]
    return "/" + r[0].split("/")[1]


def mesh_path(project, clip, own=OWN_MESH):
    """The skeletal mesh refPath a device plays `clip` on."""
    if clip in own:
        return f"/{project}/{ART}/Clip_{clip}/{MESH}_{clip}.{MESH}_{clip}"
    return f"/{project}/{ART}/Volt/{MESH}.{MESH}"


def anim_path(project, clip, own=OWN_MESH):
    """The AnimSequence refPath for `clip`."""
    folder = f"Clip_{clip}" if clip in own else "Volt"
    return f"/{project}/{ART}/{folder}/A_fnm_volt_{clip}.A_fnm_volt_{clip}"


def _find(folder, name):
    return u.call(ASSETS, "find_assets", {"folder_path": folder, "name": name, "recursive": False})["returnValue"]


def _move_anim(src_folder, mesh_name, dst):
    found = _find(src_folder, f"{mesh_name}_Anim")
    if len(found) != 1:
        sys.exit(f"expected one {mesh_name}_Anim under {src_folder}, found {found}")
    u.call(ASSETS, "move", {"path": found[0].split(".")[0], "new_path": dst})


def main(own=OWN_MESH):
    m = mount()
    folder = f"{m}/{ART}"
    if u.call(ASSETS, "exists", {"path": folder})["returnValue"]:
        u.call(ASSETS, "delete", {"path": folder})
    volt = f"{folder}/Volt"
    # The base: idle's mesh, skeleton, material and texture, and its own animation.
    u.call(SKEL, "import_file", {"folder_path": volt, "asset_name": MESH, "source_file": str(RAW / f"{BASE}.fbx"),
                                 "import_materials": True, "import_textures": True, "import_animations": True})
    _move_anim(volt, MESH, f"{volt}/A_fnm_volt_idle")
    skeleton = {"refPath": f"{volt}/{MESH}_Skeleton.{MESH}_Skeleton"}
    material = {"refPath": f"{volt}/Material_0.Material_0"}
    for clip, stem in CLIPS.items():
        if clip == "idle":
            continue
        if not (RAW / f"{stem}.fbx").is_file():
            if clip in REQUIRED:
                sys.exit(f"{RAW / (stem + '.fbx')} is missing and {clip} is needed")
            print(f"  skipped {clip}: {stem}.fbx not in art/mascot/raw")
            continue
        if clip in own:
            # Its own mesh and skeleton (the titan's way), idle's material so the texture is not imported twice.
            sub = f"{folder}/Clip_{clip}"
            name = f"{MESH}_{clip}"
            u.call(SKEL, "import_file", {"folder_path": sub, "asset_name": name, "source_file": str(RAW / f"{stem}.fbx"),
                                         "import_materials": False, "import_textures": False, "import_animations": True})
            u.call(SKEL, "set_material", {"mesh": {"refPath": f"{sub}/{name}.{name}"}, "slot_name": "Material_0",
                                          "material": material})
            _move_anim(sub, name, f"{sub}/A_fnm_volt_{clip}")
        else:
            # Animation only, bound to idle's skeleton: the throwaway mesh and its folder are deleted.
            tmp = f"{folder}/Tmp_{clip}"
            name = f"{MESH}_tmp_{clip}"
            u.call(SKEL, "import_file", {"folder_path": tmp, "asset_name": name, "source_file": str(RAW / f"{stem}.fbx"),
                                         "skeleton": skeleton, "import_materials": False, "import_textures": False,
                                         "import_animations": True})
            _move_anim(tmp, name, f"{volt}/A_fnm_volt_{clip}")
            u.call(ASSETS, "delete", {"path": tmp})
    # Full-size texture in play: the import's LOD bias 1 drops the top mip (2048 -> 1024) on a 3 m robot.
    for t in _find(volt, "baseColor"):
        u.call(OBJ, "set_properties", {"instance": {"refPath": t}, "values": json.dumps({"lODBias": 0})})
    u.call(ASSETS, "save_assets", {"asset_paths": []})
    for a in u.call(ASSETS, "find_assets", {"folder_path": folder, "name": "", "recursive": True})["returnValue"]:
        print(" ", a)
    mesh = {"refPath": f"{volt}/{MESH}.{MESH}"}
    print("mesh vertices", u.call(SKEL, "get_vertex_count", {"mesh": mesh, "lod_index": 0})["returnValue"],
          "bounds", u.call(SKEL, "get_bounds", {"mesh": mesh})["returnValue"])


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--own", default="", help="comma list of clips to import with their own mesh (e.g. ymca)")
    args = ap.parse_args()
    chosen = frozenset(x for x in args.own.split(",") if x)
    bad = chosen - set(CLIPS)
    if bad:
        sys.exit(f"unknown clips {sorted(bad)}; known: {sorted(CLIPS)}")
    main(chosen)
