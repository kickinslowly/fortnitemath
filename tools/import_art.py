"""Import the console's HUD textures (tools/art/*.png) into the open UEFN project through UEFN MCP.

The runtime (fnm_ui.verse) references FNM_Art.T_fnm_check / T_fnm_cross, so every map's UEFN project needs
them once. MCP has no texture importer, but StaticMeshTools.import_file creates a Texture2D for each texture
an imported mesh's material references: so each PNG rides in on a one-quad OBJ whose material maps it, and
the helper mesh and material are deleted afterwards. A PNG dropped into Content/ is NOT auto-imported.

    python tools/make_verdict_art.py   # (re)draw the PNGs
    python tools/import_art.py         # idempotent: replaces existing T_fnm_* assets
"""
import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import uefn_mcp as u  # noqa: E402

ART = Path(__file__).parent / "art"
ASSETS = "editor_toolset.toolsets.asset.AssetTools"
OBJ = "editor_toolset.toolsets.object.ObjectTools"
UI_SETTINGS = {"CompressionSettings": "TC_EditorIcon", "LODGroup": "TEXTUREGROUP_UI", "MipGenSettings": "TMGS_NoMipmaps"}


def mount():
    """The project's content mount (its plugin id), e.g. /c498eed2-..."""
    root = u.call("ValkyrieToolset.VerseToolset", "ListFiles", {"path": "", "bRecursive": False})
    return next(e["name"] for e in root["returnValue"] if e["type"] == "Directory" and "(" not in e["name"]).rstrip("/")


def main():
    folder = mount() + "/FNM_Art"
    with tempfile.TemporaryDirectory() as tmp:
        for png in sorted(ART.glob("fnm_*.png")):
            name = png.stem                      # fnm_check
            tex = f"{folder}/T_{name}"
            if u.call(ASSETS, "exists", {"path": tex})["returnValue"]:
                u.call(ASSETS, "delete", {"path": tex})
            t = Path(tmp)
            (t / f"{name}.png").write_bytes(png.read_bytes())
            (t / f"{name}.mtl").write_text(f"newmtl {name}\nKd 1 1 1\nmap_Kd {name}.png\n")
            (t / f"{name}.obj").write_text(f"mtllib {name}.mtl\nv 0 0 0\nv 100 0 0\nv 100 100 0\nv 0 100 0\n"
                                           "vt 0 0\nvt 1 0\nvt 1 1\nvt 0 1\nvn 0 0 1\n"
                                           f"usemtl {name}\nf 1/1/1 2/2/1 3/3/1 4/4/1\n")
            made = u.call("editor_toolset.toolsets.static_mesh.StaticMeshTools", "import_file",
                          {"folder_path": folder, "asset_name": f"SM_{name}", "source_file": str(t / f"{name}.obj"),
                           "import_materials": True, "import_textures": True})["returnValue"]
            made = [m["refPath"].split(".")[0] for m in made]
            listed = u.call(ASSETS, "find_assets", {"folder_path": folder, "recursive": True})["returnValue"]
            for path in (a.split(".")[0] for a in listed):
                if path.rsplit("/", 1)[-1].startswith("T_"):
                    continue
                cls = u.call(ASSETS, "get_asset_class", {"asset_path": path})["returnValue"]
                if cls == "Texture2D":
                    u.call(ASSETS, "move", {"path": path, "new_path": tex})
                elif path in made or path.endswith("/" + name):
                    u.call(ASSETS, "delete", {"path": path})   # helper mesh + material
            for k, v in UI_SETTINGS.items():
                u.call(OBJ, "set_properties", {"instance": {"refPath": f"{tex}.T_{name}"}, "values": json.dumps({k: v})})
            u.call(ASSETS, "save_assets", {"asset_paths": [tex]})
            print("imported", tex)
    print(u.call(ASSETS, "find_assets", {"folder_path": folder, "recursive": True})["returnValue"])


if __name__ == "__main__":
    main()
