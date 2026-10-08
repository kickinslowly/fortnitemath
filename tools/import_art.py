"""Import the console's HUD textures (tools/art/*.png) and the course's flat wall colours into the open UEFN
project through UEFN MCP.

The runtime (fnm_ui.verse) references FNM_Art.T_fnm_check / T_fnm_cross (the verdict) and T_fnm_slate / T_fnm_tile
(the question slate and its answer tiles), so every map's UEFN project needs them once. MCP has no texture importer, but StaticMeshTools.import_file creates a Texture2D for each texture
an imported mesh's material references: so each PNG rides in on a one-quad OBJ whose material maps it, and
the helper mesh and material are deleted afterwards. A PNG dropped into Content/ is NOT auto-imported.
Wall colours come in the same way: an OBJ material's Kd colour becomes a Material (M_fnm_wall_<key>), which
tools/build_course.py paints on each hallway by its tier.

    python tools/make_verdict_art.py   # (re)draw the PNGs: check, cross
    python tools/make_hud_art.py       #                     slate, tile
    python tools/import_art.py         # idempotent: replaces existing T_fnm_* / M_fnm_* assets
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
# Hallway wall colour per difficulty tier (the course builder picks by tier) and the finish hallway.
WALL_COLOURS = {"tier1": (0.30, 0.75, 0.40), "tier2": (0.25, 0.50, 0.90), "tier3": (0.55, 0.35, 0.85),
                "tier4": (0.95, 0.50, 0.15), "tier5": (0.85, 0.18, 0.18), "finish": (1.0, 0.75, 0.10),
                "ice": (0.70, 0.90, 1.0),   # icy hallway floors (build_course.py ICE_STATIONS)
                # the boss arena's answer pad tiles, A..D in build_course.LETTER_COLOURS
                "pad_a": (1.0, 1.0, 1.0), "pad_b": (0.3, 0.55, 1.0), "pad_c": (0.2, 0.9, 0.3), "pad_d": (1.0, 0.55, 0.1)}


def mount():
    """The project's content mount (its plugin id), e.g. /c498eed2-..."""
    root = u.call("ValkyrieToolset.VerseToolset", "ListFiles", {"path": "", "bRecursive": False})
    return next(e["name"] for e in root["returnValue"] if e["type"] == "Directory" and "(" not in e["name"]).rstrip("/")


def quad_obj(t, name, mtl_body):
    """A one-quad OBJ whose only material is `name` (mtl_body: its Kd / map_Kd lines)."""
    (t / f"{name}.mtl").write_text(f"newmtl {name}\n{mtl_body}")
    (t / f"{name}.obj").write_text(f"mtllib {name}.mtl\nv 0 0 0\nv 100 0 0\nv 100 100 0\nv 0 100 0\n"
                                   "vt 0 0\nvt 1 0\nvt 1 1\nvt 0 1\nvn 0 0 1\n"
                                   f"usemtl {name}\nf 1/1/1 2/2/1 3/3/1 4/4/1\n")
    return t / f"{name}.obj"


def import_quad(folder, name, obj, textures):
    made = u.call("editor_toolset.toolsets.static_mesh.StaticMeshTools", "import_file",
                  {"folder_path": folder, "asset_name": f"SM_{name}", "source_file": str(obj),
                   "import_materials": True, "import_textures": textures})["returnValue"]
    return [m["refPath"].split(".")[0] for m in made]


def replace(path):
    if u.call(ASSETS, "exists", {"path": path})["returnValue"]:
        u.call(ASSETS, "delete", {"path": path})


def textures(folder, tmp):
    for png in sorted(ART.glob("fnm_*.png")):
        name = png.stem                      # fnm_check
        tex = f"{folder}/T_{name}"
        replace(tex)
        (tmp / f"{name}.png").write_bytes(png.read_bytes())
        made = import_quad(folder, name, quad_obj(tmp, name, f"Kd 1 1 1\nmap_Kd {name}.png\n"), True)
        listed = u.call(ASSETS, "find_assets", {"folder_path": folder, "recursive": True})["returnValue"]
        for path in (a.split(".")[0] for a in listed):
            if path.rsplit("/", 1)[-1].startswith(("T_", "M_")):
                continue
            cls = u.call(ASSETS, "get_asset_class", {"asset_path": path})["returnValue"]
            if cls == "Texture2D":
                u.call(ASSETS, "move", {"path": path, "new_path": tex})
            elif path in made or path.endswith("/" + name):
                u.call(ASSETS, "delete", {"path": path})   # helper mesh + material
        for k, v in UI_SETTINGS.items():
            u.call(OBJ, "set_properties", {"instance": {"refPath": f"{tex}.T_{name}"}, "values": json.dumps({k: v})})
        u.call(ASSETS, "save_assets", {"asset_paths": [tex]})
        print("texture", tex)


def materials(folder, tmp, only=None):
    for key, (r, g, b) in WALL_COLOURS.items():
        if only and key not in only:
            continue
        name, final = f"fnm_wall_{key}", f"{folder}/M_fnm_wall_{key}"
        replace(final)
        for path in import_quad(folder, name, quad_obj(tmp, name, f"Kd {r} {g} {b}\n"), False):
            if path.endswith("/SM_" + name):
                u.call(ASSETS, "delete", {"path": path})
        u.call(ASSETS, "move", {"path": f"{folder}/{name}", "new_path": final})
        u.call(ASSETS, "save_assets", {"asset_paths": [final]})
        print("material", final)


def main(only=None):
    """only: material keys to (re)import alone, e.g. ["ice"]; default imports every texture and material."""
    folder = mount() + "/FNM_Art"
    with tempfile.TemporaryDirectory() as tmp:
        if not only:
            textures(folder, Path(tmp))
        materials(folder, Path(tmp), only)
    print(u.call(ASSETS, "find_assets", {"folder_path": folder, "recursive": True})["returnValue"])


if __name__ == "__main__":
    main(sys.argv[1:] or None)   # python tools/import_art.py [key ...]
