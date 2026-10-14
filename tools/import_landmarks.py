"""Import the two landmark meshes (Meshy static meshes, bought 2026-10-13) into the UEFN project under FNM_LandmarkArt:

    FNM_LandmarkArt/Volcano/SM_fnm_volcano   art/volcano/raw/volcano.glb  (~20k triangles, 2K base colour, "Titan Peak")
    FNM_LandmarkArt/Trophy/SM_fnm_trophy     art/trophy/raw/trophy.glb    (~14k triangles, 2K base colour, the Titan Cup)

    python tools/import_landmarks.py              # import what is missing, fix settings, save, report
    python tools/import_landmarks.py --force      # delete and re-import (this EMPTIES every actor's reference to the mesh and
                                                  # its material: rerun tools/build_landmarks.py afterwards)
    python tools/import_landmarks.py --check      # read-only: which assets exist, triangles, bounds, texture sizes, emissive
    python tools/import_landmarks.py --glow [--power 4 --strength 4]   # rewire / retune the volcano's lava glow only

The FBX is the GLB re-exported by Blender (tools/glb_to_fbx.py, headless; made here when `art/<name>/raw/<name>_blender.fbx` is
missing or older than the GLB): Meshy's own FBX welds the texture's UV seams (tools/import_cannon.py, 2026-10-10). StaticMeshTools
takes FBX or OBJ only. Each mesh gets its own subfolder because both GLBs name their material `Material_0` and their texture
`Image_0`. The folder is not a Verse-style name (a content folder becomes a Verse module; uefn-mcp skill).

Settings (per the cannon's lessons): `lODBias` 0 on the base colour (the import's bias 1 drops the top mip; Meshy packs the
atlas as thousands of small islands, so the lost mip shows as blotches). Blotches in tools/capture.py frames are the editor
streaming mips for its main viewport, not this. Never Stream / NoMipmaps would hide them but fails session validation.

The volcano's lava glows at dusk (Hour19): `lava_glow` wires an emissive onto the imported Material (the MaterialTools toolset edits
the graph headlessly; ~5 minutes to get right): the texture's colour times its own red channel raised to a power, so rock browns fall
to nothing and the lava and crater rim keep their hue. Best effort: if the material graph refuses it, the mesh is left with its base
colour and the script says so.

Both meshes have their collision shapes removed (`no_collision`, on every run).

Assets are kept when present (re-importing nulls every reference to them: uefn-mcp skill, 2026-10-13); `--force` replaces them.
"""
import argparse
import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import uefn_mcp as u  # noqa: E402

ASSETS = "editor_toolset.toolsets.asset.AssetTools"
STATIC = "editor_toolset.toolsets.static_mesh.StaticMeshTools"
OBJ = "editor_toolset.toolsets.object.ObjectTools"
MAT = "editor_toolset.toolsets.material.MaterialTools"
TEXTURE_TOOLS = "editor_toolset.toolsets.texture.TextureTools"

ROOT = Path(__file__).resolve().parent.parent
BLENDER = Path(r"C:\Program Files\Blender Foundation\Blender 5.2\blender.exe")
ART = "FNM_LandmarkArt"
# name -> (subfolder, mesh asset name)
MESHES = {"volcano": ("Volcano", "SM_fnm_volcano"), "trophy": ("Trophy", "SM_fnm_trophy")}
# Full-size texture in play (the import's LOD bias 1 drops the top mip).
TEXTURE = {"lODBias": 0}
# The lava glow (volcano only). Emissive = BaseColor * BaseColor.R ^ GLOW_POWER * GLOW_STRENGTH: a brown rock texel (R 0.35 sRGB, ~0.1
# linear) falls to nothing at power 4 while the lava (R 1.0) keeps its own hue. Tuned by eye at Hour19 (see lava_glow).
GLOW_POWER = 4.0
GLOW_STRENGTH = 4.0
GLOW_MESH = "volcano"


def fbx(name):
    return ROOT / "art" / name / "raw" / f"{name}_blender.fbx"


def make_fbx(name):
    """Blender headless: art/<name>/raw/<name>.glb -> <name>_blender.fbx (textures embedded) when missing or stale."""
    src, dst = ROOT / "art" / name / "raw" / f"{name}.glb", fbx(name)
    if dst.exists() and dst.stat().st_mtime >= src.stat().st_mtime:
        return dst
    if not src.exists():
        sys.exit(f"{src} is missing")
    subprocess.run([str(BLENDER), "-b", "--factory-startup", "--python", str(ROOT / "tools" / "glb_to_fbx.py"), "--", str(src), str(dst)],
                   check=True, capture_output=True)
    print(f"  blender: {src.name} -> {dst.name}")
    return dst


def mount():
    m = "/" + u.call(ASSETS, "find_assets", {"folder_path": "", "name": "M_fnm_wall_bm_marble", "recursive": True})["returnValue"][0].split("/")[1]
    return m


def folder(name, project=None):
    return f"{project or mount()}/{ART}/{MESHES[name][0]}"


def mesh_path(project, name):
    """The mesh's asset path as an actor refers to it: /<mount>/FNM_LandmarkArt/<Sub>/<SM>.<SM>."""
    sub, sm = MESHES[name]
    return f"/{project.strip('/')}/{ART}/{sub}/{sm}.{sm}"


def assets(f):
    return u.call(ASSETS, "find_assets", {"folder_path": f, "name": "", "recursive": True})["returnValue"]


def get(obj, keys):
    return json.loads(u.call(OBJ, "get_properties", {"instance": {"refPath": obj}, "properties": keys})["returnValue"])


def glow_wired(material):
    """The expression feeding the material's emissive output (None when nothing does)."""
    got = u.call(MAT, "get_property_input", {"material": {"refPath": material}, "material_property": "MP_EmissiveColor"})["returnValue"]
    return got.get("expression")


def lava_glow(material, power=None, strength=None):
    """Wire the lava glow onto `material` (a Material path), or retune it: emissive = BaseColor * (BaseColor.R ^ power) * strength.
    The mask is the red channel raised to a power (rock browns fall to nothing, the orange lava and the crater rim stay), and
    the glow keeps the texture's own hue: an emissive of BaseColor ^ power alone pushed the lava to pure red, which the dusk
    haze turned hot pink (play frames 2026-10-13). Nodes: TextureSample.R -> Power -> Multiply(constB = strength) ->
    Multiply(B) with the texture's RGB on A -> MP_EmissiveColor, recompiled. Every connection is rewritten each call, so a
    second call only retunes. Verified 2026-10-13: the imported FBX material is one TextureSample on BaseColor."""
    power = GLOW_POWER if power is None else power
    strength = GLOW_STRENGTH if strength is None else strength
    ref = lambda p: {"refPath": p}  # noqa: E731
    M = ref(material)
    tex = u.call(MAT, "get_property_input", {"material": M, "material_property": "MP_BaseColor"})["returnValue"]["expression"]
    nodes = [e["refPath"] for e in u.call(MAT, "get_expressions", {"material_or_function": M})["returnValue"]]

    def node(kind, x, y, skip=()):
        have = [n for n in nodes if f":MaterialExpression{kind}_" in n and n not in skip]
        if have:
            return have[0]
        path = u.call(MAT, "add_expression", {"material_or_function": M, "expression_class": ref(f"/Script/Engine.MaterialExpression{kind}"),
                                              "x": x, "y": y})["returnValue"]["refPath"]
        nodes.append(path)
        return path

    pw = node("Power", -600, 300)
    scale = node("Multiply", -300, 300)
    tint = node("Multiply", 0, 300, skip=(scale,))
    u.call(OBJ, "set_properties", {"instance": ref(pw), "values": json.dumps({"constExponent": power})})
    u.call(OBJ, "set_properties", {"instance": ref(scale), "values": json.dumps({"constB": strength})})
    wire = lambda src, out, dst, pin: u.call(MAT, "connect_expressions", {"from_expression": src, "from_output_name": out,  # noqa: E731
                                                                           "to_expression": ref(dst), "to_input_name": pin})
    wire(tex, "R", pw, "Base")
    wire(ref(pw), "", scale, "A")
    wire(tex, "RGB", tint, "A")
    wire(ref(scale), "", tint, "B")
    u.call(MAT, "connect_to_output", {"expression": ref(tint), "output_name": "", "material_property": "MP_EmissiveColor"})
    u.call(MAT, "delete_unused_expressions", {"material": M})       # an earlier version's orphaned nodes
    u.call(MAT, "recompile", {"material_or_function": M})
    return power, strength


def report(name, project):
    sub, sm = MESHES[name]
    f = folder(name, project)
    mp = f"{f}/{sm}"
    mesh = {"refPath": f"{mp}.{sm}"}
    tris = u.call(STATIC, "get_triangle_count", {"mesh": mesh})["returnValue"]
    b = u.call(STATIC, "get_bounds", {"mesh": mesh})["returnValue"]
    size = [b["max"][k] - b["min"][k] for k in "xyz"]
    print(f"  {sm}: {tris} triangles, bounds x {b['min']['x']:.1f}..{b['max']['x']:.1f}  y {b['min']['y']:.1f}..{b['max']['y']:.1f}  "
          f"z {b['min']['z']:.1f}..{b['max']['z']:.1f}  (size {size[0]:.1f} x {size[1]:.1f} x {size[2]:.1f} cm)")
    for a in assets(f):
        print("   ", a)
    if name == GLOW_MESH:
        print("  emissive:", "wired" if glow_wired(f"{f}/Material_0.Material_0") else "none")
    for t in u.call(ASSETS, "find_assets", {"folder_path": f, "name": "Image_", "recursive": True})["returnValue"]:
        size = u.call(TEXTURE_TOOLS, "get_size", {"texture": {"refPath": t}})["returnValue"]
        print(f"  texture {t.split('/')[-1]}: {size}, {get(t, ['lODBias'])}")


def import_one(name, project, force):
    sub, sm = MESHES[name]
    f = folder(name, project)
    exists = u.call(ASSETS, "exists", {"path": f"{f}/{sm}"})["returnValue"]
    if exists and not force:
        print(f"{sm}: kept (exists); --force replaces it")
        return False
    if force:
        for a in assets(f):
            u.call(ASSETS, "delete", {"path": a.split(".")[0]})
    u.call(STATIC, "import_file", {"folder_path": f, "asset_name": sm, "source_file": str(make_fbx(name)),
                                   "import_materials": True, "import_textures": True})
    for t in u.call(ASSETS, "find_assets", {"folder_path": f, "name": "Image_", "recursive": True})["returnValue"]:
        for k, v in TEXTURE.items():     # one key per call
            u.call(OBJ, "set_properties", {"instance": {"refPath": t}, "values": json.dumps({k: v})})
    print(f"{sm}: imported into {f}")
    return True


def no_collision(name, project):
    """Strip the mesh asset's collision shapes (landmarks are scenery: the volcano is 2 km out, the trophy stands beside the walking
    line). Done on the ASSET, because a placed mesh actor's `collisionEnabled: NoCollision` set in the editor did not hold in play
    (uefn-mcp skill, 2026-10-08). Safe to repeat."""
    sm = MESHES[name][1]
    ok = u.call(STATIC, "remove_collisions", {"mesh": {"refPath": f"{folder(name, project)}/{sm}.{sm}"}})["returnValue"]
    print(f"{sm}: collision shapes removed" if ok else f"{sm}: remove_collisions answered {ok!r}")


def glow(name, project, retune=False):
    """The volcano's emissive (see the module docstring): applied on import and whenever it is missing; `retune` rewires it."""
    if name != GLOW_MESH:
        return
    material = f"{folder(name, project)}/Material_0.Material_0"
    if glow_wired(material) and not retune:
        print(f"{MESHES[name][1]}: emissive already wired")
        return
    try:
        power, strength = lava_glow(material)
        print(f"{MESHES[name][1]}: lava glow wired (emissive = base ^ {power} * {strength})")
    except Exception as e:  # best effort: the mesh stays usable with its base colour
        print(f"{MESHES[name][1]}: lava glow NOT wired ({e}); left with its base colour")


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--force", action="store_true", help="delete and re-import (empties every reference: rerun build_landmarks.py)")
    ap.add_argument("--check", action="store_true", help="read-only report")
    ap.add_argument("--glow", action="store_true", help="rewire / retune the volcano's lava glow only (GLOW_POWER, GLOW_STRENGTH), no import")
    ap.add_argument("--power", type=float, default=None, help="with --glow: the mask's exponent")
    ap.add_argument("--strength", type=float, default=None, help="with --glow: the emissive multiplier")
    args = ap.parse_args()
    project = mount()
    if args.glow:
        material = f"{folder(GLOW_MESH, project)}/Material_0.Material_0"
        print("lava glow:", lava_glow(material, args.power, args.strength))
        u.call(ASSETS, "save_assets", {"asset_paths": []})
        return
    if not args.check:
        for name in MESHES:
            import_one(name, project, args.force)
            no_collision(name, project)
            glow(name, project)
        u.call(ASSETS, "save_assets", {"asset_paths": []})
    for name in MESHES:
        report(name, project)


if __name__ == "__main__":
    main()
