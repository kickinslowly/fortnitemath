"""Draw the question slate and the answer-tile frame as RGBA PNGs (no PIL: plain zlib), for the HUD's texture_blocks
(console/verse/fnm_ui.verse). Deterministic: seeded noise, so a rerun writes identical bytes.

    python tools/make_hud_art.py [OUTDIR]   # writes tools/art/fnm_slate.png and fnm_tile.png (or into OUTDIR)

fnm_slate.png  1024x256  dark chalk slate: noise, chalk-dust smudges, vignette, rounded corners, alpha 236 (the
               frame is a color_block rim in Verse, so it stays crisp when the slate stretches).
fnm_shield.png 256x256   a cyan shield with a dark outline and a white highlight (G10: the streak line's shield indicator).
fnm_cell.png   128x128   a rounded square ring round a near-black interior: the brag grid's tile (the 560x240 tile would squash).
fnm_redeem.png 256x256   an amber disc, left half filled, right half dark, dark outline (G10: a brag-grid tile redeemed at the boss).
fnm_tile.png   560x240   a 12 px white ring round a near-black interior, drawn large and stretched down to the 256x112
               on-screen tile (ring ~6 px). Verse tints it per tile (FnmTileSrgb through FnmSrgb: a raw color{} draws
               ~3.86x too bright), so the ring takes the tile colour and the interior stays dark.
"""
import math
import random
import struct
import sys
import zlib
from pathlib import Path

OUT = Path(__file__).parent / "art"
SEED = 20261008


def png(w, h, rows):
    """rows: h bytes objects of w*4 RGBA bytes each."""
    raw = zlib.compress(b"".join(b"\x00" + r for r in rows), 9)

    def chunk(t, data):
        return struct.pack(">I", len(data)) + t + data + struct.pack(">I", zlib.crc32(t + data) & 0xFFFFFFFF)
    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 6, 0, 0, 0))
            + chunk(b"IDAT", raw) + chunk(b"IEND", b""))


def rounded_dist(px, py, w, h, inset, radius):
    """Signed distance from pixel centre (px, py) to a rounded rectangle inset from a w x h image (negative inside)."""
    hx, hy = w / 2 - inset, h / 2 - inset
    qx = abs(px - w / 2) - (hx - radius)
    qy = abs(py - h / 2) - (hy - radius)
    return math.hypot(max(qx, 0.0), max(qy, 0.0)) + min(max(qx, qy), 0.0) - radius


def cover(d):
    """Antialiased coverage of a 1 px edge at signed distance d."""
    return max(0.0, min(1.0, 0.5 - d))


def slate(w=1024, h=256, radius=18, alpha=236):
    rng = random.Random(SEED)
    base = (34, 38, 40)
    # Chalk dust: soft lighter discs, added to every channel.
    light = [[0.0] * w for _ in range(h)]
    for _ in range(24):
        cx, cy = rng.uniform(0, w), rng.uniform(0, h)
        r = rng.uniform(30, 90)
        amp = rng.uniform(8, 14)
        for y in range(max(0, int(cy - r)), min(h, int(cy + r) + 1)):
            row = light[y]
            for x in range(max(0, int(cx - r)), min(w, int(cx + r) + 1)):
                t = ((x + 0.5 - cx) ** 2 + (y + 0.5 - cy) ** 2) / (r * r)
                if t < 1.0:
                    row[x] += amp * (1.0 - t) ** 2
    rows = []
    for y in range(h):
        out = bytearray()
        for x in range(w):
            a = cover(rounded_dist(x + 0.5, y + 0.5, w, h, 0, radius))
            if a <= 0.0:
                out += b"\x00\x00\x00\x00"
                continue
            dx, dy = (x + 0.5 - w / 2) / (w / 2), (y + 0.5 - h / 2) / (h / 2)
            vig = 1.0 - 0.18 * (dx * dx + dy * dy) / 2.0     # corner: d^2 = 1
            px = []
            for c in base:
                v = (c + light[y][x] + rng.randint(-6, 6)) * vig
                px.append(max(0, min(255, int(round(v)))))
            out += bytes(px) + bytes([int(round(alpha * a))])
        rows.append(bytes(out))
    return png(w, h, rows)


def _sdf_png(inside, size=256, ss=3):
    """Render RGBA from inside(x, y) -> (r, g, b, a) or None, for x, y in 0..1, supersampled ss x ss (deterministic)."""
    import numpy as np
    n = size * ss
    ys, xs = np.mgrid[0:n, 0:n]
    px, py = (xs + 0.5) / n, (ys + 0.5) / n
    rgba = inside(px, py)                       # float array (n, n, 4), premultiplied-free colour + alpha 0..1
    a = rgba[..., 3]
    rgb = rgba[..., :3] * a[..., None]
    rgb = rgb.reshape(size, ss, size, ss, 3).mean(axis=(1, 3))
    a = a.reshape(size, ss, size, ss).mean(axis=(1, 3))
    out = np.zeros((size, size, 4))
    ok = a > 0
    out[ok, :3] = rgb[ok] / a[ok][:, None]
    out[..., 3] = a
    data = np.clip(np.rint(out * 255), 0, 255).astype(np.uint8)
    return png(size, size, [bytes(data[y].tobytes()) for y in range(size)])


def _shield_dist(px, py, grow):
    """Inside test of the shield outline grown by `grow` (negative = shrunk), as a boolean array."""
    import numpy as np
    t = (py - 0.10) / 0.82                       # 0 at the top edge, 1 at the point
    half = np.where(t < 0.5, 0.36, 0.36 * np.sqrt(np.clip(1 - ((t - 0.5) / 0.5) ** 2 * 0.98, 0, 1)))
    return (np.abs(px - 0.5) <= half + grow) & (t >= -grow / 0.82) & (t <= 1 + grow / 0.82)


def shield():
    import numpy as np

    def inside(px, py):
        rgba = np.zeros(px.shape + (4,))
        outer = _shield_dist(px, py, 0.0)
        body = _shield_dist(px, py, -0.035)
        rgba[outer] = (0.10, 0.10, 0.12, 1.0)
        rgba[body] = (0.12, 0.62, 0.95, 1.0)
        light = body & (px < 0.5) & (py < 0.62)                 # lighter left-top quadrant
        rgba[light] = (0.38, 0.80, 1.0, 1.0)
        inner = _shield_dist(px, py, -0.085) & ~_shield_dist(px, py, -0.115)
        rgba[inner] = (0.85, 0.96, 1.0, 1.0)                    # a thin white inner rim
        return rgba
    return _sdf_png(inside)


def redeem():
    import numpy as np

    def inside(px, py):
        rgba = np.zeros(px.shape + (4,))
        r = np.hypot(px - 0.5, py - 0.5)
        rgba[r <= 0.43] = (0.10, 0.10, 0.12, 1.0)
        disc = r <= 0.37
        rgba[disc] = (0.20, 0.17, 0.12, 1.0)                    # the dark half
        rgba[disc & (px < 0.5)] = (1.0, 0.72, 0.12, 1.0)        # the amber half
        rgba[(np.abs(px - 0.5) < 0.012) & (r <= 0.37)] = (0.10, 0.10, 0.12, 1.0)
        return rgba
    return _sdf_png(inside)


def tile(w=560, h=240, radius=36, ring=12):
    rows = []
    for y in range(h):
        out = bytearray()
        for x in range(w):
            a = cover(rounded_dist(x + 0.5, y + 0.5, w, h, 0, radius))
            if a <= 0.0:
                out += b"\x00\x00\x00\x00"
                continue
            i = cover(rounded_dist(x + 0.5, y + 0.5, w, h, ring, radius - ring))   # 1 inside the interior
            rgb = [int(round(255 * (1 - i) + c * i)) for c in (26, 26, 30)]
            out += bytes(rgb) + bytes([int(round(a * (255 * (1 - i) + 230 * i)))])
        rows.append(bytes(out))
    return png(w, h, rows)


if __name__ == "__main__":
    out = Path(sys.argv[1]) if len(sys.argv) > 1 else OUT
    out.mkdir(parents=True, exist_ok=True)
    (out / "fnm_slate.png").write_bytes(slate())
    (out / "fnm_tile.png").write_bytes(tile())
    (out / "fnm_cell.png").write_bytes(tile(128, 128, 24, 10))
    (out / "fnm_shield.png").write_bytes(shield())
    (out / "fnm_redeem.png").write_bytes(redeem())
    print("wrote", out / "fnm_slate.png", out / "fnm_tile.png", out / "fnm_cell.png", out / "fnm_shield.png", out / "fnm_redeem.png")
