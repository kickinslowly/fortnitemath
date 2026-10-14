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
  for the floors, import_art WALL_COLOURS; a pale texture glares the same way). Against the wallpaper look (Aaron, after
  playing): a turned, larger second sample blended in by a low-frequency mask (VARIATION), a colour jitter (JITTER), grime at
  a wall's foot and a weathered band at its top (GRIME_*, TOP_*), floors darker towards the walls (EDGE_*), and a per-actor
  offset so facing walls do not mirror (ACTOR_OFFSET): surface_knobs(key) is what each instance gets. A rerun re-applies
  them in place; an M_fnm_tp_surface built before a parameter existed is rebuilt in place (surface_master).
  A second, organic layer per tier (PATCHES: the Mint "_patch" materials under art/titanpeak/materials/<key>_patch/, textures
  T_fnm_tp_<key>_patch_base / _normal / _rough) is blended over the first in irregular patches by a noise mask
  (T_fnm_tp_patch_noise from art/titanpeak/materials/patch_noise.png; PATCH_* and NOISE_* knobs). Rerun --materials when a
  patch material that was still generating lands (it gets coverage 0 until then).
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
# Variation knobs per surface (M_fnm_tp_surface's parameters; surface_master explains each). Aaron after playing (2026-10-13):
# "some of it feels repetitive and tiled too monotonously like wallpaper".
# how strongly the macro map (light / dark patches) multiplies the base: factor = 1 + VariationBlend x (map - 1). The probe
# (station 1, 2026-10-13): 1.0 barely showed on the even flagstones, 3.0 made garish moss blobs, 2.0 read as moss and wear.
# The saturated textures (lava, river stone) get less, the near-black obsidian more.
VARIATION = {"t1_floor": 2.0, "t1_wall": 2.0, "t2_floor": 1.5, "t2_wall": 1.5, "t3_floor": 1.5, "t3_wall": 1.5,
             "t4_floor": 2.0, "t4_wall": 2.0, "t5_floor": 1.0, "t5_wall": 1.5, "forge_floor": 1.5}
VARIATION_SCALE = {k: 2.7 for k in SURFACES}       # the macro map is this many tiles across before it repeats
JITTER = {k: 0.12 for k in SURFACES}               # +- colour jitter over ~13 m
GRIME_STRENGTH = {k: 1.0 if k.endswith("_wall") else 0.0 for k in SURFACES}
GRIME_TINT = (0.45, 0.42, 0.36)                    # the bottom of a wall shades towards this (multiplied)
GRIME_HEIGHT = 80.0                                # cm
TOP_LIGHT = {k: 0.15 if k.endswith("_wall") else 0.0 for k in SURFACES}
TOP_HEIGHT = 35.0                                  # cm
EDGE_DARK = {k: 0.0 if k.endswith("_wall") else 0.3 for k in SURFACES}
EDGE_WIDTH = 140.0                                 # cm from the wall's foot
ACTOR_OFFSET = 1.0                                 # 1: each wall actor starts its tiling at its own offset
# The second, organic layer per tier (wave 5c; Mint materials bought 2026-10-13, ids in meshy_tasks.json "mint_patch_materials",
# unzipped under art/titanpeak/materials/<key>_patch/): t1 floor earth + leaves + grass tufts, t1 wall dense ivy; t2 floor wet
# sand + pebbles + algae, t2 wall teal moss + ferns; t3 floor snow drifts, t3 wall glacier ice; t4 floor ash + cinders, t4 wall
# pumice / scorched rock; t5 floor lava rubble, t5 wall scorched layered rock. The arena's forge floor has none. A key whose
# maps are not on disk yet gets coverage 0 (and the base's own maps in the patch slots) until a rerun.
PATCHES = {k: f"{k}_patch" for k in SURFACES if k != "forge_floor"}
PATCH_COVERAGE = {k: 0.40 if k.endswith("_floor") else 0.35 for k in SURFACES}   # share of a surface the patch covers (no bias)
PATCH_COVERAGE.update({"t1_wall": 0.40, "forge_floor": 0.0})
# Wave 5d (manager after pairs3_A.png): the walls were a clear win, the floors overshot: t1's earth read orange and
# camouflage-like against the cool flagstones, t2's wet sand purple and smeared. Floors now cover less and are tinted to sit in.
PATCH_COVERAGE.update({"t1_floor": 0.25, "t2_floor": 0.25, "t5_floor": 0.30})
PATCH_TILE = dict(TILE)                            # cm per patch texture repeat
PATCH_TILE["t2_floor"] = 200.0                     # 300 magnified the soft sand into a smear
# Mean linear luminance of the patch base colours (2026-10-13): t1 floor 0.13, t1 wall 0.27, t2 floor 0.08, t2 wall 0.07,
# t3 floor 0.84 (snow), t3 wall 0.44 (ice), t4 floor 0.03, t4 wall 0.03, t5 floor 0.03; tinted to sit near their tier's tinted base
PATCH_TINT = {k: (1.0, 1.0, 1.0) for k in SURFACES}
PATCH_TINT.update({"t1_wall": (0.8, 0.8, 0.8), "t3_floor": (0.3, 0.3, 0.3), "t3_wall": (0.6, 0.6, 0.6),
                   "t1_floor": (0.34, 0.56, 0.40),     # dark earth and green leaves, not orange (was 0.75 0.8 0.7; 0.42 0.62 0.45 still read red-brown)
                   "t2_floor": (0.95, 0.75, 0.5),      # toward neutral grey-brown sand, not purple-blue (was 1 1 1)
                   "t5_floor": (0.8, 0.7, 0.7)})       # rubble as ground, not a red stain (was 1 1 1)   # the station 1 probe: the raw earth read orange against the green flagstones
PATCH_EDGE = {k: 0.08 for k in SURFACES}          # soft-edge width in mask units (S runs 0..1)
PATCH_EDGE.update({"t1_floor": 0.05, "t2_floor": 0.05})   # crisper floor patches
PATCH_SCALE = 2400.0                               # cm per repeat of the first noise read
PATCH_FOOT_BIAS = {k: 0.25 if k.endswith("_wall") else 0.0 for k in SURFACES}   # more ivy / moss / ice at a wall's foot
PATCH_FOOT_HEIGHT = 250.0                          # cm over which that bias fades
PATCH_EDGE_BIAS = {k: 0.2 if k.endswith("_floor") else 0.0 for k in SURFACES}   # more leaves / drift / ash along the walls
PATCH_EDGE_BIAS.update({"forge_floor": 0.0, "t5_floor": 0.1})


def surface_knobs(key):
    """(scalars, vectors) every M_fnm_tp_<key> instance gets: the per-tier knobs."""
    scalars = [("TileSize", TILE[key]), ("NormalStrength", NORMAL_STRENGTH), ("RoughnessMin", ROUGHNESS_MIN),
               ("ActorOffset", ACTOR_OFFSET), ("VariationBlend", VARIATION[key]), ("VariationScale", VARIATION_SCALE[key]),
               ("Jitter", JITTER[key]), ("GrimeStrength", GRIME_STRENGTH[key]), ("GrimeHeight", GRIME_HEIGHT),
               ("TopLight", TOP_LIGHT[key]), ("TopHeight", TOP_HEIGHT), ("EdgeDark", EDGE_DARK[key]), ("EdgeWidth", EDGE_WIDTH),
               ("MacroBlur", MACRO_BLUR), ("PatchTileSize", PATCH_TILE[key]), ("PatchThreshold", patch_threshold(PATCH_COVERAGE[key])),
               ("PatchEdge", PATCH_EDGE[key]), ("PatchScale", PATCH_SCALE), ("PatchFootBias", PATCH_FOOT_BIAS[key]),
               ("PatchFootHeight", PATCH_FOOT_HEIGHT), ("PatchEdgeBias", PATCH_EDGE_BIAS[key])]
    return scalars, [("Tint", TINT[key]), ("GrimeTint", GRIME_TINT), ("PatchTint", PATCH_TINT[key])]


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


# The surface master's parameters (an existing M_fnm_tp_surface that lacks any of them is rebuilt in place: its expressions
# are replaced, the asset and every instance and actor reference to it are kept).
SURFACE_PARAMS = ("BaseColor", "Normal", "Roughness", "TileSize", "Tint", "NormalStrength", "RoughnessMin", "ActorOffset",
                  "VariationBlend", "VariationScale", "Jitter", "GrimeTint", "GrimeStrength", "GrimeHeight", "TopLight",
                  "TopHeight", "EdgeDark", "EdgeWidth",
                  "PatchBaseColor", "PatchNormal", "PatchRoughness", "PatchNoise", "PatchTileSize", "PatchTint",
                  "PatchThreshold", "PatchEdge", "PatchScale", "PatchFootBias", "PatchFootHeight", "PatchEdgeBias")
# texture parameter -> the defaults key surface_master takes
TEXTURE_PARAMS = {"BaseColor": "base", "Normal": "normal", "Roughness": "rough", "PatchBaseColor": "pbase",
                  "PatchNormal": "pnormal", "PatchRoughness": "prough", "PatchNoise": "noise"}
# The macro map (surface_graph): the base colour turned VARIATION_ANGLE, VariationScale times larger, read MACRO_BLUR mips
# down and divided by its average (MEAN_MIP: past the last mip, so 1 x 1), clamped to MACRO_CLAMP. MacroBlur 5 (32 texels a
# repeat) read better than 6 in the probe. First probe (2026-10-13, station 1): blending the SHARP turned sample in by a sine
# mask ghosted a second, larger paving pattern over the flagstones, so the second sample is only light and colour.
MACRO_BLUR = 5.0
MEAN_MIP = 12.0
MACRO_CLAMP = (0.5, 1.7)
# The colour jitter, a sine over the actor-aligned coordinates (px, py, pz) in cycles per cm (~13 m, a phase per channel so it
# shifts hue a little as well as brightness). Incommensurate with every TILE.
JITTER_K = (0.00031, 0.00057, 0.00041)
JITTER_PHASE = (0.0, 0.21, 0.43)
VARIATION_ANGLE = 37.0      # degrees the second sample is turned
VARIATION_SHIFT = (0.37, 0.71)
ACTOR_OFFSET_K = (0.00731, 0.00517)   # tiles of UV offset per cm of the actor's position (walls only), fractional part
EDGE_INSET = 40.0           # a station / connector floor slab runs this far under its walls (build_course.WALL_T)
EDGE_MIN_HALF = 300.0       # floors narrower than 2 x this (stair treads, hurdle tops) get no edge darkening
# The patch mask (wave 5c, manager: "a SECOND surface per tier, organic and gridless, blended over the first in large irregular
# patches like terrain blending"). A periodic band-limited noise (make_patch_noise: wavelengths NOISE_BAND texels of a
# NOISE_SIZE square, rank-normalised so its values are uniform on 0..1) read twice over the face coordinates, turned
# NOISE_ANGLES and NOISE_SCALES x PatchScale cm per repeat, weighted NOISE_WEIGHTS: S = w1 n1 + w2 n2. A pixel wears the patch
# where S + bias > PatchThreshold, over a soft edge PatchEdge wide. Two independent uniform reads make S trapezoid-distributed,
# so the threshold for a wanted coverage is analytic (patch_threshold). The noise does not depend on the tier's texture, so
# every tier gets the coverage its knob asks for (the brief's "from the blurred macro sample" was tried on paper: the macro
# ratio's spread differs tenfold between the even t4 basalt and the patchy t1 moss, so one threshold cannot fit both).
NOISE_SIZE = 512
NOISE_BAND = (60.0, 300.0)  # texels: with PatchScale 2400 cm, features of ~2.8-14 m; nothing finer, so mips barely shift it
# (offline mask previews on a 30 x 22 m floor, 2026-10-13: band 40-260 at 1600 cm read as busy camouflage, 80-300 at 3200 cm
# as two or three giant blobs; this one as irregular patches a few metres across)
NOISE_SEED = 20261013
NOISE_ANGLES = (23.0, -61.0)
NOISE_SCALES = (1.0, 0.41)
NOISE_WEIGHTS = (0.7, 0.3)
NOISE_SHIFT = (0.29, 0.63)


def make_patch_noise(path):
    """Write the patch-mask noise: NOISE_SIZE square, periodic (it tiles), band-limited to NOISE_BAND texels, rank-normalised
    to a uniform 0..255 histogram, 8-bit grey PNG. Deterministic (NOISE_SEED)."""
    import numpy as np
    rng = np.random.default_rng(NOISE_SEED)
    n = NOISE_SIZE
    f = np.fft.fftfreq(n)
    r = np.hypot(*np.meshgrid(f, f))
    band = (r >= 1 / NOISE_BAND[1]) & (r <= 1 / NOISE_BAND[0])
    spec = np.fft.fft2(rng.standard_normal((n, n))) * band / np.maximum(r, 1e-9)
    field = np.real(np.fft.ifft2(spec))
    ranks = field.ravel().argsort().argsort().reshape(n, n)
    img = (ranks * 256 // (n * n)).astype(np.uint8)
    Image.fromarray(img, "L").save(path)
    return path


def patch_threshold(coverage, weights=NOISE_WEIGHTS):
    """The PatchThreshold at which S = w1 U1 + w2 U2 (U uniform on 0..1, independent) exceeds it on `coverage` of a surface.
    coverage 0 -> a threshold above S's maximum (no patches)."""
    a, b = max(weights), min(weights)
    if coverage <= 0:
        return a + b + 1.0
    p = 1.0 - coverage                      # the CDF value wanted
    if p <= b / (2 * a):                    # F(s) = s^2 / (2ab) on [0, b]
        return math.sqrt(2 * a * b * p)
    if p <= 1 - b / (2 * a):                # F(s) = (2s - b) / (2a) on [b, a]
        return (2 * a * p + b) / 2
    return a + b - math.sqrt(2 * a * b * (1 - p))   # F(s) = 1 - (a + b - s)^2 / (2ab) on [a, a + b]


def surface_graph(m, defaults):
    """Build M_fnm_tp_surface's expressions into the (empty) Material m. See surface_master for what it computes."""
    g = Graph(m)

    def c2(xy, y):
        return g.node("Constant2Vector", y, R=xy[0], G=xy[1])

    def c3(v, y):
        return g.node("Constant3Vector", y, Constant={"r": v[0], "g": v[1], "b": v[2], "a": 0})

    def op1(cls, src, y, out="", **kw):
        n = g.node(cls, y, **kw)
        g.wire(src, n, "", out)
        return n

    def param(name, value, y):
        return g.node("ScalarParameter", y, ParameterName=name, DefaultValue=value)

    def turn(v, deg, y):
        a = math.radians(deg)
        return g.binop("AppendVector", g.binop("DotProduct", v, c2((math.cos(a), -math.sin(a)), y), y=y),
                       g.binop("DotProduct", v, c2((math.sin(a), math.cos(a)), y), y=y), y=y)

    def sample(name, uv_, y, key, **kw):
        n = g.node("TextureSampleParameter2D", y, ParameterName=name, Texture=ref(defaults[key]), **kw)
        g.wire(uv_, n, "UVs")
        return n

    # ---- geometry: actor-aligned world coordinates, the face, heights on a wall, distance to a floor's long sides
    wp = g.node("WorldPosition", 0)
    tx = op1("Transform", c3((1, 0, 0), 200), 200, TransformSourceType="TRANSFORMSOURCE_Local", TransformType="TRANSFORM_World")
    ty = op1("Transform", c3((0, 1, 0), 300), 300, TransformSourceType="TRANSFORMSOURCE_Local", TransformType="TRANSFORM_World")
    ax, ay = op1("Normalize", tx, 200), op1("Normalize", ty, 300)
    px, py = g.binop("DotProduct", wp, ax, y=0), g.binop("DotProduct", wp, ay, y=100)
    wz = g._mask(wp, "b", 200)
    pz = op1("Multiply", wz, 200, ConstB=-1.0)
    vn = g.node("VertexNormalWS", 400)
    tl = op1("Transform", vn, 400, TransformSourceType="TRANSFORMSOURCE_World", TransformType="TRANSFORM_Local")
    na = op1("Abs", op1("Normalize", tl, 400), 400)
    nx, nz = g._mask(na, "r", 450), g._mask(na, "b", 500)
    side_m = op1("OneMinus", nz, 500)                                  # 1 on a wall face, 0 on a top / bottom face
    xy = g.binop("AppendVector", px, py, y=0)
    uvw = g.lerp(g.lerp(g.binop("AppendVector", px, pz, y=200), g.binop("AppendVector", py, pz, y=100), nx, y=150), xy, nz, y=100)
    op = g.node("ObjectPositionWS", 600)
    off = op1("Frac", g.binop("Multiply", g._mask(op, "rg", 600), c2(ACTOR_OFFSET_K, 600), y=600), 600)
    offs = g.binop("Multiply", g.binop("Multiply", off, param("ActorOffset", 1.0, 650), y=620), side_m, y=640)
    uv = g.binop("Add", g.binop("Divide", uvw, param("TileSize", 300.0, 300), y=100), offs, y=100)
    hrel = g.binop("Subtract", wz, g._mask(op, "b", 800), y=800)
    half = op1("Multiply", g._mask(g.node("ObjectBounds", 820), "b", 820), 820, ConstB=0.5)
    above, below_top = g.binop("Add", hrel, half, y=800), g.binop("Subtract", half, hrel, y=840)
    rx = op1("Abs", g.binop("Subtract", px, g.binop("DotProduct", op, ax, y=1000), y=1000), 1000)
    ry = op1("Abs", g.binop("Subtract", py, g.binop("DotProduct", op, ay, y=1020), y=1020), 1020)
    hx = op1("Multiply", op1("Length", tx, 1040), 1040, ConstB=50.0)   # the engine cube is 100 cm: half its scaled size
    hy = op1("Multiply", op1("Length", ty, 1060), 1060, ConstB=50.0)
    pick = g.node("If", 1080)
    pins = u.call(MAT, "get_expression_input_names", {"expression": ref(pick)})["returnValue"]   # A, B, A > B, A == B, A < B
    pin = lambda sym: next(p for p in pins if sym in p.replace(" ", ""))  # noqa: E731
    g.wire(hx, pick, "A")
    g.wire(hy, pick, "B")
    ey_, ex_ = g.binop("Subtract", hy, ry, y=1090), g.binop("Subtract", hx, rx, y=1095)
    g.wire(ey_, pick, pin(">"))         # longer in x than in y: the short side is y
    g.wire(ey_, pick, pin("=="))
    g.wire(ex_, pick, pin("<"))
    gate = op1("Saturate", op1("Multiply", op1("Subtract", g.binop("Min", hx, hy, y=1100), 1100, ConstB=EDGE_MIN_HALF), 1100,
                               ConstB=0.01), 1100)
    edge = op1("OneMinus", op1("Saturate", g.binop("Divide", op1("Subtract", pick, 1110, ConstB=EDGE_INSET),
                                                     param("EdgeWidth", 140.0, 1120), y=1110), 1110), 1110)
    floor_edge = g.binop("Multiply", g.binop("Multiply", edge, nz, y=1125), gate, y=1130)   # 1 at a floor's wall foot, else 0

    # ---- the patch mask: two reads of the noise over the face, a bias towards a wall's foot and a floor's long sides
    ps = param("PatchScale", 1600.0, -900)
    n1 = sample("PatchNoise", g.binop("Divide", turn(uvw, NOISE_ANGLES[0], -900), ps, y=-900), -900, "noise",
                SamplerType="SAMPLERTYPE_LinearGrayscale")
    uv2 = g.binop("Add", g.binop("Divide", turn(uvw, NOISE_ANGLES[1], -950),
                                 op1("Multiply", ps, -950, ConstB=NOISE_SCALES[1]), y=-950), c2(NOISE_SHIFT, -950), y=-950)
    n2 = sample("PatchNoise", uv2, -980, "noise", SamplerType="SAMPLERTYPE_LinearGrayscale")
    s = g.binop("Add", op1("Multiply", n1, -920, out="R", ConstB=NOISE_WEIGHTS[0]),
                op1("Multiply", n2, -970, out="R", ConstB=NOISE_WEIGHTS[1]), y=-940)
    foot = op1("OneMinus", op1("Saturate", g.binop("Divide", above, param("PatchFootHeight", 250.0, -1000), y=-1000), -1000), -1000)
    bias = g.binop("Add", g.binop("Multiply", g.binop("Multiply", foot, side_m, y=-1010), param("PatchFootBias", 0.0, -1020), y=-1010),
                   g.binop("Multiply", floor_edge, param("PatchEdgeBias", 0.0, -1040), y=-1030), y=-1020)
    pmask = op1("Saturate", op1("Add", g.binop("Divide", g.binop("Subtract", g.binop("Add", s, bias, y=-1050),
                                                                 param("PatchThreshold", 3.0, -1060), y=-1050),
                                               param("PatchEdge", 0.06, -1070), y=-1050), -1050, ConstB=0.5), -1050)

    # ---- the two layers' colour
    base_a = sample("BaseColor", uv, -200, "base")
    # macro variation: the same texture, turned VARIATION_ANGLE, VariationScale times larger and blurred MacroBlur mips down,
    # divided by its own average colour (its last mip): a soft map of the texture's own light and dark patches, metres across
    uvb = g.binop("Add", g.binop("Divide", turn(uv, VARIATION_ANGLE, -400), param("VariationScale", 2.7, -470), y=-420),
                  c2(VARIATION_SHIFT, -480), y=-420)
    blur = sample("BaseColor", uvb, -500, "base", MipValueMode="TMVM_MipBias", ConstMipValue=MACRO_BLUR)
    mip_pin = [p_ for p_ in u.call(MAT, "get_expression_input_names", {"expression": ref(blur)})["returnValue"]
               if p_ not in ("UVs", "Apply View MipBias")]
    if mip_pin:                         # the bias as an instance knob when the node exposes its pin
        g.wire(param("MacroBlur", MACRO_BLUR, -520), blur, mip_pin[0])
    mean = sample("BaseColor", uvb, -560, "base", MipValueMode="TMVM_MipLevel", ConstMipValue=MEAN_MIP)
    ratio = g.node("Divide", -540)
    g.wire(blur, ratio, "A", "RGB")
    g.wire(op1("Max", mean, -560, out="RGB", ConstB=0.02), ratio, "B")
    macro = op1("Clamp", ratio, -540, MinDefault=MACRO_CLAMP[0], MaxDefault=MACRO_CLAMP[1])
    vfac = g.lerp(c3((1, 1, 1), -580), macro, param("VariationBlend", 0.0, -600), y=-580)
    tint = g.node("VectorParameter", -300, ParameterName="Tint", DefaultValue={"r": 1, "g": 1, "b": 1, "a": 1})
    col_a = g.binop("Multiply", g.binop("Multiply", base_a, vfac, a_out="RGB", y=-300), tint, y=-290)
    uvp = g.binop("Add", g.binop("Divide", uvw, param("PatchTileSize", 300.0, -1100), y=-1100), offs, y=-1100)
    base_p = sample("PatchBaseColor", uvp, -1150, "pbase")
    ptint = g.node("VectorParameter", -1160, ParameterName="PatchTint", DefaultValue={"r": 1, "g": 1, "b": 1, "a": 1})
    col_p = g.binop("Multiply", g.binop("Multiply", base_p, vfac, a_out="RGB", y=-1170), ptint, y=-1170)
    col = g.lerp(col_a, col_p, pmask, y=-280)
    # ---- over both: the colour jitter, a wall's grime foot and weathered top, a floor's darker edges
    p3 = g.binop("AppendVector", xy, pz, y=-600)
    s3 = op1("Sine", g.binop("Add", g.binop("DotProduct", p3, c3(JITTER_K, -700), y=-700), c3(JITTER_PHASE, -720), y=-710), -710)
    jf = op1("Add", g.binop("Multiply", s3, param("Jitter", 0.0, -740), y=-720), -720, ConstB=1.0)
    col = g.binop("Multiply", col, jf, y=-260)
    grime = op1("OneMinus", op1("Saturate", g.binop("Divide", above, param("GrimeHeight", 80.0, 860), y=860), 860), 860)
    gamt = g.binop("Multiply", g.binop("Multiply", grime, param("GrimeStrength", 0.0, 880), y=870), side_m, y=880)
    gtint = g.node("VectorParameter", 900, ParameterName="GrimeTint", DefaultValue={"r": 0.45, "g": 0.42, "b": 0.36, "a": 1})
    col = g.binop("Multiply", col, g.lerp(c3((1, 1, 1), 900), gtint, gamt, y=900), y=-240)
    top = op1("OneMinus", op1("Saturate", g.binop("Divide", below_top, param("TopHeight", 35.0, 940), y=940), 940), 940)
    tamt = g.binop("Multiply", g.binop("Multiply", top, param("TopLight", 0.0, 960), y=950), side_m, y=960)
    col = g.binop("Multiply", col, op1("Add", tamt, 970, ConstB=1.0), y=-220)
    eamt = g.binop("Multiply", floor_edge, param("EdgeDark", 0.0, 1130), y=1135)
    col = g.binop("Multiply", col, op1("OneMinus", eamt, 1140), y=-200)
    g.out(col, "MP_BaseColor")
    # ---- roughness and the world-space normal, each a blend of the two layers
    rmin = param("RoughnessMin", ROUGHNESS_MIN, 700)
    r_a = g.binop("Max", sample("Roughness", uv, 600, "rough", SamplerType="SAMPLERTYPE_LinearGrayscale"), rmin, a_out="R", y=650)
    r_p = g.binop("Max", sample("PatchRoughness", uvp, 680, "prough", SamplerType="SAMPLERTYPE_LinearGrayscale"), rmin,
                  a_out="R", y=690)
    g.out(g.lerp(r_a, r_p, pmask, y=670), "MP_Roughness")
    nt_a = sample("Normal", uv, 800, "normal", SamplerType="SAMPLERTYPE_Normal")
    nt_p = sample("PatchNormal", uvp, 850, "pnormal", SamplerType="SAMPLERTYPE_Normal")
    nt = g.node("LinearInterpolate", 860)
    g.wire(nt_a, nt, "A", "RGB")
    g.wire(nt_p, nt, "B", "RGB")
    g.wire(pmask, nt, "Alpha")
    u_ax = g.lerp(g.lerp(ax, ay, nx, y=900), ax, nz, y=900)
    v_ax = g.lerp(c3((0, 0, -1), 1000), ay, nz, y=1000)
    tn = g.binop("Add", g.binop("Add", g.binop("Multiply", g._mask(nt, "r", 900), u_ax, y=900),
                                g.binop("Multiply", g._mask(nt, "g", 1000), v_ax, y=1000), y=950),
                 g.binop("Multiply", g._mask(nt, "b", 1100), vn, y=1100), y=1000)
    g.out(op1("Normalize", g.lerp(vn, tn, param("NormalStrength", NORMAL_STRENGTH, 1200), y=1100), 1100), "MP_Normal")
    setp(m, {"bTangentSpaceNormal": False})
    u.call(MAT, "layout_expressions", {"material_or_function": ref(m)})


def surface_params(m):
    return {p["name"] for p in u.call(MI, "list_parameters", {"material": ref(m)})["returnValue"]}


def surface_master(f, defaults, name="M_fnm_tp_surface", rebuild=False):
    """M_fnm_tp_surface: a box-projected (per-face planar) tiling material for scaled engine cubes, with variation so a long
    wall or a hallway floor does not read as wallpaper.

    Projection. Engine-cube UVs run 0..1 across every face, so a texture stretches with the actor's scale. Here the UVs come
    from the WORLD position measured along the actor's own axes (so a 45-degree connector wall tiles along its length too):
        ax, ay = normalize(local X / Y axis in world); px = dot(P, ax), py = dot(P, ay), pz = -P.z (image v runs down)
        n = |normalize(the pixel's normal in LOCAL space)|: exactly one axis is 1 on a box face
        uv = lerp(lerp((px, pz), (py, pz), n.x), (px, py), n.z) / TileSize  (+ a per-actor offset on wall faces, ActorOffset)
    Variation (G9 wave 5b, Aaron: "tiled too monotonously like wallpaper"):
    - a macro map: the same texture turned VARIATION_ANGLE, VariationScale times larger, MACRO_BLUR mips blurred and divided
      by its own average colour, multiplies the base (VariationBlend): the texture's own light and dark patches, metres
      across, never lined up with the tile; the stones keep their detail;
    - a colour jitter of +-Jitter from a third sine (~13 m, a phase per channel);
    - wall faces: the bottom GrimeHeight cm shade towards GrimeTint (GrimeStrength), the top TopHeight cm lighten (TopLight),
      measured from the actor's bounds (ObjectBounds), so a wall reads as built, not a flat sheet;
    - floor tops: darker by up to EdgeDark within EdgeWidth cm of the walls, along the floor's short side only (its ends join
      the next floor piece), past the EDGE_INSET the slab runs under the walls; floors narrower than 2 x EDGE_MIN_HALF skip it;
    - a second, organic layer (wave 5c: ivy, moss, leaves, drift snow, ash, rubble: PatchBaseColor / PatchNormal /
      PatchRoughness at PatchTileSize, tinted PatchTint) over the first in irregular patches a few metres across: the patch
      mask (see NOISE_*) is noise read twice over the face at PatchScale, plus PatchFootBias towards a wall's foot (over
      PatchFootHeight cm) and PatchEdgeBias near a floor's long sides, thresholded at PatchThreshold with a PatchEdge soft edge.
      Colour, roughness and the tangent normal blend by the mask before the normal is turned to world space.
    The normal map is re-expressed in world space along the same axes (U = ax or ay, V = -Z or ay, N = the face normal), so the
    material's Normal is world space (bTangentSpaceNormal false); roughness = max(map, RoughnessMin). Cost (get_statistics, the
    report): 10 texture fetches over 7 samplers. Assumes yaw-only actors (every course piece; lids are pitched but never painted).
    defaults: {TEXTURE_PARAMS value: texture} for the texture parameters' own values (a Normal / LinearGrayscale sampler
    refuses to compile on the engine's default colour texture). A material that already has every SURFACE_PARAMS is kept (its
    texture defaults re-set); one that lacks any is rebuilt IN PLACE (expressions replaced; the asset, its instances and every
    actor's reference to it survive); rebuild=True (--rebuild-surface) rebuilds it the same way after a graph change. Then it is
    recompiled, which raises when it does not compile."""
    m, made = new_material(f, name)
    if not rebuild and not made and has_graph(m) and set(SURFACE_PARAMS) <= surface_params(m):
        for e in u.call(MAT, "get_expressions", {"material_or_function": ref(m)})["returnValue"]:
            if "TextureSampleParameter2D" in e["refPath"]:
                key = TEXTURE_PARAMS[getp(e["refPath"], ["parameterName"])["parameterName"]]
                u.call(OBJ, "set_properties", {"instance": ref(e["refPath"]), "values": json.dumps({"texture": ref(defaults[key])})})
    else:
        for e in u.call(MAT, "get_expressions", {"material_or_function": ref(m)})["returnValue"]:
            u.call(MAT, "delete_expression", {"material_or_function": ref(m), "expression": ref(e["refPath"])})
        surface_graph(m, defaults)
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


def patch_ready(key):
    """True when the key's patch maps are on disk (a Mint material still generating is not)."""
    d = TP / "materials" / PATCHES.get(key, "-")
    return key in PATCHES and d.is_dir() and all(any(d.rglob(pat)) for pat in ("*base-color*.png", "*normal*.png", "*roughness*.png"))


NOISE_PNG = TP / "materials" / "patch_noise.png"


def noise_texture(f):
    """T_fnm_tp_patch_noise: the patch-mask noise (make_patch_noise, written when missing), linear grey."""
    if not NOISE_PNG.exists():
        make_patch_noise(NOISE_PNG)
    return import_texture(f, "T_fnm_tp_patch_noise", NOISE_PNG, {"compressionSettings": "TC_Grayscale", "sRGB": False})


def layer_textures(f, key):
    """{base, normal, rough, pbase, pnormal, prough, noise} for surface `key`; a key with no patch yet gets its own maps in
    the patch slots (and coverage 0 from surface_knobs)."""
    t = surface_textures(f, key)
    pt = surface_textures(f, PATCHES[key]) if patch_ready(key) else t
    return {**t, "pbase": pt["base"], "pnormal": pt["normal"], "prough": pt["rough"], "noise": noise_texture(f)}


def surface_textures(f, key):
    """{"base" | "normal" | "rough": texture object path} for a surface key, importing what is missing."""
    mp = maps(key)
    return {"base": import_texture(f, f"T_fnm_tp_{key}_base", mp["base"]),
            "normal": import_texture(f, f"T_fnm_tp_{key}_normal", mp["normal"],
                                     {"compressionSettings": "TC_Normalmap", "sRGB": False}),
            "rough": import_texture(f, f"T_fnm_tp_{key}_rough", mp["rough"],
                                    {"compressionSettings": "TC_Grayscale", "sRGB": False})}


def surfaces(only=None, rebuild=False):
    f = folder("Surfaces")
    master = surface_master(f, layer_textures(f, SURFACES[0]), rebuild=rebuild)
    have = surface_params(master)           # MacroBlur exists only where the sample node exposes its mip pin
    for key in SURFACES:
        if only and key not in only:
            continue
        t = layer_textures(f, key)
        scalars, vectors = surface_knobs(key)
        if not patch_ready(key):
            scalars = [(k, patch_threshold(0.0) if k == "PatchThreshold" else v) for k, v in scalars]
            if key in PATCHES:
                print(f"surface {key}: no patch maps yet under art/titanpeak/materials/{PATCHES[key]}/ (coverage 0 until a rerun)")
        scalars = [(k, v) for k, v in scalars if k in have]
        mi = instance(f, f"M_fnm_tp_{key}", master,
                      textures=[(name, t[k]) for name, k in TEXTURE_PARAMS.items()], scalars=scalars, vectors=vectors)
        print(f"surface {key}: {mi} " + ", ".join(f"{k} {v:g}" for k, v in scalars[:1] + scalars[4:]) + f", tint {TINT[key]}")
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
    ap.add_argument("--rebuild-surface", action="store_true", help="with --materials: rebuild M_fnm_tp_surface's graph in place")
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
        surfaces(a.only, a.rebuild_surface)


if __name__ == "__main__":
    main()
