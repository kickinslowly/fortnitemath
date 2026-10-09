"""Draw the boss-mode banner burst and the nuke icon as RGBA PNGs (no PIL: plain zlib), for the HUD's texture_blocks
(console/verse/fnm_ui.verse, BOSS_MODE.md section 9). Deterministic: seeded jitter, so a rerun writes identical bytes.

    python tools/make_boss_art.py [OUTDIR]   # writes tools/art/fnm_banner.png and fnm_nuke.png (or into OUTDIR)

fnm_banner.png  1024x256  a comic speech-burst: a star outline in polar form round the centre,
                r(t) = E(t) * (1 + 0.16 * |sin(11 t)| * (1 + lobe jitter)) with E an ellipse 480 x 108 (shrunk by a
                few percent when the spikes would leave the image), red (200,30,30) core to orange (255,140,20)
                rim, 6 px dark outline (40,10,10), antialiased, alpha 245 inside, transparent outside.
fnm_nuke.png    256x256   a mushroom cloud in pale yellow (255,236,150), lighter on top: a cap (circle (128,92) r 70
                with three bumps on top), a stem (rounded rect 60 wide, y 120..210) and a base ring (ellipse 170 x 40
                at y 205), 6 px dark outline (40,30,10), transparent outside.
"""
import bisect
import math
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from make_hud_art import cover, png, rounded_dist  # noqa: E402

OUT = Path(__file__).parent / "art"
SEED = 20261009
OUTLINE_PX = 6


def lerp(a, b, t):
    return a + (b - a) * t


def mix(c0, c1, t):
    return tuple(lerp(x, y, t) for x, y in zip(c0, c1))


# ---------------------------------------------------------------- banner

def burst_polygon(ea, eb, lobes, spike, rng):
    """Vertices (x, y relative to the centre) of the star: 2 * lobes points spaced EQUALLY along the ellipse's arc, valleys
    on the ellipse, peaks pushed out along its normal by `spike` px (+-25 % seeded jitter)."""
    fine = 20000
    pts = [(ea * math.cos(2 * math.pi * k / fine), eb * math.sin(2 * math.pi * k / fine)) for k in range(fine + 1)]
    cum = [0.0]
    for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
        cum.append(cum[-1] + math.hypot(x1 - x0, y1 - y0))
    total = cum[-1]
    verts = []
    for v in range(2 * lobes):
        # half equal-arc, half equal-angle spacing: equal arc alone leaves the narrow ends with two fat spikes
        k_arc = min(bisect.bisect_left(cum, total * v / (2 * lobes)), fine - 1)
        k = int(round(0.5 * k_arc + 0.5 * fine * v / (2 * lobes)))
        x, y = pts[k]
        if v % 2 == 0:                                      # a peak (v = 0 and v = lobes are the two tips): out along the normal
            nx, ny = x / (ea * ea), y / (eb * eb)
            nl = math.hypot(nx, ny)
            cos2 = (x / ea) ** 2 / ((x / ea) ** 2 + (y / eb) ** 2)   # 1 at the tips, 0 at top and bottom
            length = spike * (0.85 + 0.9 * cos2) * (1.0 + rng.uniform(-0.25, 0.25))
            x, y = x + nx / nl * length, y + ny / nl * length
        else:                                               # a valley: a hair of seeded wobble
            x, y = x * (1 + rng.uniform(-0.01, 0.01)), y * (1 + rng.uniform(-0.01, 0.01))
        verts.append((x, y))
    return verts


def banner(w=1024, h=256, ea=440.0, eb=92.0, lobes=30, spike=30.0, alpha=245):
    """Comic burst: the valleys sit on an ellipse, the peaks `spike` px outside it (0.85 x at the top and bottom,
    1.75 x at the tips, +-25 % jitter), so the star stays inside the 512 x 128 half-size with a few px for the AA."""
    rng = random.Random(SEED)
    cx, cy = w / 2, h / 2
    verts = [(cx + x, cy + y) for x, y in burst_polygon(ea, eb, lobes, spike, rng)]
    edges = list(zip(verts, verts[1:] + verts[:1]))
    near = 8.0
    core, rim, edge = (200, 30, 30), (255, 140, 20), (40, 10, 10)
    rows = []
    for y in range(h):
        py = y + 0.5
        # Edges that can matter on this row: within `near` px vertically (distance), and the ones that straddle the row
        # (crossings: inside = an odd number of crossings to the left of the pixel).
        local = [(a, b) for a, b in edges if min(a[1], b[1]) - near <= py <= max(a[1], b[1]) + near]
        xs = sorted(a[0] + (py - a[1]) / (b[1] - a[1]) * (b[0] - a[0]) for a, b in edges
                    if (a[1] <= py) != (b[1] <= py))
        out = bytearray()
        for x in range(w):
            px = x + 0.5
            dmin = 99.0
            for (ax, ay), (bx, by) in local:
                abx, aby = bx - ax, by - ay
                t = max(0.0, min(1.0, ((px - ax) * abx + (py - ay) * aby) / (abx * abx + aby * aby)))
                dd = math.hypot(px - ax - t * abx, py - ay - t * aby)
                if dd < dmin:
                    dmin = dd
            inside = bisect.bisect_left(xs, px) % 2 == 1
            d = -dmin if inside else dmin                       # signed distance, negative inside
            a = cover(d)
            if a <= 0.0:
                out += b"\x00\x00\x00\x00"
                continue
            dx, dy = px - cx, py - cy
            e = ea * eb / math.hypot(eb * dx / max(math.hypot(dx, dy), 1e-9), ea * dy / max(math.hypot(dx, dy), 1e-9))
            g = min(1.0, math.hypot(dx, dy) / (e + spike)) ** 1.3   # red core out to orange at the peaks
            fill = mix(core, rim, g)
            o = cover(-(d + OUTLINE_PX))                        # 1 in the outline band, 0 inside it
            rgb = mix(fill, edge, o)
            out += bytes(int(round(c)) for c in rgb) + bytes([int(round(alpha * a))])
        rows.append(bytes(out))
    return png(w, h, rows)


# ---------------------------------------------------------------- nuke

def ellipse_dist(px, py, cx, cy, a, b):
    """Approximate signed distance to an ellipse (exact on the axes; plenty for a 6 px outline)."""
    k = math.hypot((px - cx) / a, (py - cy) / b)
    return (k - 1.0) * min(a, b) if k > 0 else -min(a, b)


def smin(a, b, k):
    """Smooth union of two signed distances (fillets where the shapes meet)."""
    hh = max(k - abs(a - b), 0.0) / k
    return min(a, b) - hh * hh * k / 4.0


def _box(px, py, cx, cy, hx, hy, r):
    qx = abs(px - cx) - (hx - r)
    qy = abs(py - cy) - (hy - r)
    return math.hypot(max(qx, 0.0), max(qy, 0.0)) + min(max(qx, qy), 0.0) - r


def nuke_dist(px, py):
    cap = math.hypot(px - 128, py - 92) - 70
    # three bumps on top, two billows low on the sides: the cap reads as a boiling cloud, not a head
    for bx, by, br in ((78, 52, 28), (128, 34, 31), (178, 52, 28), (58, 122, 30), (198, 122, 30)):
        cap = smin(cap, math.hypot(px - bx, py - by) - br, 10)
    stem = _box(px, py, 128, 165, 30, 45, 18)          # 60 wide, y 120..210
    base = ellipse_dist(px, py, 128, 205, 85, 20)      # the ring the blast spreads into
    return smin(smin(cap, stem, 8), base, 10)


def nuke(w=256, h=256):
    pale, light, low, edge = (255, 236, 150), (255, 252, 218), (238, 200, 110), (40, 30, 10)
    rows = []
    for y in range(h):
        out = bytearray()
        for x in range(w):
            d = nuke_dist(x + 0.5, y + 0.5)
            a = cover(d)
            if a <= 0.0:
                out += b"\x00\x00\x00\x00"
                continue
            top = max(0.0, min(1.0, (110 - (y + 0.5)) / 90.0))           # lighter toward the top of the cap
            bot = max(0.0, min(1.0, ((y + 0.5) - 150) / 70.0))           # a touch darker toward the base
            fill = mix(mix(pale, light, top), low, bot * 0.8)
            o = cover(-(d + OUTLINE_PX))
            rgb = mix(fill, edge, o)
            out += bytes(int(round(c)) for c in rgb) + bytes([int(round(255 * a))])
        rows.append(bytes(out))
    return png(w, h, rows)


if __name__ == "__main__":
    out = Path(sys.argv[1]) if len(sys.argv) > 1 else OUT
    out.mkdir(parents=True, exist_ok=True)
    (out / "fnm_banner.png").write_bytes(banner())
    (out / "fnm_nuke.png").write_bytes(nuke())
    print("wrote", out / "fnm_banner.png", out / "fnm_nuke.png")
