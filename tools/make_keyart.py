"""Discover release art for DOORS OF DOOM: the Meshy key art and logo raws in art/keyart and art/logo -> art/keyart/out.

    python tools/make_keyart.py

Writes landscape 1920x1080 and portrait 1080x1920 thumbnails (with the logo and art-only), each a centre "cover" crop of its
raw, and the logo as a transparent PNG cropped to its alpha. The raws are Meshy nano-banana-pro images (task ids in
art/keyart/meshy_tasks.json) composed from an editor capture of station 1, the chosen logo (art/logo, pick b), Volt's
portrait and the titan concept: everything shown exists in the game (Epic rule 1.13), with no Fortnite name, logo or
player character. Re-runnable.
"""
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "art" / "keyart"
OUT = RAW / "out"
LOGO = ROOT / "art" / "logo" / "logo_b_raw.png"
SIZES = {"landscape": (1920, 1080), "portrait": (1080, 1920)}


def cover(im, size):
    """Scale im to cover size, then crop the centre."""
    w, h = size
    s = max(w / im.width, h / im.height)
    im = im.resize((round(im.width * s), round(im.height * s)), Image.Resampling.LANCZOS)
    x, y = (im.width - w) // 2, (im.height - h) // 2
    return im.crop((x, y, x + w, y + h))


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    for shape, size in SIZES.items():
        for kind in ("logo", "art"):
            src = RAW / f"{shape}_{kind}_raw.png"
            if not src.exists():
                print("missing", src.name)
                continue
            out = OUT / f"doors_of_doom_{shape}_{'with_logo' if kind == 'logo' else 'art_only'}.png"
            cover(Image.open(src).convert("RGB"), size).save(out)
            print("wrote", out.relative_to(ROOT), size)
    logo = Image.open(LOGO).convert("RGBA")
    alpha = logo.getchannel("A").point(lambda a: 0 if a < 16 else 255)
    logo = logo.crop(alpha.getbbox())
    out = OUT / "doors_of_doom_logo.png"
    logo.save(out)
    print("wrote", out.relative_to(ROOT), logo.size)


if __name__ == "__main__":
    main()
