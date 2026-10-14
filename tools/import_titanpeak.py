"""Import the Titan Peak art (bought 2026-10-13 evening; ids in art/titanpeak/meshy_tasks.json) into the open UEFN project
under FNM_TitanPeakArt, through UEFN MCP. Idempotent: an asset that exists is KEPT (never deleted or re-imported: deleting an
asset empties every reference to it, which is how the whole course lost its paint on 2026-10-13); materials and material
instances are updated IN PLACE (parameters re-applied, a missing graph built), so a rerun is always safe.

    python tools/import_titanpeak.py               # everything below, in this order: props, banners, arch, materials
    python tools/import_titanpeak.py --props       # the gate, the podium and the six set pieces (T2 places them)
    python tools/import_titanpeak.py --banners     # the seven tier-name banners as textured quads (T2 places them)
    python tools/import_titanpeak.py --arch        # the door arch mesh + its five tier skins (tools/build_arches.py places it)
    python tools/import_titanpeak.py --materials   # the eleven tiling surfaces (tools/build_course.py paint wears them)
    python tools/import_titanpeak.py --check       # read-only: what exists, triangles, texture sizes, MI parameters

What it makes (T2 and build_arches/build_course code against these names; <F> = /<mount>/FNM_TitanPeakArt):
- Props: <F>/<Sub>/SM_fnm_tp_<name> for gate, podium, jungle_pillar, river_boulders, ice_crystals, obsidian_spire, lava_vent,
  rune_stone (PROPS: one subfolder each, because every Meshy GLB names its material Material_0 and its texture Image_0).
  Route as tools/import_cannon.py: the GLB re-exported to FBX by headless Blender (tools/glb_to_fbx.py, cached next to the GLB
  as <name>_blender.fbx; Meshy's own FBX welds UV seams), StaticMeshTools.import_file with materials and textures, lODBias 0 on
  the base colour (the import's bias 1 drops the top mip in play). The meshes are centred on their bounding box (the GLBs are
  NOT origin-bottom): place by get_bounds, not by the pivot.
- Banners: <F>/Banners/SM_fnm_tp_banner_<key> (key = the PNG stem less "_raw": base_camp, waterfall_gorge, frost_ridge,
  obsidian_descent, magma_core, titans_forge, hall_of_champions). Each PNG is cropped to its alpha bbox (alpha < 16 zeroed, as
  tools/make_medal_art.py) and resampled to a power-of-two texture (a non-power-of-two texture cannot stream, and session
  validation wants streaming); the quad has the crop's true aspect, so the art is not stretched. Quad: BANNER_W cm wide, pivot at
  its bottom centre, standing in the XZ plane; which side reads is in BANNER_FACING (seen in an editor capture). Material:
  MI_fnm_tp_banner_<key> of M_fnm_tp_banner (masked by the PNG's alpha, a little emissive so it reads at dusk).
- Arch: <F>/Arch/SM_fnm_tp_arch (arch_t1.glb; the four retextures share its UVs and vertices exactly, checked by hash) and the
  skins M_fnm_tp_arch_t1..t5 (material instances of M_fnm_tp_uv, each tier's 2048 base colour as T_fnm_tp_arch_t<N>). The
  mesh's collision is removed (StaticMeshTools.remove_collisions): the arch must never catch a player.
- Surfaces: <F>/Surfaces/M_fnm_tp_<key> for SURFACES (t1_floor ... t5_wall, forge_floor): material instances of
  M_fnm_tp_surface, a world-scale tiling material (see surface_master): each face of a box takes the texture projected along the
  box's own axes at TILE[key] cm per repeat, so a scaled engine cube (every course piece) shows the stone at its real size on
  every face, at any yaw. Textures T_fnm_tp_<key>_base / _normal / _rough from the Mint zips unzipped under
  art/titanpeak/materials/<key>/ (1024 x 1024 each). TINT[key] darkens a texture that glares (a dark flat paint was needed
  for the floors, import_art WALL_COLOURS; a pale texture glares the same way).
"""
import argparse
import json
import math
import subprocess
import sys
import tempfile
from pathlib import Path

from PIL import Image

sys.path.insert(0, str(Path(__file__).parent))
import uefn_mcp as u  # noqa: E402

ASSETS = "editor_toolset.toolsets.asset.AssetTools"
STATIC = "editor_toolset.toolsets.static_mesh.StaticMeshTools"
OBJ = "editor_toolset.toolsets.object.ObjectTools"
MAT = "editor_toolset.toolsets.material.MaterialTools"
MI = "editor_toolset.toolsets.material_instance.MaterialInstanceTools"
TEX = "editor_toolset.toolsets.texture.TextureTools"

ROOT = Path(__file__).resolve().parent.parent
TP = ROOT / "art" / "titanpeak"
BLENDER = Path(r"C:\Program Files\Blender Foundation\Blender 5.2\blender.exe")
ART = "FNM_TitanPeakArt"

# mesh name -> (content subfolder, GLB under art/titanpeak, less ".glb")
PROPS = {"gate": ("Gate", "gate/raw/gate"), "podium": ("Podium", "podium/raw/podium"),
         "jungle_pillar": ("JunglePillar", "set/raw/jungle_pillar"), "river_boulders": ("RiverBoulders", "set/raw/river_boulders"),
         "ice_crystals": ("IceCrystals", "set/raw/ice_crystals"), "obsidian_spire": ("ObsidianSpire", "set/raw/obsidian_spire"),
         "lava_vent": ("LavaVent", "set/raw/lava_vent"), "rune_stone": ("RuneStone", "set/raw/rune_stone")}
ARCH = ("Arch", "arch/raw/arch_t1")
ARCH_TIERS = (1, 2, 3, 4, 5)
BANNERS = tuple(sorted(p.stem[:-len("_raw")] for p in (TP / "banners").glob("*_raw.png")))
BANNER_W = 400.0            # cm, every banner quad's width (T2 scales the actor)
BANNER_TEX_W = 1024         # texture width; the height is the power of two nearest the crop's aspect
BANNER_FACING = "-Y"        # the readable side at yaw 0 (a runner looking +Y reads it); seen in an editor capture
BANNER_EMISSIVE = 0.35      # emissive = base colour x this: reads at dusk (Hour19) without glowing
ALPHA_CUT = 16
SURFACES = ("t1_floor", "t1_wall", "t2_floor", "t2_wall", "t3_floor", "t3_wall", "t4_floor", "t4_wall", "t5_floor", "t5_wall",
            "forge_floor")
# cm per texture repeat in the world (brief: about 2-4 m). A wall is 600 cm tall.
TILE = {"t1_floor": 300.0, "t1_wall": 400.0, "t2_floor": 300.0, "t2_wall": 400.0, "t3_floor": 300.0, "t3_wall": 400.0,
        "t4_floor": 250.0, "t4_wall": 400.0, "t5_floor": 300.0, "t5_wall": 350.0, "forge_floor": 300.0}
# base colour multiplier (linear): < 1 darkens a texture that would glare at Hour19 or fight a door colour. Mean linear
# luminance of the base colours (2026-10-13): t1_floor 0.32, t1_wall 0.33, t2_floor 0.30, t2_wall 0.16, t3_floor 0.85 (snow),
# t3_wall 0.36, t4_floor 0.035, t4_wall 0.019, t5_floor 0.11 (lava p95 0.50), t5_wall 0.05, forge_floor 0.07; the flat floors
# that stopped the glare were Kd 0.03-0.10 (import_art WALL_COLOURS), so the pale floors are darkened most. t1_wall was 0.8
# until the first play session (Hour19, 2026-10-13): the sun-lit hallway wall at station 1 read near-white yellow.
TINT = {"t1_floor": (0.5, 0.5, 0.5), "t1_wall": (0.65, 0.65, 0.65), "t2_floor": (0.55, 0.55, 0.55), "t2_wall": (1.0, 1.0, 1.0),
        "t3_floor": (0.3, 0.3, 0.3), "t3_wall": (0.75, 0.75, 0.75), "t4_floor": (1.0, 1.0, 1.0), "t4_wall": (1.0, 1.0, 1.0),
        "t5_floor": (0.85, 0.85, 0.85), "t5_wall": (1.0, 1.0, 1.0), "forge_floor": (1.0, 1.0, 1.0)}
NORMAL_STRENGTH = 1.0       # 0 = flat (the normal maps ignored), 1 = full
# roughness = max(the map, this): the Mint roughness maps are glossy (t3_floor averages 0.03, t2_floor 0.22), which mirrors the
# low Hour19 sun off a floor
ROUGHNESS_MIN = 0.6


def ref(p):
    return {"refPath": p}


def obj_path(path):
    """/a/b/Name -> /a/b/Name.Name (an asset's object path)."""
    return path if "." in path.rsplit("/", 1)[-1] else f"{path}.{path.rsplit('/', 1)[-1]}"


def exists(path):
    return u.call(ASSETS, "exists", {"path": path.split(".")[0]})["returnValue"]


def setp(obj, values):
    """One key per set_properties call (a combined write has kept an old value: uefn-mcp skill)."""
    for k, v in values.items():
        u.call(OBJ, "set_properties", {"instance": ref(obj_path(obj)), "values": json.dumps({k: v})})


def getp(obj, keys):
    r = u.call(OBJ, "get_properties", {"instance": ref(obj_path(obj)), "properties": keys})["returnValue"]
    return json.loads(r) if isinstance(r, str) else r


def mount():
    root = u.call("ValkyrieToolset.VerseToolset", "ListFiles", {"path": "", "bRecursive": False})
    return next(e["name"] for e in root["returnValue"] if e["type"] == "Directory" and "(" not in e["name"]).rstrip("/")


def folder(sub=""):
    return f"{mount()}/{ART}" + (f"/{sub}" if sub else "")


def find(f, name=""):
    return u.call(ASSETS, "find_assets", {"folder_path": f, "name": name, "recursive": True})["returnValue"]


# ---------------------------------------------------------------- meshes (props and the arch)

def make_fbx(glb_rel):
    """Headless Blender: art/titanpeak/<glb_rel>.glb -> <glb_rel>_blender.fbx (textures embedded), when missing or stale."""
    src, dst = TP / f"{glb_rel}.glb", TP / f"{glb_rel}_blender.fbx"
    if not src.exists():
        sys.exit(f"{src} is missing")
    if not dst.exists() or dst.stat().st_mtime < src.stat().st_mtime:
        subprocess.run([str(BLENDER), "-b", "--factory-startup", "--python", str(ROOT / "tools" / "glb_to_fbx.py"), "--",
                        str(src), str(dst)], check=True, capture_output=True)
        print(f"  blender: {src.name} -> {dst.name}")
    return dst


def import_mesh(name, sub, glb_rel):
    """SM_fnm_tp_<name> in <F>/<sub> from the GLB; kept when it exists. Returns the mesh's object path."""
    f = folder(sub)
    sm = f"SM_fnm_tp_{name}"
    path = f"{f}/{sm}"
    if exists(path):
        print(f"{sm}: kept (exists)")
        return obj_path(path)
    u.call(STATIC, "import_file", {"folder_path": f, "asset_name": sm, "source_file": str(make_fbx(glb_rel)),
                                   "import_materials": True, "import_textures": True})
    for t in find(f, "Image_"):
        setp(t, {"lODBias": 0})
    u.call(ASSETS, "save_assets", {"asset_paths": []})
    print(f"{sm}: imported into {f}")
    return obj_path(path)


def props():
    for name, (sub, glb) in PROPS.items():
        import_mesh(name, sub, glb)


# ---------------------------------------------------------------- textures

# A colour texture's settings, set explicitly: the importer guesses a normal map from the pixels, and the purple frost arch skin
# (arch_t3) came in as TC_Normalmap / sRGB off and drew bright yellow (editor capture 2026-10-13).
COLOUR = {"compressionSettings": "TC_Default", "sRGB": True}


def import_texture(f, name, png, settings=None):
    """T_<...> from a PNG on disk (TextureTools.import_file), kept when it exists. lODBias 0 and `settings` (default COLOUR)
    are (re)applied every run, one key per call, only where they read back different (a write rebuilds the texture in place;
    references to it survive)."""
    path = f"{f}/{name}"
    if not exists(path):
        made = u.call(TEX, "import_file", {"folder_path": f, "asset_name": name, "source_file": str(png)})["returnValue"]
        if not made:
            sys.exit(f"texture import of {png} made nothing")
    want = {"lODBias": 0, **(COLOUR if settings is None else settings)}
    have = getp(path, list(want))
    for k, v in want.items():
        if have.get(k) != v:
            setp(path, {k: v})
    return obj_path(path)


# ---------------------------------------------------------------- material graphs

E = "/Script/Engine.MaterialExpression"


class Graph:
    """Small helper over MaterialTools: add nodes, set their properties, wire them."""

    def __init__(self, material):
        self.m = ref(material)
        self.x = -1600

    def node(self, cls, y=0, **props_):
        self.x += 60
        n = u.call(MAT, "add_expression", {"material_or_function": self.m, "expression_class": ref(E + cls),
                                           "x": self.x, "y": y})["returnValue"]["refPath"]
        for k, v in props_.items():   # MCP property names are the UPROPERTY names, first letter lower (ConstB -> constB)
            u.call(OBJ, "set_properties", {"instance": ref(n), "values": json.dumps({k[0].lower() + k[1:]: v})})
        return n

    def wire(self, src, dst, pin, out=""):
        u.call(MAT, "connect_expressions", {"from_expression": ref(src), "from_output_name": out, "to_expression": ref(dst),
                                            "to_input_name": pin})

    def out(self, src, prop, out=""):
        u.call(MAT, "connect_to_output", {"expression": ref(src), "output_name": out, "material_property": prop})

    def binop(self, cls, a, b, a_out="", b_out="", y=0):
        n = self.node(cls, y)
        self.wire(a, n, "A", a_out)
        self.wire(b, n, "B", b_out)
        return n

    def lerp(self, a, b, alpha, alpha_out="", y=0):
        n = self.node("LinearInterpolate", y)
        self.wire(a, n, "A")
        self.wire(b, n, "B")
        self.wire(alpha, n, "Alpha", alpha_out)
        return n

    def _mask(self, src, channels, y):
        n = self.node("ComponentMask", y, R="r" in channels, G="g" in channels, B="b" in channels, A="a" in channels)
        self.wire(src, n, "")
        return n


def new_material(f, name):
    """(object path, True when it was just created) for Material <f>/<name>."""
    path = f"{f}/{name}"
    if exists(path):
        return obj_path(path), False
    u.call(MAT, "create_material", {"folder_path": f, "asset_name": name})
    return obj_path(path), True


def has_graph(material):
    return bool(u.call(MAT, "get_expressions", {"material_or_function": ref(material)})["returnValue"])


def surface_master(f, defaults):
    """M_fnm_tp_surface: a box-projected (per-face planar) tiling material for scaled engine cubes.

    Engine-cube UVs run 0..1 across every face, so a texture stretches with the actor's scale. Here the UVs come from the WORLD
    position instead, measured along the actor's own axes (so a 45-degree connector wall tiles along its length too):
        ax, ay = normalize(local X / Y axis in world); px = dot(P, ax), py = dot(P, ay), pz = -P.z (image v runs down)
        n = |normalize(the pixel's normal in LOCAL space)|: exactly one axis is 1 on a box face
        uv = lerp(lerp((px, pz), (py, pz), n.x), (px, py), n.z) / TileSize
    The normal map is re-expressed in world space along the same axes (U = ax or ay, V = -Z or ay, N = the face normal), so
    the material's Normal is world space (bTangentSpaceNormal false). Parameters: BaseColor, Normal, Roughness (textures),
    TileSize (cm), Tint (colour multiplier), NormalStrength (0..1), RoughnessMin (roughness = max(map, this)).
    Assumes yaw-only actors (every course piece; lids are pitched but never painted).
    defaults: {"base" | "normal" | "rough": texture} for the texture parameters' own values (a Normal / LinearGrayscale sampler
    refuses to compile on the engine's default colour texture). A graph that exists is kept: its texture defaults are re-set
    and it is recompiled (which raises when it does not compile)."""
    m, made = new_material(f, "M_fnm_tp_surface")
    if not made and has_graph(m):
        for e in u.call(MAT, "get_expressions", {"material_or_function": ref(m)})["returnValue"]:
            if "TextureSampleParameter2D" in e["refPath"]:
                name = getp(e["refPath"], ["parameterName"])["parameterName"]
                key = {"BaseColor": "base", "Normal": "normal", "Roughness": "rough"}[name]
                u.call(OBJ, "set_properties", {"instance": ref(e["refPath"]), "values": json.dumps({"texture": ref(defaults[key])})})
        u.call(MAT, "recompile", {"material_or_function": ref(m)})
        return m
    g = Graph(m)
    wp = g.node("WorldPosition", 0)
    ex = g.node("Constant3Vector", 200, Constant={"r": 1, "g": 0, "b": 0, "a": 0})
    ey = g.node("Constant3Vector", 300, Constant={"r": 0, "g": 1, "b": 0, "a": 0})
    axes = []
    for e_, y in ((ex, 200), (ey, 300)):
        t = g.node("Transform", y, TransformSourceType="TRANSFORMSOURCE_Local", TransformType="TRANSFORM_World")
        g.wire(e_, t, "")
        nrm = g.node("Normalize", y)
        g.wire(t, nrm, "")
        axes.append(nrm)
    ax, ay = axes
    px = g.binop("DotProduct", wp, ax, y=0)
    py = g.binop("DotProduct", wp, ay, y=100)
    pz0 = g._mask(wp, "b", 200)
    pz = g.node("Multiply", 200, ConstB=-1.0)
    g.wire(pz0, pz, "A")
    vn = g.node("VertexNormalWS", 400)
    tl = g.node("Transform", 400, TransformSourceType="TRANSFORMSOURCE_World", TransformType="TRANSFORM_Local")
    g.wire(vn, tl, "")
    nl = g.node("Normalize", 400)
    g.wire(tl, nl, "")
    na = g.node("Abs", 400)
    g.wire(nl, na, "")
    nx = g._mask(na, "r", 450)
    nz = g._mask(na, "b", 500)
    xy = g.binop("AppendVector", px, py, y=0)
    yz = g.binop("AppendVector", py, pz, y=100)
    xz = g.binop("AppendVector", px, pz, y=200)
    side = g.lerp(xz, yz, nx, y=150)
    uvw = g.lerp(side, xy, nz, y=100)
    tile = g.node("ScalarParameter", 300, ParameterName="TileSize", DefaultValue=300.0)
    uv = g.binop("Divide", uvw, tile, y=100)
    base = g.node("TextureSampleParameter2D", -200, ParameterName="BaseColor", Texture=ref(defaults["base"]))
    g.wire(uv, base, "UVs")
    tint = g.node("VectorParameter", -300, ParameterName="Tint", DefaultValue={"r": 1, "g": 1, "b": 1, "a": 1})
    col = g.binop("Multiply", base, tint, a_out="RGB", y=-250)
    g.out(col, "MP_BaseColor")
    rough = g.node("TextureSampleParameter2D", 600, ParameterName="Roughness", Texture=ref(defaults["rough"]),
                   SamplerType="SAMPLERTYPE_LinearGrayscale")
    g.wire(uv, rough, "UVs")
    rmin = g.node("ScalarParameter", 700, ParameterName="RoughnessMin", DefaultValue=ROUGHNESS_MIN)
    rmax = g.binop("Max", rough, rmin, a_out="R", y=650)
    g.out(rmax, "MP_Roughness")
    nt = g.node("TextureSampleParameter2D", 800, ParameterName="Normal", Texture=ref(defaults["normal"]),
                SamplerType="SAMPLERTYPE_Normal")
    g.wire(uv, nt, "UVs")
    down = g.node("Constant3Vector", 900, Constant={"r": 0, "g": 0, "b": -1, "a": 0})
    u_in = g.lerp(ax, ay, nx, y=900)
    u_ax = g.lerp(u_in, ax, nz, y=900)
    v_ax = g.lerp(down, ay, nz, y=1000)
    tu = g.binop("Multiply", nt, u_ax, a_out="R", y=900)
    tv = g.binop("Multiply", nt, v_ax, a_out="G", y=1000)
    tn = g.binop("Multiply", nt, vn, a_out="B", y=1100)
    s1 = g.binop("Add", tu, tv, y=950)
    s2 = g.binop("Add", s1, tn, y=1000)
    strength = g.node("ScalarParameter", 1200, ParameterName="NormalStrength", DefaultValue=NORMAL_STRENGTH)
    mix = g.lerp(vn, s2, strength, y=1100)
    wn = g.node("Normalize", 1100)
    g.wire(mix, wn, "")
    g.out(wn, "MP_Normal")
    setp(m, {"bTangentSpaceNormal": False})
    u.call(MAT, "layout_expressions", {"material_or_function": ref(m)})
    u.call(MAT, "recompile", {"material_or_function": ref(m)})
    return m


def uv_master(f):
    """M_fnm_tp_uv: the base colour texture on the mesh's own UVs (the arch skins), roughness 0.85."""
    m, made = new_material(f, "M_fnm_tp_uv")
    if not made and has_graph(m):
        return m
    g = Graph(m)
    base = g.node("TextureSampleParameter2D", 0, ParameterName="BaseColor")
    g.out(base, "MP_BaseColor", "RGB")
    r = g.node("Constant", 200, R=0.85)
    g.out(r, "MP_Roughness")
    u.call(MAT, "recompile", {"material_or_function": ref(m)})
    return m


def banner_master(f):
    """M_fnm_tp_banner: masked by the texture's alpha, base colour + a little emissive (BannerGlow) so it reads at dusk."""
    m, made = new_material(f, "M_fnm_tp_banner")
    if not made and has_graph(m):
        return m
    setp(m, {"blendMode": "BLEND_Masked"})
    setp(m, {"twoSided": True})
    g = Graph(m)
    t = g.node("TextureSampleParameter2D", 0, ParameterName="Banner")
    g.out(t, "MP_BaseColor", "RGB")
    g.out(t, "MP_OpacityMask", "A")
    glow = g.node("ScalarParameter", 200, ParameterName="BannerGlow", DefaultValue=BANNER_EMISSIVE)
    e = g.binop("Multiply", t, glow, a_out="RGB", y=200)
    g.out(e, "MP_EmissiveColor")
    r = g.node("Constant", 300, R=0.9)
    g.out(r, "MP_Roughness")
    u.call(MAT, "recompile", {"material_or_function": ref(m)})
    return m


def instance(f, name, parent, textures=(), scalars=(), vectors=()):
    """Material instance <f>/<name> of `parent`, created when missing, parameters (re)applied in place every run."""
    path = f"{f}/{name}"
    if not exists(path):
        u.call(MI, "create", {"folder_path": f, "asset_name": name, "parent": ref(parent)})
    mi = ref(obj_path(path))
    for k, v in textures:
        u.call(MI, "set_texture_parameter", {"instance": mi, "name": k, "value": ref(v)})
    for k, v in scalars:
        u.call(MI, "set_scalar_parameter", {"instance": mi, "name": k, "value": v})
    for k, (r, g_, b) in vectors:
        u.call(MI, "set_vector_parameter", {"instance": mi, "name": k, "value": {"r": r, "g": g_, "b": b, "a": 1.0}})
    return obj_path(path)


# ---------------------------------------------------------------- banners

def banner_png(key, out_dir):
    """Crop art/titanpeak/banners/<key>_raw.png to its alpha bbox and resample to BANNER_TEX_W x a power of two. Returns
    (png path, true aspect width/height of the crop)."""
    im = Image.open(TP / "banners" / f"{key}_raw.png").convert("RGBA")
    r, g, b, a = im.split()
    a = a.point(lambda v: 0 if v < ALPHA_CUT else v)
    im = Image.merge("RGBA", (r, g, b, a))
    im = im.crop(a.getbbox())
    aspect = im.width / im.height
    h = 2 ** round(math.log2(BANNER_TEX_W / aspect))
    out = out_dir / f"T_fnm_tp_banner_{key}.png"
    im.resize((BANNER_TEX_W, h), Image.LANCZOS).save(out)
    return out, aspect


def banner_obj(tmp, key, aspect):
    """A one-quad OBJ BANNER_W wide and BANNER_W / aspect tall, bottom centre at the origin, no material file.
    UEFN's OBJ import maps OBJ (x, y, z) to (x, -y, z) with NO Y-up conversion (read back 2026-10-13: a quad drawn in OBJ x/y
    came in flat on the ground), so the quad is drawn in x (width) and z (height). u runs from +X to -X: a reader looking +Y
    has +X on their left, so the art reads left to right from -Y (BANNER_FACING); the material is two-sided."""
    w, h = BANNER_W / 2, BANNER_W / aspect
    p = tmp / f"SM_fnm_tp_banner_{key}.obj"
    p.write_text(f"v {w} 0 0\nv {-w} 0 0\nv {-w} 0 {h}\nv {w} 0 {h}\nvt 0 0\nvt 1 0\nvt 1 1\nvt 0 1\nvn 0 -1 0\n"
                 "f 1/1/1 2/2/1 3/3/1 4/4/1\n")
    return p


def banners():
    f = folder("Banners")
    master = banner_master(f)
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        for key in BANNERS:
            png, aspect = banner_png(key, tmp)
            tex = import_texture(f, f"T_fnm_tp_banner_{key}", png)
            mi = instance(f, f"MI_fnm_tp_banner_{key}", master, textures=[("Banner", tex)])
            sm = f"SM_fnm_tp_banner_{key}"
            if not exists(f"{f}/{sm}"):
                u.call(STATIC, "import_file", {"folder_path": f, "asset_name": sm, "source_file": str(banner_obj(tmp, key, aspect)),
                                               "import_materials": False, "import_textures": False})
                u.call(STATIC, "remove_collisions", {"mesh": ref(obj_path(f"{f}/{sm}"))})
            slots = u.call(STATIC, "get_material_slots", {"mesh": ref(obj_path(f"{f}/{sm}"))})["returnValue"]
            slot = slots[0] if isinstance(slots[0], str) else slots[0].get("slotName", slots[0].get("name"))
            u.call(STATIC, "set_material", {"mesh": ref(obj_path(f"{f}/{sm}")), "slot_name": slot, "material": ref(mi)})
            print(f"banner {key}: {sm} ({BANNER_W:.0f} x {BANNER_W / aspect:.0f} cm), {mi}")
    u.call(ASSETS, "save_assets", {"asset_paths": []})


# ---------------------------------------------------------------- the arch

def arch():
    mesh = import_mesh("arch", *ARCH)
    u.call(STATIC, "remove_collisions", {"mesh": ref(mesh)})
    f = folder("Arch")
    master = uv_master(f)
    for n in ARCH_TIERS:
        tex = import_texture(f, f"T_fnm_tp_arch_t{n}", TP / "arch" / "raw" / f"arch_t{n}_base_color.png")
        instance(f, f"M_fnm_tp_arch_t{n}", master, textures=[("BaseColor", tex)])
    u.call(ASSETS, "save_assets", {"asset_paths": []})
    print("arch: SM_fnm_tp_arch (no collision) + M_fnm_tp_arch_t1..t5")


# ---------------------------------------------------------------- surfaces

def maps(key):
    """{'base' | 'normal' | 'rough': png} for a Mint material unzipped under art/titanpeak/materials/<key>/."""
    d = TP / "materials" / key
    pick = lambda pat: next(iter(sorted(d.rglob(pat))), None)  # noqa: E731
    got = {"base": pick("*base-color*.png"), "normal": pick("*normal*.png"), "rough": pick("*roughness*.png")}
    missing = [k for k, v in got.items() if v is None]
    if missing:
        sys.exit(f"{key}: maps {missing} missing under {d} (unzip art/titanpeak/materials/{key}.zip there)")
    return got


def surface_mi_path(key, project=None):
    """The object path build_course paints with: /<mount>/FNM_TitanPeakArt/Surfaces/M_fnm_tp_<key>.M_fnm_tp_<key>."""
    return obj_path(f"{project or mount()}/{ART}/Surfaces/M_fnm_tp_{key}")


def surface_textures(f, key):
    """{"base" | "normal" | "rough": texture object path} for a surface key, importing what is missing."""
    mp = maps(key)
    return {"base": import_texture(f, f"T_fnm_tp_{key}_base", mp["base"]),
            "normal": import_texture(f, f"T_fnm_tp_{key}_normal", mp["normal"],
                                     {"compressionSettings": "TC_Normalmap", "sRGB": False}),
            "rough": import_texture(f, f"T_fnm_tp_{key}_rough", mp["rough"],
                                    {"compressionSettings": "TC_Grayscale", "sRGB": False})}


def surfaces(only=None):
    f = folder("Surfaces")
    master = surface_master(f, surface_textures(f, SURFACES[0]))
    for key in SURFACES:
        if only and key not in only:
            continue
        t = surface_textures(f, key)
        mi = instance(f, f"M_fnm_tp_{key}", master,
                      textures=[("BaseColor", t["base"]), ("Normal", t["normal"]), ("Roughness", t["rough"])],
                      scalars=[("TileSize", TILE[key]), ("NormalStrength", NORMAL_STRENGTH), ("RoughnessMin", ROUGHNESS_MIN)],
                      vectors=[("Tint", TINT[key])])
        print(f"surface {key}: {mi} tile {TILE[key]:.0f} cm tint {TINT[key]}")
    u.call(ASSETS, "save_assets", {"asset_paths": []})


# ---------------------------------------------------------------- report

def check():
    f = folder()
    for name, (sub, _) in {**PROPS, "arch": ARCH}.items():
        mp = obj_path(f"{f}/{sub}/SM_fnm_tp_{name}")
        if not exists(mp):
            print(f"MISSING SM_fnm_tp_{name}")
            continue
        tris = u.call(STATIC, "get_triangle_count", {"mesh": ref(mp)})["returnValue"]
        b = u.call(STATIC, "get_bounds", {"mesh": ref(mp)})["returnValue"]
        size = [round(b["max"][k] - b["min"][k]) for k in "xyz"]
        texs = [(t.split("/")[-1].split(".")[0], u.call(TEX, "get_size", {"texture": ref(t)})["returnValue"])
                for t in find(f"{f}/{sub}", "Image_")]
        print(f"SM_fnm_tp_{name}: {tris} tris, size {size} cm, min z {b['min']['z']:.0f}; textures {texs}")
    for key in BANNERS:
        mp = obj_path(f"{f}/Banners/SM_fnm_tp_banner_{key}")
        if not exists(mp):
            print(f"MISSING SM_fnm_tp_banner_{key}")
            continue
        b = u.call(STATIC, "get_bounds", {"mesh": ref(mp)})["returnValue"]
        t = obj_path(f"{f}/Banners/T_fnm_tp_banner_{key}")
        print(f"SM_fnm_tp_banner_{key}: bounds {b}; texture {u.call(TEX, 'get_size', {'texture': ref(t)})['returnValue']}")
    for n in ARCH_TIERS:
        p = obj_path(f"{f}/Arch/M_fnm_tp_arch_t{n}")
        print(f"M_fnm_tp_arch_t{n}: {'ok' if exists(p) else 'MISSING'}")
    for key in SURFACES:
        p = obj_path(f"{f}/Surfaces/M_fnm_tp_{key}")
        if not exists(p):
            print(f"MISSING M_fnm_tp_{key}")
            continue
        tile = u.call(MI, "get_scalar_parameter", {"instance": ref(p), "name": "TileSize"})["returnValue"]
        tex = u.call(MI, "get_texture_parameter", {"instance": ref(p), "name": "BaseColor"})["returnValue"]
        print(f"M_fnm_tp_{key}: TileSize {tile}, BaseColor {(tex or {}).get('refPath')}")


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    for g in ("props", "banners", "arch", "materials"):
        ap.add_argument(f"--{g}", action="store_true")
    ap.add_argument("--check", action="store_true", help="read-only report")
    ap.add_argument("--only", nargs="*", help="with --materials: just these surface keys")
    a = ap.parse_args()
    if a.check:
        check()
        return
    everything = not (a.props or a.banners or a.arch or a.materials)
    if everything or a.props:
        props()
    if everything or a.banners:
        banners()
    if everything or a.arch:
        arch()
    if everything or a.materials:
        surfaces(a.only)


if __name__ == "__main__":
    main()
