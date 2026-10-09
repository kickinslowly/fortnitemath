"""Draw the door signs: one square PNG per answer letter in the HUD answer-tile style (fnm_ui.verse): a near-black
rounded tile with a ring in the door's colour and the letter in that colour. tools/import_art.py imports each as a
textured quad mesh (SM_door_sign_<x>), and tools/build_course.py door_dress hangs it on the door panel.

    python tools/make_door_signs.py [OUTDIR]   # writes tools/art/door_sign_a.png .. door_sign_d.png

Colours come from build_course.LETTER_COLOURS (= FnmDoorColors). Named door_sign_* (not fnm_*) so import_art's
HUD-texture step leaves them alone.
"""
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, str(Path(__file__).parent))
from build_course import LETTERS, LETTER_COLOURS  # noqa: E402

OUT = Path(__file__).parent / "art"
SIZE = 512
RING = 30
RADIUS = 70
INTERIOR = (26, 26, 30)
FONT = "C:/Windows/Fonts/ariblk.ttf"   # Arial Black
SS = 4                                  # supersampling for clean edges


def sign(rgb):
    s = SIZE * SS
    colour = tuple(int(round(c * 255)) for c in rgb)
    img = Image.new("RGB", (s, s), colour)   # corners outside the rounded ring blend into the door panel
    d = ImageDraw.Draw(img)
    d.rounded_rectangle([0, 0, s - 1, s - 1], radius=RADIUS * SS, fill=colour)
    d.rounded_rectangle([RING * SS, RING * SS, s - 1 - RING * SS, s - 1 - RING * SS],
                        radius=(RADIUS - RING) * SS, fill=INTERIOR)
    return img, d, colour, s


def draw(letter, rgb):
    img, d, colour, s = sign(rgb)
    font = ImageFont.truetype(FONT, int(s * 0.62))
    l, t, r, b = d.textbbox((0, 0), letter, font=font)
    d.text(((s - (r - l)) / 2 - l, (s - (b - t)) / 2 - t), letter, font=font, fill=colour)
    return img.resize((SIZE, SIZE), Image.LANCZOS)


if __name__ == "__main__":
    out = Path(sys.argv[1]) if len(sys.argv) > 1 else OUT
    out.mkdir(parents=True, exist_ok=True)
    for letter, rgb in zip(LETTERS, LETTER_COLOURS):
        draw(letter, rgb).save(out / f"door_sign_{letter.lower()}.png", optimize=True)
    print("wrote", ", ".join(f"door_sign_{c.lower()}.png" for c in LETTERS), "in", out)
