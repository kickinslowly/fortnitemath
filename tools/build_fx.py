"""Build the boss battle's Niagara effects in the open UEFN project through UEFN MCP (Niagara toolsets).

NS_fnm_laser is one mega laser shot: Verse SpawnParticleSystem(Asset, Position, Rotation) fires it at a cannon muzzle,
rotated so the system's local +X points at the target. Verse cannot set user parameters, so the shot is baked: every
emitter simulates in local space and the beam runs from local (0, 0, 0) to (LENGTH, 0, 0), the muzzle-to-boss distance.
A wide soft cyan glow, a thick white-hot core, two jagged lightning strands crackling around it, a flash and sparks at
the muzzle and at the hit point. It appears at once, holds 0.5 s, is gone by 0.8 s, and the system runs Once, so the
spawned instance dies on its own. NS_fnm_impact is the electrical explosion at the target: flash, lingering glow, a
shock ring ~5 m across, sparks under gravity and four short arcs, 1.6 s, Once.

Everything is engine content (/Niagara emitter templates, modules and DefaultSpriteMaterial): session validation
rejects /Game references and the /CRD_ plugin folders are not writable. DefaultSpriteMaterial is a round radial
gradient; on a ribbon its middle column (UV0 U fixed at 0.5) gives a soft tube cross-section, so no custom material.
UEFN refuses custom HLSL expressions on module inputs (bSupportsExpressions false), so shapes over time are curve data
interfaces and the crackle is the JitterPosition module on a beam of few points with ribbon tessellation off.

FNM_FX is also the Verse module the runtime reads the assets from (FNM_FX.NS_fnm_laser), so the folder name stays.

The editor world does not tick particles while UEFN sits in the background, so a placed system shows nothing in a
viewport capture. --preview builds looping copies (NS_fnm_*_preview) with a warm-up, which a freshly placed actor
renders at that age without ticking; place one, capture, and delete it with --clean-preview.

Idempotent: each run deletes and recreates the systems from scratch.

    python tools/build_fx.py                    # build NS_fnm_laser and NS_fnm_impact, save, report
    python tools/build_fx.py --check            # compile state, stack issues and dependencies only
    python tools/build_fx.py --preview 0.3      # looping copies warmed up 0.3 s, for viewport captures
    python tools/build_fx.py --clean-preview    # delete the preview copies
"""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import uefn_mcp as u  # noqa: E402

NS = "NiagaraToolsets.NiagaraToolset_System"
INFO = "NiagaraToolsets.NiagaraToolset_Info"
ASSETS = "editor_toolset.toolsets.asset.AssetTools"
MOUNT = "/c498eed2-96c5-4757-91a1-edb374b16d67"
FOLDER = f"{MOUNT}/FNM_FX"
TEMPLATES = "/Niagara/DefaultAssets/Templates/Emitters"
EMPTY_SYSTEM = "/Niagara/DefaultAssets/DefaultSystem.DefaultSystem"

ES, EU, PS, PU, SU = "EmitterSpawnScript", "EmitterUpdateScript", "ParticleSpawnScript", "ParticleUpdateScript", "SystemUpdateScript"
STATE_ENUM = "/Niagara/Enums/ENiagara_EmitterStateOptions.ENiagara_EmitterStateOptions"


def ref(p):
    return {"refPath": p}


def n(tool, args, timeout=180):
    return u.call(NS, tool, args, timeout=timeout)


class Sys:
    def __init__(self, name):
        self.name = name
        self.path = f"{FOLDER}/{name}.{name}"

    def item(self, emitter="", script="", module="", renderer=-1, inputs=None):
        return {"system": ref(self.path), "emitterName": emitter, "scriptName": script, "moduleName": module,
                "rendererIndex": renderer, "inputNameStack": inputs or []}

    def set(self, emitter, script, module, name, value):
        struct, val = value
        names = name if isinstance(name, list) else [name]
        return n("SetStackInputData", {"stackInputRef": self.item(emitter, script, module, inputs=names),
                                       "inputData": {"struct": ref(struct), "value": val}})


# --- value builders: (struct path, value dict) -------------------------------------------------------------------
def F(x):
    return "/Script/Niagara.NiagaraFloat", {"value": float(x)}


def B(x):
    return "/Script/Niagara.NiagaraBool", {"value": -1 if x else 0}


def I(x):
    return "/Script/Niagara.NiagaraInt32", {"value": int(x)}


def V3(x, y, z):
    return "/Script/CoreUObject.Vector3f", {"x": x, "y": y, "z": z}


def V2(x, y):
    return "/Script/CoreUObject.Vector2f", {"x": x, "y": y}


def COL(r, g, b, a=1.0):
    return "/Script/CoreUObject.LinearColor", {"r": r, "g": g, "b": b, "a": a}


def E(enum, name, display):
    return "/Script/NiagaraEditor.NiagaraExt_StackInputData_Enum", {"enum": ref(enum), "enumName": name, "displayName": display}


def DI(asset):
    return "/Script/NiagaraEditor.NiagaraExt_StackInputData_DynamicInput", {"dynamicInputAsset": ref(asset)}


ONCE = E(STATE_ENUM, "ENiagara_EmitterStateOptions::NewEnumerator1", "Once")
INFINITE = E(STATE_ENUM, "ENiagara_EmitterStateOptions::NewEnumerator0", "Infinite")


def curve(keys):
    """A FloatCurve data-interface value, linear between (time, value) keys."""
    k = [{"interpMode": "RCIM_Linear", "tangentMode": "RCTM_Auto", "tangentWeightMode": "RCTWM_WeightedNone",
          "time": t, "value": v, "arriveTangent": 0, "arriveTangentWeight": 0, "leaveTangent": 0,
          "leaveTangentWeight": 0} for t, v in keys]
    return ("/Script/NiagaraEditor.NiagaraExt_StackInputData_DataInterface",
            {"propertyValues": json.dumps({"Curve": {"keys": k, "preInfinityExtrap": "RCCE_Constant",
                                                     "postInfinityExtrap": "RCCE_Constant"}})})


def recreate(name):
    path = f"{FOLDER}/{name}"
    if u.call(ASSETS, "exists", {"path": path})["returnValue"]:
        u.call(ASSETS, "delete", {"path": path})
    n("CreateNiagaraSystem", {"assetName": name, "assetPath": FOLDER, "templateSystem": ref(EMPTY_SYSTEM)})
    s = Sys(name)
    for e in n("GetSystemSummary", {"system": ref(s.path)})["returnValue"].get("emitters", []):
        n("RemoveEmitter", {"emitterToRemove": s.item(e["emitterName"])})
    return s


def add_emitter(s, template, name, loop, duration, local=True):
    n("AddEmitter", {"system": ref(s.path), "templateEmitter": ref(f"{TEMPLATES}/{template}.{template}"),
                     "emitterName": name})
    if local:
        n("SetEmitterData", {"emitter": s.item(name), "emitterData": {"propertyValues": json.dumps({"bLocalSpace": True})}})
    s.set(name, EU, "EmitterState", "Loop Behavior", INFINITE if loop else ONCE)
    s.set(name, EU, "EmitterState", "Loop Duration", F(duration))


def add_module(s, emitter, script, asset, after=""):
    return n("AddModule", {"moduleLocationRef": s.item(emitter, script, after), "moduleAsset": ref(asset)})["returnValue"]


def system_state(s, loop, duration):
    s.set("", SU, "SystemState", "Loop Behavior", INFINITE if loop else ONCE)
    s.set("", SU, "SystemState", "Loop Duration", F(duration))


# --- emitter recipes ------------------------------------------------------------------------------------------------
SOFT = "/Niagara/DefaultAssets/DefaultSpriteMaterial.DefaultSpriteMaterial"      # round radial falloff, takes colour
CURVE_DI = "/Niagara/DynamicInputs/ValueFromCurve/FloatFromCurve.FloatFromCurve"
JITTER = "/Niagara/Modules/Update/Position/JitterPosition.JitterPosition"
SCALE_BEAM = "/Niagara/Modules/Beams/ScaleBeamWidth.ScaleBeamWidth"
SIZE_ENUM = "/Niagara/Enums/ENiagara_SizeScaleMode.ENiagara_SizeScaleMode"
ROT_ENUM = "/Niagara/Enums/ENiagara_SpriteRotationMode.ENiagara_SpriteRotationMode"


def renderer(s, emitter, values, index=0):
    n("SetRendererData", {"renderer": s.item(emitter, renderer=index),
                          "rendererData": {"propertyValues": json.dumps(values)}})


def beam(s, name, loop, start, end, width, color, alpha, count=60, life=0.8, jitter=None, width_scale=None,
         delay=0.0, duration=1.0):
    """A StaticBeam ribbon from local start to local end. The sprite material sampled down its middle column (U
    fixed at 0.5) gives a soft round cross-section, so a ribbon reads as a glowing tube, not a flat strip."""
    add_emitter(s, "StaticBeam", name, loop, duration)
    if delay:
        s.set(name, EU, "SpawnBurst_Instantaneous", "Spawn Time", F(delay))
    if start != (0, 0, 0):
        s.set(name, EU, "BeamEmitterSetup", "Absolute Beam Start", B(False))
        s.set(name, EU, "BeamEmitterSetup", "Beam Start", V3(*start))
    s.set(name, EU, "BeamEmitterSetup", "Beam End", V3(*[e - b for e, b in zip(end, start)]))
    s.set(name, EU, "SpawnBurst_Instantaneous", "Spawn Count", I(count))
    s.set(name, PS, "InitializeParticle", "Lifetime", F(life))
    s.set(name, PS, "BeamWidth", "Beam Width", F(width))
    s.set(name, PU, "Color", "Color", COL(*color))
    s.set(name, PU, "Color", ["Scale Alpha", "FloatCurve"], curve(alpha))
    if width_scale:
        m = add_module(s, name, PU, SCALE_BEAM, "Color")["moduleName"]
        s.set(name, PU, m, "Beam Width Scale", DI(CURVE_DI))
        s.set(name, PU, m, ["Beam Width Scale", "FloatCurve"], curve(width_scale))
    if jitter:
        amount, delay = jitter
        m = add_module(s, name, PU, JITTER, "Color")["moduleName"]
        s.set(name, PU, m, "Jitter Amount", F(amount))
        s.set(name, PU, m, "Jitter Delay", F(delay))
    # A jittered strand keeps straight segments between its points (no tessellation smoothing): jagged like lightning.
    renderer(s, name, {"Material": ref(SOFT), "bCastShadows": False,
                       "TessellationMode": "Disabled" if jitter else "Automatic", "UV0Settings": {
        "distributionMode": "ScaledUniformly", "leadingEdgeMode": "SmoothTransition",
        "trailingEdgeMode": "SmoothTransition", "bEnablePerParticleUOverride": False,
        "bEnablePerParticleVRangeOverride": False, "tilingLength": 100,
        "offset": {"x": 0.5, "y": 0}, "scale": {"x": 0, "y": 1}}})


def flare(s, name, loop, at, size, color, alpha, life, grow=None, delay=0.0, duration=1.0):
    """One big soft sprite: a flash or a glow."""
    add_emitter(s, "SimpleSpriteBurst", name, loop, duration)
    if delay:
        s.set(name, EU, "SpawnBurst_Instantaneous", "Spawn Time", F(delay))
    s.set(name, PS, "InitializeParticle", "Lifetime", F(life))
    s.set(name, PS, "InitializeParticle", "Color", COL(*color))
    s.set(name, PS, "InitializeParticle", "Uniform Sprite Size", F(size))
    if at != (0, 0, 0):
        s.set(name, PS, "InitializeParticle", "UsePositionOffset", B(True))
        s.set(name, PS, "InitializeParticle", "Position Offset", V3(*at))
    s.set(name, PU, "ScaleColor", ["Scale Alpha", "FloatCurve"], curve(alpha))
    if grow:
        m = add_module(s, name, PU, "/Niagara/Modules/Update/Size/ScaleSpriteSize.ScaleSpriteSize", "ScaleColor")["moduleName"]
        s.set(name, PU, m, "Uniform Curve Sprite Scale", curve(grow))   # the module's default mode: Uniform Curve
    renderer(s, name, {"bCastShadows": False})


def sparks(s, name, loop, at, count, speed, life, size, color, away_from=(0, 0, 0), radius=20, gravity=-980,
           drag=1.5, shape=None, delay=0.0, duration=1.0):
    """A burst of hot specks flying out of a small sphere, streaked along their velocity."""
    add_emitter(s, "OmnidirectionalBurst", name, loop, duration)
    if delay:
        s.set(name, EU, "SpawnBurst_Instantaneous", "Spawn Time", F(delay))
    s.set(name, EU, "SpawnBurst_Instantaneous", "Spawn Count", I(count))
    s.set(name, PS, "InitializeParticle", "Lifetime Min", F(life[0]))
    s.set(name, PS, "InitializeParticle", "Lifetime Max", F(life[1]))
    s.set(name, PS, "InitializeParticle", "Color", COL(*color))
    # Streaks: width x length, the length laid along the velocity by the renderer's VelocityAligned alignment.
    s.set(name, PS, "InitializeParticle", "Sprite Size Mode", E(SIZE_ENUM, "ENiagara_SizeScaleMode::NewEnumerator2",
                                                                "Random Non-Uniform"))
    s.set(name, PS, "InitializeParticle", "Sprite Size Min", V2(size[0], size[2]))
    s.set(name, PS, "InitializeParticle", "Sprite Size Max", V2(size[1], size[3]))
    s.set(name, PS, "InitializeParticle", "Sprite Rotation Mode", E(ROT_ENUM, "ENiagara_SpriteRotationMode::NewEnumerator3",
                                                                    "Unset"))
    if at != (0, 0, 0):
        s.set(name, PS, "InitializeParticle", "UsePositionOffset", B(True))
        s.set(name, PS, "InitializeParticle", "Position Offset", V3(*at))
    if shape:
        shape(s, name)
    else:
        s.set(name, PS, "ShapeLocation", "Sphere Radius", F(radius))
    s.set(name, PS, "AddVelocity", ["Velocity Speed", "Minimum"], F(speed[0]))
    s.set(name, PS, "AddVelocity", ["Velocity Speed", "Maximum"], F(speed[1]))
    s.set(name, PS, "AddVelocity", "Origin Offset", V3(*away_from))
    s.set(name, PU, "GravityForce", "Gravity", V3(0, 0, gravity))
    s.set(name, PU, "Drag", "Drag", F(drag))
    renderer(s, name, {"bCastShadows": False, "Alignment": "VelocityAligned"})


# --- the two systems ------------------------------------------------------------------------------------------------
LENGTH = 1830.0                       # cm: muzzle to target along the system's local +X (Verse cannot pass it)
END = (LENGTH, 0, 0)
IMPACT_TIME = 1.6                     # s: the impact's emitters and system all run once for this long
HOLD_FADE = [(0, 1), (0.62, 1), (1, 0)]          # over a 0.8 s life: full for 0.5 s, gone at 0.8 s
FLICKER = [(0, 1), (0.1, 0.4), (0.2, 1), (0.3, 0.5), (0.42, 1), (0.55, 0.3), (0.62, 0.9), (0.8, 0.3), (1, 0)]


def build_laser(name, loop=False):
    s = recreate(name)
    system_state(s, loop, 1.0)
    # Widest first: translucent ribbons sort by emitter order, so the core draws over the glow.
    beam(s, "Glow", loop, (0, 0, 0), END, 300, (0.05, 0.6, 1.6, 0.45), HOLD_FADE, count=40,
         width_scale=[(0, 1.5), (0.12, 1.0), (0.62, 1.0), (1, 0.6)])
    beam(s, "Core", loop, (0, 0, 0), END, 90, (2.0, 6.0, 8.0, 1.0), HOLD_FADE, count=40,
         width_scale=[(0, 1.6), (0.1, 1.0), (0.62, 1.0), (1, 0.3)])
    # Few points per strand, so the ribbon runs in straight segments between jittered points: jagged, not curly.
    beam(s, "Arc1", loop, (0, 0, 0), END, 14, (1.2, 4.0, 10.0, 1.0), FLICKER, count=16, jitter=(65, 0.04))
    beam(s, "Arc2", loop, (0, 0, 0), END, 9, (3.0, 6.0, 10.0, 1.0), FLICKER, count=12, jitter=(80, 0.03))
    flare(s, "MuzzleFlash", loop, (0, 0, 0), 260, (0.6, 3.0, 6.0, 0.8), [(0, 1), (0.15, 0.7), (0.7, 0.5), (1, 0)],
          0.65, grow=[(0, 0.6), (0.15, 1.0), (1, 0.6)])
    flare(s, "HitFlash", loop, END, 340, (0.8, 3.5, 7.0, 0.8), [(0, 1), (0.15, 0.7), (0.7, 0.5), (1, 0)], 0.75,
          grow=[(0, 0.5), (0.15, 1.0), (1, 0.7)])
    sparks(s, "MuzzleSparks", loop, (0, 0, 0), 50, (600, 1500), (0.15, 0.45), (4, 8, 30, 70), (2.0, 6.0, 10.0, 1.0),
           away_from=(-60, 0, 0), radius=25)
    sparks(s, "HitSparks", loop, END, 110, (800, 2200), (0.25, 0.7), (5, 10, 40, 110), (2.0, 6.0, 10.0, 1.0),
           away_from=(LENGTH + 80, 0, 0), radius=40)
    return s


RING = E("/Niagara/Enums/Location/ENiagara_LocationShapes.ENiagara_LocationShapes", "ENiagara_LocationShapes::NewEnumerator4",
         "Ring / Disc")


def ring_shape(radius):
    def apply(s, name):
        s.set(name, PS, "ShapeLocation", "Shape Primitive", RING)
        s.set(name, PS, "ShapeLocation", "Ring Radius", F(radius))
    return apply


def build_impact(name, loop=False):
    s = recreate(name)
    system_state(s, loop, IMPACT_TIME)
    flare(s, "Glow", loop, (0, 0, 0), 420, (0.3, 2.0, 5.0, 0.7), [(0, 1), (0.3, 0.7), (1, 0)], 1.3,
          grow=[(0, 0.5), (0.15, 1.0), (1, 1.3)], duration=IMPACT_TIME)
    flare(s, "Flash", loop, (0, 0, 0), 560, (3.0, 7.0, 10.0, 1.0), [(0, 1), (0.35, 0.6), (1, 0)], 0.3,
          grow=[(0, 0.4), (0.25, 1.0), (1, 1.2)], duration=IMPACT_TIME)
    # Shock ring: soft blobs on a flat ring around the hit, flung outward and braked by drag to ~5 m across.
    sparks(s, "Ring", loop, (0, 0, 0), 160, (1100, 1300), (0.45, 0.6), (70, 90, 70, 90), (0.6, 3.5, 8.0, 0.6),
           gravity=0, drag=2.5, shape=ring_shape(40), duration=IMPACT_TIME)
    sparks(s, "Sparks", loop, (0, 0, 0), 160, (900, 2600), (0.4, 1.2), (5, 10, 40, 120), (2.0, 6.0, 10.0, 1.0),
           radius=40, drag=1.2, duration=IMPACT_TIME)
    for i, (end, delay) in enumerate([((260, 40, 170), 0.0), ((-180, 210, 60), 0.12), ((40, -240, -60), 0.25),
                                      ((-90, -120, 230), 0.4)]):
        beam(s, f"Arc{i + 1}", loop, (0, 0, 0), end, 10, (1.5, 5.0, 10.0, 1.0), FLICKER, count=8, life=0.7,
             jitter=(45, 0.04), delay=delay, duration=IMPACT_TIME)
    return s


SYSTEMS = {"NS_fnm_laser": build_laser, "NS_fnm_impact": build_impact}
ALLOWED = ("/Niagara/", "/Engine/", "/Script/", MOUNT + "/")
# Every UEFN-created Niagara system carries this effect type (scalability defaults); UEFN sets it, validation knows it.
EFFECT_TYPE = "/Game/Valkyrie/Niagara/EffectTypes/UEFN_DefaultEffectType"


def check(name):
    """Print compile state, stack issues and every external dependency; return False on an error or a foreign path."""
    s = Sys(name)
    ok = True
    state = n("GetSystemCompileState", {"system": ref(s.path)})["returnValue"]
    print(f"{name}: compile {state['aggregateStatus']}, errors {state['bHasErrors']}, warnings {state['bHasWarnings']}")
    ok &= not state["bHasErrors"]
    issues = n("GetStackIssues", {"system": ref(s.path)})["returnValue"]
    print(f"  stack issues: {issues['numErrors']} errors, {issues['numWarnings']} warnings, {issues['numInfos']} infos")
    for i in issues["issues"]:
        if i["severity"] != "Info":
            print(f"    {i['severity']}: {i['stackDisplayPath']}: {i['shortDescription']}")
    ok &= issues["numErrors"] == 0
    deps = n("GetSystemDependencies", {"system": ref(s.path)})["returnValue"]
    paths = sorted({r["refPath"] for v in deps.values() for r in v})
    paths += sorted(u.call(ASSETS, "get_dependencies", {"asset_path": f"{FOLDER}/{name}"})["returnValue"])
    for p in paths:
        foreign = not p.startswith(ALLOWED) and not p.startswith(EFFECT_TYPE)
        print(f"  {'FOREIGN ' if foreign else ''}{p}")
        ok &= not foreign
    return ok


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--preview", type=float, metavar="SECONDS")
    ap.add_argument("--clean-preview", action="store_true")
    a = ap.parse_args()
    if a.clean_preview:
        for name in SYSTEMS:
            if u.call(ASSETS, "exists", {"path": f"{FOLDER}/{name}_preview"})["returnValue"]:
                print("deleted", name + "_preview", u.call(ASSETS, "delete", {"path": f"{FOLDER}/{name}_preview"}))
        return
    if a.preview is not None:
        for name, build in SYSTEMS.items():
            s = build(name + "_preview", loop=True)
            n("SetSystemData", {"system": ref(s.path), "systemData": {"propertyValues": json.dumps({
                "WarmupTime": a.preview, "WarmupTickCount": max(1, round(a.preview / 0.05)), "WarmupTickDelta": 0.05})}})
            u.call(ASSETS, "save_assets", {"asset_paths": [s.path]})
            print("built", s.path)
        return
    if not a.check:
        for name, build in SYSTEMS.items():
            s = build(name)
            u.call(ASSETS, "save_assets", {"asset_paths": [s.path]})
            print("built", s.path)
    ok = all([check(name) for name in SYSTEMS])
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
