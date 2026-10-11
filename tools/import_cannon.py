"""Import the boss arena's mega laser cannon (Meshy static mesh, art/cannon/raw/cannon.glb) into the UEFN project as
FNM_CannonArt/SM_fnm_megacannon (+ its material and base-colour texture). Idempotent: deletes the folder's assets first.
The FBX is art/cannon/raw/cannon.glb re-exported by Blender (tools/glb_to_fbx.py): Meshy's own FBX of this model welded the
texture's UV seams and the import showed blotches in place of the stripes and rivets (editor frames 2026-10-10).

    python tools/import_cannon.py

Then `python tools/build_bossmode.py --cannons` places it (BOSS_MODE 15d). The art: a Meshy concept image
(art/cannon/concept.png) and image to 3D, textured, 40k triangles; task ids in art/cannon/meshy_tasks.json.
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import uefn_mcp as u  # noqa: E402

ASSETS = "editor_toolset.toolsets.asset.AssetTools"
STATIC = "editor_toolset.toolsets.static_mesh.StaticMeshTools"
OBJ = "editor_toolset.toolsets.object.ObjectTools"
# Full-size texture in play: the import's LOD bias 1 drops the top mip. (Brown and teal blotches in editor captures are not
# this: the editor streams mips for its main viewport camera, not the capture's, so a freshly built texture shows its low
# mips in tools/capture.py frames; play streams by the player's camera. Never Stream / NoMipmaps would hide it in the
# editor but fail session validation, "Texture needs to support streaming".)
TEXTURE = {"lODBias": 0}
RAW = Path(__file__).resolve().parent.parent / "art" / "cannon" / "raw"
MESH = "SM_fnm_megacannon"


def folder():
    m = "/" + u.call(ASSETS, "find_assets", {"folder_path": "", "name": "M_fnm_wall_bm_marble", "recursive": True})["returnValue"][0].split("/")[1]
    return f"{m}/FNM_CannonArt"


def main():
    f = folder()
    for a in u.call(ASSETS, "find_assets", {"folder_path": f, "name": "", "recursive": True})["returnValue"]:
        u.call(ASSETS, "delete", {"path": a.split(".")[0]})
    u.call(STATIC, "import_file", {"folder_path": f, "asset_name": MESH, "source_file": str(RAW / "cannon.fbx"),
                                   "import_materials": True, "import_textures": True})
    for t in u.call(ASSETS, "find_assets", {"folder_path": f, "name": "Image_", "recursive": True})["returnValue"]:
        for k, v in TEXTURE.items():     # one key per call
            u.call(OBJ, "set_properties", {"instance": {"refPath": t}, "values": json.dumps({k: v})})
    u.call(ASSETS, "save_assets", {"asset_paths": []})
    for a in u.call(ASSETS, "find_assets", {"folder_path": f, "name": "", "recursive": True})["returnValue"]:
        print(" ", a)


if __name__ == "__main__":
    main()
