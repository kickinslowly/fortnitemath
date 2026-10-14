"""Swap an imported static mesh for a re-made FBX in place, keeping every placed actor on it; and audit the project's meshes against
UEFN's LOD0 vertex cap.

    python tools/replace_mesh.py --audit                                   # every project mesh's LOD0 render vertices, flags > CAP
    python tools/replace_mesh.py FNM_TitanPeakArt/Gate/SM_fnm_tp_gate art/titanpeak/gate/raw/gate_blender.fbx

UEFN's validator warns when a static mesh's LOD0 render data has more than CAP vertices (ValkyrieValidator_StaticMesh, a Warning:
the session and the memory calculation still ran, 2026-10-14). The importers keep new meshes under it (tools/simplify_glb.py
aims a GLB at VERT_BUDGET before the FBX export); this swaps a mesh that is already placed.

Why the dance: StaticMeshTools.import_file refuses an existing asset ("already exists"), and deleting an asset empties every
reference to it (uefn-mcp skill). So the FBX goes into a staging folder WITHOUT materials, its slots take the old mesh's materials
(the old texture keeps its lODBias 0), each actor that shows the old mesh is pointed at the staged one, the old mesh is deleted,
the staged one moved into its path, the actors pointed at that path, and the staging folder deleted. Collision: an old mesh with
no shapes (build_titanpeak strips the dressing's) gets none; otherwise the import's own stays. Everything is read back; save at the end.
"""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import uefn_mcp as u  # noqa: E402

ASSETS = "editor_toolset.toolsets.asset.AssetTools"
STATIC = "editor_toolset.toolsets.static_mesh.StaticMeshTools"
OBJ = "editor_toolset.toolsets.object.ObjectTools"
SCENE = "editor_toolset.toolsets.scene.SceneTools"
ROOT = Path(__file__).resolve().parent.parent

CAP = 30000                 # UEFN's LOD0 render-vertex limit (the validator's message)
VERT_BUDGET = 27000         # what tools/simplify_glb.py aims at: 10 % under CAP
STAGING = "FNM_MeshSwap"
MESH_ACTOR = "/Script/FortniteGame.FortStaticMeshActor"


def ref(p):
    return {"refPath": p}


def obj_path(path):
    """/a/b/Name -> /a/b/Name.Name"""
    return path if "." in path.rsplit("/", 1)[-1] else f"{path}.{path.rsplit('/', 1)[-1]}"


def mount():
    return "/" + u.call(ASSETS, "find_assets", {"folder_path": "", "name": "M_fnm_wall_bm_marble", "recursive": True})["returnValue"][0].split("/")[1]


def getp(obj, key):
    r = u.call(OBJ, "get_properties", {"instance": ref(obj), "properties": [key]})["returnValue"]
    return (json.loads(r) if isinstance(r, str) else r).get(key)


def setp(obj, values):
    u.call(OBJ, "set_properties", {"instance": ref(obj), "values": json.dumps(values)})


def verts(mesh):
    return u.call(STATIC, "get_vertex_count", {"mesh": ref(obj_path(mesh)), "lod_index": 0})["returnValue"]


def shapes(mesh):
    """Collision shapes on the mesh's BodySetup (as build_titanpeak.shape_count)."""
    body = getp(obj_path(mesh), "bodySetup")
    if not body:
        return 0
    return sum(len(v) for k, v in (getp(body["refPath"], "aggGeom") or {}).items() if k.endswith("Elems"))


def slots(mesh):
    m = ref(obj_path(mesh))
    return [(s, u.call(STATIC, "get_material", {"mesh": m, "slot_name": s})["returnValue"]["refPath"])
            for s in u.call(STATIC, "get_material_slots", {"mesh": m})["returnValue"]]


def users(mesh):
    """[(actor path, label, static mesh component path)] for every placed actor that shows `mesh`. Exits on any other referencer."""
    names = {r.rsplit(".", 1)[-1]: r for r in u.call(ASSETS, "get_referencers", {"asset_path": mesh})["returnValue"]}
    actors = [a for a in u.call(SCENE, "find_actors", {"actor_type": ref(MESH_ACTOR), "collision_channels": []})["returnValue"]
              if a["name"] in names]
    if len(actors) != len(names):
        sys.exit(f"{mesh}: referencers that are not placed mesh actors: {sorted(set(names) - {a['name'] for a in actors})}")
    out = []
    for a in actors:
        comp = getp(a["actorPath"], "staticMeshComponent")["refPath"]
        if (getp(comp, "staticMesh") or {}).get("refPath") != obj_path(mesh):
            sys.exit(f"{a['label']}: its component does not show {mesh}")
        out.append((a["actorPath"], a["label"], comp))
    return out


def point(actors, mesh):
    """Point each actor's component at `mesh`, read it back, save (get_referencers reads saved packages: before the save the old
    mesh still listed the actor)."""
    for _, label, comp in actors:
        setp(comp, {"staticMesh": ref(obj_path(mesh))})
        now = (getp(comp, "staticMesh") or {}).get("refPath")
        if now != obj_path(mesh):
            sys.exit(f"{label}: shows {now} after pointing it at {mesh}")
    u.call(ASSETS, "save_assets", {"asset_paths": []})


def replace(rel, fbx):
    m = mount()
    old = rel if rel.startswith("/") else f"{m}/{rel}"
    old = old.split(".")[0]
    name = old.rsplit("/", 1)[1]
    fbx = Path(fbx) if Path(fbx).is_absolute() else ROOT / fbx
    if not fbx.exists():
        sys.exit(f"{fbx} is missing")
    actors = users(old)
    mats, had_shapes, before = slots(old), shapes(old), verts(old)
    print(f"{name}: {before} LOD0 vertices, {len(mats)} slot(s), {had_shapes} collision shape(s), on {[a[1] for a in actors]}")

    stage = f"{m}/{STAGING}"
    if u.call(ASSETS, "exists", {"path": stage})["returnValue"]:
        staged = u.call(ASSETS, "find_assets", {"folder_path": stage, "name": "", "recursive": True})["returnValue"]
        if any(u.call(ASSETS, "get_referencers", {"asset_path": s.split(".")[0]})["returnValue"] for s in staged):
            sys.exit(f"{stage} holds a mesh placed actors show (an interrupted swap): finish that one by hand first")
        u.call(ASSETS, "delete", {"path": stage})
    new = f"{stage}/{name}"
    u.call(STATIC, "import_file", {"folder_path": stage, "asset_name": name, "source_file": str(fbx),
                                   "import_materials": False, "import_textures": False})
    new_slots = [s for s, _ in slots(new)]
    if len(new_slots) != len(mats):
        sys.exit(f"staged {name} has {len(new_slots)} slot(s), the old one {len(mats)}: left both in place, staging in {stage}")
    for s, (_, mat) in zip(new_slots, mats):
        u.call(STATIC, "set_material", {"mesh": ref(obj_path(new)), "slot_name": s, "material": ref(mat)})
    if not had_shapes:
        u.call(STATIC, "remove_collisions", {"mesh": ref(obj_path(new))})

    point(actors, new)
    left = u.call(ASSETS, "get_referencers", {"asset_path": old})["returnValue"]
    if left:
        sys.exit(f"{old} is still referenced by {left}: not deleted; the actors show the staged mesh {new}")
    if not u.call(ASSETS, "delete", {"path": old})["returnValue"]:
        sys.exit(f"could not delete {old}; the actors show the staged mesh {new}")
    if not u.call(ASSETS, "move", {"path": new, "new_path": old})["returnValue"]:
        sys.exit(f"could not move {new} to {old}; the actors show the staged mesh")
    point(actors, old)
    # the move leaves an ObjectRedirector at the staged path; nothing points at it once the actors are re-pointed and saved
    for s in u.call(ASSETS, "find_assets", {"folder_path": stage, "name": "", "recursive": True})["returnValue"]:
        s = s.split(".")[0]
        if (u.call(ASSETS, "get_asset_class", {"asset_path": s})["returnValue"] == "ObjectRedirector"
                and not u.call(ASSETS, "get_referencers", {"asset_path": s})["returnValue"]):
            u.call(ASSETS, "delete", {"path": s})
    if u.call(ASSETS, "find_assets", {"folder_path": stage, "name": "", "recursive": True})["returnValue"] == []:
        u.call(ASSETS, "delete", {"path": stage})
    u.call(ASSETS, "save_assets", {"asset_paths": []})

    after, now_mats, now_shapes = verts(old), slots(old), shapes(old)
    print(f"{name}: {before} -> {after} LOD0 vertices; slots {[s[1].rsplit('.', 1)[1] for s in now_mats]}; "
          f"{now_shapes} collision shape(s); on {len(users(old))} actor(s)")
    if after > CAP or [s[1] for s in now_mats] != [s[1] for s in mats] or bool(now_shapes) != bool(had_shapes):
        sys.exit("READ-BACK FAILED")


def audit():
    m = mount()
    over = 0
    for a in u.call(ASSETS, "find_assets", {"folder_path": "", "name": "SM_", "recursive": True})["returnValue"]:
        if not a.startswith(m + "/"):
            continue
        v = verts(a)
        over += v > CAP
        print(f"{v:>7}  {a[len(m) + 1:].split('.')[0]}{'   OVER ' + str(CAP) if v > CAP else ''}")
    print(f"{over} mesh(es) over {CAP}")
    return over


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("mesh", nargs="?", help="content path under the project mount, e.g. FNM_CannonArt/SM_fnm_megacannon")
    ap.add_argument("fbx", nargs="?", help="the FBX to import in its place")
    ap.add_argument("--audit", action="store_true")
    a = ap.parse_args()
    if a.audit:
        sys.exit(1 if audit() else 0)
    if not (a.mesh and a.fbx):
        ap.error("mesh and fbx, or --audit")
    replace(a.mesh, a.fbx)


if __name__ == "__main__":
    main()
