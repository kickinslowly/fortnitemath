// Simplify a GLB to at most MAX_VERTICES vertices with meshoptimizer, keeping its normals and UVs (tools/simplify_glb.py runs it).
//
//     node tools/meshopt/simplify.mjs in.glb out.glb MAX_VERTICES
//
// Weld (exact duplicates only, so a double-sided part's two faces stay apart), then simplifyWithAttributes with normals and UVs in
// the error metric and the Permissive flag, which lets a collapse cross a UV seam when the attribute error allows it. Without it
// meshopt stalls on a fragmented Meshy UV atlas: the gate stopped at 29.6k vertices at any ratio, error 0.069; permissive reached
// 25k at error 0.005 (2026-10-14). The ratio is bisected for the most triangles that fit. Prints one JSON line.
import { NodeIO } from '@gltf-transform/core';
import { weld, compactPrimitive, prune } from '@gltf-transform/functions';
import { MeshoptSimplifier as S } from 'meshoptimizer';

const [src, dst, maxArg] = process.argv.slice(2);
const MAX = Number(maxArg);
const WEIGHTS = [0.5, 0.5, 0.5, 1.0, 1.0];     // normal xyz, uv
await S.ready;
const io = new NodeIO();
const doc = await io.read(src);
await doc.transform(weld());

const prims = doc.getRoot().listMeshes().flatMap(m => m.listPrimitives()).map(prim => {
  const pos = prim.getAttribute('POSITION').getArray();
  const nrm = prim.getAttribute('NORMAL').getArray();
  const uv = prim.getAttribute('TEXCOORD_0').getArray();
  const n = pos.length / 3, attrs = new Float32Array(n * 5);
  for (let i = 0; i < n; i++) attrs.set([nrm[3 * i], nrm[3 * i + 1], nrm[3 * i + 2], uv[2 * i], uv[2 * i + 1]], 5 * i);
  return { prim, pos, attrs, n, idx: new Uint32Array(prim.getIndices().getArray()) };
});

function simplify(ratio) {
  let vertices = 0, triangles = 0, error = 0;
  const out = prims.map(p => {
    const target = Math.floor(p.idx.length * ratio / 3) * 3;
    const [idx, err] = S.simplifyWithAttributes(p.idx, p.pos, 3, p.attrs, 5, WEIGHTS, null, target, 1.0, ['Permissive']);
    vertices += S.compactMesh(new Uint32Array(idx))[1];
    triangles += idx.length / 3;
    error = Math.max(error, err);
    return idx;
  });
  return { out, vertices, triangles, error, ratio };
}

let best = null, lo = 0.02, hi = 1.0;
for (let i = 0; i < 14; i++) {                  // largest ratio whose result fits
  const mid = (lo + hi) / 2, r = simplify(mid);
  if (r.vertices <= MAX) { best = r; lo = mid; } else hi = mid;
}
if (!best) { console.error(`cannot reach ${MAX} vertices`); process.exit(1); }
best.out.forEach((idx, i) => {
  const p = prims[i];
  p.prim.getIndices().setArray(p.n > 65535 ? idx : new Uint16Array(idx));
  compactPrimitive(p.prim);
});
await doc.transform(prune());
await io.write(dst, doc);
console.log(JSON.stringify({ vertices: best.vertices, triangles: best.triangles, ratio: +best.ratio.toFixed(4), error: +best.error.toFixed(5) }));
