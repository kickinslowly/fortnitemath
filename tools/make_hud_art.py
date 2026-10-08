"""Draw the question slate and the answer-tile frame as RGBA PNGs (no PIL: plain zlib), for the HUD's texture_blocks
(console/verse/fnm_ui.verse). Deterministic: seeded noise, so a rerun writes identical bytes.

    python tools/make_hud_art.py [OUTDIR]   # writes tools/art/fnm_slate.png and fnm_tile.png (or into OUTDIR)

fnm_slate.png  1024x256  dark chalk slate: noise, chalk-dust smudges, vignette, rounded corners, alpha 236 (the
               frame is a color_block rim in Verse, so it stays crisp when the slate stretches).
fnm_tile.png   560x240   a 12 px white ring round a near-black interior, drawn large and stretched down to the 240x100
               on-screen tile (ring ~5 px). Verse tints it per door, so the ring takes the door colour and the
               interior stays dark.
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
    print("wrote", out / "fnm_slate.png", out / "fnm_tile.png")
