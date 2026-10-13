"""Import the console's HUD textures (tools/art/*.png) and the course's flat wall colours into the open UEFN
project through UEFN MCP.

The runtime (fnm_ui.verse) references FNM_Art.T_fnm_check / T_fnm_cross (the verdict), T_fnm_slate / T_fnm_tile
(the question slate and its answer tiles) and T_fnm_banner / T_fnm_nuke (boss mode), so every map's UEFN project needs them
once. MCP has no texture importer, but StaticMeshTools.import_file creates a Texture2D for each texture
an imported mesh's material references: so each PNG rides in on a one-quad OBJ whose material maps it, and
the helper mesh and material are deleted afterwards. A PNG dropped into Content/ is NOT auto-imported.
Door faces (tools/make_door_signs.py: door_face_a..d.png) come in the same way and keep their material: M_door_face_<x>
(texture T_door_face_<x>) is each door panel's material (build_course.door_dress).
Wall colours come in the same way: an OBJ material's Kd colour becomes a Material (M_fnm_wall_<key>), which
tools/build_course.py paints on each hallway by its tier.

    python tools/make_verdict_art.py   # (re)draw the PNGs: check, cross
    python tools/make_hud_art.py       #                     slate, tile
    python tools/make_door_signs.py    #                     door_face_a..d
    python tools/import_art.py         # imports what is missing; existing HUD textures, door faces and wall materials are KEPT
    python tools/import_art.py --force tile   # a redrawn HUD PNG: key = the file name less "fnm_" (HUD_KEYS: check cross slate
                                                         # tile banner nuke); replaces that texture only, no course repaint; then Verse
                                                         # BuildAll so the names resolve again
    python tools/import_art.py signs   # the door faces alone
    python tools/import_art.py floor_tier1 floor_tier2   # chosen material keys alone
    python tools/import_art.py --force signs ice         # REPLACE existing ones (see below), then repaint the course
                                                         # (explicit keys only; the course's own, see COURSE_KEYS)
    python tools/import_art.py --force --force-shared bm_stone   # a key the boss arenas also use: replaced, then exits 1
                                                         # until you rerun build_bossmode.py / build_colosseum.py

A material the level uses must never be deleted and re-imported at its own path: deleting an asset EMPTIES every
reference to it (the cube's overrideMaterials / the door's doorAnimatingMaterial read back null), and the actors do not
repaint themselves. That is how all 40 doors and the whole course's wall paint were lost (read back 2026-10-13: every
override null, get_referencers empty, while bm_stone, never replaced since, still had over 100 users; the run was most likely
the full one that brought T_fnm_nuke / T_fnm_banner in on 2026-10-09, an hour after the doors were painted). Reproduced
2026-10-13 on a throwaway material and cube: the override read back set before and null after the old materials().
So the default run skips an asset that exists (the T_fnm_* HUD textures too: they were deleted and re-imported on
every default run until 2026-10-13; nothing but Verse referenced them, so it did no harm, but it was the same pattern).
--force replaces it anyway
(a recoloured WALL_COLOURS entry or a redrawn door face) and then calls build_course.paint() and door_paint() so the
course is repainted at once. That repaint covers only COURSE_KEYS (the course's tiers, floors, lintel, ice, finish and the
door faces). `--force` therefore needs explicit keys (a bare `--force` would replace every material, boss mode's and the
colosseum's too: bm_stone has 100+ users, and nothing would repaint them), and refuses the others (bm_*, pad_*, steel,
glow: the boss battle arena and colosseum use them) unless `--force-shared` is added; then it replaces them, repaints the
course, and exits 1 saying which builders to rerun (tools/build_bossmode.py, tools/build_colosseum.py).
"""
import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import uefn_mcp as u  # noqa: E402

ART = Path(__file__).parent / "art"
# The HUD texture keys: a PNG's file name less "fnm_" (tools/art/fnm_tile.png -> "tile" -> FNM_Art/T_fnm_tile).
HUD_KEYS = tuple(p.stem[len("fnm_"):] for p in sorted(ART.glob("fnm_*.png")))
ASSETS = "editor_toolset.toolsets.asset.AssetTools"
OBJ = "editor_toolset.toolsets.object.ObjectTools"
UI_SETTINGS = {"CompressionSettings": "TC_EditorIcon", "LODGroup": "TEXTUREGROUP_UI", "MipGenSettings": "TMGS_NoMipmaps"}
# Hallway wall colour per difficulty tier (the course builder picks by tier) and the finish hallway.
WALL_COLOURS = {"tier1": (0.30, 0.75, 0.40), "tier2": (0.25, 0.50, 0.90), "tier3": (0.55, 0.35, 0.85),
                "tier4": (0.95, 0.50, 0.15), "tier5": (0.85, 0.18, 0.18), "finish": (1.0, 0.75, 0.10),
                "ice": (0.70, 0.90, 1.0),   # icy hallway floors (build_course.py ICE_STATIONS)
                # hallway floors, a dark mid-tone of each tier's wall colour (build_course.paint; G9 2026-10-13: the white
                # engine-cube floor glared by day). A flat Kd renders much lighter than its numbers (bm_stone needed 0.09).
                "floor_tier1": (0.03, 0.085, 0.04), "floor_tier2": (0.03, 0.055, 0.10), "floor_tier3": (0.06, 0.035, 0.10),
                "floor_tier4": (0.10, 0.055, 0.025), "floor_tier5": (0.10, 0.025, 0.025), "floor_finish": (0.10, 0.07, 0.02),
                # the header band over each station's doors: dark, so the 3D lintel letters (tools/build_door_marks.py: white,
                # blue, green, orange) read against it instead of against a pale tier-coloured wall (editor frames 2026-10-13)
                "lintel": (0.015, 0.015, 0.02),
                # the boss arena's answer pad tiles, A..D in build_course.LETTER_COLOURS
                "pad_a": (1.0, 1.0, 1.0), "pad_b": (0.3, 0.55, 1.0), "pad_c": (0.2, 0.9, 0.3), "pad_d": (1.0, 0.55, 0.1),
                # the old engine-shape laser cannons (tools/build_cannon.py, retired 2026-10-11); build_bossmode still checks them
                "steel": (0.16, 0.18, 0.22), "glow": (0.25, 0.95, 1.0),
                # the boss battle arena (tools/build_bossmode.py): dark walls, a lighter floor, gold perches
                "bm_wall": (0.12, 0.10, 0.14), "bm_floor": (0.22, 0.20, 0.24), "bm_perch": (1.0, 0.8, 0.1),
                # the colosseum pass (2026-10-09): arena sand, a blue-grey stone matching the Coliseum kit's brick, marble
                "bm_sand": (0.80, 0.65, 0.42), "bm_stone": (0.09, 0.09, 0.11), "bm_marble": (0.90, 0.88, 0.82)}


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


REPLACED = []   # (asset, actors that referenced it) for every in-use asset --force replaced; main() repaints when non-empty


def keep(path, force, record=True):
    """True when `path` exists and must be left alone (the default). Deleting a material the level uses empties every
    reference to it (module docstring), so an existing asset is kept unless force; a forced replacement is recorded in
    REPLACED for the repaint. record=False (a HUD texture: no course actor carries it, Verse re-resolves the name on the
    next build) replaces without queueing a repaint."""
    if not u.call(ASSETS, "exists", {"path": path})["returnValue"]:
        return False
    refs = [r for r in u.call(ASSETS, "get_referencers", {"asset_path": path})["returnValue"] if "/FNM_Art/" not in r]
    if force:
        if record:
            REPLACED.append((path, len(refs)))
        else:
            print(f"replacing {path} ({len(refs)} saved actors reference it); rebuild Verse afterwards")
        return False
    print(f"kept {path} ({len(refs)} saved actors use it; --force replaces it and empties their references)")
    return True


def textures(folder, tmp, only=None, force=False):
    """Import the HUD textures that are missing (an existing one is kept, like a material); only: HUD keys to handle
    alone; force replaces the named ones."""
    for png in sorted(ART.glob("fnm_*.png")):
        name = png.stem                      # fnm_check
        if only and name[len("fnm_"):] not in only:
            continue
        tex = f"{folder}/T_{name}"
        if keep(tex, force, record=False):
            continue
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


def signs(folder, tmp, force=False):
    for png in sorted(ART.glob("door_face_*.png")):
        name = png.stem                      # door_face_a
        tex, mat = f"{folder}/T_{name}", f"{folder}/M_{name}"
        if keep(mat, force):
            continue
        for path in (tex, mat, f"{folder}/{name}", f"{folder}/{name}_ncl1_1", f"{folder}/SM_{name}"):
            replace(path)
        (tmp / f"{name}.png").write_bytes(png.read_bytes())
        import_quad(folder, name, quad_obj(tmp, name, f"Kd 1 1 1\nmap_Kd {name}.png\n"), True)
        replace(f"{folder}/SM_{name}")       # the helper quad; the material and its texture stay
        u.call(ASSETS, "move", {"path": f"{folder}/{name}_ncl1_1", "new_path": tex})
        u.call(ASSETS, "move", {"path": f"{folder}/{name}", "new_path": mat})
        u.call(ASSETS, "save_assets", {"asset_paths": [tex, mat]})
        print("door face", mat)


def materials(folder, tmp, only=None, force=False):
    for key, (r, g, b) in WALL_COLOURS.items():
        if only and key not in only:
            continue
        name, final = f"fnm_wall_{key}", f"{folder}/M_fnm_wall_{key}"
        if keep(final, force):
            continue
        replace(final)
        for path in import_quad(folder, name, quad_obj(tmp, name, f"Kd {r} {g} {b}\n"), False):
            if path.endswith("/SM_" + name):
                u.call(ASSETS, "delete", {"path": path})
        u.call(ASSETS, "move", {"path": f"{folder}/{name}", "new_path": final})
        u.call(ASSETS, "save_assets", {"asset_paths": [final]})
        print("material", final)


# The keys build_course.paint() / door_paint() repaint (the course's own): what --force may replace on its own. Every other
# WALL_COLOURS key (bm_*, pad_*, steel, glow) has users the course repaint does not reach, so a new key defaults to refused.
COURSE_KEYS = frozenset({"signs", "ice", "finish", "lintel", "floor_finish"}
                        | {f"tier{n}" for n in range(1, 6)} | {f"floor_tier{n}" for n in range(1, 6)})
SHARED_BUILDERS = "tools/build_bossmode.py and tools/build_colosseum.py (the boss battle arena and colosseum use bm_*, pad_*, steel, glow)"


def check_force(only, force, shared_ok):
    """Refuse a --force that would empty references nothing repaints, before any UEFN call."""
    if not force:
        return
    if not only:
        sys.exit("--force needs explicit keys (e.g. --force signs ice floor_tier1): a bare --force would replace every "
                 "material, boss mode's and the colosseum's included, and only the course is repainted afterwards")
    shared = [k for k in only if k not in COURSE_KEYS and k not in HUD_KEYS]   # a HUD texture has no course actors to repaint
    if shared and not shared_ok:
        sys.exit(f"--force {' '.join(shared)}: the course repaint does not cover these, {SHARED_BUILDERS}; replacing "
                 f"them empties those references. Refused. Add --force-shared to replace them anyway, then rerun the builders.")


def parse_args(argv):
    """(keys or None, force, shared_ok) from the command line."""
    force, shared_ok = "--force" in argv, "--force-shared" in argv
    if shared_ok and not force:
        sys.exit("--force-shared needs --force")
    return [a for a in argv if a not in ("--force", "--force-shared")] or None, force, shared_ok


def main(only=None, force=False, shared_ok=False):
    """only: keys to (re)import alone, e.g. ["ice"] or a HUD texture key like "tile"; default imports, where missing, every
    HUD texture, material and door face (existing ones are kept). force (explicit keys only, check_force): replace existing
    door faces / materials and repaint the course afterwards (a HUD texture is replaced alone, no repaint); shared_ok: also
    replace keys the boss arenas use (then exits 1 until their builders are rerun)."""
    check_force(only, force, shared_ok)
    folder = mount() + "/FNM_Art"
    with tempfile.TemporaryDirectory() as tmp:
        if not only or any(k in HUD_KEYS for k in only):
            textures(folder, Path(tmp), only, force)
        if not only or "signs" in only:
            signs(folder, Path(tmp), force)
        if only != ["signs"]:
            materials(folder, Path(tmp), only, force)
    print(u.call(ASSETS, "find_assets", {"folder_path": folder, "recursive": True})["returnValue"])
    if REPLACED:
        import build_course as c             # the course's own paint: walls and floors by tier, then the door faces
        print("replaced assets (the references to them were emptied):", REPLACED)
        c.paint()
        c.door_paint()
        print("course repainted")
        shared = [p.rsplit("M_fnm_wall_", 1)[-1] for p, _ in REPLACED if p.rsplit("M_fnm_wall_", 1)[-1] not in COURSE_KEYS
                  and "M_fnm_wall_" in p]
        if shared:
            sys.exit(f"NOT DONE: {' '.join(shared)} replaced, their references emptied. Rerun {SHARED_BUILDERS} so they are painted again.")


if __name__ == "__main__":
    main(*parse_args(sys.argv[1:]))   # python tools/import_art.py [--force [--force-shared]] [key ...]
