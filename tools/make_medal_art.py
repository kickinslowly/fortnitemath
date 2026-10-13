"""Prepare the finish board's medal and mascot art for the HUD (Pillow, no UEFN): the three medal renders and Volt's
cheering portrait come from Meshy (bought 2026-10-13, kept untracked under art/) as 1024x1024 RGBA with a transparent
background; each becomes a 256x256 HUD texture that console/verse/fnm_ui.verse draws on the finish board.

    python tools/make_medal_art.py [OUTDIR]   # writes tools/art/fnm_medal_{gold,silver,bronze}.png and fnm_volt.png

    art/medals/gold_raw.png            -> fnm_medal_gold.png      (T_fnm_medal_gold,   ShowResults, Medal "GOLD")
    art/medals/silver_raw.png          -> fnm_medal_silver.png    (T_fnm_medal_silver, Medal "SILVER")
    art/medals/bronze_raw.png          -> fnm_medal_bronze.png    (T_fnm_medal_bronze, Medal "BRONZE")
    art/mascot/hud_portrait_raw.png    -> fnm_volt.png            (T_fnm_volt, the host on every finish board)

Per image: alpha below ALPHA_CUT (16) is zeroed (the raw silver and bronze carry a stray near-transparent pixel at the
image edge, so their alpha bbox started at 0,0 and the medal would have shrunk), the image is cropped to the bbox of what
is left, padded to a square with the subject centred (transparent padding), and resized to 256x256 (LANCZOS; Pillow
resizes RGBA premultiplied, so no dark fringe). Deterministic: a rerun writes identical bytes. Then
`python tools/import_art.py medal_gold medal_silver medal_bronze volt` brings the textures into the UEFN project (HUD keys
are the PNG names less "fnm_").
"""
import sys
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
OUT = Path(__file__).parent / "art"
SIZE = 256
ALPHA_CUT = 16
# (raw file, output name)
JOBS = (
    ("art/medals/gold_raw.png", "fnm_medal_gold.png"),
    ("art/medals/silver_raw.png", "fnm_medal_silver.png"),
    ("art/medals/bronze_raw.png", "fnm_medal_bronze.png"),
    ("art/mascot/hud_portrait_raw.png", "fnm_volt.png"),
)


def prepare(raw: Image.Image) -> Image.Image:
    """Zero alpha below ALPHA_CUT, crop to the alpha bbox, centre on a transparent square, resize to SIZE x SIZE."""
    im = raw.convert("RGBA")
    r, g, b, a = im.split()
    a = a.point(lambda v: 0 if v < ALPHA_CUT else v)
    im = Image.merge("RGBA", (r, g, b, a))
    box = a.getbbox()
    if box is None:
        raise ValueError("image has no pixel at or above the alpha cut")
    im = im.crop(box)
    w, h = im.size
    side = max(w, h)
    square = Image.new("RGBA", (side, side), (0, 0, 0, 0))
    square.paste(im, ((side - w) // 2, (side - h) // 2))
    return square.resize((SIZE, SIZE), Image.LANCZOS)


def main(out: Path = OUT):
    out.mkdir(parents=True, exist_ok=True)
    for src, name in JOBS:
        done = prepare(Image.open(ROOT / src))
        done.save(out / name, optimize=False)
        print(f"wrote {out / name}  {done.size[0]}x{done.size[1]}  alpha bbox {done.getchannel('A').getbbox()}")


if __name__ == "__main__":
    main(Path(sys.argv[1]) if len(sys.argv) > 1 else OUT)
