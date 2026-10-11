"""Import the boss monster (Meshy rig + animations, art/boss/raw/*.fbx) into the UEFN project as FNM_BossArt/SK_fnm_titan
and one AnimSequence per animation (A_fnm_titan_<name>). Idempotent: deletes FNM_BossArt first.

    python tools/import_boss.py

The folder is FNM_BossArt, not a Verse-style name: a content folder becomes a Verse module and `fnm_boss` collided with the
tag class (uefn-mcp skill). Each animation FBX carries the skin too, and each clip is imported WITH its own mesh and
skeleton into FNM_BossArt/Clip_<clip> (SK_fnm_titan_<clip> + A_fnm_titan_<clip>): bound to the skeleton of Meshy's separate
rig file instead, a clip whose hips turn or tip played on the wrong axis (the knockdown spun standing, the chest pound
tipped flat; play frames 2026-10-10), so the rig file is not used. dead_8 is the fall (plays once, BOSS_MODE 15b).
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import uefn_mcp as u  # noqa: E402

ASSETS = "editor_toolset.toolsets.asset.AssetTools"
SKEL = "editor_toolset.toolsets.skeletal_mesh.SkeletalMeshTools"
OBJ = "editor_toolset.toolsets.object.ObjectTools"
RAW = Path(__file__).resolve().parent.parent / "art" / "boss" / "raw"
# The clips the titan uses (build_bossmode TITAN_CLIPS). chestpound_88 and knockdown_187 were bought too and sit in
# art/boss/unused (not committed; Meshy task ids in art/boss/meshy_tasks.json): they misplay on the device (BOSS_MODE 15b).
# dead_8 (Meshy "Dead") is the fall at a level clear.
ANIMS = ["idle_0", "flail_172", "stomp_255", "dead_8"]


def mount():
    root = u.call("ValkyrieToolset.VerseToolset", "ListFiles", {"path": "", "bRecursive": False})
    return "/" + str(root).split("/")[1] if isinstance(root, str) else None


def main():
    m = "/" + u.call(ASSETS, "find_assets", {"folder_path": "", "name": "M_fnm_wall_bm_marble", "recursive": True})["returnValue"][0].split("/")[1]
    folder = f"{m}/FNM_BossArt"
    if u.call(ASSETS, "exists", {"path": folder})["returnValue"]:
        u.call(ASSETS, "delete", {"path": folder})
    for name in ANIMS:
        clip = name.split("_")[0]
        sub = f"{folder}/Clip_{clip}"
        mesh = f"SK_fnm_titan_{clip}"
        u.call(SKEL, "import_file", {"folder_path": sub, "asset_name": mesh, "source_file": str(RAW / f"{name}.fbx"),
                                     "import_materials": True, "import_textures": True, "import_animations": True})
        for a in u.call(ASSETS, "find_assets", {"folder_path": sub, "name": f"{mesh}_Anim", "recursive": False})["returnValue"]:
            u.call(ASSETS, "move", {"path": a.split(".")[0], "new_path": f"{sub}/A_fnm_titan_{clip}"})
    # Full-size textures in play: the import's LOD bias 1 drops the top mip (2048 -> 1024) on a 12 m monster.
    for t in u.call(ASSETS, "find_assets", {"folder_path": folder, "name": "baseColor", "recursive": True})["returnValue"]:
        u.call(OBJ, "set_properties", {"instance": {"refPath": t}, "values": json.dumps({"lODBias": 0})})
    u.call(ASSETS, "save_assets", {"asset_paths": []})
    for a in u.call(ASSETS, "find_assets", {"folder_path": folder, "name": "", "recursive": True})["returnValue"]:
        print(" ", a)

if __name__ == "__main__":
    main()
