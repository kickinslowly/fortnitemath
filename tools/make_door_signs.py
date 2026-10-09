"""Draw the door-panel textures: one per answer letter, the whole texture in the door's colour with the HUD answer tile
(fnm_ui.verse: a near-black rounded tile, a ring and the letter in the door's colour) where the panel's front face shows
it. tools/import_art.py imports each as a material (M_door_face_<x>); tools/build_course.py door_dress makes it the door
prop's doorAnimatingMaterial, so the letter is painted on the panel: it swings away with the door and has no collision.

    python tools/make_door_signs.py [OUTDIR]   # writes tools/art/door_face_a.png .. door_face_d.png

The door mesh (Neo_Door_01, on OilRig_Platform_Wall_01_Door_01) maps its front face onto part of the texture,
mirrored left-right: measured 2026-10-09 with stripe and grid calibration textures on station 1's door B (FACE_U, FACE_V).
Colours come from build_course.LETTER_COLOURS (= FnmDoorColors). Named door_face_* (not fnm_*) so import_art's
HUD-texture step leaves them alone.
"""
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, str(Path(__file__).parent))
from build_course import LETTERS, LETTER_COLOURS  # noqa: E402

OUT = Path(__file__).parent / "art"
SIZE = 1024
# The panel's front face as seen from the hallway: its RIGHT edge is at u = FACE_U[0], its LEFT edge at FACE_U[1]
# (mirrored); its top at v = FACE_V[0], its bottom at FACE_V[1]. The face is PANEL_W x PANEL_H cm.
FACE_U = (0.042, 0.613)
FACE_V = (0.04, 1.0)
PANEL_W, PANEL_H = 142, 228
TILE = 96               # tile edge, cm
TILE_Z = 165            # tile centre above the floor, cm (the letter above a third-person character's head)
RING = 6                # ring width, cm
RADIUS = 14             # corner radius, cm
INTERIOR = (26, 26, 30)
FONT = "C:/Windows/Fonts/ariblk.ttf"   # Arial Black
SS = 2                  # supersampling


def face(letter, rgb):
    s = SIZE * SS
    colour = tuple(int(round(c * 255)) for c in rgb)
    img = Image.new("RGB", (s, s), colour)
    d = ImageDraw.Draw(img)
    pu = (FACE_U[1] - FACE_U[0]) * s / PANEL_W           # texture px per cm, across
    pv = (FACE_V[1] - FACE_V[0]) * s / PANEL_H           # and down
    cu = (FACE_U[0] + FACE_U[1]) / 2 * s                 # the panel's centre line
    cv = FACE_V[0] * s + (PANEL_H - TILE_Z) * pv
    hw, hh = TILE / 2 * pu, TILE / 2 * pv
    box = [cu - hw, cv - hh, cu + hw, cv + hh]
    d.rounded_rectangle(box, radius=RADIUS * pu, fill=colour)
    d.rounded_rectangle([box[0] + RING * pu, box[1] + RING * pv, box[2] - RING * pu, box[3] - RING * pv],
                        radius=(RADIUS - RING) * pu, fill=INTERIOR)
    # The letter, drawn upright on its own layer, stretched to the face's px/cm and mirrored to undo the mesh's flip.
    gh = int(TILE * 0.62 * pv)
    font = ImageFont.truetype(FONT, gh)
    glyph = Image.new("L", (gh * 2, gh * 2), 0)
    gd = ImageDraw.Draw(glyph)
    l, t, r, b = gd.textbbox((0, 0), letter, font=font)
    gd.text((-l, -t), letter, font=font, fill=255)
    glyph = glyph.crop((0, 0, r - l, b - t))
    glyph = glyph.resize((max(1, int(glyph.width * pu / pv)), glyph.height)).transpose(Image.FLIP_LEFT_RIGHT)
    img.paste(colour, (int(cu - glyph.width / 2), int(cv - glyph.height / 2)), glyph)
    return img.resize((SIZE, SIZE), Image.LANCZOS)


if __name__ == "__main__":
    out = Path(sys.argv[1]) if len(sys.argv) > 1 else OUT
    out.mkdir(parents=True, exist_ok=True)
    for letter, rgb in zip(LETTERS, LETTER_COLOURS):
        face(letter, rgb).save(out / f"door_face_{letter.lower()}.png", optimize=True)
    print("wrote", ", ".join(f"door_face_{c.lower()}.png" for c in LETTERS), "in", out)
