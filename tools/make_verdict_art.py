"""Draw the verdict check mark and cross as 256x256 RGBA PNGs (no PIL: plain zlib), for the HUD's
texture_blocks. The default HUD font has no check/cross glyphs.

    python tools/make_verdict_art.py      # writes tools/art/fnm_check.png and fnm_cross.png
"""
import math
import struct
import zlib
from pathlib import Path

N = 256
OUT = Path(__file__).parent / "art"


def seg_dist(px, py, ax, ay, bx, by):
    dx, dy = bx - ax, by - ay
    t = max(0.0, min(1.0, ((px - ax) * dx + (py - ay) * dy) / (dx * dx + dy * dy)))
    return math.hypot(px - (ax + t * dx), py - (ay + t * dy))


def draw(segments, rgb, width=26.0, outline=10.0):
    rows = []
    for y in range(N):
        row = bytearray([0])
        for x in range(N):
            d = min(seg_dist(x + 0.5, y + 0.5, *s) for s in segments)
            if d <= width:        # the stroke, antialiased edge
                a = min(1.0, width - d + 0.5)
                c = tuple(int(v * a) for v in rgb)
                row += bytes(c) + bytes([255])
            elif d <= width + outline:   # dark outline so it reads on any background
                a = min(1.0, width + outline - d + 0.5)
                row += bytes([0, 0, 0, int(220 * a)])
            else:
                row += bytes([0, 0, 0, 0])
        rows.append(bytes(row))
    raw = zlib.compress(b"".join(rows), 9)

    def chunk(t, data):
        return struct.pack(">I", len(data)) + t + data + struct.pack(">I", zlib.crc32(t + data) & 0xFFFFFFFF)
    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", N, N, 8, 6, 0, 0, 0))
            + chunk(b"IDAT", raw) + chunk(b"IEND", b""))


if __name__ == "__main__":
    OUT.mkdir(exist_ok=True)
    (OUT / "fnm_check.png").write_bytes(draw([(48, 136, 104, 196), (104, 196, 212, 64)], (60, 230, 60)))
    (OUT / "fnm_cross.png").write_bytes(draw([(60, 60, 196, 196), (196, 60, 60, 196)], (235, 30, 30)))
    print("wrote", OUT / "fnm_check.png", OUT / "fnm_cross.png")
