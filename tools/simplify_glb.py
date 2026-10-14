"""Fit a Meshy GLB under UEFN's LOD0 vertex cap before it goes to FBX (meshoptimizer: tools/meshopt/simplify.mjs).

    python tools/simplify_glb.py art/titanpeak/gate/raw/gate.glb          # prints the counts; writes gate_lod.glb when over budget

UEFN's validator warns when a static mesh's LOD0 has more than 30,000 render vertices (tools/replace_mesh.py CAP). A GLB's vertex
count is nearly its render count (glTF splits a vertex per normal and UV): UE read the gate's original 43,037 as 43,050, but a
simplified gate's 25,961 as 28,528 (more tangent splits on the thinner triangles), so the GLB aims at VERT_BUDGET / UE_SPLIT.
meshopt keeps the GLB's own normals and UVs and never joins a double-sided part's two faces; a Blender collapse on merged vertices
does both, and the gate's post tops came out crinkled (2026-10-14, editor close-ups against the original mesh: the flat orange posts
and dark bunting in those frames are the original's too, low capture mips and single-sided flags seen from behind).

fit(src) returns the GLB to export: src itself when within budget, else <stem>_lod.glb next to it (rebuilt when older than src or
the simplifier). Needs node; installs tools/meshopt's pinned packages on first use.
"""
import json
import struct
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from replace_mesh import VERT_BUDGET  # noqa: E402

MESHOPT = Path(__file__).resolve().parent / "meshopt"
UE_SPLIT = 1.10             # UE's render count over the GLB's on a simplified mesh: 1.099 for the gate (2026-10-14)
WIN = sys.platform == "win32"


def counts(glb):
    """(vertices, triangles) summed over every primitive of a .glb."""
    b = Path(glb).read_bytes()
    g = json.loads(b[20:20 + struct.unpack_from("<I", b, 12)[0]])
    v = t = 0
    for m in g["meshes"]:
        for p in m["primitives"]:
            v += g["accessors"][p["attributes"]["POSITION"]]["count"]
            t += g["accessors"][p["indices"]]["count"] // 3 if "indices" in p else 0
    return v, t


def fit(src, budget=VERT_BUDGET):
    src = Path(src)
    v, t = counts(src)
    if v <= budget:
        return src
    dst = src.with_name(f"{src.stem}_lod.glb")
    newest = max(src.stat().st_mtime, Path(__file__).stat().st_mtime, (MESHOPT / "simplify.mjs").stat().st_mtime)
    if dst.exists() and dst.stat().st_mtime >= newest:
        return dst
    if not (MESHOPT / "node_modules").exists():
        subprocess.run(["npm", "ci"], cwd=MESHOPT, check=True, capture_output=True, shell=WIN)
    r = subprocess.run(["node", str(MESHOPT / "simplify.mjs"), str(src), str(dst), str(int(budget / UE_SPLIT))],
                       check=True, capture_output=True, text=True)
    res = json.loads(r.stdout.strip().splitlines()[-1])
    print(f"  meshopt: {src.name} {v} vertices / {t} triangles -> {dst.name} {res['vertices']} / {res['triangles']} "
          f"(ratio {res['ratio']}, error {res['error']})")
    return dst


if __name__ == "__main__":
    for a in sys.argv[1:]:
        p = Path(a)
        print(p.name, counts(p), "->", fit(p).name)
